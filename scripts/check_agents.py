#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""check_agents.py - Chequeo estructural determinista de los agentes.

Verifica que cada plugins/sentinel-agents/agents/*.md cumpla:
- frontmatter con name, description, model: inherit, maxTurns
- tools allowlist SIN Write/Edit/Bash (read-only por construcción)
- referencia el contrato compartido en el cuerpo
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
AGENTS_DIR = REPO_ROOT / "plugins" / "sentinel-agents" / "agents"
# Escritura/edición: prohibidas SIEMPRE, sin excepción.
PROHIBIDAS = {"Write", "Edit", "MultiEdit", "NotebookEdit"}
# Bash: prohibido por defecto; permitido SOLO para los agentes de este set
# (ejecutores). Allowlist cerrada y bidireccional (ver check_agent): un agente
# con Bash fuera del set falla; un agente del set sin Bash falla (drift).
BASH_ALLOWED = {"validator", "debugger"}


def frontmatter(text: str) -> dict[str, str]:
    m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if not m:
        return {}
    fm = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            fm[k.strip()] = v.strip()
    return fm


def check_agent(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    fm = frontmatter(text)
    errs = []
    for campo in ("name", "description", "model", "maxTurns", "tools"):
        if campo not in fm:
            errs.append(f"falta frontmatter '{campo}'")
    if fm.get("model") != "inherit":
        errs.append(f"model debe ser 'inherit' (es '{fm.get('model')}')")
    # tools inline con comas (constraint documentado en el contrato).
    tools = {t.strip() for t in fm.get("tools", "").split(",") if t.strip()}
    conflict = tools & PROHIBIDAS
    if conflict:
        errs.append(f"tools incluye herramientas de escritura/edición: {sorted(conflict)}")
    # Bash: allowlist cerrada y bidireccional, evaluada por-archivo (file-driven).
    name = fm.get("name", path.stem)
    if "Bash" in tools and name not in BASH_ALLOWED:
        errs.append(f"'{name}' declara Bash pero no está en BASH_ALLOWED (read-only)")
    if name in BASH_ALLOWED and "Bash" not in tools:
        errs.append(f"'{name}' está en BASH_ALLOWED pero NO declara Bash (drift)")
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
