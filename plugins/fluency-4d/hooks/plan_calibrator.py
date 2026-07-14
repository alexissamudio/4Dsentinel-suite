#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""plan_calibrator.py - Hook UserPromptSubmit del plugin fluency-4d.

Ultraplan CALIBRADO por 4D: al ENTRAR en plan mode, inyecta un protocolo que hace
a Claude calibrar el tamano de la tarea (Delegacion del marco 4D) y aplicar rigor
proporcional - tarea grande => flujo riguroso (advisor -> plan -> critic con los
agentes de sentinel-agents); tarea chica => planificacion liviana.

A diferencia del ultraplan de oh-my-claude (que dispara la ceremonia en TODO plan
mode), este distingue. La inteligencia esta en el protocolo inyectado: el hook solo
lo emite; la clasificacion la hace Claude.

Edge-trigger: dispara SOLO en la transicion no-plan -> plan (entrada a plan mode),
se calla en los prompts siguientes del mismo episodio, y se re-arma al salir y
volver a entrar (asi la 2da/3ra tarea de planificacion de la sesion tambien recibe
el protocolo).
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from hook_utils import (
    hook_main,
    load_state,
    output_context,
    output_empty,
    parse_hook_input,
    read_stdin_safe,
    save_state,
    session_key,
)

PROTOCOLO = (
    "[Calibrador de plan (fluency-4d) - Delegacion 4D aplicada a planificar]\n"
    "Antes de planificar, CLASIFICA la tarea:\n"
    "- GRANDE: feature nueva, release, refactor, cambio de arquitectura, algo de "
    "varios pasos, o riesgoso/irreversible. Ante la duda, mira el blast-radius y "
    "sesga hacia GRANDE.\n"
    "- CHICA: fix puntual, typo, edicion de una linea, consulta, cambio trivial.\n"
    "Si es CHICA: planifica LIVIANO - entende, hace, verifica. NO invoques advisor/"
    "critic ni una ceremonia de varios pasos.\n"
    "Si es GRANDE: flujo RIGUROSO - recon -> (opcional entrevista) -> advisor "
    "(gap analysis) -> escribi el plan -> critic (revision) -> recien ExitPlanMode. "
    "Si tenes el plugin sentinel-agents instalado, delega en sentinel-agents:advisor "
    "(gap analysis pre-plan) y sentinel-agents:critic (revision del plan); son "
    "read-only: analizan y revisan, no editan el plan.\n"
    "El rigor es PROPORCIONAL al tamano: no impongas la ceremonia sobre lo trivial."
)


@hook_main("UserPromptSubmit")
def main() -> None:
    data = parse_hook_input(read_stdin_safe())
    if not data:
        return output_empty()
    if data.get("agent_type"):  # subagentes: no inyectar
        return output_empty()

    current = data.get("permission_mode")
    key = session_key(data) + "-calib"
    state = load_state(key)
    prev = state.get("last_mode")

    # Edge-trigger: solo en la transicion no-plan -> plan.
    fire = current == "plan" and prev != "plan"
    state["last_mode"] = current
    save_state(key, state)

    if fire:
        output_context("UserPromptSubmit", PROTOCOLO)
    else:
        output_empty()


if __name__ == "__main__":
    main()
