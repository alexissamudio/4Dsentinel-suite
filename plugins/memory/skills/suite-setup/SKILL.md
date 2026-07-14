---
name: suite-setup
description: Instala el binario de codebase-memory-mcp (grafo de codebase) y REGISTRA el MCP con ruta absoluta verificada (claude mcp add --scope user). El plugin ya NO declara el MCP. Triggers on '/suite-setup', 'instalar codebase-memory', 'setup de la suite'.
---

# /suite-setup — instalar y registrar codebase-memory-mcp

Este plugin (`4dsentinel-memory`) **YA NO declara el MCP server** en su `plugin.json`
(no hay `mcpServers`): declararlo con un command pelado (`codebase-memory-mcp`) resuelto por
PATH permite un **cwd/PATH-hijack** en Windows (el cwd precede al PATH -> un exe hostil plantado
en el repo se auto-ejecuta al arrancar el MCP; CWE-427). Por eso el registro del MCP es
**OBLIGATORIO y manual**, con `claude mcp add` y **ruta absoluta** al exe verificado (ver paso 3).
Este skill instala el binario de forma **minima y limpia** (sin los auto-hooks del install.ps1
oficial, que inyectan en cada grep/glob) y luego registra el MCP.

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
3. **Solo si (1) Y (2) pasaron**, colocar el ejecutable verificado en algun dir del usuario
   (ej. `~/.local/bin` o `%LOCALAPPDATA%`; NO hace falta que este en el PATH). Ahora
   **REGISTRA el MCP** — este paso es **OBLIGATORIO**: el plugin ya NO declara `mcpServers`,
   asi que sin este `claude mcp add` el MCP no existe. El registro va con **ruta ABSOLUTA**
   al `.exe` verificado, **NUNCA** por resolucion via PATH (una ruta absoluta no puede ser
   secuestrada por un `codebase-memory-mcp` hostil plantado en el cwd o mas arriba en el PATH
   — CWE-427):
   `claude mcp add --scope user codebase-memory -- <ruta-absoluta-al-exe-verificado>`
   VERIFICAR: `& "<ruta-absoluta>" --version`.
4. **Reiniciar Claude Code** (el MCP se conecta al arrancar) y confirmar con `/mcp` que
   `codebase-memory` aparece conectado.
5. En cada repo grande: pedirle al MCP `Index this project` (tool `index_repository`).

## Uso (patron de la suite, domain-agnostic)
- El **conductor (main)** consulta el grafo: `search_graph`, `trace_path` (call-graph),
  `detect_changes` (git diff -> simbolos), en vez de fan-out de Explore que lee archivos.
- Los **agentes sentinel** NO ven el MCP (los agentes de plugin no acceden a servidores MCP) -> el conductor
  les **relaya** los resultados del grafo en el brief (mismo patron que el handoff SENTINEL-REPORT).
- Cargar las tools del MCP de forma **diferida** (ToolSearch) para no inflar el contexto con 14 schemas.
