# ISO/IEC 27032 — Ciberseguridad y Respuesta Operativa

> **Checklist asociado:** [`../checklists/checklist-27032.md`](../checklists/checklist-27032.md)
> **Enfoque:** Preparación técnica para resistir y responder a ataques a nivel de red y endpoint.

---

## 1. Qué es y por qué existe

Es la norma más **operativa y de defensa activa**. Mientras la 27002 configura controles estáticos, la **27032 se enfoca en el combate**: mitigar ataques en curso, detectar malware en tiempo real, contener intrusiones y proteger el canal de correo contra phishing.

```
   PREVENIR ──► DETECTAR ──► CONTENER ──► RESPONDER
   (anti-DDoS)  (EDR/XDR)    (aislar)     (playbooks IRP)
```

---

## 2. Arquitectura de Red Anti-DDoS

**Objetivo:** mantener el servicio disponible bajo ataque de denegación.

- Sistemas de mitigación de **DDoS** distribuida (**Cloudflare**, **AWS Shield**, Azure DDoS Protection).
- **Rate-limiting** en las APIs para evitar el abuso de *endpoints*.
- *Throttling* y *circuit breakers* para degradar de forma controlada.

```text
Tráfico ──► CDN/Anti-DDoS ──► Rate-limit (ej. 100 req/min/IP) ──► API
              │                      │
              └─ absorbe volumen     └─ bloquea abuso por endpoint
```

---

## 3. Protección de Endpoints (EDR/XDR)

**Objetivo:** detectar y frenar malware en servidores y terminales.

Agentes con **análisis heurístico** (no solo firmas) para detectar ejecuciones de malware o *payloads* maliciosos **en tiempo real**.

| Tecnología | Cómo detecta | Atrapa amenazas nuevas |
|-----------|--------------|------------------------|
| Antivirus clásico | Por **firmas** conocidas | No |
| **EDR/XDR** | Por **comportamiento** (heurística + ML) | Sí |

- Agentes desplegados en todos los servidores y endpoints.
- Telemetría centralizada y capacidad de respuesta remota (aislar/terminar proceso).

---

## 4. Plan de Respuesta a Incidentes (IRP) Técnico

**Objetivo:** contener una intrusión confirmada antes de que se propague.

**Scripts de automatización y playbooks** para **aislar máquinas comprometidas** de la red (aislamiento lógico) en caso de intrusión confirmada.

Fases típicas de un IRP:
```
1. Detección   ──► 2. Contención ──► 3. Erradicación ──► 4. Recuperación ──► 5. Lecciones
   (alerta SIEM)     (aislar host)     (limpiar malware)    (restaurar)        (post-mortem)
```

- Playbooks por tipo de incidente (ransomware, fuga, intrusión).
- Automatización: aislar host de la red con un solo comando/acción.
- Roles y contactos definidos (quién decide, quién ejecuta, quién comunica).

---

## 5. Políticas de Seguridad en Correo (Anti-Phishing)

**Objetivo:** impedir la suplantación de tu dominio y el phishing.

Configuración **obligatoria** de tres registros DNS que trabajan juntos:

| Registro | Función | Ejemplo |
|----------|---------|---------|
| **SPF** | Define qué servidores están **autorizados a enviar** correo de tu dominio | `v=spf1 include:_spf.google.com -all` |
| **DKIM** | **Firma criptográfica** del correo (integridad + origen) | Selector + clave pública en DNS |
| **DMARC** | **Política de acción** ante correos falsos + reportes | `v=DMARC1; p=reject; rua=mailto:...` |

```
Correo entrante ──► ¿Pasa SPF? ──► ¿Pasa DKIM? ──► DMARC decide:
                                                     p=none      → solo monitorear
                                                     p=quarantine→ a spam
                                                     p=reject    → rechazar
```

Los tres juntos mitigan el phishing y la suplantación (*spoofing*) de tu dominio.

---

## 6. Resumen de controles clave

| Control | Requisito verificable |
|---------|------------------------|
| Anti-DDoS | Mitigación activa + rate-limiting en APIs |
| EDR/XDR | Agente heurístico en todos los endpoints |
| IRP | Playbooks + aislamiento automatizado de hosts |
| Correo | SPF + DKIM + DMARC (p=reject/quarantine) |

➡️ **Verifica tu cumplimiento en** [`checklist-27032.md`](../checklists/checklist-27032.md).
