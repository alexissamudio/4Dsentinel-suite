"""Testeo adversarial del fix de UnicodeDecodeError en load_state / bump_stats.

Tres capas:
  (a) propiedades con hypothesis (>= 500 ejemplos c/u) sobre hook_utils en proceso;
  (b) casos extremos parametrizados (encodings, truncado, NUL, tipos, no-archivo);
  (c) hooks reales por subprocess (fixture run_hook) con estado corrupto.

Todo lo persistente va a tmp_path: tempfile.tempdir (estado) y HOME/USERPROFILE
(stats.json). Los que antes eran xfail(strict=True) (RecursionError, _ts y
campos de tipo raro, stats.json con tipos raros, concurrencia de bump_stats) ya
pasan: read_json_safe, la validacion de _ts en load_state, state_num/str_list en
los hooks, _sanitize_stats y el lock + escritura atomica de bump_stats.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

REPO_ROOT = Path(__file__).resolve().parents[3]
HOOKS_DIR = REPO_ROOT / "plugins" / "fluency-4d" / "hooks"
sys.path.insert(0, str(HOOKS_DIR))

import hook_utils  # noqa: E402

EJEMPLOS = settings(
    max_examples=500,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow],
)

JSON_ESCALAR = (
    st.none()
    | st.booleans()
    | st.integers()
    | st.floats(allow_nan=False, allow_infinity=False)
    | st.text(max_size=8)
)
JSON_VALOR = st.recursive(
    JSON_ESCALAR,
    lambda hijos: (
        st.lists(hijos, max_size=4) | st.dictionaries(st.text(max_size=6), hijos, max_size=4)
    ),
    max_leaves=12,
)
NO_NUMERICO = JSON_VALOR.filter(lambda v: not isinstance(v, (int, float)) or isinstance(v, bool))


@pytest.fixture()
def state_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(hook_utils.tempfile, "tempdir", str(tmp_path))
    return tmp_path / "fluency4d"


@pytest.fixture()
def home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    h = tmp_path / "home"
    monkeypatch.setenv("HOME", str(h))
    monkeypatch.setenv("USERPROFILE", str(h))
    return h


def _stats_path(home: Path) -> Path:
    return home / ".claude" / "fluency4d" / "stats.json"


def _entry(home: Path, cwd: str) -> dict[str, Any]:
    stats = json.loads(_stats_path(home).read_text(encoding="utf-8"))
    assert isinstance(stats, dict)
    entry = stats[str(Path(cwd).resolve()).casefold()]
    assert isinstance(entry, dict)
    return entry


def _assert_roundtrip(key: str) -> None:
    hook_utils.save_state(key, {"marca": [1, "dos"]})
    got = hook_utils.load_state(key)
    assert got["marca"] == [1, "dos"] and isinstance(got["_ts"], float)


def _assert_bump_incrementa(home: Path, cwd: str) -> None:
    hook_utils.bump_stats(cwd, ["t"], True)
    e1 = _entry(home, cwd)
    hook_utils.bump_stats(cwd, ["t"], True)
    e2 = _entry(home, cwd)
    assert e2["sesiones"] == e1["sesiones"] + 1
    assert e2["temas"]["t"]["inyecciones"] == e1["temas"]["t"]["inyecciones"] + 1


# --- (a) propiedades hypothesis ---------------------------------------------


@EJEMPLOS
@given(contenido=st.binary(max_size=512))
def test_prop_bytes_arbitrarios_estado(state_dir: Path, contenido: bytes) -> None:
    path = hook_utils._state_path("kbin")
    path.write_bytes(contenido)
    got = hook_utils.load_state("kbin")
    assert isinstance(got, dict)
    _assert_roundtrip("kbin")


@EJEMPLOS
@given(contenido=st.binary(max_size=512))
def test_prop_bytes_arbitrarios_stats(home: Path, tmp_path: Path, contenido: bytes) -> None:
    path = _stats_path(home)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(contenido)
    _assert_bump_incrementa(home, str(tmp_path))


@EJEMPLOS
@given(valor=JSON_VALOR.filter(lambda v: not isinstance(v, dict)))
def test_prop_json_no_objeto_es_vacio(
    state_dir: Path, home: Path, tmp_path: Path, valor: Any
) -> None:
    texto = json.dumps(valor)
    hook_utils._state_path("knoobj").write_text(texto, encoding="utf-8")
    assert hook_utils.load_state("knoobj") == {}
    _stats_path(home).parent.mkdir(parents=True, exist_ok=True)
    _stats_path(home).write_text(texto, encoding="utf-8")
    _assert_bump_incrementa(home, str(tmp_path))


@EJEMPLOS
@given(
    estado=st.dictionaries(st.text(max_size=6).filter(lambda k: k != "_ts"), JSON_VALOR, max_size=5)
)
def test_prop_objeto_valido_vigente_se_preserva(state_dir: Path, estado: dict[str, Any]) -> None:
    estado = {**estado, "_ts": time.time()}
    hook_utils._state_path("kok").write_text(json.dumps(estado), encoding="utf-8")
    assert hook_utils.load_state("kok") == estado


@EJEMPLOS
@given(ts=NO_NUMERICO)
def test_prop_ts_de_tipo_raro_no_lanza(state_dir: Path, ts: Any) -> None:
    hook_utils._state_path("kts").write_text(json.dumps({"_ts": ts, "a": 1}), encoding="utf-8")
    assert isinstance(hook_utils.load_state("kts"), dict)


@EJEMPLOS
@given(ts=NO_NUMERICO)
def test_prop_stats_entrada_ajena_con_ts_raro(home: Path, tmp_path: Path, ts: Any) -> None:
    _stats_path(home).parent.mkdir(parents=True, exist_ok=True)
    _stats_path(home).write_text(json.dumps({"otro": {"_ts": ts}}), encoding="utf-8")
    _assert_bump_incrementa(home, str(tmp_path))


@EJEMPLOS
@given(sesiones=JSON_VALOR, temas=JSON_VALOR)
def test_prop_stats_entrada_propia_de_tipo_raro(
    home: Path, tmp_path: Path, sesiones: Any, temas: Any
) -> None:
    key = str(Path(tmp_path).resolve()).casefold()
    _stats_path(home).parent.mkdir(parents=True, exist_ok=True)
    _stats_path(home).write_text(
        json.dumps({key: {"_ts": time.time(), "sesiones": sesiones, "temas": temas}}),
        encoding="utf-8",
    )
    _assert_bump_incrementa(home, str(tmp_path))


# --- (b) casos extremos parametrizados -----------------------------------------

VALIDO = json.dumps(
    {"arranque_inyectado": True, "temas_inyectados": ["auth", "n" + chr(0xF1)], "_ts": 1.0e12}
)
ENCODINGS = {
    "bom_utf8": b"\xef\xbb\xbf" + VALIDO.encode("utf-8"),
    "utf16_le_bom": b"\xff\xfe" + VALIDO.encode("utf-16-le"),
    "utf16_be_bom": b"\xfe\xff" + VALIDO.encode("utf-16-be"),
    "utf32": VALIDO.encode("utf-32"),
    "nul_medio": VALIDO[:10].encode() + b"\x00" + VALIDO[10:].encode(),
    "nul_en_string": b'{"a": "x\x00y"}',
    "solo_nul": b"\x00" * 64,
    "latin1": ('{"a": "' + chr(0xF1) + chr(0xE1) + '"}').encode("latin-1"),
    "surrogate_cesu": b'{"a": "\xed\xa0\x80"}',
    "overlong": b'{"a": "\xc0\xaf"}',
    "vacio": b"",
    "espacios": b" \n\t\r ",
}


@pytest.mark.parametrize("nombre", sorted(ENCODINGS))
def test_encodings_raros_estado(state_dir: Path, nombre: str) -> None:
    hook_utils._state_path("kenc").write_bytes(ENCODINGS[nombre])
    assert hook_utils.load_state("kenc") == {}
    _assert_roundtrip("kenc")


@pytest.mark.parametrize("nombre", sorted(ENCODINGS))
def test_encodings_raros_stats(home: Path, tmp_path: Path, nombre: str) -> None:
    _stats_path(home).parent.mkdir(parents=True)
    _stats_path(home).write_bytes(ENCODINGS[nombre])
    _assert_bump_incrementa(home, str(tmp_path))


def test_bom_utf8_vigente_se_lee(state_dir: Path, home: Path, tmp_path: Path) -> None:
    """BOM UTF-8 (PowerShell 5) se tolera: el estado vigente se lee y stats.json
    con BOM conserva sus entradas."""
    estado = {"arranque_inyectado": True, "_ts": time.time()}
    hook_utils._state_path("kbom").write_bytes(b"\xef\xbb\xbf" + json.dumps(estado).encode())
    assert hook_utils.load_state("kbom") == estado
    _stats_path(home).parent.mkdir(parents=True)
    ajeno = {"ajeno": {"_ts": time.time(), "sesiones": 3, "temas": {}}}
    _stats_path(home).write_bytes(b"\xef\xbb\xbf" + json.dumps(ajeno).encode())
    _assert_bump_incrementa(home, str(tmp_path))
    final = json.loads(_stats_path(home).read_text(encoding="utf-8"))
    assert final["ajeno"]["sesiones"] == 3


def test_ts_en_el_futuro_vence(state_dir: Path) -> None:
    """Un _ts muy en el futuro no hace el estado eterno: cuenta como vencido."""
    hook_utils._state_path("kfut").write_text(json.dumps({"_ts": 1.0e12, "a": 1}))
    assert hook_utils.load_state("kfut") == {}


PROFUNDO = b"[" * 100_000 + b"]" * 100_000


def test_json_profundo_estado(state_dir: Path) -> None:
    hook_utils._state_path("kdeep").write_bytes(PROFUNDO)
    assert hook_utils.load_state("kdeep") == {}


def test_json_profundo_stats(home: Path, tmp_path: Path) -> None:
    _stats_path(home).parent.mkdir(parents=True)
    _stats_path(home).write_bytes(PROFUNDO)
    _assert_bump_incrementa(home, str(tmp_path))


def _corruptos(home: Path) -> list[Path]:
    return sorted(_stats_path(home).parent.glob("stats.json.corrupt-*"))


def test_stats_invalido_va_a_cuarentena(home: Path, tmp_path: Path) -> None:
    """stats.json invalido NO se pisa sin rastro: se renombra a .corrupt-<ts>
    con el contenido original, y solo quedan las STATS_CORRUPT_KEEP mas nuevas."""
    sp = _stats_path(home)
    sp.parent.mkdir(parents=True)
    for i in range(hook_utils.STATS_CORRUPT_KEEP + 2):
        sp.write_bytes(b'{"roto": ' + str(i).encode())
        hook_utils.bump_stats(str(tmp_path), ["t"], True)
        assert isinstance(json.loads(sp.read_text(encoding="utf-8")), dict)
    copias = _corruptos(home)
    assert len(copias) == hook_utils.STATS_CORRUPT_KEEP
    assert copias[-1].read_bytes() == b'{"roto": ' + str(i).encode()


def test_stats_vacio_no_va_a_cuarentena(home: Path, tmp_path: Path) -> None:
    sp = _stats_path(home)
    sp.parent.mkdir(parents=True)
    sp.write_bytes(b"  \n")
    hook_utils.bump_stats(str(tmp_path), ["t"], True)
    assert _corruptos(home) == []


def test_stats_entradas_saneadas_conservan_ajenas(home: Path, tmp_path: Path) -> None:
    sp = _stats_path(home)
    sp.parent.mkdir(parents=True)
    now = time.time()
    raw = {
        "ok": {"_ts": now, "sesiones": 4, "temas": {"a": {"inyecciones": 2}}, "extra": 1},
        "raro": {"_ts": "s", "sesiones": "abc", "temas": {"t": 5, "u": {"inyecciones": None}}},
        "lista": [1, 2],
        "viejo": {"_ts": now - 100 * 24 * 3600, "sesiones": 1},
    }
    sp.write_text(json.dumps(raw), encoding="utf-8")
    hook_utils.bump_stats(str(tmp_path), ["t"], True)
    final = json.loads(sp.read_text(encoding="utf-8"))
    assert final["ok"]["sesiones"] == 4 and final["ok"]["extra"] == 1
    assert final["ok"]["temas"] == {"a": {"inyecciones": 2}}
    assert final["raro"]["sesiones"] == 0
    assert final["raro"]["temas"] == {"u": {"inyecciones": 0}}
    assert "lista" not in final and "viejo" not in final
    assert _corruptos(home) == []


def test_stats_lock_ocupado_saltea_sin_tocar(home: Path, tmp_path: Path) -> None:
    """Lock tomado por otro (fresco): se saltea el incremento sin escribir."""
    sp = _stats_path(home)
    sp.parent.mkdir(parents=True)
    sp.write_text(json.dumps({"ajeno": {"_ts": time.time()}}), encoding="utf-8")
    antes = sp.read_bytes()
    lock = sp.parent / "stats.json.lock"
    lock.write_text("otro", encoding="utf-8")
    t0 = time.monotonic()
    hook_utils.bump_stats(str(tmp_path), ["t"], True)
    assert time.monotonic() - t0 < 1.0
    assert sp.read_bytes() == antes and lock.exists()


def test_stats_lock_huerfano_se_descarta(home: Path, tmp_path: Path) -> None:
    sp = _stats_path(home)
    sp.parent.mkdir(parents=True)
    lock = sp.parent / "stats.json.lock"
    lock.write_text("muerto", encoding="utf-8")
    viejo = time.time() - hook_utils.STATS_LOCK_STALE_SECONDS - 5
    os.utime(lock, (viejo, viejo))
    hook_utils.bump_stats(str(tmp_path), ["t"], True)
    assert _entry(home, str(tmp_path))["sesiones"] == 1
    assert not lock.exists()  # se libero al terminar


@pytest.mark.parametrize("corte", range(len(VALIDO)))
def test_json_truncado_en_cada_posicion(
    state_dir: Path, home: Path, tmp_path: Path, corte: int
) -> None:
    data = VALIDO.encode("utf-8")[:corte]
    hook_utils._state_path("ktrunc").write_bytes(data)
    assert hook_utils.load_state("ktrunc") == {}
    _assert_roundtrip("ktrunc")
    _stats_path(home).parent.mkdir(parents=True, exist_ok=True)
    _stats_path(home).write_bytes(data)
    _assert_bump_incrementa(home, str(tmp_path))


@pytest.mark.parametrize(
    "texto", ["[]", "[1, 2]", "0", "-1.5", "null", "true", '"str"', "1e999", "NaN"]
)
def test_json_valido_de_tipo_incorrecto(
    state_dir: Path, home: Path, tmp_path: Path, texto: str
) -> None:
    hook_utils._state_path("ktipo").write_text(texto, encoding="utf-8")
    assert hook_utils.load_state("ktipo") == {}
    _assert_roundtrip("ktipo")
    _stats_path(home).parent.mkdir(parents=True, exist_ok=True)
    _stats_path(home).write_text(texto, encoding="utf-8")
    _assert_bump_incrementa(home, str(tmp_path))


def test_estado_es_un_directorio(state_dir: Path) -> None:
    path = hook_utils._state_path("kdir")
    path.mkdir()
    assert hook_utils.load_state("kdir") == {}
    hook_utils.save_state("kdir", {"a": 1})  # no puede pisar el dir: no-op silencioso
    assert hook_utils.load_state("kdir") == {}
    assert path.is_dir()
    assert [p.name for p in state_dir.iterdir()] == ["kdir.json"]  # sin .tmp huerfano


def test_stats_es_un_directorio(home: Path, tmp_path: Path) -> None:
    _stats_path(home).mkdir(parents=True)
    hook_utils.bump_stats(str(tmp_path), ["t"], True)  # no lanza
    assert _stats_path(home).is_dir()


def test_estado_symlink_roto(state_dir: Path, tmp_path: Path) -> None:
    path = hook_utils._state_path("klink")
    destino = tmp_path / "no_existe" / "destino.json"
    try:
        path.symlink_to(destino)
    except (OSError, NotImplementedError):
        pytest.skip("sin permiso para crear symlinks")
    assert hook_utils.load_state("klink") == {}
    hook_utils.save_state("klink", {"a": 1})
    assert path.is_symlink()  # atomic_write resuelve el link: escribe en el destino
    assert hook_utils.load_state("klink")["a"] == 1


def test_stats_symlink_roto(home: Path, tmp_path: Path) -> None:
    path = _stats_path(home)
    path.parent.mkdir(parents=True)
    try:
        path.symlink_to(tmp_path / "nada" / "stats.json")
    except (OSError, NotImplementedError):
        pytest.skip("sin permiso para crear symlinks")
    hook_utils.bump_stats(str(tmp_path), ["t"], True)  # no lanza


@pytest.mark.skipif(
    os.name != "posix" or getattr(os, "geteuid", lambda: 0)() == 0, reason="POSIX no-root"
)
def test_sin_permiso_de_lectura(state_dir: Path, home: Path, tmp_path: Path) -> None:
    path = hook_utils._state_path("kperm")
    path.write_text(VALIDO, encoding="utf-8")
    path.chmod(0)
    assert hook_utils.load_state("kperm") == {}
    _assert_roundtrip("kperm")  # replace sobre el archivo 0o000 funciona (dir 0o700)
    sp = _stats_path(home)
    sp.parent.mkdir(parents=True)
    sp.write_text("{}", encoding="utf-8")
    sp.chmod(0)
    try:
        hook_utils.bump_stats(str(tmp_path), ["t"], True)  # no lanza
    finally:
        sp.chmod(0o600)


# --- concurrencia: 20 procesos bumpeando a la vez -----------------------------

N_PROCS = 20
N_BUMPS = 10
SCRIPT_CONC = """
import sys, time
sys.path.insert(0, sys.argv[1])
import hook_utils
start = float(sys.argv[3])
while time.time() < start:
    time.sleep(0.001)
