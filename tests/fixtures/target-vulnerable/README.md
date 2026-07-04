# Fixture: target-vulnerable

Proyecto de juguete con hallazgos PLANTADOS para validar los agentes de
sentinel-agents (recall/precision). NO es código real; no lo uses de referencia.

## Hallazgos plantados (ground truth)

| # | Hallazgo | Ubicación | Espera |
|---|----------|-----------|--------|
| 1 | Secreto hardcodeado | `auth.js` `JWT_SECRET` | security-auditor: CWE-798, High/Critical, CONFIRMED |
| 2 | Inyección SQL | `auth.js` `findUser` | security-auditor: CWE-89, Critical, CONFIRMED |
| 3 | Login sin MFA | `auth.js` `login` | security-auditor: CWE-287 + control-ID `CTRL-27002-IAM-01`; compliance-auditor: `CTRL-27002-IAM-01` = `NO_CUMPLE` (Prioridad Crítica → verdict NO_CONFORME) |

## Hallazgos plantados para los agentes de revisión (v0.2)

| # | Hallazgo | Ubicación | Espera |
|---|----------|-----------|--------|
| 4 | Bug de correctness (off-by-one + div por cero) | `calc.py` `promedio` | code-reviewer: Critical/Important, verdict CONCERNS/BLOCKED |
| 5 | Test que falla | `test_calc.py::test_promedio_correcto` | validator: verdict FAIL (falla real, new) |
| 6 | Plan sub-especificado | `PLAN.md` | advisor: GAPS_FOUND / critic: NEEDS_REVISION |

## Precision (no debe alucinar)

No hay: XSS, SSRF, deserialización, path traversal. `descuento` en calc.py es
correcto (no es un bug). Un agente que reporte esos está alucinando.
