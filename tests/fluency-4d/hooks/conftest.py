"""Fixtures compartidas: cada test corre los hooks por subprocess con stdin JSON
y un directorio temp aislado (TMPDIR/TEMP/TMP apuntan a tmp_path, asi el estado
de sesion de fluency4d nunca toca el temp real ni se comparte entre tests)."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
HOOKS_DIR = REPO_ROOT / "plugins" / "fluency-4d" / "hooks"


@pytest.fixture()
def run_hook(tmp_path):
    def _run(hook_name: str, payload: dict, env_extra: dict | None = None) -> str:
        env = {
            **os.environ,
            "TMPDIR": str(tmp_path),
            "TEMP": str(tmp_path),
            "TMP": str(tmp_path),
            # Aisla tambien el home: las stats van a ~/.claude/fluency4d/
            "HOME": str(tmp_path / "home"),
            "USERPROFILE": str(tmp_path / "home"),
            "PYTHONUTF8": "1",
        }
        env.pop("FLUENCY_4D_SAVE_PCT", None)
        env.pop("FLUENCY_4D_STRICT", None)
        if env_extra:
            env.update(env_extra)
        result = subprocess.run(
            ["uv", "run", "--script", str(HOOKS_DIR / hook_name)],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=env,
            timeout=120,
        )
        assert result.returncode == 0, result.stderr
        return result.stdout.strip()

    return _run


@pytest.fixture()
def state_of(tmp_path):
    def _state(session_id: str, suffix: str = "") -> dict | None:
        key = "sid-" + hashlib.sha256(session_id.encode()).hexdigest()[:16] + suffix
        path = tmp_path / "fluency4d" / f"{key}.json"
        return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None

    return _state


@pytest.fixture()
def project(tmp_path):
    """Proyecto de juguete con .claude/docs/ vacio; los tests agregan archivos."""
    root = tmp_path / "proyecto"
    (root / ".claude" / "docs").mkdir(parents=True)
    return root


BRIDGES_AUTH = {
    "version": 1,
    "temas": [
        {
            "tema": "auth",
            "archivo": ".claude/docs/auth.md",
            "keywords": ["auth", "autenticacion", "login", "token", "jwt"],
            "rutas": ["src/auth/", "config/auth.js"],
        },
        {
            "tema": "endpoints",
            "archivo": ".claude/docs/endpoints.md",
            "keywords": ["endpoint", "endpoints", "rest"],
        },
        {
            "tema": "database",
            "archivo": ".claude/docs/database.md",
            "keywords": ["database", "modelos", "migraciones"],
        },
    ],
}


def write_bridges(project: Path, data=None) -> None:
    (project / ".claude" / "docs" / "bridges.json").write_text(
        data if isinstance(data, str) else json.dumps(data or BRIDGES_AUTH),
        encoding="utf-8",
    )
