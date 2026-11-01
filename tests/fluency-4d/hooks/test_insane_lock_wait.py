"""Testeo adversarial de lock_wait_seconds() / FLUENCY_4D_LOCK_WAIT (statusline_setup.py).

Bug original: un FLUENCY_4D_LOCK_WAIT no numerico tiraba ValueError sin capturar.
Fix: lock_wait_seconds() devuelve el default (65 s) si el valor no es un numero
finito >= 0. Tres capas:
  (a) hypothesis (>= 500 ejemplos por propiedad) contra la funcion importada;
  (b) extremos parametrizados;
  (c) el script real por subprocess (status/setup, lock tomado por otro proceso).

Aislamiento: HOME/USERPROFILE/TMP* -> tmp_path; el entorno del modulo se reemplaza
por un dict (permite surrogates y NUL, que un env real no admite).
"""

from __future__ import annotations

import importlib.util
import math
import os
import shutil
import subprocess
import sys
import textwrap
import time
from pathlib import Path
from types import ModuleType
from typing import Any
from unittest import mock

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "plugins" / "fluency-4d" / "hooks" / "statusline_setup.py"
ENV_KEY = "FLUENCY_4D_LOCK_WAIT"
DEFAULT = 65.0
NEEDS_NODE = pytest.mark.skipif(shutil.which("node") is None, reason="requiere node en PATH")
HSET = settings(
    max_examples=600,
    deadline=None,
    derandomize=True,
    suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow],
)


@pytest.fixture()
def home(tmp_path: Path) -> Path:
    h = tmp_path / "home"
    (h / ".claude").mkdir(parents=True)
    return h


@pytest.fixture()
def mod(monkeypatch: pytest.MonkeyPatch, home: Path) -> ModuleType:
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    monkeypatch.delenv("CLAUDE_CONFIG_DIR", raising=False)
    monkeypatch.delenv(ENV_KEY, raising=False)
    monkeypatch.syspath_prepend(str(SCRIPT.parent))
    spec = importlib.util.spec_from_file_location("statusline_setup_insane", SCRIPT)
    assert spec is not None and spec.loader is not None
    m = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, "statusline_setup_insane", m)
    spec.loader.exec_module(m)
    return m


def call_with(m: ModuleType, raw: str | None) -> Any:
    env: dict[str, str] = {} if raw is None else {ENV_KEY: raw}
    with mock.patch.object(m.os, "environ", env):
        return m.lock_wait_seconds()


def oracle(raw: str) -> float:
    try:
        v = float(raw)
    except ValueError:
        return DEFAULT
    return v if math.isfinite(v) and v >= 0 else DEFAULT


def assert_sane(out: Any) -> None:
    assert type(out) is float
    assert math.isfinite(out)
    assert out >= 0


# --- (a) Propiedades hypothesis -------------------------------------------------

ANY_CHAR = st.characters(blacklist_categories=())  # incluye Cs (surrogates) y Cc


@HSET
@given(st.text(alphabet=ANY_CHAR, max_size=64))
def test_p1_cualquier_texto_nunca_lanza_y_sigue_el_oraculo(mod: ModuleType, raw: str) -> None:
    out = call_with(mod, raw)
    assert_sane(out)
    assert out == oracle(raw)


@HSET
@given(st.floats(min_value=0, allow_nan=False, allow_infinity=False))
def test_p2_finito_no_negativo_se_respeta_exacto(mod: ModuleType, x: float) -> None:
    for raw in (repr(x), f"  {x!r}\t\n", f"{x:e}"):
        out = call_with(mod, raw)
        assert_sane(out)
        assert out == float(raw)
    assert call_with(mod, repr(x)) == x


@HSET
@given(st.floats(max_value=-1e-300, allow_nan=False, allow_infinity=False))
def test_p3_negativos_dan_default(mod: ModuleType, x: float) -> None:
    assert call_with(mod, repr(x)) == DEFAULT


