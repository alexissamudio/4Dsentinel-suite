#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""check_agents.py - Chequeo estructural determinista de los agentes.

Verifica que cada plugins/sentinel-agents/agents/*.md cumpla:
- frontmatter con name, description, model: inherit, maxTurns
- tools allowlist SIN Write/Edit/Bash (read-only por construccion)
- referencia el contrato compartido en el cuerpo
"""

from __future__ import annotations

import sys
from pathlib import Path

from frontmatter_utils import frontmatter, parse_tools

REPO_ROOT = Path(__file__).resolve().parent.parent
AGENTS_DIR = REPO_ROOT / "plugins" / "sentinel-agents" / "agents"
# Escritura/edicion: prohibidas SIEMPRE, sin excepcion.
PROHIBIDAS = {"Write", "Edit", "MultiEdit", "NotebookEdit"}
# Bash: prohibido por defecto; permitido SOLO para los agentes de este set
# (ejecutores). Allowlist cerrada y bidireccional (ver check_agent): un agente
# con Bash fuera del set falla; un agente del set sin Bash falla (drift).
BASH_ALLOWED = {"validator", "debugger"}
# Allowlist POSITIVO de tools validas para un agente read-only. Cerrado a
# proposito: un tool fuera de este set (un typo como 'Reed', o una tool nueva
# sin decision explicita) frena el CI en vez de pasar silencioso (defensa F1:
# no solo se rechaza lo prohibido, se exige que lo declarado sea conocido).
# Al sumar una tool read-only nueva (p.ej. WebFetch), agregarla aca a mano.
KNOWN_AGENT_TOOLS = {"Read", "Grep", "Glob", "Bash"}


def check_agent(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    fm = frontmatter(text)
    errs = []
    for campo in ("name", "description", "model", "maxTurns", "tools"):
        if campo not in fm:
            errs.append(f"falta frontmatter '{campo}'")
    if fm.get("model") != "inherit":
        errs.append(f"model debe ser 'inherit' (es '{fm.get('model')}')")
    # tools en cualquiera de los dos formatos (inline con comas o bloque lista
    # YAML): parse_tools reune todo en un set, asi Write/Bash se detectan
    # siempre, sin importar como se declaren.
    tools = parse_tools(text)
    conflict = tools & PROHIBIDAS
    if conflict:
        errs.append(f"tools incluye herramientas de escritura/edicion: {sorted(conflict)}")
    # Allowlist positivo: reporta tools desconocidas (typos) que PROHIBIDAS no
    # cubre; las prohibidas ya tienen su propio mensaje, no se duplican aca.
    unknown = tools - KNOWN_AGENT_TOOLS - PROHIBIDAS
    if unknown:
        errs.append(f"tools declara herramientas desconocidas (typo?): {sorted(unknown)}")
    # Bash: allowlist cerrada y bidireccional, evaluada por-archivo (file-driven).
    name = fm.get("name", path.stem)
    if "Bash" in tools and name not in BASH_ALLOWED:
        errs.append(f"'{name}' declara Bash pero no esta en BASH_ALLOWED (read-only)")
    if name in BASH_ALLOWED and "Bash" not in tools:
        errs.append(f"'{name}' esta en BASH_ALLOWED pero NO declara Bash (drift)")
    if "agent-contract" not in text:
        errs.append("el cuerpo no referencia agent-contract.md")
    return errs


def main() -> int:
    agents = sorted(AGENTS_DIR.glob("*.md"))
    if not agents:
        print("ERROR - no hay agentes en agents/", file=sys.stderr)
        return 1
    fallas = 0
    for a in agents:
        errs = check_agent(a)
        if errs:
            fallas += 1
            print(f"ERROR - {a.name}:", file=sys.stderr)
            for e in errs:
                print(f"  - {e}", file=sys.stderr)
        else:
            print(f"OK - {a.name}")
    return 1 if fallas else 0


if __name__ == "__main__":
    sys.exit(main())
