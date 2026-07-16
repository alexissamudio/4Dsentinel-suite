"""check_commit_trailer.py rechaza commits con atribucion de IA (CLAUDE.md, F15).

- test_repo_real_limpio: sobre el repo real, HEAD no tiene atribucion -> exit 0.
- test_detecta_trailer / test_commit_limpio_ok: repo git temporal con y sin trailer.
- test_base_invalido_cae_a_head: un base 000...0 no revienta, revisa solo HEAD.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "check_commit_trailer.py"
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import check_commit_trailer as ct  # noqa: E402


def _git(cwd: Path, *args: str) -> str:
    out = subprocess.run(
        ["git", *args], cwd=str(cwd), capture_output=True, text=True, encoding="utf-8", check=True
    )
    return out.stdout.strip()


def _init_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "t@t.t")
    _git(repo, "config", "user.name", "t")
    _git(repo, "commit", "-q", "--allow-empty", "-m", "base limpio")
    return repo


def test_repo_real_limpio():
    result = subprocess.run(
        ["uv", "run", str(SCRIPT)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=str(REPO_ROOT),
        timeout=120,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_detecta_trailer(tmp_path, monkeypatch):
    repo = _init_repo(tmp_path)
    base = _git(repo, "rev-parse", "HEAD")
    _git(
        repo,
        "commit",
        "-q",
        "--allow-empty",
        "-m",
        "feat: algo",
        "-m",
        "Co-Authored-By: Claude <noreply@anthropic.com>",
    )
    monkeypatch.chdir(repo)
    offenders = ct.offending_commits(base)
    assert len(offenders) == 1, offenders


def test_commit_limpio_ok(tmp_path, monkeypatch):
    repo = _init_repo(tmp_path)
    base = _git(repo, "rev-parse", "HEAD")
    _git(repo, "commit", "-q", "--allow-empty", "-m", "feat: algo sin atribucion")
    monkeypatch.chdir(repo)
    assert ct.offending_commits(base) == []


def test_base_invalido_cae_a_head(tmp_path, monkeypatch):
    repo = _init_repo(tmp_path)
    monkeypatch.chdir(repo)
    # base 000...0 (branch nuevo): no revienta, revisa solo HEAD (limpio) -> []
    assert ct.offending_commits("0000000000000000000000000000000000000000") == []
