#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""check_harness.py - Detector de drift de los bundles multiharness.

Regenera cada bundle (dist/codex/ y dist/opencode/) a un directorio temporal y
lo compara byte-a-byte contra el commiteado. Falla (exit 1) si hay drift -> el
bundle commiteado no coincide con lo que produce el generador desde la fuente
actual.

Uso: uv run --script tools/multiharness/check_harness.py

ASCII puro (regla de CLAUDE.md).
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_harness as B  # noqa: E402


def rel_files(root: Path) -> set[Path]:
    return {p.relative_to(root) for p in root.rglob("*") if p.is_file()}


def compare_bundle(label: str, committed: Path, fresh: Path) -> bool:
    """Compara fresh vs committed byte-a-byte. Devuelve True si hay drift."""
    fresh_set = rel_files(fresh)
    comm_set = rel_files(committed)
    drift = False
    for p in sorted(fresh_set - comm_set):
        print("DRIFT: falta en dist/%s/ : %s" % (label, p))
        drift = True
    for p in sorted(comm_set - fresh_set):
        print("DRIFT: sobra en dist/%s/ : %s" % (label, p))
        drift = True
    for p in sorted(fresh_set & comm_set):
        if (fresh / p).read_bytes() != (committed / p).read_bytes():
            print("DRIFT: contenido difiere en dist/%s/ : %s" % (label, p))
            drift = True
    if not drift:
        print("OK dist/%s/ : sin drift (%d archivos)" % (label, len(comm_set)))
    return drift


def main() -> int:
    targets = [
        ("codex", B.DEFAULT_DIST, B.build),
        ("opencode", B.DEFAULT_OPENCODE_DIST, B.build_opencode),
    ]
    drift = False
    with tempfile.TemporaryDirectory() as td:
        for label, committed, build_fn in targets:
            if not committed.exists():
                print("DRIFT: dist/%s/ no existe; corre build_harness.py primero" % label)
                drift = True
                continue
            fresh = Path(td) / label
            build_fn(fresh)
            drift = compare_bundle(label, committed, fresh) or drift

    if drift:
        print("RESULTADO: DRIFT detectado (regenera con build_harness.py)")
        return 1
    print("RESULTADO: OK, sin drift en todos los bundles")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
