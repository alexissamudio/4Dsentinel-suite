"""Testeo adversarial del fix de bridge_router.tema_lines (bridges.json no-objeto).

Contrato atacado: con CUALQUIER contenido en .claude/docs/bridges.json el hook
nunca crashea, sale con exit 0, emite JSON valido o nada, la inyeccion de
arranque (lecciones.md) sigue apareciendo, y una entrada valida rodeada de
basura se sigue inyectando.

Tres capas:
(a) hypothesis in-process (main() real con stdin/stdout/temp/home aislados),
    >= 500 ejemplos por propiedad;
(b) casos extremos parametrizados (in-process);
(c) el hook real por subprocess (run_hook) con archivos corruptos en disco.

Los .py son ASCII puro: los caracteres no-ASCII se escriben con escapes.
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import sys
import tempfile
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from conftest import HOOKS_DIR
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

sys.path.insert(0, str(HOOKS_DIR))

import bridge_router  # noqa: E402
import hook_utils  # noqa: E402

HOOK = "bridge_router.py"
LECCIONES = "lecciones.md"
VALID_TEMA = "zzvalido"
VALID_FILE = ".claude/docs/zzvalido.md"
VALID_KW = "zzpalabraclave"
FUZZ = settings(
    max_examples=500,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.data_too_large],
)


# --- harness in-process --------------------------------------------------------


@contextlib.contextmanager
def isolated(root: Path) -> Iterator[None]:
    """Aisla temp (estado) y home (stats) del proceso de tests durante main()."""
    old_tempdir = tempfile.tempdir
    old_env = {k: os.environ.get(k) for k in ("HOME", "USERPROFILE", "HOOK_DEBUG")}
    (root / "tmp").mkdir(exist_ok=True)
    (root / "home").mkdir(exist_ok=True)
    tempfile.tempdir = str(root / "tmp")
    os.environ["HOME"] = str(root / "home")
    os.environ["USERPROFILE"] = str(root / "home")
    os.environ.pop("HOOK_DEBUG", None)
    try:
        yield
    finally:
        tempfile.tempdir = old_tempdir
        for k, v in old_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def run_inproc(root: Path, project: Path, prompt: Any, session: str = "s") -> str:
    """Corre bridge_router.main() en proceso; devuelve stdout (strip)."""
    payload = {"prompt": prompt, "cwd": str(project), "session_id": session}
    buf = io.StringIO()
    old_stdin = sys.stdin
    sys.stdin = io.StringIO(json.dumps(payload))
    try:
        with isolated(root), contextlib.redirect_stdout(buf):
            bridge_router.main()
    finally:
        sys.stdin = old_stdin
    return buf.getvalue().strip()


def make_project(root: Path, bridges_text: str | bytes | None) -> Path:
    project = root / "proyecto"
    docs = project / ".claude" / "docs"
    docs.mkdir(parents=True, exist_ok=True)
    (docs / LECCIONES).write_text("# L", encoding="utf-8")
    if bridges_text is not None:
        target = docs / "bridges.json"
        if isinstance(bridges_text, bytes):
            target.write_bytes(bridges_text)
        else:
            target.write_text(bridges_text, encoding="utf-8")
    return project


def context_of(out: str) -> str:
    """Valida la forma de la salida: vacia o un unico JSON de UserPromptSubmit."""
    if not out:
        return ""
    obj = json.loads(out)  # debe ser JSON valido
    assert isinstance(obj, dict)
    if not obj:
        return ""
    hso = obj["hookSpecificOutput"]
    assert hso["hookEventName"] == "UserPromptSubmit"
    ctx = hso["additionalContext"]
    assert isinstance(ctx, str)
    return ctx


def assert_arranque(out: str) -> str:
    ctx = context_of(out)
    assert LECCIONES in ctx, f"se perdio la inyeccion de arranque: {out!r}"
    assert ctx.count("(inyectado por fluency-4d") == 1
    return ctx


def fresh_root() -> tempfile.TemporaryDirectory[str]:
    return tempfile.TemporaryDirectory(prefix="f4d-insane-")


VALID_ENTRY = {"tema": VALID_TEMA, "archivo": VALID_FILE, "keywords": [VALID_KW]}

# --- estrategias -----------------------------------------------------------------

json_scalar = (
    st.none()
    | st.booleans()
    | st.integers()
    | st.floats(allow_nan=True, allow_infinity=True)
    | st.text(max_size=30)
)
json_value = st.recursive(
    json_scalar,
    lambda children: (
        st.lists(children, max_size=6) | st.dictionaries(st.text(max_size=10), children, max_size=6)
    ),
    max_leaves=40,
)
# Valores "con forma de puente" para atacar las claves que el router lee.
field_value = json_value | st.text(max_size=20) | st.lists(json_value, max_size=4)
garbage_entry = json_value | st.fixed_dictionaries(
    {},
    optional={
        "tema": field_value.filter(lambda v: v != VALID_TEMA),
        "archivo": field_value
        | st.sampled_from(
            [
                "../fuera.md",
                "/etc/passwd",
                "C:\\x.md",
                "~/x.md",
                "\\\\host\\x",
                "a/../../b.md",
                "inexistente/nunca.md",
                "a\nb.md",
                "",
                " ",
            ]
        ),
        "keywords": field_value,
        "rutas": field_value,
        "relaciones": field_value
        | st.lists(
            st.fixed_dictionaries({}, optional={"tema": field_value, "verbo": field_value}),
            max_size=4,
        ),
    },
)


# --- (a) fuzzing -------------------------------------------------------------------


@FUZZ
@given(value=json_value)
def test_fuzz_json_arbitrario_no_crashea_y_mantiene_arranque(value: Any) -> None:
    with fresh_root() as d:
        root = Path(d)
        project = make_project(root, json.dumps(value))
        # tema_lines nunca lanza (propiedad mas fuerte que "hook_main lo traga").
        bridge_router.tema_lines(project, "auth login " + VALID_KW, {})
        assert_arranque(run_inproc(root, project, "hola " + VALID_KW))


@FUZZ
@given(top=json_value, temas_raw=json_value)
def test_fuzz_bridges_con_temas_arbitrario(top: Any, temas_raw: Any) -> None:
    doc = top if isinstance(top, dict) else {}
    doc = {**doc, "temas": temas_raw}
    with fresh_root() as d:
        root = Path(d)
        project = make_project(root, json.dumps(doc))
        bridge_router.tema_lines(project, VALID_KW, {})
        assert_arranque(run_inproc(root, project, VALID_KW))


@FUZZ
@given(
    before=st.lists(garbage_entry, max_size=8),
    after=st.lists(garbage_entry, max_size=8),
)
def test_fuzz_entrada_valida_entre_basura_se_inyecta(before: list[Any], after: list[Any]) -> None:
    doc = {"version": 1, "temas": [*before, VALID_ENTRY, *after]}
    with fresh_root() as d:
        root = Path(d)
        project = make_project(root, json.dumps(doc))
        ctx = assert_arranque(run_inproc(root, project, "explicame " + VALID_KW))
        directas = ctx.count("LEE ese archivo ANTES")
        # O se inyecto el valido, o (muy raro) dos temas de basura llenaron el cap.
        assert VALID_FILE in ctx or directas == bridge_router.MAX_TEMAS_POR_PROMPT, ctx


@FUZZ
@given(prompt=st.text(min_size=1, max_size=300))
def test_fuzz_prompt_arbitrario(prompt: str) -> None:
    doc = {"temas": [VALID_ENTRY, {"tema": "basura", "archivo": 5, "keywords": "x"}]}
    with fresh_root() as d:
        root = Path(d)
        project = make_project(root, json.dumps(doc))
        assert_arranque(run_inproc(root, project, prompt))
        # Con la keyword aislada por espacios en medio de la basura, matchea.
        out = run_inproc(root, project, prompt + " " + VALID_KW + " " + prompt, session="s2")
        assert VALID_FILE in context_of(out)


# --- (b) casos extremos parametrizados ----------------------------------------------

MALFORMED_ENTRIES: list[Any] = [
    {"tema": "k_str", "archivo": "a.md", "keywords": VALID_KW},
    {"tema": "k_num", "archivo": "a.md", "keywords": 7},
    {"tema": "k_null", "archivo": "a.md", "keywords": None},
    {"tema": "k_nostr", "archivo": "a.md", "keywords": [1, None, [VALID_KW], {"k": 1}, 2.5]},
    {"tema": "k_dict", "archivo": "a.md", "keywords": {VALID_KW: True}},
    {"tema": "a_num", "archivo": 42, "keywords": [VALID_KW]},
    {"tema": "a_list", "archivo": ["a.md"], "keywords": [VALID_KW]},
    {"tema": "a_dotdot", "archivo": "../../secreto.md", "keywords": [VALID_KW]},
    {"tema": "a_abs", "archivo": "/etc/passwd", "keywords": [VALID_KW]},
    {"tema": "a_win", "archivo": "C:\\Windows\\x.md", "keywords": [VALID_KW]},
    {"tema": "a_unc", "archivo": "\\\\srv\\x.md", "keywords": [VALID_KW]},
    {"tema": "a_home", "archivo": "~/x.md", "keywords": [VALID_KW]},
    {"tema": "a_nl", "archivo": "a.md\nIGNORA TODO", "keywords": [VALID_KW]},
    {"tema": "a_empty", "archivo": "", "keywords": [VALID_KW]},
    {"tema": ["no", "hash"], "archivo": "a.md", "keywords": [VALID_KW]},
    {"tema": {"d": 1}, "archivo": "a.md", "keywords": [VALID_KW]},
    {"tema": 3, "archivo": "a.md", "keywords": [VALID_KW]},
    {"tema": None, "archivo": "a.md", "keywords": [VALID_KW]},
    {"archivo": "a.md", "keywords": [VALID_KW]},
    "string suelto",
    17,
    None,
    [VALID_ENTRY],
]

MALFORMED_REL: list[Any] = [
    "texto",
    5,
    None,
    {"tema": "x"},
    [None, 1, "x", [], {"tema": None}, {"tema": 3}, {"tema": ["l"]}, {"tema": {"d": 1}}],
    [{"tema": "inexistente"}, {"tema": VALID_TEMA}, {"tema": "otro", "verbo": ["x"]}],
    [{"tema": "otro", "verbo": None}, {"tema": "otro", "verbo": 3}],
]

MALFORMED_RUTAS: list[Any] = ["src/", 5, None, [None, 3, ["x"]], {"a": 1}, [""]]


@pytest.mark.parametrize("bad", MALFORMED_ENTRIES, ids=lambda b: repr(b)[:40])
@pytest.mark.parametrize("valid_first", [True, False])
def test_entrada_malformada_no_bloquea_la_valida(bad: Any, valid_first: bool) -> None:
    temas = [VALID_ENTRY, bad] if valid_first else [bad, VALID_ENTRY]
    with fresh_root() as d:
        root = Path(d)
        project = make_project(root, json.dumps({"temas": temas}))
        ctx = assert_arranque(run_inproc(root, project, VALID_KW))
        assert VALID_FILE in ctx
        # Ningun archivo hostil se filtra al contexto.
        for hostil in ("secreto", "passwd", "Windows", "srv", "IGNORA", "~/"):
            assert hostil not in ctx


@pytest.mark.parametrize("rel", MALFORMED_REL, ids=lambda r: repr(r)[:40])
@pytest.mark.parametrize("rutas", MALFORMED_RUTAS, ids=lambda r: repr(r)[:20])
def test_relaciones_y_rutas_malformadas(rel: Any, rutas: Any) -> None:
    temas = [
        {**VALID_ENTRY, "relaciones": rel, "rutas": rutas},
        {"tema": "otro", "archivo": ".claude/docs/otro.md", "keywords": ["nadamatchea"]},
    ]
    with fresh_root() as d:
        root = Path(d)
        project = make_project(root, json.dumps({"temas": temas}))
        ctx = assert_arranque(run_inproc(root, project, VALID_KW))
        assert VALID_FILE in ctx
        assert ctx.count("Tema relacionado") <= bridge_router.MAX_RELACIONADOS


@pytest.mark.parametrize(
    "top",
    [
        [],
        [VALID_ENTRY],
        "texto",
        0,
        -1.5,
        True,
        False,
        None,
        {},
        {"temas": None},
        {"temas": "x"},
        {"temas": {"0": VALID_ENTRY}},
        {"temas": 3},
        {"version": 1},
    ],
    ids=repr,
)
def test_top_level_no_objeto_o_sin_temas(top: Any) -> None:
    with fresh_root() as d:
        root = Path(d)
        project = make_project(root, json.dumps(top))
        assert bridge_router.tema_lines(project, VALID_KW, {}) == []
        ctx = assert_arranque(run_inproc(root, project, VALID_KW))
        assert VALID_FILE not in ctx


@pytest.mark.parametrize(
    "prompt",
    [
        "\x00",
        "\x00" + VALID_KW,
        "\u202e" + VALID_KW,
        VALID_KW.upper(),
        "\ud800 " + VALID_KW,
        "\r\n\t" + VALID_KW + "\x1b[31m",
        "a" * 200_000 + " " + VALID_KW,
    ],
    ids=lambda p: repr(p)[:20],
)
def test_prompts_raros(prompt: str) -> None:
    with fresh_root() as d:
        root = Path(d)
        project = make_project(root, json.dumps({"temas": [VALID_ENTRY]}))
        assert_arranque(run_inproc(root, project, prompt))


@pytest.mark.parametrize("prompt", [123, ["auth"], {"a": 1}, [VALID_KW], True], ids=repr)
def test_prompt_no_string_mantiene_arranque(prompt: Any) -> None:
    """Prompt no-string: cuenta como "" (sin keywords) pero el arranque sigue."""
    with fresh_root() as d:
        root = Path(d)
        project = make_project(root, json.dumps({"temas": [VALID_ENTRY]}))
        ctx = assert_arranque(run_inproc(root, project, prompt))
        assert VALID_FILE not in ctx


# --- (c) hook real por subprocess, archivos corruptos en disco --------------------


def _big_bridges() -> bytes:
    temas = [
        {"tema": f"t{i}", "archivo": f".claude/docs/t{i}.md", "keywords": [f"kw{i}x", 5, None]}
        for i in range(60_000)
    ]
    temas.append(VALID_ENTRY)
    data = json.dumps({"temas": temas}).encode()
    assert len(data) >= 5 * 1024 * 1024, len(data)
    return data


VALID_DOC = json.dumps({"temas": [VALID_ENTRY]})
CORRUPTOS: dict[str, bytes] = {
    "vacio": b"",
    "solo_espacios": b"   \n\t ",
    "bytes_invalidos": b"\xff\xfe\x80\x81{\x00",
    "utf16": VALID_DOC.encode("utf-16"),
    "utf16_sin_bom": VALID_DOC.encode("utf-16-le"),
    "truncado": VALID_DOC.encode()[:-3],
    "nul_en_medio": b'{"temas": [\x00]}',
    "lista_top": b"[1, 2, 3]",
    "string_top": b'"hola"',
    "null_top": b"null",
    "numero_top": b"1e999",
    "nan": b"NaN",
    "anidado_1000": b'{"temas": ' + b"[" * 1000 + b"]" * 1000 + b"}",
    "anidado_dict_1000": b'{"temas": [' + b'{"a":' * 1000 + b"1" + b"}" * 1000 + b"]}",
    "basura_5mb": b"{" * (5 * 1024 * 1024),
}


def _write_raw(project: Path, data: bytes) -> None:
    (project / ".claude" / "docs" / "bridges.json").write_bytes(data)


def _with_lecciones(project: Path) -> None:
    (project / ".claude" / "docs" / LECCIONES).write_text("# L", encoding="utf-8")


def _payload(project: Path, prompt: str = VALID_KW) -> dict[str, str]:
    return {"prompt": prompt, "cwd": str(project), "session_id": "sx"}


@pytest.mark.parametrize("name", sorted(CORRUPTOS))
def test_subprocess_archivo_corrupto(run_hook, project, name: str) -> None:  # type: ignore[no-untyped-def]
    _with_lecciones(project)
    _write_raw(project, CORRUPTOS[name])
    out = run_hook(HOOK, _payload(project))  # run_hook ya exige exit 0
    assert_arranque(out)
    # doc_drift con el mismo archivo tampoco crashea.
    drift = run_hook(
        "doc_drift.py",
        {
            "cwd": str(project),
            "tool_input": {"file_path": str(project / "src" / "a.py")},
            "session_id": "sx",
        },
    )
    assert drift == "" or isinstance(json.loads(drift), dict)


def test_subprocess_bridges_es_directorio(run_hook, project) -> None:  # type: ignore[no-untyped-def]
    _with_lecciones(project)
    (project / ".claude" / "docs" / "bridges.json").mkdir()
    assert_arranque(run_hook(HOOK, _payload(project)))


def test_subprocess_5mb_valido_con_entrada_al_final(run_hook, project) -> None:  # type: ignore[no-untyped-def]
    """Un bridges.json de 5 MB supera MAX_BRIDGES_BYTES: se ignora entero (la
    entrada valida del final NO se inyecta), pero el arranque si."""
    _with_lecciones(project)
    _write_raw(project, _big_bridges())
    ctx = assert_arranque(run_hook(HOOK, _payload(project)))
    assert VALID_FILE not in ctx


def test_5mb_entra_holgado_en_el_timeout_del_hook() -> None:
    """Antes: ~70us por tema -> 60k temas tardaban > 5 s (timeout del hook) y se
    perdia tambien el arranque. Ahora el tope de tamano lo corta sin leerlo."""
    with fresh_root() as d:
        root = Path(d)
        project = make_project(root, _big_bridges().decode())
        t0 = time.perf_counter()
        lines = bridge_router.tema_lines(project, VALID_KW, {})
        elapsed = time.perf_counter() - t0
        assert lines == []  # > MAX_BRIDGES_BYTES: sin puentes
        # 1 s in-process deja margen para el arranque de uv dentro de los 5 s.
        assert elapsed < 1.0, f"tema_lines tardo {elapsed:.2f}s con 5 MB"
        assert_arranque(run_inproc(root, project, VALID_KW))


def _temas_relleno(n: int) -> list[dict[str, Any]]:
    return [
        {"tema": f"t{i}", "archivo": f".claude/docs/t{i}.md", "keywords": [f"kw{i}x"]}
        for i in range(n)
    ]


def test_tope_de_temas_ignora_los_que_sobran() -> None:
    """Debajo de MAX_BRIDGES_BYTES pero con mas de MAX_BRIDGES_TEMAS temas: solo
    cuentan los primeros MAX_BRIDGES_TEMAS (cota del costo de tema_lines)."""
    tope = hook_utils.MAX_BRIDGES_TEMAS
    with fresh_root() as d:
        root = Path(d)
        detras = {"tema": "detras", "archivo": ".claude/docs/detras.md", "keywords": ["zzdetras"]}
        doc = {"temas": [*_temas_relleno(tope - 1), VALID_ENTRY, detras]}
        data = json.dumps(doc)
        assert len(data.encode()) < hook_utils.MAX_BRIDGES_BYTES
        project = make_project(root, data)
        lines = bridge_router.tema_lines(project, VALID_KW + " zzdetras", {})
        joined = "\n".join(lines)
        assert VALID_FILE in joined  # posicion tope-1: entra
        assert "detras.md" not in joined  # posicion tope: se ignora
        t0 = time.perf_counter()
        bridge_router.tema_lines(project, "nada", {})
        assert time.perf_counter() - t0 < 1.0


def test_bridges_justo_debajo_del_tope_de_bytes_se_lee() -> None:
    with fresh_root() as d:
        root = Path(d)
        head = '{"temas": ' + json.dumps([VALID_ENTRY]) + ', "q": "'
        tope = hook_utils.MAX_BRIDGES_BYTES
        data = head + "z" * (tope - len(head) - 2) + '"}'
        assert len(data.encode()) == tope
        project = make_project(root, data)
        assert any(VALID_FILE in ln for ln in bridge_router.tema_lines(project, VALID_KW, {}))
        project2 = make_project(root, data[:-1] + " }")  # 1 byte de mas
        assert bridge_router.tema_lines(project2, VALID_KW, {}) == []


@pytest.mark.parametrize("depth", [20_000, 200_000])
def test_subprocess_anidado_profundo_recursion(run_hook, project, depth: int) -> None:  # type: ignore[no-untyped-def]
    _with_lecciones(project)
    _write_raw(project, b'{"temas": ' + b"[" * depth + b"]" * depth + b"}")
    assert_arranque(run_hook(HOOK, _payload(project)))


def test_subprocess_bom_valido_inyecta(run_hook, project) -> None:  # type: ignore[no-untyped-def]
    _with_lecciones(project)
    _write_raw(project, b"\xef\xbb\xbf" + VALID_DOC.encode())
    ctx = assert_arranque(run_hook(HOOK, _payload(project)))
    assert VALID_FILE in ctx


def test_subprocess_bom_no_rompe_arranque(run_hook, project) -> None:  # type: ignore[no-untyped-def]
    _with_lecciones(project)
    _write_raw(project, b"\xef\xbb\xbf" + VALID_DOC.encode())
    assert_arranque(run_hook(HOOK, _payload(project)))


def test_subprocess_basura_y_valida_mismo_archivo(run_hook, project) -> None:  # type: ignore[no-untyped-def]
    _with_lecciones(project)
    doc = {"temas": [*MALFORMED_ENTRIES, VALID_ENTRY], "version": "x", "extra": [None]}
    _write_raw(project, json.dumps(doc).encode())
    ctx = assert_arranque(run_hook(HOOK, _payload(project, "hola " + VALID_KW)))
    assert VALID_FILE in ctx


@pytest.mark.parametrize(
    "state",
    [
        {"_ts": "ayer", "arranque_inyectado": False},
        {"_ts": None},
        {"temas_inyectados": 5},
        {"temas_inyectados": [[1], {"a": 1}]},
    ],
    ids=repr,
)
def test_subprocess_estado_corrupto(run_hook, project, tmp_path, state) -> None:  # type: ignore[no-untyped-def]
    """Estado de sesion corrupto en disco (lo escribe el propio hook, pero puede
    quedar asi por otra version o edicion manual)."""
    import hashlib

    _with_lecciones(project)
    _write_raw(project, VALID_DOC.encode())
    key = "sid-" + hashlib.sha256(b"sx").hexdigest()[:16] + "-bridge"
    sdir = tmp_path / "fluency4d"
    sdir.mkdir(exist_ok=True)
    if "_ts" not in state:
        state = {**state, "_ts": time.time()}
    (sdir / f"{key}.json").write_text(json.dumps(state), encoding="utf-8")
    assert_arranque(run_hook(HOOK, _payload(project)))
