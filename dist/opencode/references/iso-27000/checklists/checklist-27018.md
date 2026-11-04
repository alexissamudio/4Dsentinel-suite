# Checklist — ISO/IEC 27018 (Datos Personales / PII en la Nube)

> **Norma asociada:** [`../normas/04-iso-27018-pii-nube.md`](../normas/04-iso-27018-pii-nube.md)
> **Instrucciones de uso:** [`../00-INSTRUCCIONES-IA.md`](../00-INSTRUCCIONES-IA.md)
> **Estados:** `✅ CUMPLE` · `⚠️ PARCIAL` · `❌ NO_CUMPLE` · `➖ NO_APLICA` · `🔍 POR_VERIFICAR`

---

## Dominio: Anonimización / Enmascaramiento

### [CTRL-27018-MSK-01] Enmascaramiento de PII en dev/staging
- **Estado:** 🔍 POR_VERIFICAR
- **Anexo A:** A.8.11 — Enmascaramiento de datos
- **Objetivo:** que los desarrolladores no vean datos reales (DNI, tarjetas, nombres).
- **Cómo verificar:** inspeccionar una BD de staging y confirmar que la PII está enmascarada/seudonimizada.
- **Evidencia esperada:** muestra de registros enmascarados + proceso de masking documentado.
- **Remediación:** aplicar masking/seudonimización al clonar datos a entornos no productivos.
- **Prioridad:** Alta
- **Evidencia adjunta:** (rellenar)

---

## Dominio: Residencia de Datos (Data Residency)

### [CTRL-27018-RES-01] Restricción de región geográfica de los datos
- **Estado:** 🔍 POR_VERIFICAR
- **Anexo A:** A.5.34 — Privacidad y protección de PII
- **Objetivo:** que la PII no salga de la región legalmente permitida.
- **Cómo verificar:** revisar políticas del CSP que restringen regiones (SCP/Azure Policy) incl. backups.
- **Evidencia esperada:** política de regiones permitidas + verificación de ubicación de backups.
- **Remediación:** aplicar políticas que limiten almacenamiento y réplicas a la región autorizada.
- **Prioridad:** Alta
- **Evidencia adjunta:** (rellenar)

---

## Dominio: Notificación de Brechas

### [CTRL-27018-DLP-01] DLP con alerta automática de fugas
- **Estado:** 🔍 POR_VERIFICAR
- **Anexo A:** A.8.12 — Prevención de fuga de datos
- **Objetivo:** detectar fugas de PII y alertar a los responsables.
- **Cómo verificar:** confirmar que existe DLP inspeccionando salidas (correo, subidas, exportaciones).
- **Evidencia esperada:** configuración de reglas DLP + destino de alertas (DPO/seguridad).
- **Remediación:** desplegar DLP con reglas sobre PII y alertas inmediatas.
- **Prioridad:** Alta
- **Evidencia adjunta:** (rellenar)

### [CTRL-27018-DLP-02] Procedimiento de notificación de brechas (plazo legal)
- **Estado:** 🔍 POR_VERIFICAR
- **Anexo A:** A.5.26 — Respuesta a incidentes de seguridad
- **Objetivo:** cumplir plazos legales (ej. 72h GDPR).
- **Cómo verificar:** revisar el procedimiento documentado con plazos y responsables.
- **Evidencia esperada:** procedimiento de notificación con SLA y contactos.
- **Remediación:** documentar el flujo de notificación a la autoridad y afectados.
- **Prioridad:** Media
- **Evidencia adjunta:** (rellenar)

---

## Dominio: Destrucción Segura

### [CTRL-27018-DEL-01] Wipe seguro de datos al dar de baja
- **Estado:** 🔍 POR_VERIFICAR
- **Anexo A:** A.8.10 — Eliminación de información
- **Objetivo:** que un dato dado de baja sea irrecuperable (incl. backups).
- **Cómo verificar:** revisar el procedimiento de borrado (sobreescritura o borrado criptográfico) y su alcance.
- **Evidencia esperada:** procedimiento + certificado/registro de destrucción.
- **Remediación:** implementar borrado criptográfico o wipe de bloques, incluyendo snapshots/backups.
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
| 🔍 POR_VERIFICAR | 5 |
| **Total items** | **5** |

**% Cumplimiento = CUMPLE / (Total − NO_APLICA) × 100 = ____%**
