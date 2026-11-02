# Índice de la KB ISO 27000 — lookup CTRL-id → archivo

Para ubicar un control por su id, mirá este índice **primero**: abrí solo el checklist
que lo contiene (`grep 'CTRL-…' checklists/<archivo>`) en vez de leer
`00-INSTRUCCIONES-IA.md` + `README.md` enteros para orientarte. El CTRL-id es el
heading del control dentro de su archivo, así que es grep-able directo.

Formato del id: `CTRL-<norma>-<dominio>-<n>`. 39 controles, 5 checklists.

## ISO/IEC 27001 — SGSI / Gobierno → `checklists/checklist-27001.md`

| CTRL-id | Control |
|---|---|
| CTRL-27001-RSK-01 | Inventario de activos de información |
| CTRL-27001-RSK-02 | Matriz de riesgos (Impacto × Probabilidad) |
| CTRL-27001-RSK-03 | Plan de tratamiento de riesgos |
| CTRL-27001-SOA-01 | SoA con los 93 controles justificados |
| CTRL-27001-KPI-01 | KPIs de seguridad definidos |
| CTRL-27001-KPI-02 | KPIs medidos con registros reales |
| CTRL-27001-AUD-01 | Programa de auditoría interna |
| CTRL-27001-AUD-02 | Revisión por la Dirección |

## ISO/IEC 27002 — Controles técnicos → `checklists/checklist-27002.md`

| CTRL-id | Control |
|---|---|
| CTRL-27002-IAM-01 | MFA obligatoria en todas las cuentas |
| CTRL-27002-IAM-02 | Contraseñas con hashing seguro (Argon2/bcrypt + salt) |
| CTRL-27002-IAM-03 | Mínimo privilegio con RBAC |
| CTRL-27002-CRY-01 | TLS 1.3 para datos en tránsito |
| CTRL-27002-CRY-02 | AES-256 para datos en reposo |
| CTRL-27002-CRY-03 | Gestión y rotación de llaves (KMS) |
| CTRL-27002-VUL-01 | SAST/DAST/SCA en el pipeline CI/CD |
| CTRL-27002-VUL-02 | Patch management con zero-day < 24h |
| CTRL-27002-NET-01 | Segmentación (VPC) y WAF |
| CTRL-27002-NET-02 | Sin SSH por contraseña ni FTP |
| CTRL-27002-LOG-01 | Logs centralizados (SIEM) con WORM |
| CTRL-27002-LOG-02 | Registro de eventos críticos |

## ISO/IEC 27017 — Seguridad en la nube → `checklists/checklist-27017.md`

| CTRL-id | Control |
|---|---|
| CTRL-27017-ISO-01 | Aislamiento lógico entre clientes/entornos |
| CTRL-27017-IMG-01 | Escaneo de imágenes Docker antes de desplegar |
| CTRL-27017-IMG-02 | Golden Images revisadas y contenedores no-root |
| CTRL-27017-ADM-01 | Acceso a consola restringido por IP + MFA |
| CTRL-27017-ADM-02 | Cuenta root bloqueada / sin uso operativo |
| CTRL-27017-ADM-03 | Auditoría de infraestructura activa (CloudTrail/equivalente) |
| CTRL-27017-NTP-01 | NTP activo en todas las instancias |

## ISO/IEC 27018 — Protección de PII en la nube → `checklists/checklist-27018.md`

| CTRL-id | Control |
|---|---|
| CTRL-27018-MSK-01 | Enmascaramiento de PII en dev/staging |
| CTRL-27018-RES-01 | Restricción de región geográfica de los datos |
| CTRL-27018-DLP-01 | DLP con alerta automática de fugas |
| CTRL-27018-DLP-02 | Procedimiento de notificación de brechas (plazo legal) |
| CTRL-27018-DEL-01 | Wipe seguro de datos al dar de baja |

## ISO/IEC 27032 — Ciberseguridad → `checklists/checklist-27032.md`

| CTRL-id | Control |
|---|---|
| CTRL-27032-DDS-01 | Mitigación DDoS activa |
| CTRL-27032-DDS-02 | Rate-limiting en APIs |
| CTRL-27032-EDR-01 | Agente EDR/XDR heurístico en endpoints y servidores |
| CTRL-27032-IRP-01 | Playbooks de respuesta a incidentes |
| CTRL-27032-IRP-02 | Aislamiento automatizado de hosts comprometidos |
| CTRL-27032-MAIL-01 | Registro SPF configurado |
| CTRL-27032-MAIL-02 | Firma DKIM activa |
| CTRL-27032-MAIL-03 | Política DMARC (reject/quarantine) |
