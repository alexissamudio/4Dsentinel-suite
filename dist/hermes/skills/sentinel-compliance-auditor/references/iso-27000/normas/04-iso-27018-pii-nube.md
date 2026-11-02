# ISO/IEC 27018 — Datos Personales (PII) en la Nube

> **Checklist asociado:** [`../checklists/checklist-27018.md`](../checklists/checklist-27018.md)
> **Enfoque:** Ingeniería de privacidad de datos personales (PII) almacenados o procesados en la nube.

---

## 1. Qué es y por qué existe

La 27018 se centra en la **protección de datos personales** (*Personally Identifiable Information*: nombres, DNI, tarjetas, direcciones, datos de salud). Conecta directamente con leyes de privacidad como el **GDPR** o las leyes nacionales de protección de datos. Su foco es: *minimizar, enmascarar, localizar y poder borrar* los datos personales.

```
   PRINCIPIOS PII:  Minimizar ──► Enmascarar ──► Localizar ──► Notificar ──► Destruir
```

---

## 2. Anonimización y Seudonimización

**Objetivo:** que los datos reales no se expongan fuera de producción.

Técnicas de **enmascaramiento de datos** en entornos de desarrollo y pruebas: los desarrolladores **no deben ver DNI, tarjetas ni nombres reales** en las bases de datos de *staging*.

```text
Producción:  Juan Pérez | DNI 12345678 | 4111-1111-1111-1111
Staging:     Usuario_A  | DNI ********  | 4111-****-****-1111
```

| Técnica | Qué hace | ¿Reversible? |
|---------|----------|--------------|
| **Anonimización** | Elimina la identidad de forma irreversible | No |
| **Seudonimización** | Reemplaza identificadores por tokens | Sí, con la llave |
| **Enmascaramiento** | Oculta parte del dato (`****`) | Depende |

---

## 3. Geolocalización de Datos (*Data Residency*)

**Objetivo:** cumplir leyes locales sobre dónde pueden residir los datos.

Configuración técnica para garantizar que los datos personales **no salgan de una región geográfica** específica (ej. restringir las regiones de almacenamiento de AWS a la **UE** o a tu país). Esto cumple requisitos de **soberanía de datos**.

- Restringir regiones permitidas a nivel de política de la nube (*SCP* en AWS, *Azure Policy*).
- Verificar que **backups y réplicas** también respeten la región.
- Documentar la ubicación física de cada categoría de datos.

---

## 4. Notificación Automatizada de Brechas

**Objetivo:** detectar fugas y notificar dentro del plazo legal.

Sistemas de **DLP** (*Data Loss Prevention*) configurados para detectar fugas de datos y **alertar inmediatamente** a los responsables, para cumplir los **plazos legales de notificación**.

> ⚖️ Bajo **GDPR**, las brechas de datos personales deben notificarse a la autoridad en **72 horas**.

- DLP que inspecciona tráfico de salida y almacenamiento (correos, subidas, exportaciones).
- Alertas automáticas al **DPO** (*Data Protection Officer*) / equipo de seguridad.
- Procedimiento de notificación documentado con plazos.

---

## 5. Destrucción Segura de Datos

**Objetivo:** que un dato dado de baja sea irrecuperable.

Protocolos de **sobreescritura (wipe técnico)** cuando un cliente solicita la baja de sus servicios, asegurando que los **bloques de disco virtual queden en cero** (no basta con "marcar como borrado").

- Borrado criptográfico (destruir la llave que cifra el dato) o sobreescritura de bloques.
- Aplicar también a **backups y snapshots**.
- Dejar **registro/certificado de destrucción** con fecha.

---

## 6. Resumen de controles clave

| Control | Requisito verificable |
|---------|------------------------|
| Enmascaramiento | PII oculta en dev/staging |
| Data residency | Región geográfica restringida y verificada |
| Notificación de brechas | DLP + alerta + plazo (72h GDPR) |
| Destrucción segura | Wipe de bloques + backups + certificado |

➡️ **Verifica tu cumplimiento en** [`checklist-27018.md`](../checklists/checklist-27018.md).
