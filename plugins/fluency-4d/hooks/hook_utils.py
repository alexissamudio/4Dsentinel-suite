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
- Lectura de JSON: read_json_safe / parse_json_dict (todo error -> None, BOM
  tolerado, solo objetos) y load_bridges_temas (bridges.json con topes de
  tamano y de temas). Coercion de campos: state_num / str_list.
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

import contextlib
import functools
import hashlib
import json
import math
import os
import re
import sys
import tempfile
import threading
import time
import unicodedata
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any, ParamSpec, TypeGuard, TypeVar

MAX_STDIN_BYTES = 1024 * 1024
_BOM = chr(0xFEFF)  # BOM UTF-8 ya decodificado (chr: los .py son ASCII)
STATE_TTL_SECONDS = 4 * 60 * 60  # 4 horas

# Topes de bridges.json. Los hooks tienen timeout de 5 s en hooks.json (y uv se
# come parte en el arranque): un bridges.json de 5 MB / 60k temas tardaba > 5 s
# en tema_lines, Claude Code mataba el hook y se perdia TAMBIEN la inyeccion de
# arranque. Un bridges.json real pesa unos KB con decenas de temas; por encima
# de estos topes se ignora (archivo) o se trunca (temas) en vez de arriesgar el
# timeout.
MAX_BRIDGES_BYTES = 1024 * 1024
MAX_BRIDGES_TEMAS = 500

