"""bump_suite.py maneja la version PARAGUAS (metadata.version) del marketplace.

- test_check_*: --check da exit 0 sobre el repo real.
- test_set_*: --set escribe metadata.version sin tocar las versiones por-plugin.
- test_check_tag_*: valida metadata.version == tag, normalizando el ref.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "bump_suite.py"
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import bump_suite as bs  # noqa: E402


def test_check_exit_cero_sobre_repo_real():
    result = subprocess.run(
        ["uv", "run", str(SCRIPT), "--check"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=str(REPO_ROOT),
        timeout=120,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "metadata.version" in result.stdout


def _market(tmp_path, version="1.0.3"):
    market = tmp_path / "marketplace.json"
    market.write_text(
        json.dumps(
            {
                "metadata": {"version": version},
                "plugins": [{"name": "fluency-4d", "version": "0.18.1"}],
            }
        ),
        encoding="utf-8",
    )
    return market


def test_set_solo_toca_metadata_version(tmp_path, monkeypatch):
    market = _market(tmp_path)
    monkeypatch.setattr(bs, "MARKETPLACE", market)
    assert bs.set_version("1.0.4") == 0
    data = json.loads(market.read_text(encoding="utf-8"))
    assert data["metadata"]["version"] == "1.0.4"
    # las versiones por-plugin no se tocan
    assert data["plugins"][0]["version"] == "0.18.1"


def test_set_rechaza_no_semver(tmp_path, monkeypatch):
    market = _market(tmp_path)
    monkeypatch.setattr(bs, "MARKETPLACE", market)
    assert bs.set_version("1.0.4\n") == 1  # SEMVER con \Z rechaza newline
    assert bs.set_version("1.0") == 1


def test_read_version_falta_da_error_limpio(tmp_path, monkeypatch):
    market = tmp_path / "marketplace.json"
    market.write_text(json.dumps({"plugins": []}), encoding="utf-8")
    monkeypatch.setattr(bs, "MARKETPLACE", market)
    try:
        bs.read_version()
    except SystemExit:
        pass
    else:
        raise AssertionError("read_version deberia SystemExit si falta metadata.version")


def test_check_tag_coincide(tmp_path, monkeypatch):
    market = _market(tmp_path, "1.0.3")
    monkeypatch.setattr(bs, "MARKETPLACE", market)
    assert bs.check_tag("v1.0.3") == 0
    assert bs.check_tag("1.0.3") == 0
    assert bs.check_tag("refs/tags/v1.0.3") == 0


def test_check_tag_no_coincide_falla(tmp_path, monkeypatch):
    market = _market(tmp_path, "1.0.3")
    monkeypatch.setattr(bs, "MARKETPLACE", market)
    assert bs.check_tag("v1.0.4") == 1
