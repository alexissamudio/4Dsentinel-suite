# 4dsentinel-memory

Plugin que aporta el MCP **`codebase-memory`** (grafo de conocimiento del codebase) para la
sesión, más comandos en español que lo envuelven. No vendoriza el binario ni lo declara en
`plugin.json`: **`/suite-setup` instala el binario firmado y registra el MCP** con `claude mcp add`
(ruta absoluta verificada). El plugin **no declara `mcpServers`** a propósito: un command pelado
resuelto por PATH permitiría un cwd/PATH-hijack en Windows (CWE-427).

## Cómo funciona

1. **`/suite-setup`** instala el binario externo [`codebase-memory-mcp`](https://github.com/DeusData/codebase-memory-mcp)
   (C, MIT) de forma verificada (ver "Seguridad" abajo) y **registra el MCP** con
   `claude mcp add --scope user codebase-memory -- <ruta-absoluta-verificada>`. El `plugin.json`
   **no** declara el MCP (evita el cwd/PATH-hijack de un command resuelto por PATH); tras
   reiniciar, el MCP registrado conecta.
2. **`/indexar`** parsea el repo con tree-sitter → un **grafo**: nodos (funciones, clases, rutas,
   archivos) y aristas (`CALLS`, `IMPORTS`, `HTTP_CALLS`, `DEFINES`…). Persiste el artefacto en
   `.codebase-memory/graph.db.zst` **dentro del repo** (compartible con el equipo).
3. Consultás el grafo **estructuralmente** en vez de leer/grepear archivo por archivo.

## Comandos (envuelven las tools del MCP)

| Comando | Tool MCP | Qué hace |
|---|---|---|
| `/indexar [ruta]` | `index_repository` | Indexa el repo (persistencia dentro del repo) |
| `/arquitectura` | `get_architecture` | Stack, rutas API, hotspots (fan-in), clusters (Leiden) |
| `/buscar <consulta>` | `search_graph` | Funciones/clases/rutas por lenguaje natural o patrón |
| `/rastrear <función>` | `trace_path` | Llamadores/llamados e impacto (call-graph BFS) |
| `/impacto [rango git]` | `detect_changes` | `git diff` → símbolos afectados |
| `/proyectos` | `list_projects` | Proyectos indexados y estado |

El MCP expone 14 tools en total (incluyendo `query_graph` tipo Cypher, `get_code_snippet`,
`search_code`, `manage_adr`, `ingest_traces`); los comandos cubren las de uso diario.

## Patrón de uso (domain-agnostic)

- El **conductor** (agente principal) consulta el grafo y razona sobre los resultados, en vez de
  hacer *fan-out* de subagentes que leen archivos.
- Los **agentes de plugin NO ven el MCP** (limitación de Claude Code): por eso sentinel
  usa el grafo **por relay** — el conductor le pasa los resultados en el brief (mismo patrón que
  el handoff `SENTINEL-REPORT`).
- Cargá las tools del MCP de forma **diferida** (se resuelven bajo demanda) para no inflar el
  contexto con los 14 schemas.
- Aporta valor real en **codebases grandes** — como orientación, del orden de **cientos de
  archivos / miles de símbolos** para arriba; en repos chicos, `grep`/`Explore` alcanzan.

## Seguridad del binario (`/suite-setup`)

El binario es externo, así que la instalación es **verificada y secuencial** — ambas condiciones
deben pasar, en orden, antes de colocarlo:

1. **Atestación de procedencia:** `gh attestation verify <exe> --repo DeusData/codebase-memory-mcp`
   (firma sigstore + SLSA L3). Requiere **`gh` autenticado** (`gh auth login`): el comando
   consulta la API de GitHub y falla sin sesión. Si la verificación falla → **abortar**.
2. **Checksum SHA-256** contra el `checksums.txt` del tag pinneado. Si no coincide → **abortar**.

Se pinnea un **tag concreto** (no `latest`) para que la verificación sea reproducible. El MCP se
registra **siempre con ruta absoluta** al `.exe` verificado (nunca por resolución PATH; evita el
cwd/PATH-hijack, CWE-427). No se corre el
`install.ps1` completo (que agregaría hooks no deseados). Detalle en
`plugins/memory/skills/suite-setup/SKILL.md`.
