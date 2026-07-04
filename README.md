# sentinel-agents

[![validate](https://github.com/alexissamudio/sentinel-agents/actions/workflows/validate.yml/badge.svg)](https://github.com/alexissamudio/sentinel-agents/actions/workflows/validate.yml)

Suite de **agentes de auditoría** para Claude Code, read-only y más rigurosos que
un suite genérico. Fase 1: los dos agentes diferenciados.

| Agente | Qué hace |
|--------|----------|
| **`compliance-auditor`** | Audita un proyecto contra ISO 27000 (27001/27002/27017/27018/27032) recorriendo checklists por control-ID, con máquina de estados de evidencia. Se niega a marcar `CUMPLE` sin evidencia. |
| **`security-auditor`** | AppSec exploitable: OWASP Top 10 + CWE, severidad anclada a CVSS, trazado boundary-to-sink. |

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

- **Fase 1 (esta):** compliance-auditor + security-auditor.
- **Fase 2-3:** los agentes de revisión (advisor, critic, code-reviewer, validator,
  risk-assessor) con el mismo contrato superior, y el handoff orquestado.

## Licencias

- Código (`agents/`, `scripts/`): MIT (`LICENSE`).
- Base ISO (`references/iso-27000/`): CC-BY-4.0 (`references/iso-27000/LICENSE`).

## Créditos

Contrato de agentes inspirado (y endurecido) a partir del suite de
[oh-my-claude](https://github.com/TechDufus/oh-my-claude) (MIT).