@HSET
@given(
    st.sampled_from(["nan", "NaN", "-nan", "inf", "-inf", "Infinity", "+INFINITY", "1e400"]),
    st.text(alphabet=" \t\n\r\x0b\x0c\u2003\u3000", max_size=4),
)
def test_p4_no_finitos_con_espacios_unicode_dan_default(
    mod: ModuleType, core: str, pad: str
) -> None:
    assert call_with(mod, pad + core + pad) == DEFAULT


@HSET
@given(st.text(alphabet=st.characters(categories=["Nd"]), min_size=1, max_size=12))
def test_p5_digitos_unicode_cualquier_script(mod: ModuleType, digits: str) -> None:
    out = call_with(mod, digits)
    assert_sane(out)
    assert out == oracle(digits)


# --- (b) Extremos parametrizados ------------------------------------------------

CASES: list[tuple[str, float]] = [
    ("abc", DEFAULT),
    ("", DEFAULT),
    ("  5  ", 5.0),
    ("-0", 0.0),
    ("-5", DEFAULT),
    ("1e999", DEFAULT),
    ("1e-999", 0.0),
    ("NaN", DEFAULT),
    ("nan", DEFAULT),
    ("inf", DEFAULT),
    ("-inf", DEFAULT),
    ("Infinity", DEFAULT),
    ("0x10", DEFAULT),
    ("1_000", 1000.0),
    ("\u0663", 3.0),  # digito arabe-indico 3
    ("\uff15", 5.0),  # 5 de ancho completo
    ("5\x00", DEFAULT),
    ("9" * 5000, DEFAULT),  # float -> inf
    ("0." + "0" * 5000 + "1", 0.0),
    ("0", 0.0),
    ("1e308", 1e308),
    ("1.7976931348623157e308", sys.float_info.max),
    ("5e-324", 5e-324),
    ("\ud800", DEFAULT),
    ("--5", DEFAULT),
    ("5 5", DEFAULT),
    ("1,5", DEFAULT),
]


@pytest.mark.parametrize(("raw", "expected"), CASES, ids=[repr(c[0])[:20] for c in CASES])
def test_extremos(mod: ModuleType, raw: str, expected: float) -> None:
    out = call_with(mod, raw)
    assert_sane(out)
    assert out == expected


def test_sin_variable_es_default(mod: ModuleType) -> None:
    assert call_with(mod, None) == DEFAULT == mod.LOCK_STALE_S + 5


def test_menos_cero_devuelve_cero_negativo_inocuo(mod: ModuleType) -> None:
    """'-0' -> -0.0: pasa '>= 0' y es inocuo (deadline = monotonic() + -0.0)."""
    out = call_with(mod, "-0")
    assert out == 0.0 and math.copysign(1.0, out) == -1.0


