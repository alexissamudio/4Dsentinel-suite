"""statusline_setup.py (skill /statusline): setup / remove / status por subprocess.

Mismo patron que conftest.run_hook: el script REAL corre con `uv run --script`
(o bajo coverage con FLUENCY_COV) y HOME/USERPROFILE apuntan a tmp_path, asi
nunca se toca el ~/.claude real. Los JSON del usuario se comparan byte a byte.
"""

from __future__ import annotations

import json
import os
import re
import shlex
import shutil
import stat
import subprocess
import time
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
PLUGIN_DIR = REPO_ROOT / "plugins" / "fluency-4d"
SCRIPT = PLUGIN_DIR / "hooks" / "statusline_setup.py"

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="requiere node en PATH")

USER_SETTINGS = {
    "env": {"FOO": "bar", "CLAUDE_CODE_PLUGIN_DIRS": "/x/mods/panel-4d"},
    "permissions": {"allow": ["Bash(ls:*)"]},
    "model": "opus",
    "nota": "acentos: canción",
}
USER_KB = {
    "$schema": "https://www.schemastore.org/claude-code-keybindings.json",
    "bindings": [{"context": "Chat", "bindings": {"ctrl+e": "chat:externalEditor"}}],
}


def dump(obj: object) -> bytes:
    return (json.dumps(obj, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


@pytest.fixture()
def home(tmp_path: Path) -> Path:
    h = tmp_path / "home"
    (h / ".claude").mkdir(parents=True)
    return h


@pytest.fixture()
def run(home: Path, tmp_path: Path):
    return make_runner(home, tmp_path)


def make_runner(home: Path, tmp_path: Path):
    def _run(*args: str, env_extra: dict[str, str] | None = None) -> subprocess.CompletedProcess:
        env = {
            **os.environ,
            "HOME": str(home),
            "USERPROFILE": str(home),
            "TMPDIR": str(tmp_path),
            "TEMP": str(tmp_path),
            "TMP": str(tmp_path),
            "PYTHONUTF8": "1",
        }
        env.pop("CLAUDE_PLUGIN_ROOT", None)
        env.pop("FLUENCY_4D_NODE_BIN", None)
        if env_extra:
            env.update(env_extra)
        cmd = ["uv", "run", "--script", str(SCRIPT), *args]
        if os.environ.get("FLUENCY_COV"):
            cmd = [
                "uv",
                "run",
                "--with",
                "coverage==7.15.2",
                "coverage",
                "run",
                "--parallel-mode",
                "--source",
                str(SCRIPT.parent),
                str(SCRIPT),
                *args,
            ]
        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=env,
            cwd=REPO_ROOT,
            timeout=120,
        )

    return _run


def settings(home: Path) -> Path:
    return home / ".claude" / "settings.json"


def kb(home: Path) -> Path:
    return home / ".claude" / "keybindings.json"


def fdir(home: Path) -> Path:
    return home / ".claude" / "fluency4d"


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_setup_status_remove_ciclo_limpio(run, home):
    settings(home).write_bytes(dump(USER_SETTINGS))
    kb(home).write_bytes(dump(USER_KB))
    before_s, before_k = settings(home).read_bytes(), kb(home).read_bytes()

    r = run("setup", "--keybinding", "--copy-theme")
    assert r.returncode == 0, r.stdout + r.stderr
    copy = fdir(home) / "statusline.js"
    assert copy.read_bytes() == (PLUGIN_DIR / "statusline" / "statusline.js").read_bytes()
    s = read(settings(home))
    assert s["statusLine"] == {
        "type": "command",
        "command": "node " + shlex.quote(copy.resolve().as_posix()),
        "refreshInterval": 5,
    }
    assert "\\" not in s["statusLine"]["command"]
    assert "CLAUDE_CODE_PLUGIN_DIRS" not in s["env"] and s["env"]["FOO"] == "bar"
    assert s["nota"] == "acentos: canción"
    chat = read(kb(home))["bindings"][0]["bindings"]
    assert chat["ctrl+x ctrl+p"] == "command:panel"
    assert (home / ".claude" / "themes" / "templado.json").is_file()
    rec = read(fdir(home) / "setup.json")
    assert rec["version"] == read(PLUGIN_DIR / ".claude-plugin" / "plugin.json")["version"]
    assert rec["statusline"] == {"had_key": False, "had_previous": False, "previous": None}
    assert "pending" not in rec
    assert rec["plugin_dirs"]["previous"] == "/x/mods/panel-4d"

    st = run("status")
    assert st.returncode == 0
    assert "sincronizada" in st.stdout and "apunta a la copia fija" in st.stdout
    assert "refresco cada 5 s" in st.stdout
    assert "SUGERENCIA" not in st.stdout

    r = run("remove")
    assert r.returncode == 0, r.stdout + r.stderr
    assert settings(home).read_bytes() == before_s
    assert kb(home).read_bytes() == before_k
    assert not copy.exists()
    assert not (fdir(home) / "setup.json").exists()
    assert not (home / ".claude" / "themes" / "templado.json").exists()


def test_setup_sin_archivos_previos_y_remove_los_borra(run, home):
    assert run("setup", "--keybinding").returncode == 0
    assert settings(home).is_file() and kb(home).is_file()
    assert run("remove").returncode == 0
    assert not settings(home).exists()
    assert not kb(home).exists()


def test_statusline_ajeno_sale_2_sin_tocar_y_force_lo_reemplaza(run, home):
    ajeno = {**USER_SETTINGS, "statusLine": {"type": "command", "command": "otro.sh"}}
    settings(home).write_bytes(dump(ajeno))
    before = settings(home).read_bytes()

    r = run("setup")
    assert r.returncode == 2
    assert "otro.sh" in r.stdout
    assert settings(home).read_bytes() == before
    assert not fdir(home).exists()  # ni copia, ni backup, ni setup.json

    r = run("setup", "--force")
    assert r.returncode == 0, r.stdout + r.stderr
    s = read(settings(home))
    assert "fluency4d/statusline.js" in s["statusLine"]["command"]
    assert list(s) == list(ajeno)  # reemplazo en el lugar, mismo orden
    rec = read(fdir(home) / "setup.json")
    assert rec["statusline"]["previous"] == {"type": "command", "command": "otro.sh"}

    assert run("remove").returncode == 0
    assert settings(home).read_bytes() == before


def test_settings_corrupto_aborta_sin_escribir(run, home):
    settings(home).write_text('{"env": {', encoding="utf-8")
    r = run("setup", "--force")
    assert r.returncode == 1
    assert "no es JSON valido" in r.stdout
    assert settings(home).read_text(encoding="utf-8") == '{"env": {'
    assert not fdir(home).exists()


def test_setup_idempotente(run, home):
    settings(home).write_bytes(dump(USER_SETTINGS))
    kb(home).write_bytes(dump(USER_KB))
    before_s, before_k = settings(home).read_bytes(), kb(home).read_bytes()
    assert run("setup", "--keybinding").returncode == 0
    after1 = (settings(home).read_bytes(), kb(home).read_bytes())
    rec1 = read(fdir(home) / "setup.json")
    assert run("setup", "--keybinding").returncode == 0
    assert (settings(home).read_bytes(), kb(home).read_bytes()) == after1
    assert read(fdir(home) / "setup.json") == rec1  # no pisa los valores previos
    assert run("remove").returncode == 0
    assert (settings(home).read_bytes(), kb(home).read_bytes()) == (before_s, before_k)


def test_remove_sin_setup_previo_no_toca_nada(run, home):
    settings(home).write_bytes(dump(USER_SETTINGS))
    before = settings(home).read_bytes()
    r = run("remove")
    assert r.returncode == 0
    assert "nada que revertir" in r.stdout
    assert settings(home).read_bytes() == before
    assert not fdir(home).exists()


def dated(backups: Path, name: str) -> list[Path]:
    pat = re.compile(re.escape(name) + r"\.\d{8}-\d{6}-\d{6}\.bak")
    return [p for p in backups.iterdir() if pat.fullmatch(p.name)]


def test_poda_conserva_orig_bak_y_ajenos_y_remove_borra_orig(run, home):
    """Fix 2: la poda solo toca backups fechados propios; el .orig.bak de la primera
    instalacion sobrevive y remove lo borra al final si restauro limpio."""
    settings(home).write_bytes(dump(USER_SETTINGS))
    kb(home).write_bytes(dump(USER_KB))
    original_s, original_k = settings(home).read_bytes(), kb(home).read_bytes()
    backups = fdir(home) / "backups"
    backups.mkdir(parents=True)
    for i in range(5):
        (backups / f"settings.json.20200101-000000-00000{i}.bak").write_text("{}")
    ajeno = backups / "settings.json.mio.bak"
    ajeno.write_text("mio")

    assert run("setup", "--keybinding").returncode == 0
    assert len(dated(backups, "settings.json")) == 3
    assert (backups / "settings.json.orig.bak").read_bytes() == original_s
    assert (backups / "keybindings.json.orig.bak").read_bytes() == original_k
    assert ajeno.read_text() == "mio"

    r = run("remove")
    assert r.returncode == 0, r.stdout + r.stderr
    assert not (backups / "settings.json.orig.bak").exists()
    assert not (backups / "keybindings.json.orig.bak").exists()
    assert ajeno.read_text() == "mio"


def test_setup_sin_cambios_no_hace_backup(run, home):
    """Fix 2: backup solo si algo cambia (re-correr setup no rota backups)."""
    settings(home).write_bytes(dump(USER_SETTINGS))
    assert run("setup").returncode == 0
    backups = fdir(home) / "backups"
    first = sorted(p.name for p in backups.iterdir())
    for _ in range(4):
        assert run("setup").returncode == 0
    assert sorted(p.name for p in backups.iterdir()) == first
    assert len(dated(backups, "settings.json")) == 1


# --- Fix 1: falla parcial -> se revierte y el original no se pierde ------------


def _assert_rollback_limpio(run, home, r, before_s, before_k):
    assert r.returncode == 1, r.stdout + r.stderr
    assert "se revirtio" in r.stdout
    assert "Traceback" not in r.stderr
    assert settings(home).read_bytes() == before_s
    assert kb(home).read_bytes() == before_k
    assert not (fdir(home) / "setup.json").exists()
    assert not (fdir(home) / "statusline.js").exists()
    assert not (fdir(home) / "backups" / "settings.json.orig.bak").exists()
    r2 = run("remove")
    assert r2.returncode == 0
    assert settings(home).read_bytes() == before_s


def test_keybindings_solo_lectura_revierte_settings(run, home):
    settings(home).write_bytes(dump(USER_SETTINGS))
    kb(home).write_bytes(dump(USER_KB))
    before_s, before_k = settings(home).read_bytes(), kb(home).read_bytes()
    r = run("setup", "--keybinding", env_extra={"FLUENCY_4D_FAIL_WRITE": "keybindings.json"})
    _assert_rollback_limpio(run, home, r, before_s, before_k)


@pytest.mark.skipif(os.name != "nt", reason="os.replace sobre un read-only solo falla en Windows")
def test_keybindings_read_only_real_windows(run, home):
    settings(home).write_bytes(dump(USER_SETTINGS))
    kb(home).write_bytes(dump(USER_KB))
    before_s, before_k = settings(home).read_bytes(), kb(home).read_bytes()
    os.chmod(kb(home), stat.S_IREAD)
    try:
        r = run("setup", "--keybinding")
        _assert_rollback_limpio(run, home, r, before_s, before_k)
    finally:
        os.chmod(kb(home), stat.S_IREAD | stat.S_IWRITE)


def test_falla_parcial_en_reinstalacion_conserva_registro_previo(run, home):
    settings(home).write_bytes(dump(USER_SETTINGS))
    kb(home).write_bytes(dump(USER_KB))
    before_s = settings(home).read_bytes()
    assert run("setup").returncode == 0
    rec1 = (fdir(home) / "setup.json").read_bytes()
    r = run("setup", "--keybinding", env_extra={"FLUENCY_4D_FAIL_WRITE": "keybindings.json"})
    assert r.returncode == 1
    assert (fdir(home) / "setup.json").read_bytes() == rec1
    assert run("remove").returncode == 0
    assert settings(home).read_bytes() == before_s


# --- Fix 3: remove byte a byte -------------------------------------------------

RAW_CRLF = (
    '{"model": "opus", "statusLine": null, "a": 1, "a": 2,\r\n'
    '  "env": {"FOO": "x", "CLAUDE_CODE_PLUGIN_DIRS": "/x/mods/panel-4d"}}'
)


def test_remove_vuelve_byte_a_byte_crlf_inline_duplicadas_null(run, home):
    settings(home).write_bytes(RAW_CRLF.encode("utf-8"))  # sin newline final
    r = run("setup")
    assert r.returncode == 0, r.stdout + r.stderr
    assert read(settings(home))["statusLine"]["type"] == "command"
    assert read(fdir(home) / "setup.json")["statusline"]["had_key"] is True
    assert run("remove").returncode == 0
    assert settings(home).read_bytes() == RAW_CRLF.encode("utf-8")


def test_remove_con_edicion_intermedia_revierte_minimo_y_conserva_crlf(run, home):
    settings(home).write_bytes(RAW_CRLF.encode("utf-8"))
    assert run("setup").returncode == 0
    raw = settings(home).read_bytes()
    assert b"\r\n" in raw  # setup tambien respeta CRLF
    settings(home).write_bytes(raw.replace(b'"opus"', b'"sonnet"'))
    assert run("remove").returncode == 0
    out = settings(home).read_bytes()
    assert b"\r\n" in out and b"\n" not in out.replace(b"\r\n", b"")
    data = json.loads(out)
    assert data["model"] == "sonnet"
    assert "statusLine" in data and data["statusLine"] is None  # had_key: vuelve a null
    assert data["env"]["CLAUDE_CODE_PLUGIN_DIRS"] == "/x/mods/panel-4d"


# --- Fix 4: lock ----------------------------------------------------------------


def test_lock_ocupado_aborta_sin_tocar(run, home):
    settings(home).write_bytes(dump(USER_SETTINGS))
    before = settings(home).read_bytes()
    fdir(home).mkdir()
    lock = fdir(home) / ".setup.lock"
    lock.write_text("otro")
    r = run("setup", env_extra={"FLUENCY_4D_LOCK_WAIT": "0.3"})
    assert r.returncode == 1
    assert "lock" in r.stdout
    assert settings(home).read_bytes() == before
    assert lock.read_text() == "otro"  # no libera un lock ajeno
    assert not (fdir(home) / "setup.json").exists()


def test_lock_huerfano_se_retoma_y_se_libera(run, home):
    fdir(home).mkdir()
    lock = fdir(home) / ".setup.lock"
    lock.write_text("muerto")
    viejo = time.time() - 120
    os.utime(lock, (viejo, viejo))
    r = run("setup", env_extra={"FLUENCY_4D_LOCK_WAIT": "0.3"})
    assert r.returncode == 0, r.stdout + r.stderr
    assert not lock.exists()
    assert run("remove").returncode == 0
    assert not lock.exists()


# --- Fix 5: `$` en la ruta ------------------------------------------------------


def _git_bash() -> str | None:
    exe = shutil.which("bash")
    if exe is None:
        return None
    low = exe.lower()
    if os.name == "nt" and ("system32" in low or "windowsapps" in low):
        return None  # bash de WSL: no entiende rutas C:/
    return exe


@pytest.mark.skipif(_git_bash() is None, reason="requiere bash (Git Bash en Windows)")
@pytest.mark.skipif(os.name == "nt", reason="en Windows esa ruta se rechaza (lista blanca)")
def test_home_con_dolar_el_comando_funciona_en_bash(tmp_path):
    home = tmp_path / "ho$me `x`"
    (home / ".claude").mkdir(parents=True)
    run = make_runner(home, tmp_path)
    r = run("setup")
    assert r.returncode == 0, r.stdout + r.stderr
    command = read(settings(home))["statusLine"]["command"]
    out = subprocess.run(
        [str(_git_bash()), "-c", command],
        input="{}",
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
    )
    assert "Cannot find module" not in out.stderr, out.stderr
    assert out.returncode == 0, out.stderr
    assert run("status").stdout.count("apunta a la copia fija") == 1


# --- Fix 6: _split_dirs -----------------------------------------------------------


def test_plugin_dirs_no_se_separa_por_coma(run, home):
    entrada = "/x/a,b/mods/panel-4d"  # UNA ruta con coma: es el mod panel-4d entero
    otra = f"/x/c,d{os.pathsep}/x/mods/panel-4d"
    settings(home).write_bytes(dump({"env": {"CLAUDE_CODE_PLUGIN_DIRS": entrada, "K": "v"}}))
    assert run("setup").returncode == 0
    assert "CLAUDE_CODE_PLUGIN_DIRS" not in read(settings(home))["env"]
    assert run("remove").returncode == 0
    settings(home).write_bytes(dump({"env": {"CLAUDE_CODE_PLUGIN_DIRS": otra}}))
    assert run("setup").returncode == 0
    assert read(settings(home))["env"]["CLAUDE_CODE_PLUGIN_DIRS"] == "/x/c,d"


# --- Fix 7: surrogate suelto --------------------------------------------------------


def test_surrogate_suelto_error_limpio_sin_tmp(run, home):
    raw = b'{"x": "\\ud800"}\n'
    settings(home).write_bytes(raw)
    r = run("setup")
    assert r.returncode == 1
    assert "ERROR" in r.stdout and "Traceback" not in r.stderr
    assert settings(home).read_bytes() == raw
    assert not list((home / ".claude").rglob("*.tmp"))
    assert not (fdir(home) / "setup.json").exists()


# --- Fix 8: status ------------------------------------------------------------------


def test_status_tolera_setup_json_corrupto(run, home):
    fdir(home).mkdir()
    (fdir(home) / "setup.json").write_text("{roto", encoding="utf-8")
    st = run("status")
    assert st.returncode == 0, st.stdout + st.stderr
    assert "CORRUPTO" in st.stdout


def test_status_sin_src_del_plugin_no_sugiere_setup(run, home, tmp_path):
    assert run("setup").returncode == 0
    st = run("status", "--plugin-root", str(tmp_path / "no-hay-plugin"))
    assert st.returncode == 0
    assert "NO encontrado" in st.stdout
    assert "SUGERENCIA" not in st.stdout


# --- Fix 10: version de Node --------------------------------------------------------


def fake_node(tmp_path: Path, version: str) -> str:
    if os.name == "nt":
        exe = tmp_path / "fakenode.cmd"
        exe.write_text(f"@echo {version}\r\n", encoding="ascii")
    else:
        exe = tmp_path / "fakenode"
        exe.write_text(f"#!/bin/sh\necho {version}\n", encoding="ascii")
        exe.chmod(0o755)
    return str(exe)


def test_node_viejo_aborta_con_mensaje(run, home, tmp_path):
    settings(home).write_bytes(dump(USER_SETTINGS))
    before = settings(home).read_bytes()
    r = run("setup", env_extra={"FLUENCY_4D_NODE_BIN": fake_node(tmp_path, "v16.20.2")})
    assert r.returncode == 1
    assert "v16.20.2" in r.stdout and ">= 18" in r.stdout
    assert settings(home).read_bytes() == before
    assert not fdir(home).exists()


# --- Fix 11: points_to_ours exacto ---------------------------------------------------


def test_wrapper_ajeno_que_menciona_la_ruta_no_es_nuestro(run, home):
    copy = (fdir(home) / "statusline.js").resolve().as_posix()
    wrapper = {"type": "command", "command": f"bash -c 'node {copy} | tee /tmp/x'"}
    settings(home).write_bytes(dump({"statusLine": wrapper}))
    before = settings(home).read_bytes()
    r = run("setup")
    assert r.returncode == 2, r.stdout
    assert settings(home).read_bytes() == before
    assert run("setup", "--force").returncode == 0
    assert run("remove").returncode == 0
    assert settings(home).read_bytes() == before


def test_comando_legacy_con_comillas_dobles_se_reconoce_y_migra(run, home):
    copy = (fdir(home) / "statusline.js").resolve().as_posix()
    settings(home).write_bytes(
        dump({"statusLine": {"type": "command", "command": f'node "{copy}"'}})
    )
    r = run("setup")
    assert r.returncode == 0, r.stdout
    assert read(settings(home))["statusLine"] == {
        "type": "command",
        "command": "node " + shlex.quote(copy),
        "refreshInterval": 5,
    }


# --- refreshInterval: setup limpio, migracion de 0.22.0 y valor del usuario -------------


def _ours(home: Path) -> dict:
    copy = (fdir(home) / "statusline.js").resolve().as_posix()
    return {"type": "command", "command": "node " + shlex.quote(copy)}


def test_setup_migra_statusline_propio_sin_refresh_y_remove_lo_revierte(run, home):
    # Instalacion de 0.22.0: statusLine nuestro sin refreshInterval y su setup.json.
    settings(home).write_bytes(dump(USER_SETTINGS))
    before = settings(home).read_bytes()
    assert run("setup").returncode == 0
    data = read(settings(home))
    del data["statusLine"]["refreshInterval"]
    settings(home).write_bytes(dump(data))
    r = run("setup")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "agregado refreshInterval 5" in r.stdout
    assert read(settings(home))["statusLine"] == {**_ours(home), "refreshInterval": 5}
    assert read(fdir(home) / "setup.json")["statusline"]["refresh_added"] is True
    assert run("setup").returncode == 0  # idempotente tras migrar
    assert run("remove").returncode == 0
    assert settings(home).read_bytes() == before


def test_setup_migra_statusline_propio_sin_registro(run, home):
    # statusLine nuestro sin refreshInterval y sin setup.json: se agrega y se registra.
    settings(home).write_bytes(dump({**USER_SETTINGS, "statusLine": _ours(home)}))
    before = settings(home).read_bytes()
    r = run("setup")
    assert r.returncode == 0, r.stdout + r.stderr
    assert read(settings(home))["statusLine"]["refreshInterval"] == 5
    rec = read(fdir(home) / "setup.json")
    assert rec["settings_doc"]["text"] == before.decode("utf-8")
    st = run("status")
    assert "refresco cada 5 s" in st.stdout


def test_refresh_personalizado_del_usuario_se_respeta(run, home):
    custom = {**_ours(home), "refreshInterval": 2}
    settings(home).write_bytes(dump({"model": "opus", "statusLine": custom}))
    before = settings(home).read_bytes()
    r = run("setup")
    assert r.returncode == 0, r.stdout + r.stderr
    assert settings(home).read_bytes() == before  # el refreshInterval 2 no se pisa
    assert "CONFLICTO" not in r.stdout
    st = run("status")
    assert "apunta a la copia fija" in st.stdout and "refresco cada 2 s" in st.stdout


def test_status_avisa_statusline_propio_sin_refresh(run, home):
    settings(home).write_bytes(dump({"statusLine": _ours(home)}))
    st = run("status")
    assert st.returncode == 0
    assert "sin refreshInterval" in st.stdout


# --- Fix 12: allowed-tools de la skill no autoriza --force -------------------------------


def _rule_matches(rule: str, command: str) -> bool:
    return re.fullmatch(".*".join(re.escape(p) for p in rule.split("*")), command) is not None


def test_skill_allowed_tools_no_cubre_force():
    text = (PLUGIN_DIR / "skills" / "statusline" / "SKILL.md").read_text(encoding="utf-8")
    line = next(ln for ln in text.splitlines() if ln.startswith("allowed-tools:"))
    rules = [r.replace("${CLAUDE_PLUGIN_ROOT}", "/p") for r in re.findall(r"Bash\(([^)]*)\)", line)]
    assert rules and not any(r.endswith(":*") for r in rules)
    assert not any("*" in r for r in rules)  # CWE-863: sin comodines, solo nuestro script
    base = 'uv run --script "/p/hooks/statusline_setup.py"'
    for ajeno in (
        'uv run --script "/evil/hooks/statusline_setup.py" setup',
        'uv run --script "https://x.example/statusline_setup.py" setup',
        'uv run --with evil --script "/p/hooks/statusline_setup.py" setup',
        'uv run --script "/p/hooks/statusline_setup.py.evil.py" setup',
    ):
        assert not any(_rule_matches(r, ajeno) for r in rules), ajeno
    for sub in (
        "setup",
        "setup --keybinding",
        "setup --copy-theme",
        "setup --keybinding --copy-theme",
        "remove",
        "status",
    ):
        assert any(_rule_matches(r, f"{base} {sub}") for r in rules), sub
    for sub in ("setup --force", "setup --keybinding --force", "setup --force --keybinding"):
        assert not any(_rule_matches(r, f"{base} {sub}") for r in rules), sub


def test_atajo_tecla_libre_se_agrega_y_remove_la_quita(run, home):
    kb(home).write_bytes(dump(USER_KB))
    before = kb(home).read_bytes()
    r = run("setup", "--keybinding")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "-> /panel" in r.stdout
    assert read(kb(home))["bindings"][0]["bindings"]["ctrl+x ctrl+p"] == "command:panel"
    assert read(fdir(home) / "setup.json")["keybinding"]["command"] == "command:panel"
    assert run("remove").returncode == 0
    assert kb(home).read_bytes() == before


def test_atajo_ya_en_command_panel_no_es_conflicto_ni_nuestro(run, home):
    # El caso real: el mod local panel-4d ya dejo ctrl+x ctrl+p -> command:panel.
    ya = {"bindings": [{"context": "Chat", "bindings": {"ctrl+x ctrl+p": "command:panel"}}]}
    kb(home).write_bytes(dump(ya))
    before = kb(home).read_bytes()
    r = run("setup", "--keybinding")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "ya estaba configurado" in r.stdout and "ocupado" not in r.stdout
    assert kb(home).read_bytes() == before
    assert "keybinding" not in read(fdir(home) / "setup.json")
    assert run("remove").returncode == 0
    assert kb(home).read_bytes() == before  # no es nuestro: remove no lo borra


def _instalacion_022(run, home) -> bytes:
    """Simula un setup de 0.22.0: atajo y registro con command:fluency-4d:panel.

    El string viejo sigue en los tests a proposito: cubre la compatibilidad con los
    setup.json que dejo 0.22.0 (ver LEGACY_KEYBINDING_CMD en statusline_setup.py).
    """
    kb(home).write_bytes(dump(USER_KB))
    before = kb(home).read_bytes()
    assert run("setup", "--keybinding").returncode == 0
    legacy = "command:fluency-4d:panel"
    data = read(kb(home))
    data["bindings"][0]["bindings"]["ctrl+x ctrl+p"] = legacy
    kb(home).write_bytes(dump(data))
    rec = read(fdir(home) / "setup.json")
    rec["keybinding"]["command"] = legacy
    (fdir(home) / "setup.json").write_bytes(dump(rec))
    return before


def test_remove_quita_el_atajo_de_022(run, home):
    before = _instalacion_022(run, home)
    r = run("remove")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "ya no es el de fluency-4d" not in r.stdout
    assert kb(home).read_bytes() == before


def test_setup_migra_el_atajo_de_022(run, home):
    before = _instalacion_022(run, home)
    r = run("setup")  # migra aunque no se pase --keybinding
    assert r.returncode == 0, r.stdout + r.stderr
    assert "migrado" in r.stdout
    assert read(kb(home))["bindings"][0]["bindings"]["ctrl+x ctrl+p"] == "command:panel"
    assert read(fdir(home) / "setup.json")["keybinding"]["command"] == "command:panel"
    assert run("setup", "--keybinding").returncode == 0  # idempotente tras migrar
    assert run("remove").returncode == 0
    assert kb(home).read_bytes() == before


def test_atajo_no_pisa_tecla_ocupada(run, home):
    ocupado = {"bindings": [{"context": "Chat", "bindings": {"ctrl+x ctrl+p": "command:otro"}}]}
    kb(home).write_bytes(dump(ocupado))
    before = kb(home).read_bytes()
    r = run("setup", "--keybinding")
    assert r.returncode == 0
    assert "ocupado" in r.stdout
    assert kb(home).read_bytes() == before
    assert "keybinding" not in read(fdir(home) / "setup.json")
    assert run("remove").returncode == 0
    assert kb(home).read_bytes() == before


def test_sin_node_aborta_con_mensaje(run, home):
    settings(home).write_bytes(dump(USER_SETTINGS))
    before = settings(home).read_bytes()
    r = run("setup", env_extra={"FLUENCY_4D_NODE_BIN": "node-que-no-existe-xyz"})
    assert r.returncode == 1
    assert "Node.js" in r.stdout and "nodejs.org" in r.stdout
    assert settings(home).read_bytes() == before
    assert not fdir(home).exists()


def test_status_detecta_copia_desactualizada(run, home):
    assert run("setup").returncode == 0
    (fdir(home) / "statusline.js").write_text("// viejo\n", encoding="utf-8")
    st = run("status")
    assert st.returncode == 0
    assert "DIFIERE" in st.stdout and "SUGERENCIA" in st.stdout


def test_plugin_dirs_ajeno_no_se_toca(run, home):
    otro = {"env": {"CLAUDE_CODE_PLUGIN_DIRS": "/x/mods/otro-mod"}}
    settings(home).write_bytes(dump(otro))
    assert run("setup").returncode == 0
    assert read(settings(home))["env"] == otro["env"]
    assert "plugin_dirs" not in read(fdir(home) / "setup.json")


def test_plugin_root_por_argumento_inexistente_falla(run, home, tmp_path):
    r = run("setup", "--plugin-root", str(tmp_path / "no-hay-plugin"))
    assert r.returncode == 1
    assert "no se encontro" in r.stdout


# --- Revision del port: CLAUDE_CONFIG_DIR, .orig.bak, copia, lock, rutas --------------


def _load_module(monkeypatch, home: Path):
    """Importa statusline_setup en el proceso (para inyectar carreras en el lock)."""
    import importlib.util
    import sys

    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    monkeypatch.delenv("CLAUDE_CONFIG_DIR", raising=False)
    monkeypatch.syspath_prepend(str(SCRIPT.parent))
    spec = importlib.util.spec_from_file_location("statusline_setup_t", SCRIPT)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, "statusline_setup_t", mod)
    spec.loader.exec_module(mod)
    return mod


