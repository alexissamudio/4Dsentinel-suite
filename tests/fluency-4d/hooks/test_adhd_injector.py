"""Modo ADHD/TDAH: el hook reinyecta la directiva del nivel en cada turno cuando
esta ON, y hace pass-through en OFF / ausente / subagente / JSON corrupto. Si
caveman tambien esta ON, caveman tiene precedencia (mutex de facto).

El estado vive en ~/.claude/fluency4d/adhd.json; el conftest aisla HOME/
USERPROFILE en tmp_path/home, asi que escribimos el flag ahi."""

from __future__ import annotations

import json

import pytest

HOOK = "adhd_injector.py"
LEVELS = ("auto", "lite", "full")


def p(prompt="hola"):
    return {"prompt": prompt, "cwd": "x", "session_id": "s1", "permission_mode": "default"}


def write_adhd(tmp_path, data) -> None:
    directory = tmp_path / "home" / ".claude" / "fluency4d"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "adhd.json"
    path.write_text(data if isinstance(data, str) else json.dumps(data), encoding="utf-8")


def write_caveman(tmp_path, data) -> None:
    directory = tmp_path / "home" / ".claude" / "fluency4d"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "caveman.json"
    path.write_text(data if isinstance(data, str) else json.dumps(data), encoding="utf-8")


@pytest.mark.parametrize("level", LEVELS)
def test_on_inyecta_directiva(run_hook, tmp_path, level):
    write_adhd(tmp_path, {"on": True, "level": level})
    out = run_hook(HOOK, p())
    assert out != ""
    payload = json.loads(out)
    ctx = payload["hookSpecificOutput"]["additionalContext"]
    assert "Modo TDAH/ADHD (fluency-4d)" in ctx


def test_archivo_ausente_passthrough(run_hook):
    assert run_hook(HOOK, p()) == ""


def test_off_passthrough(run_hook, tmp_path):
    write_adhd(tmp_path, {"on": False, "level": "auto"})
    assert run_hook(HOOK, p()) == ""


def test_level_invalido_passthrough(run_hook, tmp_path):
    write_adhd(tmp_path, {"on": True, "level": "wenyan"})
    assert run_hook(HOOK, p()) == ""


def test_subagente_passthrough(run_hook, tmp_path):
    write_adhd(tmp_path, {"on": True, "level": "full"})
    data = p()
    data["agent_type"] = "Explore"
    assert run_hook(HOOK, data) == ""


def test_json_corrupto_passthrough(run_hook, tmp_path):
    write_adhd(tmp_path, "{esto no es json valido")
    assert run_hook(HOOK, p()) == ""


def test_caveman_tiene_precedencia(run_hook, tmp_path):
    write_caveman(tmp_path, {"on": True, "level": "auto"})
    write_adhd(tmp_path, {"on": True, "level": "full"})
    assert run_hook(HOOK, p()) == ""
