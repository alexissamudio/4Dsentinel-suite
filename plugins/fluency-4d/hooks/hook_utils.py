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
import sys
import tempfile
import threading
import time
from pathlib import Path

MAX_STDIN_BYTES = 1024 * 1024
STATE_TTL_SECONDS = 4 * 60 * 60  # 4 horas


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


def save_state(key: str, state: dict) -> None:
    state["_ts"] = time.time()
    try:
        _state_path(key).write_text(
            json.dumps(state, ensure_ascii=True), encoding="utf-8"
        )
    except OSError as exc:
        log_debug(f"no se pudo guardar estado: {exc}")