def test_claude_config_dir_se_respeta_y_fluency4d_queda_en_home(run, home, tmp_path):
    cfg = tmp_path / "cfg"
    cfg.mkdir()
    (cfg / "settings.json").write_bytes(dump(USER_SETTINGS))
    before = (cfg / "settings.json").read_bytes()
    env = {"CLAUDE_CONFIG_DIR": str(cfg)}
    r = run("setup", "--keybinding", "--copy-theme", env_extra=env)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "fluency4d/statusline.js" in read(cfg / "settings.json")["statusLine"]["command"]
    assert (cfg / "keybindings.json").is_file()
    assert (cfg / "themes" / "templado.json").is_file()
    assert not settings(home).exists() and not kb(home).exists()
    assert not (home / ".claude" / "themes").exists()
    assert (fdir(home) / "statusline.js").is_file()  # copia, setup.json y flags en ~/.claude
    assert (fdir(home) / "setup.json").is_file()
    assert not (cfg / "fluency4d").exists()
    st = run("status", env_extra=env)
    assert "apunta a la copia fija" in st.stdout
    r = run("remove", env_extra=env)
    assert r.returncode == 0, r.stdout + r.stderr
    assert (cfg / "settings.json").read_bytes() == before
    assert not (cfg / "keybindings.json").exists()
    assert not (cfg / "themes" / "templado.json").exists()


