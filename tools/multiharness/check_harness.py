#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml"]
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


# Guardas OpenCode: fallan si vuelven los defectos del port verificados en
# runtime real (contexto visible como texto del usuario, stdin cp1252, estado
# fugado entre sesiones, nombres/rutas de Claude Code, commands-wrapper).
OC_FORBIDDEN = ("sentinel-agents:", "${CLAUDE_PLUGIN_ROOT}")
OC_PUSH_SYNTHETIC = re.compile(r"output\.parts\.push\(\{[^}]*\bsynthetic:\s*true\b", re.S)
OC_SHIM_REQUIRED = (
    ("session_id:", "el payload no pasa session_id (el estado se keyea por cwd)"),
    ('PYTHONUTF8: "1"', "spawnSync sin PYTHONUTF8=1 (stdin cp1252 en Windows)"),
    ("hook_event_name:", "el payload no pasa hook_event_name"),
    ("permission_mode:", "el payload no pasa permission_mode (plan_calibrator)"),
    ("isSubagent(input)", "no se saltea la inyeccion en subagentes"),
)
OC_SKILL_REF = re.compile(r"SKILL\.md")


def validate_opencode(root: Path) -> bool:
    """Guardas especificas del bundle OpenCode. Devuelve True si hay error."""
    err = False

    def fail(msg: str) -> None:
        nonlocal err
        print("OPENCODE: " + msg)
        err = True

    shim = root / "plugin" / "fluency-hooks.js"
    text = shim.read_text(encoding="utf-8") if shim.is_file() else ""
    if not text:
        fail("falta plugin/fluency-hooks.js")
    else:
        if not OC_PUSH_SYNTHETIC.search(text):
            fail("la parte inyectada en output.parts no lleva synthetic: true")
        for needle, why in OC_SHIM_REQUIRED:
            if needle not in text:
                fail("shim: " + why)

    kb = root / "references" / "iso-27000"
    for f in sorted(root.rglob("*")):
        if not f.is_file() or kb in f.parents:
            continue  # la KB ISO es copia byte-a-byte (manifest), no se traduce
        rel = f.relative_to(root).as_posix()
        body = f.read_text(encoding="utf-8")
        for bad in OC_FORBIDDEN:
            if bad in body:
                fail("%s contiene %r (no traducido a OpenCode)" % (rel, bad))
        if rel.startswith("command/"):
            if OC_SKILL_REF.search(body):
                fail("%s referencia un SKILL.md en vez de incrustarlo" % rel)
            if "$ARGUMENTS" not in body:
                fail("%s no recibe $ARGUMENTS" % rel)
        if rel.startswith("agent/") and "external_directory:" not in body:
            fail("%s sin permiso external_directory para references/" % rel)

    for skipped in B.M.OPENCODE_SKILLS_SKIPPED:
        if (root / "command" / (skipped + ".md")).exists():
            fail("command/%s.md no deberia emitirse (OPENCODE_SKILLS_SKIPPED)" % skipped)

    if not err:
        print("OK dist/opencode/ : guardas OpenCode (synthetic, session_id, "
              "PYTHONUTF8, subagentes, sin nombres/rutas de Claude, commands "
              "autocontenidos)")
    return err


DEFAULT_HERMES_DIST = B.REPO_ROOT / "dist" / "hermes"


def validate_hermes(root: Path) -> bool:
    """Valida el bundle hermes: SKILL.md con frontmatter valido y references existentes.

    Devuelve True si hay algun error.
    """
    try:
        import yaml as _yaml_lib  # declarado en la cabecera PEP 723
    except ImportError:
        print("ERROR: falta pyyaml para validar dist/hermes/ (corre con "
              "`uv run --script` o `--with pyyaml`)")
        return True
    err = False
    skills_dir = root / "skills"
    if not skills_dir.is_dir():
        print("ERROR dist/hermes/ : no existe skills/")
        return True

    skill_count = 0
    for skill_dir in sorted(skills_dir.iterdir()):
        if not skill_dir.is_dir():
            continue
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            print("ERROR dist/hermes/ : falta SKILL.md en %s" % skill_dir.name)
            err = True
            continue
        skill_count += 1
        # Validar frontmatter
        try:
            text = skill_md.read_text(encoding="utf-8")
            if not text.startswith("---"):
                print("ERROR dist/hermes/skills/%s : frontmatter no empieza con ---" % skill_dir.name)
                err = True
                continue
            end = text.find("\n---", 3)
            if end == -1:
                print("ERROR dist/hermes/skills/%s : frontmatter sin cierre ---" % skill_dir.name)
                err = True
                continue
            fm = _yaml_lib.safe_load(text[3:end])
            if not fm or "name" not in fm:
                print("ERROR dist/hermes/skills/%s : frontmatter sin 'name'" % skill_dir.name)
                err = True
                continue
            if "description" not in fm:
                print("ERROR dist/hermes/skills/%s : frontmatter sin 'description'" % skill_dir.name)
                err = True
        except Exception as e:
            print("ERROR dist/hermes/skills/%s : YAML invalido (%s)" % (skill_dir.name, e))
            err = True

    if not err:
        print("OK dist/hermes/ : %d skills con frontmatter valido" % skill_count)
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
            if label == "opencode":
                invalid = validate_opencode(committed) or invalid

    # Validar hermes (skills, no drift — los skills no se generan, se copian)
    if DEFAULT_HERMES_DIST.exists():
        invalid = validate_hermes(DEFAULT_HERMES_DIST) or invalid
    else:
        print("INFO: dist/hermes/ no existe; ejecuta build_harness.py primero")

    if drift:
        print("RESULTADO: DRIFT detectado (regenera con build_harness.py)")
        return 1
    if invalid:
        print("RESULTADO: bundle INVALIDO (JSON/TOML roto, hook .py inexistente o guarda OpenCode)")
        return 1
    print("RESULTADO: OK, sin drift y bundles validos")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
