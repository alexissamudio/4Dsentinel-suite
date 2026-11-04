# Delegación 4D → agentes de sentinel-agents

> **Requiere el skill sentinel-agents instalado.** Si no lo tenés, seguí la guía
> pasiva de `/4d` sin invocar agentes: el marco funciona igual.

Este mapeo conecta cada fase del marco 4D con el/los agente(s) de sentinel-agents que
aportan valor en esa fase.

| Fase 4D | Agente sentinel | Qué aporta | Estado |
|---|---|---|---|
| Delegación | sentinel-advisor | Gap analysis pre-tarea: requisitos ocultos, supuestos, riesgo de alcance | activo |
| Descripción | sentinel-librarian | Resume el contexto/archivos grandes para armar el pedido | manual |
| Descripción (revisar plan) | sentinel-critic | Verifica la ejecutabilidad del plan contra el código real | v2 |
| Discernimiento | sentinel-risk-assessor | Evalúa el riesgo del resultado antes de aceptarlo | v2 |
| Diligencia (código) | sentinel-code-reviewer + sentinel-bug-hunter + sentinel-validator | Revisión de calidad, caza de bugs y checks reales | v2 |

## Cómo emiten resultado

Los agentes de sentinel-agents son **read-only** (salvo validator y debugger, que
corren comandos pero tampoco editan). Cada uno emite un bloque
`=== SENTINEL-REPORT ===`; el skill `/4d` lo **surface-a** al usuario como insumo de la
fase siguiente.

## Gate por entregable

El marco 4D es **domain-agnostic**; sentinel-agents es code-centric. Para entregables de
**texto/contenido** (no código) NO invoques los agentes de código: no aportan y agregan ruido.