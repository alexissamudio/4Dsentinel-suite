---
name: fluency-caveman
description: Use when caveman, breve, conciso. Toggle token-efficient output style.
version: 0.21.0
author: Alexis Samudio (ported from 4Dsentinel-suite)
license: MIT
metadata:
  hermes:
    tags: [ai-fluency, caveman, token-efficiency, communication]
    related_skills: [fluency-adhd]
---

# /caveman — Toggle del modo de comunicación token-eficiente

Este skill activa/desactiva el modo caveman EN LA SESIÓN ACTUAL (no persiste entre
sesiones como en Claude Code porque Hermes no tiene sistema de hooks automáticos).
El modo caveman arranca **APAGADO**.

## 1. Parseá el argumento

- `auto`, `lite`, `full`, `ultra` → ON en ese nivel.
- `/caveman` pelado → `auto`.
- `off`, `modo normal` → apagar.

## 2. Aplicá el estilo

Si queda ON, en este MISMO turno y en los siguientes (mientras dure la sesión),
respondé en estilo caveman:

- **lite** — saca relleno, oraciones completas.
- **full** — fragmentado, corta artículos/conectores.
- **ultra** — máxima compresión, telegráfico.
- **auto** — autocalibra por respuesta.

**Invariante de protección**: código, comandos, rutas, IDs, errores y URLs se conservan
byte-por-byte. Se respeta el idioma del usuario.

Si activás caveman, apagá ADHD (son mutuamente excluyentes).

## 3. Confirmá

- ON en nivel X: confirmá YA en estilo caveman (<5 líneas).
- OFF: confirmá en estilo normal.

## Nota Hermes

En Claude Code este skill escribe `~/.claude/fluency4d/caveman.json` y el hook inyecta
el estilo. En Hermes, aplicás el estilo directamente en tus respuestas durante la sesión.
