#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""check_manifests.py - Valida todos los manifests JSON del monorepo en un solo lugar.

DRY del CI (F12 de la auditoria): antes cada job de validate.yml repetia el
`python -m json.tool` de sus manifests y el grep anti-`../`. Esta guarda los valida
todos de una vez:
- Todo manifest JSON parsea: marketplace paraguas, cada `plugin.json`, y `hooks.json`.
- Ningun `plugin.json` contiene `../` (guarda de path-traversal, F1/F6).

Descubre los manifests por glob, asi sumar un plugin no exige tocar el CI.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def plugin_manifests() -> list[Path]:
    return sorted(REPO_ROOT.glob("plugins/*/.claude-plugin/plugin.json"))


def json_manifests() -> list[Path]:
    paths = [REPO_ROOT / ".claude-plugin" / "marketplace.json"]
    paths += plugin_manifests()
    hooks = REPO_ROOT / "plugins" / "fluency-4d" / "hooks" / "hooks.json"
    if hooks.is_file():
        paths.append(hooks)
    return paths


def check() -> int:
    problemas = []
    for p in json_manifests():
        rel = p.relative_to(REPO_ROOT).as_posix()
        if not p.is_file():
            problemas.append(f"FALTA: {rel}")
            continue
        try:
            json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            problemas.append(f"JSON invalido en {rel}: {e}")
    # Guarda anti path-traversal: ningun plugin.json debe referenciar `../`.
    for p in plugin_manifests():
        rel = p.relative_to(REPO_ROOT).as_posix()
        if "../" in p.read_text(encoding="utf-8"):
            problemas.append(f"ruta ../ en {rel} (path-traversal)")

    if problemas:
        print("ERROR - manifests invalidos:", file=sys.stderr)
        for pb in problemas:
            print(f"  - {pb}", file=sys.stderr)
        return 1
    print(f"OK - {len(json_manifests())} manifests JSON validos, sin rutas ../")
    return 0


def main() -> int:
    return check()


if __name__ == "__main__":
    sys.exit(main())
