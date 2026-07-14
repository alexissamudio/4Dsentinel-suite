#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""suite_playbook.py - Hook UserPromptSubmit del plugin fluency-4d.

"El conductor OFRECE, el humano confirma." Con keywords ESTRECHAS (frases
especificas, no anchas), inyecta un NUDGE que le sugiere al conductor que
PROPONGA una capacidad de la suite (indexar con el grafo, o auditar) en el
momento justo, para que el usuario tipee menos comandos.

El nudge NUNCA dispara una accion: solo le recuerda al conductor que ofrezca;
el humano decide. Guardarrailes (filosofia #3/#6):
- Dedup una vez por TIPO por sesion (set nudges_dados): no insiste.
- No dispara en plan mode (plan_calibrator ya cubre ese momento).
- No dispara en subagentes (agent_type).

Reusa normalize/keyword_matches de bridge_router (mismo patron de matcheo con
lookarounds y sin acentos) y load_state/save_state/session_key de hook_utils.
ASCII puro: cp1252 en Windows, sin acentos en strings.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from bridge_router import keyword_matches, normalize
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

# Cada cluster: (tipo, frases ESTRECHAS que lo disparan, nudge a inyectar).
# Las frases son multi-palabra a proposito (critic #3/#4): una keyword ancha
# como "revisar" o "antes de" quema el dedup con falsos positivos y sesga a
# codigo. El nudge es afirmativo ("PROPONE X; si confirma, hacelo"): forma mas
# robusta que el doble-negativo. Nunca ordena una accion.
CLUSTERS = (
    (
        "indexar",
        (
            "entender este repo",
            "mapear el codebase",
            "onboarding del proyecto",
            "explorar la arquitectura",
        ),
        "El usuario quiere entender el repo. PROPONE al humano indexar con el "
        "grafo (/indexar, /arquitectura); si confirma, hacelo. No indexes sin "
        "confirmar.",
    ),
    (
        "auditar",
        (
            "voy a mergear",
            "antes de commitear",
            "revisar este diff",
            "revisar este pr",
            "listo para release",
        ),
        "Suena a paso previo a mergear CODIGO. PROPONE auditar (code-reviewer + "
        "validator, o /sentinel-audit). Si el entregable es TEXTO "
        "(spec/doc/politica), propone auditor-de-redaccion en su lugar. Opt-in.",
    ),
)


@hook_main("UserPromptSubmit")
def main() -> None:
    data = parse_hook_input(read_stdin_safe())
    if not data:
        return output_empty()
    if data.get("agent_type"):  # subagentes: no inyectar
        return output_empty()
    if data.get("permission_mode") == "plan":  # plan_calibrator ya cubre plan mode
        return output_empty()

    prompt = data.get("prompt") or ""
    if not prompt:
        return output_empty()

    key = session_key(data) + "-playbook"
    state = load_state(key)
    dados = set(state.get("nudges_dados", []))

    norm_prompt = normalize(prompt)
    lines: list[str] = []
    for tipo, frases, nudge in CLUSTERS:
        if tipo in dados:  # dedup: una vez por tipo por sesion
            continue
        if any(keyword_matches(frase, norm_prompt) for frase in frases):
            lines.append(nudge)
            dados.add(tipo)

    if not lines:
        return output_empty()

    state["nudges_dados"] = sorted(dados)
    save_state(key, state)
    lines.append("(sugerencia de fluency-4d; ofrecelo, no lo hagas sin confirmar)")
    output_context("UserPromptSubmit", "\n".join(lines))


if __name__ == "__main__":
    main()
