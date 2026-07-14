# Discernimiento — evaluar lo que te devuelve

Tiene los mismos tres niveles que la Descripción: **describís en tres capas y evaluás
en esas mismas tres capas**.

## Product Discernment — ¿el resultado sirve?

¿Es correcto, completo y apropiado para lo que necesitabas? Armá una checklist concreta
derivada del criterio de éxito. Ejemplo (email del caso guía):

- ☐ ¿Dice "8%" y "marzo" correctamente?
- ☐ ¿Son ~130 palabras?
- ☐ ¿Ofrece una vía de contacto?
- ☐ ¿El tono es cálido, no frío?

## Process Discernment — ¿el camino tiene sentido?

¿Cómo llegó la IA al resultado? Si le pediste que razonara, revisá si la lógica se
sostiene o si saltó a una conclusión.

**Cazar alucinaciones:** el borrador dice "Según un estudio de Gartner, el 82% de los
clientes acepta subas justificadas". No pediste datos externos y no hay fuente
verificable → se elimina. Inventar cifras con aire de autoridad es una alucinación típica.

## Performance Discernment — ¿mantuvo el rol?

¿Sostuvo el comportamiento pedido durante toda la interacción? Ejemplo: pediste tono
empático pero aparece una frase defensiva ("si no está de acuerdo, puede cancelar") →
rompió el rol, se corrige en la siguiente iteración.

## El loop Descripción → Discernimiento

Describir y discernir forman un ciclo: describís, evaluás, corregís y volvés a
describir. **Iterar es la habilidad que más distingue el uso fluido del superficial.**

Corrección puntual (no re-describir todo):

```
Buen borrador. Dos cambios: 1) eliminá la estadística de Gartner (no tengo la
fuente). 2) Reemplazá "si no está de acuerdo, puede cancelar" por una frase
que invite a conversar dudas. Mantené las ~130 palabras.
```

## Barrido de cobertura — cierre del Discernimiento (opcional)

Antes de dar por cerrado el loop podés ofrecer un **barrido de cobertura**: un pase
final para que ningún concern del entregable quede sin abrir en silencio. Es
**opt-in** —se ofrece en una línea y, si el usuario declina, seguís sin fricción—;
nunca un loop automático.

**Qué se barre (no hay lista nueva):** el barrido TOMA los concerns que ya surgieron
en esta fase —la checklist de criterios de éxito (arriba), las alucinaciones que
cazaste, y los tres niveles Product / Process / Performance— y les aplica un cierre
explícito. Son los concerns del entregable de ESTA tarea; nunca un catálogo técnico
genérico ajeno al entregable.

**Cómo se cierra (el humano, no el modelo):** presentás la tabla y el humano cierra
cada fila —no se aprueba la tabla en bloque—.

| Concern (de los ya evaluados) | Estado | Razón si DIFERIDO |
|-------------------------------|--------|-------------------|

- **RESUELTO** solo después de que el humano lo evaluó él mismo —sobre todo las cifras
  y fuentes, que verifica el humano contra el original (ver *Punto crítico*)—. El
  modelo lista y a lo sumo sugiere un estado marcado como sugerencia; **no
  auto-certifica RESUELTO**.
- **DIFERIDO** con una razón de una línea. Diferir con criterio es legítimo; dejarlo
  sin abrir en silencio no.

Los items **DIFERIDO** alimentan el eje Despliegue del informe de Diligencia: son
parte de lo que el usuario verifica antes de publicar.

## Punto crítico

El discernimiento depende de tu propio conocimiento del dominio. **No podés evaluar de
forma fiable algo que no entendés.** Si no sos experto:

1. Delegá solo tareas verificables,
2. sumá un revisor humano que sí lo sea, o
3. diseñá un paso de verificación independiente (una fuente, un dato de control).

## No lo confundas con Delegación (trampa del examen)

Evaluar el resultado **después** (¿esto sirve?) es Discernimiento; diseñar el reparto
**por adelantado** (quién hace qué) es Delegación (`references/delegacion.md`). No
mezcles el *después* con el *antes*: es la trampa más habitual del examen.
