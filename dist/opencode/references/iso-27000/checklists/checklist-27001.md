# Checklist — ISO/IEC 27001 (SGSI / Gobierno)

> **Norma asociada:** [`../normas/01-iso-27001-sgsi.md`](../normas/01-iso-27001-sgsi.md)
> **Instrucciones de uso:** [`../00-INSTRUCCIONES-IA.md`](../00-INSTRUCCIONES-IA.md)
> **Estados:** `✅ CUMPLE` · `⚠️ PARCIAL` · `❌ NO_CUMPLE` · `➖ NO_APLICA` · `🔍 POR_VERIFICAR`

---

## Dominio: Gestión de Riesgos

### [CTRL-27001-RSK-01] Inventario de activos de información
- **Estado:** 🔍 POR_VERIFICAR
- **Anexo A:** A.5.9 — Inventario de información y activos asociados
- **Objetivo:** conocer y clasificar todos los activos a proteger.
- **Cómo verificar:** revisar que exista un inventario actualizado con clasificación (Público/Interno/Confidencial/Restringido).
- **Evidencia esperada:** documento/tabla de activos con responsable y clasificación.
- **Remediación:** crear inventario de servidores, BD, APIs, repos y llaves; asignar dueño y nivel.
- **Prioridad:** Crítica
- **Evidencia adjunta:** (rellenar)

### [CTRL-27001-RSK-02] Matriz de riesgos (Impacto × Probabilidad)
- **Estado:** 🔍 POR_VERIFICAR
- **Anexo A:** A.5.7 / Cláusula 6.1.2 — Evaluación de riesgos
- **Objetivo:** priorizar controles según el riesgo calculado.
- **Cómo verificar:** confirmar que cada activo tiene Impacto (1–5), Probabilidad (1–5) y Riesgo = I×P.
- **Evidencia esperada:** matriz con puntajes y mapa de calor.
- **Remediación:** calcular el riesgo de cada activo y definir tratamiento (mitigar/transferir/aceptar/evitar).
- **Prioridad:** Crítica
- **Evidencia adjunta:** (rellenar)

### [CTRL-27001-RSK-03] Plan de tratamiento de riesgos
- **Estado:** 🔍 POR_VERIFICAR
- **Anexo A:** Cláusula 6.1.3 — Tratamiento de riesgos
- **Objetivo:** asignar acciones concretas a cada riesgo relevante.
- **Cómo verificar:** revisar que los riesgos altos tienen acción, responsable y fecha.
- **Evidencia esperada:** plan de tratamiento con estado por riesgo.
- **Remediación:** documentar decisión y control aplicado por cada riesgo.
- **Prioridad:** Alta
- **Evidencia adjunta:** (rellenar)

---

## Dominio: Declaración de Aplicabilidad (SoA)

### [CTRL-27001-SOA-01] SoA con los 93 controles justificados
- **Estado:** 🔍 POR_VERIFICAR
- **Anexo A:** Cláusula 6.1.3 d) — Statement of Applicability
- **Objetivo:** declarar qué controles aplican y justificar exclusiones.
- **Cómo verificar:** confirmar que cada control del Anexo A tiene "Aplica Sí/No" + justificación.
- **Evidencia esperada:** documento SoA completo y aprobado.
- **Remediación:** completar la SoA enlazando cada control a un riesgo o exclusión justificada.
- **Prioridad:** Crítica
- **Evidencia adjunta:** (rellenar)

---

## Dominio: Métricas y KPIs

### [CTRL-27001-KPI-01] KPIs de seguridad definidos
- **Estado:** 🔍 POR_VERIFICAR
- **Anexo A:** Cláusula 9.1 — Monitoreo, medición, análisis
- **Objetivo:** poder medir la efectividad de los controles.
- **Cómo verificar:** revisar que existen KPIs con objetivo y fuente de datos.
- **Evidencia esperada:** tablero/listado de KPIs (ej. respuesta a incidentes < 1h, % parchado ≥ 95%).
- **Remediación:** definir KPIs medibles y su origen de datos.
- **Prioridad:** Alta
- **Evidencia adjunta:** (rellenar)

### [CTRL-27001-KPI-02] KPIs medidos con registros reales
- **Estado:** 🔍 POR_VERIFICAR
- **Anexo A:** Cláusula 9.1 — Evaluación del desempeño
- **Objetivo:** demostrar que los KPIs se miden, no solo se definen.
- **Cómo verificar:** revisar registros históricos de las mediciones.
- **Evidencia esperada:** reportes periódicos con valores reales y tendencia.
- **Remediación:** instrumentar la recolección y registrar mediciones periódicas.
- **Prioridad:** Media
- **Evidencia adjunta:** (rellenar)

---

## Dominio: Auditorías y Revisión por la Dirección

### [CTRL-27001-AUD-01] Programa de auditoría interna
- **Estado:** 🔍 POR_VERIFICAR
- **Anexo A:** Cláusula 9.2 — Auditoría interna
- **Objetivo:** evaluar periódicamente el SGSI.
- **Cómo verificar:** revisar plan anual de auditoría y hallazgos.
- **Evidencia esperada:** informe de auditoría interna con no conformidades y plan de acción.
- **Remediación:** programar y ejecutar auditoría interna documentada.
- **Prioridad:** Alta
- **Evidencia adjunta:** (rellenar)

### [CTRL-27001-AUD-02] Revisión por la Dirección
- **Estado:** 🔍 POR_VERIFICAR
- **Anexo A:** Cláusula 9.3 — Revisión por la dirección
- **Objetivo:** que la dirección apruebe recursos y mejoras.
- **Cómo verificar:** revisar actas de reunión con decisiones y aprobación de presupuesto.
- **Evidencia esperada:** acta firmada de revisión por la dirección.
- **Remediación:** convocar y documentar la revisión con asignación de recursos.
- **Prioridad:** Media
- **Evidencia adjunta:** (rellenar)

---

## Contadores (rellenar al auditar)

| Estado | Cantidad |
|--------|----------|
| ✅ CUMPLE | 0 |
| ⚠️ PARCIAL | 0 |
| ❌ NO_CUMPLE | 0 |
| ➖ NO_APLICA | 0 |
| 🔍 POR_VERIFICAR | 8 |
| **Total items** | **8** |

**% Cumplimiento = CUMPLE / (Total − NO_APLICA) × 100 = ____%**
