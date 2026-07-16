# Lecciones

Correcciones no triviales y errores cazados, para no repetirlos. Formato:
`## [fecha] — [título]` + contexto + lección + cómo aplicar. Máx ~30, fusionar duplicadas.

## [2026-07-15] — El bridges.json vive en la raíz, no en el plugin
**Contexto:** al planificar un puente de doc, el plan apuntó a
`plugins/fluency-4d/**/bridges.json`, que no existe. El critic lo cazó.
**Lección:** el `bridges.json` que los hooks leen en runtime está en
`.claude/docs/bridges.json` (raíz del repo), cargado por `bridge_router.py:124` y
`doc_drift.py:76`. Es dogfooding del repo, no un archivo shippeado dentro del plugin.
**Cómo aplicar:** para wirear un tema nuevo, editar `.claude/docs/bridges.json` + la
tabla de `CLAUDE.md` raíz. Keywords estrechas y sin solape con temas existentes
(`MAX_TEMAS_POR_PROMPT=2` → keywords anchas queman el cap).

## [2026-07-15] — Verificar los claims antes de actuar sobre ellos
**Contexto:** un análisis externo de eficiencia de tokens vendía como "prioridad #1"
partir `agent-contract.md` (ahorro ×4 en cadena). La verificación mostró que solo 3/11
agentes lo leen y en la cadena real solo 1 → ahorro 3-4× menor, premisa falsa.
**Lección:** los análisis (propios o traídos) inflan números y parten de supuestos no
medidos. SIN EVIDENCIA = NO ESTÁ HECHO aplica también a diagnósticos, no solo a fixes.
**Cómo aplicar:** antes de priorizar sobre un análisis, delegar un recon que confirme
cada claim con evidencia archivo:línea; recalibrar la prioridad con los números reales.

## [2026-07-15] — Los docs generados (4d-init) driftan; no los valida nada
**Contexto:** `README.md`, `hooks.md`, `testing.md`, `pyproject.toml` tenían conteos
viejos (4/6 hooks vs 7 real; 30/75 tests vs ~130). El `content_hash` del frontmatter no
lo valida ningún `.py`.
**Lección:** el drift documental es el fallo #1 del triángulo PSS (spec desincronizada)
ocurriendo en los propios docs. Nada lo atrapa automáticamente.
**Cómo aplicar:** al tocar hooks/tests/agentes, revisar el doc del tema (el hook
`doc_drift` avisa). Considerar un check que cuente hooks/tests reales vs lo documentado.

## [2026-07-15] — pytest-cov NO ve los hooks (corren por subprocess)
**Contexto:** al agregar coverage, los hooks daban 0% pese a estar muy testeados.
**Lección:** los hooks se ejecutan por subprocess (`uv run --script`), y `pytest-cov`
instrumenta solo el proceso padre → mide 0% (señal FALSA de "sin tests"). En cambio
`mutmut` SÍ los cubre porque muta el archivo en disco que el subprocess lee.
**Cómo aplicar:** medir `--cov` solo del código importado directo (`scripts/`); para los
hooks confiar en los tests E2E por subprocess (+ mutation), no en el % de cobertura.
Mutation en Windows requiere WSL (mutmut no corre nativo).

## [2026-07-15] — mypy strict + `# type: ignore` platform-only = trampa cross-platform
**Contexto:** `os.getuid()` (POSIX-only, guardado por `os.name`) llevaba
`# type: ignore[attr-defined]`. En lenient no molestaba; con `strict = true` (que activa
`warn_unused_ignores`) el CI **linux** —donde `getuid` SÍ existe— vería el ignore como
inútil y FALLARÍA, aunque en Windows pasa.
**Lección:** un `type: ignore` que solo aplica en una plataforma rompe el CI de la otra
bajo strict. Fix: agregar el código `unused-ignore` a la lista →
`# type: ignore[attr-defined, unused-ignore]` (suprime el error donde aplica Y tolera que
sea inútil donde no).
**Cómo aplicar:** al tipar código con ramas por `os.name`/plataforma, verificá mypy en
AMBAS (Windows local + WSL/linux) antes de pushear; el CI es linux.

