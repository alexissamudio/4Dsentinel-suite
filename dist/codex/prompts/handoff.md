# /handoff

Wrapper de slash command para Codex CLI. Dispara el skill `handoff`
(instalado en `.agents/skills/handoff/SKILL.md`).

Segui el skill `handoff` al pie de la letra: recolecta el contexto de
git y el estado de sesion, actualiza `.claude/docs/estado-sesion.md`
(o su equivalente del proyecto), sugeri el commit (NO lo ejecutes) y
copia el handoff al portapapeles.

NOTA (Codex): el paso del "plan activo" en `~/.codex/plans/` degrada a
"sin plan" si ese directorio no existe (Codex no hereda los planes de
Claude). El resto del skill es cross-harness.
