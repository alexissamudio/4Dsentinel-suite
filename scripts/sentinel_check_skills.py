#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""check_skills.py - Chequeo estructural determinista de los skills del plugin.

Por cada plugins/sentinel-agents/skills/<nombre>/SKILL.md:
- frontmatter con `description` (lo que usa Claude para auto-invocar)
- el cuerpo referencia el contrato o los agentes (es un orquestador de sentinel)
"""

from __future__ import annotations

import sys
from pathlib import Path

from frontmatter_utils import frontmatter

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = REPO_ROOT / "plugins" / "sentinel-agents" / "skills"


def check_skill(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    fm = frontmatter(text)
    errs = []
    if "description" not in fm:
        errs.append("falta frontmatter 'description'")
    if "agent-contract" not in text and "sentinel-agents:" not in text:
        errs.append("el cuerpo no referencia el contrato ni los agentes de sentinel")
    return errs


def main() -> int:
    skills = sorted(SKILLS_DIR.glob("*/SKILL.md"))
    if not skills:
        print("OK - no hay skills (nada que validar)")
        return 0
    fallas = 0
    for s in skills:
        errs = check_skill(s)
        nombre = s.parent.name
        if errs:
            fallas += 1
            print(f"ERROR - {nombre}:", file=sys.stderr)
            for e in errs:
                print(f"  - {e}", file=sys.stderr)
        else:
            print(f"OK - {nombre}")
    return 1 if fallas else 0


if __name__ == "__main__":
    sys.exit(main())
