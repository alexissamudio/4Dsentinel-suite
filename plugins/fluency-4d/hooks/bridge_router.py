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
    bump_stats,
    hook_main,
    load_state,
    log_debug,
    output_context,
    output_empty,
    parse_hook_input,
    read_stdin_safe,
    safe_doc_path,
    sanitize_field,
    save_state,
    session_key,
)

MAX_TEMAS_POR_PROMPT = 2
MAX_RELACIONADOS = 1
MIN_KEYWORD_LEN = 3
ESTADO_VIEJO_SEGUNDOS = 24 * 60 * 60

# Verbo de relacion -> frase ASCII. Verbo desconocido cae en la frase neutra.
VERBOS = {
    "depende_de": "depende de",
    "va_con": "va con",
    "alimenta_a": "alimenta a",
}


def normalize(text: str) -> str:
    """casefold + sin acentos, para que 'autenticacion' matchee 'autenticacion'."""
    decomposed = unicodedata.normalize("NFKD", text)
    stripped = "".join(c for c in decomposed if not unicodedata.combining(c))
    return stripped.casefold()


def keyword_matches(keyword: str, norm_prompt: str) -> bool:
    kw = normalize(keyword.strip())
    if not kw:
        return False
    # Piso de longitud: evita que una keyword alfanumerica demasiado corta
    # genere falsos positivos. Una keyword con puntuacion (c++, .net, c#) es
    # especifica por construccion y NO debe caer por longitud.
    if kw.isalnum() and len(kw) < MIN_KEYWORD_LEN:
        return False
    # Lookarounds en vez de \b: \b nunca casa si la keyword empieza/termina en
    # un caracter no-palabra (c++, .net, c#), por lo que ese puente jamas se
    # inyectaba. (?<!\w)...(?!\w) exige solo que no haya un caracter de palabra
    # ADYACENTE, asi 'c++' matchea en el prompt pero 'auth' sigue sin matchear
    # como subcadena dentro de otra palabra.
    return re.search(r"(?<!\w)" + re.escape(kw) + r"(?!\w)", norm_prompt) is not None


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

    # Indice tema -> entry en una pasada COMPLETA y separada del loop de hits.
    # El loop de hits corta con break en el cap, asi que no sirve para resolver
    # destinos de relaciones mas alla del cap (un destino valido se marcaria
    # como dangling). Este indice recorre todos los temas validos.
    entry_por_tema: dict[str, dict] = {}
    for entry in temas:
        if not isinstance(entry, dict):
            continue
        tema = entry.get("tema")
        archivo = entry.get("archivo")
        keywords = entry.get("keywords")
        if not tema or not archivo or not isinstance(keywords, list):
            continue
        safe_archivo = safe_doc_path(archivo)
        if safe_archivo is None:
            # `archivo` hostil (absoluto / .. / ~ / con controles): NO se puentea
            # este tema, ni como hit directo ni como destino de relacion.
            continue
        entry_por_tema[tema] = {**entry, "archivo": safe_archivo}

    injected = set(state.get("temas_inyectados", []))
    norm_prompt = normalize(prompt)
    hits: list[tuple[str, str]] = []
    for tema, entry in entry_por_tema.items():
        if tema in injected:
            continue
        keywords = entry["keywords"]
        if any(keyword_matches(kw, norm_prompt) for kw in keywords if isinstance(kw, str)):
            hits.append((tema, entry["archivo"]))
            if len(hits) >= MAX_TEMAS_POR_PROMPT:
                break

    if not hits:
        return []
    injected.update(tema for tema, _ in hits)
    state["temas_inyectados"] = sorted(injected)
    lineas_directas = [
        f"Este proyecto documenta '{sanitize_field(tema)}' en `{sanitize_field(archivo)}`. "
        "LEE ese archivo ANTES de responder sobre este tema."
        for tema, archivo in hits
    ]

    # Pasada de relacionados: sugerir (no ordenar) el puente relacionado.
    # Guardas isinstance explicitas: una 'relaciones' malformada NUNCA debe
    # lanzar, o el catch-all del hook descartaria la inyeccion COMPLETA.
    # No toca state (G3): la sugerencia no consume el cap de temas ni se
    # marca como inyectada. Dedup local via 'sugeridos'.
    sugeridos: set[str] = set()
    lineas_sugerencia: list[str] = []
    for tema, _archivo in hits:
        if len(lineas_sugerencia) >= MAX_RELACIONADOS:
            break
        relaciones = entry_por_tema.get(tema, {}).get("relaciones")
        if not isinstance(relaciones, list):
            continue
        for rel in relaciones:
            if len(lineas_sugerencia) >= MAX_RELACIONADOS:
                break
            if not isinstance(rel, dict):
                continue
            rt = rel.get("tema")
            verbo = rel.get("verbo")
            if not rt:
                continue
            if rt in injected:  # G2: ya inyectado (previo o hit de este prompt)
                continue
            if rt in sugeridos:  # dedup local
                continue
            if rt not in entry_por_tema:  # G1: destino dangling
                continue
            frase = VERBOS.get(verbo, "se relaciona con")
            archivo_rt = entry_por_tema[rt]["archivo"]
            sugeridos.add(rt)
            lineas_sugerencia.append(
                f"Tema relacionado: '{sanitize_field(tema)}' {frase} "
                f"'{sanitize_field(rt)}' -- "
                f"quizas quieras leer `{sanitize_field(archivo_rt)}`."
            )

    return lineas_directas + lineas_sugerencia


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
    arranque_previo = bool(state.get("arranque_inyectado"))
    temas_previos = set(state.get("temas_inyectados", []))

    lines = arranque_lines(cwd, state) + tema_lines(cwd, prompt, state)

    # Punto de emision y persistencia unicos.
    if json.dumps(state, sort_keys=True, ensure_ascii=True) != state_before:
        save_state(key, state)
        # Telemetria: la sesion se cuenta en la TRANSICION del flag de
        # arranque (inyecte lineas o no); los temas, solo los nuevos.
        nueva_sesion = not arranque_previo and bool(state.get("arranque_inyectado"))
        temas_nuevos = sorted(set(state.get("temas_inyectados", [])) - temas_previos)
        if nueva_sesion or temas_nuevos:
            bump_stats(cwd_raw, temas_nuevos, nueva_sesion)
    if lines:
        lines.append("(inyectado por fluency-4d; no se repetira en esta sesion)")
        output_context("UserPromptSubmit", "\n".join(lines))
    else:
        output_empty()


if __name__ == "__main__":
    main()
