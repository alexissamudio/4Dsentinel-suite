"""Paridad de flags 4D: los hooks aplican exactamente los modos que la status line
muestra. Los casos viven en tests/fluency-4d/fixtures/flags_parity.json, que tambien
lee plugins/fluency-4d/statusline/test/parity.test.js (node --test).

Por cada caso:
- ADHD se considera aplicado si adhd_injector.py (subprocess real) inyecta algo;
  asi entra la regla "ADHD cede ante caveman" (adhd_injector.py, load_caveman).
- caveman, si caveman_injector.py inyecta algo.
- verify, si hook_utils.load_verify() devuelve el flag (lo consume discernment_gate).
El nivel sale de load_adhd()/load_caveman() y se cruza con la directiva inyectada.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
HOOKS_DIR = REPO_ROOT / "plugins" / "fluency-4d" / "hooks"
FIXTURE = REPO_ROOT / "tests" / "fluency-4d" / "fixtures" / "flags_parity.json"
sys.path.insert(0, str(HOOKS_DIR))

import hook_utils  # noqa: E402

CASES = json.loads(FIXTURE.read_text(encoding="utf-8"))["cases"]
PAYLOAD = {"prompt": "hola", "cwd": "x", "session_id": "s1", "permission_mode": "default"}


def _write_flags(home: Path, flags: dict) -> None:
    directory = home / ".claude" / "fluency4d"
    directory.mkdir(parents=True, exist_ok=True)
    for name, data in flags.items():
        text = data if isinstance(data, str) else json.dumps(data)
        (directory / f"{name}.json").write_text(text, encoding="utf-8")


def _label(name: str, level: str) -> str:
    return name if level == "auto" else f"{name}:{level}"


def test_fixture_tiene_casos_clave():
    names = {c["name"] for c in CASES}
    assert len(CASES) >= 15
    assert "ambos activos: ADHD cede ante caveman" in names
    assert any("verify" in c["flags"] for c in CASES)


@pytest.mark.parametrize("case", CASES, ids=[c["name"] for c in CASES])
def test_hooks_coinciden_con_fixture(case, run_hook, tmp_path, monkeypatch):
    home = tmp_path / "home"  # el mismo home que aisla run_hook
    _write_flags(home, case["flags"])
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))

    shown: list[str] = []

    adhd_out = run_hook("adhd_injector.py", PAYLOAD)
    if adhd_out:
        level = hook_utils.load_adhd()["level"]
        assert f"Nivel {level.upper()}" in adhd_out
        shown.append(_label("ADHD", level))

    caveman_out = run_hook("caveman_injector.py", PAYLOAD)
    if caveman_out:
        level = hook_utils.load_caveman()["level"]
        assert f"Nivel {level.upper()}" in caveman_out
        shown.append(_label("caveman", level))

    if hook_utils.load_verify():
        shown.append("verify")

    assert shown == case["expected"]


@pytest.mark.parametrize(
    ("loader", "name", "level"),
    [
        ("load_adhd", "adhd.json", "full"),
        ("load_caveman", "caveman.json", "lite"),
    ],
)
def test_flag_con_utf8_invalido_se_lee_como_node(loader, name, level, tmp_path, monkeypatch):
    # Un byte 0xff no rompe el loader: decodifica con perdida como Node,
    # asi la barra y el hook siguen coincidiendo (hallazgo adversarial).
    home = tmp_path / "home"
    flags = home / ".claude" / "fluency4d"
    flags.mkdir(parents=True)
    raw = b'{"on":true,"level":"' + level.encode() + b'","n":"\xff"}'
    (flags / name).write_bytes(raw)
    monkeypatch.setattr(Path, "home", lambda: home)
    assert getattr(hook_utils, loader)().get("level") == level
