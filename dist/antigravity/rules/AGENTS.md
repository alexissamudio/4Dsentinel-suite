# AGENTS.md - contrato del proyecto (bundle Antigravity)

> Generado por `tools/multiharness/build_harness.py` desde los innegociables de `CLAUDE.md`. En Antigravity vive bajo `rules/AGENTS.md` (markdown plano sin frontmatter, activo siempre que el plugin este habilitado).

## Reglas del proyecto (siempre)

- SIEMPRE `uv run`; NUNCA el `python` del PATH (apunta al venv de hermes-agent).
- SIEMPRE ASCII en los `.py`; NUNCA acentos en strings de hooks (cp1252 en Windows).
- Los hooks NUNCA escriben dentro del proyecto: solo temp o `~/.claude/fluency4d/`.
- Commits convencionales: subject ≤50 chars; NUNCA atribución de IA.
- Versión sincronizada en los 2 lugares vía `fluency_bump_version.py`; NUNCA a mano.
- Tag/release SOLO tras CI verde.

## Puentes de documentacion

> NOTA (Antigravity): los puentes apuntan a `.claude/docs/*` del proyecto. El shim `hooks/fluency_hooks.py` invoca `bridge_router.py` en `PreInvocation`; tambien podes leerlos a mano si la tarea toca ese tema.

| Tema | Cuándo leer | Archivo |
|------|-------------|---------|
| Hooks | eventos, stdin/stdout, estado, bridge_router, checkpoint | .claude/docs/hooks.md |
| Skills | frontmatter, triggers, references, registro doble | .claude/docs/skills.md |
| Testing | pytest, conftest, aislamiento, cómo correr | .claude/docs/testing.md |
| PSS | teoría de pruebas (triángulo, V&V, mutation, property, flaky) + gaps de la suite | .claude/docs/pss.md |
| Release | versión en 2 lugares, caché, CI antes de tag | .claude/docs/release.md |
| Filosofía | qué es / qué no es el plugin, criterio de decisión para features/ports | .claude/docs/filosofia.md |
| Persistencia | qué pasa con planes/estado-sesion/puentes/memoria al cambiar requisitos (flow-back/forward/living) | .claude/docs/persistencia.md |
| Arquitectura | mapa del plugin, runtimes, estado en `~/.claude/fluency4d/`, barra, Panel 4D, `/statusline setup`, cómo extender | docs/fluency-4d-arquitectura.md |

## Notas de portabilidad

- Hooks: emitidos como `hooks.json` en la raiz del plugin (`<plugin_dir>/hooks.json`, clave raiz `"fluency-4d"`) junto al shim `hooks/fluency_hooks.py`, que puentea `PreInvocation` -> `UserPromptSubmit` (`injectSteps`) y `Stop` -> `discernment_gate` (`decision: continue`).
- Subagentes: `agents/<name>.md` con frontmatter `name` y `description` (read-only por defecto en Antigravity).
- Skills: `skills/<name>/SKILL.md` (mismo formato que Claude Code).
- MCP (codebase-memory): DIFERIDO (binario `cbm` no instalado).
