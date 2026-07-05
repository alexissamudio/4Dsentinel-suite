#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""caveman_injector.py - Hook UserPromptSubmit del plugin fluency-4d.

Modo Caveman: estilo de comunicacion token-eficiente. Si el flag global esta ON
(~/.claude/fluency4d/caveman.json), reinyecta en CADA turno la directiva del
nivel elegido. Arranca APAGADO (opt-in via el skill /caveman).

A diferencia de plan_calibrator, NO usa edge-trigger: reinyecta siempre que
este ON, y eso es lo que da la persistencia del estilo entre turnos. La fuente
unica de verdad del estilo es el dict DIRECTIVA de aca; el skill solo escribe
el flag.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from hook_utils import (
    hook_main,
    load_caveman,
    output_context,
    output_empty,
    parse_hook_input,
    read_stdin_safe,
)

_PREFIJO = "[Modo Caveman (fluency-4d) - comunicacion token-eficiente]\n"

_INVARIANTE = (
    "Invariante (todos los niveles): codigo, comandos, rutas, identificadores, "
    "mensajes de error y URLs = byte-por-byte, JAMAS comprimir ni abreviar. "
    "Conserva el idioma del usuario. No omitas pasos ni advertencias que cambien "
    "la correctitud del resultado.\n"
)

DIRECTIVA = {
    "lite": (
        _PREFIJO
        + _INVARIANTE
        + "Nivel LITE: saca relleno, hedging y cortesias, pero manten oraciones "
        "completas y gramaticales. Prosa mas seca, misma informacion."
    ),
    "full": (
        _PREFIJO
        + _INVARIANTE
        + "Nivel FULL: sintaxis fragmentada estilo telegrama. Corta articulos y "
        "conectores cuando no genere ambiguedad. Frases cortas, directo al punto."
    ),
    "ultra": (
        _PREFIJO
        + _INVARIANTE
        + "Nivel ULTRA: compresion maxima, telegrafico. Fragmentos en vinetas, "
        "sin oraciones completas. Solo lo esencial. Cero relleno."
    ),
    "auto": (
        _PREFIJO
        + _INVARIANTE
        + "Nivel AUTO (autocalibracion por respuesta): elegi el nivel segun el "
        "tipo de respuesta. Explicacion o ensenanza -> estilo LITE (prima la "
        "claridad). Confirmacion, status o comando corto -> ULTRA. El resto -> "
        "FULL. Ademas, si la sesion viene larga o el contexto se esta llenando, "
        "subi un escalon de compresion."
    ),
}


@hook_main("UserPromptSubmit")
def main() -> None:
    data = parse_hook_input(read_stdin_safe())
    if not data:
        return output_empty()
    if data.get("agent_type"):  # subagentes: no imponer caveman
        return output_empty()

    st = load_caveman()
    if not st:
        return output_empty()

    output_context("UserPromptSubmit", DIRECTIVA[st["level"]])


if __name__ == "__main__":
    main()
