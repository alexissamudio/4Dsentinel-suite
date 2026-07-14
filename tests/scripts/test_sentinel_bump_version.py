"""Regresion: sentinel_bump_version.py --check debe operar sobre la entrada
name=="sentinel-agents" del marketplace (no sobre plugins[0], que es fluency-4d).

Antes del fix este test FALLA: --check leia plugins[0].version (fluency, 0.15.0)
y la comparaba contra plugin.json de sentinel (0.6.0) -> exit 1 falso.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "sentinel_bump_version.py"


def test_check_exit_cero_sobre_estado_actual():
    result = subprocess.run(
        ["uv", "run", str(SCRIPT), "--check"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=str(REPO_ROOT),
        timeout=120,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "OK - version sincronizada" in result.stdout


if __name__ == "__main__":
    sys.exit(subprocess.call(["pytest", "-q", str(Path(__file__))]))
