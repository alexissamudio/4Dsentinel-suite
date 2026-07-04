---
name: sentinel-audit
description: "Orquesta una auditoría encadenando los agentes de sentinel-agents (security, compliance ISO, code-review, validate) con handoff real entre ellos y un informe combinado. Usar cuando el usuario quiere auditar un proyecto/directorio de punta a punta. Triggers on: '/sentinel-audit', 'auditar con sentinel', 'auditoria completa'."
---

# /sentinel-audit — Orquestador de auditoría

Sos el ORQUESTADOR (rol tipo orchestrator: repartís y encadenás, no reimplementás
lo que hacen los agentes). Corrés los agentes de `sentinel-agents` en secuencia,
**relayás sus bloques `=== SENTINEL-REPORT ===`** de uno al siguiente, y armás un
informe combinado. Seguís el contrato `references/agent-contract.md` (§5 handoff/
dueños, §6 formato).

## Args

- `target` — path a auditar (default: el cwd).
- `tipo` — `security` (default) | `compliance` | `review` | `full`.
  Cadenas cortas por defecto: `full` encadena 4 agentes y acumula contexto — es
  opt-in explícito.

## Orquestación por tipo (invocá con el Agent tool)

- **security:** `sentinel-agents:security-auditor` sobre `target`. Un solo agente,
  sin handoff.
- **compliance (handoff ISO):**
  1. Corré `sentinel-agents:security-auditor` sobre `target`. Guardá su bloque.
  2. **Ubicá la KB una vez**: Glob `**/sentinel-agents/**/references/iso-27000/00-INSTRUCCIONES-IA.md`
     bajo `~/.claude/plugins`; pasá esa ruta al compliance.
  3. Corré `sentinel-agents:compliance-auditor` PEGÁNDOLE en el prompt el bloque
     SENTINEL-REPORT de security (sus findings `CWE-*`/`CTRL-*`) como evidencia de
     entrada, más la ruta de la KB. El compliance debe CITAR el finding relayado en
     su `evidence:` del control correspondiente.
- **review:** corré `git diff` sobre `target` (vos tenés Bash); pasale el diff + la
  descripción de la tarea a `sentinel-agents:code-reviewer` (para su scope-check), y
  corré `sentinel-agents:validator` (detecta stack y corre checks).
- **full:** security → compliance (con handoff) → code-reviewer → validator, en ese
  orden, relayando lo que aplique.

## Agregación (informe combinado)

- Juntá los bloques de cada agente en un solo informe.
- **Dueños por tipo de id (§5, best-effort):** el `CWE-*` lo mantiene security; el
  `CTRL-*` lo mantiene compliance; el otro agente lo REFERENCIA, no lo re-enuncia.
- Cuando pegaste el bloque de A en la invocación de B, escribí una línea
  `handoff: <A>→<B>` en el informe (traza que el relay ocurrió de verdad).
- Cerrá con un resumen: verdict de cada agente + los hallazgos dedupeados.

## Reglas

- El relay depende de vos: tomá el bloque entre `=== SENTINEL-REPORT ===` y
  `=== END ===` textual y pegalo. NO prometas dedup perfecto (es best-effort).
- No reimplementás el análisis: los agentes hacen el trabajo, vos coordinás.
- Nota de diligencia al cierre: "Auditoría orquestada por sentinel-agents; revisá
  los hallazgos antes de actuar."
