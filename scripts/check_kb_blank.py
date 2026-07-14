#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""check_kb_blank.py - Guarda anti-write-back de la base ISO (por checksum).

La KB (references/iso-27000/) viaja EN BLANCO con el plugin. Esta guarda impide
que resultados de una auditoría (evidencia real, estados, IPs, nombres de la
organización) se commiteen de vuelta al repo público. Compara cada archivo contra
los hashes prístinos de .manifest.sha256; FALLA si algo difiere o falta.

Editar la plantilla a propósito => regenerar el manifest conscientemente:
  uv run scripts/check_kb_blank.py --update
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
KB_DIR = REPO_ROOT / "plugins" / "sentinel-agents" / "references" / "iso-27000"
MANIFEST = KB_DIR / ".manifest.sha256"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def kb_files() -> list[Path]:
    return sorted(p for p in KB_DIR.rglob("*") if p.is_file() and p.name != ".manifest.sha256")


def build_manifest() -> str:
    lines = []
    for p in kb_files():
        rel = p.relative_to(KB_DIR).as_posix()
        lines.append(f"{sha256(p)}  {rel}")
    return "\n".join(lines) + "\n"


def update() -> int:
    MANIFEST.write_text(build_manifest(), encoding="utf-8")
    print(f"OK - manifest actualizado con {len(kb_files())} archivos")
    return 0


def check() -> int:
    if not MANIFEST.is_file():
        print("ERROR - falta .manifest.sha256; corré --update", file=sys.stderr)
        return 1
    expected = {}
    for line in MANIFEST.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        h, rel = line.split("  ", 1)
        expected[rel] = h
    actual = {p.relative_to(KB_DIR).as_posix(): sha256(p) for p in kb_files()}

    problemas = []
    for rel, h in expected.items():
        if rel not in actual:
            problemas.append(f"FALTA: {rel}")
        elif actual[rel] != h:
            problemas.append(f"MODIFICADO (posible write-back de auditoría): {rel}")
    for rel in actual:
        if rel not in expected:
            problemas.append(f"NUEVO (no en el manifest): {rel}")

    if problemas:
        print("ERROR - la KB no coincide con el manifest prístino:", file=sys.stderr)
        for p in problemas:
            print(f"  - {p}", file=sys.stderr)
        print("Si el cambio es intencional en la PLANTILLA, corré --update.", file=sys.stderr)
        return 1
    print(f"OK - KB en blanco: {len(actual)} archivos coinciden con el manifest")
    return 0


def main() -> int:
    if "--update" in sys.argv:
        return update()
    return check()


if __name__ == "__main__":
    sys.exit(main())
