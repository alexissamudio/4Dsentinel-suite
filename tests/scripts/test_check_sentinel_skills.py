"""Guardrail de sentinel_check_skills.py: PASA sobre los skills reales del repo y
FALLA cuando un SKILL.md esta malformado (sin el frontmatter `description`).

- test_pasa_sobre_repo_real: el script real da exit 0.
- test_skill_sin_description_falla: check_skill detecta la falta de description.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "sentinel_check_skills.py"
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import sentinel_check_skills as scs  # noqa: E402


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


def test_skill_sin_description_falla(tmp_path):
    skill = tmp_path / "SKILL.md"
    skill.write_text(
        "---\nname: solo-nombre\n---\ncuerpo sin description ni referencia\n",
        encoding="utf-8",
    )
    errs = scs.check_skill(skill)
    assert any("description" in e for e in errs), errs


def test_skill_valido_pasa(tmp_path):
    skill = tmp_path / "SKILL.md"
    skill.write_text(
        "---\ndescription: orquesta sentinel-agents:validator\n---\ncuerpo\n",
        encoding="utf-8",
    )
    assert scs.check_skill(skill) == []
