# Checklist — ISO/IEC 27002 (Controles Técnicos)

> **Norma asociada:** [`../normas/02-iso-27002-controles-tecnicos.md`](../normas/02-iso-27002-controles-tecnicos.md)
> **Instrucciones de uso:** [`../00-INSTRUCCIONES-IA.md`](../00-INSTRUCCIONES-IA.md)
> **Estados:** `✅ CUMPLE` · `⚠️ PARCIAL` · `❌ NO_CUMPLE` · `➖ NO_APLICA` · `🔍 POR_VERIFICAR`

---

## Dominio: Control de Accesos (IAM)

### [CTRL-27002-IAM-01] MFA obligatoria en todas las cuentas
- **Estado:** 🔍 POR_VERIFICAR
- **Anexo A:** A.8.5 — Autenticación segura
- **Objetivo:** impedir accesos no autorizados aun con la contraseña comprometida.
- **Cómo verificar:** revisar la política del IdP/IAM y confirmar MFA forzada (cobertura 100%).
- **Evidencia esperada:** captura de la política + reporte de cobertura de MFA.
- **Remediación:** activar MFA obligatorio; bloquear login sin segundo factor.
- **Prioridad:** Crítica
- **Evidencia adjunta:** (rellenar)

### [CTRL-27002-IAM-02] Contraseñas con hashing seguro (Argon2/bcrypt + salt)
- **Estado:** 🔍 POR_VERIFICAR
- **Anexo A:** A.8.5 / A.8.24 — Autenticación / Criptografía
- **Objetivo:** que las contraseñas robadas no sean reversibles.
- **Cómo verificar:** revisar el código/config de almacenamiento de credenciales.
- **Evidencia esperada:** fragmento de configuración usando Argon2id o bcrypt con salt por usuario.
- **Remediación:** migrar de hashes débiles (MD5/SHA1) a Argon2/bcrypt.
- **Prioridad:** Crítica
- **Evidencia adjunta:** (rellenar)

### [CTRL-27002-IAM-03] Mínimo privilegio con RBAC
- **Estado:** 🔍 POR_VERIFICAR
- **Anexo A:** A.8.2 — Derechos de acceso privilegiado
- **Objetivo:** que cada identidad tenga solo los permisos que necesita.
- **Cómo verificar:** revisar roles y permisos; buscar cuentas con permisos excesivos.
- **Evidencia esperada:** matriz de roles RBAC + revisión de accesos.
- **Remediación:** definir roles por función y revocar permisos sobrantes.
- **Prioridad:** Alta
- **Evidencia adjunta:** (rellenar)

---

## Dominio: Cifrado (Criptografía)

### [CTRL-27002-CRY-01] TLS 1.3 para datos en tránsito
- **Estado:** 🔍 POR_VERIFICAR
- **Anexo A:** A.8.24 — Uso de criptografía
- **Objetivo:** proteger los datos en la red.
- **Cómo verificar:** escanear endpoints (ej. `testssl.sh`) y confirmar TLS 1.3 y descarte de SSL/TLS ≤1.1.
- **Evidencia esperada:** salida del escaneo SSL/TLS.
- **Remediación:** habilitar TLS 1.3 y deshabilitar protocolos obsoletos.
- **Prioridad:** Alta
- **Evidencia adjunta:** (rellenar)

### [CTRL-27002-CRY-02] AES-256 para datos en reposo
- **Estado:** 🔍 POR_VERIFICAR
- **Anexo A:** A.8.24 — Uso de criptografía
- **Objetivo:** que un disco/BD robado sea inútil sin la llave.
- **Cómo verificar:** confirmar cifrado en BD, volúmenes y backups.
- **Evidencia esperada:** configuración de cifrado en reposo activa.
- **Remediación:** activar cifrado AES-256 en almacenamiento y backups.
- **Prioridad:** Alta
- **Evidencia adjunta:** (rellenar)

### [CTRL-27002-CRY-03] Gestión y rotación de llaves (KMS)
- **Estado:** 🔍 POR_VERIFICAR
- **Anexo A:** A.8.24 — Gestión de llaves
- **Objetivo:** evitar llaves en código y permitir rotación.
- **Cómo verificar:** confirmar uso de KMS/HSM y política de rotación; buscar secretos en repos.
- **Evidencia esperada:** configuración de KMS + política de rotación + escaneo de secretos limpio.
- **Remediación:** mover llaves a KMS, activar rotación, purgar secretos del repo.
- **Prioridad:** Crítica
- **Evidencia adjunta:** (rellenar)

