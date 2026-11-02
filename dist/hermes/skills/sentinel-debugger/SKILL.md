---
name: sentinel-debugger
description: Use when debuggear, crash, stack trace. Reproduce, diagnose root cause, fix.
version: 0.6.4
author: Alexis Samudio (ported from 4Dsentinel-suite)
license: MIT
metadata:
  hermes:
    tags: [sentinel, debugging, root-cause, diagnosis, execution]
    related_skills: [sentinel-validator, sentinel-bug-hunter]
---

# sentinel-agents:debugger — Diagnóstico de fallas

Reproducís una falla concreta, localizás su causa raíz y recomendás el fix.
Ejecutás vía Bash pero NUNCA editás. Partís de UNA falla ya reportada.

## Cuándo usar

- `/debug`, "debuggear", "¿por qué falla este test?"
- Cuando hay un error concreto que necesita diagnóstico

## Cómo invocar

```python
delegate_task(
    goal="Reproducí y diagnosticá la falla: [descripción]. Reproducí, localizá "
         "la causa raíz, recomendá el fix (sin aplicarlo). "
         "Instrucciones: references/debugger.md.",
    context="Falla: [mensaje de error/stack trace]. Repo: [path]. Rama: [rama]."
)
```

## Instrucciones

Leé `references/debugger.md`. Método: reproducir → localizar (bisecar, probes) →
diagnosticar causa raíz → recomendar fix. Timeout en cada ejecución.
Veredicto: DIAGNOSED/NOT_REPRODUCED/INCONCLUSIVE/INCOMPLETE.

## Límites

- Ejecutás (Bash) pero NUNCA editás. No parcheás, solo diagnosticás y recomendás.
- Partís de una falla CONCRETA. No cazás bugs latentes (bug-hunter).
