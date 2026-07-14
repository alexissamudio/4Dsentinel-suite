---
name: 4d
description: "Flujo guiado por el marco 4D de AI Fluency (Delegación → Descripción → Discernimiento → Diligencia) para encarar una tarea con criterio. Usar cuando la tarea es grande, ambigua o de alto impacto, o cuando el usuario quiere aplicar el marco. Triggers on: '/4d', 'aplicar las 4d', 'aplicar 4d', 'marco 4d', 'ai fluency'."
---

# /4d — Flujo guiado por las 4D de AI Fluency

Guiá la tarea del usuario por las cuatro dimensiones, EN ORDEN. No son pasos rígidos
sino un ciclo, pero se recorren en este orden. La regla madre: **la mayoría de los
fallos con IA no vienen de un mal prompt, sino de un mal reparto** — arreglá primero
la Delegación, después la Descripción.

## Calibración inicial

Si la tarea es trivial (un typo, una pregunta puntual), NO apliques la ceremonia
completa: decilo y resolvé directo. Este flujo es para tareas con entregable real.

## Fase 1 — Delegación (¿qué hago yo y qué la IA?)

Leé `references/delegacion.md` de esta skill antes de ejecutar la fase.

1. **Objetivo claro**: exigí (o derivá y confirmá) la frase-objetivo:
   > "Quiero **[entregable concreto]** para **[audiencia/objetivo]**, que cumpla **[criterio de éxito]**."
   Si no se puede completar, la tarea NO está lista para delegarse: preguntá lo que falte
   (usá AskUserQuestion si hay opciones claras).
2. **Límites de la herramienta**: identificá si la tarea choca con límites conocidos
   (datos recientes, cifras exactas, información privada) y decilo explícitamente.
3. **Gap analysis opcional (orquestación con sentinel-agents)**: SOLO si el entregable
   es técnico/de código o un plan (gate: para texto puro, saltá esta oferta y seguí la
   guía pasiva). Ofrecé al usuario —con AskUserQuestion, opt-in— correr un gap analysis
   pre-tarea con `sentinel-agents:advisor`.
   - Si acepta: invocá el agente `sentinel-agents:advisor` vía Agent tool, pasándole la
     frase-objetivo y el contexto de la tarea; después surface-á su bloque
     `=== SENTINEL-REPORT ===` al usuario como insumo de la fase Descripción.
   - Fallback reactivo (no es detección): si la invocación falla porque el agente no
     resuelve (el plugin sentinel-agents no está instalado), seguí con la guía pasiva
     actual SIN error. El skill no puede detectar plugins: intenta y cae con gracia.
   - Mapeo completo de fases 4D ↔ agentes: `references/delegacion-agentes.md`.
4. **Tabla de reparto**: presentá las sub-tareas etiquetadas **IA / Usuario / Ambos**.
   Principio: la IA toma lo repetitivo; el usuario conserva el criterio, las cifras
   reales y la relación con terceros. Pedí confirmación del reparto antes de seguir.

## Fase 2 — Descripción (¿cómo comunico lo que quiero?)

Leé `references/descripcion.md`.

Construí el pedido en los TRES niveles, etiquetados para que el usuario los vea:

- **[Performance]** — rol y comportamiento ("actuá como X, mantené tono Y").
- **[Process]** — método ("primero listá/razoná..., recién después producí").
- **[Product]** — entregable ("formato, extensión, tono, audiencia").

Mostrá el prompt combinado resultante y ejecutalo (o entregáselo al usuario si el
destino es otra herramienta).

## Fase 3 — Discernimiento (¿puedo confiar en el resultado?)

Leé `references/discernimiento.md`.

Evaluá el resultado en los mismos tres niveles y mostrá la checklist marcada:

- **Product**: ¿correcto, completo y apropiado? Verificá contra el criterio de éxito de la Fase 1.
- **Process**: ¿la lógica se sostiene? Cazá alucinaciones: toda cifra, cita o fuente
  no provista por el usuario se marca como NO VERIFICADA o se elimina.
- **Performance**: ¿se mantuvo el rol/tono pedido de punta a punta?

Si algo falla, **iterá con correcciones puntuales** ("buen borrador; dos cambios: ...")
en vez de re-describir todo. Repetí el loop Descripción → Discernimiento hasta que la
checklist pase. Advertencia honesta: si el dominio excede tu capacidad de verificación
o la del usuario, decilo y proponé un paso de verificación independiente.

**Barrido de cobertura (opcional, cierre del Discernimiento):** para tareas con
entregable real, OFRECÉ en una línea —opt-in, declinar sin fricción— un barrido
final donde cada concern del entregable que ya evaluaste arriba queda **RESUELTO**
(tras evaluarlo el humano) o **DIFERIDO** con una razón de una línea, para que nada
quede sin abrir en silencio. El modelo lista y a lo sumo sugiere; **el humano
discierne y cierra cada item**. Mecánica y formato: `references/discernimiento.md`.

**Autoaprendizaje:** al cerrar el loop, si hubo correcciones del usuario o errores/
alucinaciones cazadas, guardá la lección en `.claude/docs/lecciones.md` con formato
`## [fecha] — [título]` + contexto + lección + cómo aplicar. Consolidá: máximo ~30
lecciones, fusioná duplicadas, borrá las supersedidas.

## Fase 4 — Diligencia (¿quién se hace responsable?)

Leé `references/diligencia.md`.

Cerrá con un **informe de diligencia** breve:

```
INFORME DE DILIGENCIA
- Creación: qué herramienta/modelo se usó y qué datos sensibles se evitaron o anonimizaron.
- Transparencia: qué parte hizo la IA y qué parte el humano (nota lista para compartir).
- Despliegue: qué debe verificar el usuario ANTES de publicar/enviar (lista concreta:
  cifras contra fuente, lectura completa, aprobación consciente; sumá acá los items
  DIFERIDO del barrido de cobertura, si lo hubo).
```

Recordale al usuario: el resultado es suyo — la IA es el martillo, no el responsable.
