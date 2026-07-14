#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""memory_checkpoint.py - Hook PostToolUse del plugin fluency-4d.

Al cruzar el umbral de contexto (default 50%, env FLUENCY_4D_SAVE_PCT; "0"
desactiva), inyecta la instruccion de guardar el estado en
.claude/docs/estado-sesion.md y consolidar lecciones en lecciones.md.

Re-armado dual (v0.3):
- Modo nativo (context_window.used_percentage presente): una caida de >20
  puntos = compactacion detectada -> se re-arma y vuelve a disparar al cruzar
  el umbral. Una compactacion que cae <20 puntos no re-arma (tolerancia
  aceptada).
- Modo fallback (estimacion por tamano del transcript, append-only: el %
  nunca baja): re-dispara por intervalo de tokens (~cada {umbral}% de
  contexto acumulado). Si el archivo se achica (se reseteo), el intervalo
  se re-ancla.

El hook solo inyecta la instruccion: Claude escribe los archivos. El estado
se escribe en cada tool call (refresca el TTL de 4 h en sesiones activas:
efecto benigno).
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
NATIVE_DROP_POINTS = 20  # caida de % que interpretamos como compactacion


def usage_value(data: dict) -> tuple[float, bool] | None:
    """Devuelve (valor, es_nativo): pct nativo, o tokens estimados SIN cap."""
    context_window = data.get("context_window")
    if isinstance(context_window, dict):
        pct = context_window.get("used_percentage")
        if isinstance(pct, (int, float)):
            return float(pct), True

    transcript_path = data.get("transcript_path")
    if transcript_path:
        try:
            size_bytes = Path(transcript_path).stat().st_size
        except OSError as exc:
            log_debug(f"transcript_path ilegible: {exc}")
            return None
        estimated_tokens = size_bytes / 4
        log_debug(f"estimacion por transcript: {size_bytes} bytes ~ {estimated_tokens:.0f} tokens")
        return estimated_tokens, False

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
        f"Contexto ~{min(pct, 100.0):.0f}% usado (fluency-4d). Al completar el paso actual: "
        "1) guarda el estado en `.claude/docs/estado-sesion.md` (encabezado con "
        "fecha, objetivo/frase 4D, decisiones tomadas, pendientes); "
        "2) si hubo correcciones del usuario o errores cazados, consolida las "
        "lecciones en `.claude/docs/lecciones.md` (max ~30; fusiona duplicadas). "
        "Despues continua con la tarea. Este aviso puede repetirse tras avanzar "
        "otro tramo de contexto o tras una compactacion."
    )


@hook_main("PostToolUse")
def main() -> None:
    data = parse_hook_input(read_stdin_safe())
    if not data:
        return output_empty()
    if data.get("agent_type"):  # subagentes: nunca inyectar
        return output_empty()

    threshold = parse_threshold()  # recalculado en cada corrida (env puede cambiar)
    if threshold <= 0:  # desactivado
        return output_empty()

    # En plan mode Claude no puede escribir archivos: saltear SIN tocar el
    # estado, para que dispare al salir de plan mode.
    if data.get("permission_mode") == "plan":
        return output_empty()

    cwd = data.get("cwd") or ""
    if not cwd or not (Path(cwd) / ".claude").is_dir():
        return output_empty()

    usage = usage_value(data)
    if usage is None:
        return output_empty()
    value, es_nativo = usage

    key = session_key(data) + "-ckpt"
    state = load_state(key)
    fire = False

    if es_nativo:
        pct = value
        last_seen = float(state.get("last_seen_pct", 0))
        if pct < last_seen - NATIVE_DROP_POINTS:
            state["fired"] = False  # compactacion detectada: re-armar
        state["last_seen_pct"] = pct
        if pct >= threshold and not state.get("fired"):
            state["fired"] = True
            fire = True
        display_pct = pct
    else:
        tokens = value
        interval = threshold / 100 * CONTEXT_LIMIT_TOKENS
        last_seen = float(state.get("last_seen_tokens", 0))
        last_fired = float(state.get("last_fired_tokens", 0))
        # Migracion desde estado v0.2: el flag viejo sin ancla de tokens
        # sembraria un disparo duplicado post-upgrade.
        if state.get("checkpoint_disparado") and "last_fired_tokens" not in state:
            last_fired = tokens
            state["last_fired_tokens"] = tokens
        if tokens < last_seen * 0.5:  # el transcript se reseteo
            last_fired = 0.0
            state["last_fired_tokens"] = 0.0
        state["last_seen_tokens"] = tokens
        if tokens >= last_fired + interval:
            state["last_fired_tokens"] = tokens
            fire = True
        display_pct = tokens / CONTEXT_LIMIT_TOKENS * 100

    if fire:
        state["disparos"] = int(state.get("disparos", 0)) + 1
    save_state(key, state)  # last_seen se persiste SIEMPRE, en ambos modos

    if fire:
        output_context("PostToolUse", checkpoint_text(display_pct))
    else:
        output_empty()


if __name__ == "__main__":
    main()
