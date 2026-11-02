---
name: fluency-4d-quiz
description: Use when examen, certificacion, quiz. Practice AI Fluency certification.
version: 0.21.0
author: Alexis Samudio (ported from 4Dsentinel-suite)
license: MIT
metadata:
  hermes:
    tags: [ai-fluency, 4d, quiz, certification, practice]
    related_skills: [fluency-4d]
---

# /4d-quiz — Práctica para la certificación AI Fluency

Tomale al usuario un quiz usando EXCLUSIVAMENTE el banco de `references/preguntas.md`
(24 preguntas en 6 secciones). NO inventes preguntas ni distractores.

## Flujo

1. **Cantidad**: `/4d-quiz [n]` — default 10; máximo el banco completo.
2. **Selección**: repartidas entre las 6 secciones (no las primeras n).
3. **Una por vez** con `clarify`:
   - Enunciado COMPLETO con opciones A-D en el texto de la pregunta.
   - Choices: solo "A", "B", "C", "D".
   - Si responde por "Other", interpretalo como A-D si es inequívoco.
4. **Corrección inmediata**: tras cada respuesta, correcta/incorrecta + explicación del banco.
5. **Abandono**: si cancela, mostrá puntaje parcial sin insistir.
6. **Cierre**: puntaje final, secciones con más errores, qué reference releer.

## Reglas

- Solo preguntas del banco, textuales.
- Una pregunta por vez (corrección inmediata > velocidad).
- Tono de práctica, no de evaluación: el objetivo es aprobar la certificación real.
