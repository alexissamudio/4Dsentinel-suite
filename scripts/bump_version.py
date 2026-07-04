#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""bump_version.py - Sincroniza la versión del plugin en los 3 lugares.

  1. .claude-plugin/marketplace.json  -> metadata.version
  2. .claude-plugin/marketplace.json  -> plugins[0].version
  3. plugins/sentinel-agents/.claude-plugin/plugin.json -> version

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

REPO_ROOT = Path(__file__).resolve().parent.parent
MARKETPLACE = REPO_ROOT / ".claude-plugin" / "marketplace.json"
PLUGIN = REPO_ROOT / "plugins" / "sentinel-agents" / ".claude-plugin" / "plugin.json"
SEMVER = re.compile(r"^\d+\.\d+\.\d+$")


def read_versions() -> dict[str, str]:
    m = json.loads(MARKETPLACE.read_text(encoding="utf-8"))
    p = json.loads(PLUGIN.read_text(encoding="utf-8"))
    return {
        "marketplace.metadata.version": m["metadata"]["version"],
        "marketplace.plugins[0].version": m["plugins"][0]["version"],
        "plugin.json version": p["version"],
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
    m["metadata"]["version"] = new
    m["plugins"][0]["version"] = new
    p["version"] = new
    MARKETPLACE.write_text(json.dumps(m, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    PLUGIN.write_text(json.dumps(p, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"OK - version {new} escrita en los 3 lugares")
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
