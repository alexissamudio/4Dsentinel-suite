#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""hook_utils.py - Utilidades compartidas para los hooks de fluency-4d.

Basado en el patron de hook_utils.py de oh-my-claude
(https://github.com/TechDufus/oh-my-claude, licencia MIT).

NO es un hook: ningun evento de hooks.json lo dispara. Lo importan los hooks
(sys.path.insert del dir hooks/) y statusline_setup.py (escritura atomica).
Reune:
- Entrada: read_stdin_safe (stdin con timeout, apto Windows) y parse_hook_input
  (payload JSON del evento; cualquier cosa que no sea un objeto -> {}).
- Salida: output_empty / output_context / output_stop_block, siempre JSON ASCII.
- hook_main: decorador que convierte toda excepcion en pass-through.
- Estado por sesion: <temp>/fluency4d/<session_key>[-sufijo].json con TTL de
  4 h (load_state / save_state). Cada hook usa su propio sufijo (-bridge,
  -calib, -ckpt, -drift, -gate, -playbook) para no pisar el estado ajeno.
- Flags globales de solo lectura en ~/.claude/fluency4d/ (caveman, adhd, verify)
  que escriben las skills, y la telemetria stats.json (bump_stats).
- Sanitizacion de lo que viene de bridges.json (sanitize_field, safe_doc_path).

Nunca escribe dentro del proyecto del usuario: solo en temp y ~/.claude/fluency4d/.

Contrato de salida:
- Pass-through: exit 0 sin stdout.
- Contexto adicional (SessionStart/UserPromptSubmit):
  {"hookSpecificOutput": {"hookEventName": "...", "additionalContext": "..."}}
- Bloqueo en Stop (top-level, NO hookSpecificOutput):
  {"decision": "block", "reason": "..."}
"""

from __future__ import annotations

import functools
import hashlib
import json
import os
import re
import sys
import tempfile
import threading
import time
import unicodedata
from collections.abc import Callable
from pathlib import Path
from typing import Any, ParamSpec, TypeVar

MAX_STDIN_BYTES = 1024 * 1024
STATE_TTL_SECONDS = 4 * 60 * 60  # 4 horas

_P = ParamSpec("_P")
_R = TypeVar("_R")

# Chars que, si vienen de un bridges.json hostil, podrian romper/confundir la
# plantilla de display o el markdown del additionalContext: backticks (delimitan
# codigo), comillas (cierran el campo citado), corchetes y llaves. Se neutralizan
# a espacio en sanitize_field junto con los controles/separadores unicode.
_UNSAFE_DISPLAY_CHARS = frozenset("`'\"[]{}")


# --- Sanitizacion de campos controlados por el proyecto (bridges.json) --------
# bridges.json vive en el repo del usuario; en un repo de terceros HOSTIL lo
# controla el atacante. Sus campos se interpolan en additionalContext (texto que
# Claude lee como contexto). Sin sanitizar, un atacante puede meter newlines para
# cerrar la plantilla e inyectar instrucciones falsas (prompt injection de 2do
# orden), o poner un `archivo` fuera del proyecto (`~/.ssh/id_rsa`, `../secreto`,
# `X:\...`) para que Claude lo lea.


def sanitize_field(text: object, max_len: int = 80) -> str:
    """Devuelve un string seguro para interpolar en additionalContext.

    Colapsa saltos de linea, caracteres de control y separadores unicode a un
    solo espacio, y neutraliza (tambien a espacio) los chars que podrian romper
    o confundir la plantilla de display / el markdown del contexto: backticks,
    comillas, corchetes y llaves (ver `_UNSAFE_DISPLAY_CHARS`). Recorta y trunca
    a `max_len` (marcador ASCII '...'). Deterministica. Un input benigno corto
    (un `tema` como 'auth') vuelve intacto: sin regresion.

    Residuo aceptado (SEC-004): neutraliza la ESTRUCTURA (template-escape), no la
    SEMANTICA -- deja pasar <=max_len chars de texto plano instructivo. Es
    inherente al feature (inyectar contexto del repo). Mitigacion: cap de 80
    chars por campo, requiere match de keyword para inyectarse, y Claude lo ve
    entrecomillado como dato del repo, no como instruccion.
    """
    s = str(text)
    cleaned = [
        " " if (ch in _UNSAFE_DISPLAY_CHARS or unicodedata.category(ch)[0] in ("C", "Z")) else ch
        for ch in s
    ]
    collapsed = " ".join("".join(cleaned).split())
    if len(collapsed) > max_len:
        collapsed = collapsed[: max(0, max_len - 3)].rstrip() + "..."
    return collapsed


def safe_doc_path(archivo: object) -> str | None:
    """Valida que `archivo` sea una ruta RELATIVA dentro del proyecto.

    Acepta solo rutas relativas (forma POSIX normalizada). Rechaza (-> None):
    - no-strings, vacios o con caracteres de control (newline injection),
    - rutas absolutas POSIX (`/...`) o con expansion de home (`~...`),
    - unidades Windows (`X:\\...`, `X:/...`) y UNC (`\\\\host`),
    - cualquier componente `..` (traversal).

    None significa "ruta insegura": el llamador NO debe puentear ese tema.
    """
    if not isinstance(archivo, str):
        return None
    raw = archivo.strip()
    if not raw:
        return None
    if any(unicodedata.category(ch)[0] == "C" for ch in raw):
        return None  # controles/newlines: ruta invalida
    unified = raw.replace("\\", "/")
    if unified.startswith("/") or unified.startswith("~"):
        return None  # absoluta POSIX o home-expansion
    if re.match(r"^[A-Za-z]:", unified):
        return None  # unidad Windows (X:)
    parts = [p for p in unified.split("/") if p not in ("", ".")]
    if not parts or any(p == ".." for p in parts):
        return None  # vacia tras normalizar, o traversal
    return "/".join(parts)


def read_stdin_safe(timeout: float = 5.0) -> str:
    """Lee stdin con timeout. En Windows no hay select/SIGALRM sobre pipes,
    asi que se usa un hilo daemon con join(timeout).

    Lee como maximo MAX_STDIN_BYTES. Devuelve "" si vence el timeout o la lectura
    falla: el hilo daemon queda colgado pero no impide que el proceso termine.
    """
    result = {"data": ""}

    def _read() -> None:
        try:
            result["data"] = sys.stdin.read(MAX_STDIN_BYTES)
        except Exception:
            result["data"] = ""

    reader = threading.Thread(target=_read, daemon=True)
    reader.start()
    reader.join(timeout)
    return result["data"]


def parse_hook_input(raw: str) -> dict[str, Any]:
    """Parsea el payload JSON del evento. Vacio, invalido o no-objeto -> {}.

    Los hooks tratan {} como "sin datos" y hacen pass-through.
    """
    try:
        data = json.loads(raw) if raw else {}
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _emit(obj: dict[str, Any]) -> None:
    # ensure_ascii=True: la consola de Windows puede ser cp1252; el texto
    # acentuado viaja escapado dentro del JSON y llega intacto.
    sys.stdout.write(json.dumps(obj, ensure_ascii=True) + "\n")
    sys.stdout.flush()


def output_empty() -> None:
    """Pass-through: sin salida, exit 0."""


def output_context(event: str, text: str) -> None:
    """Emite `text` como additionalContext del evento `event` (lo lee Claude)."""
    _emit({"hookSpecificOutput": {"hookEventName": event, "additionalContext": text}})


def output_stop_block(reason: str) -> None:
    """Bloquea el Stop con `reason` (formato top-level, no hookSpecificOutput)."""
    _emit({"decision": "block", "reason": reason})


def log_debug(message: str) -> None:
    """Log de debug a stderr, a prueba de encoding y que NUNCA lanza.

    Se invoca dentro del `except` de hook_main; si un `print` normal reventara
    (p.ej. stderr cp1252 en Windows y un mensaje con un char no representable),
    la excepcion propagaria y el hook moriria con traceback en vez de degradar a
    pass-through. Por eso se escribe a `sys.stderr.buffer` en UTF-8 con
    `errors='replace'` y todo va envuelto en un try/except que traga cualquier
    fallo: el logging jamas rompe el contrato "el hook nunca crashea".
    """
    if os.environ.get("HOOK_DEBUG") != "1":
        return
    line = f"[fluency-4d] {message}\n"
    try:
        buffer = getattr(sys.stderr, "buffer", None)
        if buffer is not None:
            buffer.write(line.encode("utf-8", "replace"))
            buffer.flush()
        else:
            # stderr sin buffer (p.ej. capturado en tests): degrada representando
            # los chars no soportados por su encoding en vez de lanzar.
            enc = getattr(sys.stderr, "encoding", None) or "utf-8"
            sys.stderr.write(line.encode(enc, "replace").decode(enc, "replace"))
            sys.stderr.flush()
    except Exception:  # noqa: BLE001 - el log jamas rompe el hook
        pass


def hook_main(event: str) -> Callable[[Callable[_P, _R]], Callable[_P, _R | None]]:
    """Decorador: cualquier excepcion degrada a pass-through (nunca romper la sesion).

    Envuelve el `main` de cada hook. Si `fn` lanza una Exception, la registra con
    log_debug (solo con HOOK_DEBUG=1), no emite nada y devuelve None: el hook sale
    con exit 0 y Claude Code sigue como si no existiera. No atrapa BaseException
    (SystemExit / KeyboardInterrupt).

    Args:
        event: nombre del evento, solo para el mensaje de log.
    """

    def decorator(fn: Callable[_P, _R]) -> Callable[_P, _R | None]:
        @functools.wraps(fn)
        def wrapper(*args: _P.args, **kwargs: _P.kwargs) -> _R | None:
            try:
                return fn(*args, **kwargs)
            except Exception as exc:  # noqa: BLE001 - degradacion intencional
                log_debug(f"{event} hook error: {exc}")
                output_empty()
                return None

        return wrapper

    return decorator


# --- Estado por sesion (dedup) -------------------------------------------------


def session_key(data: dict[str, Any]) -> str:
    """Clave de estado de la sesion: hash de session_id, o del cwd si falta.

    Se hashea para que el nombre de archivo sea seguro (sin separadores ni chars
    raros) cualquiera sea el valor recibido. Los hooks le agregan su sufijo.
    """
    sid = data.get("session_id")
    if sid:
        return "sid-" + hashlib.sha256(str(sid).encode()).hexdigest()[:16]
    # Fallback por cwd. Limitacion conocida: dos sesiones concurrentes en el
    # mismo proyecto comparten estado y la segunda pierde la inyeccion. v1.
    return "cwd-" + hashlib.sha256(str(data.get("cwd", "")).encode()).hexdigest()[:16]


def _state_path(key: str) -> Path:
    """Ruta <temp>/fluency4d/<key>.json; crea y endurece el directorio (ver abajo)."""
    directory = Path(tempfile.gettempdir()) / "fluency4d"
    # CWE-377: en un /tmp compartido (POSIX) el subdir de estado no debe ser
    # world-accesible ni un symlink pre-creado por un atacante. Se crea con
    # modo 0o700; en POSIX se rechaza el symlink y se fuerzan los permisos
    # (mkdir con exist_ok reusa un dir laxo y el umask puede recortar el modo).
    # En Windows %TEMP% ya es per-user y chmod(0o700) no aplica -> se omite.
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    if os.name == "posix":
        if directory.is_symlink():
            raise OSError("directorio de estado es un symlink: " + str(directory))
        # exist_ok reusa un dir pre-plantado por un atacante en /tmp compartido:
        # si no es nuestro (uid distinto) fallamos cerrado en vez de operar sobre
        # estado ajeno. hook_main traga el OSError -> passthrough (igual que el
        # caso symlink de arriba): fail-safe, no fail-open peligroso.
        if directory.stat().st_uid != os.getuid():  # type: ignore[attr-defined, unused-ignore]
            raise OSError("directorio de estado no es propiedad del usuario: " + str(directory))
        try:
            os.chmod(directory, 0o700)
        except OSError:
            pass
    return directory / f"{key}.json"


def load_state(key: str) -> dict[str, Any]:
    """Lee el estado de `key`. Ausente, ilegible, no-objeto o vencido -> {}.

    Vencido = su `_ts` (lo pone save_state) tiene mas de STATE_TTL_SECONDS: una
    sesion retomada al otro dia arranca como nueva (vuelve la inyeccion de
    arranque). Puede lanzar OSError desde _state_path (dir inseguro); hook_main
    lo convierte en pass-through.
    """
    path = _state_path(key)
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(state, dict):
        return {}
    if time.time() - state.get("_ts", 0) > STATE_TTL_SECONDS:
        return {}
    return state


# --- Flags globales (~/.claude/fluency4d/*.json) -------------------------------
# Los escriben las skills (/caveman, /adhd, /verify-diff) con la tool Write; los
# hooks solo los leen. La barra de estado (statusline/statusline.js) lee los
# mismos archivos con Node y ambos lados tienen que dar el MISMO veredicto
# (fixture compartido tests/fluency-4d/fixtures/flags_parity.json). Por eso los
# loaders leen con errors="replace": Node (readFileSync con 'utf8') no falla
# ante bytes UTF-8 invalidos, los reemplaza por U+FFFD. Con el decode estricto
# Python lanzaria UnicodeDecodeError (que no esta en el except) y el hook haria
# pass-through donde la barra muestra el modo prendido.


def load_caveman() -> dict[str, Any]:
    """Lee el flag global de modo caveman (~/.claude/fluency4d/caveman.json).

    Solo lectura. Devuelve el dict si esta prendido (on=True) y level es valido;
    ante cualquier error / JSON invalido / OFF / level fuera del set -> {}
    (pass-through). El writer es la tool Write del skill, no este helper.
    Niveles validos: auto, lite, full, ultra.
    """
    path = Path.home() / ".claude" / "fluency4d" / "caveman.json"
    try:
        st = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(st, dict):
        return {}
    if st.get("on") is not True:
        return {}
    if st.get("level") not in ("auto", "lite", "full", "ultra"):
        return {}
    return st


def load_verify() -> dict[str, Any]:
    """Lee el flag global de verificacion del diff (~/.claude/fluency4d/verify.json).

    Solo lectura. Devuelve el dict si esta prendido (on=True); ante cualquier
    error / JSON invalido / OFF -> {} (pass-through). El writer es la tool Write
    del skill verify-diff, no este helper.
    """
    path = Path.home() / ".claude" / "fluency4d" / "verify.json"
    try:
        st = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(st, dict):
        return {}
    if st.get("on") is not True:
        return {}
    return st


def load_adhd() -> dict[str, Any]:
    """Lee el flag global de modo ADHD/TDAH (~/.claude/fluency4d/adhd.json).

    Solo lectura. Devuelve el dict si esta prendido (on=True) y level es valido;
    ante cualquier error / JSON invalido / OFF / level fuera del set -> {}
    (pass-through). El writer es la tool Write del skill, no este helper.
    Niveles validos: auto, lite, full (sin ultra, a diferencia de caveman).
    """
    path = Path.home() / ".claude" / "fluency4d" / "adhd.json"
    try:
        st = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(st, dict):
        return {}
    if st.get("on") is not True:
        return {}
    if st.get("level") not in ("auto", "lite", "full"):
        return {}
    return st


def bump_stats(cwd: str, temas_nuevos: list[str], nueva_sesion: bool) -> None:
    """Telemetria de uso de puentes, best-effort y SIN lock.

    Vive en ~/.claude/fluency4d/stats.json (nunca dentro del proyecto del
    usuario). Dos sesiones concurrentes pueden pisarse un contador: los
    numeros son senal para podar puentes, no contabilidad. Cualquier error
    degrada a no-op para no romper el hot path del router.
    """
    try:
        directory = Path.home() / ".claude" / "fluency4d"
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / "stats.json"
        try:
            stats = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            stats = {}
        if not isinstance(stats, dict):
            stats = {}
        now = time.time()
        # Poda de proyectos inactivos: 90 dias sin actividad.
        stats = {
            k: v
            for k, v in stats.items()
            if isinstance(v, dict) and now - v.get("_ts", now) <= 90 * 24 * 3600
        }
        key = str(Path(cwd).resolve()).casefold()
        entry = stats.setdefault(key, {"sesiones": 0, "temas": {}})
        entry["_ts"] = now
        entry["ultima_actividad"] = time.strftime("%Y-%m-%d")
        if nueva_sesion:
            entry["sesiones"] = int(entry.get("sesiones", 0)) + 1
        for tema in temas_nuevos:
            registro = entry.setdefault("temas", {}).setdefault(tema, {"inyecciones": 0})
            registro["inyecciones"] = int(registro.get("inyecciones", 0)) + 1
            registro["ultima"] = time.strftime("%Y-%m-%d")
        path.write_text(json.dumps(stats, ensure_ascii=True), encoding="utf-8")
    except Exception as exc:  # noqa: BLE001 - telemetria jamas rompe el hook
        log_debug(f"stats no disponibles: {exc}")


def atomic_write_text(path: Path | str, text: str) -> None:
    """Escribe `text` en `path` de forma ATOMICA (temporal en el mismo dir + replace).

    Se escribe a un temporal en el MISMO directorio y luego os.replace(tmp, dst),
    atomico en Windows y POSIX: un lector concurrente nunca ve un archivo a medio
    escribir (torn-write). Si algo falla, borra el temporal y RE-LANZA el OSError:
    el llamador decide si degradar (save_state) o abortar (statusline_setup).
    Un UnicodeError (p. ej. un surrogate suelto que utf-8 no codifica) tambien
    borra el temporal y se re-lanza. Si `path` es un symlink se escribe en su
    DESTINO (Path.resolve): os.replace sobre el link lo reemplazaria por un
    archivo comun. Crea el directorio padre si falta.
    """
    dst = Path(path).resolve()
    dst.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(dst.parent), prefix=dst.name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as fh:
            fh.write(text)
        os.replace(tmp, dst)
    except (OSError, UnicodeError):
        try:
            os.unlink(tmp)  # limpieza best-effort si el write/replace fallo
        except OSError:
            pass
        raise


def atomic_write_json(
    path: Path | str,
    obj: Any,
    *,
    indent: int | str | None = None,
    ensure_ascii: bool = True,
    trailing_newline: bool = False,
) -> None:
    """Serializa `obj` a JSON y lo escribe atomicamente (ver atomic_write_text).

    Por defecto compacto y ASCII (estado interno). Para archivos del usuario
    (settings.json, keybindings.json) el llamador pasa indent, ensure_ascii=False
    y trailing_newline para respetar el formato que ya tenian.
    """
    payload = json.dumps(obj, ensure_ascii=ensure_ascii, indent=indent)
    if trailing_newline:
        payload += "\n"
    atomic_write_text(path, payload)


def save_state(key: str, state: dict[str, Any]) -> None:
    """Persiste `state` (lo muta: le pone `_ts` = ahora, que renueva el TTL).

    Best-effort: un OSError al escribir solo se loguea; el hook sigue y emite lo
    que tenga que emitir (a lo sumo se pierde el dedup de esta sesion). Un OSError
    de _state_path (dir inseguro) se propaga a hook_main.
    """
    state["_ts"] = time.time()
    path = _state_path(key)
    try:
        # Escritura ATOMICA (atomic_write_json): un load_state concurrente
        # (memory_checkpoint y doc_drift disparan en PostToolUse casi a la vez)
        # nunca ve un JSON a medio escribir -> no hay torn-write ni
        # JSONDecodeError espurio que devuelva {} y pierda el dedup. El
        # lost-update residual (dos writes solapados, gana el ultimo) es benigno
        # y equivalente al ya aceptado en bump_stats: el estado es senal de dedup
        # best-effort, no contabilidad.
        atomic_write_json(path, state)
    except OSError as exc:
        log_debug(f"no se pudo guardar estado: {exc}")
