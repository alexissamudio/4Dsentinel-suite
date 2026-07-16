# sentinel-agents

Suite de agentes más rigurosos que un suite genérico: salida parseable, severidad
calibrada, auto-verificación adversarial y evidencia dura. **9 auditores read-only
+ 2 ejecutores (validator y debugger, con Bash, nunca editan).** El detalle de cada
agente (para qué sirve) está en su `description` de frontmatter, ya visible en contexto.

Todos cumplen `references/agent-contract.md`. Al invocar `compliance-auditor`,
pasale la ruta absoluta de `references/iso-27000/` si la conocés (ver §7 del
contrato); si no, el agente la ubica por Glob.

**Regla de datos:** los resultados de una auditoría se registran en el proyecto
auditado o en un lugar privado — NUNCA de vuelta en `references/iso-27000/` (esa
KB viaja en blanco con el plugin y está protegida por checksum).

## Cuándo ofrecer auditar

Ofrecé (no ejecutes por tu cuenta) en el momento justo; el humano confirma:

- **Antes de mergear/cerrar un diff** → ofrecé `code-reviewer` (+ `validator`
  para correr los checks reales del proyecto).
- **Release o cambio riesgoso/irreversible** → ofrecé `risk-assessor` o la
  auditoría encadenada `/sentinel-audit`.
- **Código sensible** (auth, cripto, entrada externa, manejo de secretos) →
  ofrecé `security-auditor`.
- **Un spec/doc/política a revisar** (el entregable es TEXTO, no código) →
  ofrecé `auditor-de-redaccion`, no `code-reviewer`.

Cerrá siempre igual: **es opt-in; el humano decide; nunca auditar sin confirmar.**
Declinar no debe tener fricción.
