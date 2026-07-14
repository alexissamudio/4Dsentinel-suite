# 00 · INSTRUCCIONES PARA IA — Cómo operar esta carpeta

> Este archivo es el **contrato de operación**. Si eres un agente de IA (o un humano que sigue un proceso), léelo completo antes de tocar cualquier checklist. Define cómo interpretar la carpeta, cómo marcar estados, qué evidencia exigir y qué nunca debes hacer.

---

## 1. Propósito y modelo mental

Esta carpeta es un **SGSI documentado como código**. Cada control de seguridad está representado por un **item de checklist** con un **ID estable**. Tu trabajo como IA puede ser uno de estos modos:

| Modo | Objetivo | Resultado esperado |
|------|----------|--------------------|
| `AUDITAR` | Determinar el estado real de cada control | Checklists con estados actualizados + evidencia |
| `REMEDIAR` | Implementar/corregir controles en `❌`/`⚠️` | Cambios aplicados + evidencia + estado `✅` |
| `REPORTAR` | Resumir el nivel de cumplimiento | Informe con % por norma y brechas priorizadas |
| `EXTENDER` | Añadir nuevos controles o normas | Nuevos items con el formato estándar |

**Regla de oro:** *Sin evidencia verificable, un control NO está cumplido.* Nunca marques `✅` por suposición.

---

## 2. Anatomía de un item (formato que DEBES respetar)

Cada item de checklist tiene esta forma exacta. No cambies los nombres de los campos.

```markdown
### [CTRL-27002-IAM-01] MFA obligatoria en todas las cuentas
- **Estado:** 🔍 POR_VERIFICAR
- **Anexo A (27001):** A.8.5 — Autenticación segura
- **Objetivo:** impedir accesos no autorizados aun con la contraseña comprometida.
- **Cómo verificar:** revisar la consola de IdP/IAM y confirmar política MFA forzada.
- **Evidencia esperada:** captura de la política + reporte de cobertura ≥ 100% de cuentas.
- **Remediación:** activar MFA obligatorio a nivel de política; bloquear login sin 2FA.
- **Prioridad:** Crítica
- **Evidencia adjunta:** (rellenar)
```

### Significado de cada campo

| Campo | Quién lo rellena | Notas |
|-------|------------------|-------|
| `ID` | Fijo (no cambiar) | Formato `CTRL-<norma>-<dominio>-<n>` |
| `Estado` | Auditor/IA | Solo valores de la tabla de la §3 |
| `Anexo A` | Fijo | Referencia cruzada a ISO 27001 Anexo A |
| `Objetivo` | Fijo | El "por qué" del control |
| `Cómo verificar` | Fijo | El método de comprobación |
| `Evidencia esperada` | Fijo | Qué prueba el cumplimiento |
| `Remediación` | Fijo | Qué hacer si falla |
| `Prioridad` | Fijo | Crítica / Alta / Media / Baja |
| `Evidencia adjunta` | Auditor/IA | Ruta, enlace, hash, log o descripción concreta |

---

## 3. Cómo marcar el estado (máquina de estados)

```
                ┌──────────────────┐
                │  🔍 POR_VERIFICAR │  ← estado inicial de todo item
                └────────┬─────────┘
                         │  verificas con evidencia
        ┌────────────────┼────────────────┬─────────────────┐
        ▼                ▼                ▼                 ▼
   ┌─────────┐     ┌──────────┐     ┌───────────┐    ┌────────────┐
   │ ✅ CUMPLE│     │⚠️ PARCIAL│     │❌ NO_CUMPLE│    │ ➖ NO_APLICA │
   └─────────┘     └──────────┘     └───────────┘    └────────────┘
   evidencia       evidencia        sin              fuera del alcance
   completa        incompleta       implementación   (justifica en SoA)
```