# stats.json: lock liviano para el read-modify-write de bump_stats. Si no se
# consigue en STATS_LOCK_WAIT_SECONDS se saltea el incremento (el hook tiene que
# ser rapido; perder un incremento es aceptable, corromper no). Un lock con mas
# de STATS_LOCK_STALE_SECONDS es huerfano (proceso muerto) y se descarta.
STATS_LOCK_WAIT_SECONDS = 0.2
STATS_LOCK_STALE_SECONDS = 10.0
STATS_CORRUPT_KEEP = 3  # copias stats.json.corrupt-<ts> que se conservan

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

    Los hooks tratan {} como "sin datos" y hacen pass-through. Usa
    parse_json_dict: un payload anidado miles de niveles (RecursionError) tambien
    cuenta como invalido.
    """
    if not raw:
        return {}
    data = parse_json_dict(raw)
    return data if data is not None else {}


# --- Lectura de JSON a prueba de todo ------------------------------------------


def parse_json_dict(text: str | bytes) -> dict[str, Any] | None:
    """Parsea `text` como un objeto JSON. Cualquier falla o no-objeto -> None.

    Ademas de JSONDecodeError atrapa RecursionError: json.loads de un JSON
    anidado miles de niveles (`[[[[...`) lo lanza, no esta en el except habitual
    y el hook moria en pass-through (o, con estado/stats, quedaba congelado para
    siempre porque nunca llegaba a reescribir el archivo). Con bytes, el decode
    es `utf-8-sig` estricto (BOM tolerado; bytes no UTF-8 -> None).
    """
    try:
        if isinstance(text, bytes):
            text = text.decode("utf-8-sig")
        elif text.startswith(_BOM):
            text = text[1:]
        data = json.loads(text)
    except (ValueError, UnicodeDecodeError, RecursionError):
        # ValueError cubre JSONDecodeError y UnicodeDecodeError es subclase,
        # pero se nombra explicito por legibilidad.
        return None
    return data if isinstance(data, dict) else None


def read_json_safe(
    path: Path | str, *, errors: str = "strict", max_bytes: int | None = None
) -> dict[str, Any] | None:
    """Lee `path` como objeto JSON. Ausente, ilegible, invalido o no-objeto -> None.

    Punto unico de lectura de JSON de los hooks (estado, flags, bridges.json).
    - Decodifica con `utf-8-sig`: tolera el BOM UTF-8 que escribe p.ej.
      PowerShell 5 (`Out-File -Encoding utf8`); sin esto json.loads falla con
      'Unexpected UTF-8 BOM' y el archivo se ignoraba en silencio.
    - `errors`: "strict" (default; bytes no UTF-8 -> None) o "replace" (los
      flags, por paridad con Node, ver la seccion de flags).
    - `max_bytes`: si el archivo pesa mas, ni se lee -> None (ver
      MAX_BRIDGES_BYTES).
    Atrapa OSError, ValueError (JSONDecodeError), UnicodeDecodeError y
    RecursionError: nunca lanza.
    """
    p = Path(path)
    try:
        if max_bytes is not None and p.stat().st_size > max_bytes:
            log_debug(f"{p.name} supera {max_bytes} bytes: se ignora")
            return None
        text = p.read_bytes().decode("utf-8-sig", errors=errors)
    except (OSError, ValueError):
        return None
    return parse_json_dict(text)


def load_bridges_temas(cwd: Path) -> list[Any]:
    """Lista `temas` de <cwd>/.claude/docs/bridges.json, o [] si no hay puentes.

    Ausente, ilegible, invalido, no-objeto, sin `temas` lista o mas pesado que
    MAX_BRIDGES_BYTES -> []. Se devuelven a lo sumo MAX_BRIDGES_TEMAS entradas
    crudas (sin validar: eso es de cada hook). Nunca lanza.
    """
    bridges = read_json_safe(cwd / ".claude" / "docs" / "bridges.json", max_bytes=MAX_BRIDGES_BYTES)
    if bridges is None:
        return []
    temas = bridges.get("temas")
    if not isinstance(temas, list):
        return []
    if len(temas) > MAX_BRIDGES_TEMAS:
        log_debug(f"bridges.json con {len(temas)} temas: se usan los primeros {MAX_BRIDGES_TEMAS}")
        return temas[:MAX_BRIDGES_TEMAS]
    return temas


def _finite_number(value: object) -> TypeGuard[int | float]:
    """True si `value` es int/float finito (bool NO cuenta como numero)."""
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def state_num(value: object, default: float = 0.0) -> float:
    """`value` como float si es un numero finito; si no (str, None, bool...) -> default.

    Para campos numericos del estado/stats: un tipo raro (p.ej. last_seen_pct
    = "abc") hacia lanzar float()/int() antes de save_state y el hook quedaba en
    pass-through hasta que venciera el TTL.
    """
    return float(value) if _finite_number(value) else default


def str_list(value: object) -> list[str]:
    """`value` si es lista, quedandose solo con sus strings; cualquier otra cosa -> [].

    Para campos tipo `temas_inyectados` / `nudges_dados`: set() de un int o de
    una lista con no-hasheables lanzaba TypeError.
    """
    if not isinstance(value, list):
        return []
    return [v for v in value if isinstance(v, str)]


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
    arranque). Un `_ts` ausente, que no es un numero finito (null, "x", NaN,
    bool) o mas de STATE_TTL_SECONDS en el futuro cuenta como vencido: antes
    `time.time() - "x"` lanzaba TypeError y, como el hook nunca llegaba a
    save_state, quedaba en pass-through PERMANENTE.
    La lectura va por read_json_safe: bytes no UTF-8, BOM, JSON anidado profundo
    (RecursionError) o no-objeto nunca escapan como excepcion (si escaparan, el
    hook quedaria en pass-through toda la sesion). Los campos propios de cada
    hook los valida el hook (state_num / str_list).
    Puede lanzar OSError desde _state_path (dir inseguro); hook_main lo
    convierte en pass-through.
    """
    path = _state_path(key)
    state = read_json_safe(path)
    if state is None:
        return {}
    ts = state.get("_ts")
    # abs(): un _ts en el FUTURO (reloj corrido, archivo editado) tambien vence;
    # sin esto un estado con _ts = 1e12 no venceria nunca.
    if not _finite_number(ts) or abs(time.time() - ts) > STATE_TTL_SECONDS:
        return {}
    return state


# --- Flags globales (~/.claude/fluency4d/*.json) -------------------------------
# Los escriben las skills (/caveman, /adhd, /verify-diff) con la tool Write; los
# hooks solo los leen. La barra de estado (statusline/statusline.js) lee los
# mismos archivos con Node y ambos lados tienen que dar el MISMO veredicto
# (fixture compartido tests/fluency-4d/fixtures/flags_parity.json). Por eso los
# loaders leen con errors="replace" (via read_json_safe): Node (readFileSync con
# 'utf8') no falla ante bytes UTF-8 invalidos, los reemplaza por U+FFFD. Con el
# decode estricto el hook haria pass-through donde la barra muestra el modo
# prendido. read_json_safe ademas tolera el BOM UTF-8 (utf-8-sig).


