#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""fluency_bump_version.py - Sincroniza la version del plugin fluency-4d.

La version de fluency-4d vive en DOS lugares (ambos deben coincidir):
  1. .claude-plugin/marketplace.json  -> plugins[name=="fluency-4d"].version
  2. plugins/fluency-4d/.claude-plugin/plugin.json -> version

La logica vive en scripts/bump_common.py; este archivo solo aporta los paths y
el PLUGIN_NAME. `metadata.version` (paraguas de la suite) NO se toca aca; su
cross-check lo hace scripts/check_suite_versions.py.

Uso:
  uv run scripts/fluency_bump_version.py --check        # verifica que las 2 coincidan
  uv run scripts/fluency_bump_version.py --set 0.2.0    # escribe la nueva version
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import bump_common

REPO_ROOT = Path(__file__).resolve().parent.parent
MARKETPLACE = REPO_ROOT / ".claude-plugin" / "marketplace.json"
PLUGIN = REPO_ROOT / "plugins" / "fluency-4d" / ".claude-plugin" / "plugin.json"
PLUGIN_NAME = "fluency-4d"


def _market_entry(marketplace: dict[str, Any]) -> dict[str, Any]:
    return bump_common.market_entry(marketplace, PLUGIN_NAME)


def read_versions() -> dict[str, str]:
    return bump_common.read_versions(
        marketplace_path=MARKETPLACE, plugin_path=PLUGIN, plugin_name=PLUGIN_NAME
    )


def check() -> int:
    return bump_common.check(
        marketplace_path=MARKETPLACE, plugin_path=PLUGIN, plugin_name=PLUGIN_NAME
    )


def set_version(new_version: str) -> int:
    return bump_common.set_version(
        new_version, marketplace_path=MARKETPLACE, plugin_path=PLUGIN, plugin_name=PLUGIN_NAME
    )


def main() -> int:
    return bump_common.main(
        doc=__doc__, marketplace_path=MARKETPLACE, plugin_path=PLUGIN, plugin_name=PLUGIN_NAME
    )


if __name__ == "__main__":
    sys.exit(main())
