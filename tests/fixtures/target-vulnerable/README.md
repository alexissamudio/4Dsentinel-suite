# Fixture: target-vulnerable

Proyecto de juguete con hallazgos PLANTADOS para validar los agentes de
sentinel-agents (recall/precision). NO es código real; no lo uses de referencia.

## Hallazgos plantados (ground truth)

| # | Hallazgo | Ubicación | Espera |
|---|----------|-----------|--------|
| 1 | Secreto hardcodeado | `auth.js` `JWT_SECRET` | security-auditor: CWE-798, High/Critical, CONFIRMED |
| 2 | Inyección SQL | `auth.js` `findUser` | security-auditor: CWE-89, Critical, CONFIRMED |
| 3 | Login sin MFA | `auth.js` `login` | security-auditor: CWE-287 + control-ID `CTRL-27002-IAM-01`; compliance-auditor: `CTRL-27002-IAM-01` = `NO_CUMPLE` (Prioridad Crítica → verdict NO_CONFORME) |

## Precision (no debe alucinar)

No hay: XSS, SSRF, deserialización, path traversal. Un agente que reporte esos
sobre esta fixture está alucinando.
