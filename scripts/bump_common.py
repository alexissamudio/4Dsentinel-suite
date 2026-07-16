"""bump_common.py - Logica compartida de los bump scripts por-plugin.

Cada plugin (fluency-4d, 4dsentinel-memory, sentinel-agents) tiene su version en
DOS lugares que deben coincidir:
  1. .claude-plugin/marketplace.json  -> plugins[name==PLUGIN_NAME].version
  2. plugins/<dir>/.claude-plugin/plugin.json -> version

`metadata.version` del marketplace es la version PARAGUAS de la suite (no la de
un plugin), por eso NO entra en este check por-plugin y estas funciones NO la
tocan. El cross-check paraguas<->subtree lo hace scripts/check_suite_versions.py.

Este modulo NO es un script ejecutable: lo importan los 3 wrappers finos
(fluency_bump_version.py, memory_bump_version.py, sentinel_bump_version.py),
que aportan sus paths/PLUGIN_NAME. Asi el fix de un bug vive en UN solo lugar
(cf. auditoria 2026-07-15, F8: triplicacion que ya divergia).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

# \Z (no $): rechaza un newline final tipo "1.2.3\n" (cf. F2).
SEMVER = re.compile(r"^\d+\.\d+\.\d+\Z")


def market_entry(marketplace: dict[str, Any], plugin_name: str) -> dict[str, Any]:
    """Devuelve la entrada del plugin en marketplace.json por `name` (no por indice)."""
    plugins: list[dict[str, Any]] = marketplace.get("plugins", [])
    for entry in plugins:
        if entry.get("name") == plugin_name:
            return entry
    print(
        f"ERROR - no hay entrada name=='{plugin_name}' en marketplace.json plugins[]",
        file=sys.stderr,
    )
    raise SystemExit(1)


def read_versions(*, marketplace_path: Path, plugin_path: Path, plugin_name: str) -> dict[str, str]:
    marketplace = json.loads(marketplace_path.read_text(encoding="utf-8"))
    plugin = json.loads(plugin_path.read_text(encoding="utf-8"))
    mv = market_entry(marketplace, plugin_name).get("version")
    pv = plugin.get("version")
    if not isinstance(mv, str) or not isinstance(pv, str):
        print(
            "ERROR - falta la clave 'version' (string) en marketplace o plugin.json",
            file=sys.stderr,
        )
        raise SystemExit(1)
    return {
        f"marketplace.plugins[{plugin_name}].version": mv,
        "plugin.json version": pv,
    }


def check(*, marketplace_path: Path, plugin_path: Path, plugin_name: str) -> int:
    versions = read_versions(
        marketplace_path=marketplace_path, plugin_path=plugin_path, plugin_name=plugin_name
    )
    for lugar, version in versions.items():
        print(f"  {lugar}: {version}")
    if len(set(versions.values())) == 1:
        print(f"OK - version sincronizada: {next(iter(versions.values()))}")
        return 0
    print("ERROR - las versiones NO coinciden", file=sys.stderr)
    return 1


def set_version(
    new_version: str, *, marketplace_path: Path, plugin_path: Path, plugin_name: str
) -> int:
    if not SEMVER.match(new_version):
        print(f"ERROR - '{new_version}' no es semver X.Y.Z", file=sys.stderr)
        return 1
    marketplace = json.loads(marketplace_path.read_text(encoding="utf-8"))
    plugin = json.loads(plugin_path.read_text(encoding="utf-8"))
    # NO se toca marketplace["metadata"]["version"] (version paraguas de la suite).
    market_entry(marketplace, plugin_name)["version"] = new_version
    plugin["version"] = new_version
    marketplace_path.write_text(
        json.dumps(marketplace, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    plugin_path.write_text(
        json.dumps(plugin, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"OK - version {new_version} escrita en los 2 lugares")
    return check(
        marketplace_path=marketplace_path, plugin_path=plugin_path, plugin_name=plugin_name
    )


def main(
    *,
    doc: str | None,
    marketplace_path: Path,
    plugin_path: Path,
    plugin_name: str,
    argv: list[str] | None = None,
) -> int:
    parser = argparse.ArgumentParser(description=doc)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check", action="store_true", help="verificar sincronizacion")
    group.add_argument("--set", metavar="X.Y.Z", help="escribir nueva version")
    args = parser.parse_args(argv)
    if args.set:
        return set_version(
            args.set,
            marketplace_path=marketplace_path,
            plugin_path=plugin_path,
            plugin_name=plugin_name,
        )
    return check(
        marketplace_path=marketplace_path, plugin_path=plugin_path, plugin_name=plugin_name
    )
