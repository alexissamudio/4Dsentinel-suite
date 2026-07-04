# Checklist — ISO/IEC 27017 (Seguridad en la Nube)

> **Norma asociada:** [`../normas/03-iso-27017-nube.md`](../normas/03-iso-27017-nube.md)
> **Instrucciones de uso:** [`../00-INSTRUCCIONES-IA.md`](../00-INSTRUCCIONES-IA.md)
> **Estados:** `✅ CUMPLE` · `⚠️ PARCIAL` · `❌ NO_CUMPLE` · `➖ NO_APLICA` · `🔍 POR_VERIFICAR`

---

## Dominio: Aislamiento (Multitenancy)

### [CTRL-27017-ISO-01] Aislamiento lógico entre clientes/entornos
- **Estado:** 🔍 POR_VERIFICAR
- **Anexo A:** A.8.22 — Segregación de redes / aislamiento de tenants
- **Objetivo:** que los recursos de un cliente/entorno no se mezclen con otro.
- **Cómo verificar:** revisar namespaces, network policies y resource quotas (K8s) o aislamiento de VMs.
- **Evidencia esperada:** manifiestos de network policies + quotas + documentación de aislamiento.
- **Remediación:** segmentar por namespace/tenant con políticas de red y límites de recursos.
- **Prioridad:** Crítica
- **Evidencia adjunta:** (rellenar)

---

## Dominio: Hardening de Imágenes y Contenedores

### [CTRL-27017-IMG-01] Escaneo de imágenes Docker antes de desplegar
- **Estado:** 🔍 POR_VERIFICAR
- **Anexo A:** A.8.8 — Gestión de vulnerabilidades
- **Objetivo:** no desplegar imágenes con vulnerabilidades conocidas.
- **Cómo verificar:** revisar el pipeline buscando etapa de escaneo (Trivy/Grype/Clair) que bloquee críticas.
- **Evidencia esperada:** reporte de escaneo de imagen + política de bloqueo.
- **Remediación:** añadir escaneo obligatorio pre-deploy.
- **Prioridad:** Alta
- **Evidencia adjunta:** (rellenar)

### [CTRL-27017-IMG-02] Golden Images revisadas y contenedores no-root
- **Estado:** 🔍 POR_VERIFICAR
- **Anexo A:** A.8.9 — Gestión de configuración
- **Objetivo:** partir de plantillas seguras y mínimas.
- **Cómo verificar:** revisar Dockerfiles/AMIs (usuario no-root, imagen slim/distroless).
- **Evidencia esperada:** Dockerfile con `USER` no-root + base mínima.
- **Remediación:** versionar Golden Images y eliminar ejecución como root.
- **Prioridad:** Media
- **Evidencia adjunta:** (rellenar)

---

## Dominio: Consola de Administración

### [CTRL-27017-ADM-01] Acceso a consola restringido por IP + MFA
- **Estado:** 🔍 POR_VERIFICAR
- **Anexo A:** A.8.5 / A.8.20 — Autenticación / Seguridad de redes
- **Objetivo:** proteger el panel de control de la nube.
- **Cómo verificar:** revisar políticas de IP whitelisting y MFA en la consola del CSP.
- **Evidencia esperada:** política de restricción por IP + MFA activo.
- **Remediación:** restringir acceso a IPs conocidas y forzar MFA.
- **Prioridad:** Alta
- **Evidencia adjunta:** (rellenar)

### [CTRL-27017-ADM-02] Cuenta root bloqueada / sin uso operativo
- **Estado:** 🔍 POR_VERIFICAR
- **Anexo A:** A.8.2 — Acceso privilegiado
- **Objetivo:** evitar el uso de la cuenta raíz para operaciones diarias.
- **Cómo verificar:** revisar registros de uso de root y que tenga MFA + sin access keys.
- **Evidencia esperada:** reporte de no-uso de root + MFA activo en root.
- **Remediación:** bloquear root, eliminar sus claves, operar con roles de mínimo privilegio.
- **Prioridad:** Crítica
- **Evidencia adjunta:** (rellenar)

### [CTRL-27017-ADM-03] Auditoría de infraestructura activa (CloudTrail/equivalente)
- **Estado:** 🔍 POR_VERIFICAR
- **Anexo A:** A.8.15 — Registro de eventos
- **Objetivo:** registrar toda acción sobre la infraestructura.
- **Cómo verificar:** confirmar CloudTrail/Activity Log/Audit Logs activos en todas las regiones.
- **Evidencia esperada:** configuración del log de auditoría habilitado y protegido.
- **Remediación:** activar el log de auditoría del CSP de forma permanente.
- **Prioridad:** Alta
- **Evidencia adjunta:** (rellenar)

---

## Dominio: Sincronización de Relojes

### [CTRL-27017-NTP-01] NTP activo en todas las instancias
- **Estado:** 🔍 POR_VERIFICAR
- **Anexo A:** A.8.17 — Sincronización de relojes
- **Objetivo:** que los logs sean correlacionables en investigaciones forenses.
- **Cómo verificar:** revisar que las instancias sincronizan con NTP (ej. `timedatectl` / `chronyc`).
- **Evidencia esperada:** salida que muestre NTP sincronizado en muestras de instancias.
- **Remediación:** configurar NTP en la plantilla base de todas las instancias.
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
| 🔍 POR_VERIFICAR | 7 |
| **Total items** | **7** |

**% Cumplimiento = CUMPLE / (Total − NO_APLICA) × 100 = ____%**
