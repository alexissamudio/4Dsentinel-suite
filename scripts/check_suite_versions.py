#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""check_suite_versions.py - Cross-check de versiones paraguas <-> subtree.

El marketplace paraguas (`.claude-plugin/marketplace.json`) declara una `version`
por cada plugin de la suite; cada subtree tiene ademas su propio `plugin.json` con
otra `version`. Si divergen, el usuario instala una version distinta de la que dice
el catalogo. Este check FALLA (exit != 0) si algun par no coincide.

La ruta del `plugin.json` de cada plugin se deriva de su `source` en el marketplace
(`<source>/.claude-plugin/plugin.json`), asi el check no hardcodea rutas y sigue al
catalogo si se agrega/mueve un plugin.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MARKETPLACE = REPO_ROOT / ".claude-plugin" / "marketplace.json"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    if not MARKETPLACE.is_file():
        print(f"ERROR - no existe {MARKETPLACE}", file=sys.stderr)
        return 1

    market = load_json(MARKETPLACE)
    plugins = market.get("plugins", [])
    if not plugins:
        print("ERROR - el marketplace no declara plugins", file=sys.stderr)
        return 1

    fallas = 0
    for p in plugins:
        name = p.get("name", "<sin-name>")
        umbrella_ver = p.get("version")
        source = p.get("source")
        if umbrella_ver is None:
            print(f"ERROR - {name}: el marketplace no declara 'version'", file=sys.stderr)
            fallas += 1
            continue
        if not source:
            print(f"ERROR - {name}: el marketplace no declara 'source'", file=sys.stderr)
            fallas += 1
            continue

        plugin_json = (REPO_ROOT / source / ".claude-plugin" / "plugin.json").resolve()
        if not plugin_json.is_file():
            print(
                f"ERROR - {name}: no existe el plugin.json de subtree ({plugin_json})",
                file=sys.stderr,
            )
            fallas += 1
            continue

        subtree_ver = load_json(plugin_json).get("version")
        if subtree_ver != umbrella_ver:
            print(
                f"ERROR - {name}: version divergente "
                f"(marketplace={umbrella_ver!r} vs subtree={subtree_ver!r} en {source})",
                file=sys.stderr,
            )
            fallas += 1
        else:
            print(f"OK - {name}: {umbrella_ver} (paraguas == subtree)")

    if fallas:
        print(f"ERROR - {fallas} plugin(s) con version desalineada", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
