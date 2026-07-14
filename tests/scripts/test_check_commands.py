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


def test_command_drive_relative_falla(tmp_path):
    # C:foo (sin barra) es DRIVE-RELATIVE en Windows: resuelve contra el cwd de la
    # unidad, hijackeable. El regex viejo lo aceptaba como "absoluto Windows".
    path = _write_plugin_json(
        tmp_path, {"mcpServers": {"cbm": {"command": "C:foo\\bar"}}}
    )
    errs = cc.check_plugin_json(path)
    assert any("CWE-427" in e or "PATH" in e for e in errs), errs


def test_command_windows_absoluto_ok(tmp_path):
    for cmd in ("C:\\bin\\cbm.exe", "C:/bin/cbm.exe"):
        path = _write_plugin_json(tmp_path, {"mcpServers": {"cbm": {"command": cmd}}})
        assert cc.check_plugin_json(path) == [], cmd


def test_cubre_los_tres_plugins():
    # El guardrail anti-CWE-427 debe recorrer los 3 plugins, no solo memory.
    nombres = {p.parent.parent.name for p in cc._plugin_jsons()}
    assert {"fluency-4d", "sentinel-agents", "memory"} <= nombres, nombres


def test_command_mal_tipado_no_crashea(tmp_path):
    # BH-01: un mcpServers con command no-str o cfg no-dict NO debe tirar
    # TypeError/AttributeError (solo se atrapaba JSONDecodeError) -> el script
    # entero reventaba. Ahora falla cerrado con mensaje limpio.
    casos = [
        {"mcpServers": {"cbm": {"command": None}}},
        {"mcpServers": {"cbm": {"command": ["a", "b"]}}},
        {"mcpServers": {"cbm": {"command": 123}}},
        {"mcpServers": {"cbm": "no soy un objeto"}},
    ]
    for data in casos:
        path = _write_plugin_json(tmp_path, data)
        errs = cc.check_plugin_json(path)  # no debe lanzar
        assert errs, data  # reporta el problema, no crashea


def test_command_unc_absoluto_ok(tmp_path):
    # BH-02: una ruta UNC absoluta (\\host\share\x.exe) es absoluta y no
    # hijackeable -> debe aceptarse (antes se rechazaba: falso positivo).
    path = _write_plugin_json(
        tmp_path, {"mcpServers": {"cbm": {"command": "\\\\host\\share\\cbm.exe"}}}
    )
    assert cc.check_plugin_json(path) == []


def test_command_un_solo_backslash_falla(tmp_path):
    # Un solo backslash (\foo) es raiz-relativo de la unidad actual (hijackeable)
    # -> sigue rechazado; el fix UNC solo abre `\\` (dos).
    path = _write_plugin_json(
        tmp_path, {"mcpServers": {"cbm": {"command": "\\foo\\cbm.exe"}}}
    )
    errs = cc.check_plugin_json(path)
    assert any("CWE-427" in e or "PATH" in e for e in errs), errs
