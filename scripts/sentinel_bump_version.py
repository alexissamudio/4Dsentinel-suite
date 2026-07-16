#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""bump_version.py - Sincroniza la version del plugin sentinel-agents.

La version de sentinel-agents vive en DOS lugares (ambos deben coincidir):
  1. .claude-plugin/marketplace.json  -> plugins[name=="sentinel-agents"].version
  2. plugins/sentinel-agents/.claude-plugin/plugin.json -> version

`metadata.version` del marketplace es la version PARAGUAS de la suite (no la de
sentinel-agents), por eso NO entra en este check por-plugin. El cross-check
paraguas<->subtree lo hace scripts/check_suite_versions.py.

Uso:
  uv run scripts/bump_version.py --check
  uv run scripts/bump_version.py --set 0.2.0
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
PLUGIN = REPO_ROOT / "plugins" / "sentinel-agents" / ".claude-plugin" / "plugin.json"
PLUGIN_NAME = "sentinel-agents"
SEMVER = re.compile(r"^\d+\.\d+\.\d+\Z")  # \Z (no $): rechaza un newline final


def _market_entry(m: dict[str, Any]) -> dict[str, Any]:
    """Devuelve la entrada del plugin en marketplace.json por `name` (no por indice)."""
    plugins: list[dict[str, Any]] = m.get("plugins", [])
    for entry in plugins:
        if entry.get("name") == PLUGIN_NAME:
            return entry
    print(
        f"ERROR - no hay entrada name=='{PLUGIN_NAME}' en marketplace.json plugins[]",
        file=sys.stderr,
    )
    raise SystemExit(1)


def read_versions() -> dict[str, str]:
    m = json.loads(MARKETPLACE.read_text(encoding="utf-8"))
    p = json.loads(PLUGIN.read_text(encoding="utf-8"))
    mv, pv = _market_entry(m).get("version"), p.get("version")
    if not isinstance(mv, str) or not isinstance(pv, str):
        print(
            "ERROR - falta la clave 'version' (string) en marketplace o plugin.json",
            file=sys.stderr,
        )
        raise SystemExit(1)
    return {
        f"marketplace.plugins[{PLUGIN_NAME}].version": mv,
        "plugin.json version": pv,
    }


def check() -> int:
    versions = read_versions()
    for lugar, version in versions.items():
        print(f"  {lugar}: {version}")
    if len(set(versions.values())) == 1:
        print(f"OK - version sincronizada: {next(iter(versions.values()))}")
        return 0
    print("ERROR - las versiones NO coinciden", file=sys.stderr)
    return 1


def set_version(new: str) -> int:
    if not SEMVER.match(new):
        print(f"ERROR - '{new}' no es semver X.Y.Z", file=sys.stderr)
        return 1
    m = json.loads(MARKETPLACE.read_text(encoding="utf-8"))
    p = json.loads(PLUGIN.read_text(encoding="utf-8"))
    # NO se toca m["metadata"]["version"] (version paraguas de la suite).
    _market_entry(m)["version"] = new
    p["version"] = new
    MARKETPLACE.write_text(json.dumps(m, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    PLUGIN.write_text(json.dumps(p, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"OK - version {new} escrita en los 2 lugares")
    return check()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--check", action="store_true")
    g.add_argument("--set", metavar="X.Y.Z")
    args = ap.parse_args()
    return set_version(args.set) if args.set else check()


if __name__ == "__main__":
    sys.exit(main())
