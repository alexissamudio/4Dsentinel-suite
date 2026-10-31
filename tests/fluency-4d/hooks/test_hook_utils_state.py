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

REPO_ROOT = Path(__file__).resolve().parents[3]
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


# --- MINOR 4 (CWE-377): dir de estado endurecido en POSIX ---------------------


@pytest.mark.skipif(os.name != "posix", reason="permisos POSIX no aplican en Windows")
def test_state_dir_permisos_restringidos(state_dir):
    """El subdir fluency4d se crea 0o700 (no world/group-accesible) en /tmp."""
    hook_utils._state_path("kperm")
    mode = state_dir.stat().st_mode & 0o777
    assert mode == 0o700


@pytest.mark.skipif(os.name != "posix", reason="symlink hardening solo en POSIX")
def test_state_dir_symlink_rechazado(tmp_path, monkeypatch):
    """Si un atacante pre-crea fluency4d como symlink en /tmp compartido,
    _state_path lo rechaza (OSError) en vez de seguir el enlace."""
    base = tmp_path / "base"
    base.mkdir()
    target = tmp_path / "target"
    target.mkdir()
    (base / "fluency4d").symlink_to(target, target_is_directory=True)
    monkeypatch.setattr(hook_utils.tempfile, "tempdir", str(base))
    with pytest.raises(OSError):
        hook_utils._state_path("k")


# --- atomic_write_json (helper compartido con statusline_setup) ---------------


def test_atomic_write_json_roundtrip_y_sin_temporales(tmp_path):
    dst = tmp_path / "sub" / "x.json"  # crea el dir padre si falta
    hook_utils.atomic_write_json(dst, {"a": 1, "b": "ñ"})
    assert json.loads(dst.read_text(encoding="utf-8")) == {"a": 1, "b": "ñ"}
    assert "\\u00f1" in dst.read_text(encoding="utf-8")  # ASCII por defecto
    assert [p.name for p in dst.parent.iterdir()] == ["x.json"]


def test_atomic_write_json_formato_de_usuario(tmp_path):
    dst = tmp_path / "settings.json"
    obj = {"env": {"K": "ñ"}, "x": [1]}
    hook_utils.atomic_write_json(dst, obj, indent=2, ensure_ascii=False, trailing_newline=True)
    esperado = json.dumps(obj, indent=2, ensure_ascii=False) + "\n"
    assert dst.read_bytes() == esperado.encode("utf-8")  # sin CRLF en Windows


def test_atomic_write_json_falla_no_pisa_destino(tmp_path, monkeypatch):
    """Si el replace falla, el destino previo queda intacto, no queda temporal
    y el OSError se propaga (el llamador decide)."""
    dst = tmp_path / "y.json"
    dst.write_text('{"viejo": true}', encoding="utf-8")

    def boom(src, dstp):
        raise OSError("replace fallo")

    monkeypatch.setattr(hook_utils.os, "replace", boom)
    with pytest.raises(OSError):
        hook_utils.atomic_write_json(dst, {"nuevo": True})
    assert dst.read_text(encoding="utf-8") == '{"viejo": true}'
    assert [p.name for p in tmp_path.iterdir()] == ["y.json"]


def test_atomic_write_text_surrogate_borra_tmp(tmp_path):
    """Un surrogate suelto (utf-8 no lo codifica) re-lanza UnicodeError SIN dejar
    el .tmp huerfano y sin tocar el destino."""
    dst = tmp_path / "s.json"
    dst.write_text("{}", encoding="utf-8")
    with pytest.raises(UnicodeError):
        hook_utils.atomic_write_text(dst, '{"x": "\ud800"}')
    assert dst.read_text(encoding="utf-8") == "{}"
    assert [p.name for p in tmp_path.iterdir()] == ["s.json"]


def test_atomic_write_text_symlink_escribe_en_destino(tmp_path):
    """os.replace sobre un symlink lo reemplazaria por un archivo comun: el helper
    resuelve el path y escribe en el DESTINO, dejando el link intacto."""
    target = tmp_path / "real" / "settings.json"
    target.parent.mkdir()
    target.write_text("{}", encoding="utf-8")
    link = tmp_path / "settings.json"
    try:
        link.symlink_to(target)
    except OSError:
        pytest.skip("sin permiso para crear symlinks")
    hook_utils.atomic_write_text(link, '{"a": 1}')
    assert link.is_symlink()
    assert target.read_text(encoding="utf-8") == '{"a": 1}'
