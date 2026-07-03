#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""bridge_router.py - Hook UserPromptSubmit del plugin fluency-4d.

Dos responsabilidades, ambas con dedup por sesion:

1. Arranque (primer prompt de la sesion): si el proyecto tiene
   .claude/docs/lecciones.md o estado-sesion.md, inyecta la instruccion de
   leerlos (nombrando SOLO los que existen, con edad para el estado).
2. Puentes por tema: si el prompt menciona una keyword de bridges.json,
   inyecta la instruccion de leer el doc del tema antes de responder.

Estructura de punto de emision unico: las dos fuentes de lineas se calculan
por separado y se emiten juntas al final; save_state se llama exactamente
una vez cuando el estado cambio.
"""

from __future__ import annotations

import json
import re
import sys
import time
import unicodedata
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

MAX_TEMAS_POR_PROMPT = 2
MIN_KEYWORD_LEN = 3
ESTADO_VIEJO_SEGUNDOS = 24 * 60 * 60


def normalize(text: str) -> str:
    """casefold + sin acentos, para que 'autenticación' matchee 'autenticacion'."""
    decomposed = unicodedata.normalize("NFKD", text)
    stripped = "".join(c for c in decomposed if not unicodedata.combining(c))
    return stripped.casefold()


def keyword_matches(keyword: str, norm_prompt: str) -> bool:
    kw = normalize(keyword.strip())
    if len(kw) < MIN_KEYWORD_LEN:
        return False
    return re.search(r"\b" + re.escape(kw) + r"\b", norm_prompt) is not None


def arranque_lines(cwd: Path, state: dict) -> list[str]:
    """Primer prompt de la sesion: senalar lecciones y estado previo si existen.

    Marca 'arranque_inyectado' aunque no exista ninguno, para no re-chequear
    el filesystem en cada prompt.
    """
    if state.get("arranque_inyectado"):
        return []
    state["arranque_inyectado"] = True

    lines: list[str] = []
    lecciones = cwd / ".claude" / "docs" / "lecciones.md"
    if lecciones.is_file():
        lines.append(
            "Este proyecto tiene lecciones aprendidas en `.claude/docs/lecciones.md`: "
            "leelas antes de empezar a trabajar."
        )
    estado = cwd / ".claude" / "docs" / "estado-sesion.md"
    if estado.is_file():
        try:
            age_seconds = time.time() - estado.stat().st_mtime
        except OSError:
            age_seconds = 0.0
        if age_seconds > ESTADO_VIEJO_SEGUNDOS:
            dias = int(age_seconds // 86400)
            lines.append(
                "Hay un estado guardado en `.claude/docs/estado-sesion.md`, pero es de "
                f"una sesion anterior (hace {dias} dia(s)): verifica su vigencia antes "
                "de asumir pendientes."
            )
        else:
            lines.append(
                "Hay un estado de sesion reciente en `.claude/docs/estado-sesion.md`: "
                "leelo para retomar el contexto."
            )
    return lines


def tema_lines(cwd: Path, prompt: str, state: dict) -> list[str]:
    """Puentes por tema segun bridges.json; puede devolver vacio por cualquier motivo."""
    bridges_path = cwd / ".claude" / "docs" / "bridges.json"
    if not bridges_path.is_file():
        return []
    try:
        bridges = json.loads(bridges_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        log_debug(f"bridges.json ilegible: {exc}")
        return []
    temas = bridges.get("temas")
    if not isinstance(temas, list):
        return []

    injected = set(state.get("temas_inyectados", []))
    norm_prompt = normalize(prompt)
    hits: list[tuple[str, str]] = []
    for entry in temas:
        if not isinstance(entry, dict):
            continue
        tema = entry.get("tema")
        archivo = entry.get("archivo")
        keywords = entry.get("keywords")
        if not tema or not archivo or not isinstance(keywords, list):
            continue
        if tema in injected:
            continue
        if any(keyword_matches(kw, norm_prompt) for kw in keywords if isinstance(kw, str)):
            hits.append((tema, archivo))
            if len(hits) >= MAX_TEMAS_POR_PROMPT:
                break

    if not hits:
        return []
    injected.update(tema for tema, _ in hits)
    state["temas_inyectados"] = sorted(injected)
    return [
        f"Este proyecto documenta '{tema}' en `{archivo}`. "
        "LEE ese archivo ANTES de responder sobre este tema."
        for tema, archivo in hits
    ]


@hook_main("UserPromptSubmit")
def main() -> None:
    data = parse_hook_input(read_stdin_safe())
    if not data:
        return output_empty()
    if data.get("agent_type"):  # subagentes: no inyectar
        return output_empty()

    prompt = data.get("prompt") or ""
    cwd_raw = data.get("cwd") or ""
    if not prompt or not cwd_raw:
        return output_empty()
    cwd = Path(cwd_raw)

    key = session_key(data)
    state = load_state(key)
    state_before = json.dumps(state, sort_keys=True, ensure_ascii=True)

    lines = arranque_lines(cwd, state) + tema_lines(cwd, prompt, state)

    # Punto de emision y persistencia unicos.
    if json.dumps(state, sort_keys=True, ensure_ascii=True) != state_before:
        save_state(key, state)
    if lines:
        lines.append("(inyectado por fluency-4d; no se repetira en esta sesion)")
        output_context("UserPromptSubmit", "\n".join(lines))
    else:
        output_empty()


if __name__ == "__main__":
    main()
