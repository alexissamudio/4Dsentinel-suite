# Estado de sesion — 2026-07-16 — agent-improver: piloto + ESCALADO a los 11 agentes (en curso)

## ESCALADO COMPLETO — los 11 agentes pasaron por el loop. PR #13 CI 5/5 VERDE.
- **Motor extendido con modo META-ONLY** (`runMetaOnly`): agentes sin casos golden corren solo
  meta-review + synthesis (validator/debugger usan Bash, librarian extrae, risk-assessor escalar).
- **9 casos golden nuevos** (verificados a mano): code-reviewer x3, advisor x3, auditor-de-redaccion x3.
- **Runs**: wku2o40nh (librarian meta-only), wf_940dacb0-5ca (los 7 restantes, 107 agentes).
- **Resultados clave del eval**:
  - **advisor: candidato ACEPTADO via RECALL** (baseline 0.875 -> 1.0, Δ+0.125, win 2/2) — 1er auto-aceptado.
  - **code-reviewer: headroom real** (baseline 0.75 -> cand 0.85, Δ+0.10) — el dataset dificil SI da senal.
  - **auditor-de-redaccion: candidato RECHAZADO** (Δ-0.04, degrada) -> NO aplicado (propuesta guardada).
- **MEJORAS APLICADAS a 10/11 agentes** (todas con check_agents verde + gate F17 + CI verde, bump 0.6.2):
  bug-hunter, security-auditor, critic (piloto) + advisor, code-reviewer (eval) + librarian, validator,
  debugger, risk-assessor, compliance-auditor (meta-only). auditor-de-redaccion NO (candidato degradaba).
- Propuestas durables: `.claude/docs/propuestas-agent-improver.md` (piloto) + `.claude/docs/propuestas-escalado.md` (8).
- **Guardas verificadas en los 10**: frontmatter+tools intactos (Bash de validator/debugger preservado),
  === SENTINEL-REPORT === y enums de verdict sin cambios, cita a agent-contract. check_agents 11/11 OK.

## PENDIENTE (siguiente sesion)
1. **Mergear PR #13** (CI verde). Auto-aprobacion: pedir OK al usuario -> `! gh pr merge 13 --squash --delete-branch`.
2. auditor-de-redaccion: re-intentar (mejorar su dataset o el prompt del synth); su candidato degradaba.
3. Mejora del motor: exponer `candidateFileFull`; el resume no cachea.
4. Arreglar venv local (borrar .venv linux + uv sync).

---
# Estado previo — agent-improver COMPLETO (piloto) + mejoras aplicadas (PR #13 verde)

## Objetivo / frase 4D
Diligencia: construir `agent-improver` (Workflow que mide/mejora prompts de sentinel-agents), aplicar
sus propuestas, endurecer el dataset y verificar. Plan: `~/.claude/plans/snug-launching-newt.md`.

## PR #13 — CI 5/5 VERDE (rama `feat/improve-sentinel-agents`)
Incluye TODO el trabajo (scaffolding + mejoras + dataset duro). Commits:
- Scaffolding: motor `.claude/workflows/agent-improver.js` + dataset `tests/agent-evals/` (bug-hunter x5,
  security-auditor x3, critic x3) + RUBRIC + README + propuestas durables.
- Mejoras piloto a los 3 agentes (.md) + bump **sentinel-agents 0.6.1 -> 0.6.2** (F17).
- Dataset endurecido: +3 casos dificiles (verificados a mano).
- Mejoras EXTRA a bug-hunter (del 3er run, aplicadas a mano por session-limit del synth): **scope de
  entrada** (Método) + **`summary:` en la enumeración de salida** + clase **no-terminación**.
- fix LF del workflow (.gitattributes `.claude/workflows/*.js text eol=lf`).
Guardas verdes en todos: check_agents, check_suite_versions (sentinel 0.6.2), gate F17. Frontmatter +
=== SENTINEL-REPORT === + enums de verdict intactos.

## VERIFICACION del motor (3 runs, todos con baseline catch-rate 1.0)
- Run 1 y 2 (3 targets): motor OK end-to-end; ningun candidato aceptado (baseline satura + judge-noise).
- Run 3 (bug-hunter, dataset DURO): baseline SIGUE 1.0 (Opus caza los casos dificiles igual) -> **NO hay
  headroom de recall**. El synth murio por **session limit** (ver abajo). El meta-review SI dio 2 gaps
  Important nuevos (scope de entrada + summary omitido) -> aplicados a mano a bug-hunter.md.
- **CONCLUSION**: para agentes cazados por un modelo fuerte, el valor del loop es el **meta-review**
  (guard de regresion + mejoras de calidad), no el delta de catch-rate. Documentado en README y lecciones.

## BLOQUEO ACTIVO: session limit de Claude
`You've hit your session limit · resets 2:50pm (America/Asuncion)`. NO se pueden correr mas Workflows/
subagentes hasta el reset. El trabajo LOCAL (git, edicion, checks Python con entorno efimero, CI de
GitHub) NO esta bloqueado.

## PENDIENTE (tras el reset del session limit)
1. **Mergear PR #13** (CI verde). Auto-aprobacion: el clasificador bloquea `gh pr merge` de MI PR ->
   pedir OK al usuario o que lo mergee el: `! gh pr merge 13 --squash --delete-branch`.
2. **Escalar a los 8 agentes restantes** (advisor, code-reviewer, compliance-auditor, debugger, librarian,
   risk-assessor, validator, auditor-de-redaccion): crear casos golden (>=3-4 c/u) en tests/agent-evals/
   + correr el loop `Workflow({scriptPath: '...agent-improver.js', args:{targets:[...], rounds:2, reps:3}})`.
   El motor no cambia; solo crece el dataset. OJO: crear los casos NO requiere API (edicion); correr el
   loop SI. Costo ~2.8M tok/run de 3 targets, ~0.9M/run de 1 target.
3. **Mejora del motor**: exponer `candidateFileFull` en el reporte (hoy solo `diff`, que no es git-apply-able).
4. **Arreglar venv local** (borrar .venv linux + uv sync) para correr check_agents/pytest sin entorno efimero.

## GOTCHAS (consolidados en .claude/docs/lecciones.md)
- Diffs del synth NO son git-apply-able (entities HTML + conteos LLM) -> aplicar a mano.
- .venv es de LINUX -> usar `uv run --no-project --python 3.12 python scripts/<x>.py`; `uvx ruff`.
- Workflow rechaza .js con CRLF (permission handler) -> forzar LF; `Workflow({name})` no resuelve -> scriptPath.
- Clasificador bloquea auto-merge de PR propio -> OK del usuario.

## ARRANCAR SESION NUEVA
cd C:\Users\samud\dev\4Dsentinel-suite ; leer .claude/docs/estado-sesion.md y ~/.claude/plans/snug-launching-newt.md
