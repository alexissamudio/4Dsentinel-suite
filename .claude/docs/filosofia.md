---
tema: filosofia
descripcion: Qué ES y qué NO ES el plugin fluency-4d, y el criterio de decisión para features/ports.
audiencia: maintainer
actualizado: 2026-07-13
---

# Filosofía del plugin — qué ES y qué NO ES

Este doc **no reescribe** la filosofía: la reconcilia y la vuelve un **criterio de decisión**.
Las fuentes canónicas por dimensión viven, y siguen viviendo, en las references shipped del
skill `/4d` (`skills/4d/references/{delegacion,descripcion,discernimiento,diligencia}.md`).
Acá se cita, no se duplica ("one home per fact").

## Qué ES

fluency-4d es una **disciplina de colaboración humano-IA** — el método 4D de AI Fluency
(Delegación → Descripción → Discernimiento → Diligencia), llevado a la práctica en español.

- **Human-in-the-loop.** El humano conserva el criterio del reparto y es el responsable del
  resultado. Regla madre: *"la mayoría de los fallos con IA no vienen de un mal prompt, sino de
  un mal reparto"* (`skills/4d/SKILL.md:9-11`). Principio de reparto: *"delegá lo repetitivo,
  quedate con el criterio y la relación"* (`skills/4d/references/delegacion.md:37`).
- **Pedagógica e interactiva.** Las 4D son cuatro preguntas que el usuario aprende a hacerse
  (`README.md:60-67`): ¿qué hago yo y qué la IA? / ¿cómo le explico lo que quiero? / ¿puedo
  confiar en lo que me dio? / ¿quién se hace responsable?
- **Responsabilidad humana como ancla.** *"La IA es el martillo, no el responsable"*
  (`skills/4d/references/diligencia.md:1-3`).
- **Domain-agnostic.** El marco sirve para cualquier entregable (texto, contenido, código), no
  solo software (`skills/4d/references/delegacion-agentes.md:28-31`).
- **Conductor, no músico** (identidad user-level en `~/.claude/CLAUDE.md`): planificar,
  delegar, coordinar y **verificar** — el contexto es para razonar, no para almacenar.

## Qué NO ES

- **NO un motor de orquestación autónoma.** El 4D no "corre solo": el humano confirma el
  reparto y aprueba. Toda delegación en agentes es opt-in y surface-ada (guardrail v0.8.0,
  `skills/4d/SKILL.md` fase 1).
- **NO una base de conocimiento / wiki de building-blocks componibles** (modelo pull, estilo
  `system-design-skills`). Eso es una cosmovisión distinta: entrega de *contenido de dominio*;
  el 4D es una *disciplina de trabajo*.
- **NO un router que reemplace el criterio humano.** El hook `bridge_router.py` empuja docs por
  keyword (push), pero no decide por el usuario.
- **NO ceremonia obligatoria.** En tareas triviales no se aplica el flujo completo
  (`skills/4d/SKILL.md:14-16`): el rigor es proporcional al tamaño.
- **NO solo-código.** Invocar agentes de código sobre un entregable de texto es un error de
  categoría (`skills/4d/references/delegacion-agentes.md:28-31`).

## Framework vs. Foundations (un matiz honesto)

El PDF fuente tiene **dos capas**: el *Framework* (las 4D como disciplina) y las
*Foundations* (el "cómo funciona por dentro": IA generativa vs. tradicional, los tres
pilares, cómo se entrena un LLM, la ventana de contexto). El plugin **porta el
Framework** —la disciplina— con fidelidad casi 1:1. Las Foundations no se disuelven en el
flujo operativo: viven, **por diseño**, como referencia pedagógica en
`skills/4d/references/fundamentos.md` y se practican en `/4d-quiz`.

Esto **no contradice** el "NO una base de conocimiento" de arriba: `fundamentos.md` es una
capa fina de contexto para *entender por qué* las 4D funcionan (por qué la IA suena segura
y se equivoca), no un catálogo de contenido de dominio componible. La disciplina sigue
siendo el centro; los fundamentos la sostienen.

## Criterio de decisión (para toda feature o port)

Antes de sumar una capacidad al plugin, tiene que pasar este checklist. Si falla una, o se
rediseña con guardrail, o se rechaza:

1. **Delegación** — ¿El humano conserva el criterio del reparto?
2. **Diligencia** — ¿El humano sigue siendo el responsable del resultado?
3. **Guardrail de orquestación** — ¿Toda delegación en agentes es **opt-in, confirmada y
   surface-ada** — nunca autónoma? (el patrón que hizo que la integración con sentinel NO
   rompiera el 4D).
4. **Cosmovisión** — ¿Sirve a la disciplina de colaboración, o importa una worldview ajena
   (autónoma / pull / knowledge-base)?
5. **Domain-agnostic** — ¿No asume que el entregable es código?
6. **Proporcionalidad** — ¿No impone ceremonia sobre lo trivial? (`skills/4d/SKILL.md:14-16`)

## Aplicación: los 6 patrones minados de system-design-skills

Corriendo el criterio sobre la propuesta de mining (ver `estado-sesion.md`):

| Patrón | Veredicto | Por qué |
|---|---|---|
| #1 `fluency_check_skills.py` en CI | ✅ Pasa | Es **Diligencia aplicada al propio plugin** (verificación automática). No toca el método 4D. |
| #2 mapa de ownership de conceptos | ✅ Pasa | Higiene interna (DRY de docs). Neutral a la cosmovisión. |
| #3 verbos de relación en puentes | ✅ Pasa | Enriquece el push con semántica de grafo; sigue siendo push automático. |
| #4 mini SKILL-CONTRACT propio | ✅ Pasa | Consistencia interna, **por arquetipo propio** (no la plantilla ajena). |
| #5 orquestador / coverage-sweep autónomo | ⚠️ Solo con guardrail | Arriesga el **error de categoría**: importa el loop autónomo/pull que erosiona Delegación y Diligencia. Se acepta SOLO como checklist interactivo opt-in; se rechaza como loop automático. |

## Nota meta

El propio proceso de mining ya fue 4D en acción: cuando el advisor dijo *"no portes ciego"*,
eso fue **Discernimiento**. Extraer patrones ≠ importar la filosofía ajena — siempre que se
discierna, que es lo que el marco manda.

## La línea-misión (cierre del PDF, p12)

> **La fluidez con IA no es generar más rápido, sino generar mejor y con criterio.**

Es el norte del plugin: cada guardrail, cada checklist y cada `references/*.md` existe para
que el resultado sea uno del que te podés hacer responsable — no para acelerar la generación.
