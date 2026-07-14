---
tema: persistencia
descripcion: Politica de que pasa con los artefactos de la suite (planes, estado-sesion, puentes, memoria) cuando cambian los requisitos o el entendimiento.
audiencia: maintainer
actualizado: 2026-07-13
---

# Persistencia de artefactos — flow-back / flow-forward / living

Minado de spec-kit (`spec-persistence.md`). Vocabulario **domain-agnostic** para nombrar QUÉ PASA
con un artefacto vivo (un plan, un `estado-sesion`, un doc de puente, una memoria) cuando cambia
el entendimiento. No es una regla forzada: es una **convención que se elige por contexto** (opt-in).

## Las dos preguntas
1. Un artefacto ya completado, ¿es un **registro histórico** (congela lo decidido) o un **área
   editable** (se sigue tocando)?
2. La fuente de verdad, ¿es **única** (un doc manda) o **co-igual** (varios valen a la par)?

## Los tres modelos
- **flow-back** — el cambio se hace abajo (implementación) y se **refleja hacia arriba** en el
  artefacto de origen para que no mienta. Fuente de verdad = arriba.
- **flow-forward** — el origen se **congela** como registro histórico; los cambios viven solo
  adelante (notas/tareas nuevas). El origen no se re-escribe.
- **living** — el artefacto es siempre editable y dice la **verdad de ahora**; no hay versión
  histórica.

## Aplicado a NUESTROS artefactos
- **Plan file** (`~/.claude/plans/...`): **living** por tarea (se reescribe por increment); al
  cerrar, su verdad migra a memoria/commits (flow-back hacia la memoria).
- **`estado-sesion.md`**: **living** mientras hay pendientes; se **BORRA** al cerrar (no es
  histórico — un estado residual miente y hace arrancar la próxima sesión con info vieja).
- **`lecciones.md`**: **flow-forward** acotado (se acumulan, se consolidan duplicadas, máx ~30).
- **Docs de puentes** (`.claude/docs/*.md`): **living**; el hook `doc_drift.py` avisa cuando
  quedaron atrás (flow-back pendiente).
- **Memoria** (`~/.claude/projects/.../memory/*.md`): **living** por hecho; una nota por hecho, se
  corrige o borra si queda falsa.

## Regla práctica
Antes de dejar un artefacto, decidí conscientemente cuál de los 3 es: si es **histórico** no lo
re-escribas; si es **living**, que diga la verdad de AHORA; si es **flow-back**, propagá el cambio
hacia arriba. El artefacto que quedó a mitad de camino —ni congelado ni actualizado— es el que
rompe la continuidad.
