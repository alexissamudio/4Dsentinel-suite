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

Evento: UserPromptSubmit (matcher .*), registrado en hooks/hooks.json.
Stdin: payload del evento; usa `prompt`, `cwd`, `agent_type` y `session_id`
(o `cwd`) para la clave de estado.
Stdout: un unico additionalContext con las lineas de arranque y de temas, mas
un trailer "(inyectado por fluency-4d; no se repetira en esta sesion)".
Lee (solo lectura) del proyecto: .claude/docs/lecciones.md, estado-sesion.md
(su mtime) y bridges.json. Estado: <temp>/fluency4d/<clave>-bridge.json con
`arranque_inyectado` y `temas_inyectados`. Telemetria: ~/.claude/fluency4d/
stats.json via bump_stats (sesion nueva y temas nuevos).
Pass-through: payload vacio o invalido, subagente, `prompt` o `cwd` vacios (o
`cwd` que no es string), o nada nuevo que inyectar (en ese caso el estado igual
se guarda si cambio). Un `prompt` no vacio que no es string (123, lista, dict)
cuenta como "" para las keywords, pero el arranque se inyecta igual.

Lo importa tambien suite_playbook (normalize y keyword_matches): cambiar su
firma rompe ese hook.
"""

from __future__ import annotations

import json
import re
import sys
import time
import unicodedata
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))

from hook_utils import (
    bump_stats,
    hook_main,
    load_bridges_temas,
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
    str_list,
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
    """casefold + sin acentos (NFKD sin marcas combinantes).

    Se aplica a la keyword Y al prompt, asi un prompt con tildes o mayusculas
    matchea una keyword escrita sin ellas, y viceversa.
    """
    decomposed = unicodedata.normalize("NFKD", text)
    stripped = "".join(c for c in decomposed if not unicodedata.combining(c))
    return stripped.casefold()


def keyword_matches(keyword: str, norm_prompt: str) -> bool:
    """True si `keyword` aparece como palabra (o frase) completa en el prompt.

    Args:
        keyword: keyword cruda de bridges.json (o frase de suite_playbook); se
            normaliza aca.
        norm_prompt: el prompt YA pasado por normalize (se hace una vez por prompt).
    """
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


def arranque_lines(cwd: Path, state: dict[str, Any]) -> list[str]:
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


def tema_lines(cwd: Path, prompt: str, state: dict[str, Any]) -> list[str]:
    """Puentes por tema segun bridges.json; puede devolver vacio por cualquier motivo.

    Muta `state["temas_inyectados"]` con los hits de este prompt (a lo sumo
    MAX_TEMAS_POR_PROMPT). Ademas puede sugerir hasta MAX_RELACIONADOS temas
    relacionados, que NO se marcan como inyectados. Temas con `archivo` inseguro
    (ver safe_doc_path) se descartan enteros. Un bridges.json que no es un objeto
    con `temas` lista se trata como sin puentes, y las entradas malformadas se
    ignoran: nada de esto lanza.

    La lectura va por load_bridges_temas (hook_utils): BOM UTF-8 tolerado, JSON
    invalido / anidado profundo (RecursionError) / no-objeto -> sin puentes, y
    topes MAX_BRIDGES_BYTES (archivo mas pesado: se ignora) y MAX_BRIDGES_TEMAS
    (solo los primeros temas) para no pasarse del timeout de 5 s del hook, que
    se llevaria puesta tambien la inyeccion de arranque. Un `state` con
    `temas_inyectados` de tipo raro se trata como lista vacia (str_list).
    """
    if not prompt:
        return []  # sin texto (o prompt no-string, ver main): ninguna keyword matchea
    temas = load_bridges_temas(cwd)
    if not temas:
        return []

    # Indice tema -> entry en una pasada COMPLETA y separada del loop de hits.
    # El loop de hits corta con break en el cap, asi que no sirve para resolver
    # destinos de relaciones mas alla del cap (un destino valido se marcaria
    # como dangling). Este indice recorre todos los temas validos.
    entry_por_tema: dict[str, dict[str, Any]] = {}
    for entry in temas:
        if not isinstance(entry, dict):
            continue
        tema = entry.get("tema")
        archivo = entry.get("archivo")
        keywords = entry.get("keywords")
        # `tema` se usa como clave de dict; un valor no-hasheable (lista/dict)
        # lanzaria TypeError y degradaria TODO el puenteo en silencio. Exigir str
        # tanto en tema como en archivo cierra esa via.
        if not isinstance(tema, str) or not isinstance(archivo, str):
            continue
        if not tema or not archivo or not isinstance(keywords, list):
            continue
        safe_archivo = safe_doc_path(archivo)
        if safe_archivo is None:
            # `archivo` hostil (absoluto / .. / ~ / con controles): NO se puentea
            # este tema, ni como hit directo ni como destino de relacion.
            continue
        if tema in entry_por_tema:
            # Tema duplicado: quedarse con el PRIMERO (no last-wins silencioso).
            log_debug(f"tema duplicado en bridges.json, se ignora la repeticion: {tema!r}")
            continue
        entry_por_tema[tema] = {**entry, "archivo": safe_archivo}

    injected = set(str_list(state.get("temas_inyectados")))
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
            if not rt or not isinstance(rt, str):
                continue
            if rt in injected:  # G2: ya inyectado (previo o hit de este prompt)
                continue
            if rt in sugeridos:  # dedup local
                continue
            if rt not in entry_por_tema:  # G1: destino dangling
                continue
            frase = (
                VERBOS.get(verbo, "se relaciona con")
                if isinstance(verbo, str)
                else "se relaciona con"
            )
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

    prompt_raw = data.get("prompt")
    cwd_raw = data.get("cwd") or ""
    if not prompt_raw or not cwd_raw or not isinstance(cwd_raw, str):
        return output_empty()
    # Prompt no vacio pero que no es string (123, lista, dict): normalize()
    # lanzaba TypeError y hook_main se llevaba puesto el arranque. Se trata como
    # "" (sin keywords) y el arranque sigue.
    prompt = prompt_raw if isinstance(prompt_raw, str) else ""
    cwd = Path(cwd_raw)
    # NO agregar early-returns despues de este punto: cortarian la inyeccion de
    # arranque, que no depende de que haya bridges.json ni hits de temas.

    # Sufijo -bridge: aisla el estado del router del resto de los hooks
    # (-ckpt/-drift/-calib/-playbook/-gate) que comparten el mismo session_key.
    key = session_key(data) + "-bridge"
    state = load_state(key)
    # Campo de tipo raro (temas_inyectados = 5, o con no-hasheables): set() lanzaba
    # TypeError antes de save_state -> pass-through hasta vencer el TTL. Se
    # normaliza a lista de strings ANTES de la foto.
    if "temas_inyectados" in state:
        state["temas_inyectados"] = str_list(state["temas_inyectados"])
    # Foto serializada del estado: permite saber si arranque_lines/tema_lines lo
    # mutaron sin rastrear cada cambio, y asi guardar solo cuando hace falta.
    state_before = json.dumps(state, sort_keys=True, ensure_ascii=True)
    arranque_previo = bool(state.get("arranque_inyectado"))
    temas_previos = set(str_list(state.get("temas_inyectados")))

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
