#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""bump_version.py - Sincroniza la version del plugin fluency-4d.

La version de fluency-4d vive en DOS lugares (ambos deben coincidir):
  1. .claude-plugin/marketplace.json  -> plugins[name=="fluency-4d"].version
  2. plugins/fluency-4d/.claude-plugin/plugin.json -> version

`metadata.version` del marketplace es la version PARAGUAS de la suite (no la de
fluency-4d), por eso NO entra en este check por-plugin y este script NO la toca.
El cross-check paraguas<->subtree lo hace scripts/check_suite_versions.py.

Uso:
  uv run scripts/bump_version.py --check        # verifica que las 2 coincidan
  uv run scripts/bump_version.py --set 0.2.0    # escribe la nueva version en las 2
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
MARKETPLACE = REPO_ROOT / ".claude-plugin" / "marketplace.json"
PLUGIN = REPO_ROOT / "plugins" / "fluency-4d" / ".claude-plugin" / "plugin.json"
PLUGIN_NAME = "fluency-4d"

SEMVER = re.compile(r"^\d+\.\d+\.\d+$")


def _market_entry(marketplace: dict[str, Any]) -> dict[str, Any]:
    """Devuelve la entrada del plugin en marketplace.json por `name` (no por indice)."""
    plugins: list[dict[str, Any]] = marketplace.get("plugins", [])
    for entry in plugins:
        if entry.get("name") == PLUGIN_NAME:
            return entry
    print(
        f"ERROR - no hay entrada name=='{PLUGIN_NAME}' en marketplace.json plugins[]",
        file=sys.stderr,
    )
    raise SystemExit(1)


def read_versions() -> dict[str, str]:
    marketplace = json.loads(MARKETPLACE.read_text(encoding="utf-8"))
    plugin = json.loads(PLUGIN.read_text(encoding="utf-8"))
    return {
        f"marketplace.plugins[{PLUGIN_NAME}].version": _market_entry(marketplace)["version"],
        "plugin.json version": plugin["version"],
    }


def check() -> int:
    versions = read_versions()
    unique = set(versions.values())
    for lugar, version in versions.items():
        print(f"  {lugar}: {version}")
    if len(unique) == 1:
        print(f"OK - version sincronizada: {unique.pop()}")
        return 0
    print("ERROR - las versiones NO coinciden", file=sys.stderr)
    return 1


def set_version(new_version: str) -> int:
    if not SEMVER.match(new_version):
        print(f"ERROR - '{new_version}' no es semver X.Y.Z", file=sys.stderr)
        return 1
    marketplace = json.loads(MARKETPLACE.read_text(encoding="utf-8"))
    plugin = json.loads(PLUGIN.read_text(encoding="utf-8"))
    # NO se toca marketplace["metadata"]["version"] (version paraguas de la suite).
    _market_entry(marketplace)["version"] = new_version
    plugin["version"] = new_version
    MARKETPLACE.write_text(
        json.dumps(marketplace, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    PLUGIN.write_text(json.dumps(plugin, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"OK - version {new_version} escrita en los 2 lugares")
    return check()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check", action="store_true", help="verificar sincronizacion")
    group.add_argument("--set", metavar="X.Y.Z", help="escribir nueva version")
    args = parser.parse_args()
    return set_version(args.set) if args.set else check()


if __name__ == "__main__":
    sys.exit(main())
