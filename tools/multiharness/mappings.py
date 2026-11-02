# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""mappings.py - Tablas de mapeo Claude Code -> Codex CLI / OpenCode.

Este modulo es DATOS puros (sin efectos): lo importa build_harness.py para
saber como traducir cada artefacto de la suite (skills, agentes, hooks, home)
del contrato de Claude Code al contrato que Codex CLI 0.130 adopto.

IMPORTANTE - que gobierna de verdad la salida y que es solo documentacion:
Cada tabla esta marcada abajo con uno de estos rotulos:
  [CONSUMIDA]  -> build_harness.py la lee; editarla CAMBIA el bundle generado.
  [DOC-ONLY]   -> referencia para humanos; el generador NO la consume, editarla
                  NO cambia la salida (la traduccion real esta en otro lado o
                  esta hardcodeada de forma equivalente). No asumas lo contrario.
Consumidas hoy: HOME_MAP, HOOK_FEATURE_FLAG, PLUGIN_ROOT_VAR, HARNESSES,
SKILLS_UNSUPPORTED y las tablas OPENCODE_* (seccion 7). El resto es DOC-ONLY
hasta que alguien las cablee en build_harness.py.

ASCII puro (regla de CLAUDE.md): sin acentos en los strings de este archivo.
"""

from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# 1) Directorios "home" del harness: ~/.claude -> ~/.codex
# ---------------------------------------------------------------------------
# [CONSUMIDA] build_harness.build_handoff_skill() itera esta tabla para
# reescribir el home en el SKILL.md portado (~/.claude -> ~/.codex, etc.).
# Codex usa CODEX_HOME (default ~/.codex) como equivalente de ~/.claude.
# NOTA: ~/.claude/plans/ NO tiene equivalente en Codex (no hereda planes) ->
# el consumidor degrada ese paso a "sin plan".
HOME_MAP: dict[str, str] = {
    "~/.claude": "~/.codex",
    "$CLAUDE_HOME": "$CODEX_HOME",
    "${CLAUDE_HOME}": "${CODEX_HOME}",
}

# [DOC-ONLY] la nota de degradacion se emite hardcodeada en build_harness.py;
# esta tabla es referencia, el generador no la lee.
# Subdirectorios sin equivalente 1:1 en Codex (se degradan, no se rompen).
HOME_NO_EQUIV: dict[str, str] = {
    "~/.claude/plans": "sin-equivalente (Codex no hereda planes -> 'sin plan')",
}

# ---------------------------------------------------------------------------
# 2) Eventos de hooks: nombre Claude -> nombre Codex
# ---------------------------------------------------------------------------
# [DOC-ONLY] los eventos se copian tal cual desde hooks.json fuente (schema
# identico); el generador no consulta esta tabla. Referencia del contrato.
# Codex 0.130 adopto el contrato de hooks de Claude Code: los nombres de evento
# coinciden 1:1. Se mantiene la tabla explicita para documentar el contrato y
# para poder detectar un evento no soportado en el futuro.
HOOK_EVENT_MAP: dict[str, str] = {
    "UserPromptSubmit": "UserPromptSubmit",
    "PostToolUse": "PostToolUse",
    "PreToolUse": "PreToolUse",
    "Stop": "Stop",
    "SubagentStop": "SubagentStop",
    "SessionStart": "SessionStart",
    "Notification": "Notification",
}

# [DOC-ONLY] referencia; el bundle emite hooks.json completo desde la fuente.
# Eventos que el PoC transpila hoy. El resto queda como TODO en el bundle.
HOOK_EVENTS_PORTED: tuple[str, ...] = ("UserPromptSubmit",)

# Diferencias de schema Claude -> Codex en config.toml:
# - hay que habilitar [features] hooks = true.
# - cada hook necesita type = "command" (sin el, Codex: missing field `type`).
# - rutas Windows: usar string TOML literal (comillas simples) o basic con
#   backslashes escapados; aca se usa literal + comillas dobles internas.
# - command / commandWindows: misma invocacion uv en esta maquina.
# [DOC-ONLY] HOOK_TYPE: el bundle emite hooks.json (schema Claude), NO declara
#            hooks [type=...] en config.toml -> este literal ya no se consume.
HOOK_TYPE = "command"
# [CONSUMIDA] build_harness.build_config_toml() la escribe tal cual en config.toml.
HOOK_FEATURE_FLAG = "[features]\nhooks = true"

# [CONSUMIDA] resolve_plugin_root()/opencode_userprompt_scripts() la usan para
# resolver la variable de plugin de Claude a ruta absoluta.
PLUGIN_ROOT_VAR = "${CLAUDE_PLUGIN_ROOT}"

# ---------------------------------------------------------------------------
# 3) Ubicacion de skills
# ---------------------------------------------------------------------------
# [DOC-ONLY] build_harness.py usa su propio glob (discover_skills) y arma la
# ruta destino con literales (".agents"/"skills"); estas constantes son
# referencia y no gobiernan la salida.
# Claude:  plugins/<plugin>/skills/<name>/SKILL.md
# Codex:   .agents/skills/<name>/SKILL.md   (mismo formato de SKILL.md)
SKILLS_SRC_GLOB = "plugins/*/skills/*/SKILL.md"
SKILLS_DST_SUBDIR = ".agents/skills"  # relativo a CODEX_HOME o al proyecto

# ---------------------------------------------------------------------------
# 4) Slash commands / prompts
# ---------------------------------------------------------------------------
# [DOC-ONLY] referencia; build() escribe el literal "prompts" directamente.
# Claude:  el skill se dispara por su trigger.
# Codex:   ~/.codex/prompts/<name>.md  (wrapper fino que invoca el skill)
PROMPTS_DST_SUBDIR = "prompts"

# ---------------------------------------------------------------------------
# 5) Subagentes
# ---------------------------------------------------------------------------
# [DOC-ONLY] discover_agents() usa su propio glob y build() escribe el literal
# "agents"; estas constantes son referencia del contrato.
# Claude:  plugins/sentinel-agents/agents/<name>.md (frontmatter + cuerpo)
# Codex:   [agents] + [agents.<name>] en config.toml, con config_file = "<name>.config.toml"
#          y el cuerpo/instrucciones en agents/<name>.md.
AGENTS_SRC_GLOB = "plugins/sentinel-agents/agents/*.md"
AGENTS_DST_SUBDIR = "agents"

# [DOC-ONLY] parse_frontmatter() lee todas las claves presentes; esta tupla es
# referencia de las que sabemos interpretar, no un filtro que aplique el generador.
# Campos de frontmatter de agente que sabemos leer.
AGENT_FRONTMATTER_KEYS = ("name", "description", "model", "tools", "maxTurns", "color")

# [DOC-ONLY] build_critic_config() mapea los campos de forma hardcodeada
# (model, maxTurns->max_turns) en comentarios del .config.toml; esta tabla es
# referencia y no gobierna la salida.
# Mapeo de campos de agente Claude -> config de agente Codex (best-effort).
# NOTA(verificar-schema): confirmar nombres exactos de campos en el schema
# [agents] de Codex 0.130 antes de darlos por firmes.
AGENT_FIELD_MAP: dict[str, str] = {
    "model": "model",       # "inherit" -> se omite override (hereda sesion)
    "maxTurns": "max_turns",
    "description": "description",
    # tools: Read/Grep/Glob (read-only) -> mapear a tools de solo-lectura de Codex.
}

# ---------------------------------------------------------------------------
# 6) MCP: DIFERIDO
# ---------------------------------------------------------------------------
# [DOC-ONLY] flag de estado; el bundle simplemente no emite [mcp_servers].
# El binario `cbm` (codebase-memory) NO esta instalado en esta maquina.
# No se incluye ninguna seccion [mcp_servers] en el bundle. Queda como TODO.
MCP_DEFERRED = True

# ---------------------------------------------------------------------------
# 7) OpenCode (dist/opencode/)
# ---------------------------------------------------------------------------
# [CONSUMIDA] build_harness.py (README, banners y shim) declara la version
# contra la que se verifico el bundle (E2E con `opencode run`).
# El shim (plugin/fluency-hooks.js) es UN archivo con los dos contratos de
# plugin: v1 (`default.server` -> hook `chat.message`) y v2 (`default.setup` ->
# `api.session.hook("context")`). E2E real en 1.19.1, 1.19.5 y 2.2.5.
OPENCODE_V1_VERSION = "1.19.x"
OPENCODE_V2_VERSION = "2.2.5"
OPENCODE_VERSION = OPENCODE_V1_VERSION + " / " + OPENCODE_V2_VERSION

# Harnesses a los que el generador porta la suite (dist/<harness>/).
HARNESSES: tuple[str, ...] = ("codex", "opencode")

# [CONSUMIDA] tabla UNICA de skills sin soporte: {skill: (harnesses, razon)}.
# - Las que no soporta NINGUN harness de HARNESSES entran en
#   build_harness.CLAUDE_CODE_ONLY (skills/<name>) -> discover_skills() las omite.
# - build_harness.unsupported_skills("opencode") filtra los commands OpenCode y
#   arma la seccion "Skills que NO se emiten" del README (en este orden).
SKILLS_UNSUPPORTED: dict[str, tuple[tuple[str, ...], str]] = {
    "verify-diff": (
        ("opencode",),
        "solo escribe el flag que lee el hook `Stop` (discernment_gate.py). El "
        "shim de OpenCode puentea UNICAMENTE `UserPromptSubmit` (`chat.message`) "
        "y OpenCode no tiene un evento que pueda bloquear el cierre del turno: "
        "el toggle no tendria ningun efecto, asi que emitirlo seria mentir.",
    ),
    "barra": (
        HARNESSES,
        "cambia el modo/tema de la status line de Claude Code (no existe en OpenCode).",
    ),
    "statusline": (
        HARNESSES,
        "instala la status line y el Panel 4D en settings.json de Claude Code "
        "(engine de mods exclusivo de Claude Code).",
    ),
}

# [CONSUMIDA] oc_translate_common(): nombres de tools exclusivas de Claude Code
# -> equivalente OpenCode. Orden importa (lo especifico primero).
OPENCODE_TOOL_MAP: tuple[tuple[str, str], ...] = (
    ("el Agent tool", "la tool `task` (`subagent` en OpenCode 2.x)"),
    ("Agent tool", "la tool `task` (`subagent` en OpenCode 2.x)"),
    ("AskUserQuestion", "la tool `question`"),
)

# [CONSUMIDA] renombres de IDENTIFICADORES de tools, por palabra completa
# (\b...\b): oc_translate_common() los aplica a los .md y el shim JS al texto que
# emiten los hooks Python (su CONTEXT_REWRITES se genera desde esta tabla).
OPENCODE_TOOL_RENAMES: tuple[tuple[str, str], ...] = (
    ("ExitPlanMode", "plan_exit"),
)

# [CONSUMIDA] oc_translate_common(): home de Claude -> OpenCode. SOLO planes:
# ~/.claude/fluency4d/ NO se traduce a proposito (lo leen/escriben los hooks
# Python, que en OpenCode corren via el shim con esa misma ruta).
OPENCODE_HOME_MAP: tuple[tuple[str, str], ...] = (
    ("`~/.claude/plans/`",
     "`.opencode/plans/` (proyecto) o `~/.local/share/opencode/plans/`"),
)

# [CONSUMIDA] build_opencode_skill_command(): reglas (old, new) por skill que se
# aplican al SKILL.md fuente (frontmatter incluido) ANTES de la traduccion comun.
# old = str literal o re.Pattern. Cada regla DEBE matchear (si la fuente cambia,
# el build falla en vez de emitir una traduccion a medias). {OC_REFS} = ruta
# abs de references/ instalado. Acentos de la fuente via escapes (ASCII puro).
OPENCODE_SKILL_RULES: dict[str, tuple] = {
    "4d-quiz": (
        ("Una AskUserQuestion por pregunta", "Una llamada a la tool `question` por pregunta"),
    ),
    "sentinel-audit": (
        (re.compile(r"Glob `\*\*/sentinel-agents/\*\*/references/iso-27000/"
                    r"00-INSTRUCCIONES-IA\.md`\s+bajo `~/\.claude/plugins`"),
         "en OpenCode la KB ya esta instalada (bundle) en `{OC_REFS}/iso-27000/`"),
        ("(ver `../../CLAUDE.md`)", "(regla de datos de la suite)"),
    ),
    "suite-setup": (
        ("(claude mcp add --scope user)", "(en opencode.json)"),
        ("con `claude mcp add` y **ruta absoluta**",
         "en `opencode.json` y **ruta absoluta**"),
        ("y `claude mcp add` corren", "y el registro en `opencode.json` corren"),
        ("sin este `claude mcp add` el MCP no existe",
         "sin este registro en `opencode.json` el MCP no existe"),
        ("`claude mcp add --scope user codebase-memory -- <ruta-absoluta-al-exe-verificado>`",
         "agrega a tu `opencode.json` global (`~/.config/opencode/opencode.json`) "
         "el bloque `\"mcp\": { \"codebase-memory-mcp\": { \"type\": \"local\", "
         "\"command\": [\"<ruta-absoluta-al-exe-verificado>\"], \"enabled\": true } }` "
         "(si ya existe una entrada, actualiza su `command`)"),
        (re.compile(r"\*\*Reiniciar Claude Code\*\* \(el MCP se conecta al arrancar\) "
                    r"y confirmar con `/mcp` que\s+`codebase-memory` aparece conectado\."),
         "**Reiniciar OpenCode** (el MCP se conecta al arrancar) y confirmar con "
         "`opencode mcp list` que `codebase-memory-mcp` aparece conectado."),
        (re.compile(r"- Los \*\*agentes sentinel\*\* NO ven el MCP[^\n]*\n[^\n]*"),
         "- En OpenCode los subagentes de la suite SI pueden ver las tools MCP "
         "(salvo que sus permisos las nieguen), pero igual conviene que el "
         "conductor consulte el grafo y les **relaye** un brief conciso."),
        (re.compile(r"- Cargar las tools del MCP de forma \*\*diferida\*\* \(ToolSearch\)[^\n]*"),
         "- En OpenCode las tools del MCP se exponen como `codebase-memory-mcp_<tool>` "
         "(prefijo = nombre del server en `opencode.json`)."),
    ),
}

# [CONSUMIDA] oc_translate_agent_body(): reglas por agente (y para el contrato,
# clave "agent-contract"). Mismo formato que OPENCODE_SKILL_RULES.
_GLOB_HINT = "(ubicalo por Glob si lo necesit\u00e1s)"
_GLOB_HINT_OC = "(ruta absoluta de instalacion: leelo directo con la tool read)"
OPENCODE_AGENT_RULES: dict[str, tuple] = {
    **dict.fromkeys(
        ("bug-hunter", "debugger", "security-auditor"), ((_GLOB_HINT, _GLOB_HINT_OC),)
    ),
    "compliance-auditor": (
        (re.compile(r"Glob de `00-INSTRUCCIONES-IA\.md` bajo `<HOME>/\.claude/plugins`"),
         "la KB instalada por el bundle OpenCode en `{OC_REFS}/iso-27000/`"),
    ),
    "agent-contract": (
        (re.compile(r"`\$\{CLAUDE_PLUGIN_ROOT\}` NO est\u00e1 disponible para agentes "
                    r"\(verificado\)\. La KB se\s+ubica as\u00ed, en orden:"),
         "En OpenCode la KB la instala el bundle en `{OC_REFS}/iso-27000/`. Se "
         "ubica as\u00ed, en orden:"),
        (re.compile(r"2\. Si no, con Glob busc\u00e1 `\*\*/sentinel-agents/\*\*/references/"
                    r"iso-27000/00-INSTRUCCIONES-IA\.md`\s+bajo el directorio de plugins "
                    r"del usuario \(`<HOME>/\.claude/plugins`\), y us\u00e1 esa\s+carpeta "
                    r"como ra\u00edz del KB\."),
         "2. Si no, us\u00e1 la KB instalada: `{OC_REFS}/iso-27000/` (ra\u00edz del KB; "
         "abr\u00ed `INDEX.md` o `00-INSTRUCCIONES-IA.md`)."),
    ),
}

def _flag_note(injector: str) -> str:
    """Nota de los toggles cuyo flag lee un hook *_injector.py via el shim."""
    return (
        "El flag va en `~/.claude/fluency4d/` A PROPOSITO (no en "
        "`~/.config/opencode`): es la ruta que lee `%s`, que en "
        "OpenCode corre via el plugin `fluency-hooks.js` en cada mensaje. Usa la "
        "tool `write` con la ruta absoluta expandida (esta fuera del proyecto: "
        "OpenCode pedira permiso `external_directory`, aprobalo)." % injector
    )


# [CONSUMIDA] build_opencode_skill_command(): nota extra (blockquote) por skill.
# {SKILL_AGENTS} = subagentes de sentinel-agents que nombra el SKILL.md fuente
# (en orden de aparicion, solo los que devuelve discover_agents()).
OPENCODE_SKILL_NOTES: dict[str, str] = {
    "4d-status": (
        "Reporte de SOLO LECTURA: lee exactamente los archivos listados y nada "
        "mas. `~/.claude/fluency4d/stats.json` es la ruta REAL de las metricas "
        "en OpenCode tambien (las escriben los hooks de fluency-4d via el plugin "
        "`fluency-hooks.js`); si no existe, reporta \"sin datos de uso\" y segui."
    ),
    "caveman": _flag_note("caveman_injector.py"),
    "adhd": _flag_note("adhd_injector.py"),
    "handoff": (
        "Planes en OpenCode: `.opencode/plans/` del proyecto o "
        "`~/.local/share/opencode/plans/`; si no hay ninguno, el paso degrada a "
        "\"sin plan\"."
    ),
    "4d-init": (
        "OpenCode lee `AGENTS.md` (y cae a `CLAUDE.md` si no existe). Los "
        "puentes en `.claude/docs/` los consume el hook `bridge_router.py` via "
        "el plugin `fluency-hooks.js`: genera la estructura tal cual."
    ),
    "4d-quiz": (
        "Si la tool `question` no esta disponible (p. ej. `opencode run`), "
        "hace la pregunta en texto y espera la letra."
    ),
    "suite-setup": (
        "Adaptado a OpenCode: el registro del MCP va en `opencode.json` (no hay "
        "`claude mcp add`). Las menciones al `plugin.json` describen el plugin "
        "de Claude Code."
    ),
    "sentinel-audit": (
        "Subagentes via la tool `task` (`subagent` en OpenCode 2.x): "
        "{SKILL_AGENTS}."
    ),
}

# [CONSUMIDA] build_opencode_memory_command(): nota MCP de los commands de memory.
OPENCODE_MCP_NOTE = (
    "Este comando envuelve tools del MCP `codebase-memory`. En OpenCode se "
    "exponen con el prefijo del server (p. ej. `codebase-memory-mcp_search_graph` "
    "si el server se llama `codebase-memory-mcp` en `opencode.json`). Si el MCP "
    "no esta conectado, corre `/suite-setup` primero."
)
