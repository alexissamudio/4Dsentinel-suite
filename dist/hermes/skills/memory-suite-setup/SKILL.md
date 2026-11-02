---
name: memory-suite-setup
description: Use when setup, instalar mcp. Install codebase-memory-mcp and configure MCP.
version: 0.6.0
author: Alexis Samudio (ported from 4Dsentinel-suite)
license: MIT
metadata:
  hermes:
    tags: [memory, codebase-memory, mcp, setup, install]
    related_skills: [memory-indexar]
---

# /suite-setup — Instalar codebase-memory MCP

## Paso 1: Instalar el binario (Windows PowerShell)

```powershell
irm https://github.com/DeusData/codebase-memory-mcp/releases/latest/download/install.ps1 | iex
```

## Paso 2: MCP ya configurado en Hermes

El `config.yaml` ya tiene la entrada `mcp_servers.codebase-memory`.

## Paso 3: Reiniciar Hermes

Al iniciar, Hermes descubre las ~15 tools MCP automaticamente.

## Paso 4: Indexar tu primer repo

```
/indexar
```
