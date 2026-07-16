#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""check_ascii.py - Los .py de produccion deben ser ASCII puro.

En Windows el default es cp1252: un .py con caracteres no-ASCII (acentos, flechas,
emojis) en un hook o script del runtime del usuario puede romper al leerse o
ejecutarse. La regla vivia solo en CLAUDE.md (convencion sin enforcement, F15);
aca se vuelve un check de CI que la hace ejecutable.

Alcance: codigo de produccion y tooling (hooks + scripts). Los tests quedan FUERA
a proposito: varios verifican el manejo de entradas no-ASCII (sanitizacion de
UTF-8, acentos, emojis) y por eso contienen esos caracteres de forma intencional.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
# Dirs de produccion/tooling a validar (relativos a REPO_ROOT).
SCAN_DIRS = [
    "scripts",
    "plugins/fluency-4d/hooks",
    "plugins/memory/scripts",
]


def _py_files() -> list[Path]:
    files: list[Path] = []
    for d in SCAN_DIRS:
        base = REPO_ROOT / d
        if not base.is_dir():
            continue
        files.extend(p for p in base.rglob("*.py") if "__pycache__" not in p.parts)
    return sorted(files)


def check_file(path: Path) -> list[str]:
    errs = []
    rel = path.relative_to(REPO_ROOT)
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        for col, ch in enumerate(line, 1):
            if ord(ch) > 0x7F:
                errs.append(f"{rel}:{lineno}:{col}: caracter no-ASCII {ch!r} (U+{ord(ch):04X})")
                break  # un error por linea basta
    return errs


def main() -> int:
    fallas = 0
    for path in _py_files():
        for e in check_file(path):
            fallas += 1
            print(f"ERROR - {e}", file=sys.stderr)
    if fallas:
        print(
            f"ERROR - {fallas} linea(s) con caracteres no-ASCII en .py de produccion",
            file=sys.stderr,
        )
        return 1
    print("OK - todos los .py de produccion son ASCII puro")
    return 0


if __name__ == "__main__":
    sys.exit(main())
