# sentinel-agents

Suite de agentes de auditoría read-only, más rigurosos que un suite genérico:
salida parseable, severidad calibrada, auto-verificación adversarial y evidencia
dura (sin afirmar sin re-leer).

- **`compliance-auditor`** — audita un proyecto contra las normas ISO 27000
  (27001/27002/27017/27018/27032) usando las checklists de `references/iso-27000/`;
  mapea hallazgos a control-IDs, con máquina de estados de evidencia.
- **`security-auditor`** — AppSec exploitable con OWASP/CWE, severidad CVSS y
  trazado boundary-to-sink.

Ambos cumplen `references/agent-contract.md`. Al invocar `compliance-auditor`,
pasale la ruta absoluta de `references/iso-27000/` si la conocés (ver §7 del
contrato); si no, el agente la ubica por Glob.

**Regla de datos:** los resultados de una auditoría se registran en el proyecto
auditado o en un lugar privado — NUNCA de vuelta en `references/iso-27000/` (esa
KB viaja en blanco con el plugin y está protegida por checksum).
