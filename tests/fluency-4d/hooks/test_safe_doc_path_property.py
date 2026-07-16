"""Property-based (Hypothesis) sobre safe_doc_path -- la guarda de path de los puentes.

Complementa (NO reemplaza) los tests por-ejemplo de test_bridge_security.py: aquellos
ejercitan el hook entero por subprocess con 3 paths concretos; estos generan cientos de
inputs contra la FUNCION pura, buscando el path hostil que nadie penso.

Requisito (spec, no caracterizacion): safe_doc_path acepta SOLO rutas relativas dentro
del proyecto y rechaza (-> None) absolutas / home / unidad Windows / traversal / con
controles. Propiedades verificadas:
  P1  nunca lanza: para cualquier str devuelve str o None.
  P2  salida siempre segura y ESTABLE: si acepta, la salida no es absoluta/home/unidad,
      no tiene componente '..' ni controles, y re-alimentarla da el mismo valor
      (idempotencia -- el sanitizado es un punto fijo seguro).
  P3  rechazo garantizado: cualquier input con componente '..', prefijo '/'/'~', o
      unidad Windows es rechazado.

Semilla pineada (derandomize=True) para reproducibilidad en CI.
"""

from __future__ import annotations

import re
import sys
import unicodedata
from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st

HOOKS_DIR = Path(__file__).resolve().parents[3] / "plugins" / "fluency-4d" / "hooks"
sys.path.insert(0, str(HOOKS_DIR))

import hook_utils as hu  # noqa: E402

# Segmentos "benignos": letras/numeros ASCII, sin separadores ni '..'.
_safe_seg = st.text(
    alphabet=st.characters(min_codepoint=48, max_codepoint=122, categories=("L", "N")),
    min_size=1,
    max_size=8,
)


@settings(derandomize=True, max_examples=300)
@given(st.text())
def test_p1_nunca_lanza(s):
    r = hu.safe_doc_path(s)
    assert r is None or isinstance(r, str)


@settings(derandomize=True, max_examples=500)
@given(st.text())
def test_p2_salida_siempre_segura_y_estable(s):
    r = hu.safe_doc_path(s)
    if r is None:
        return
    assert not r.startswith("/") and not r.startswith("~")
    assert re.match(r"^[A-Za-z]:", r) is None
    assert ".." not in r.split("/")
    assert all(unicodedata.category(ch)[0] != "C" for ch in r)
    # idempotencia: la salida segura es un punto fijo (re-alimentarla no cambia ni rechaza)
    assert hu.safe_doc_path(r) == r


@settings(derandomize=True, max_examples=300)
@given(st.lists(_safe_seg, min_size=0, max_size=4), st.integers(min_value=0, max_value=4))
def test_p3_traversal_siempre_rechazado(parts, pos):
    parts = list(parts)
    parts.insert(min(pos, len(parts)), "..")
    assert hu.safe_doc_path("/".join(parts)) is None
    assert hu.safe_doc_path("\\".join(parts)) is None  # separador Windows tambien


@settings(derandomize=True, max_examples=200)
@given(st.sampled_from(["/", "~", "~usuario"]), _safe_seg)
def test_p3_absoluto_o_home_rechazado(prefix, seg):
    assert hu.safe_doc_path(prefix + seg) is None


@settings(derandomize=True, max_examples=200)
@given(st.characters(min_codepoint=65, max_codepoint=90), _safe_seg)
def test_p3_unidad_windows_rechazada(letter, seg):
    assert hu.safe_doc_path(f"{letter}:/{seg}") is None
    assert hu.safe_doc_path(f"{letter}:\\{seg}") is None
