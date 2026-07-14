# Delegación 4D → agentes de sentinel-agents

> **Requiere el plugin sentinel-agents instalado.** Si no lo tenés, seguí la guía
> pasiva de `/4d` sin invocar agentes: el marco funciona igual, solo que la revisión
> la hacés vos (o Claude en el hilo principal) en vez de delegarla.

Este mapeo conecta cada fase del marco 4D con el/los agente(s) de sentinel-agents que
aportan valor en esa fase. En v1 solo está **activo** el acople de Delegación; el resto
queda documentado como objetivo de v2 o como paso manual.

| Fase 4D | Agente sentinel | Qué aporta | Estado |
|---|---|---|---|
| Delegación | `sentinel-agents:advisor` | Gap analysis pre-tarea: requisitos ocultos, supuestos, riesgo de alcance | **v1 activo** |
| Descripción | `sentinel-agents:librarian` | Resume el contexto/archivos grandes para armar el pedido | manual |
| Descripción (revisar plan) | `sentinel-agents:critic` | Verifica la ejecutabilidad del plan contra el código real | v2 (mapeo a resolver) |
| Discernimiento | `sentinel-agents:risk-assessor` | Evalúa el riesgo del resultado antes de aceptarlo | v2 (mapeo a resolver) |
| Diligencia (si el entregable ES código) | `sentinel-agents:code-reviewer` + `bug-hunter` + `validator` | Revisión de calidad, caza de bugs y checks reales (type/lint/test/build) | v2 |

## Cómo emiten resultado

Los agentes de sentinel-agents son **read-only** (salvo `validator` y `debugger`, que
corren comandos vía Bash pero tampoco editan). Cada uno emite un bloque
`=== SENTINEL-REPORT ===`; el skill `/4d` lo **surface-a** al usuario como insumo de la
fase siguiente (p. ej., el reporte del advisor alimenta la Descripción).

## Gate por entregable

El marco 4D es **domain-agnostic**; sentinel-agents es code-centric. Para entregables de
**texto/contenido** (no código) NO invoques los agentes de código (`code-reviewer`,
`bug-hunter`, `validator`): no aportan y agregan ruido. Reservá esos agentes para cuando
el entregable ES código; para el resto, seguí la guía pasiva.
