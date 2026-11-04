---
name: fluency-4d
description: "Use when tarea, plan, implementar. 4D Fluency: Delegacion, Desc, Discern, Diligencia."
version: 0.21.0
author: Alexis Samudio (ported from 4Dsentinel-suite)
license: MIT
metadata:
  hermes:
    tags: [ai-fluency, 4d, framework, delegacion, discernimiento, productividad]
    related_skills: [fluency-4d-init, fluency-4d-status, fluency-4d-quiz]
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
   (usá `clarify` si hay opciones claras).
   - **Plan activo:** leé el `.md` más reciente en `.hermes/plans/` (por mtime). Si existe,
     incorporá su objetivo y estado al contexto de esta tarea.
2. **Límites de la herramienta**: identificá si la tarea choca con límites conocidos
   (datos recientes, cifras exactas, información privada) y decilo explícitamente.
3. **Gap analysis opcional (orquestación con sentinel-agents)**: SOLO si el entregable
   es técnico/de código o un plan (gate: para texto puro, saltá esta oferta y seguí la
   guía pasiva). Ofrecé al usuario —con `clarify`, opt-in— correr un gap analysis
   pre-tarea con `delegate_task` usando las instrucciones del agente `sentinel-advisor`.
   - Si acepta: invocá `delegate_task` con el goal apropiado, pasándole la
     frase-objetivo y el contexto de la tarea; después surface-á su resultado al usuario
     como insumo de la fase Descripción.
   - Fallback: si `delegate_task` falla, seguí con la guía pasiva actual SIN error.
   - Mapeo de fases 4D ↔ agentes: `references/delegacion-agentes.md`.
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

- **Plan formal:** si la tarea justifica un plan escrito (multi-step, delegación a agentes,
  o el usuario pide `/plan`), guardalo en `.hermes/plans/YYYY-MM-DD_HHMMSS-<slug>.md`
  usando el formato del skill `plan`.

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

**Barrido de cobertura (opcional):** para tareas con entregable real, OFRECÉ en una
línea —opt-in, declinar sin fricción— un barrido final. Mecánica y formato:
`references/discernimiento.md`.

**Autoaprendizaje:** al cerrar el loop, SIEMPRE guardá con `memory(action='add', target='memory')`:
- Si el usuario corrigió algo: `"leccion: [tema] — [correccion] — [como evitar en futuro]"`
- Si se cazó una alucinación: `"alucinacion: [tipo] en [contexto] — [verificacion futura]"`
- Formato compacto, 1-2 lineas por leccion. NO esperes a que el usuario lo pida: hacelo automaticamente al cerrar.

## Fase 4 — Diligencia (¿quién se hace responsable?)

Leé `references/diligencia.md`.

Cerrá con un **informe de diligencia** breve:
```
INFORME DE DILIGENCIA
- Creación: qué herramienta/modelo se usó y qué datos sensibles se evitaron.
- Transparencia: qué parte hizo la IA y qué parte el humano.
- Despliegue: qué debe verificar el usuario ANTES de publicar/enviar.
```
Recordale al usuario: el resultado es suyo — la IA es el martillo, no el responsable.

## Nota Hermes

Portado desde Claude Code (fluency-4d). En Hermes no hay hooks automáticos
(bridge_router, adhd_injector, etc.). El contexto se maneja con skills bajo demanda
y `memory` para lecciones persistentes.
