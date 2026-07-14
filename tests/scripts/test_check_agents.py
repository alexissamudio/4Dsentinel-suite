"""Guardrail de check_agents.py: PASA sobre los agentes reales del repo y FALLA
si un agente declara una tool de escritura prohibida (Write/Bash no permitido).

- test_pasa_sobre_repo_real: el script real da exit 0 sobre agents/.
- test_*_falla: un agente crafteado con Write o con Bash fuera de BASH_ALLOWED
  es rechazado por check_agent (sin tocar el repo real; usa tmp_path).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "check_agents.py"
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import check_agents as ca  # noqa: E402


def _agent(tools: str, name: str = "malo") -> str:
    return (
        "---\n"
        f"name: {name}\n"
        "description: agente de prueba\n"
        "model: inherit\n"
        "maxTurns: 10\n"
        f"tools: {tools}\n"
        "---\n"
        "cuerpo que referencia agent-contract.md\n"
    )


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


def test_agente_con_write_falla(tmp_path):
    path = tmp_path / "malo.md"
    path.write_text(_agent("Read, Grep, Write"), encoding="utf-8")
    errs = ca.check_agent(path)
    assert any("Write" in e for e in errs), errs


def test_agente_con_bash_no_permitido_falla(tmp_path):
    # 'malo' no esta en BASH_ALLOWED (solo validator/debugger).
    path = tmp_path / "malo.md"
    path.write_text(_agent("Read, Grep, Bash"), encoding="utf-8")
    errs = ca.check_agent(path)
    assert any("Bash" in e for e in errs), errs
