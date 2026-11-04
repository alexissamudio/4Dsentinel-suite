"""Exclusion "solo Claude Code" del generador multiharness (build_harness.py).

El Panel 4D (hooks module TSX), la status line, los temas y las skills
barra/statusline dependen de Claude Code: no deben llegar a dist/codex ni a
dist/opencode.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

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


@pytest.fixture(scope="module")
def bundles(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Bundles codex + opencode generados UNA vez por modulo (solo lectura)."""
    root = tmp_path_factory.mktemp("bundles")
    B.build(root / "codex")
    B.build_opencode(root / "opencode")
    return root


def _texts(root: Path) -> dict[str, str]:
    return {
        p.relative_to(root).as_posix(): p.read_text(encoding="utf-8")
        for p in root.rglob("*")
        if p.is_file()
    }


def test_bundles_sin_piezas_claude_code_only(bundles: Path) -> None:
    for label in ("codex", "opencode"):
        files = _texts(bundles / label)
        assert files, label
        for rel, text in files.items():
            assert "register.tsx" not in text, (label, rel)
            assert ".tsx" not in rel, (label, rel)
            assert "skills/barra" not in rel and "skills/statusline" not in rel, (label, rel)
            if rel.endswith(".json"):
                assert '"modules"' not in text, (label, rel)


def test_opencode_emite_todo_y_omite_skills_sin_soporte(bundles: Path) -> None:
    root = bundles / "opencode"
    cmds = {p.stem for p in (root / "command").glob("*.md")}
    assert {"4d", "4d-status", "caveman", "adhd", "handoff", "sentinel-audit"} <= cmds
    assert {"buscar", "indexar"} <= cmds  # commands de memory
    assert not cmds & set(B.unsupported_skills("opencode"))
    assert {p.stem for p in (root / "agent").glob("*.md")} == set(B.discover_agents())
    assert (root / "references" / "agent-contract.md").is_file()
    assert (root / "references" / "iso-27000" / ".manifest.sha256").is_file()
    assert not C.validate_opencode(root)


def test_opencode_guardas_detectan_regresiones(bundles: Path, tmp_path: Path) -> None:
    root = tmp_path / "opencode"
    shutil.copytree(bundles / "opencode", root)  # este test muta el bundle
    shim = root / "plugin" / "fluency-hooks.js"
    text = shim.read_text(encoding="utf-8")
    shim.write_text(
        text.replace("synthetic: true,", "").replace("session_id:", "sid:"), encoding="utf-8"
    )
    assert C.validate_opencode(root)
    # v2 sin id/setup (loader v2: "Plugin must export a default definition...").
    shim.write_text(text.replace("  setup: setupV2,\n", ""), encoding="utf-8")
    assert C.validate_opencode(root)
    # Sin hook context v2, o volviendo a spawnSync (bloquea el event loop).
    shim.write_text(
        text.replace('api.session.hook("context"', 'api.session.hook("x"'), encoding="utf-8"
    )
    assert C.validate_opencode(root)
    shim.write_text(text + "\n// spawnSync(\n", encoding="utf-8")
    assert C.validate_opencode(root)
    shim.write_text(text, encoding="utf-8")
    assert not C.validate_opencode(root)
    cmd = root / "command" / "4d.md"
    good = cmd.read_text(encoding="utf-8")
    cmd.write_text(good + "\nSegui plugins/fluency-4d/skills/4d/SKILL.md\n", encoding="utf-8")
    assert C.validate_opencode(root)
    cmd.write_text(good + "\nusa sentinel-agents:advisor\n", encoding="utf-8")
    assert C.validate_opencode(root)


def _fake_agent(tools_block: str) -> dict[str, dict[str, str]]:
    text = "---\nname: fake\ndescription: x\n" + tools_block + "---\n\ncuerpo\n"
    meta = B.parse_frontmatter(text)
    meta.update(_path="fake.md", _text=text)
    return {"fake": meta}


def test_opencode_permission_tools_inline_y_lista_yaml() -> None:
    """`tools:` como lista YAML (fix F1 de parse_tools) emite los mismos deny que inline."""
    inline = B.build_opencode_agent(_fake_agent("tools: Read, Grep, Glob\n"), "fake")
    lista = B.build_opencode_agent(_fake_agent("tools:\n  - Read\n  - Grep\n  - Glob\n"), "fake")
    for out in (inline, lista):
        assert "  edit: deny\n" in out
        assert "  bash: deny\n" in out
        assert "  webfetch: deny\n" in out
    assert lista == inline
    # Con Bash en la lista NO se niega bash (la lista se lee, no queda vacia).
    con_bash = B.build_opencode_agent(_fake_agent("tools:\n  - Read\n  - Bash\n"), "fake")
    assert "bash: deny" not in con_bash and "edit: deny" in con_bash


FAKE_HOOK = """# /// script
# requires-python = ">=3.11"
# ///
import json, sys, time
data = json.loads(sys.stdin.buffer.read().decode("utf-8"))
kind = {kind!r}
if kind == "A":
    time.sleep(0.4)  # termina DESPUES de B: el orden de los chunks es por indice
    with open({log!r}, "a", encoding="utf-8") as fh:
        fh.write(data["session_id"] + "\\n")
    ctx = "A:%s|%s|%s" % (data["prompt"], data["permission_mode"], data["cwd"])
elif kind == "B":
    ctx = "B:sentinel-agents:critic"
else:
    sys.exit(1)
out = {{"hookSpecificOutput": {{"hookEventName": "UserPromptSubmit", "additionalContext": ctx}}}}
sys.stdout.write(json.dumps(out, ensure_ascii=False))
"""


@pytest.mark.skipif(
    not (shutil.which("node") and shutil.which("uv")), reason="requiere node y uv en el PATH"
)
def test_opencode_shim_contrato_v1_v2_en_node(bundles: Path, tmp_path: Path) -> None:
    """Importa el plugin generado en Node y ejercita los contratos v1 y v2 con mocks."""
    text = (bundles / "opencode" / "plugin" / "fluency-hooks.js").read_text(encoding="utf-8")
    log = tmp_path / "hooks.log"
    fakes = []
    for kind in ("A", "B", "C"):
        f = tmp_path / ("fake_%s.py" % kind)
        f.write_text(FAKE_HOOK.format(kind=kind, log=str(log)), encoding="utf-8")
        fakes.append(f)
    marker = "const USER_PROMPT_HOOKS = [\n"
    start = text.index(marker) + len(marker)
    end = text.index("\n];", start)
    hooks_js = ",\n".join("  " + json.dumps(str(f)) for f in fakes)
    plugin = tmp_path / "plugin.mjs"
    plugin.write_text(text[:start] + hooks_js + text[end:], encoding="utf-8")
    script = Path(__file__).with_name("opencode_shim_contract.mjs")
    res = subprocess.run(
        ["node", str(script), str(plugin), str(log), str(tmp_path)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
    )
    assert res.returncode == 0, res.stdout + res.stderr
    assert "OK contrato v1 + v2" in res.stdout
