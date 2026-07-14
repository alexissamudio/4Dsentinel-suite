"""Guardrail de check_suite_versions.py: PASA sobre el marketplace real y FALLA
(exit 1 controlado, sin crash) cuando la version paraguas != subtree o cuando un
plugin trae `source` objeto en vez de una ruta local.

- test_pasa_sobre_repo_real: el script real da exit 0 sobre el repo.
- test_version_desalineada_falla: paraguas != subtree -> exit 1.
- test_source_objeto_no_crashea: source dict -> exit 1 controlado (antes:
  TypeError no capturado en REPO_ROOT / dict).
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "check_suite_versions.py"
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import check_suite_versions as csv_mod  # noqa: E402


def _setup(tmp_path, market_data, monkeypatch):
    plugin_dir = tmp_path / ".claude-plugin"
    plugin_dir.mkdir(parents=True, exist_ok=True)
    market = plugin_dir / "marketplace.json"
    market.write_text(json.dumps(market_data), encoding="utf-8")
    monkeypatch.setattr(csv_mod, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(csv_mod, "MARKETPLACE", market)


def test_pasa_sobre_repo_real():
    result = subprocess.run(
        ["uv", "run", str(SCRIPT)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=str(REPO_ROOT),
        timeout=120,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_version_desalineada_falla(tmp_path, monkeypatch):
    _setup(
        tmp_path,
        {"plugins": [{"name": "p1", "source": "./sub", "version": "1.0.0"}]},
        monkeypatch,
    )
    sub = tmp_path / "sub" / ".claude-plugin"
    sub.mkdir(parents=True)
    (sub / "plugin.json").write_text(json.dumps({"version": "2.0.0"}), encoding="utf-8")
    assert csv_mod.main() == 1  # paraguas 1.0.0 != subtree 2.0.0


def test_source_objeto_no_crashea(tmp_path, monkeypatch):
    _setup(
        tmp_path,
        {"plugins": [{"name": "p1", "source": {"source": "github"}, "version": "1.0.0"}]},
        monkeypatch,
    )
    # No debe lanzar TypeError: da error legible y exit 1 controlado.
    assert csv_mod.main() == 1
