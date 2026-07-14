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
1. **Pinnear una version/tag concreta**, NO `latest`. Elegi un release fijo (ej.
   `v1.4.0`) y anotalo; asi la verificacion es reproducible y no cambia bajo tus pies:
   `https://github.com/DeusData/codebase-memory-mcp/releases/tag/<TAG>`
   Baja de ESE tag el `codebase-memory-mcp-windows-amd64.zip` **y** su `checksums.txt`.
   NO corras el `install.ps1` completo. Descomprimi a una carpeta temporal (todavia
   NO lo pongas en el PATH: primero se verifica).
2. **Verificacion OBLIGATORIA y SECUENCIAL** (ambas condiciones deben pasar, en orden;
   NO es "y/o"):
   1. **Atestacion de procedencia** — DEBE pasar:
      `gh attestation verify <exe> --repo DeusData/codebase-memory-mcp`
      (verifica la firma sigstore + SLSA contra ESE repo). Si falla -> **ABORTAR**.
   2. **Checksum SHA-256** — DEBE coincidir con el de `checksums.txt` de ese tag:
      `Get-FileHash -Algorithm SHA256 <exe>` y compara el hash (case-insensitive)
      con la linea del `.exe`/`.zip` en `checksums.txt`. Si NO coincide -> **ABORTAR**.
   - **Si cualquiera de las dos falla: ABORTAR. No coloques ni ejecutes el binario.**
     No hay fallback ni excepcion; un binario que no atesta o no matchea el checksum
     se descarta.
3. **Solo si (1) Y (2) pasaron**, colocar el ejecutable verificado. Preferentemente
   registralo con **ruta absoluta al `.exe` verificado**, no por resolucion via PATH
   (evita PATH-hijack: que un `codebase-memory-mcp` malicioso mas arriba en el PATH se
   ejecute en su lugar):
   `claude mcp add --scope user codebase-memory -- <ruta-absoluta-al-exe-verificado>`
   (o ajustar `plugins/memory/.claude-plugin/plugin.json` con esa ruta absoluta).
   Solo si preferis resolucion por PATH, copialo a un dir del PATH (ej. `~/.local/bin`).
   VERIFICAR: `codebase-memory-mcp --version` (o `& "<ruta-absoluta>" --version`).
4. **Reiniciar Claude Code** (el MCP se conecta al arrancar) y confirmar con `/mcp` que
   `codebase-memory` aparece conectado.
5. En cada repo grande: pedirle al MCP `Index this project` (tool `index_repository`).

## Uso (patron de la suite, domain-agnostic)
- El **conductor (main)** consulta el grafo: `search_graph`, `trace_path` (call-graph),
  `detect_changes` (git diff -> simbolos), en vez de fan-out de Explore que lee archivos.
- Los **agentes sentinel** NO ven mcpServers (los agentes de plugin los ignoran) -> el conductor
  les **relaya** los resultados del grafo en el brief (mismo patron que el handoff SENTINEL-REPORT).
- Cargar las tools del MCP de forma **diferida** (ToolSearch) para no inflar el contexto con 14 schemas.
