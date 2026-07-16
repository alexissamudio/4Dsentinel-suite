"""Tests de check_kb_blank.py: la guarda anti-write-back de la KB ISO.

Requisito verificado (no caracterizacion): el checksum debe DETECTAR cualquier
divergencia respecto del manifest pristino -- byte modificado, archivo faltante o
archivo nuevo -- y ACEPTAR la KB intacta. Se usa una KB falsa en tmp_path via
monkeypatch de los globales KB_DIR/MANIFEST (se leen en call-time), sin tocar la real.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import check_kb_blank as ckb  # noqa: E402


@pytest.fixture
def fake_kb(tmp_path, monkeypatch):
    """KB falsa con 2 archivos (uno en subdir) y sus globales monkeypatcheados."""
    kb = tmp_path / "kb"
    (kb / "checklists").mkdir(parents=True)
    (kb / "00-INSTRUCCIONES-IA.md").write_text("contrato\n", encoding="utf-8")
    (kb / "checklists" / "checklist-27001.md").write_text("CTRL-1\n", encoding="utf-8")
    monkeypatch.setattr(ckb, "KB_DIR", kb)
    monkeypatch.setattr(ckb, "MANIFEST", kb / ".manifest.sha256")
    return kb


def test_pristina_pasa(fake_kb):
    assert ckb.update() == 0
    assert ckb.check() == 0


def test_falta_manifest_falla(fake_kb):
    # sin --update previo, no hay manifest
    assert ckb.check() == 1


def test_byte_modificado_falla(fake_kb):
    ckb.update()
    (fake_kb / "00-INSTRUCCIONES-IA.md").write_text("MANIPULADO\n", encoding="utf-8")
    assert ckb.check() == 1


def test_archivo_faltante_falla(fake_kb):
    ckb.update()
    (fake_kb / "checklists" / "checklist-27001.md").unlink()
    assert ckb.check() == 1


def test_archivo_nuevo_falla(fake_kb):
    ckb.update()
    (fake_kb / "checklists" / "checklist-27002.md").write_text("CTRL-2\n", encoding="utf-8")
    assert ckb.check() == 1


def test_update_regenera_y_luego_pasa(fake_kb):
    ckb.update()
    # agrego un archivo nuevo -> falla, hasta re-blessear con update
    (fake_kb / "LICENSE").write_text("MIT\n", encoding="utf-8")
    assert ckb.check() == 1
    assert ckb.update() == 0
    assert ckb.check() == 0
    # el manifest lista los 3 archivos (excluye .manifest.sha256)
    lineas = (fake_kb / ".manifest.sha256").read_text(encoding="utf-8").splitlines()
    assert len([x for x in lineas if x.strip()]) == 3