def test_orig_bak_de_instalacion_vieja_no_se_pierde(run, home):
    settings(home).write_bytes(dump(USER_SETTINGS))
    original = settings(home).read_bytes()
    backups = fdir(home) / "backups"
    assert run("setup").returncode == 0
    s = read(settings(home))
    s["statusLine"] = {"type": "command", "command": "editado.sh"}
    settings(home).write_bytes(dump(s))
    r = run("remove")  # conflicto: conserva el .orig.bak y avisa
    assert "Se conserva" in r.stdout
    assert (backups / "settings.json.orig.bak").read_bytes() == original

    assert run("setup", "--force").returncode == 0
    pat = r"settings\.json\.orig\..+\.bak"
    viejos = [p for p in backups.iterdir() if re.fullmatch(pat, p.name)]
    assert len(viejos) == 1 and viejos[0].read_bytes() == original
    assert viejos[0] not in dated(backups, "settings.json")  # la poda no lo matchea
    assert read(fdir(home) / "setup.json")["orig_backups"] == ["settings.json"]
    assert run("remove").returncode == 0
    assert viejos[0].read_bytes() == original  # el respaldo de la instalacion vieja sigue
    assert not (backups / "settings.json.orig.bak").exists()  # el propio se borro


def test_remove_conserva_la_copia_si_el_statusline_no_se_revirtio(run, home):
    assert run("setup").returncode == 0
    copy = (fdir(home) / "statusline.js").resolve().as_posix()
    wrapper = {"type": "command", "command": f"bash -c 'node {copy} | tee /tmp/x'"}
    settings(home).write_bytes(dump({"statusLine": wrapper}))
    r = run("remove")
    assert r.returncode == 0, r.stdout + r.stderr
    assert (fdir(home) / "statusline.js").is_file()
    assert "copia fija" in r.stdout and "no se borra" in r.stdout