---

## Dominio: Gestión de Vulnerabilidades

### [CTRL-27002-VUL-01] SAST/DAST/SCA en el pipeline CI/CD
- **Estado:** 🔍 POR_VERIFICAR
- **Anexo A:** A.8.8 / A.8.28 — Vulnerabilidades técnicas / Codificación segura
- **Objetivo:** detectar fallos antes de producción.
- **Cómo verificar:** revisar la configuración del pipeline buscando etapas SAST, DAST y SCA.
- **Evidencia esperada:** definición del pipeline + reporte de un escaneo reciente.
- **Remediación:** añadir etapas de análisis que bloqueen ante vulnerabilidades críticas.
- **Prioridad:** Alta
- **Evidencia adjunta:** (rellenar)

### [CTRL-27002-VUL-02] Patch management con zero-day < 24h
- **Estado:** 🔍 POR_VERIFICAR
- **Anexo A:** A.8.8 — Gestión de vulnerabilidades técnicas
- **Objetivo:** cerrar fallos críticos a tiempo.
- **Cómo verificar:** revisar política de parches y registros de aplicación.
- **Evidencia esperada:** política documentada + historial de parches con fechas.
- **Remediación:** definir SLA de parcheo y ventanas de mantenimiento.
- **Prioridad:** Alta
- **Evidencia adjunta:** (rellenar)

---

## Dominio: Seguridad en Redes

### [CTRL-27002-NET-01] Segmentación (VPC) y WAF
- **Estado:** 🔍 POR_VERIFICAR
- **Anexo A:** A.8.20 / A.8.22 — Seguridad y segregación de redes
- **Objetivo:** limitar el alcance de un ataque.
- **Cómo verificar:** revisar diagrama de red, subredes y reglas de WAF.
- **Evidencia esperada:** configuración de VPC/subredes + reglas WAF activas.
- **Remediación:** segmentar en subredes privadas/públicas y desplegar WAF.
- **Prioridad:** Alta
- **Evidencia adjunta:** (rellenar)

### [CTRL-27002-NET-02] Sin SSH por contraseña ni FTP
- **Estado:** 🔍 POR_VERIFICAR
- **Anexo A:** A.8.20 / A.8.21 — Seguridad de redes y servicios
- **Objetivo:** eliminar protocolos/accesos inseguros.
- **Cómo verificar:** revisar `sshd_config` (PasswordAuthentication no) y confirmar uso de SFTP/FTPS.
- **Evidencia esperada:** configuración de SSH con solo llaves + ausencia de FTP.
- **Remediación:** deshabilitar password en SSH, migrar FTP a SFTP/FTPS.
- **Prioridad:** Media
- **Evidencia adjunta:** (rellenar)

---

## Dominio: Logging y Monitoreo

### [CTRL-27002-LOG-01] Logs centralizados (SIEM) con WORM
- **Estado:** 🔍 POR_VERIFICAR
- **Anexo A:** A.8.15 / A.8.16 — Registro y monitoreo
- **Objetivo:** detectar y reconstruir incidentes sin que los logs se alteren.
- **Cómo verificar:** confirmar centralización en SIEM y protección WORM/inmutable.
- **Evidencia esperada:** configuración del SIEM + retención inmutable.
- **Remediación:** centralizar logs y activar almacenamiento WORM.
- **Prioridad:** Alta
- **Evidencia adjunta:** (rellenar)

### [CTRL-27002-LOG-02] Registro de eventos críticos
- **Estado:** 🔍 POR_VERIFICAR
- **Anexo A:** A.8.15 — Registro de eventos
- **Objetivo:** capturar logins fallidos, cambios de privilegios y accesos a datos críticos.
- **Cómo verificar:** revisar que esos eventos se registran y alertan.
- **Evidencia esperada:** muestras de logs de esos tres tipos de evento.
- **Remediación:** habilitar auditoría de esos eventos y alertas asociadas.
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
| 🔍 POR_VERIFICAR | 13 |
| **Total items** | **13** |

**% Cumplimiento = CUMPLE / (Total − NO_APLICA) × 100 = ____%**
