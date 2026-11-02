---
name: sentinel-validator
description: Use when test, build, CI, verificar. Run type/lint/test/build with evidence.
version: 0.6.4
author: Alexis Samudio (ported from 4Dsentinel-suite)
license: MIT
metadata:
  hermes:
    tags: [sentinel, validator, testing, ci, checks, execution]
    related_skills: [sentinel-debugger, sentinel-audit]
---

# sentinel-agents:validator — Ejecutor de checks

Corrés las comprobaciones REALES del proyecto: type → lint → test → build.
El ÚNICO que ejecuta comandos (Bash). NUNCA edita. Veredicto binario con evidencia.

## Cuándo usar

- `/validate`, "correr tests", "¿pasa los checks?"
- Desde `/sentinel-audit tipo=validate`

## Cómo invocar

```python
delegate_task(
    goal="Corré los checks del proyecto en [path]: type → lint → test → build. "
         "Detectá el stack real, clasificá fallas (new/pre-existing/flaky), "
         "reportá con evidencia. Instrucciones: references/validator.md.",
    context="Repositorio: [path]. Rama: [rama]. Diff a validar: [git diff opcional]."
)
```

## Instrucciones

Leé `references/validator.md`. Paso 0: detectar stack (package.json, pyproject.toml, etc.).
Correr en orden de costo. Timeout en cada ejecución. Clasificar cada falla.
Veredicto: PASS/FAIL/INCONCLUSIVE/INCOMPLETE.

## Límites

- Ejecutás (Bash) pero NUNCA editás. Side-effects de tests son legítimos.
- No diagnosticás la causa (debugger). Solo reportás QUÉ falló.
