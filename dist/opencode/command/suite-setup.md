---
description: "Instala el binario de codebase-memory-mcp (grafo de codebase) y REGISTRA el MCP con ruta absoluta verificada (en opencode.json). El plugin ya NO declara el MCP. Triggers on '/suite-setup', 'instalar codebase-memory', 'setup de la suite'."
agent: build
---

<!-- Generado por tools/multiharness/build_harness.py desde plugins/memory/skills/suite-setup (cuerpo incrustado y traducido a OpenCode). NO editar a mano. -->

> **OpenCode (bundle 4Dsentinel, OpenCode 1.19.x / 2.2.5).** Este comando INCRUSTA el skill `suite-setup` completo: segui las instrucciones de abajo tal cual. NO busques un archivo de skill ni rutas de instalacion de Claude Code. Los subagentes de la suite (advisor, critic, librarian, ...) se invocan con la tool `task` (`subagent_type: <nombre>`) en OpenCode 1.x, o con la tool `subagent` (`agent: <nombre>`) en 2.x.
>
> Adaptado a OpenCode: el registro del MCP va en `opencode.json` (no hay `claude mcp add`). Las menciones al `plugin.json` describen el plugin de Claude Code.

# /suite-setup - instalar y registrar codebase-memory-mcp

Este plugin (`4dsentinel-memory`) **YA NO declara el MCP server** en su `plugin.json`
(no hay `mcpServers`): declararlo con un command pelado (`codebase-memory-mcp`) resuelto por
PATH permite un **cwd/PATH-hijack** en Windows (el cwd precede al PATH -> un exe hostil plantado
en el repo se auto-ejecuta al arrancar el MCP; CWE-427). Por eso el registro del MCP es
**OBLIGATORIO y manual**, en `opencode.json` y **ruta absoluta** al exe verificado (ver paso 3).
Este skill instala el binario de forma **minima y limpia** (sin los auto-hooks del install.ps1
oficial, que inyectan en cada grep/glob) y luego registra el MCP.

## Antes de instalar
- Es un binario externo (DeusData/codebase-memory-mcp, MIT, C). Postura de seguridad buena:
  firmas sigstore cosign + SLSA L3 (`gh attestation verify`) + SHA-256 checksums + VirusTotal.
- **Es outward-facing**: confirma con el usuario antes de bajar/ejecutar nada.
- Solo aporta valor en **codebases grandes** (su proposito es reducir tokens de exploracion) -
  como orientacion, del orden de cientos de archivos / miles de simbolos para arriba.

## Requisito previo: `gh` autenticado
Antes de empezar necesitas **`gh` (GitHub CLI) instalado y autenticado**: corre
`gh auth login` una sola vez. El paso de verificacion (`gh attestation verify`, paso 2)
consulta la API de GitHub y **falla sin sesion**. Confirma con `gh auth status` antes de seguir.

## Pasos (multiplataforma)
Los pasos son os-agnosticos salvo dos puntos marcados **por-OS** (el asset a bajar y el
comando de hash). `gh release download`, `gh attestation verify` y el registro en `opencode.json` corren
igual en Windows, macOS y Linux.

1. **Pinnear una version/tag concreta**, NO `latest`. Elegi un release fijo (ej.
   `v0.9.0`) y anotalo; asi la verificacion es reproducible y no cambia bajo tus pies.
   **Lista los assets de ESE tag** (no hardcodees nombres) con:
   `gh release view <TAG> --repo DeusData/codebase-memory-mcp`
   y baja el asset de **tu plataforma** mas su `checksums.txt`.
   - **OJO con la variante `-ui-`**: el repo publica DOS familias de assets por plataforma:
     el **MCP server** (`codebase-memory-mcp-<os>-<arch>`, el que necesitas) y una **GUI**
     (`codebase-memory-mcp-ui-<os>-<arch>`, ~37 MB, que NO es el MCP). El asset correcto
     **nunca** lleva el infijo `-ui-`. Un `--pattern` con comodines de borde (`*-windows-amd64.zip`)
     agarra las DOS; ancla el prefijo del binario base para excluir la UI.
   - **Windows** (por-OS): `--pattern "codebase-memory-mcp-windows-amd64.zip" --pattern "checksums.txt"`
     (o `-windows-arm64.zip` en ARM). El prefijo anclado `codebase-memory-mcp-windows` excluye
     `codebase-memory-mcp-ui-windows`.
   - **macOS / Linux** (por-OS): mismo criterio, anclando el prefijo base **sin `-ui-`**, con el
     nombre EXACTO que devolvio `gh release view` (ej. `codebase-memory-mcp-darwin-arm64.tar.gz`,
     `codebase-memory-mcp-linux-amd64.tar.gz`). No adivines arch/ext: lo dicta `gh release view`.
   - Comando general:
     `gh release download <TAG> --repo DeusData/codebase-memory-mcp --pattern "<asset-base-de-tu-OS>" --pattern "checksums.txt"`
     Tras bajar, confirma que en la carpeta quedo UN solo binario (sin el `.zip`/`.tar.gz` de la UI).
   NO corras el `install.ps1` completo. Descomprimi a una carpeta temporal (todavia
   NO lo pongas en el PATH: primero se verifica).
