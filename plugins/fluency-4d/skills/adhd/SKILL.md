---
name: adhd
description: "Activa o desactiva el modo ADHD/TDAH de fluency-4d: un estilo de comunicación accionable y estructurado (arranca por la acción, pasos numerados, next-step concreto) que ayuda a mantener el foco SIN tocar código, comandos ni mensajes de error. Es opt-in: arranca apagado. Triggers on: '/adhd', 'modo adhd', 'modo tdah', 'stop adhd mode', '/adhd off'."
---

# /adhd — Toggle del modo de comunicación accionable y estructurada

Este skill SOLO escribe un flag global. El comportamiento (reinyectar el estilo
cada turno) lo hace el hook `adhd_injector.py`. El modo ADHD arranca
**APAGADO**: este skill es el opt-in explícito.

## 1. Parseá el argumento

Del texto del usuario, resolvé un nivel:

- `auto`, `lite`, `full` → ese nivel (ON).
- `/adhd` **pelado** (sin argumento) → `auto` (el default).
- `off`, `stop adhd mode`, `/adhd off` → apagar.

Cualquier otra cosa no reconocida → tratala como `auto` y aclaralo en 1 línea.

## 2. Escribí el estado

Con la tool **Write**, escribí el archivo `~/.claude/fluency4d/adhd.json`
(ruta absoluta, expandiendo el home del usuario). La tool Write crea el
directorio padre si no existe (en instalación fresca `~/.claude/fluency4d/`
puede no existir todavía — no hace falta crearlo aparte).

- Para ENCENDER en un nivel `<lvl>`:
  ```json
  {"on": true, "level": "<lvl>"}
  ```
  Y ADEMÁS, en el mismo paso, escribí `~/.claude/fluency4d/caveman.json` con:
  ```json
  {"on": false, "level": "auto"}
  ```
  (mutex: activar ADHD apaga caveman — no pueden convivir).
- Para APAGAR:
  ```json
  {"on": false, "level": "auto"}
  ```

## 3. Confirmá (en menos de 5 líneas)

- Decí qué quedó (ON en nivel `<lvl>`, o apagado).
- Recordá brevemente el **invariante de protección**: no se eliminan pasos,
  advertencias ni detalles que cambien la correctitud; el código, los comandos,
  las rutas, los identificadores, los mensajes de error y las URLs se conservan
  byte-por-byte; y se respeta el idioma del usuario. Las reglas se relajan en
  explicaciones, en la confirmación de una acción destructiva, ante ambigüedad
  real o en un espiral de debugging.
- Si quedó **ON**, escribí esa confirmación YA en estilo ADHD (arrancá por la
  acción, sin preámbulo, según el nivel elegido). Si quedó **OFF**, confirmá en
  estilo normal.

Los niveles, en corto:
- `lite` — reglas siempre-seguras: arranca por la acción, sin preámbulo, listas cortas.
- `full` — además: pasos numerados, restate-state, next-step concreto, estimaciones.
- `auto` — Claude autocalibra: FULL en tareas multi-paso, LITE en turnos cortos.
