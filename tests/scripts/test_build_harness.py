"""Exclusion "solo Claude Code" del generador multiharness (build_harness.py).

El Panel 4D (hooks module TSX), la status line, los temas y las skills
barra/statusline dependen de Claude Code: no deben llegar a dist/codex ni a
dist/opencode.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "tools" / "multiharness"))
import build_harness as B  # noqa: E402

REQUIRED = {
    "hooks/register.tsx",
    "tests",
    "types",
    "statusline",
    "themes",
    "skills/barra",
    "skills/statusline",
}


def test_lista_claude_code_only_nombra_todo() -> None:
    assert REQUIRED <= set(B.CLAUDE_CODE_ONLY)
    assert "modules" in B.CLAUDE_CODE_ONLY_HOOK_KEYS


def test_is_claude_code_only_relativo_y_absoluto() -> None:
    root = B.FLUENCY_ROOT
    assert B.is_claude_code_only(Path("hooks/register.tsx"))
    assert B.is_claude_code_only(root / "tests" / "panel.test.tsx")
    assert B.is_claude_code_only(root / "statusline" / "statusline.js")
    assert B.is_claude_code_only(root / "skills" / "barra" / "SKILL.md")
    assert B.is_claude_code_only(root / "skills" / "statusline")
    # Lo portable NO se excluye (ni prefijos parecidos).
    assert not B.is_claude_code_only(root / "hooks" / "bridge_router.py")
    assert not B.is_claude_code_only(root / "hooks" / "hooks.json")
    assert not B.is_claude_code_only(root / "skills" / "handoff")
    assert not B.is_claude_code_only(Path("skills/barrav2"))
    assert not B.is_claude_code_only(Path("typesx"))
    # Fuera de fluency-4d nunca aplica.
    assert not B.is_claude_code_only(B.SENTINEL_ROOT / "tests")


def test_discover_skills_excluye_claude_code_only() -> None:
    names = {p.parent.name for p in B.discover_skills()}
    assert "handoff" in names
    assert not names & {"barra", "statusline"}


def test_hooks_json_sin_modules() -> None:
    raw = json.loads((B.FLUENCY_ROOT / "hooks" / "hooks.json").read_text(encoding="utf-8"))
    assert "modules" in raw, "la fuente declara el hooks module del panel"
    assert "modules" not in B.load_hooks()
    # Aun si alguien le pasa el dict crudo, el transpilado lo quita.
    out = json.loads(B.build_hooks_json(raw))
    assert "modules" not in out
    assert set(out) == set(raw) - set(B.CLAUDE_CODE_ONLY_HOOK_KEYS)
    assert out["hooks"].keys() == raw["hooks"].keys()


def _texts(root: Path) -> dict[str, str]:
    return {
        p.relative_to(root).as_posix(): p.read_text(encoding="utf-8")
        for p in root.rglob("*")
        if p.is_file()
    }


def test_bundles_sin_piezas_claude_code_only(tmp_path: Path) -> None:
    B.build(tmp_path / "codex")
    B.build_opencode(tmp_path / "opencode")
    for label in ("codex", "opencode"):
        files = _texts(tmp_path / label)
        assert files, label
        for rel, text in files.items():
            assert "register.tsx" not in text, (label, rel)
            assert ".tsx" not in rel, (label, rel)
            assert "skills/barra" not in rel and "skills/statusline" not in rel, (label, rel)
            if rel.endswith(".json"):
                assert '"modules"' not in text, (label, rel)
