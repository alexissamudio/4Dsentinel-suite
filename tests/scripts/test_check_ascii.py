"""check_ascii.py exige ASCII puro en los .py de produccion (hooks + scripts).

- test_repo_real_es_ascii: el script real da exit 0 sobre el repo.
- test_detecta_no_ascii / test_ascii_ok: check_file sobre archivos crafteados.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "check_ascii.py"
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import check_ascii as ca  # noqa: E402


def test_repo_real_es_ascii():
    result = subprocess.run(
        ["uv", "run", str(SCRIPT)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=str(REPO_ROOT),
        timeout=120,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_detecta_no_ascii(tmp_path, monkeypatch):
    monkeypatch.setattr(ca, "REPO_ROOT", tmp_path)
    bad = tmp_path / "malo.py"
    bad.write_text("# comentario con acento: cafe con leche\nx = 'nino'\n", encoding="utf-8")
    # inyecta un no-ASCII real
    bad.write_text("# café\nx = 1\n", encoding="utf-8")
    errs = ca.check_file(bad)
    assert errs and "no-ASCII" in errs[0], errs


def test_ascii_ok(tmp_path, monkeypatch):
    monkeypatch.setattr(ca, "REPO_ROOT", tmp_path)
    good = tmp_path / "bien.py"
    good.write_text("# comentario sin acentos\nx = 'ok'\n", encoding="utf-8")
    assert ca.check_file(good) == []
