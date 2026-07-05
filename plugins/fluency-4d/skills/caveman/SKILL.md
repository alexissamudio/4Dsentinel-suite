---
name: caveman
description: "Activa o desactiva el modo Caveman de fluency-4d: un estilo de comunicación token-eficiente ('why use many token when few token do trick') que recorta el relleno de las respuestas SIN tocar código, comandos ni mensajes de error. Es opt-in: arranca apagado. Triggers on: '/caveman', 'modo caveman', 'talk like caveman', 'modo normal', 'normal mode'."
---

# /caveman — Toggle del modo de comunicación token-eficiente

Este skill SOLO escribe un flag global. El comportamiento (reinyectar el estilo
cada turno) lo hace el hook `caveman_injector.py`. El modo caveman arranca
**APAGADO**: este skill es el opt-in explícito.

## 1. Parseá el argumento

Del texto del usuario, resolvé un nivel:

- `auto`, `lite`, `full`, `ultra` → ese nivel (ON).
- `/caveman` **pelado** (sin argumento) → `auto` (el default).
- `off`, `modo normal`, `normal mode` → apagar.

Cualquier otra cosa no reconocida → tratala como `auto` y aclaralo en 1 línea.

## 2. Escribí el estado

Con la tool **Write**, escribí el archivo `~/.claude/fluency4d/caveman.json`
(ruta absoluta, expandiendo el home del usuario). La tool Write crea el
directorio padre si no existe (en instalación fresca `~/.claude/fluency4d/`
puede no existir todavía — no hace falta crearlo aparte).

- Para ENCENDER en un nivel `<lvl>`:
  ```json
  {"on": true, "level": "<lvl>"}
  ```
- Para APAGAR:
  ```json
  {"on": false, "level": "auto"}
  ```

## 3. Confirmá (en menos de 5 líneas)

- Decí qué quedó (ON en nivel `<lvl>`, o apagado / modo normal).
- Recordá brevemente el **invariante de protección**: el código, los comandos,
  las rutas, los identificadores, los mensajes de error y las URLs se conservan
  byte-por-byte, nunca se comprimen; y se respeta el idioma del usuario.
- Si quedó **ON**, escribí esa confirmación YA en estilo caveman (según el nivel
  elegido). Si quedó **OFF**, confirmá en estilo normal.

Los niveles, en corto:
- `lite` — saca relleno, oraciones completas.
- `full` — fragmentado, corta artículos/conectores.
- `ultra` — máxima compresión, telegráfico.
- `auto` — Claude autocalibra el nivel por respuesta.
