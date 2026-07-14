#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""check_skills.py - Validador deterministico del contrato de skills de fluency-4d.

Contrato documentado en .claude/docs/skills.md (seccion "Contrato"). Este script
es la Diligencia aplicada al propio plugin: valida, sin dependencias externas, que
cada skill cumpla las reglas UNIVERSALES y que el registro doble este intacto.

Checks (todos deben pasar; cualquier fallo -> sys.exit(1)):
  1. Universales por skill:
     (a) frontmatter con `name` presente e igual al nombre del directorio.
     (b) `description` presente y con la subcadena "Triggers on:".
     (c) un H1 (linea `# ...`) presente en el cuerpo.
  2. Registro DOBLE: toda skill en skills/ listada en AMBOS plugin.json (skills[])
     y marketplace.json (plugins[0].skills[]) -- y sin huerfanos en ninguno.
  3. Refs no huerfanas: toda `references/<x>.md` citada en un SKILL.md debe existir.
  4. Auto-contencion: ningun path de maquina (C:\\Users\\, /home/, /Users/) en los
     .md/.py del plugin.

Uso:
  uv run scripts/check_skills.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PLUGIN_DIR = REPO_ROOT / "plugins" / "fluency-4d"
SKILLS_DIR = PLUGIN_DIR / "skills"
PLUGIN_JSON = PLUGIN_DIR / ".claude-plugin" / "plugin.json"
MARKETPLACE_JSON = REPO_ROOT / ".claude-plugin" / "marketplace.json"

FRONTMATTER = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
NAME_KEY = re.compile(r"^name:\s*(.+?)\s*$", re.MULTILINE)
DESC_KEY = re.compile(r"^description:\s*(.+?)\s*$", re.MULTILINE)
H1 = re.compile(r"^#\s+\S", re.MULTILINE)
REF = re.compile(r"references/([A-Za-z0-9._/-]+\.md)")
# Paths de maquina: home de Windows (cualquier unidad), de Linux y de macOS.
MACHINE_PATH = re.compile(r"[A-Za-z]:\\Users\\|/home/[A-Za-z0-9._-]+|/Users/[A-Za-z0-9._-]+")


def _strip_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        return value[1:-1]
    return value


def _skill_dirs() -> list[Path]:
    return sorted(p for p in SKILLS_DIR.iterdir() if p.is_dir() and (p / "SKILL.md").is_file())


def check_universales(errors: list[str]) -> None:
    print("[1] Reglas universales por skill")
    for skill_dir in _skill_dirs():
        name = skill_dir.name
        text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
        fm_match = FRONTMATTER.match(text)
        if not fm_match:
            errors.append(f"{name}: SKILL.md sin frontmatter YAML (--- ... ---)")
            print(f"  FAIL {name}: sin frontmatter")
            continue
        frontmatter = fm_match.group(1)
        body = text[fm_match.end():]
        problems = []

        name_match = NAME_KEY.search(frontmatter)
        if not name_match:
            problems.append("falta `name` en frontmatter")
        elif _strip_quotes(name_match.group(1)) != name:
            got = _strip_quotes(name_match.group(1))
            problems.append(f"`name: {got}` != nombre del directorio `{name}`")

        desc_match = DESC_KEY.search(frontmatter)
        if not desc_match:
            problems.append("falta `description` en frontmatter")
        elif "Triggers on:" not in _strip_quotes(desc_match.group(1)):
            problems.append("`description` sin la subcadena 'Triggers on:'")

        if not H1.search(body):
            problems.append("sin titulo H1 (linea `# ...`) en el cuerpo")

        if problems:
            for prob in problems:
                errors.append(f"{name}: {prob}")
                print(f"  FAIL {name}: {prob}")
        else:
            print(f"  OK   {name}")


def _registered(path: Path) -> set[str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    entries = data["skills"] if "skills" in data else data["plugins"][0]["skills"]
    return {Path(entry).name for entry in entries}


def check_registro_doble(errors: list[str]) -> None:
    print("[2] Registro doble (plugin.json + marketplace.json)")
    on_disk = {p.name for p in _skill_dirs()}
    in_plugin = _registered(PLUGIN_JSON)
    in_market = _registered(MARKETPLACE_JSON)

    for skill in sorted(on_disk):
        faltan = []
        if skill not in in_plugin:
            faltan.append("plugin.json")
        if skill not in in_market:
            faltan.append("marketplace.json")
        if faltan:
            errors.append(f"{skill}: en disco pero no listada en {', '.join(faltan)}")
            print(f"  FAIL {skill}: falta en {', '.join(faltan)}")
        else:
            print(f"  OK   {skill}: en disco + plugin.json + marketplace.json")

    for skill in sorted(in_plugin - on_disk):
        errors.append(f"{skill}: listada en plugin.json pero sin directorio en skills/")
        print(f"  FAIL {skill}: huerfana en plugin.json (sin directorio)")
    for skill in sorted(in_market - on_disk):
        errors.append(f"{skill}: listada en marketplace.json pero sin directorio en skills/")
        print(f"  FAIL {skill}: huerfana en marketplace.json (sin directorio)")


def check_refs(errors: list[str]) -> None:
    print("[3] Referencias no huerfanas")
    any_ref = False
    for skill_dir in _skill_dirs():
        text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
        for rel in sorted(set(REF.findall(text))):
            any_ref = True
            target = skill_dir / "references" / rel
            if target.is_file():
                print(f"  OK   {skill_dir.name} -> references/{rel}")
            else:
                errors.append(f"{skill_dir.name}: referencia inexistente references/{rel}")
                print(f"  FAIL {skill_dir.name} -> references/{rel} (no existe)")
    if not any_ref:
        print("  (ninguna referencia citada)")


def check_autocontencion(errors: list[str]) -> None:
    print("[4] Auto-contencion (sin paths de maquina en el plugin)")
    hits = 0
    for path in sorted(PLUGIN_DIR.rglob("*")):
        if path.suffix not in (".md", ".py") or not path.is_file():
            continue
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if MACHINE_PATH.search(line):
                hits += 1
                rel = path.relative_to(REPO_ROOT).as_posix()
                errors.append(f"{rel}:{lineno}: path de maquina en archivo del plugin")
                print(f"  FAIL {rel}:{lineno}")
    if hits == 0:
        print("  OK   sin paths de maquina en .md/.py del plugin")


def main() -> int:
    errors: list[str] = []
    check_universales(errors)
    check_registro_doble(errors)
    check_refs(errors)
    check_autocontencion(errors)
    print()
    if errors:
        print(f"ERROR - {len(errors)} problema(s) en el contrato de skills:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1
    print("OK - las skills cumplen el contrato de fluency-4d")
    return 0


if __name__ == "__main__":
    sys.exit(main())
