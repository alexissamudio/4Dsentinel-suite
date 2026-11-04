---
description: "Activa o desactiva el modo Caveman de fluency-4d: un estilo de comunicación token-eficiente ('why use many token when few token do trick') que recorta el relleno de las respuestas SIN tocar código, comandos ni mensajes de error. Es opt-in: arranca apagado. Triggers on: '/caveman', 'modo caveman', 'talk like caveman', 'modo normal', 'normal mode'."
agent: build
---

<!-- Generado por tools/multiharness/build_harness.py desde plugins/fluency-4d/skills/caveman (cuerpo incrustado y traducido a OpenCode). NO editar a mano. -->

> **OpenCode (bundle 4Dsentinel, OpenCode 1.19.x / 2.2.5).** Este comando INCRUSTA el skill `caveman` completo: segui las instrucciones de abajo tal cual. NO busques un archivo de skill ni rutas de instalacion de Claude Code. Los subagentes de la suite (advisor, critic, librarian, ...) se invocan con la tool `task` (`subagent_type: <nombre>`) en OpenCode 1.x, o con la tool `subagent` (`agent: <nombre>`) en 2.x.
>
> El flag va en `~/.claude/fluency4d/` A PROPOSITO (no en `~/.config/opencode`): es la ruta que lee `caveman_injector.py`, que en OpenCode corre via el plugin `fluency-hooks.js` en cada mensaje. Usa la tool `write` con la ruta absoluta expandida (esta fuera del proyecto: OpenCode pedira permiso `external_directory`, aprobalo).

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
  Y ADEMÁS, en el mismo paso, escribí `~/.claude/fluency4d/adhd.json` con:
  ```json
  {"on": false, "level": "auto"}
  ```
  (mutex: activar caveman apaga ADHD — no pueden convivir).
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

Argumentos del usuario: `$ARGUMENTS`