## [2026-07-15] — El prefijo de tools MCP cambia según el SCOPE de registro
**Contexto:** los 6 comandos de memory tenían `allowed-tools` con prefijo plugin-scoped
`mcp__plugin_4dsentinel-memory_codebase-memory__*`, pero el fix CWE-427 movió el registro
del MCP de `plugin.json` a user-scope (`/suite-setup` → `claude mcp add codebase-memory`).
Las tools reales pasaron a `mcp__codebase-memory__*` → allowlists muertos, comandos caían
en prompt de permiso. Ningún check validaba los nombres.
**Lección:** el prefijo de una tool MCP depende de CÓMO se registra el server: plugin
declara `mcpServers` → `mcp__plugin_<plugin>_<server>__<tool>`; `claude mcp add <name>`
user-scope → `mcp__<name>__<tool>`. Mover el registro rompe cualquier `allowed-tools`
hardcodeado con el prefijo viejo, en silencio.
**Cómo aplicar:** al cambiar el scope/registro de un MCP, actualizá todos los
`allowed-tools`; agregá un check de CI que valide los nombres de tools, no solo que la
clave exista. En este entorno las tools se ven como `mcp__codebase-memory__<tool>`.
(Hecho 2026-07-16: `check_commands.check_allowed_tools` + `KNOWN_MCP_TOOLS`.)

## [2026-07-16] — Imports hermanos en scripts/ + mypy strict → no-any-return
**Contexto:** al extraer `bump_common.py`/`frontmatter_utils.py`, los wrappers hacían
`return bump_common.foo()` con retorno anotado. mypy (con `ignore_missing_imports`) no
resolvía el import plano `import bump_common` → lo trataba como `Any` → 15 errores
`Returning Any from function declared to return ...` bajo strict.
**Lección:** el import plano funciona en RUNTIME (`uv run --script` pone el dir en
`sys.path[0]`; los tests hacen `sys.path.insert`), pero mypy no lo ve sin ayuda.
`mypy_path = ["scripts"]` en `pyproject.toml` lo resuelve con tipos reales, sin dar
"source file found twice" (mismo nombre de módulo por ambas vías).
**Cómo aplicar:** al agregar un módulo compartido en `scripts/` que otros scripts
importan por nombre plano, verificá que `mypy_path` incluya su dir; corré mypy con los
DIRS completos (como el CI), no archivos sueltos, que también falla la resolución.

## [2026-07-16] — `mutmut results` SOLO lista sobrevivientes, no los matados
**Contexto:** al validar el nightly de mutmut (F16), `mutmut run` sobre `check_kb_blank.py`
mostró "Survived (28)" y `mutmut results` no listaba nada matado → pareció que TODOS los
mutantes sobrevivían (mutmut roto). Falso: consultando la cache
(`sqlite3 .mutmut-cache "select status,count(*) from mutant group by status"`) → 27 killed /
28 survived / 55 total. El mutante de lógica real (`not in`→`in`) fue matado; los 28
sobrevivientes eran legítimos (strings de mensajes que los tests no asertan, globales
monkeypatcheados, guarda `__main__`/argv no ejercitada, equivalentes como maxsplit 1 vs 2).
**Lección:** `mutmut results` es engañoso — solo imprime NO-matados. Para el mutation score
real consultar la cache SQLite por `status` (`ok_killed` vs `bad_survived`). "Todo sobrevive"
casi siempre es mala lectura, no mutmut roto. Y mutmut genera muchas mutaciones de strings que
sobreviven bien (los tests no deben asertar texto de mensajes).
**Cómo aplicar:** validar mutmut por conteo de la cache, no por `results`. mutmut nativo en
Windows corre el baseline pero NO muta (necesita WSL, `pss.md:126`); validar siempre en Linux/WSL.

