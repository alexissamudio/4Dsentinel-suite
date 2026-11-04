---
name: fluency-verify-diff
description: Use when verificar diff, gate, antes de commit. Toggle diff verification gate.
version: 0.21.0
author: Alexis Samudio (ported from 4Dsentinel-suite)
license: MIT
metadata:
  hermes:
    tags: [ai-fluency, verify, diff, diligence, gate]
    related_skills: [fluency-4d]
---

# /verify-diff — Toggle del gate "verificá el diff"

Este skill activa/desactiva el gate de verificación de diff EN LA SESIÓN ACTUAL.
El gate arranca **APAGADO**.

## 1. Parseá el argumento

- `/verify-diff` pelado, `on`, `activar` → ON.
- `off`, `apagar` → OFF.

## 2. Comportamiento

Si queda ON: al cerrar una tarea (antes de dar el resultado por terminado), aplicá
la checklist de Discernimiento de `/4d` incluyendo:
- Verificar `git diff` contra el criterio de éxito.
- Si tenés acceso a `sentinel-agents`, ofrecé correr `delegate_task` con
  `sentinel-code-reviewer` o `sentinel-validator`.
- NUNCA entres en loop: una sola verificación por tarea.

## 3. Confirmá

- Gate ON: recordá el comportamiento en <5 líneas.
- Gate OFF: confirmá en 1 línea.

## Nota Hermes

En Claude Code este skill escribe `~/.claude/fluency4d/verify.json` y el hook
`discernment_gate.py` bloquea una vez por sesión. En Hermes, el gate es manual:
vos recordás verificar el diff al cerrar tareas durante esta sesión.
