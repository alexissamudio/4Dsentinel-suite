# Estado de sesion — 2026-07-16 — agent-improver: BUILD en curso (verificacion #2 corriendo)

## Objetivo / frase 4D
Diligencia: construir `agent-improver` (Workflow re-invocable que mide y mejora los prompts de los
11 agentes de sentinel-agents). Plan aprobado: `~/.claude/plans/snug-launching-newt.md`.

## Rama y commits
- Rama: `feat/agent-improver` (desde main @ b5f2c56... en realidad desde main post-auditoria).
- `a8d091f` feat(agent-improver): dataset golden + motor de eval. (scaffolding completo)

## HECHO
- **Dataset golden `tests/agent-evals/`** (ground-truth MANUAL): bug-hunter x4, security-auditor x2,
  critic x2. Cada caso: `input/<archivo NO test_*.py>` + `expected.json` {must_catch[], decoys[]}.
  + `RUBRIC.md` (8 dimensiones de calidad de prompt) + `README.md` (formato + escalado).
- **Motor `.claude/workflows/agent-improver.js`**: fases load -> baseline-eval -> meta-review (panel 3,
  agentType general-purpose) -> synthesis -> candidate-eval+select (delta por MARGEN 0.05, mayoria de
  reps pareadas, fp no sube) -> loop-until-dry. Role-play read-only del cuerpo del .md via agent()+schema
  (material inline, no lee disco -> baseline y candidato mismo host = delta apples-to-apples). Judge
  determinista con schema (effort low). Sintaxis validada (node --check: solo el `return` top-level
  "falla" fuera del wrapper del harness = OK). Propone diffs; NO auto-edita.
- **pyproject.toml**: `--ignore=tests/agent-evals` en pytest addopts + `tests/agent-evals` en ruff
  extend-exclude (snippets con bugs plantados, no codigo real). ruff via `uvx ruff check .` -> PASSED.

## GOTCHA de entorno (IMPORTANTE)
El `.venv` del repo es un venv de **LINUX** (`home = /home/samud/.local/share/uv/...linux-x86_64`),
inservible en Windows -> `uv run` intenta recrearlo con CPython 3.14.5 del sistema y FALLA al borrar
el symlink `.venv/lib64` ("Access is denied"). Workaround usado: `uvx ruff check .` (entorno efimero,
no toca el .venv). pytest local NO se pudo correr por esto -> se delega a **CI (Linux)**. Para arreglar
local: borrar `.venv` y `uv sync` con Python 3.11/3.12 (pendiente, no bloqueante).

## Invocacion del Workflow
`Workflow({name:'agent-improver'})` NO resuelve (el registro por name solo ve built-ins) ->
usar `Workflow({scriptPath: "C:\\Users\\samud\\dev\\4Dsentinel-suite\\.claude\\workflows\\agent-improver.js", args:{...}})`.

## VERIFICACION #2 — CUMPLIDA (Run `wf_9ecf8910-eeb`, 111 agentes, 0 errores, ~2.9M tok, 470s)
El motor corre end-to-end perfecto: eval + meta-review (17-22 findings/agente) + synthesis (diffs
reales y de alta calidad) + candidate-eval + loop-until-dry (corto bien en ronda 1). **Los 3 targets
dieron baseline catch-rate = 1.0** (Opus role-playeando los agentes actuales caza el 100% de mis
casos golden). Ningun candidato aceptado por el gate viejo.
GOTCHA: `args` llego como STRING JSON, no objeto -> se ignoro mi `reps:1` y corrio con defaults
(3 targets, rounds 2, reps 3). FIX aplicado (parsear args si es string).

## DOS INSIGHTS del run (motor MEJORADO en esta sesion, sin commitear aun)
1. **Techo de recall**: casos golden demasiado faciles para Opus -> baseline satura en 1.0 -> no hay
   headroom para medir delta de catch-rate. (Pendiente post-piloto: agregar casos mas sutiles.)
