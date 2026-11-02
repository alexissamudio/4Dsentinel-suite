"""Testeo adversarial del fix de exclusion `.claude` de doc_drift (por SEGMENTO).

Bug original: `".claude/" in rel_posix + "/"` excluia tambien `my.claude/x`.
Fix: `".claude" in rel_posix.split("/")` sobre la ruta YA resuelta y casefolded.

Requisito (spec, no caracterizacion): una edicion se excluye si y solo si el archivo
REAL queda dentro de un directorio `.claude` del proyecto (en cualquier nivel). En
Windows eso incluye las variantes que el filesystem trata como el mismo directorio:
mayusculas (`.CLAUDE`, NTFS no distingue) y el nombre corto 8.3 (`CLAUDE~1`).

Tres capas:
  (a) Hypothesis in-process: se corre el `main()` REAL de doc_drift con stdin/estado/
      salida parcheados y `prefix_matches` forzado a True, asi el UNICO motivo de
      silencio es la exclusion (o "fuera del proyecto"). Se compara contra un oraculo
      independiente que normaliza la ruta a mano (sin pathlib).
  (b) Casos extremos parametrizados (mismo runner in-process).
  (c) El hook real por subprocess (fixture `run_hook`, HOME/USERPROFILE/TEMP aislados).

Semilla pineada (derandomize=True) para reproducibilidad en CI.
"""

from __future__ import annotations

import io
import json
import os
import sys
from collections.abc import Iterator
from contextlib import contextmanager, redirect_stdout
from pathlib import Path
from typing import Any
from unittest import mock

import pytest
from conftest import fuzz_examples, write_bridges
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

HOOKS_DIR = Path(__file__).resolve().parents[3] / "plugins" / "fluency-4d" / "hooks"
sys.path.insert(0, str(HOOKS_DIR))

import doc_drift  # noqa: E402

HOOK = "doc_drift.py"
IS_NT = os.name == "nt"

# Nombre de proyecto que ningun generador produce: un `..` que sube por encima de la
# raiz no puede "volver a entrar" y el oraculo puede tratarlo como fuera del proyecto.
PROJECT_NAME = "proj_zq9_drift"

SPECIAL_SEGMENTS = [
    ".claude",
    "my.claude",
    ".claude-backup",
    ".Claude",
    ".CLAUDE",
    ".claude~",
    ".claude.md",
    "claude",
    "x.claude",
    "..",
    ".",
    "",
    "src",
    "auth",
    "a b",
    " .claude",
    "\u00f1and\u00fa",
    "\u65e5\u672c",
    "\uff0e\uff43\uff4c\uff41\uff55\uff44\uff45",  # fullwidth: NO es .claude
]
if IS_NT:
    SPECIAL_SEGMENTS.append("CLAUDE~1")
else:
    # En POSIX el backslash es un caracter mas del nombre: `.claude\x` NO es un dir.
    SPECIAL_SEGMENTS += [".claude\\x", "x\\.claude"]

_RESERVED_NT = {"CON", "PRN", "AUX", "NUL"} | {
    f"{p}{i}" for p in ("COM", "LPT") for i in "123456789"
}


def _segment_ok(seg: str) -> bool:
    """Filtra segmentos que el OS no puede representar (no es lo que se testea)."""
    if "/" in seg or "\x00" in seg:
        return False
    if not IS_NT:
        return True
    if seg in ("", ".", ".."):
        return True
    if any(c in seg for c in '\\<>:"|?*') or any(ord(c) < 32 for c in seg):
        return False
    if seg.endswith((".", " ")):  # Win32 los recorta: semantica aparte (capa b)
        return False
    base = seg.split(".")[0].strip().upper()
    if base in _RESERVED_NT or base[:3] in ("COM", "LPT") and len(base) == 4:
        return False
    if "~" in seg and seg.casefold() != "claude~1":
        return False  # otros nombres cortos 8.3 dependen del contenido del dir
    return True


_random_seg = st.text(
    alphabet=st.characters(
        blacklist_categories=("Cs", "Cc"), blacklist_characters='/\\<>:"|?*~\x00'
    ),
    min_size=1,
    max_size=10,
).filter(_segment_ok)
_segment = st.one_of(st.sampled_from(SPECIAL_SEGMENTS), _random_seg)
_segments = st.lists(_segment, min_size=1, max_size=7)


