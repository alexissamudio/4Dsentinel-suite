"""Exclusion "solo Claude Code" y contratos del generador multiharness (build_harness.py).

El Panel 4D (hooks module TSX), la status line, los temas y las skills
barra/statusline dependen de Claude Code: no deben llegar a dist/codex,
dist/opencode ni dist/antigravity.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "tools" / "multiharness"))
import build_harness as B  # noqa: E402
import check_harness as C  # noqa: E402

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
    B.build_antigravity(tmp_path / "antigravity")
    for label in ("codex", "opencode", "antigravity"):
        files = _texts(tmp_path / label)
        assert files, label
        for rel, text in files.items():
            assert "register.tsx" not in text, (label, rel)
            assert ".tsx" not in rel, (label, rel)
            assert "skills/barra" not in rel and "skills/statusline" not in rel, (label, rel)
            if rel.endswith(".json"):
                assert '"modules"' not in text, (label, rel)


def test_antigravity_estructura_y_schemas(tmp_path: Path) -> None:
    ag_dir = tmp_path / "antigravity"
    B.build_antigravity(ag_dir)
    files = _texts(ag_dir)
    expected = {
        "plugin.json",
        "hooks.json",
        "hooks/fluency_hooks.py",
        "skills/handoff/SKILL.md",
        "agents/critic.md",
        "agents/advisor.md",
        "rules/AGENTS.md",
        "README.md",
    }
    assert set(files) == expected

    # plugin.json: solo claves top-level soportadas por Antigravity + version sincronizada
    allowed_plugin_keys = {
        "name",
        "description",
        "logo",
        "suggestedPrompts",
        "displayName",
        "version",
        "author",
        "homepage",
        "repository",
        "disabled",
    }
    plugin_data = json.loads(files["plugin.json"])
    assert set(plugin_data) <= allowed_plugin_keys
    src_plugin = json.loads(
        (B.FLUENCY_ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8")
    )
    assert plugin_data["version"] == src_plugin["version"]

    # hooks.json: en la raiz del plugin, clave superior = grupo ("fluency-4d")
    hooks_data = json.loads(files["hooks.json"])
    assert "hooks" not in hooks_data
    assert "fluency-4d" in hooks_data
    grp = hooks_data["fluency-4d"]
    assert isinstance(grp.get("PreInvocation"), list)
    assert isinstance(grp.get("Stop"), list)
    for event in ("PreInvocation", "Stop"):
        for handler in grp[event]:
            assert "matcher" not in handler
            assert handler["type"] == "command"

    # rules/AGENTS.md: markdown plano sin frontmatter YAML
    assert not files["rules/AGENTS.md"].startswith("---")
    assert "## Reglas del proyecto (siempre)" in files["rules/AGENTS.md"]

    # agents/*.md: frontmatter name + description (sin maxTurns/color/tools de Claude)
    for agent_name in ("critic", "advisor"):
        fm = B.parse_frontmatter(files[f"agents/{agent_name}.md"])
        assert fm.get("name") == agent_name
        assert fm.get("description")
        assert not (set(fm) & {"maxTurns", "color", "tools"})

    # skills/handoff/SKILL.md: home reescrito a ~/.gemini/antigravity
    assert "~/.gemini/antigravity/plans/" in files["skills/handoff/SKILL.md"]
    assert "~/.claude/plans/" not in files["skills/handoff/SKILL.md"]

    # guardas de check_harness sobre el bundle generado
    assert not C.validate_antigravity(ag_dir)


def test_antigravity_shim_e2e(tmp_path: Path) -> None:
    ag_dir = tmp_path / "antigravity"
    B.build_antigravity(ag_dir)
    shim = ag_dir / "hooks" / "fluency_hooks.py"

    # Workspace con un bridge real (incluyendo keyword con acento para validar PYTHONUTF8)
    ws = tmp_path / "ws"
    docs = ws / ".claude" / "docs"
    docs.mkdir(parents=True)
    (docs / "hooks.md").write_text("# Hooks\n", encoding="utf-8")
    (docs / "bridges.json").write_text(
        json.dumps(
            {
                "temas": [
                    {
                        "tema": "Hooks",
                        "archivo": ".claude/docs/hooks.md",
                        "keywords": ["configuracion", "stdin", "stdout"],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    env = os.environ.copy()
    home = tmp_path / "home"
    home.mkdir()
    env["TMPDIR"] = str(tmp_path)
    env["TEMP"] = str(tmp_path)
    env["TMP"] = str(tmp_path)
    env["HOME"] = str(home)
    env["USERPROFILE"] = str(home)
    env.pop("PYTHONUTF8", None)  # el propio shim debe inyectar PYTHONUTF8=1 al hijo

    # 1) PreInvocation con invocationNum=0 y prompt con acentos -> devuelve injectSteps
    pre_input = {
        "conversationId": "conv-ag-test-1",
        "invocationNum": 0,
        "lastUserInput": "necesito revisar la configuraci\u00f3n del hook en el proyecto",
        "workspacePaths": [str(ws)],
    }
    res0 = subprocess.run(
        [sys.executable, str(shim), "PreInvocation"],
        input=json.dumps(pre_input),
        text=True,
        encoding="utf-8",
        capture_output=True,
        env=env,
        timeout=15,
        check=True,
    )
    out0 = json.loads(res0.stdout)
    assert "injectSteps" in out0
    msg = out0["injectSteps"][0]["ephemeralMessage"]
    assert ".claude/docs/hooks.md" in msg

    # 2) PreInvocation con invocationNum=1 (re-invocacion tras tool call) -> NO-OP
    pre_reinv = dict(pre_input, invocationNum=1)
    res1 = subprocess.run(
        [sys.executable, str(shim), "PreInvocation"],
        input=json.dumps(pre_reinv),
        text=True,
        encoding="utf-8",
        capture_output=True,
        env=env,
        timeout=15,
        check=True,
    )
    assert json.loads(res1.stdout) == {}

    # 3) Stop con FLUENCY_4D_STRICT=1 -> traduce decision:block a decision:continue (1 vez)
    env_strict = dict(env, FLUENCY_4D_STRICT="1")
    stop_input = {
        "conversationId": "conv-ag-test-stop",
        "workspacePaths": [str(ws)],
    }
    res_stop1 = subprocess.run(
        [sys.executable, str(shim), "Stop"],
        input=json.dumps(stop_input),
        text=True,
        encoding="utf-8",
        capture_output=True,
        env=env_strict,
        timeout=15,
        check=True,
    )
    out_stop1 = json.loads(res_stop1.stdout)
    assert out_stop1.get("decision") == "continue"
    assert "DISCERNIMIENTO" in out_stop1.get("reason", "")

    res_stop2 = subprocess.run(
        [sys.executable, str(shim), "Stop"],
        input=json.dumps(stop_input),
        text=True,
        encoding="utf-8",
        capture_output=True,
        env=env_strict,
        timeout=15,
        check=True,
    )
    assert json.loads(res_stop2.stdout) == {}