def test_env_real_con_valores_extremos(mod: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    """Mismo comportamiento leyendo del os.environ real (no del dict falso)."""
    for raw, expected in CASES:
        if "\x00" in raw or "\ud800" in raw:
            continue  # un env real no admite NUL ni surrogates sueltos
        monkeypatch.setenv(ENV_KEY, raw)
        assert mod.lock_wait_seconds() == expected, raw


def test_1e308_no_cuelga_porque_el_lock_vence_a_los_60s(mod: ModuleType, home: Path) -> None:
    """Punto 3: con LOCK_WAIT=1e308 y un lock ajeno 'vivo', la espera queda acotada
    por LOCK_STALE_S (el mtime no se refresca -> se retoma como huerfano), no por 1e308.
    Se simula un lock de 59.5 s de antiguedad: debe tomarse en ~0.5-1.5 s."""
    lock = home / ".claude" / "fluency4d" / ".setup.lock"
    lock.parent.mkdir(parents=True)
    lock.write_text("otro-proceso", encoding="ascii")
    old = time.time() - (mod.LOCK_STALE_S - 0.5)
    os.utime(lock, (old, old))
    t0 = time.monotonic()
    with mock.patch.dict(os.environ, {ENV_KEY: "1e308"}):
        with mod.setup_lock():
            elapsed = time.monotonic() - t0
            assert lock.read_text(encoding="ascii") != "otro-proceso"
    assert elapsed < 10
    assert not lock.exists()


def test_wait_cero_con_lock_ajeno_falla_inmediato(mod: ModuleType, home: Path) -> None:
    lock = home / ".claude" / "fluency4d" / ".setup.lock"
    lock.parent.mkdir(parents=True)
    lock.write_text("otro-proceso", encoding="ascii")
    t0 = time.monotonic()
    with mock.patch.dict(os.environ, {ENV_KEY: "0"}):
        with pytest.raises(mod.SetupError):
            with mod.setup_lock():
                pass
    assert time.monotonic() - t0 < 2
    assert lock.read_text(encoding="ascii") == "otro-proceso"


# --- (c) Script real por subprocess ---------------------------------------------


def base_env(home: Path, tmp: Path, extra: dict[str, str]) -> dict[str, str]:
    env = {
        **os.environ,
        "HOME": str(home),
        "USERPROFILE": str(home),
        "TMPDIR": str(tmp),
        "TEMP": str(tmp),
        "TMP": str(tmp),
        "PYTHONUTF8": "1",
    }
    for k in ("CLAUDE_PLUGIN_ROOT", "FLUENCY_4D_NODE_BIN", "CLAUDE_CONFIG_DIR", ENV_KEY):
        env.pop(k, None)
    env.update(extra)
    return env


def run_script(
    home: Path, tmp: Path, *args: str, extra: dict[str, str]
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["uv", "run", "--script", str(SCRIPT), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=base_env(home, tmp, extra),
        cwd=REPO_ROOT,
        timeout=120,
    )


INVALID = ["abc", "", "nan", "-inf", "1e999", "0x10", "-5", "\u0663\u0663x", "9" * 5000]


@NEEDS_NODE
@pytest.mark.parametrize("cmd", ["status", "setup"])
@pytest.mark.parametrize("raw", INVALID, ids=[repr(r)[:12] for r in INVALID])
def test_cli_valor_invalido_sale_limpio(home: Path, tmp_path: Path, cmd: str, raw: str) -> None:
    r = run_script(home, tmp_path, cmd, extra={ENV_KEY: raw})
    assert r.returncode == 0, r.stdout + r.stderr
    assert "Traceback" not in r.stdout + r.stderr
    assert not (home / ".claude" / "fluency4d" / ".setup.lock").exists()


HOLDER = textwrap.dedent(
    """
    import sys, time
    sys.path.insert(0, sys.argv[1])
    import statusline_setup as m
    with m.setup_lock(wait_s=5):
        print("ready", flush=True)
        time.sleep(float(sys.argv[2]))
    """
)


@NEEDS_NODE
@pytest.mark.parametrize("raw", ["0", "abc"])
def test_cli_lock_de_otro_proceso_falla_rapido(home: Path, tmp_path: Path, raw: str) -> None:
    """Lock tomado por un proceso vivo. LOCK_WAIT=0 -> falla limpio y rapido.
    'abc' -> default 65 s: se usa solo para confirmar que NO lanza ValueError; el
    holder suelta a los 3 s y el setup debe terminar OK (espera acotada)."""
    holder_script = tmp_path / "holder.py"
    holder_script.write_text(HOLDER, encoding="ascii")
    hold_s = "40" if raw == "0" else "3"
    env = base_env(home, tmp_path, {})
    holder = subprocess.Popen(
        [sys.executable, str(holder_script), str(SCRIPT.parent), hold_s],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
    )
    try:
        assert holder.stdout is not None
        assert holder.stdout.readline().strip() == "ready"
        lock = home / ".claude" / "fluency4d" / ".setup.lock"
        token = lock.read_text(encoding="ascii")
        t0 = time.monotonic()
        r = run_script(home, tmp_path, "setup", extra={ENV_KEY: raw})
        elapsed = time.monotonic() - t0
        out = r.stdout + r.stderr
        assert "Traceback" not in out
        if raw == "0":
            assert r.returncode == 1, out
            assert "lock" in r.stdout
            assert elapsed < 30
            assert lock.read_text(encoding="ascii") == token  # no libero el ajeno
            assert holder.poll() is None
        else:
            assert r.returncode == 0, out
            assert elapsed < 60
    finally:
        holder.kill()
        holder.wait(timeout=10)