2. **Verificacion OBLIGATORIA y SECUENCIAL** (ambas condiciones deben pasar, en orden;
   NO es "y/o"):
   1. **Atestacion de procedencia** (cross-platform, mismo comando en todo OS) - DEBE pasar:
      `gh attestation verify <exe> --repo DeusData/codebase-memory-mcp`
      (verifica la firma sigstore + SLSA contra ESE repo). Si falla -> **ABORTAR**.
   2. **Checksum SHA-256** - DEBE coincidir con el de `checksums.txt` de ese tag. El comando
      de hash es **por-OS**:
      - **Windows:** `Get-FileHash -Algorithm SHA256 <exe>`
      - **Linux:** `sha256sum <exe>`
      - **macOS:** `shasum -a 256 <exe>`
      Compara el hash (case-insensitive) con la linea del binario/`.zip` en `checksums.txt`.
      Si NO coincide -> **ABORTAR**.
   - **Si cualquiera de las dos falla: ABORTAR. No coloques ni ejecutes el binario.**
     No hay fallback ni excepcion; un binario que no atesta o no matchea el checksum
     se descarta.
3. **Solo si (1) Y (2) pasaron**, colocar el ejecutable verificado en algun dir del usuario
   (ej. `~/.local/bin` en macOS/Linux, `%LOCALAPPDATA%` en Windows; NO hace falta que este
   en el PATH). Ahora **REGISTRA el MCP** - este paso es **OBLIGATORIO**: el plugin ya NO
   declara `mcpServers`, asi que sin este registro en `opencode.json` el MCP no existe. El registro va con
   **ruta ABSOLUTA** al ejecutable verificado, **NUNCA** por resolucion via PATH (una ruta
   absoluta no puede ser secuestrada por un `codebase-memory-mcp` hostil plantado en el cwd o
   mas arriba en el PATH - CWE-427):
   agrega a tu `opencode.json` global (`~/.config/opencode/opencode.json`) el bloque `"mcp": { "codebase-memory-mcp": { "type": "local", "command": ["<ruta-absoluta-al-exe-verificado>"], "enabled": true } }` (si ya existe una entrada, actualiza su `command`)
   VERIFICAR corriendo el binario con `--version`: `& "<ruta-absoluta>" --version` en
   PowerShell, `"<ruta-absoluta>" --version` en bash/zsh.
4. **Reiniciar OpenCode** (el MCP se conecta al arrancar) y confirmar con `opencode mcp list` que `codebase-memory-mcp` aparece conectado.
5. En cada repo grande: pedirle al MCP `Index this project` (tool `index_repository`).
   Es la **misma capa** que el comando **`/indexar`** del plugin: `/indexar` solo envuelve la
   tool `index_repository`. Da igual decir "Index this project" o correr `/indexar`.

## Uso (patron de la suite, domain-agnostic)
- El **conductor (main)** consulta el grafo: `search_graph`, `trace_path` (call-graph),
  `detect_changes` (git diff -> simbolos), en vez de fan-out de Explore que lee archivos.
- En OpenCode los subagentes de la suite SI pueden ver las tools MCP (salvo que sus permisos las nieguen), pero igual conviene que el conductor consulte el grafo y les **relaye** un brief conciso.
- En OpenCode las tools del MCP se exponen como `codebase-memory-mcp_<tool>` (prefijo = nombre del server en `opencode.json`).

Argumentos del usuario: `$ARGUMENTS`
