#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""bump_suite.py - Bumpea y valida la version PARAGUAS de la suite.

La version paraguas vive en `.claude-plugin/marketplace.json` -> metadata.version
y es la que etiqueta el release (git tag vX.Y.Z). Es DISTINTA de las versiones
por-plugin (esas las maneja scripts/<plugin>_bump_version.py y su cross-check con
el subtree lo hace scripts/check_suite_versions.py). Hasta ahora metadata.version
se bumpeaba a mano, sin script ni check -> release inconsistente probable (F14).

Uso:
  uv run scripts/bump_suite.py --check                # imprime la version paraguas
  uv run scripts/bump_suite.py --set 1.0.4            # escribe metadata.version
  uv run scripts/bump_suite.py --check-tag v1.0.4     # metadata.version == tag?

`--check-tag` acepta 'v1.0.4', '1.0.4' o 'refs/tags/v1.0.4' (lo que da
github.ref_name); lo usa el CI en eventos de tag para frenar un release cuyo tag
no coincide con metadata.version.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import bump_common

REPO_ROOT = Path(__file__).resolve().parent.parent
MARKETPLACE = REPO_ROOT / ".claude-plugin" / "marketplace.json"


def read_version() -> str:
    market = json.loads(MARKETPLACE.read_text(encoding="utf-8"))
    version = market.get("metadata", {}).get("version")
    if not isinstance(version, str):
        print(
            "ERROR - falta metadata.version (string) en marketplace.json",
            file=sys.stderr,
        )
        raise SystemExit(1)
    return version


def check() -> int:
    print(f"OK - metadata.version (paraguas): {read_version()}")
    return 0


def set_version(new_version: str) -> int:
    if not bump_common.SEMVER.match(new_version):
        print(f"ERROR - '{new_version}' no es semver X.Y.Z", file=sys.stderr)
        return 1
    market = json.loads(MARKETPLACE.read_text(encoding="utf-8"))
    metadata = market.setdefault("metadata", {})
    metadata["version"] = new_version
    MARKETPLACE.write_text(
        json.dumps(market, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"OK - metadata.version = {new_version}")
    return 0


def _tag_to_version(ref: str) -> str:
    """Normaliza 'refs/tags/v1.0.4' | 'v1.0.4' | '1.0.4' -> '1.0.4'."""
    tag = ref.rsplit("/", 1)[-1]
    return tag[1:] if tag.startswith("v") else tag


def check_tag(ref: str) -> int:
    tag_version = _tag_to_version(ref)
    version = read_version()
    if version != tag_version:
        print(
            f"ERROR - metadata.version ({version!r}) != tag ({tag_version!r} de {ref!r})",
            file=sys.stderr,
        )
        return 1
    print(f"OK - metadata.version == tag: {version}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check", action="store_true", help="imprimir metadata.version")
    group.add_argument("--set", metavar="X.Y.Z", help="escribir metadata.version")
    group.add_argument(
        "--check-tag", metavar="REF", help="validar metadata.version == tag del release"
    )
    args = parser.parse_args()
    if args.set:
        return set_version(args.set)
    if args.check_tag:
        return check_tag(args.check_tag)
    return check()


if __name__ == "__main__":
    sys.exit(main())
