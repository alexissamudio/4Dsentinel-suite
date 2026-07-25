---
name: verify-diff
description: "Activa o desactiva el gate de verificación del diff de fluency-4d: al cerrar una tarea, bloquea UNA vez por sesión recordando verificar el diff (con /sentinel-audit tipo=review si tenés sentinel-agents, o revisando vos el git diff). Es opt-in: arranca apagado. Triggers on: '/verify-diff', 'verificar el diff', 'gate de diligencia', 'verify diff off', 'apagar verify'."
---

# /verify-diff — Toggle del gate "verificá el diff"

Este skill SOLO escribe un flag global. El comportamiento (bloquear una vez al
cerrar la tarea con la checklist de discernimiento + la orden de verificar el
diff) lo hace el hook `discernment_gate.py`. El gate arranca **APAGADO**: este
skill es el opt-in explícito.

## 1. Parseá el argumento

Del texto del usuario, resolvé un estado:

- `/verify-diff` **pelado** (sin argumento), `on`, `activar`, `prender` → encender (ON).
- `off`, `apagar`, `desactivar`, `verify diff off` → apagar (OFF).

Cualquier otra cosa no reconocida → tratala como `on` y aclaralo en 1 línea.

## 2. Escribí el estado

Con la tool **Write**, escribí el archivo `~/.claude/fluency4d/verify.json`
(ruta absoluta, expandiendo el home del usuario). La tool Write crea el
directorio padre si no existe (en instalación fresca `~/.claude/fluency4d/`
puede no existir todavía — no hace falta crearlo aparte).

- Para ENCENDER:
  ```json
  {"on": true}
  ```
- Para APAGAR:
  ```json
  {"on": false}
  ```

## 3. Confirmá (en menos de 5 líneas)

- Decí qué quedó (gate ON, o apagado).
- Si quedó **ON**, recordá el comportamiento: al intentar cerrar una tarea, el
  gate bloqueará **una sola vez por sesión** con la checklist de discernimiento
  de las 4D, incluyendo la orden de verificar el `git diff` (con
  `/sentinel-audit tipo=review` si tenés el plugin `sentinel-agents`, o revisando
  vos el diff contra el criterio de éxito). Los guards anti-bucle
  (`stop_hook_active`) y de subagentes (`agent_type`) se conservan: nunca
  entra en loop ni bloquea a los subagentes.
- El gate es compatible con la env var `FLUENCY_4D_STRICT=1` (misma activación).