def oracle(segs: list[str], short_name_live: bool) -> str:
    """Oraculo independiente: 'outside' | 'excluded' | 'warn'.

    Normaliza a mano: '' y '.' no cuentan, '..' sube (por encima de la raiz = afuera).
    Excluido si algun segmento final ES `.claude` para el filesystem: comparacion
    case-insensitive (el hook casefoldea; en NTFS es el mismo dir) y, en Windows con
    8.3 activo, `CLAUDE~1` en la raiz es el nombre corto del `.claude` del proyecto.
    """
    stack: list[str] = []
    for s in segs:
        if s in ("", "."):
            continue
        if s == "..":
            if not stack:
                return "outside"
            stack.pop()
            continue
        if short_name_live and not stack and s.casefold() == "claude~1":
            s = ".claude"
        stack.append(s)
    if any(s.casefold() == ".claude" for s in stack):
        return "excluded"
    return "warn"


@pytest.fixture(scope="module")
def proj(tmp_path_factory: pytest.TempPathFactory) -> Path:
    root = tmp_path_factory.mktemp("insane") / PROJECT_NAME
    (root / ".claude" / "docs").mkdir(parents=True)
    write_bridges(
        root,
        data={"temas": [{"tema": "all", "archivo": ".claude/docs/all.md", "rutas": ["x"]}]},
    )
    return root.resolve()


def _short_name_live(proj: Path) -> bool:
    return IS_NT and (proj / "CLAUDE~1").is_dir()


@contextmanager
def _isolated() -> Iterator[list[str]]:
    """Parchea stdin/estado/salida de doc_drift; prefix_matches siempre True."""
    calls: list[str] = []
    with (
        mock.patch.object(doc_drift, "prefix_matches", lambda *_a: True),
        mock.patch.object(doc_drift, "load_state", lambda _k: {}),
        mock.patch.object(doc_drift, "save_state", lambda _k, _s: None),
        mock.patch.object(doc_drift, "output_context", lambda _e, t: calls.append(t)),
    ):
        yield calls


def run_inproc(cwd: str, file_path: Any, key: str = "file_path") -> bool:
    """Corre el main() real de doc_drift; True si avisa."""
    data = {"cwd": cwd, "session_id": "s", "tool_input": {key: file_path}}
    with (
        _isolated() as calls,
        mock.patch.object(doc_drift, "read_stdin_safe", lambda: json.dumps(data)),
        redirect_stdout(io.StringIO()),
    ):
        doc_drift.main()
    return bool(calls)


def _join(segs: list[str], seps: list[str]) -> str:
    out = segs[0]
    for i, s in enumerate(segs[1:]):
        out += seps[i % len(seps)] + s
    return out


_SEPS = ["/", "\\"] if IS_NT else ["/"]
_HYP = settings(
    max_examples=fuzz_examples(600),
    deadline=None,
    derandomize=True,
    suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.filter_too_much],
)


# --------------------------------------------------------------------------- (a)


@_HYP
@given(
    segs=_segments,
    seps=st.lists(st.sampled_from(_SEPS), min_size=1, max_size=4),
    absolute=st.booleans(),
    dot_prefix=st.booleans(),
)
def test_p1_excluido_sii_segmento_claude(
    proj: Path, segs: list[str], seps: list[str], absolute: bool, dot_prefix: bool
) -> None:
    """P1: avisa <=> dentro del proyecto y ningun segmento es `.claude` (oraculo)."""
    if not absolute and segs[0] == "":
        segs = ["."] + segs  # un '' inicial haria la ruta absoluta (raiz): otro caso
    rel = _join(segs, seps)
    if dot_prefix:
        rel = "." + seps[0] + rel
    raw = str(proj) + seps[-1] + rel if absolute else rel
    expected = oracle(segs, _short_name_live(proj))
    got = run_inproc(str(proj), raw)
    assert got == (expected == "warn"), (raw, expected)


@_HYP
@given(segs=_segments.filter(lambda s: "" not in s))
def test_p2_invariante_al_separador(proj: Path, segs: list[str]) -> None:
    """P2 (Windows): `/`, `\\` y mezclados dan el mismo veredicto."""
    if not IS_NT:
        pytest.skip("en POSIX el backslash no es separador")
    verdicts = {
        run_inproc(str(proj), str(proj) + "\\" + _join(segs, seps))
        for seps in (["/"], ["\\"], ["/", "\\"], ["\\", "/"])
    }
    assert len(verdicts) == 1, segs


@_HYP
@given(raw=st.text(max_size=40))
def test_p3_nunca_lanza_con_texto_arbitrario(proj: Path, raw: str) -> None:
    """P3: cualquier str como file_path -> no propaga excepciones (hook_main)."""
    run_inproc(str(proj), raw)