def test_remove_y_status_ignoran_rutas_del_registro(run, home, tmp_path):
    victima = tmp_path / "victima.txt"
    victima.write_text("no me borres", encoding="utf-8")
    assert run("setup").returncode == 0
    rec_path = fdir(home) / "setup.json"
    rec = read(rec_path)
    sha = __import__("hashlib").sha256(victima.read_bytes()).hexdigest()
    rec["copy"] = str(victima)
    rec["theme"] = {"path": str(victima), "sha256": sha}
    rec_path.write_text(json.dumps(rec), encoding="utf-8")
    st = run("status")
    assert str(victima) not in st.stdout
    assert run("remove").returncode == 0
    assert victima.read_text(encoding="utf-8") == "no me borres"
    assert not (fdir(home) / "statusline.js").exists()


@pytest.mark.skipif(os.name != "nt", reason="la lista blanca de caracteres es solo Windows")
def test_windows_rechaza_caracteres_peligrosos_en_la_ruta(tmp_path):
    for nombre in ("ho$me", "ho%me%", "o’neil", "co'mi", "ba`ck", "a(b)"):
        home = tmp_path / nombre
        (home / ".claude").mkdir(parents=True)
        r = make_runner(home, tmp_path)("setup")
        assert r.returncode == 1, (nombre, r.stdout)
        assert "caracter" in r.stdout and "Traceback" not in r.stderr
        assert not settings(home).exists()
    home = tmp_path / "canción ñandú"  # letras con acento: si
    (home / ".claude").mkdir(parents=True)
    r = make_runner(home, tmp_path)("setup")
    assert r.returncode == 0, r.stdout + r.stderr


