---
name: suite-setup
description: Instala el binario de codebase-memory-mcp (grafo de codebase) que este plugin cablea via mcpServers. Triggers on '/suite-setup', 'instalar codebase-memory', 'setup de la suite'.
---

# /suite-setup — instalar el binario de codebase-memory-mcp

Este plugin (`4dsentinel-memory`) YA declara el MCP server `codebase-memory` en su
`plugin.json` (`mcpServers`, command `codebase-memory-mcp`). Lo unico que falta para que
conecte es tener el **binario en el PATH**. Este skill lo instala de forma **minima y limpia**
(sin los auto-hooks del install.ps1 oficial, que inyectan en cada grep/glob).

## Antes de instalar
- Es un binario externo (DeusData/codebase-memory-mcp, MIT, C). Postura de seguridad buena:
  firmas sigstore cosign + SLSA L3 (`gh attestation verify`) + SHA-256 checksums + VirusTotal.
- **Es outward-facing**: confirma con el usuario antes de bajar/ejecutar nada.
- Solo aporta valor en **codebases grandes** (su proposito es reducir tokens de exploracion).

## Pasos (Windows)
1. Bajar el binario firmado del release mas reciente:
   `https://github.com/DeusData/codebase-memory-mcp/releases/latest`
   (archivo `codebase-memory-mcp-windows-amd64.zip`), NO correr el `install.ps1` completo.
2. Verificar integridad: `gh attestation verify <exe> --repo DeusData/codebase-memory-mcp`
   y/o el `checksums.txt` (SHA-256) del release.
3. Colocar el ejecutable en un directorio del PATH (ej. `~/.local/bin`, que el instalador
   oficial usa) de modo que `codebase-memory-mcp` resuelva. VERIFICAR: `codebase-memory-mcp --version`.
   - Nota Windows: si el MCP no conecta con command `codebase-memory-mcp`, puede necesitar la
     ruta absoluta al `.exe`; en ese caso ajustar `plugins/memory/.claude-plugin/plugin.json`
     o registrar con `claude mcp add --scope user codebase-memory -- <ruta-absoluta>`.
4. **Reiniciar Claude Code** (el MCP se conecta al arrancar) y confirmar con `/mcp` que
   `codebase-memory` aparece conectado.
5. En cada repo grande: pedirle al MCP `Index this project` (tool `index_repository`).

## Uso (patron de la suite, domain-agnostic)
- El **conductor (main)** consulta el grafo: `search_graph`, `trace_path` (call-graph),
  `detect_changes` (git diff -> simbolos), en vez de fan-out de Explore que lee archivos.
- Los **agentes sentinel** NO ven mcpServers (los agentes de plugin los ignoran) -> el conductor
  les **relaya** los resultados del grafo en el brief (mismo patron que el handoff SENTINEL-REPORT).
- Cargar las tools del MCP de forma **diferida** (ToolSearch) para no inflar el contexto con 14 schemas.
