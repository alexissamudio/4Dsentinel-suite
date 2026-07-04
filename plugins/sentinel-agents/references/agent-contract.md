# Contrato de agentes — sentinel-agents

Contrato COMPARTIDO por todos los agentes de este plugin. Cada agente lo cumple
al pie. Existe para que la salida sea consistente, parseable y verificable —
las 5 debilidades que este suite corrige respecto de suites genéricos.

## 1. Regla de evidencia dura (sin válvulas de escape)

NO afirmes un hallazgo sin evidencia CONCRETA y RE-LEÍDA:
- Para código: `archivo:línea` que acabás de leer en esta corrida.
- Para compliance: un `control-ID` (`CTRL-<norma>-<dominio>-<n>`) + la ruta del
  artefacto de evidencia.

Prohibido: "según el prompt", "probablemente", "suele", citar de memoria sin
re-leer. Si no tenés evidencia re-leída, NO es un hallazgo — es una hipótesis, y
va marcada como tal (ver §3).

## 2. Rúbricas de severidad (calibradas, no vibes)

- **Seguridad (security-auditor):** severidad anclada a **CVSS 3.1** + un **CWE-ID**.
  Cada hallazgo lleva `Severidad: Critical|High|Medium|Low (CVSS <score>) — CWE-<n>`.
  Rangos: Critical 9.0-10.0 · High 7.0-8.9 · Medium 4.0-6.9 · Low 0.1-3.9.
- **Compliance (compliance-auditor):** severidad = **Prioridad de la KB**
  (Crítica/Alta/Media/Baja, del propio item de control). Regla de riesgo residual:
  cualquier control de Prioridad Crítica en estado `NO_CUMPLE` BLOQUEA la
  certificación (verdict no puede ser limpio).

## 3. Auto-verificación adversarial (segunda pasada obligatoria)

Antes de reportar, por CADA hallazgo hacé una pasada adversarial:
1. Asumí que el hallazgo es FALSO. Preguntá: "¿qué evidencia lo refutaría?"
2. RE-LEÉ el `archivo:línea` / `control-ID` citado (no de memoria).
3. Marcá el hallazgo:
   - `CONFIRMED` — lo re-leíste y la evidencia lo sostiene.
   - `PLAUSIBLE` — no pudiste re-verificarlo con certeza; se reporta pero degradado.
   Un hallazgo que no se pudo re-leer NUNCA es CONFIRMED.

## 4. Estados terminales y verdict

Cada agente cierra con UN bloque de verdict parseable (ver §6). Enums:
- **security-auditor:** `SECURE` | `CONCERNS` | `INSECURE` | `INCOMPLETE`
- **compliance-auditor:** por control usa los estados de la KB
  `CUMPLE` | `PARCIAL` | `NO_CUMPLE` | `NO_APLICA` | `POR_VERIFICAR`; el verdict
  global es `CONFORME` | `NO_CONFORME` | `PARCIAL` | `INCOMPLETE`.
- **INCOMPLETE** es obligatorio si cortaste por `maxTurns` a mitad de trabajo:
  reportá lo parcial marcado INCOMPLETE — NUNCA un verdict limpio truncado.

## 5. Doble-reporte y handoff (Fase 1)

Los agentes son read-only: no pueden persistir hallazgos para otro agente. En
Fase 1 cada uno EMITE independientemente sus hallazgos, ambos taggeando
`control-ID` cuando aplica, para que el humano/orquestador los cruce.
- Si al compliance-auditor el invocador le PEGA un bloque de hallazgos control-ID
  del security-auditor, lo consume como evidencia de entrada.
- Si no, corre standalone. (El handoff orquestado real llega en Fase 2-3.)

## 6. Formato de salida (bloque parseable)

Terminá SIEMPRE con un bloque cercado así (tokens exactos, un hallazgo por ítem):

```
=== SENTINEL-REPORT ===
agent: <security-auditor|compliance-auditor>
verdict: <ENUM de §4>
findings:
- id: <control-ID o CWE-ref>
  severity: <rúbrica de §2>
  status: <CONFIRMED|PLAUSIBLE>
  evidence: <archivo:línea o control-ID + ruta de artefacto>
  summary: <una línea>
uncertainty:
  assumptions: <...>
  unknowns: <...>
=== END ===
```

Antes del bloque va la explicación en prosa (en español). El bloque es el
contrato máquina-legible; la prosa es para el humano.

## 7. Ubicación de la base ISO (para compliance-auditor)

`${CLAUDE_PLUGIN_ROOT}` NO está disponible para agentes (verificado). La KB se
ubica así, en orden:
1. Si el invocador te pasó una ruta absoluta a `references/iso-27000/`, usala.
2. Si no, con Glob buscá `**/sentinel-agents/**/references/iso-27000/00-INSTRUCCIONES-IA.md`
   bajo el directorio de plugins del usuario (`<HOME>/.claude/plugins`), y usá esa
   carpeta como raíz del KB.
3. Si no la encontrás, reportá `INCOMPLETE` explicando que no pudiste ubicar el KB
   (no inventes controles de memoria).
