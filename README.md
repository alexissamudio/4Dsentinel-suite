# sentinel-agents

[![validate](https://github.com/alexissamudio/sentinel-agents/actions/workflows/validate.yml/badge.svg)](https://github.com/alexissamudio/sentinel-agents/actions/workflows/validate.yml)

Suite de **agentes** para Claude Code, más rigurosos que un suite genérico:
**7 auditores read-only + 1 ejecutor** (validator). Todos hablan el mismo contrato.

| Agente | Qué hace |
|--------|----------|
| **`compliance-auditor`** | Audita contra ISO 27000 (27001/27002/27017/27018/27032) por control-ID, con máquina de estados de evidencia. Se niega a marcar `CUMPLE` sin evidencia. |
| **`security-auditor`** | AppSec exploitable: OWASP Top 10 + CWE, severidad CVSS, boundary-to-sink. |
| **`advisor`** | Análisis pre-plan: requisitos ocultos y gaps rankeados, forzando lectura del código. |
| **`critic`** | Revisa un plan verificándolo contra el código real; verdict de listo/no-listo. |
| **`code-reviewer`** | Review de código con verdict global escalar (CLEAN/CONCERNS/BLOCKED) + severidad. |
| **`risk-assessor`** | Riesgo del cambio con rúbrica 1-10 calibrada. |
| **`librarian`** | Lectura/resumen eficiente, solo-archivos, anti-alucinación. |
| **`validator`** | El único ejecutor: corre type/lint/test/build vía Bash (nunca edita), con timeouts. |

## Qué los hace "superiores"

Frente a suites genéricos, cada agente aquí tiene (contrato en
`plugins/sentinel-agents/references/agent-contract.md`):

1. **Salida parseable** con verdict de enum estable (bloque `SENTINEL-REPORT`).
2. **Severidad calibrada** (CVSS/CWE para seguridad; Prioridad ISO para compliance).
3. **Auto-verificación adversarial**: cada hallazgo se re-lee y se marca
   `CONFIRMED` o `PLAUSIBLE` — nada de badges sin sustancia.
4. **Evidencia dura**: sin `archivo:línea` / `control-ID` re-leído, no hay hallazgo.
5. **Read-only por construcción** (`tools: Read, Grep, Glob` — el allowlist ES el
   límite) y `maxTurns` en cada agente.

## Instalación

```
/plugin marketplace add alexissamudio/sentinel-agents
/plugin install sentinel-agents@sentinel-agents
```

## Uso

```
Auditá la seguridad de src/ con el subagente sentinel-agents:security-auditor
Corré una auditoría de compliance ISO 27002 con sentinel-agents:compliance-auditor
```

Para `compliance-auditor`, si conocés la ruta de la KB pasásela; si no, el agente
la ubica por Glob bajo `~/.claude/plugins`.

## Modelo plantilla / instancia (IMPORTANTE)

La base ISO (`references/iso-27000/`) viaja **en blanco** con el plugin. Los
resultados de una auditoría se registran en el **proyecto auditado** o en un lugar
privado — **NUNCA** de vuelta en `references/iso-27000/`. Una guarda de CI por
checksum (`check_kb_blank.py`) + un pre-commit local fallan si la KB se modifica,
para que el repo público nunca exponga la postura de controles de una organización.

## Roadmap

- **0.1.0:** compliance-auditor + security-auditor.
- **0.2.0 (esta):** los 6 agentes de revisión (advisor, critic, code-reviewer,
  validator, risk-assessor, librarian) — 7 read-only + 1 ejecutor.
- **0.3.0:** skill `/sentinel-audit` que orquesta el handoff entre agentes + el
  protocolo de dueños/dedup.

## Licencias

- Código (`agents/`, `scripts/`): MIT (`LICENSE`).
- Base ISO (`references/iso-27000/`): CC-BY-4.0 (`references/iso-27000/LICENSE`).

## Créditos

Contrato de agentes inspirado (y endurecido) a partir del suite de
[oh-my-claude](https://github.com/TechDufus/oh-my-claude) (MIT).