def load_caveman() -> dict[str, Any]:
    """Lee el flag global de modo caveman (~/.claude/fluency4d/caveman.json).

    Solo lectura. Devuelve el dict si esta prendido (on=True) y level es valido;
    ante cualquier error / JSON invalido / OFF / level fuera del set -> {}
    (pass-through). El writer es la tool Write del skill, no este helper.
    Niveles validos: auto, lite, full, ultra.
    """
    path = Path.home() / ".claude" / "fluency4d" / "caveman.json"
    st = read_json_safe(path, errors="replace")
    if st is None:
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
    st = read_json_safe(path, errors="replace")
    if st is None:
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
    st = read_json_safe(path, errors="replace")
    if st is None:
        return {}
    if st.get("on") is not True:
        return {}
    if st.get("level") not in ("auto", "lite", "full"):
        return {}
    return st


def _as_count(value: object) -> int:
    """Contador saneado: numero finito -> int; cualquier otra cosa -> 0."""
    return int(value) if _finite_number(value) else 0


def _sanitize_stats(raw: dict[str, Any], now: float) -> dict[str, Any]:
    """Sanea stats.json POR ENTRADA, conservando las entradas ajenas validas.

    Antes, un tipo raro en cualquier entrada (`sesiones: "abc"`, `temas: []`,
    `temas: {"t": 5}`, `_ts: "s"` en otro proyecto) lanzaba dentro de bump_stats
    y stats.json quedaba CONGELADO para siempre. Ahora: una entrada que no es
    objeto se descarta; `_ts` no numerico vale `now` (gracia de 90 dias en vez
    de borrar datos); `sesiones`/`inyecciones` no numericos valen 0; `temas` que
    no es objeto vale {}; un registro de tema que no es objeto se descarta. Las
    claves desconocidas se preservan. Poda proyectos con 90 dias sin actividad.
    """
    out: dict[str, Any] = {}
    for key, entry in raw.items():
        if not isinstance(entry, dict):
            continue
        ts = state_num(entry.get("_ts"), now)
        if now - ts > 90 * 24 * 3600:
            continue  # poda: proyecto inactivo
        temas_raw = entry.get("temas")
        temas: dict[str, Any] = {}
        if isinstance(temas_raw, dict):
            for tema, registro in temas_raw.items():
                if isinstance(registro, dict):
                    temas[tema] = {
                        **registro,
                        "inyecciones": _as_count(registro.get("inyecciones")),
                    }
        out[key] = {
            **entry,
            "_ts": ts,
            "sesiones": _as_count(entry.get("sesiones")),
            "temas": temas,
        }
    return out


