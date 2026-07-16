# Estado de sesion — 2026-07-16 — agent-improver CONSTRUIDO + mejoras piloto aplicadas (PR #13 verde)

## Objetivo / frase 4D
Diligencia: construir `agent-improver` (Workflow que mide/mejora los prompts de sentinel-agents),
aplicar sus primeras propuestas y endurecer el dataset. Plan: `~/.claude/plans/snug-launching-newt.md`.

## HECHO Y VERIFICADO
### Rama `feat/agent-improver` (scaffolding) — commits a8d091f, 1221224, f0f6a32
- Dataset golden `tests/agent-evals/` (bug-hunter x4, security-auditor x2, critic x2) + RUBRIC + README.
- Motor `.claude/workflows/agent-improver.js`: load -> baseline-eval -> meta-review (panel 3) ->
  synthesis -> candidate-eval+select (vias RECALL + PRECISION, margen 0.05, mayoria de reps) -> loop-until-dry.
  Role-play read-only + judge, ambos con schema. Propuestas durables en `.claude/docs/propuestas-agent-improver.md`.
- Verif #2 CUMPLIDA: 2 runs (111 agentes c/u, 0 err). Baseline catch-rate 1.0 en los 3 (dataset facil saturaba).

### Rama `feat/improve-sentinel-agents` = feat/agent-improver + mejoras. **PR #13 (CI 5/5 VERDE)**
- **Mejoras piloto aplicadas** (commit 7433795) a bug-hunter/security-auditor/critic .md, a mano desde
  las propuestas del loop, no-regresion de contrato verificada. Bump **sentinel-agents 0.6.1 -> 0.6.2** (F17).
  Guardas verdes: check_agents (11 OK), check_suite_versions, check_bump_on_change (F17), frontmatter +
  === SENTINEL-REPORT === + enums de verdict intactos. CI Linux confirma (job sentinel-agents + suite pass).
- **Dataset endurecido** (commit 5dbcecf): +3 casos DIFICILES/sutiles con headroom:
  bug-hunter/case-05 (alias de clase, float-eq, off-by-one enmascarado, race check-then-act),
  security-auditor/case-03 (SSRF substring-allowlist, IDOR, open-redirect, timing no-constante),
  critic/case-03 (return inexistente, sentinel None, flush borra-todo, criterio no medible). Ground-truth
  verificado a mano (lineas exactas, decoys convincentes).

## GOTCHAS de esta sesion (para recordar)
- El `synth.diff` del loop NO es git-apply-able (entities HTML + conteos de linea del LLM) -> aplicar A
  MANO (que ademas es la revision humana del plan). Mejora futura del motor: exponer `candidateFileFull`.
- El `.venv` es de LINUX -> `uv run` falla al recrearlo (symlink lib64 access denied). Workaround usado:
  `uv run --no-project --python 3.12 python scripts/<x>.py` (entorno efimero, no toca el .venv). ruff: `uvx ruff`.
  Arreglo real pendiente: borrar `.venv` (Remove-Item -Recurse -Force) + `uv sync`.
- `Workflow({name:'agent-improver'})` no resuelve -> usar `scriptPath`. El `resume` NO cacheo (re-corrio full).

## PENDIENTE
1. **Mergear PR #13** (CI verde). OJO auto-aprobacion: el clasificador bloquea `gh pr merge` de PR que
   yo mismo abri -> requiere OK explicito del usuario o que lo mergee el.
2. **Correr el loop sobre el dataset DURO** para confirmar headroom: `Workflow({scriptPath:
   'C:\\Users\\samud\\dev\\4Dsentinel-suite\\.claude\\workflows\\agent-improver.js', args:{targets:['bug-hunter'], rounds:2, reps:3}})`
   -> ver si ahora hay un candidato ACEPTADO via RECALL (baseline < 1.0). Costoso (~2.8M tok/run).
3. Escalar a los 8 agentes restantes (mismo motor, sumar casos golden).
4. Arreglar venv local. Revisar `.claude/docs/testing.md` (se edito pyproject/tests).
5. El scaffolding solo (feat/agent-improver) quedo SIN PR propio: PR #13 lo incluye entero.

## ARRANCAR SESION NUEVA
cd C:\Users\samud\dev\4Dsentinel-suite ; leer .claude/docs/estado-sesion.md y ~/.claude/plans/snug-launching-newt.md