for _ in range(int(sys.argv[4])):
    hook_utils.bump_stats(sys.argv[2], ["t"], True)
"""


def _ronda_concurrente(tmp_path: Path, ronda: int) -> dict[str, Any]:
    """20 procesos x 10 bump_stats a la vez + un lector que muestrea stats.json."""
    base = tmp_path / f"r{ronda}"
    home = base / "home"
    env = {**os.environ, "HOME": str(home), "USERPROFILE": str(home), "HOOK_DEBUG": "1"}
    env.update({"TMPDIR": str(base), "TEMP": str(base), "TMP": str(base)})
    cwd = str(base / "proj")
    sp = _stats_path(home)
    sp.parent.mkdir(parents=True)
    sp.write_text(json.dumps({"ajeno": {"_ts": time.time(), "sesiones": 7}}), encoding="utf-8")
    start = time.time() + 3.0
    procs = [
        subprocess.Popen(
            [sys.executable, "-c", SCRIPT_CONC, str(HOOKS_DIR), cwd, str(start), str(N_BUMPS)],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        for _ in range(N_PROCS)
    ]
    lecturas_invalidas = 0
    while any(p.poll() is None for p in procs):
        try:
            json.loads(sp.read_bytes())
        except OSError:
            pass
        except ValueError:
            lecturas_invalidas += 1
    salidas = [p.communicate(timeout=120) for p in procs]
    final_txt = sp.read_bytes()
    try:
        final: Any = json.loads(final_txt)
    except ValueError:
        final = None
    entry = final.get(str(Path(cwd).resolve()).casefold(), {}) if isinstance(final, dict) else {}
    return {
        "rc": [p.returncode for p in procs],
        "tracebacks": [e for _, e in salidas if b"Traceback" in e],
        "noop": sum(e.count(b"stats no disponibles") for _, e in salidas),
        "invalidas": lecturas_invalidas,
        "final": final,
        "final_txt": final_txt,
        "sesiones": entry.get("sesiones", 0),
        "ajeno_vivo": isinstance(final, dict) and "ajeno" in final,
        "corruptos": sorted(p.name for p in sp.parent.glob("stats.json.corrupt-*")),
    }


def test_concurrencia_bump_stats_no_crashea(
    tmp_path: Path, record_property: Any, capsys: pytest.CaptureFixture[str]
) -> None:
    """DATO, no bug: cuenta incrementos perdidos. Solo exige que nadie crashee."""
    r = _ronda_concurrente(tmp_path, 0)
    assert r["rc"] == [0] * N_PROCS and r["tracebacks"] == []
    total = N_PROCS * N_BUMPS
    record_property("bump_perdidos", total - r["sesiones"])
    with capsys.disabled():
        print(
            f"\n[concurrencia] {r['sesiones']}/{total} incrementos, "
            f"{total - r['sesiones']} perdidos, {r['noop']} no-op, "
            f"lecturas invalidas={r['invalidas']}, final valido={r['final'] is not None}, "
            f"entrada ajena sobrevive={r['ajeno_vivo']}"
        )


def test_concurrencia_bump_stats_nunca_corrompe(tmp_path: Path) -> None:
    """Invariante (no depende del timing): con escritores concurrentes, stats.json
    es SIEMPRE JSON valido (en cada lectura y al final), NUNCA pierde la entrada de
    otro proyecto y nunca se manda a cuarentena (.corrupt-*). Los incrementos
    perdidos (lock no conseguido en 200 ms) son aceptables y no se asertan,
    salvo que al menos uno tiene que haber entrado."""
    for ronda in range(5):
        r = _ronda_concurrente(tmp_path, ronda)
        assert r["rc"] == [0] * N_PROCS and r["tracebacks"] == []
        assert r["invalidas"] == 0, f"ronda {ronda}: {r['invalidas']} lecturas invalidas"
        assert isinstance(r["final"], dict), r["final_txt"][-200:]
        assert r["ajeno_vivo"], "la entrada de otro proyecto se borro"
        assert r["final"]["ajeno"]["sesiones"] == 7
        assert 1 <= r["sesiones"] <= N_PROCS * N_BUMPS
        assert r["corruptos"] == [], r["corruptos"]


# --- (c) hooks reales por subprocess con estado corrupto -----------------------


def _key(session: str, suffix: str) -> str:
    return "sid-" + hashlib.sha256(session.encode()).hexdigest()[:16] + suffix


def _plantar(tmp_path: Path, session: str, suffix: str, contenido: bytes | None) -> Path:
    path = tmp_path / "fluency4d" / f"{_key(session, suffix)}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    if contenido is None:
        path.mkdir()
    else:
        path.write_bytes(contenido)
    return path


def _hooks(
    project: Path, s: str
) -> dict[str, tuple[str, str, dict[str, Any], dict[str, str], str]]:
    return {
        "plan_calibrator": (
            "plan_calibrator.py",
            "-calib",
            {"session_id": s, "permission_mode": "plan", "prompt": "x", "cwd": str(project)},
            {},
            "RIGUROSO",
        ),
        "memory_checkpoint": (
            "memory_checkpoint.py",
            "-ckpt",
            {
                "session_id": s,
                "cwd": str(project),
                "permission_mode": "default",
                "context_window": {"used_percentage": 70},
            },
            {},
            "estado-sesion.md",
        ),
        "suite_playbook": (
            "suite_playbook.py",
            "-playbook",
            {"session_id": s, "permission_mode": "default", "prompt": "quiero entender este repo"},
            {},
            "indexar",
        ),
        "discernment_gate": (
            "discernment_gate.py",
            "-gate",
            {"session_id": s, "cwd": str(project)},
            {"FLUENCY_4D_STRICT": "1"},
            '"decision": "block"',
        ),
        "bridge_router": (
            "bridge_router.py",
            "-bridge",
            {"session_id": s, "cwd": str(project), "prompt": "hola", "permission_mode": "default"},
            {},
            "lecciones.md",
        ),
    }


CORRUPTOS: dict[str, bytes] = {
    "bytes_invalidos": b'{"arranque_inyectado": true, "x": "\xff\xfe"}',
    "bom_utf8": b"\xef\xbb\xbf" + json.dumps({"_ts": 1.0e12, "gate_bloqueado": True}).encode(),
    "utf16": json.dumps({"_ts": 1.0e12}).encode("utf-16"),
    "truncado": b'{"_ts": 17000000',
    "nul": b'{"a":\x00 1}',
    "lista": b"[1, 2, 3]",
    "null": b"null",
    "binario": bytes(range(256)),
}


@pytest.mark.parametrize("corrupcion", sorted(CORRUPTOS))
@pytest.mark.parametrize(
    "hook",
    ["plan_calibrator", "memory_checkpoint", "suite_playbook", "discernment_gate", "bridge_router"],
)
def test_hook_real_se_recupera(
    run_hook: Any, project: Path, tmp_path: Path, state_of: Any, hook: str, corrupcion: str
) -> None:
    (project / ".claude" / "docs" / "lecciones.md").write_text("# L", encoding="utf-8")
    s = f"{hook}-{corrupcion}"
    nombre, suffix, payload, env, marca = _hooks(project, s)[hook]
    _plantar(tmp_path, s, suffix, CORRUPTOS[corrupcion])
    primera = run_hook(nombre, payload, env)  # run_hook ya exige exit 0
    assert marca in primera  # estado corrupto == estado vacio: el hook dispara
    assert isinstance(state_of(s, suffix), dict)  # y lo reescribio valido
    segunda = run_hook(nombre, payload, env)
    assert marca not in segunda  # dedup vuelve a funcionar


@pytest.mark.parametrize("hook", ["plan_calibrator", "suite_playbook"])
def test_hook_real_estado_es_directorio(
    run_hook: Any, project: Path, tmp_path: Path, hook: str
) -> None:
    s = f"{hook}-dir"
    nombre, suffix, payload, env, marca = _hooks(project, s)[hook]
    _plantar(tmp_path, s, suffix, None)
    assert marca in run_hook(nombre, payload, env)
    assert marca in run_hook(nombre, payload, env)  # sin persistencia: re-dispara, sin crash


@pytest.mark.parametrize(
    "hook",
    ["plan_calibrator", "memory_checkpoint", "suite_playbook", "discernment_gate", "bridge_router"],
)
def test_hook_real_ts_string(run_hook: Any, project: Path, tmp_path: Path, hook: str) -> None:
    (project / ".claude" / "docs" / "lecciones.md").write_text("# L", encoding="utf-8")
    s = f"{hook}-ts"
    nombre, suffix, payload, env, marca = _hooks(project, s)[hook]
    _plantar(tmp_path, s, suffix, b'{"_ts": "x"}')
    # El estado con tipo raro cuenta como vacio: dispara YA en la primera
    # llamada, lo reescribe valido y la segunda queda deduplicada.
    assert marca in run_hook(nombre, payload, env)
    assert marca not in run_hook(nombre, payload, env)


CAMPO_RARO: dict[str, dict[str, Any]] = {
    "memory_checkpoint": {"last_seen_pct": "abc"},
    "suite_playbook": {"nudges_dados": 5},
    "bridge_router": {"temas_inyectados": 5},
}


@pytest.mark.parametrize("hook", sorted(CAMPO_RARO))
def test_hook_real_campo_de_tipo_raro(
    run_hook: Any, project: Path, tmp_path: Path, hook: str
) -> None:
    (project / ".claude" / "docs" / "lecciones.md").write_text("# L", encoding="utf-8")
    s = f"{hook}-campo"
    nombre, suffix, payload, env, marca = _hooks(project, s)[hook]
    _plantar(tmp_path, s, suffix, json.dumps({"_ts": time.time(), **CAMPO_RARO[hook]}).encode())
    assert marca in run_hook(nombre, payload, env)
    assert marca not in run_hook(nombre, payload, env)
