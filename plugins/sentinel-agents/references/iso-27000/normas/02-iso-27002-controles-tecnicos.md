# ISO/IEC 27002 — Controles Técnicos Específicos

> **Checklist asociado:** [`../checklists/checklist-27002.md`](../checklists/checklist-27002.md)
> **Enfoque:** El "cómo" técnico. Baja al detalle de los bits y la configuración.

---

## 1. Qué es y por qué existe

Si la 27001 dice *"debes gestionar el riesgo"*, la **27002 es el catálogo de buenas prácticas de implementación**. No es certificable por sí sola: es la **guía de referencia** que te dice *cómo* configurar cada control que declaraste aplicable en tu SoA. En una auditoría, aquí te piden demostrar **configuraciones concretas**.

Los controles se agrupan en cinco dominios técnicos principales:

```
IAM ──► Cifrado ──► Vulnerabilidades ──► Redes ──► Logging
(quién  (proteger   (encontrar y         (aislar   (registrar
 entra)  el dato)    cerrar fallos)        tráfico)  y detectar)
```

---

## 2. Control de Accesos (IAM)

**Objetivo:** que solo las identidades correctas accedan a los recursos correctos, con el mínimo privilegio.

- **MFA obligatoria** (autenticación de doble factor) para todo acceso, en especial el administrativo.
- Políticas de contraseñas robustas: longitud mínima, rotación razonable, y **hashing con salt** usando `bcrypt`, `scrypt` o **`Argon2`**.
- **Principio de mínimo privilegio** mediante **RBAC** (*Role-Based Access Control*).
- Revisión periódica de accesos y **baja inmediata** de cuentas inactivas.

```text
✗ MAL:  password_hash = SHA1("clave123")            # sin salt, algoritmo roto
✓ BIEN: password_hash = Argon2id(salt, "clave123")  # lento por diseño, con salt único
```

**Anexo A relacionado:** A.8.2 (privilegios), A.8.3 (acceso a información), A.8.5 (autenticación segura).

---

## 3. Cifrado (Criptografía)

**Objetivo:** que un dato robado sea inútil sin la llave.

| Estado del dato | Estándar mínimo |
|-----------------|------------------|
| **En tránsito** | **TLS 1.3** (deshabilitar TLS ≤ 1.1 y SSL) |
| **En reposo** | **AES-256** (BD, volúmenes, backups) |
| **Llaves** | **KMS** con rotación automática; nunca en código ni repos |

Reglas:
- Las llaves se gestionan en un **KMS/HSM**, no en variables de entorno planas ni en el repositorio.
- **Rotación** periódica de llaves y certificados.
- Cifrado de **backups** además de los datos vivos.

**Anexo A relacionado:** A.8.24 (uso de criptografía).

---

## 4. Gestión de Vulnerabilidades

**Objetivo:** encontrar y cerrar fallos antes de que los exploten.

- Escaneos automatizados en el pipeline **CI/CD**:
  - **SAST** (*Static Application Security Testing*): analiza el **código fuente**.
  - **DAST** (*Dynamic Application Security Testing*): analiza la **app en ejecución**.
  - **SCA** (*Software Composition Analysis*): analiza **dependencias** de terceros.
- Política estricta de **patch management** con ventanas de mantenimiento.
- **Zero-days críticos parchados en < 24 horas**.

```
Commit ──► SAST ──► Build ──► DAST ──► SCA ──► Deploy
            │                  │        │
            └── bloquea si encuentra vulnerabilidad crítica ──┘
```

**Anexo A relacionado:** A.8.8 (gestión de vulnerabilidades técnicas), A.8.28 (codificación segura).

---

## 5. Seguridad en Redes

**Objetivo:** segmentar y filtrar el tráfico para limitar el alcance de un ataque.

- Segmentación mediante **VPCs** y subredes privadas/públicas.
- **WAF** (*Web Application Firewall*) frente a las aplicaciones web.
- **ACLs** (listas de control de acceso) y *security groups* restrictivos.
- Deshabilitar lo inseguro: **nada de SSH por contraseña** (solo llaves), **nada de FTP** (usar SFTP/FTPS).
- Cerrar puertos no usados; principio de *deny by default*.

**Anexo A relacionado:** A.8.20 (seguridad de redes), A.8.21 (seguridad de servicios de red), A.8.22 (segregación de redes).

---

## 6. Registros y Monitoreo (Logging)

**Objetivo:** poder detectar y reconstruir lo que pasó.

- Centralización de logs (**Syslog**, herramientas **SIEM**).
- Protección contra alteración: **WORM** (*Write Once, Read Many*).
- Registrar como mínimo:
  - **Logins fallidos**
  - **Cambios de privilegios**
  - **Accesos a datos críticos**
- Definir **retención** de logs y alertas sobre eventos sospechosos.

**Anexo A relacionado:** A.8.15 (registro de eventos), A.8.16 (monitoreo de actividades).

---

## 7. Resumen de configuraciones mínimas

| Dominio | Requisito mínimo verificable |
|---------|------------------------------|
| IAM | MFA 100% + RBAC + Argon2/bcrypt |
| Cifrado | TLS 1.3 + AES-256 + KMS con rotación |
| Vulnerabilidades | SAST+DAST+SCA en CI/CD + zero-day < 24h |
| Redes | VPC + WAF + sin SSH-password/FTP |
| Logging | SIEM + WORM + logins/privilegios/accesos |

➡️ **Verifica tu cumplimiento en** [`checklist-27002.md`](../checklists/checklist-27002.md).
