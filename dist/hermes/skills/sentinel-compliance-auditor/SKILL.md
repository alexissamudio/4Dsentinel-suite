---
name: sentinel-compliance-auditor
description: Use when ISO 27001, compliance, SGSI. Audit controls with evidence.
version: 0.6.4
author: Alexis Samudio (ported from 4Dsentinel-suite)
license: MIT
metadata:
  hermes:
    tags: [sentinel, compliance, iso-27001, sgsi, audit, read-only]
    related_skills: [sentinel-security-auditor, sentinel-audit]
---

# sentinel-agents:compliance-auditor — Auditor ISO 27000

Evaluás el cumplimiento de un proyecto contra normas ISO 27000 usando checklists
de `references/iso-27000/`, control por control, exigiendo evidencia. Read-only.

REGLA DE ORO: sin evidencia verificable, un control NO está cumplido.

## Cuándo usar

- `/compliance`, "auditar compliance", "¿cumple con ISO 27001?"
- Desde `/sentinel-audit tipo=compliance`

## Cómo invocar

```python
delegate_task(
    goal="Auditá compliance ISO 27000 de [proyecto]. Normas: [27001, 27002, ...]. "
         "Recorré checklists control por control, exigí evidencia, reportá "
         "CUMPLE/PARCIAL/NO_CUMPLE/NO_APLICA/POR_VERIFICAR. "
         "Instrucciones en references/compliance-auditor.md.",
    context="Repositorio: [path]. KB iso-27000: [path a references/iso-27000/]."
)
```

## Instrucciones

Leé `references/compliance-auditor.md`. Recorrer checklists de la KB ISO 27000
(27001 SGSI, 27002 controles, 27017 nube, 27018 PII, 27032 ciberseguridad).
Cada control: buscar evidencia en el proyecto, asignar estado con evidencia re-leída.
Veredicto: CONFORME/NO_CONFORME/PARCIAL/INCOMPLETE.

## Límites

- Read-only. NUNCA marques CUMPLE sin evidencia.
- No hacés análisis de vulnerabilidades (security-auditor).