@contextlib.contextmanager
def _stats_lock(directory: Path) -> Iterator[bool]:
    """Lock liviano (O_CREAT|O_EXCL) para el read-modify-write de stats.json.

    Cede True si lo consiguio en STATS_LOCK_WAIT_SECONDS, False si no (el
    llamador se saltea el incremento). Un lock mas viejo que
    STATS_LOCK_STALE_SECONDS es de un proceso muerto: se borra y se reintenta
    (sin esto un crash con el lock tomado congelaria la telemetria). El borrado
    del huerfano tiene una carrera benigna (dos procesos lo ven viejo a la vez):
    a lo sumo dos escritores solapados, y como la escritura es atomica eso solo
    puede perder un incremento, nunca corromper ni borrar entradas ajenas.
    """
    lock = directory / "stats.json.lock"
    deadline = time.monotonic() + STATS_LOCK_WAIT_SECONDS
    acquired = False
    while True:
        try:
            fd = os.open(str(lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            os.close(fd)
            acquired = True
            break
        except FileExistsError:
            try:
                if time.time() - lock.stat().st_mtime > STATS_LOCK_STALE_SECONDS:
                    lock.unlink()
                    continue
            except OSError:
                pass  # lo libero otro entre el open y el stat: reintentar
        except OSError:
            # No se puede crear (dir de solo lectura; en Windows tambien
            # PermissionError si el lock se esta borrando): reintentar hasta
            # el deadline como si estuviera tomado.
            pass
        if time.monotonic() >= deadline:
            break
        time.sleep(0.01)
    try:
        yield acquired
    finally:
        if acquired:
            try:
                lock.unlink()
            except OSError:
                pass


def _quarantine_stats(path: Path) -> None:
    """Renombra un stats.json invalido a stats.json.corrupt-<ts> (deja rastro).

    Conserva las STATS_CORRUPT_KEEP copias mas recientes para no acumular
    basura sin limite. Un OSError del rename se propaga a bump_stats (no-op:
    sin rename no se pisa el archivo). El nombre ordena cronologicamente
    (<AAAAMMDD-HHMMSS>-<ns>) y, si ya existe (reloj de baja resolucion), se le
    agrega un contador en vez de pisar la copia anterior.
    """
    ns = time.time_ns()
    stamp = time.strftime("%Y%m%d-%H%M%S", time.localtime(ns // 1_000_000_000))
    base = f"{path.name}.corrupt-{stamp}-{ns % 1_000_000_000:09d}"
    destino = path.with_name(base)
    n = 0
    while destino.exists():
        n += 1
        destino = path.with_name(f"{base}-{n}")
    os.replace(path, destino)
    copias = sorted(path.parent.glob(f"{path.name}.corrupt-*"))
    for viejo in copias[:-STATS_CORRUPT_KEEP]:
        try:
            viejo.unlink()
        except OSError:
            pass


def bump_stats(cwd: str, temas_nuevos: list[str], nueva_sesion: bool) -> None:
    """Telemetria de uso de puentes, best-effort, con lock liviano y escritura atomica.

    Vive en ~/.claude/fluency4d/stats.json (nunca dentro del proyecto del
    usuario). Invariante: el archivo final SIEMPRE es JSON valido y NUNCA pierde
    las entradas de otros proyectos, aun con muchas sesiones concurrentes:
    - escritura atomica (atomic_write_json): un lector nunca ve un archivo a
      medio escribir (antes write_text truncaba+escribia y 20 procesos dejaban
      `...}}}` invalido, que el siguiente "rehacia de cero" borrando todo);
    - lock (_stats_lock) para el read-modify-write; sin lock en <=200 ms se
      saltea el incremento: los numeros son senal para podar puentes, no
      contabilidad, y el hook tiene que ser rapido;
    - un stats.json existente pero invalido (o no-objeto) NO se pisa sin mas:
      se renombra a stats.json.corrupt-<ts> y se arranca de cero;
    - las entradas se sanean una por una (_sanitize_stats).
    Cualquier error degrada a no-op para no romper el hot path del router.
    """
    try:
        directory = Path.home() / ".claude" / "fluency4d"
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / "stats.json"
        with _stats_lock(directory) as locked:
            if not locked:
                log_debug("stats.json ocupado: se saltea el incremento")
                return
            try:
                data = path.read_bytes()
            except FileNotFoundError:
                data = b""
            # Otro OSError (es un directorio, sin permiso...) cae al except de
            # afuera: no-op, mejor perder el incremento que pisar el archivo.
            parsed: dict[str, Any] = {}  # ausente o vacio: nada que preservar
            if data.strip():
                leido = parse_json_dict(data)
                if leido is None:
                    log_debug("stats.json invalido: se renombra a .corrupt-<ts>")
                    _quarantine_stats(path)
                else:
                    parsed = leido
            now = time.time()
            stats = _sanitize_stats(parsed, now)
            key = str(Path(cwd).resolve()).casefold()
            entry = stats.setdefault(key, {"sesiones": 0, "temas": {}})
            entry["_ts"] = now
            entry["ultima_actividad"] = time.strftime("%Y-%m-%d")
            if nueva_sesion:
                entry["sesiones"] += 1
            for tema in temas_nuevos:
                registro = entry["temas"].setdefault(tema, {"inyecciones": 0})
                registro["inyecciones"] += 1
                registro["ultima"] = time.strftime("%Y-%m-%d")
            atomic_write_json(path, stats)
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
        # lost-update residual (dos writes solapados, gana el ultimo) es benigno:
        # el estado es senal de dedup best-effort, no contabilidad (por eso, a
        # diferencia de bump_stats, no lleva lock).
        atomic_write_json(path, state)
    except OSError as exc:
        log_debug(f"no se pudo guardar estado: {exc}")
