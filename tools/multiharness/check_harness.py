#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""check_harness.py - Detector de drift + validador de los bundles multiharness.

Dos comprobaciones sobre dist/codex/ y dist/opencode/:

1) DRIFT: regenera cada bundle a un directorio temporal y lo compara byte-a-byte
   contra el commiteado. Falla (exit 1) si difieren -> el bundle commiteado no
   coincide con lo que produce el generador desde la fuente actual.

2) VALIDACION del bundle commiteado (evita falsos-verdes): parsea cada `.json`
   (json.loads) y cada `.toml` (tomllib.load) generado, y verifica que los `.py`
   referenciados por ruta absoluta dentro de los artefactos (commands de
   hooks.json/config.toml y USER_PROMPT_HOOKS del shim fluency-hooks.js) EXISTAN.
   Un cambio futuro con caracteres de control en una `description` produciria
   TOML/JSON invalido; sin este paso, el drift-check por bytes seguiria verde.

Uso: uv run --script tools/multiharness/check_harness.py

ASCII puro (regla de CLAUDE.md).
"""

from __future__ import annotations

import json
import re
import sys
import tempfile
import tomllib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_harness as B  # noqa: E402

# Ruta .py entrecomillada dentro de un string (command de hook o entrada del
# array USER_PROMPT_HOOKS): "...\\algo.py" -> captura la ruta.
PY_QUOTED = re.compile(r'"([^"]*\.py)"')


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


def py_paths_in_obj(obj) -> list[str]:
    """Rutas .py entrecomilladas dentro de cualquier string del arbol parseado.

    Cubre los `command` de hooks.json y de un eventual [hooks] en config.toml.
    Las rutas ya vienen des-escapadas (json.loads / tomllib decodifican \\ -> \\).
    """
    found: list[str] = []
    if isinstance(obj, dict):
        for v in obj.values():
            found += py_paths_in_obj(v)
    elif isinstance(obj, list):
        for v in obj:
            found += py_paths_in_obj(v)
    elif isinstance(obj, str):
        found += PY_QUOTED.findall(obj)
    return found


def validate_bundle(label: str, root: Path) -> bool:
    """Parsea JSON/TOML del bundle y verifica que los .py referenciados existan.

    Devuelve True si hay algun error (parse invalido o hook inexistente).
    """
    err = False
    py_refs: list[tuple[Path, str]] = []

    for f in sorted(root.rglob("*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, ValueError) as e:
            print("PARSE ERROR (json) en dist/%s/ %s : %s"
                  % (label, f.relative_to(root), e))
            err = True
            continue
        for p in py_paths_in_obj(data):
            py_refs.append((f.relative_to(root), p))

    for f in sorted(root.rglob("*.toml")):
        try:
            with f.open("rb") as fh:
                data = tomllib.load(fh)
        except (tomllib.TOMLDecodeError, ValueError) as e:
            print("PARSE ERROR (toml) en dist/%s/ %s : %s"
                  % (label, f.relative_to(root), e))
            err = True
            continue
        for p in py_paths_in_obj(data):
            py_refs.append((f.relative_to(root), p))

    # Shim JS: las entradas de USER_PROMPT_HOOKS son literales JS "C:\\...\\x.py".
    # No es JSON: extraemos las rutas .py entrecomilladas y des-escapamos \\ -> \\.
    for f in sorted(root.rglob("*.js")):
        text = f.read_text(encoding="utf-8")
        for raw in PY_QUOTED.findall(text):
            py_refs.append((f.relative_to(root), raw.replace("\\\\", "\\")))

    for origen, p in py_refs:
        if not Path(p).exists():
            print("REF ROTA en dist/%s/ %s : hook .py referenciado no existe -> %s"
                  % (label, origen, p))
            err = True

    if not err:
        print("OK dist/%s/ : JSON/TOML validos, %d hooks .py referenciados existen"
              % (label, len(py_refs)))
    return err


def main() -> int:
    targets = [
        ("codex", B.DEFAULT_DIST, B.build),
        ("opencode", B.DEFAULT_OPENCODE_DIST, B.build_opencode),
    ]
    drift = False
    invalid = False
    with tempfile.TemporaryDirectory() as td:
        for label, committed, build_fn in targets:
            if not committed.exists():
                print("DRIFT: dist/%s/ no existe; corre build_harness.py primero" % label)
                drift = True
                continue
            fresh = Path(td) / label
            build_fn(fresh)
            drift = compare_bundle(label, committed, fresh) or drift
            invalid = validate_bundle(label, committed) or invalid

    if drift:
        print("RESULTADO: DRIFT detectado (regenera con build_harness.py)")
        return 1
    if invalid:
        print("RESULTADO: bundle INVALIDO (JSON/TOML roto o hook .py inexistente)")
        return 1
    print("RESULTADO: OK, sin drift y bundles validos")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
