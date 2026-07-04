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
PROHIBIDAS = {"Write", "Edit", "MultiEdit", "NotebookEdit", "Bash"}


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
    tools = {t.strip() for t in fm.get("tools", "").split(",") if t.strip()}
    conflict = tools & PROHIBIDAS
    if conflict:
        errs.append(f"tools incluye herramientas de escritura/ejecución: {sorted(conflict)}")
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
