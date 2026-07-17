#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""check_verdict_enums.py - Invariante del enum de verdict de cada agente.

El enum de verdict de cada agente esta DUPLICADO: se declara inline en su ficha
(plugins/sentinel-agents/agents/*.md) y tambien en la lista canonica de la
seccion 4 de references/agent-contract.md. Hoy los 12 coinciden pero nada lo
verifica: este check falla si alguna ficha declara un enum que NO coincide con
el canonico de la seccion 4.

OJO (por diseno, NO drift): cada agente tiene su PROPIO enum (code-reviewer usa
CLEAN|CONCERNS|BLOCKED, risk-assessor usa PROCEED|PROCEED_WITH_CAUTION|DEFER,
etc.). Ademas 'INCOMPLETE' es universal (lo admiten todos). La comparacion se
hace modulo INCOMPLETE: se ignora en ambos lados para no confundir la senal.

Fuente canonica: seccion 4 del contrato. Para compliance-auditor esa seccion
lista DOS enums (los estados de la KB por control y el verdict GLOBAL); el que
compara la ficha es el verdict global (CONFORME|NO_CONFORME|PARCIAL).

Uso:  uv run scripts/check_verdict_enums.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from frontmatter_utils import frontmatter

REPO_ROOT = Path(__file__).resolve().parent.parent
AGENTS_DIR = REPO_ROOT / "plugins" / "sentinel-agents" / "agents"
CONTRACT = REPO_ROOT / "plugins" / "sentinel-agents" / "references" / "agent-contract.md"

# Token de estado universal: se ignora en la comparacion (todos lo admiten).
UNIVERSAL = "INCOMPLETE"

# Un token de enum: MAYUSCULAS con guion bajo (p. ej. PROCEED_WITH_CAUTION, OK).
_TOKEN = re.compile(r"[A-Z][A-Z_]*")
# Item de la lista de la seccion 4: "- **<agente>:** ...".
_SECTION4_ITEM = re.compile(r"^- \*\*([a-z0-9-]+):\*\*")
# Token de enum entre backticks (asi los declara la seccion 4).
_BACKTICK_TOKEN = re.compile(r"`([A-Z][A-Z_]*)`")


def _tokens(text: str) -> set[str]:
    """Set de tokens de enum en un fragmento, sin el universal INCOMPLETE."""
    return {t for t in _TOKEN.findall(text) if t != UNIVERSAL}


def parse_contract_section4(text: str) -> dict[str, set[str]]:
    """Enum canonico (verdict global) por agente, desde la seccion 4 del contrato.

    Devuelve {agente: set(tokens)} sin el universal INCOMPLETE.
    """
    # Aisla el bloque de la seccion 4 (hasta el proximo encabezado de nivel 2).
    start = text.find("## 4.")
    if start < 0:
        return {}
    rest = text[start + len("## 4.") :]
    end = rest.find("\n## ")
    block = rest if end < 0 else rest[:end]

    enums: dict[str, set[str]] = {}
    current: str | None = None
    buffer: list[str] = []

    def flush() -> None:
        if current is None:
            return
        seg = " ".join(buffer)
        # Quita parentesis: alli viven notas y la severidad de findings
        # (p. ej. "(+ findings `Critical|Important|Minor`)"), no el enum de verdict.
        seg = re.sub(r"\([^)]*\)", "", seg)
        # compliance-auditor lista los estados de la KB y LUEGO el verdict global;
        # el que se compara con la ficha es el global.
        marker = "global es"
        if marker in seg:
            seg = seg.split(marker, 1)[1]
        tokens = {t for t in _BACKTICK_TOKEN.findall(seg) if t != UNIVERSAL}
        if tokens:
            enums[current] = tokens

    for line in block.splitlines():
        # El bullet final "- **INCOMPLETE** ..." cierra la lista de agentes.
        if line.startswith("- **INCOMPLETE"):
            break
        m = _SECTION4_ITEM.match(line)
        if m:
            flush()
            current = m.group(1)
            buffer = [line]
        elif current is not None:
            buffer.append(line)
    flush()
    return enums


def parse_ficha_enum(text: str) -> set[str] | None:
    """Enum de verdict declarado inline en una ficha, sin el universal INCOMPLETE.

    Dos formas soportadas:
      - Pipe (10 agentes):  `verdict: A|B|C|INCOMPLETE`
      - Flechas (risk-assessor): "... 1-3 -> PROCEED; ... -> INCOMPLETE."
    """
    # Forma pipe: verdict: seguido de tokens unidos por '|'.
    m = re.search(r"verdict:\s*([A-Z][A-Z_]*(?:\|[A-Z][A-Z_]*)+)", text)
    if m:
        return _tokens(m.group(1))

    # Forma flecha (fallback): tokens tras '->' en el parrafo del verdict.
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if "verdict:" in line and "global" in line:
            region = " ".join(lines[i : i + 3])
            tokens = {t for t in re.findall(r"->\s*([A-Z][A-Z_]*)", region) if t != UNIVERSAL}
            if tokens:
                return tokens
    return None


def main() -> int:
    if not CONTRACT.exists():
        print(f"ERROR - no existe el contrato: {CONTRACT}", file=sys.stderr)
        return 1
    canonical = parse_contract_section4(CONTRACT.read_text(encoding="utf-8"))
    if not canonical:
        print("ERROR - no se pudo parsear la seccion 4 del contrato", file=sys.stderr)
        return 1

    agents = sorted(AGENTS_DIR.glob("*.md"))
    if not agents:
        print("ERROR - no hay agentes en agents/", file=sys.stderr)
        return 1

    fallas = 0
    seen: set[str] = set()
    for path in agents:
        text = path.read_text(encoding="utf-8")
        name = frontmatter(text).get("name", path.stem)
        seen.add(name)
        declared = parse_ficha_enum(text)
        expected = canonical.get(name)

        if declared is None:
            fallas += 1
            print(f"MISMATCH - {name}: no se pudo parsear el enum de verdict en la ficha", file=sys.stderr)
            continue
        if expected is None:
            fallas += 1
            print(f"MISMATCH - {name}: sin entrada en la seccion 4 del contrato", file=sys.stderr)
            continue
        if declared != expected:
            fallas += 1
            missing = sorted(expected - declared)
            extra = sorted(declared - expected)
            detail = []
            if missing:
                detail.append(f"falta(n) {missing}")
            if extra:
                detail.append(f"sobra(n) {extra}")
            print(
                f"MISMATCH - {name}: ficha={sorted(declared)} vs contrato={sorted(expected)} ({'; '.join(detail)})",
                file=sys.stderr,
            )
        else:
            print(f"OK - {name}: {sorted(declared)}")

    # Entradas del contrato sin ficha correspondiente (drift inverso).
    for name in sorted(set(canonical) - seen):
        fallas += 1
        print(f"MISMATCH - {name}: en la seccion 4 pero sin ficha en agents/", file=sys.stderr)

    return 1 if fallas else 0


if __name__ == "__main__":
    sys.exit(main())
