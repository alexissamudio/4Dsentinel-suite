# ai-fluency-4d

Marketplace y plugin de Claude Code que aplica el marco 4D de AI Fluency.
El plugin vive en `plugins/fluency-4d/`; este repo es su fuente de desarrollo.

<!-- BEGIN 4D-BRIDGES -->
## Reglas del proyecto (siempre)
- SIEMPRE `uv run`; NUNCA el `python` del PATH (apunta al venv de hermes-agent).
- SIEMPRE ASCII en los `.py`; NUNCA acentos en strings de hooks (cp1252 en Windows).
- Los hooks NUNCA escriben dentro del proyecto: solo temp o `~/.claude/fluency4d/`.
- Commits convencionales: subject ≤50 chars; NUNCA atribución de IA.
- Versión sincronizada en los 3 lugares vía `fluency_bump_version.py`; NUNCA a mano.
- Tag/release SOLO tras CI verde.

## Puentes de documentación
| Tema | Cuándo leer | Archivo |
|------|-------------|---------|
| Hooks | eventos, stdin/stdout, estado, bridge_router, checkpoint | .claude/docs/hooks.md |
| Skills | frontmatter, triggers, references, registro doble | .claude/docs/skills.md |
| Testing | pytest, conftest, aislamiento, cómo correr | .claude/docs/testing.md |
| Release | versión en 3 lugares, caché, CI antes de tag | .claude/docs/release.md |
| Filosofía | qué es / qué no es el plugin, criterio de decisión para features/ports | .claude/docs/filosofia.md |
| Persistencia | qué pasa con planes/estado-sesion/puentes/memoria al cambiar requisitos (flow-back/forward/living) | .claude/docs/persistencia.md |

Si la pregunta o tarea toca un tema de la tabla, LEÉ ese archivo ANTES de responder.
Al escribir código, respetá `.claude/docs/convenciones.md`.
<!-- END 4D-BRIDGES -->
