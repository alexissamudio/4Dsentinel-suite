#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""bridge_router.py - Hook UserPromptSubmit del plugin fluency-4d.

Si el proyecto tiene .claude/docs/bridges.json y el prompt del usuario menciona
una keyword de algun tema, inyecta la instruccion de leer el doc del tema antes
de responder. Dedup por sesion: cada tema se inyecta una sola vez.
"""

from __future__ import annotations

import json
import re
import sys
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


@hook_main("UserPromptSubmit")
def main() -> None:
    data = parse_hook_input(read_stdin_safe())
    if not data:
        return output_empty()
    if data.get("agent_type"):  # subagentes: no inyectar
        return output_empty()

    prompt = data.get("prompt") or ""
    cwd = data.get("cwd") or ""
    if not prompt or not cwd:
        return output_empty()

    bridges_path = Path(cwd) / ".claude" / "docs" / "bridges.json"
    if not bridges_path.is_file():  # proyecto sin puentes: no-op rapido
        return output_empty()

    try:
        bridges = json.loads(bridges_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        log_debug(f"bridges.json ilegible: {exc}")
        return output_empty()

    temas = bridges.get("temas")
    if not isinstance(temas, list):
        return output_empty()

    key = session_key(data)
    state = load_state(key)
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
        return output_empty()

    lines = [
        f"Este proyecto documenta '{tema}' en `{archivo}`. "
        "LEE ese archivo ANTES de responder sobre este tema."
        for tema, archivo in hits
    ]
    lines.append("(puente inyectado por fluency-4d; no se repetira en esta sesion)")

    injected.update(tema for tema, _ in hits)
    state["temas_inyectados"] = sorted(injected)
    save_state(key, state)

    output_context("UserPromptSubmit", "\n".join(lines))


if __name__ == "__main__":
    main()
