# sentinel-agents

Suite de agentes más rigurosos que un suite genérico: salida parseable, severidad
calibrada, auto-verificación adversarial y evidencia dura. **9 auditores read-only
+ 2 ejecutores (validator y debugger, con Bash, nunca editan).**

- **`compliance-auditor`** — ISO 27000 por control-ID, máquina de estados de evidencia.
- **`security-auditor`** — AppSec exploitable con OWASP/CWE, CVSS, boundary-to-sink.
- **`advisor`** — análisis pre-plan (gaps rankeados, fuerza lectura).
- **`critic`** — revisa planes verificando contra el código.
- **`code-reviewer`** — review con verdict global + severidad calibrada.
- **`risk-assessor`** — riesgo del cambio con rúbrica 1-10 calibrada.
- **`bug-hunter`** — caza bugs de correctitud (lógica/off-by-one/null/races), read-only.
- **`librarian`** — lectura/resumen, solo-archivos, anti-alucinación.
- **`auditor-de-redaccion`** — califica la calidad de la redacción de un texto (spec/doc/política/hallazgo) en 5 dimensiones; domain-agnostic, read-only.
- **`validator`** — corre checks (type/lint/test/build) con timeouts; ejecutor con Bash.
- **`debugger`** — reproduce y diagnostica una falla vía Bash (con timeouts); nunca edita.

Ambos cumplen `references/agent-contract.md`. Al invocar `compliance-auditor`,
pasale la ruta absoluta de `references/iso-27000/` si la conocés (ver §7 del
contrato); si no, el agente la ubica por Glob.

**Regla de datos:** los resultados de una auditoría se registran en el proyecto
auditado o en un lugar privado — NUNCA de vuelta en `references/iso-27000/` (esa
KB viaja en blanco con el plugin y está protegida por checksum).