## [2026-07-16] — agent-improver: el output del loop no se auto-aplica ni siempre da delta
**Contexto:** al construir `agent-improver` (Workflow que mejora prompts de agentes) y dogfoodearlo:
(a) el `synth.diff` que genera el LLM NO es `git apply`-able — trae entities HTML (`&lt;`/`&gt;`) y
conteos de línea `@@` imprecisos → "corrupt patch"; (b) con Opus, el baseline cazó el 100% de los
casos golden INCLUSO los diseñados "difíciles" (race, float-eq, off-by-one enmascarado) → sin headroom
para medir delta de recall; el gate correctamente no auto-acepta.
**Lección:** un loop de mejora de prompts es human-in-loop de verdad: el diff se aplica A MANO (que ES
la revisión de no-regresión), no mecánicamente. Y el valor no es solo el delta de catch-rate (un modelo
fuerte satura casos razonables); el **meta-review** es el entregable más consistente — produce gaps
reales y accionables (p. ej. "la ficha no define su SCOPE de entrada", "la enumeración de salida omite
`summary:`") que se aplican aunque el delta sea 0. El judge además es ruidoso (FP 2.0→1.33 en un run,
1.67→1.67 en otro) → por eso reps + margen.
**Cómo aplicar:** aplicar los `reviewDiff` a mano respetando check_agents (frontmatter/verdict/
=== SENTINEL-REPORT === intactos) + bump del plugin (F17); no confiar en git apply. Para medir delta de
recall se necesitarían casos que el modelo objetivo NO cace — difícil de calibrar con modelos fuertes;
tratar el meta-review como la señal primaria. Mejora del motor pendiente: exponer `candidateFileFull`
(hoy solo `diff`) para poder sobrescribir el .md sin depender del diff.

## [2026-07-16] — Gotchas de entorno/harness en la máquina Windows del usuario
**Contexto:** varios bloqueos de tooling ajenos al código: (a) el `.venv` del repo es de LINUX
(`home = /home/samud/.local/.../linux-x86_64`) → `uv run` intenta recrearlo y FALLA al borrar el symlink
`.venv/lib64` ("Access is denied"); (b) `Workflow({scriptPath})` con un `.js` en CRLF → el permission
handler lo rechaza ("script contains control characters"); (c) el clasificador de permisos BLOQUEA
`gh pr merge` de un PR que el propio agente abrió (auto-aprobación); (d) `Workflow({name})` no resuelve
workflows de `.claude/workflows/` (solo built-ins) → usar `scriptPath`.
**Lección:** son límites del entorno, no del trabajo. Workarounds: (a) `uv run --no-project --python 3.12
python scripts/<x>.py` (entorno efímero, no toca el .venv roto) y `uvx ruff`; arreglo real = borrar
`.venv` + `uv sync`; (b) forzar LF: `.claude/workflows/*.js text eol=lf` en `.gitattributes` + normalizar;
(c) el merge de un PR propio requiere OK explícito del usuario o que lo mergee él; (d) invocar por scriptPath.
**Cómo aplicar:** para checks Python locales usar el entorno efímero de uv; para workflows mantenerlos en
LF; no intentar auto-mergear PRs propios (pedir al usuario). El `resume` de Workflow puede NO cachear aunque
los prompts no cambien (re-corre full) — no asumir cache barato.

## [2026-07-16] — Un check de contenido se marca a sí mismo si no ancla el patrón
**Contexto:** `check_commit_trailer.py` (prohíbe `Co-Authored-By: Claude`) marcó su
PROPIO commit como infractor: el mensaje describía la regla y mencionaba el patrón
(`noreply@anthropic.com`, `Co-Authored-By: Claude`) en prosa.
**Lección:** un check que busca un patrón "en cualquier parte" del texto se dispara con
menciones legítimas (docs, mensajes que describen la regla). Un trailer git SIEMPRE está
a inicio de línea → anclarlo con `^...` + `re.MULTILINE` distingue el trailer real de una
cita. El test debe incluir un caso "menciona la regla en prosa → NO marca".
**Cómo aplicar:** al escribir un guard que busca strings prohibidos, anclá al formato
estructural real (inicio de línea, trailer, key: value), no substring libre; testeá el
falso positivo de auto-referencia.
