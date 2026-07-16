---
description: Mapea los cambios de git a los simbolos afectados (envuelve detect_changes). Util antes de review o release.
argument-hint: "[rango git opcional; por defecto los cambios sin commitear]"
allowed-tools: ["mcp__codebase-memory__detect_changes", "mcp__codebase-memory__list_projects"]
---

Mapeá los **cambios de git a los símbolos** (funciones/clases) afectados.

- **Proyecto:** resolvelo del repo actual si no se da.
- Llamá `detect_changes` (usá `$ARGUMENTS` como rango git si se da; si no, los cambios actuales
  sin commitear).
- Presentá en español: qué símbolos toca el diff y, si aporta, qué otros dependen de ellos (la
  **superficie de impacto**). Ideal antes de una code-review o un release.