2. **Gate de select ciego a FP**: en `critic` el candidato BAJO falsos positivos 2.0->1.33/rep
   manteniendo catch-rate, pero se rechazo porque el criterio solo miraba delta de catch-rate.
   -> FIX: 2da via de aceptacion **PRECISION** (recall se mantiene en mayoria de reps + FP baja).
   Ahora hay `acceptedByRecall` (via A) y `acceptedByPrecision` (via B); `via` se propaga al reporte.
   + reporte expone `reviewDiff` (diff de ronda 1 SIEMPRE, aceptado o no, para revision humana).

## RE-RUN con fixes (Run `wlufn7g1b`, 111 agentes, 0 err, ~2.8M tok, 405s) — NO cacheo (re-corrio full)
Resultado con criterio nuevo (rounds:1, reps:3):
- bug-hunter: catch 1.0, fp 0.00->0.00, held 3/3 -> no aceptado (nada que mejorar, ya perfecto). OK.
- security-auditor: catch 1.0, fp 0.00->0.00, held 3/3 -> no aceptado. OK.
- critic: catch 1.0, fp **1.67->1.67** (sin mejora este run; el run previo fue 2.0->1.33) -> no aceptado.
  => **JUDGE-NOISE CONFIRMADO**: la senal de FP del judge varia entre corridas -> por eso reps+margen.
- **`reviewDiff` funciona**: los 3 exponen diff de alta calidad para revision humana (bug-hunter 4456c,
  security 3609c, critic 4612c), todos con `held 3/3` (ningun candidato degrada el recall).
- Diffs extraidos a scratchpad: `diff-bug-hunter.patch`, `diff-security-auditor.patch`, `diff-critic.patch`.

## CONCLUSION verif #2: el motor FUNCIONA. El gate NO auto-acepta con el dataset actual porque el
baseline satura (catch 1.0) y la senal de FP es ruidosa en casos faciles. Comportamiento correcto y
honesto. El valor entregado: (a) guard de regresion (los agentes cazan 100% de casos golden conocidos);
(b) generador de diffs de mejora que el conductor revisa a mano (modo human-in-loop que pidio el usuario).

## GOTCHA nuevo: el `resume` NO cacheo (re-corrio los 111 agentes). Motivo probable: editar el script
invalida el cache aunque los prompts de agent() no cambien. Para iterar barato, cambiar SOLO
post-proceso puede no bastar. (No critico; ~2.8M tok por corrida.)

## DECISION DEL USUARIO (pendiente)
1. **Aplicar diffs reales** a los agentes (bug-hunter/security/critic) -> mejora de producto. Requiere
   bump sentinel-agents 0.6.1->0.6.2 (gate F17) + check_agents.py verde + revision de no-regresion de
   contrato. Es un PR aparte del scaffolding.
2. **Endurecer dataset** (casos mas sutiles con headroom) para que el delta de recall sea medible.
3. **Arreglar venv local** (borrar .venv linux + uv sync 3.12) para correr check_agents/pytest local.
4. **PR del scaffolding** (rama feat/agent-improver: dataset + motor + pyproject). Sin tocar plugins.

## PENDIENTE
1. Leer resultado de verif #2; si el motor tiene un bug, iterar (Workflow resume con resumeFromRunId).
2. **Verif #4 (loop cierra)**: aplicar a mano 1 diff propuesto a bug-hunter.md, `check_agents.py` verde
   + `pytest tests/scripts/test_check_agents.py`, re-invocar Workflow -> catch-rate no baja. OJO: editar
   bug-hunter.md exige **bump de sentinel-agents** (gate F17) -> el PR de mejora bumpea 0.6.1->0.6.2.
3. Verif #1/#3 (proxy fiel / caso cazable con agente REAL via agentType): requieren plugin instalado ==
   repo. El glob de instalado no resolvio en recon -> confirmar version instalada antes.
4. Revisar `.claude/docs/testing.md` (hook pidio: edite pyproject/tests) -> actualizar si aplica.
5. PR de la rama feat/agent-improver (scaffolding). El PR de MEJORAS (diffs aplicados) va aparte con bump.

## ARRANCAR SESION NUEVA
cd C:\Users\samud\dev\4Dsentinel-suite ; leer .claude/docs/estado-sesion.md y ~/.claude/plans/snug-launching-newt.md
