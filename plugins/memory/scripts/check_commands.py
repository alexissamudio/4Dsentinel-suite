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

import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent  # plugins/memory
COMMANDS_DIR = REPO_ROOT / "commands"
SKILLS_DIR = REPO_ROOT / "skills"
SUITE_ROOT = REPO_ROOT.parent.parent  # raiz de 4Dsentinel-suite


def _plugin_jsons() -> list[Path]:
    """Todos los plugins/*/.claude-plugin/plugin.json de la suite. La regla
    anti-CWE-427 aplica a los TRES plugins, no solo a memory: una regresion
    futura que declare mcpServers PATH-resuelto en cualquiera debe frenar CI.
    Un plugin sin plugin.json simplemente no aparece (no es error)."""
    return sorted(SUITE_ROOT.glob("plugins/*/.claude-plugin/plugin.json"))


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


def _command_is_safe(command: str) -> bool:
    """True si el command NO es secuestrable por cwd/PATH-hijack (CWE-427).

    Seguro = ruta absoluta POSIX (/...), ruta absoluta Windows (X:\\ o X:/),
    UNC (\\\\host\\share) o variable expandida por Claude Code (${...}). Un
    command pelado (resuelto por PATH) NO es seguro: en Windows el cwd precede
    al PATH, asi que un exe hostil plantado en el repo se auto-ejecutaria. Se
    exige separador tras la unidad: `C:foo` (sin barra) es DRIVE-RELATIVE en
    Windows (resuelve contra el cwd de la unidad, hijackeable), no absoluto; un
    solo backslash (`\\foo`, raiz-relativo de la unidad actual) tampoco es seguro.
    """
    return bool(re.match(r"^(/|\\\\|[A-Za-z]:[\\/]|\$\{)", command))


def check_plugin_json(path: Path) -> list[str]:
    """El plugin.json de memory NO debe declarar un mcpServers con command
    resuelto por PATH. Regla anti-regresion del fix CWE-427: el registro del
    MCP lo hace /suite-setup con `claude mcp add` y ruta absoluta verificada."""
    if not path.exists():
        return [f"no existe {path.name}"]
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return [f"JSON invalido: {e}"]

    servers = data.get("mcpServers")
    if not servers:
        return []  # sin mcpServers = el registro es via /suite-setup (correcto)

    errs = []
    for name, cfg in servers.items():
        if not isinstance(cfg, dict):
            errs.append(f"mcpServers['{name}'] no es un objeto")
            continue
        command = cfg.get("command", "")
        if not isinstance(command, str):
            errs.append(f"mcpServers['{name}'].command no es un string")
            continue
        if not _command_is_safe(command):
            errs.append(
                f"mcpServers['{name}'].command = {command!r} es resoluble por PATH "
                f"(cwd/PATH-hijack, CWE-427). Sacalo del plugin.json: el MCP se "
                f"registra en /suite-setup con `claude mcp add` y ruta absoluta. "
                f"Si tiene que quedar, usa ruta absoluta (/... o X:...) o ${{...}}."
            )
    return errs


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

    for pj in _plugin_jsons():
        rel = f"{pj.parent.parent.name}/.claude-plugin/plugin.json"
        plugin_errs = check_plugin_json(pj)
        if plugin_errs:
            fallas += 1
            print(f"ERROR - {rel}:", file=sys.stderr)
            for e in plugin_errs:
                print(f"  - {e}", file=sys.stderr)
        else:
            print(f"OK - {rel} (sin mcpServers PATH-resueltos)")

    return 1 if fallas else 0


if __name__ == "__main__":
    sys.exit(main())
