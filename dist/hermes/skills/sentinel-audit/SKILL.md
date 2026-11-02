---
name: sentinel-audit
description: Use when auditoria, revision, pipeline. Orchestrate full audit pipeline.
version: 0.6.4
author: Alexis Samudio (ported from 4Dsentinel-suite)
license: MIT
metadata:
  hermes:
    tags: [sentinel, audit, orchestration, security, compliance, review]
    related_skills: [sentinel-advisor, sentinel-critic, sentinel-code-reviewer, sentinel-bug-hunter, sentinel-security-auditor, sentinel-validator, sentinel-compliance-auditor, sentinel-risk-assessor, sentinel-auditor-redaccion, sentinel-debugger, sentinel-librarian, fluency-4d]
---

# /sentinel-audit — Orquestador de auditorías

Coordinás auditorías con los agentes de sentinel-agents según el tipo pedido.
Cada agente es read-only y devuelve un bloque `=== SENTINEL-REPORT ===`.

## Tipos de auditoría

| Comando | Agente(s) | Qué hace |
|---|---|---|
| `/sentinel-audit tipo=advisor` | `sentinel-advisor` | Gap analysis pre-plan |
| `/sentinel-audit tipo=critic` | `sentinel-critic` | Revisar ejecutabilidad de plan |
| `/sentinel-audit tipo=review` | `sentinel-code-reviewer` + `sentinel-bug-hunter` | Code review + caza de bugs |
| `/sentinel-audit tipo=security` | `sentinel-security-auditor` | Vulnerabilidades OWASP/CWE/CVSS |
| `/sentinel-audit tipo=compliance` | `sentinel-compliance-auditor` | Compliance ISO 27000 |
| `/sentinel-audit tipo=risk` | `sentinel-risk-assessor` | Evaluación de riesgo del cambio |
| `/sentinel-audit tipo=validate` | `sentinel-validator` | Ejecutar type/lint/test/build |
| `/sentinel-audit tipo=redaccion` | `sentinel-auditor-redaccion` | Calidad de redacción |
| `/sentinel-audit tipo=debug` | `sentinel-debugger` | Diagnosticar falla |
| `/sentinel-audit tipo=full` | advisor → critic → review → security → risk → validate | Pipeline completo |
| `/sentinel-audit tipo=librarian` | `sentinel-librarian` | Extraer/resumir archivos |

## Método

1. Confirmá el scope (archivos/directorio/diff) con el usuario.
2. Lanzá los agentes con `delegate_task` (en paralelo si son independientes).
3. Recibí cada `=== SENTINEL-REPORT ===`, surface-alo al usuario.
4. Si hay hallazgos Critical, preguntá al usuario antes de seguir.

## Pipeline completo (`tipo=full`)

Orden: advisor (gap analysis) → critic (ejecutabilidad) → review + bugs en paralelo → security → risk → validate.
Cada fase sucede a la anterior. Si una fase bloquea (Critical), preguntar antes de seguir.

## Reglas

- Cada agente recibe su `references/<agent>.md` con instrucciones completas.
- El `agent-contract.md` es compartido por todos los agentes.
- Los agentes son read-only (salvo validator y debugger que ejecutan Bash sin editar).
- Deducir hallazgos entre agentes: si dos agentes reportan lo mismo, se referencia, no se duplica.

## Nota Hermes

En Claude Code los agentes se invocan vía Agent tool. En Hermes usamos `delegate_task`
con el goal apropiado y las instrucciones del agente en references/.
