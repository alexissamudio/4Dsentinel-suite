---
generated: 2026-07-03
source: 4d-init
content_hash: c235e7050712aa56915067a2d058f7a37f728db955e4fb6a03106ba40b7b25d9
---

# Hooks en este proyecto

Cuatro hooks Python autocontenidos (PEP-723, corren con `uv run --script`) en
`plugins/fluency-4d/hooks/`, registrados en `hooks/hooks.json` (auto-descubierto:
NUNCA listarlo en plugin.json — causa "Duplicate hooks file").

## Los cuatro

| Hook | Evento | Qué hace |
|------|--------|----------|
| `bridge_router.py` | UserPromptSubmit | Inyección de arranque (lecciones/estado) + puentes por tema desde `bridges.json`; dedup por sesión; telemetría vía `bump_stats` |
| `memory_checkpoint.py` | PostToolUse `.*` | Al cruzar `FLUENCY_4D_SAVE_PCT` (50%) instruye guardar estado; re-armado dual (caída de % nativo / intervalo de tokens fallback) |
| `doc_drift.py` | PostToolUse `Edit\|Write\|MultiEdit\|NotebookEdit` | Si se edita bajo las `rutas` de un tema, recuerda revisar su doc; matching por segmento casefolded |
| `discernment_gate.py` | Stop | Opt-in `FLUENCY_4D_STRICT=1`: bloquea UNA vez con checklist |

`hook_utils.py` comparte: `read_stdin_safe` (hilo+join, compatible Windows),
`output_context`/`output_stop_block`, `hook_main` (toda excepción degrada a
pass-through), estado por sesión en `<temp>/fluency4d/<clave>.json` (TTL 4 h,
fallback por hash de cwd si falta `session_id`) y `bump_stats`.

## Contratos de salida

- Contexto: `{"hookSpecificOutput": {"hookEventName": ..., "additionalContext": ...}}`
- Bloqueo en Stop (top-level, NO hookSpecificOutput): `{"decision": "block", "reason": ...}`
- Pass-through: exit 0 sin stdout.

## Trampas conocidas (no repetirlas)

- `ensure_ascii=True` en TODO json.dumps a stdout: la consola Windows puede ser
  cp1252 y el texto acentuado revienta el hook en silencio.
- Esta versión de Claude Code NO manda `context_window.used_percentage` ni
  `transcript` en el stdin; SÍ manda `transcript_path` — el checkpoint estima
  por tamaño de archivo (bytes/4, SIN cap para la lógica: el cap mataba la
  detección de intervalo).
- Guardas obligatorias en hooks nuevos: `agent_type` (subagentes), y en los que
  piden escrituras, `permission_mode == "plan"` sin marcar estado.
- Stop: respetar `stop_hook_active` (anti-bucle canónico).
- El router tiene punto de emisión único: cualquier feature nueva se cuelga ahí,
  no agrega early-returns (se tragan la inyección de arranque).
- Los hooks NUNCA escriben dentro del proyecto del usuario: temp y
  `~/.claude/fluency4d/` solamente.
