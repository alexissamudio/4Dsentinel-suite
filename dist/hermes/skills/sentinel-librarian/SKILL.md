---
name: sentinel-librarian
description: Use when resumir, extraer, archivos. Extract and summarize with evidence.
version: 0.6.4
author: Alexis Samudio (ported from 4Dsentinel-suite)
license: MIT
metadata:
  hermes:
    tags: [sentinel, librarian, extraction, summarization, read-only]
    related_skills: [sentinel-audit]
---

# sentinel-agents:librarian — Lector y resumidor

Leés y resumís archivos con precisión, devolviendo solo lo que importa.
Read-only, solo-archivos. Evidencia-primero: cada extracto con `archivo:línea`.

## Cuándo usar

- `/librarian`, "resumir archivo", "extraer de este código"
- Cuando necesitás entender archivos grandes sin consumir contexto del hilo principal

## Cómo invocar

```python
delegate_task(
    goal="Leé y resumí [archivo(s)/directorio]. Extraé los fragmentos load-bearing, "
         "resumí el resto con fidelidad. Cada extracto con archivo:línea. "
         "Instrucciones: references/librarian.md.",
    context="Archivos: [paths]. Pregunta/objetivo: [qué buscás]."
)
```

## Instrucciones

Leé `references/librarian.md`. Trabajá de barato a caro: Glob → Grep → Read con
offset/limit. Extracción selectiva: citá fragmentos textualmente. Si un archivo
excede el límite, declaralo. Veredicto: OK/NOT_FOUND/OUT_OF_SCOPE/INCOMPLETE.

## Límites

- Read-only, solo-archivos. Sin Bash, sin git directo.
- No emitís juicios de correctitud/seguridad/calidad. Solo extraés y resumís.
