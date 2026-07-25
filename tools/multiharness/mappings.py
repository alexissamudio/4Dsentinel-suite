# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""mappings.py - Tablas de mapeo Claude Code -> Codex CLI.

Este modulo es DATOS puros (sin efectos): lo importa build_harness.py para
saber como traducir cada artefacto de la suite (skills, agentes, hooks, home)
del contrato de Claude Code al contrato que Codex CLI 0.130 adopto.

IMPORTANTE - que gobierna de verdad la salida y que es solo documentacion:
Cada tabla esta marcada abajo con uno de estos rotulos:
  [CONSUMIDA]  -> build_harness.py la lee; editarla CAMBIA el bundle generado.
  [DOC-ONLY]   -> referencia para humanos; el generador NO la consume, editarla
                  NO cambia la salida (la traduccion real esta en otro lado o
                  esta hardcodeada de forma equivalente). No asumas lo contrario.
Consumidas hoy: HOME_MAP, HOOK_FEATURE_FLAG, PLUGIN_ROOT_VAR. El resto es
DOC-ONLY hasta que alguien las cablee en build_harness.py.

ASCII puro (regla de CLAUDE.md): sin acentos en los strings de este archivo.
"""

from __future__ import annotations

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
