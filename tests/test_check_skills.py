"""Congela el validador del contrato de skills: el repo real pasa, y las piezas
puras (regex de paths de maquina y de referencias) matchean lo esperado."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "check_skills.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("check_skills", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_repo_real_cumple_el_contrato():
    result = subprocess.run(
        ["uv", "run", str(SCRIPT)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=str(REPO_ROOT),
        timeout=120,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "cumplen el contrato" in result.stdout


def test_regex_path_de_maquina():
    check = _load_module()
    assert check.MACHINE_PATH.search(r"C:\Users\alguien\x")
    assert check.MACHINE_PATH.search("/home/bob/proyecto")
    assert check.MACHINE_PATH.search("/Users/ana/dev")
    assert not check.MACHINE_PATH.search("un texto sin paths de maquina")


def test_regex_referencias():
    check = _load_module()
    texto = "Lee `references/delegacion.md` y references/ejemplo-clasificacion.md."
    hallados = set(check.REF.findall(texto))
    assert hallados == {"delegacion.md", "ejemplo-clasificacion.md"}


def test_strip_quotes():
    check = _load_module()
    assert check._strip_quotes('"4d"') == "4d"
    assert check._strip_quotes("'caveman'") == "caveman"
    assert check._strip_quotes("4d-init") == "4d-init"


if __name__ == "__main__":
    sys.exit(subprocess.call(["pytest", "-q", str(Path(__file__))]))
