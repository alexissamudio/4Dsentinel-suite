# ISO/IEC 27000 — SGSI: Guía Técnica y Checklists de Cumplimiento

Carpeta de trabajo para **implementar y auditar** un **Sistema de Gestión de Seguridad de la Información (SGSI)** basado en la familia ISO/IEC 27000. Está diseñada para que **una persona o una IA** pueda leerla, interpretarla y ejecutar las instrucciones de forma autónoma, dejando evidencia rastreable en cada paso.

---

## 1. Estructura de la carpeta

```
ISO-27000-SGSI/
├── README.md                       ← estás aquí (índice maestro y manual de uso)
├── 00-INSTRUCCIONES-IA.md          ← protocolo formal para que una IA opere esta carpeta
│
├── normas/                         ← explicación técnica detallada de cada norma
│   ├── 01-iso-27001-sgsi.md            (gestión / gobierno del SGSI)
│   ├── 02-iso-27002-controles-tecnicos.md  (controles técnicos: IAM, cripto, redes…)
│   ├── 03-iso-27017-nube.md            (seguridad en la nube)
│   ├── 04-iso-27018-pii-nube.md        (datos personales / PII en la nube)
│   └── 05-iso-27032-ciberseguridad.md  (ciberseguridad y respuesta a incidentes)
│
└── checklists/                     ← listas de verificación rastreables
    ├── checklist-27001.md              (cada item: ID · control · cómo verificar · evidencia · estado)
    ├── checklist-27002.md
    ├── checklist-27017.md
    ├── checklist-27018.md
    └── checklist-27032.md
```

Cada **norma** tiene su par en **checklist**: el archivo de norma explica *qué es y por qué*; el checklist convierte esa teoría en *items accionables y verificables*.

---

## 2. Mapa de normas y cómo se relacionan

| Norma | Enfoque | Pregunta que responde | Archivo | Checklist |
|-------|---------|------------------------|---------|-----------|
| **ISO/IEC 27001** | Gestión / Gobierno | ¿Tienes un sistema de gestión formal y auditable? | [normas/01](normas/01-iso-27001-sgsi.md) | [27001](checklists/checklist-27001.md) |
| **ISO/IEC 27002** | Controles técnicos | ¿Cómo configuras la seguridad a nivel de bits? | [normas/02](normas/02-iso-27002-controles-tecnicos.md) | [27002](checklists/checklist-27002.md) |
| **ISO/IEC 27017** | Nube | ¿Cómo aseguras infraestructura virtual e híbrida? | [normas/03](normas/03-iso-27017-nube.md) | [27017](checklists/checklist-27017.md) |
| **ISO/IEC 27018** | Privacidad / PII | ¿Cómo proteges los datos personales en la nube? | [normas/04](normas/04-iso-27018-pii-nube.md) | [27018](checklists/checklist-27018.md) |
| **ISO/IEC 27032** | Ciberseguridad operativa | ¿Cómo resistes y respondes a ataques? | [normas/05](normas/05-iso-27032-ciberseguridad.md) | [27032](checklists/checklist-27032.md) |

```
                    ┌─────────────────────────────────────┐
                    │   ISO 27001  (EL SGSI / GOBIERNO)    │
                    │   Riesgos · SoA · KPIs · Auditorías  │
                    └──────────────────┬──────────────────┘
                                       │ se implementa con...
                    ┌──────────────────┴──────────────────┐
                    │   ISO 27002  (CONTROLES TÉCNICOS)    │
                    │   IAM · Cifrado · Redes · Logging    │
                    └──────────────────┬──────────────────┘
                                       │ extendido para contextos...
        ┌──────────────────────────────┼──────────────────────────────┐
        ▼                              ▼                              ▼
 ┌────────────┐               ┌────────────┐               ┌────────────┐
 │ ISO 27017  │               │ ISO 27018  │               │ ISO 27032  │
 │   NUBE     │               │  PII/Nube  │               │ CIBERSEG.  │
 └────────────┘               └────────────┘               └────────────┘
```

---

## 3. Flujo de trabajo recomendado

```
   [1] ENTENDER          [2] AUDITAR           [3] REMEDIAR          [4] REPORTAR
   ───────────          ───────────           ────────────          ───────────
   Lee normas/*    →    Recorre cada      →   Para cada ❌/⚠️    →   Calcula % de
                        checklist y           ejecuta la acción     cumplimiento con
                        marca el estado       y adjunta evidencia   los contadores
                        real de cada item                           de cada checklist
```

1. **Entender** → lee los archivos en `normas/`.
2. **Auditar** → recorre cada `checklists/checklist-*.md` y marca el **estado real** de cada control (no el deseado).
3. **Remediar** → para cada item en `❌ NO_CUMPLE` o `⚠️ PARCIAL`, ejecuta la **acción de remediación** y registra la **evidencia**.
4. **Reportar** → usa el bloque de contadores al final de cada checklist para calcular el % de cumplimiento global.

> 🤖 **Si eres una IA**, lee primero **[`00-INSTRUCCIONES-IA.md`](00-INSTRUCCIONES-IA.md)** — define el formato exacto, cómo marcar estados, qué evidencia adjuntar y qué nunca debes hacer.

---

## 4. Leyenda de estados (común a todos los checklists)

| Símbolo | Estado | Significado | ¿Cuenta como cumplido? |
|---------|--------|-------------|------------------------|
| `✅` | `CUMPLE` | Implementado **y** con evidencia verificable | Sí |
| `⚠️` | `PARCIAL` | Implementado a medias o sin evidencia completa | No |
| `❌` | `NO_CUMPLE` | No implementado | No |
| `➖` | `NO_APLICA` | Fuera del alcance — **requiere justificación** en la SoA | Excluido del cálculo |
| `🔍` | `POR_VERIFICAR` | Pendiente de revisión/auditoría | No (aún) |

---

## 5. Formato estándar de un item de checklist

Todos los items siguen esta misma plantilla para que sean **legibles por máquina**:

```markdown
### [ID] Título corto del control
- **Estado:** 🔍 POR_VERIFICAR
- **Anexo A (27001):** A.x.y — Nombre del control
- **Objetivo:** qué se busca lograr y por qué.
- **Cómo verificar:** comando, configuración o documento concreto a revisar.
- **Evidencia esperada:** captura, log, archivo o salida que prueba el cumplimiento.
- **Remediación:** acción a ejecutar si el estado es ❌ o ⚠️.
- **Prioridad:** Crítica | Alta | Media | Baja
- **Evidencia adjunta:** (ruta/enlace/descripción — rellenar al auditar)
```

---

## 6. Glosario rápido

| Sigla | Significado |
|-------|-------------|
| **SGSI** | Sistema de Gestión de Seguridad de la Información |
| **SoA** | *Statement of Applicability* (Declaración de Aplicabilidad) |
| **IAM** | *Identity & Access Management* (gestión de identidad y accesos) |
| **MFA** | *Multi-Factor Authentication* (autenticación multifactor) |
| **RBAC** | *Role-Based Access Control* (control de acceso por roles) |
| **KMS** | *Key Management System* (gestión de llaves criptográficas) |
| **SAST/DAST** | Análisis de seguridad estático / dinámico de aplicaciones |
| **SIEM** | *Security Information and Event Management* |
| **EDR/XDR** | *Endpoint/Extended Detection and Response* |
| **DLP** | *Data Loss Prevention* (prevención de fuga de datos) |
| **PII** | *Personally Identifiable Information* (datos personales) |
| **WAF** | *Web Application Firewall* |
| **PDCA** | Ciclo *Plan-Do-Check-Act* (mejora continua) |