@_HYP
@given(segs=_segments)
def test_p4_no_regresion_substring(proj: Path, segs: list[str]) -> None:
    """P4: con un segmento que solo TERMINA en `.claude` y ningun `.claude` real, avisa."""
    full = ["pkg", "my.claude"] + [s for s in segs if s not in ("..",)]
    if oracle(full, _short_name_live(proj)) != "warn":
        return
    assert run_inproc(str(proj), str(proj / "/".join(x for x in full if x)))


# --------------------------------------------------------------------------- (b)

COMMON_CASES = [
    # (ruta relativa al proyecto, avisa?)
    ("my.claude/x.py", True),
    (".claude-backup/x.py", True),
    (".claude~/x.py", True),
    ("a/.claude.md", True),
    ("a/my.claude", True),
    ("x.claude/y", True),
    ("claude/x", True),
    (".claude", False),
    ("pkg/.claude", False),
    ("./.claude/settings.json", False),
    ("./.claude/", False),
    (".claude/", False),
    (".CLAUDE/x", False),
    (".Claude/docs/a.md", False),
    ("a/b/c/.claude/d/e", False),
    ("a//.claude//b", False),
    ("a/./.claude/./b", False),
    ("my.claude/../.claude/x", False),
    (".claude/../src/x.py", True),
    ("a b/.claude/x", False),
    ("a b/c d.py", True),
    ("\u00f1/.claude/x", False),
    ("\uff0e\uff43\uff4c\uff41\uff55\uff44\uff45/x", True),
]

NT_CASES = [
    ("x\\.claude\\y", False),
    ("x\\.claude/y", False),
    ("x/.claude\\y", False),
    (".claude\\x", False),
    ("my.claude\\x", True),
    (".\\.claude\\x", False),
    ("CLAUDE~1\\docs\\x.md", False),  # nombre corto 8.3 del .claude existente
]

POSIX_CASES = [
    ("x\\.claude\\y", True),  # un solo nombre de archivo con backslashes
    (".claude\\x", True),
]


@pytest.mark.parametrize(("rel", "warns"), COMMON_CASES + (NT_CASES if IS_NT else POSIX_CASES))
@pytest.mark.parametrize("absolute", [False, True])
def test_casos_extremos(proj: Path, rel: str, warns: bool, absolute: bool) -> None:
    if rel.startswith("CLAUDE~1") and not _short_name_live(proj):
        pytest.skip("8.3 desactivado en este volumen")
    sep = "\\" if IS_NT else "/"
    raw = str(proj) + sep + rel if absolute else rel
    assert run_inproc(str(proj), raw) is warns


@pytest.mark.skipif(not IS_NT, reason="unidad relativa solo en Windows")
def test_nt_unidad_relativa_misma_unidad_es_del_proyecto(proj: Path) -> None:
    """`C:x.py` (relativa a la unidad) contra un cwd en C: -> pathlib la une al cwd.
    Aceptable: el cwd del proceso en esa unidad ES el proyecto."""
    drive = proj.drive
    assert run_inproc(str(proj), drive + "my.claude\\x.py") is True
    assert run_inproc(str(proj), drive + ".claude\\x.py") is False


@pytest.mark.parametrize(
    "raw",
    [
        "\\\\host\\share\\.claude\\x",
        "\\\\host\\share\\proj\\src\\x.py",
        "Z:\\otro\\src\\x.py",
        "Z:\\otro\\.claude\\x",
        "/etc/.claude/x",
        "../.claude/x",
        "../x.py",
    ],
)
def test_fuera_del_proyecto_nunca_avisa(proj: Path, raw: str) -> None:
    assert run_inproc(str(proj), raw) is False


@pytest.mark.skipif(not IS_NT, reason="semantica Win32 de puntos/espacios finales")
@pytest.mark.parametrize("rel", ["x/.claude./y", "x/.claude /y", "x/.claude.. /y"])
def test_nt_punto_o_espacio_final_es_el_mismo_dir(proj: Path, rel: str) -> None:
    """Win32 recorta puntos/espacios finales: `x/.claude./y` se escribe en
    `x/.claude/y`. En PostToolUse el archivo YA existe y resolve() devuelve el
    nombre real -> debe excluirse."""
    real = proj / "x" / ".claude" / "y"
    real.parent.mkdir(parents=True, exist_ok=True)
    real.write_text("z", encoding="utf-8")
    try:
        assert run_inproc(str(proj), str(proj) + "\\" + rel.replace("/", "\\")) is False
    finally:
        real.unlink()


