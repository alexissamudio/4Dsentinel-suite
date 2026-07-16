"""Cobertura del helper centralizado scripts/frontmatter_utils.py (F9).

parse_tools es un GUARD DE SEGURIDAD read-only: un agente con Write/Bash NO debe
pasar. Se testean los dos formatos de riesgo (inline y lista YAML a indentacion 0)
mas la rama de quotes (`.strip("'\"")`), que el refactor F9 marco como sensible.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import frontmatter_utils as fu  # noqa: E402


def _doc(front: str) -> str:
    return f"---\n{front}\n---\n\ncuerpo\n"


def test_frontmatter_scalar():
    fm = fu.frontmatter(_doc("name: advisor\ndescription: hace cosas"))
    assert fm == {"name": "advisor", "description": "hace cosas"}


def test_frontmatter_sin_bloque_devuelve_vacio():
    assert fu.frontmatter("no hay frontmatter aca") == {}


def test_frontmatter_tolera_trailing_whitespace():
    # Regex endurecido ^---\s*\n (F5): un `---` con espacios/CR al final igual matchea.
    assert fu.frontmatter("--- \nname: x\n--- \n\ncuerpo") == {"name": "x"}


def test_parse_tools_inline():
    assert fu.parse_tools(_doc("tools: Read, Grep, Glob")) == {"Read", "Grep", "Glob"}


def test_parse_tools_inline_corchetes():
    assert fu.parse_tools(_doc("tools: [Read, Grep]")) == {"Read", "Grep"}


def test_parse_tools_lista_yaml_indentada():
    assert fu.parse_tools(_doc("tools:\n  - Read\n  - Grep")) == {"Read", "Grep"}


def test_parse_tools_lista_yaml_indentacion_cero():
    # F1: una lista a indentacion 0 (`- Write` sin sangria) NO debe quedar vacia;
    # el guard read-only tiene que VER el Write.
    assert fu.parse_tools(_doc("tools:\n- Read\n- Write")) == {"Read", "Write"}


def test_parse_tools_desquota_valores():
    # Rama de quotes marcada como sensible en el review de F9.
    assert fu.parse_tools(_doc("tools: 'Read', \"Bash\"")) == {"Read", "Bash"}
    assert fu.parse_tools(_doc("tools:\n  - 'Write'\n  - \"Edit\"")) == {"Write", "Edit"}


def test_parse_tools_sin_clave_vacio():
    assert fu.parse_tools(_doc("name: x")) == set()


def test_strip_quotes():
    assert fu.strip_quotes("'x'") == "x"
    assert fu.strip_quotes('"x"') == "x"
    assert fu.strip_quotes("x") == "x"
    assert fu.strip_quotes("'x") == "'x"  # sin cierre: no toca
