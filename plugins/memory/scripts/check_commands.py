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

# El helper de frontmatter vive en scripts/ (raiz de la suite); este check corre
# desde plugins/memory/scripts/, asi que agrega ese dir al path para importarlo.
sys.path.insert(0, str(SUITE_ROOT / "scripts"))
from frontmatter_utils import frontmatter  # noqa: E402


def _plugin_jsons() -> list[Path]:
    """Todos los plugins/*/.claude-plugin/plugin.json de la suite. La regla
    anti-CWE-427 aplica a los TRES plugins, no solo a memory: una regresion
    futura que declare mcpServers PATH-resuelto en cualquiera debe frenar CI.
    Un plugin sin plugin.json simplemente no aparece (no es error)."""
    return sorted(SUITE_ROOT.glob("plugins/*/.claude-plugin/plugin.json"))


# Prefijo user-scope del MCP (lo que registra /suite-setup con `claude mcp add`).
# El prefijo plugin-scoped `mcp__plugin_4dsentinel-memory_codebase-memory__` quedo
# MUERTO al mover el registro a user-scope (fix CWE-427) -> los allowed-tools que
# lo usaran caian en prompt de permiso en vez de correr pre-aprobados (F3).
MCP_PREFIX = "mcp__codebase-memory__"
# Tools reales del MCP codebase-memory. Allowlist mantenido A MANO: es el unico
# ground-truth estatico (el MCP no se puede consultar en CI). Si el server agrega
# o renombra un tool, actualizar aca. Defensa de F3/F1: un allowed-tools con
# prefijo muerto o un tool inexistente frena el CI (no solo se valida la clave).
KNOWN_MCP_TOOLS = {
    "delete_project",
    "detect_changes",
    "get_architecture",
    "get_code_snippet",
    "get_graph_schema",
    "index_repository",
    "index_status",
    "ingest_traces",
    "list_projects",
    "manage_adr",
    "query_graph",
    "search_code",
    "search_graph",
    "trace_path",
}


def _parse_allowed_tools(raw: str) -> list[str]:
    """Extrae la lista de tools de un `allowed-tools` en cualquier formato:
    array JSON (`["a", "b"]`) o inline con comas (`a, b`)."""
    raw = raw.strip()
    try:
        val = json.loads(raw)
        if isinstance(val, list):
            return [str(t).strip() for t in val]
    except json.JSONDecodeError:
        pass
    inner = raw.strip().strip("[]")
    return [t.strip().strip("'\"") for t in inner.split(",") if t.strip()]


def check_allowed_tools(raw: str) -> list[str]:
    """Valida los NOMBRES de tools MCP en un allowed-tools (no solo su presencia).

    Cada tool `mcp__*` debe usar el prefijo user-scope correcto y nombrar un tool
    real del MCP. Las tools nativas (Read, Grep, ...) se aceptan sin validar aca.
    """
    errs = []
    for tool in _parse_allowed_tools(raw):
        if not tool.startswith("mcp__"):
            continue  # tool nativa: no la valida este check
        if not tool.startswith(MCP_PREFIX):
            errs.append(
                f"tool MCP '{tool}' con prefijo invalido: se espera "
                f"'{MCP_PREFIX}<tool>' (user-scope, el que registra /suite-setup)"
            )
            continue
        suffix = tool[len(MCP_PREFIX) :]
        if suffix not in KNOWN_MCP_TOOLS:
            errs.append(
                f"tool MCP '{tool}' desconocido: '{suffix}' no esta en el set del "
                f"MCP codebase-memory (revisa un typo o actualiza KNOWN_MCP_TOOLS)"
            )
    return errs


def check_command(path: Path) -> list[str]:
    fm = frontmatter(path.read_text(encoding="utf-8"))
    errs = []
    for campo in ("description", "allowed-tools"):
        if campo not in fm:
            errs.append(f"falta frontmatter '{campo}'")
    if "allowed-tools" in fm:
        errs += check_allowed_tools(fm["allowed-tools"])
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
