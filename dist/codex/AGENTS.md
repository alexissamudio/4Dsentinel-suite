# AGENTS.md - contrato del proyecto (bundle Codex)

> Generado por `tools/multiharness/build_harness.py` desde los innegociables de `CLAUDE.md`. Equivalente en Codex de las reglas duras de Claude Code.

## Reglas del proyecto (siempre)

- SIEMPRE `uv run`; NUNCA el `python` del PATH (apunta al venv de hermes-agent).
- SIEMPRE ASCII en los `.py`; NUNCA acentos en strings de hooks (cp1252 en Windows).
- Los hooks NUNCA escriben dentro del proyecto: solo temp o `~/.claude/fluency4d/`.
- Commits convencionales: subject ≤50 chars; NUNCA atribución de IA.
- Versión sincronizada en los 3 lugares vía `fluency_bump_version.py`; NUNCA a mano.
- Tag/release SOLO tras CI verde.

## Puentes de documentacion

> NOTA (Codex): los puentes apuntan a `.claude/docs/*` del proyecto. Codex no ejecuta el hook `bridge_router` automaticamente para leerlos; leelos a mano si la tarea toca ese tema.

| Tema | Cuándo leer | Archivo |
|------|-------------|---------|
| Hooks | eventos, stdin/stdout, estado, bridge_router, checkpoint | .claude/docs/hooks.md |
| Skills | frontmatter, triggers, references, registro doble | .claude/docs/skills.md |
| Testing | pytest, conftest, aislamiento, cómo correr | .claude/docs/testing.md |
| PSS | teoría de pruebas (triángulo, V&V, mutation, property, flaky) + gaps de la suite | .claude/docs/pss.md |
| Release | versión en 3 lugares, caché, CI antes de tag | .claude/docs/release.md |
| Filosofía | qué es / qué no es el plugin, criterio de decisión para features/ports | .claude/docs/filosofia.md |
| Persistencia | qué pasa con planes/estado-sesion/puentes/memoria al cambiar requisitos (flow-back/forward/living) | .claude/docs/persistencia.md |

## Notas de portabilidad

- Hooks: emitidos como `hooks.json` (schema de Claude Code), descubierto en `$CODEX_HOME/hooks.json` o `<proyecto>/.codex/hooks.json`. `config.toml` solo activa `[features] hooks = true`; su bloque `[hooks]` NO dispara nada.
- Subagentes: `[agents.<name>]` + `<name>.config.toml`.
- MCP (codebase-memory): DIFERIDO (binario `cbm` no instalado).
