"""Guardrail de plugins/memory/scripts/check_commands.py: PASA sobre el plugin
real y FALLA cuando plugin.json declara un mcpServers con command NO-absoluto
(resoluble por PATH, CWE-427).

- test_pasa_sobre_repo_real: el script real da exit 0.
- test_command_no_absoluto_falla: check_plugin_json rechaza un command pelado.
- test_command_absoluto_ok / test_sin_mcpservers_ok: casos validos no fallan.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "plugins" / "memory" / "scripts" / "check_commands.py"
sys.path.insert(0, str(REPO_ROOT / "plugins" / "memory" / "scripts"))

import check_commands as cc  # noqa: E402


def _write_plugin_json(tmp_path, data) -> Path:
    path = tmp_path / "plugin.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


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


def test_command_no_absoluto_falla(tmp_path):
    path = _write_plugin_json(
        tmp_path, {"mcpServers": {"cbm": {"command": "codebase-memory-mcp"}}}
    )
    errs = cc.check_plugin_json(path)
    assert any("CWE-427" in e or "PATH" in e for e in errs), errs


def test_command_absoluto_ok(tmp_path):
    path = _write_plugin_json(
        tmp_path, {"mcpServers": {"cbm": {"command": "/usr/local/bin/cbm"}}}
    )
    assert cc.check_plugin_json(path) == []


def test_sin_mcpservers_ok(tmp_path):
    path = _write_plugin_json(tmp_path, {"name": "memory"})
    assert cc.check_plugin_json(path) == []
