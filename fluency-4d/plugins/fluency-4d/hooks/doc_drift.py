#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""doc_drift.py - Hook PostToolUse (Edit|Write|MultiEdit|NotebookEdit) de fluency-4d.

Si se edita un archivo bajo las `rutas` de un tema de bridges.json, inyecta
(una vez por tema por sesion) el recordatorio de revisar el doc del tema al
terminar la tarea. Temas sin `rutas` no se trackean (proyectos v0.2: re-correr
/4d-init para activarlo).

Matching por segmento: `src/auth` matchea `src/auth/x.py` y el archivo exacto
`src/auth`, pero NO `src/authentication/x.py`. Case-insensitive (NTFS).
"""

from __future__ import annotations

import json
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


def prefix_matches(rel_posix: str, prefix: str) -> bool:
    prefix = prefix.strip().casefold().rstrip("/")
    if not prefix:
        return False
    return rel_posix == prefix or rel_posix.startswith(prefix + "/")


@hook_main("PostToolUse")
def main() -> None:
    data = parse_hook_input(read_stdin_safe())
    if not data:
        return output_empty()
    if data.get("agent_type"):
        return output_empty()

    cwd_raw = data.get("cwd") or ""
    tool_input = data.get("tool_input") or {}
    file_raw = tool_input.get("file_path") or tool_input.get("notebook_path") or ""
    if not cwd_raw or not file_raw:
        return output_empty()

    cwd = Path(cwd_raw).resolve()
    file_path = Path(file_raw)
    if not file_path.is_absolute():
        file_path = cwd / file_path  # relativa: contra el cwd del payload
    file_path = file_path.resolve()

    try:
        rel = file_path.relative_to(cwd)
    except ValueError:  # fuera del proyecto
        return output_empty()

    rel_posix = rel.as_posix().casefold()
    if ".claude/" in rel_posix + "/":  # nunca avisar por ediciones bajo .claude/
        return output_empty()

    bridges_path = cwd / ".claude" / "docs" / "bridges.json"
    if not bridges_path.is_file():
        return output_empty()
    try:
        bridges = json.loads(bridges_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        log_debug(f"bridges.json ilegible: {exc}")
        return output_empty()
    temas = bridges.get("temas")
    if not isinstance(temas, list):
        return output_empty()

    key = session_key(data) + "-drift"
    state = load_state(key)
    avisados = set(state.get("temas_avisados", []))

    for entry in temas:
        if not isinstance(entry, dict):
            continue
        tema = entry.get("tema")
        archivo = entry.get("archivo")
        rutas = entry.get("rutas")
        if not tema or not archivo or not isinstance(rutas, list) or not rutas:
            continue  # tema sin rutas: no se trackea
        if tema in avisados:
            continue
        if any(prefix_matches(rel_posix, r) for r in rutas if isinstance(r, str)):
            avisados.add(tema)
            state["temas_avisados"] = sorted(avisados)
            save_state(key, state)
            return output_context(
                "PostToolUse",
                f"Editaste archivos del tema '{tema}'. Cuando termines la tarea "
                f"actual, revisa si `{archivo}` sigue vigente y actualizalo si el "
                "cambio afecta lo documentado. (fluency-4d; una vez por tema por sesion)",
            )

    output_empty()


if __name__ == "__main__":
    main()
