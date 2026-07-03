#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""bump_version.py - Sincroniza la versión del plugin en los 3 lugares obligatorios.

Lugares (los tres DEBEN coincidir para que la instalación funcione):
  1. .claude-plugin/marketplace.json  -> metadata.version
  2. .claude-plugin/marketplace.json  -> plugins[0].version
  3. plugins/fluency-4d/.claude-plugin/plugin.json -> version

Uso:
  uv run scripts/bump_version.py --check        # verifica que las 3 coincidan
  uv run scripts/bump_version.py --set 0.2.0    # escribe la nueva versión en las 3
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MARKETPLACE = REPO_ROOT / ".claude-plugin" / "marketplace.json"
PLUGIN = REPO_ROOT / "plugins" / "fluency-4d" / ".claude-plugin" / "plugin.json"

SEMVER = re.compile(r"^\d+\.\d+\.\d+$")


def read_versions() -> dict[str, str]:
    marketplace = json.loads(MARKETPLACE.read_text(encoding="utf-8"))
    plugin = json.loads(PLUGIN.read_text(encoding="utf-8"))
    return {
        "marketplace.metadata.version": marketplace["metadata"]["version"],
        "marketplace.plugins[0].version": marketplace["plugins"][0]["version"],
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
    marketplace["metadata"]["version"] = new_version
    marketplace["plugins"][0]["version"] = new_version
    plugin["version"] = new_version
    MARKETPLACE.write_text(
        json.dumps(marketplace, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    PLUGIN.write_text(
        json.dumps(plugin, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"OK - version {new_version} escrita en los 3 lugares")
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
