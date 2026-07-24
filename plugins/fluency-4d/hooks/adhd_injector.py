#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""adhd_injector.py - Hook UserPromptSubmit del plugin fluency-4d.

Modo ADHD/TDAH: estilo de comunicacion accionable y estructurado. Si el flag
global esta ON (~/.claude/fluency4d/adhd.json), reinyecta en CADA turno la
directiva del nivel elegido. Arranca APAGADO (opt-in via el skill /adhd).

A diferencia de plan_calibrator, NO usa edge-trigger: reinyecta siempre que
este ON, y eso es lo que da la persistencia del estilo entre turnos. La fuente
unica de verdad del estilo es el dict DIRECTIVA de aca; el skill solo escribe
el flag.

Precedencia: caveman gana si ambos flags estan ON (mutex de facto). Los
subagentes no reciben la directiva.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from hook_utils import (
    hook_main,
    load_adhd,
    load_caveman,
    output_context,
    output_empty,
    parse_hook_input,
    read_stdin_safe,
)

_PREFIJO = "[Modo TDAH/ADHD (fluency-4d) - salida accionable y estructurada]\n"

_INVARIANTE = (
    "Invariante (todos los niveles): no elimines pasos, advertencias ni detalles "
    "que cambien la correctitud del resultado. Codigo, comandos, rutas, "
    "identificadores, mensajes de error y URLs = byte-por-byte. Las reglas se "
    "relajan cuando el usuario pide una explicacion, cuando una accion destructiva "
    "necesita confirmacion, cuando hay ambiguedad real o un espiral de debugging. "
    "Conserva el idioma del usuario.\n"
)

DIRECTIVA = {
    "lite": (
        _PREFIJO
        + _INVARIANTE
        + "Nivel LITE (siempre-seguro): arranca por la accion concreta, no por el "
        "contexto. Sin preambulo, recap ni cortesias. Errores: causa y fix "
        "directos, tono matter-of-fact. Listas <=5 items; si hay mas, parti en "
        "niveles de prioridad. NO agregues restate-state ni estimaciones de tiempo."
    ),
    "full": (
        _PREFIJO
        + _INVARIANTE
        + "Nivel FULL: aplica LITE y ademas: numera las tareas multi-paso (cada "
        "paso = una accion acotada); recorda en 1 linea en que paso del plan estas "
        "(restate state); termina con UN next-step concreto hacible en menos de 2 "
        "minutos; da estimaciones de tiempo en unidades concretas; haz visible lo "
        "que ya funciona."
    ),
    "auto": (
        _PREFIJO
        + _INVARIANTE
        + "Nivel AUTO (autocalibracion por turno): en un turno de tarea multi-paso "
        "aplica FULL (numerar, restate-state, next-step, estimacion). En una "
        "consulta corta, una explicacion o un estado ya-hecho aplica LITE: solo "
        "las reglas siempre-seguras, y NO uses restate-state ni estimaciones de "
        "tiempo (en turnos cortos son ruido o precision falsa)."
    ),
}


@hook_main("UserPromptSubmit")
def main() -> None:
    data = parse_hook_input(read_stdin_safe())
    if not data:
        return output_empty()
    if data.get("agent_type"):  # subagentes: no imponer el modo
        return output_empty()
    if load_caveman():  # caveman gana si ambos estan ON
        return output_empty()

    st = load_adhd()
    if not st:
        return output_empty()

    output_context("UserPromptSubmit", DIRECTIVA[st["level"]])


if __name__ == "__main__":
    main()
