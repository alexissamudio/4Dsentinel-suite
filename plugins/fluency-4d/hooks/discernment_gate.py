#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""discernment_gate.py - Hook Stop OPT-IN del plugin fluency-4d.

Apagado por defecto. Con FLUENCY_4D_STRICT=1, bloquea UNA vez por sesion con la
checklist de discernimiento de las 4D antes de dejar terminar la tarea.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from hook_utils import (
    hook_main,
    load_state,
    output_empty,
    output_stop_block,
    parse_hook_input,
    read_stdin_safe,
    save_state,
    session_key,
)

CHECKLIST = (
    "DISCERNIMIENTO (fluency-4d, modo estricto) - antes de terminar, verifica y "
    "reporta en tu respuesta final: "
    "1) PRODUCT: el resultado cumple el criterio de exito pedido (correcto, completo, apropiado). "
    "2) PROCESS: toda cifra, cita o fuente que no dio el usuario esta verificada o marcada como NO VERIFICADA. "
    "3) PERFORMANCE: se mantuvo el rol/tono/formato pedido de punta a punta. "
    "Si algo no pasa, corregilo ahora; si pasa, termina normalmente e incluye una "
    "linea 'Discernimiento: OK' con lo verificado. Este gate no volvera a bloquear en esta sesion."
)


@hook_main("Stop")
def main() -> None:
    if os.environ.get("FLUENCY_4D_STRICT") != "1":
        return output_empty()

    data = parse_hook_input(read_stdin_safe())
    # Guarda canonica anti-bucle, independiente del archivo de estado.
    if data.get("stop_hook_active"):
        return output_empty()
    if data.get("agent_type"):
        return output_empty()

    key = session_key(data)
    state = load_state(key)
    if state.get("gate_bloqueado"):
        return output_empty()

    state["gate_bloqueado"] = True
    save_state(key, state)
    output_stop_block(CHECKLIST)


if __name__ == "__main__":
    main()
