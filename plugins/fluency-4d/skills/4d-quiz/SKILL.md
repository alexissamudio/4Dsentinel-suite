---
name: 4d-quiz
description: "Quiz de opción múltiple para practicar la certificación AI Fluency (Anthropic Academy): 24 preguntas del marco 4D con corrección explicada y detección de temas débiles. Triggers on: '/4d-quiz', 'quiz 4d', 'practicar examen ai fluency'."
---

# /4d-quiz — Práctica para la certificación AI Fluency

Tomale al usuario un quiz usando EXCLUSIVAMENTE el banco de
`references/preguntas.md` (24 preguntas en 6 secciones, cada una con opciones,
correcta y explicación YA escritas). NO inventes preguntas ni distractores.

## Flujo

1. **Cantidad**: `/4d-quiz [n]` — default 10; si n supera el tamaño del banco,
   usá el banco completo. Leé `references/preguntas.md` antes de empezar.
2. **Selección**: elegí las n preguntas REPARTIDAS entre las 6 secciones (no
   las primeras n del banco). Si el usuario repite el quiz en la misma sesión,
   variá las preguntas. No prometas aleatoriedad real.
3. **Una pregunta por vez** con AskUserQuestion:
   - El texto de la pregunta lleva el enunciado COMPLETO y las cuatro opciones
     escritas ("A) ... B) ... C) ... D) ...").
   - Los labels de las opciones son solo "A", "B", "C", "D" (los labels largos
     se truncan y pueden revelar la respuesta); en la description de cada
     opción repetí su texto corto.
   - Si el usuario responde por "Other" con texto libre, interpretalo como
     A-D si es inequívoco; si no, pedile la letra.
4. **Corrección inmediata**: tras cada respuesta, decí si es correcta y dá la
   explicación del banco (por qué la correcta lo es y por qué la elegida no,
   si falló). Llevá el puntaje.
5. **Abandono**: si el usuario deja de responder o cancela, mostrá el puntaje
   parcial sin insistir.
6. **Cierre**: puntaje final, secciones con más errores, y qué reference de
   `/4d` releer (cada pregunta del banco trae su referencia). Si el puntaje es
   alto en todo, decilo y recordá la trampa de examen (P24).

## Reglas

- Solo preguntas del banco, con sus opciones y explicaciones textuales.
- Una AskUserQuestion por pregunta (corrección inmediata > velocidad).
- Tono de práctica, no de evaluación: el objetivo es aprobar la certificación
  real de Anthropic Academy (Skilljar).
