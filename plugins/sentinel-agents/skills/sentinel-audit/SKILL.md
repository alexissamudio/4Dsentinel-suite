---
name: sentinel-audit
description: "Orquesta una auditoría encadenando los agentes de sentinel-agents (security, compliance ISO, code-review, validate) con handoff real entre ellos y un informe combinado. Usar cuando el usuario quiere auditar un proyecto/directorio de punta a punta. Triggers on: '/sentinel-audit', 'auditar con sentinel', 'auditoria completa'."
---

# /sentinel-audit — Orquestador de auditoría

Sos el ORQUESTADOR (rol tipo orchestrator: repartís y encadenás, no reimplementás
lo que hacen los agentes). Corrés los agentes de `sentinel-agents` en secuencia,
**relayás sus bloques `=== SENTINEL-REPORT ===` por RUTA** (no pegándolos textual) de
uno al siguiente, y armás un informe combinado. Seguís el contrato
`references/agent-contract.md` (§5 handoff/dueños, §6 formato).

## Relay por ruta (cómo pasar un reporte al siguiente agente)

Los agentes son read-only (no escriben): **el que escribe el reporte a disco sos vos**.
1. Elegí un `run-id` corto para esta auditoría (p.ej. `audit-<target-basename>-NN`).
2. Cuando un agente A devuelva su bloque, escribilo tal cual a
   `<target>/.sentinel/<run-id>/<A>.md` (crealo si hace falta). **La primera vez que
   creás `<target>/.sentinel/`, protegé el repo auditado del commit accidental:** si
   `<target>/.gitignore` existe y no ignora `.sentinel/`, agregale una linea `.sentinel/`;
   si no existe, avisá al usuario que los reportes quedan sin ignorar. Escribir ahí es
   **opt-in**: si el usuario no quiere tocar su repo, usá un dir privado fuera del target.
3. Al invocar el agente B, en vez de pegarle el bloque entero pasale: la **ruta** del
   reporte de A, su **verdict**, y un **digest de ≤3 líneas** (los ids clave que B va a
   citar, p.ej. `CWE-89@app/db.py:42`). B usa su `Read`/`Grep` para abrir esa ruta y
   traer SOLO el finding que necesita (`grep 'CWE-'` / `grep 'CTRL-'`).

Regla de datos: `.sentinel/` vive en el proyecto auditado (o un lugar privado), NUNCA
de vuelta en `references/iso-27000/` (ver `../../CLAUDE.md`).

## Args

- `target` — path a auditar (default: el cwd).
- `tipo` — `security` (default) | `compliance` | `review` | `full`.
  Cadenas cortas por defecto: `full` encadena 4 agentes y acumula contexto — es
  opt-in explícito.

## Orquestación por tipo (invocá con el Agent tool)

- **security:** `sentinel-agents:security-auditor` sobre `target`. Un solo agente,
  sin handoff.
- **compliance (handoff ISO):**
  1. Corré `sentinel-agents:security-auditor` sobre `target`. Escribí su bloque a
     `<target>/.sentinel/<run-id>/security.md` (ver "Relay por ruta").
  2. **Ubicá la KB una vez**: Glob `**/sentinel-agents/**/references/iso-27000/00-INSTRUCCIONES-IA.md`
     bajo `~/.claude/plugins`; pasá esa ruta al compliance.
  3. Corré `sentinel-agents:compliance-auditor` pasándole en el prompt: la **ruta**
     `<target>/.sentinel/<run-id>/security.md` + verdict + digest de los `CWE-*`/`CTRL-*`
     relevantes, más la ruta de la KB. El compliance abre esa ruta con `Read`/`Grep`
     para el finding que va a CITAR en su `evidence:` del control correspondiente.
- **review:** corré `git diff` sobre `target` (vos tenés Bash); pasale el diff + la
  descripción de la tarea a `sentinel-agents:code-reviewer` (para su scope-check), y
  corré `sentinel-agents:validator` (detecta stack y corre checks).
- **full:** security → compliance (con handoff) → code-reviewer → validator, en ese
  orden, relayando por ruta lo que aplique (cada agente escribe a
  `<target>/.sentinel/<run-id>/<agente>.md`).

## Agregación (informe combinado)

- Juntá los bloques de cada agente en un solo informe.
- **Dueños por tipo de id (§5, best-effort):** el `CWE-*` lo mantiene security; el
  `CTRL-*` lo mantiene compliance; el otro agente lo REFERENCIA, no lo re-enuncia.
- Cuando relayaste el reporte de A (por su ruta) a la invocación de B, escribí una
  línea `handoff: <A>→<B>` en el informe (traza que el relay ocurrió de verdad).
- Cerrá con un resumen: verdict de cada agente + los hallazgos dedupeados.

## Reglas

- El relay depende de vos: escribí el bloque entre `=== SENTINEL-REPORT ===` y
  `=== END ===` a `<target>/.sentinel/<run-id>/<agente>.md` y pasá al siguiente la
  ruta + verdict + digest (no el bloque entero). NO prometas dedup perfecto (es
  best-effort).
- No reimplementás el análisis: los agentes hacen el trabajo, vos coordinás.
- Nota de diligencia al cierre: "Auditoría orquestada por sentinel-agents; revisá
  los hallazgos antes de actuar."
