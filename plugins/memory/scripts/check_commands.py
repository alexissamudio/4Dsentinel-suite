#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""check_commands.py - Chequeo estructural determinista del plugin memory.

Por cada plugins/memory/commands/*.md:
- frontmatter con `description` (lo que usa Claude para el slash command)
- frontmatter con `allowed-tools` (el allowlist de herramientas MCP que puede usar)

Y ademas el skill:
- plugins/memory/skills/suite-setup/SKILL.md con frontmatter `description`.

Sigue el patron de scripts/sentinel_check_skills.py (parser de frontmatter
scalar, exit codes, mensajes OK/ERROR).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent  # plugins/memory
COMMANDS_DIR = REPO_ROOT / "commands"
SKILLS_DIR = REPO_ROOT / "skills"


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


def check_command(path: Path) -> list[str]:
    fm = frontmatter(path.read_text(encoding="utf-8"))
    errs = []
    for campo in ("description", "allowed-tools"):
        if campo not in fm:
            errs.append(f"falta frontmatter '{campo}'")
    return errs


def check_skill(path: Path) -> list[str]:
    fm = frontmatter(path.read_text(encoding="utf-8"))
    return [] if "description" in fm else ["falta frontmatter 'description'"]


def main() -> int:
    commands = sorted(COMMANDS_DIR.glob("*.md"))
    if not commands:
        print("ERROR - no hay commands en commands/", file=sys.stderr)
        return 1

    fallas = 0
    for c in commands:
        errs = check_command(c)
        if errs:
            fallas += 1
            print(f"ERROR - commands/{c.name}:", file=sys.stderr)
            for e in errs:
                print(f"  - {e}", file=sys.stderr)
        else:
            print(f"OK - commands/{c.name}")

    for s in sorted(SKILLS_DIR.glob("*/SKILL.md")):
        errs = check_skill(s)
        rel = f"skills/{s.parent.name}/SKILL.md"
        if errs:
            fallas += 1
            print(f"ERROR - {rel}:", file=sys.stderr)
            for e in errs:
                print(f"  - {e}", file=sys.stderr)
        else:
            print(f"OK - {rel}")

    return 1 if fallas else 0


if __name__ == "__main__":
    sys.exit(main())