def test_lock_huerfano_no_roba_un_lock_recien_tomado(monkeypatch, home):
    """TOCTOU: entre ver el lock viejo y tomarlo, otro proceso ya lo retomo."""
    mod = _load_module(monkeypatch, home)
    lock = fdir(home) / ".setup.lock"
    fdir(home).mkdir()
    lock.write_text("muerto", encoding="ascii")
    viejo = time.time() - 120
    os.utime(lock, (viejo, viejo))
    state = {"done": False}

    def gana_otro() -> None:
        if not state["done"]:
            state["done"] = True
            lock.unlink()
            lock.write_text("otro-proceso", encoding="ascii")  # mtime fresco

    real_unlink, real_replace, real_rename = Path.unlink, os.replace, os.rename

    def unlink(self, *a, **k):
        if Path(self) == lock:
            gana_otro()
        return real_unlink(self, *a, **k)

    def replace(src, dst, *a, **k):
        if Path(src) == lock:
            gana_otro()
        return real_replace(src, dst, *a, **k)

    def rename(src, dst, *a, **k):
        if Path(src) == lock:
            gana_otro()
        return real_rename(src, dst, *a, **k)

    monkeypatch.setattr(Path, "unlink", unlink)
    monkeypatch.setattr(os, "replace", replace)
    monkeypatch.setattr(os, "rename", rename)
    with pytest.raises(mod.SetupError):
        with mod.setup_lock(wait_s=0.3):
            pass
    assert lock.read_text(encoding="ascii") == "otro-proceso"


def test_lock_sobrevive_al_rmdir_del_duenio(monkeypatch, home):
    """El dueno borra fluency4d/ al terminar justo antes del os.open del que espera."""
    mod = _load_module(monkeypatch, home)
    real_open = os.open
    state = {"done": False}

    def fake_open(path, *a, **k):
        if not state["done"] and str(path).endswith(".setup.lock"):
            state["done"] = True
            shutil.rmtree(fdir(home))
        return real_open(path, *a, **k)

    monkeypatch.setattr(os, "open", fake_open)
    with mod.setup_lock(wait_s=0.3):
        assert (fdir(home) / ".setup.lock").is_file()
    assert not (fdir(home) / ".setup.lock").exists()
