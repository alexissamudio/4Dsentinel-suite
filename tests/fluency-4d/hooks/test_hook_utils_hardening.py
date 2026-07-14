"""Endurecimiento de hook_utils:

- MINOR 3 (CWE-94): sanitize_field trunca mas corto (max_len=80) y neutraliza
  backticks/comillas/corchetes/llaves para que texto hostil de bridges.json no
  pueda romper/confundir la plantilla de display ni el markdown del contexto.
- MINOR 1: log_debug es a prueba de encoding y NUNCA lanza (se llama dentro del
  except de hook_main; si lanzara, el hook moriria en vez de degradar).

Importa hook_utils directamente (no por subprocess) para inspeccionar el helper.
"""

from __future__ import annotations

import io
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
HOOKS_DIR = REPO_ROOT / "plugins" / "fluency-4d" / "hooks"
sys.path.insert(0, str(HOOKS_DIR))

import hook_utils  # noqa: E402

# --- MINOR 3: sanitize_field --------------------------------------------------


def test_benigno_intacto():
    assert hook_utils.sanitize_field("auth") == "auth"
    assert hook_utils.sanitize_field(".claude/docs/auth.md") == ".claude/docs/auth.md"


def test_default_max_len_es_80():
    largo = "a" * 200
    out = hook_utils.sanitize_field(largo)
    assert len(out) == 80
    assert out.endswith("...")


def test_truncado_marcador_es_ascii():
    out = hook_utils.sanitize_field("x" * 200)
    assert out == out.encode("ascii", "ignore").decode("ascii")  # sin '…'
    assert "…" not in out


def test_neutraliza_backticks_comillas_y_brackets():
    out = hook_utils.sanitize_field("a`b'c\"d[e]f{g}h")
    for ch in "`'\"[]{}":
        assert ch not in out
    # los chars peligrosos colapsan a espacio, no se borran pegando tokens
    assert out == "a b c d e f g h"


def test_neutraliza_controles_y_newlines():
    out = hook_utils.sanitize_field("auth\n\nINYECCION: `rm -rf /`")
    assert "\n" not in out
    assert "`" not in out
    assert out.count("  ") == 0  # espacios colapsados


def test_es_deterministica():
    entrada = "auth\t`x`\n[y]{z}" + "q" * 200
    assert hook_utils.sanitize_field(entrada) == hook_utils.sanitize_field(entrada)


# --- MINOR 1: log_debug a prueba de encoding ----------------------------------


class _Cp1252Stderr:
    """Simula un stderr de consola cp1252: el write de texto revienta ante un
    char no representable (como haria print en Windows), pero expone un .buffer
    de bytes (lo que log_debug debe usar)."""

    encoding = "cp1252"

    def __init__(self) -> None:
        self.buffer = io.BytesIO()

    def write(self, s: str) -> int:
        s.encode("cp1252")  # lanza UnicodeEncodeError si hay char no-cp1252
        raise AssertionError("log_debug no debe escribir por la capa de texto")

    def flush(self) -> None:
        pass


class _NoBufferStrictStderr:
    """stderr sin .buffer cuyo write estricto lanza ante chars no representables."""

    encoding = "cp1252"

    def __init__(self) -> None:
        self.data = ""

    def write(self, s: str) -> int:
        s.encode("cp1252")  # emula el error de un stream estricto
        self.data += s
        return len(s)

    def flush(self) -> None:
        pass


def test_log_debug_no_lanza_con_no_ascii_stderr_cp1252(monkeypatch):
    monkeypatch.setenv("HOOK_DEBUG", "1")
    fake = _Cp1252Stderr()
    monkeypatch.setattr(sys, "stderr", fake)
    # ruta con acento (no representable de forma trivial): no debe lanzar
    hook_utils.log_debug("ruta con acento: /home/josé/proyecto – dash")
    assert fake.buffer.getvalue()  # se escribio por sys.stderr.buffer en UTF-8


def test_log_debug_no_lanza_sin_buffer(monkeypatch):
    monkeypatch.setenv("HOOK_DEBUG", "1")
    fake = _NoBufferStrictStderr()
    monkeypatch.setattr(sys, "stderr", fake)
    # sin .buffer y con write estricto: el mensaje no-cp1252 no debe propagar
    hook_utils.log_debug("emoji \U0001f4a5 y acento ñ")  # no lanza


def test_log_debug_silencioso_si_flag_apagado(monkeypatch):
    monkeypatch.delenv("HOOK_DEBUG", raising=False)
    fake = _Cp1252Stderr()
    monkeypatch.setattr(sys, "stderr", fake)
    hook_utils.log_debug("no deberia escribir nada")
    assert fake.buffer.getvalue() == b""
