# Fixture: target-vulnerable

Proyecto de juguete con hallazgos PLANTADOS para validar los agentes de
sentinel-agents (recall/precision). NO es código real; no lo uses de referencia.

## Hallazgos plantados (ground truth)

| # | Hallazgo | Ubicación | Espera |
|---|----------|-----------|--------|
| 1 | Secreto hardcodeado | `auth.js` `JWT_SECRET` | security-auditor: CWE-798, High/Critical, CONFIRMED |
| 2 | Inyección SQL | `auth.js` `findUser` | security-auditor: CWE-89, Critical, CONFIRMED |
| 3 | Login sin MFA | `auth.js` `login` | security-auditor: CWE-287 + control-ID `CTRL-27002-IAM-01`; compliance-auditor: `CTRL-27002-IAM-01` = `NO_CUMPLE` (Prioridad Crítica → verdict NO_CONFORME) |

## Hallazgos plantados para los agentes de revisión (v0.3)

| # | Hallazgo | Ubicación | Espera |
|---|----------|-----------|--------|
| 4 | Bug de correctness (off-by-one + div por cero) | `calc.py:7` `promedio` | **bug-hunter**: Critical (off-by-one en camino común + ZeroDivisionError en lista vacía), verdict BUGS_FOUND. code-reviewer también lo marca (Critical, CONCERNS/BLOCKED); el DUEÑO del bug de correctitud es bug-hunter. |
| 5 | Test que falla | `test_calc.py::test_promedio_correcto` | validator: verdict FAIL (falla real). **debugger**: verdict DIAGNOSED, causa raíz = `promedio` divide por `len-1` (off-by-one) en `calc.py:7`; fix = dividir por `len(numeros)` y manejar lista vacía (no parchea). |
| 6 | Plan sub-especificado | `PLAN.md` | advisor: GAPS_FOUND / critic: NEEDS_REVISION |
| 7 | Migración destructiva e irreversible | `migration.sql` | **risk-assessor**: banda 9-10 (irreversible, toca datos de producción, sin rollback ni backup), verdict DEFER (o PROCEED_WITH_CAUTION si asume backup externo). |
| 8 | Doc a resumir (prosa correcta, sin fallas) | `ARCHITECTURE.md` | **librarian**: verdict OK; resumen fiel de componentes/flujo/persistencia con evidencia `archivo:línea`. NO debe reportar hallazgos ni inventar módulos ausentes. |
| 9 | Spec mal redactada (no bugs de código) | `SPEC.md` | **auditor-de-redaccion**: verdict NECESITA_REVISION o DEFICIENTE. Hallazgos con `id: <marcador>@<ubicación>` (contrato §6): `Ambiguedad@SPEC.md:3` ("rápido"/"seguro" sin umbral), `Ambiguedad@SPEC.md:9` (R2 "de forma segura"), `Conflicto@SPEC.md:10` (R3 "hasta 1000... y muchos más"), `Gap@SPEC.md:14` ("El login funciona" no cubre R1/R2/R3 ni casos de error). |

## Precision (no debe alucinar)

No hay: XSS, SSRF, deserialización, path traversal. `descuento` en calc.py es
correcto (no es un bug). Un agente que reporte esos está alucinando.

Precisión de los agentes nuevos (castiga alucinaciones):
- **risk-assessor** solo debe marcar `migration.sql`; `ARCHITECTURE.md`/`SPEC.md`
  son cambios de bajo/nulo riesgo — no debe inflar su banda.
- **librarian** sobre `ARCHITECTURE.md` NO reporta hallazgos (es lectura/resumen):
  no inventa caché, ORM ni módulos que el doc no menciona.
- **auditor-de-redaccion** juzga SOLO la prosa de `SPEC.md`; NO debe afirmar que el
  login "funciona" o "falla" (eso es code-reviewer/validator), ni tocar `auth.js`
  como si fuera calidad de redacción.
- El bug de `calc.py` es de **correctitud** (bug-hunter/code-reviewer), NO de
  seguridad: el security-auditor no debe reclamarlo.
