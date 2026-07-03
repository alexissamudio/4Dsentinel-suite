#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""memory_checkpoint.py - Hook PostToolUse del plugin fluency-4d.

Al cruzar el umbral de contexto (default 50%, env FLUENCY_4D_SAVE_PCT; "0"
desactiva), inyecta UNA vez por sesion la instruccion de guardar el estado en
.claude/docs/estado-sesion.md y consolidar lecciones en lecciones.md.

El hook solo inyecta la instruccion: Claude (que si sabe que es importante)
escribe los archivos. Limitacion v1 documentada: no se re-arma tras una
compactacion (una vez por sesion).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from hook_utils import (
    hook_main,
    load_state,
    log_debug,
    output_context,
    output_empty,
    parse_hook_input,
    read_stdin_safe,
    save_state,
    session_key,
)

DEFAULT_THRESHOLD = 50
CONTEXT_LIMIT_TOKENS = 200_000


def usage_percentage(data: dict) -> float | None:
    """Porcentaje de contexto usado.

    Preferencia: campo nativo context_window.used_percentage. Fallback
    (verificado: el campo no viene en todas las versiones de Claude Code):
    estimacion conservadora por tamano del archivo de transcript
    (bytes/4 ~ tokens sobre 200k; el overhead del JSONL infla la estimacion,
    asi que dispara un poco antes, nunca despues).
    """
    context_window = data.get("context_window")
    if isinstance(context_window, dict):
        pct = context_window.get("used_percentage")
        if isinstance(pct, (int, float)):
            return float(pct)

    transcript_path = data.get("transcript_path")
    if transcript_path:
        try:
            size_bytes = Path(transcript_path).stat().st_size
        except OSError as exc:
            log_debug(f"transcript_path ilegible: {exc}")
            return None
        estimated_tokens = size_bytes / 4
        log_debug(f"estimacion por transcript: {size_bytes} bytes ~ {estimated_tokens:.0f} tokens")
        return min(100.0, estimated_tokens / CONTEXT_LIMIT_TOKENS * 100)

    log_debug("sin context_window.used_percentage ni transcript_path")
    return None


def parse_threshold() -> int:
    raw = os.environ.get("FLUENCY_4D_SAVE_PCT", str(DEFAULT_THRESHOLD))
    try:
        return int(float(raw))
    except (TypeError, ValueError):
        # Un valor basura no debe desactivar el hook para siempre via hook_main.
        log_debug(f"FLUENCY_4D_SAVE_PCT invalido ({raw!r}), usando {DEFAULT_THRESHOLD}")
        return DEFAULT_THRESHOLD


def checkpoint_text(pct: float) -> str:
    return (
        f"Contexto ~{pct:.0f}% usado (fluency-4d). Al completar el paso actual: "
        "1) guarda el estado en `.claude/docs/estado-sesion.md` (encabezado con "
        "fecha, objetivo/frase 4D, decisiones tomadas, pendientes); "
        "2) si hubo correcciones del usuario o errores cazados, consolida las "
        "lecciones en `.claude/docs/lecciones.md` (max ~30; fusiona duplicadas). "
        "Despues continua con la tarea. Este aviso no se repetira en esta sesion."
    )


@hook_main("PostToolUse")
def main() -> None:
    data = parse_hook_input(read_stdin_safe())
    if not data:
        return output_empty()
    if data.get("agent_type"):  # subagentes: nunca inyectar
        return output_empty()

    threshold = parse_threshold()
    if threshold <= 0:  # desactivado
        return output_empty()

    # En plan mode Claude no puede escribir archivos: saltear SIN marcar el
    # umbral como disparado, para que dispare al salir de plan mode.
    if data.get("permission_mode") == "plan":
        return output_empty()

    cwd = data.get("cwd") or ""
    if not cwd or not (Path(cwd) / ".claude").is_dir():
        return output_empty()

    pct = usage_percentage(data)
    if pct is None:
        return output_empty()

    if pct < threshold:
        return output_empty()

    key = session_key(data) + "-ckpt"  # estado propio: no compartir con el router
    state = load_state(key)
    if state.get("checkpoint_disparado"):
        return output_empty()

    state["checkpoint_disparado"] = True
    save_state(key, state)
    output_context("PostToolUse", checkpoint_text(float(pct)))


if __name__ == "__main__":
    main()
