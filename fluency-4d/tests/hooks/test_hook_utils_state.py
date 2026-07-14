"""C1 - save_state atomico: escritura via temporal + os.replace, para que un
load_state concurrente nunca vea un JSON a medio escribir (torn-write).

Importa hook_utils directamente (no por subprocess) para inspeccionar la
mecanica de la escritura. El estado se redirige a tmp_path via tempfile.tempdir.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
HOOKS_DIR = REPO_ROOT / "plugins" / "fluency-4d" / "hooks"
sys.path.insert(0, str(HOOKS_DIR))

import hook_utils  # noqa: E402


@pytest.fixture()
def state_dir(tmp_path, monkeypatch):
    """Redirige el estado de fluency4d a tmp_path (aislado por test)."""
    monkeypatch.setattr(hook_utils.tempfile, "tempdir", str(tmp_path))
    return tmp_path / "fluency4d"


def test_save_load_roundtrip(state_dir):
    hook_utils.save_state("k1", {"temas_inyectados": ["auth"], "arranque_inyectado": True})
    got = hook_utils.load_state("k1")
    assert got["temas_inyectados"] == ["auth"]
    assert got["arranque_inyectado"] is True
    assert "_ts" in got  # save_state sella el timestamp


def test_save_state_no_deja_temporales(state_dir):
    hook_utils.save_state("k2", {"temas_inyectados": ["db"]})
    sobrantes = [p.name for p in state_dir.iterdir() if p.suffix == ".tmp"]
    assert sobrantes == []  # el temporal se renombra, no queda basura


def test_save_state_escritura_atomica_via_replace(state_dir, monkeypatch):
    """En el instante del replace, el destino previo sigue siendo JSON valido
    (nunca truncado in-place) y el temporal fuente ya esta completo: eso es la
    garantia anti torn-write."""
    hook_utils.save_state("k3", {"n": 1})  # estado inicial completo
    dst = hook_utils._state_path("k3")

    real_replace = os.replace
    observado = {"n": 0}

    def spy_replace(src, dstp):
        # destino previo: completo y parseable (no truncado a medias)
        json.loads(Path(dstp).read_text(encoding="utf-8"))
        # temporal fuente: contenido nuevo ya escrito por completo
        assert json.loads(Path(src).read_text(encoding="utf-8"))["n"] == 2
        observado["n"] += 1
        return real_replace(src, dstp)

    monkeypatch.setattr(hook_utils.os, "replace", spy_replace)
    hook_utils.save_state("k3", {"n": 2, "relleno": "x" * 5000})

    assert observado["n"] == 1  # paso por os.replace exactamente una vez
    assert hook_utils.load_state("k3")["n"] == 2
    assert dst.read_text(encoding="utf-8")  # destino final no vacio/valido
    json.loads(dst.read_text(encoding="utf-8"))


def test_save_state_error_no_rompe(state_dir, monkeypatch):
    """best-effort: si la escritura falla, save_state degrada a no-op silencioso
    (nunca lanza en el hot path del hook)."""

    def boom(*a, **k):
        raise OSError("disco lleno")

    monkeypatch.setattr(hook_utils.tempfile, "mkstemp", boom)
    hook_utils.save_state("k4", {"x": 1})  # no debe lanzar
