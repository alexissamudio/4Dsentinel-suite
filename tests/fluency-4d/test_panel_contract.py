"""Contrato del panel 4D (plugins/fluency-4d/hooks/register.tsx) que el kit de
tests del engine no puede verificar solo.

- Paridad: los casos FLAG_CASES de plugins/fluency-4d/tests/panel.test.tsx son
  copia del fixture compartido tests/fluency-4d/fixtures/flags_parity.json (el fs
  de esos tests es falso y no puede leerlo). Cada caso del fixture con adhd o
  caveman y sin verify tiene que estar en el panel con el mismo nombre, el mismo
  contenido de archivos y el valor de fila que corresponde a lo que muestra la barra.
- Gates: `claude plugin validate --json` no lista ningun gating hook sin `.catch`
  (se saltea si el CLI `claude` no esta en el PATH).
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
PLUGIN = REPO_ROOT / "plugins" / "fluency-4d"
PANEL_TEST = PLUGIN / "tests" / "panel.test.tsx"
FIXTURE = REPO_ROOT / "tests" / "fluency-4d" / "fixtures" / "flags_parity.json"

_TOKEN = re.compile(r"'((?:[^'\\]|\\.)*)'|\b([A-Za-z_]\w*)\s*:")


def _ts_literal_to_json(text: str) -> object:
    """Convierte un literal TS simple (strings con comillas simples, claves sin
    comillas, comas finales) a JSON."""

    def sub(m: re.Match[str]) -> str:
        if m.group(1) is not None:
            raw = re.sub(r"\\(.)", r"\1", m.group(1))
            return json.dumps(raw)
        return json.dumps(m.group(2)) + ":"

    converted = _TOKEN.sub(sub, text)
    converted = re.sub(r",(\s*[}\]])", r"\1", converted)
    return json.loads(converted)


def _panel_cases() -> list[dict]:
    src = PANEL_TEST.read_text(encoding="utf-8")
    start = src.index("const FLAG_CASES")
    body_start = src.index("}[] = [", start) + len("}[] = ")
    body_end = src.index("\n]\n", body_start) + 2
    cases = _ts_literal_to_json(src[body_start:body_end])
    assert isinstance(cases, list)
    return cases


def _level(expected: list[str], label: str) -> str:
    for mode in expected:
        if mode == label:
            return "auto"
        if mode.startswith(label + ":"):
            return mode.split(":", 1)[1]
    return "off"


def _applicable() -> list[dict]:
    cases = json.loads(FIXTURE.read_text(encoding="utf-8"))["cases"]
    return [
        c
        for c in cases
        if "verify" not in c["flags"] and ("adhd" in c["flags"] or "caveman" in c["flags"])
    ]


def test_panel_flag_cases_cubren_el_fixture() -> None:
    panel = {c["name"]: c for c in _panel_cases()}
    fixture = _applicable()
    assert fixture, "el fixture no tiene casos de adhd/caveman"
    missing = [c["name"] for c in fixture if c["name"] not in panel]
    assert missing == [], f"casos del fixture sin cubrir en panel.test.tsx: {missing}"
    extra = sorted(set(panel) - {c["name"] for c in fixture})
    assert extra == [], f"casos del panel que no estan en el fixture: {extra}"


@pytest.mark.parametrize("case", _applicable(), ids=lambda c: c["name"])
def test_panel_flag_case_coincide_con_el_fixture(case: dict) -> None:
    panel = {c["name"]: c for c in _panel_cases()}
    got = panel.get(case["name"])
    assert got is not None
    for flag in ("adhd", "caveman"):
        want = case["flags"].get(flag)
        if want is None:
            assert flag not in got, f"{flag}: el fixture no tiene archivo"
        elif isinstance(want, str):
            assert got.get(flag) == want
        else:
            assert json.loads(got[flag]) == want
    assert got["expected"] == {
        "adhd": _level(case["expected"], "ADHD"),
        "caveman": _level(case["expected"], "caveman"),
    }


def test_ts_literal_parser() -> None:
    assert _ts_literal_to_json("[{ name: 'a: b', adhd: '{\"on\":true}', }, ]") == [
        {"name": "a: b", "adhd": '{"on":true}'}
    ]


@pytest.mark.skipif(shutil.which("claude") is None, reason="sin el CLI claude")
def test_gating_hooks_tienen_catch() -> None:
    exe = shutil.which("claude")
    assert exe is not None
    proc = subprocess.run(
        [exe, "plugin", "validate", str(PLUGIN), "--json"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
        check=False,
    )
    report = json.loads(proc.stdout)
    gates: list[dict] = []

    def walk(node: object) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if key == "gatingHooks" and isinstance(value, list):
                    gates.extend(value)
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(report)
    assert any(g.get("pattern") == "ui.close" for g in gates)
    without = [g["hook"] for g in gates if not g.get("hasCatch")]
    assert without == [], f"gating hooks sin .catch: {without}"
