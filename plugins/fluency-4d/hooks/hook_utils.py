#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""hook_utils.py - Utilidades compartidas para los hooks de fluency-4d.

Basado en el patron de hook_utils.py de oh-my-claude
(https://github.com/TechDufus/oh-my-claude, licencia MIT).

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
from pathlib import Path

MAX_STDIN_BYTES = 1024 * 1024
STATE_TTL_SECONDS = 4 * 60 * 60  # 4 horas


# --- Sanitizacion de campos controlados por el proyecto (bridges.json) --------
# bridges.json vive en el repo del usuario; en un repo de terceros HOSTIL lo
# controla el atacante. Sus campos se interpolan en additionalContext (texto que
# Claude lee como contexto). Sin sanitizar, un atacante puede meter newlines para
# cerrar la plantilla e inyectar instrucciones falsas (prompt injection de 2do
# orden), o poner un `archivo` fuera del proyecto (`~/.ssh/id_rsa`, `../secreto`,
# `X:\...`) para que Claude lo lea.


def sanitize_field(text: object, max_len: int = 120) -> str:
    """Devuelve un string seguro para interpolar en additionalContext.

    Colapsa saltos de linea, caracteres de control y separadores unicode a un
    solo espacio, recorta y trunca a `max_len` (con elipsis). Un input benigno
    corto (un `tema` como 'auth') vuelve intacto: sin regresion.
    """
    s = str(text)
    cleaned = [
        " " if (unicodedata.category(ch)[0] in ("C", "Z")) else ch for ch in s
    ]
    collapsed = " ".join("".join(cleaned).split())
    if len(collapsed) > max_len:
        collapsed = collapsed[: max(0, max_len - 1)].rstrip() + "…"
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
    asi que se usa un hilo daemon con join(timeout)."""
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


def parse_hook_input(raw: str) -> dict:
    try:
        data = json.loads(raw) if raw else {}
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _emit(obj: dict) -> None:
    # ensure_ascii=True: la consola de Windows puede ser cp1252; el texto
    # acentuado viaja escapado dentro del JSON y llega intacto.
    sys.stdout.write(json.dumps(obj, ensure_ascii=True) + "\n")
    sys.stdout.flush()


def output_empty() -> None:
    """Pass-through: sin salida, exit 0."""


def output_context(event: str, text: str) -> None:
    _emit({"hookSpecificOutput": {"hookEventName": event, "additionalContext": text}})


def output_stop_block(reason: str) -> None:
    _emit({"decision": "block", "reason": reason})


def log_debug(message: str) -> None:
    if os.environ.get("HOOK_DEBUG") == "1":
        print(f"[fluency-4d] {message}", file=sys.stderr)


def hook_main(event: str):
    """Decorador: cualquier excepcion degrada a pass-through (nunca romper la sesion)."""

    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            try:
                return fn(*args, **kwargs)
            except Exception as exc:  # noqa: BLE001 - degradacion intencional
                log_debug(f"{event} hook error: {exc}")
                output_empty()

        return wrapper

    return decorator


# --- Estado por sesion (dedup) -------------------------------------------------


def session_key(data: dict) -> str:
    sid = data.get("session_id")
    if sid:
        return "sid-" + hashlib.sha256(str(sid).encode()).hexdigest()[:16]
    # Fallback por cwd. Limitacion conocida: dos sesiones concurrentes en el
    # mismo proyecto comparten estado y la segunda pierde la inyeccion. v1.
    return "cwd-" + hashlib.sha256(str(data.get("cwd", "")).encode()).hexdigest()[:16]


def _state_path(key: str) -> Path:
    directory = Path(tempfile.gettempdir()) / "fluency4d"
    directory.mkdir(parents=True, exist_ok=True)
    return directory / f"{key}.json"


def load_state(key: str) -> dict:
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


def load_caveman() -> dict:
    """Lee el flag global de modo caveman (~/.claude/fluency4d/caveman.json).

    Solo lectura. Devuelve el dict si esta prendido (on=True) y level es valido;
    ante cualquier error / JSON invalido / OFF / level fuera del set -> {}
    (pass-through). El writer es la tool Write del skill, no este helper.
    """
    path = Path.home() / ".claude" / "fluency4d" / "caveman.json"
    try:
        st = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(st, dict):
        return {}
    if st.get("on") is not True:
        return {}
    if st.get("level") not in ("auto", "lite", "full", "ultra"):
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


def save_state(key: str, state: dict) -> None:
    state["_ts"] = time.time()
    path = _state_path(key)
    payload = json.dumps(state, ensure_ascii=True)
    try:
        # Escritura ATOMICA: se escribe a un temporal en el MISMO directorio y
        # luego os.replace(tmp, dst) (atomico en Windows y POSIX). Asi un
        # load_state concurrente (memory_checkpoint y doc_drift disparan en
        # PostToolUse casi a la vez) nunca ve un JSON a medio escribir -> no hay
        # torn-write ni JSONDecodeError espurio que devuelva {} y pierda el
        # dedup. El lost-update residual (dos writes solapados, gana el ultimo)
        # es benigno y equivalente al ya aceptado en bump_stats: el estado es
        # senal de dedup best-effort, no contabilidad.
        fd, tmp = tempfile.mkstemp(
            dir=str(path.parent), prefix=path.name + ".", suffix=".tmp"
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(payload)
            os.replace(tmp, path)
        except OSError:
            try:
                os.unlink(tmp)  # limpieza best-effort si el replace fallo
            except OSError:
                pass
            raise
    except OSError as exc:
        log_debug(f"no se pudo guardar estado: {exc}")
