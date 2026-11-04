---
name: sentinel-auditor-redaccion
description: Use when redaccion, claridad, documento. Audit text quality 6 dims.
version: 0.6.4
author: Alexis Samudio (ported from 4Dsentinel-suite)
license: MIT
metadata:
  hermes:
    tags: [sentinel, writing, quality, audit, text, read-only]
    related_skills: [sentinel-audit]
---

# sentinel-agents:auditor-de-redaccion — Calidad de redacción

Calificás la calidad de cómo está escrito un texto (requisitos, spec, doc, política).
NO evaluás si el sistema funciona. 6 dimensiones. Read-only.
Veredicto: BIEN_ESCRITO/NECESITA_REVISION/DEFICIENTE.

## Cuándo usar

- `/audit-text`, "auditar redacción", "¿está bien escrito este documento?"
- Desde `/sentinel-audit tipo=redaccion`

## Cómo invocar

```python
delegate_task(
    goal="Auditá la calidad de redacción del texto en [archivo]. 6 dimensiones: "
         "completitud, claridad, consistencia, medibilidad, cobertura, atomicidad. "
         "Instrucciones: references/auditor-de-redaccion.md.",
    context="Texto a auditar: [ruta o contenido]. Tipo: [spec/doc/política]."
)
```

## Instrucciones

Leé `references/auditor-de-redaccion.md`. Marcadores: [Gap], [Ambiguedad],
[Conflicto], [Supuesto]. Severidad: Critical/Important/Minor anclados al COSTO
de actuar sobre el texto. Veredicto: BIEN_ESCRITO/NECESITA_REVISION/DEFICIENTE.

## Límites

- Read-only. Domain-agnostic. Solo el TEXTO, no el sistema.
- NO evaluás sustancia/viabilidad (advisor/critic).
