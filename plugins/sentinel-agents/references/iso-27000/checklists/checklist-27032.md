# Checklist — ISO/IEC 27032 (Ciberseguridad y Respuesta Operativa)

> **Norma asociada:** [`../normas/05-iso-27032-ciberseguridad.md`](../normas/05-iso-27032-ciberseguridad.md)
> **Instrucciones de uso:** [`../00-INSTRUCCIONES-IA.md`](../00-INSTRUCCIONES-IA.md)
> **Estados:** `✅ CUMPLE` · `⚠️ PARCIAL` · `❌ NO_CUMPLE` · `➖ NO_APLICA` · `🔍 POR_VERIFICAR`

---

## Dominio: Anti-DDoS y Rate-Limiting

### [CTRL-27032-DDS-01] Mitigación DDoS activa
- **Estado:** 🔍 POR_VERIFICAR
- **Anexo A:** A.8.20 — Seguridad de redes
- **Objetivo:** mantener disponibilidad bajo ataque de denegación.
- **Cómo verificar:** confirmar protección DDoS (Cloudflare/AWS Shield/Azure DDoS) frente a los servicios públicos.
- **Evidencia esperada:** configuración del servicio anti-DDoS activo.
- **Remediación:** poner los servicios detrás de un mitigador DDoS.
- **Prioridad:** Alta
- **Evidencia adjunta:** (rellenar)

### [CTRL-27032-DDS-02] Rate-limiting en APIs
- **Estado:** 🔍 POR_VERIFICAR
- **Anexo A:** A.8.20 / A.8.23 — Seguridad de redes / filtrado web
- **Objetivo:** evitar el abuso de endpoints.
- **Cómo verificar:** revisar configuración de límites por IP/usuario en el API gateway.
- **Evidencia esperada:** reglas de rate-limit (ej. 100 req/min/IP).
- **Remediación:** configurar throttling y límites por endpoint.
- **Prioridad:** Media
- **Evidencia adjunta:** (rellenar)

---

## Dominio: Protección de Endpoints (EDR/XDR)

### [CTRL-27032-EDR-01] Agente EDR/XDR heurístico en endpoints y servidores
- **Estado:** 🔍 POR_VERIFICAR
- **Anexo A:** A.8.7 — Protección contra malware
- **Objetivo:** detectar malware por comportamiento, no solo por firmas.
- **Cómo verificar:** confirmar despliegue del agente y cobertura sobre todos los hosts.
- **Evidencia esperada:** consola EDR con inventario de hosts protegidos + cobertura %.
- **Remediación:** desplegar EDR/XDR en todos los endpoints y servidores.
- **Prioridad:** Alta
- **Evidencia adjunta:** (rellenar)

---

## Dominio: Respuesta a Incidentes (IRP)

### [CTRL-27032-IRP-01] Playbooks de respuesta a incidentes
- **Estado:** 🔍 POR_VERIFICAR
- **Anexo A:** A.5.26 — Respuesta a incidentes de seguridad
- **Objetivo:** responder de forma ordenada y rápida.
- **Cómo verificar:** revisar playbooks por tipo de incidente (ransomware, fuga, intrusión).
- **Evidencia esperada:** documentos de playbook con fases y responsables.
- **Remediación:** redactar playbooks con detección, contención, erradicación, recuperación y lecciones.
- **Prioridad:** Alta
- **Evidencia adjunta:** (rellenar)

### [CTRL-27032-IRP-02] Aislamiento automatizado de hosts comprometidos
- **Estado:** 🔍 POR_VERIFICAR
- **Anexo A:** A.5.26 / A.8.16 — Respuesta a incidentes / Monitoreo
- **Objetivo:** contener una intrusión antes de que se propague.
- **Cómo verificar:** confirmar que existe acción/script para aislar lógicamente un host de la red.
- **Evidencia esperada:** script/runbook de aislamiento + prueba documentada.
- **Remediación:** implementar capacidad de aislamiento de red con un solo paso.
- **Prioridad:** Crítica
- **Evidencia adjunta:** (rellenar)

---

## Dominio: Seguridad de Correo (Anti-Phishing)

### [CTRL-27032-MAIL-01] Registro SPF configurado
- **Estado:** 🔍 POR_VERIFICAR
- **Anexo A:** A.8.23 — Filtrado / seguridad de servicios
- **Objetivo:** declarar qué servidores pueden enviar correo del dominio.
- **Cómo verificar:** consultar el registro TXT SPF del dominio (`dig TXT dominio`).
- **Evidencia esperada:** registro SPF con `-all` o `~all`.
- **Remediación:** publicar registro SPF con los emisores autorizados.
- **Prioridad:** Media
- **Evidencia adjunta:** (rellenar)

### [CTRL-27032-MAIL-02] Firma DKIM activa
- **Estado:** 🔍 POR_VERIFICAR
- **Anexo A:** A.8.24 — Uso de criptografía
- **Objetivo:** firmar criptográficamente los correos salientes.
- **Cómo verificar:** verificar el selector DKIM en DNS y la firma en correos enviados.
- **Evidencia esperada:** registro DKIM publicado + cabecera de firma en un correo.
- **Remediación:** habilitar DKIM en el proveedor de correo y publicar la clave pública.
- **Prioridad:** Media
- **Evidencia adjunta:** (rellenar)

### [CTRL-27032-MAIL-03] Política DMARC (reject/quarantine)
- **Estado:** 🔍 POR_VERIFICAR
- **Anexo A:** A.8.23 — Filtrado / seguridad de servicios
- **Objetivo:** decidir qué hacer con correos que falsean el dominio.
- **Cómo verificar:** consultar el registro DMARC y confirmar `p=quarantine` o `p=reject` + reportes (rua).
- **Evidencia esperada:** registro DMARC con política de acción y dirección de reportes.
- **Remediación:** publicar DMARC empezando por `p=none` (monitoreo) y endurecer a reject.
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