@pytest.mark.parametrize("value", [None, 0, 5, 3.14, True, False, [], ["a.py"], {"a": 1}, ""])
@pytest.mark.parametrize("key", ["file_path", "notebook_path"])
def test_tipos_raros_inproc_no_lanzan(proj: Path, value: Any, key: str) -> None:
    assert run_inproc(str(proj), value, key=key) is False


@pytest.mark.parametrize("value", ["\x00", "a\x00b", ".claude\x00/x", "pkg/.claude/\x00"])
def test_nul_no_lanza(proj: Path, value: str) -> None:
    """NUL embebido: no debe propagar (con prefix forzado puede avisar; ver reporte)."""
    run_inproc(str(proj), value)


# --------------------------------------------------------------------------- (c)

BRIDGES_ALL = {
    "temas": [
        {
            "tema": "todo",
            "archivo": ".claude/docs/todo.md",
            "rutas": [
                ".claude/",
                "claude~1/",
                "my.claude/",
                ".claude-backup/",
                ".claude~/",
                "a/",
                "pkg/",
                "x/",
            ],
        }
    ]
}


def _payload(project: Path, sid: str, tool: str, tool_input: Any) -> dict[str, Any]:
    return {"cwd": str(project), "session_id": sid, "tool_name": tool, "tool_input": tool_input}


SUBPROC_CASES: list[tuple[str, bool]] = [
    ("my.claude/x.py", True),
    (".claude-backup/x.py", True),
    (".claude~/x.py", True),
    ("a/.claude.md", True),
    ("pkg/.claude", False),
    ("./.claude/settings.json", False),
    (".CLAUDE/settings.json", False),
    ("pkg/.claude/x.md", False),
    ("x/../.claude/y.md", False),
]
if IS_NT:
    SUBPROC_CASES += [
        ("pkg\\.claude\\x.md", False),
        ("pkg/.claude\\x.md", False),
        ("my.claude\\x.py", True),
        ("CLAUDE~1\\docs\\x.md", False),
    ]
else:
    SUBPROC_CASES += [("pkg/.claude\\x.md", True)]


@pytest.mark.parametrize(("rel", "warns"), SUBPROC_CASES)
@pytest.mark.parametrize("tool", ["Edit", "Write"])
@pytest.mark.parametrize("form", ["relative", "absolute"])
def test_hook_real(
    run_hook: Any, project: Path, rel: str, warns: bool, tool: str, form: str
) -> None:
    write_bridges(project, data=BRIDGES_ALL)
    if rel.startswith("CLAUDE~1") and not (project / "CLAUDE~1").is_dir():
        pytest.skip("8.3 desactivado en este volumen")
    sep = "\\" if IS_NT else "/"
    raw = rel if form == "relative" else str(project) + sep + rel
    tool_input: dict[str, Any] = {"file_path": raw}
    if tool == "Edit":
        tool_input |= {"old_string": "a", "new_string": "b"}
    else:
        tool_input |= {"content": "z"}
    out = run_hook(HOOK, _payload(project, f"ins-{tool}-{form}", tool, tool_input))
    if warns:
        assert "todo.md" in out, (rel, out)
        assert json.loads(out)["hookSpecificOutput"]["hookEventName"] == "PostToolUse"
    else:
        assert out == "", (rel, out)


@pytest.mark.parametrize(
    "tool_input",
    [
        {"file_path": None},
        {"file_path": 7},
        {"file_path": 1.5},
        {"file_path": True},
        {"file_path": ["src/auth/x.py"]},
        {"file_path": {"p": "src/auth/x.py"}},
        {"notebook_path": 3},
        {"notebook_path": ["a"]},
        {"file_path": "a\x00b"},
        "src/auth/x.py",
        ["src/auth/x.py"],
        None,
        42,
    ],
)
def test_hook_real_tipos_raros_no_crashea(run_hook: Any, project: Path, tool_input: Any) -> None:
    write_bridges(project, data=BRIDGES_ALL)
    # run_hook ya asserta returncode == 0; ademas no debe emitir nada.
    assert run_hook(HOOK, _payload(project, "ins-raro", "Write", tool_input)) == ""


def test_hook_real_my_claude_y_luego_claude_dedup(run_hook: Any, project: Path) -> None:
    """Editar `.claude/x` NO consume el aviso del tema: `my.claude/x` luego avisa."""
    write_bridges(project, data=BRIDGES_ALL)
    sid = "ins-seq"
    assert run_hook(HOOK, _payload(project, sid, "Write", {"file_path": ".claude/a.md"})) == ""
    out = run_hook(HOOK, _payload(project, sid, "Write", {"file_path": "my.claude/a.md"}))
    assert "todo.md" in out