| Estado | Cuándo usarlo | Requisito obligatorio |
|--------|---------------|------------------------|
| `✅ CUMPLE` | Control implementado y probado | **Debe** tener `Evidencia adjunta` |
| `⚠️ PARCIAL` | Existe pero incompleto o sin evidencia plena | Describir qué falta |
| `❌ NO_CUMPLE` | No implementado | Indicar remediación pendiente |
| `➖ NO_APLICA` | No corresponde al alcance | **Debe** incluir justificación |
| `🔍 POR_VERIFICAR` | Aún no auditado | Estado por defecto |

**Prohibido:** marcar `✅` sin rellenar `Evidencia adjunta`. Si no puedes obtener evidencia, usa `🔍 POR_VERIFICAR` y explica el bloqueo.

---

## 4. Reglas de evidencia (qué cuenta y qué no)

| ✅ Evidencia válida | ❌ NO es evidencia |
|---------------------|--------------------|
| Salida de comando con timestamp | "Debería estar activo" |
| Captura de consola/configuración | "Lo configuré hace tiempo" |
| Fragmento de log o ID de auditoría | Suposición por defecto del proveedor |
| Hash/ruta de un documento firmado | Enlace roto o inaccesible |
| Reporte de herramienta (scanner, SIEM) | Afirmación sin fuente |

Al adjuntar evidencia, incluye **fuente + fecha**. Ejemplo:
`Evidencia adjunta: salida 'aws iam get-account-password-policy' (2026-06-15), MinPasswordLength=14, RequireMFA=true`

---

## 5. Procedimiento paso a paso por modo

### Modo AUDITAR
1. Abre el checklist correspondiente.
2. Para cada item, ejecuta el campo **Cómo verificar**.
3. Compara el resultado con **Evidencia esperada**.
4. Asigna `Estado` y rellena **Evidencia adjunta** (fuente + fecha).
5. Si un item no aplica, usa `➖ NO_APLICA` + justificación.
6. Al final, actualiza el **bloque de contadores**.

### Modo REMEDIAR
1. Filtra items en `❌` o `⚠️`, ordenados por **Prioridad** (Crítica → Baja).
2. Ejecuta la **Remediación** descrita.
3. Vuelve a verificar (pasa por el modo AUDITAR de ese item).
4. Solo entonces cambia el estado a `✅` con su evidencia.
5. Nunca marques como hecho algo que no validaste tras el cambio.

### Modo REPORTAR
1. Cuenta items por estado en cada checklist.
2. Calcula: `% Cumplimiento = CUMPLE / (Total − NO_APLICA) × 100`.
3. Lista las **brechas críticas** (items `❌` de prioridad Crítica/Alta) primero.

---

## 6. Cómo calcular el cumplimiento

```
Total controles aplicables = (Total de items) − (items NO_APLICA)

% Cumplimiento = (items CUMPLE) / (Total controles aplicables) × 100
```

- `⚠️ PARCIAL` y `🔍 POR_VERIFICAR` cuentan como **no cumplido** para el porcentaje.
- Reporta también el **riesgo residual**: cualquier item `❌` de prioridad **Crítica** bloquea la certificación aunque el % global sea alto.

---

## 7. Límites y seguridad operativa (qué NUNCA hacer)

- ❌ **No inventes evidencia** ni asumas configuraciones por defecto.
- ❌ **No ejecutes acciones destructivas** (borrado de datos, wipe, rotación forzada de llaves en producción) sin confirmación humana explícita.
- ❌ **No expongas secretos** (llaves, contraseñas, tokens) en el campo de evidencia — usa identificadores o hashes, nunca el valor.
- ❌ **No cambies los IDs** de los controles; son la clave de trazabilidad.
- ✅ **Sí señala** cuando un control requiere decisión humana, presupuesto o acceso que no tienes.
- ✅ **Sí preserva** el formato exacto de los campos para que el archivo siga siendo parseable.

---

## 8. Orden de lectura recomendado para una IA

```
1. README.md                         (contexto general)
2. 00-INSTRUCCIONES-IA.md            (este archivo — reglas de operación)
3. normas/01..05                     (teoría de cada norma)
4. checklists/checklist-27001..27032 (ejecución y registro)
```

Cada archivo de norma enlaza a su checklist y viceversa, así que puedes navegar en ambos sentidos.
