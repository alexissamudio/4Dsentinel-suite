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

## [2026-07-16] — Ruido del judge != mejora real; verificá el candidato contra HEAD
**Contexto:** en el `agent-improver` (reps:3, judge `effort:low`), el Run B reportó el
candidato del synth "aceptado vía PRECISION, fp 2.33 -> 1.33". Lo presenté como "hay una
versión mejor sin adoptar" y caractericé lo mergeado (0.6.3) como "cambio simple". Al
diffear el `candidateFileFull` del journal contra HEAD, resultaron IDÉNTICOS (salvo el
newline final): 0.6.3 YA ERA ese candidato. El fp 1.33 vs 2.33 fue variabilidad del LLM
judge sobre ~el mismo texto, no una mejora de contenido.
**Lección:** con reps bajos y judge de bajo esfuerzo, un delta de fp entre baseline y
candidato puede ser RUIDO, no señal — sobre todo cuando el catch-rate satura. Antes de
afirmar que un candidato es "mejor" o que "queda algo por adoptar", DIFF el texto del
candidato contra lo que ya está mergeado; si es idéntico, no hay delta que shippear.
**Cómo aplicar:** tratá los números del gate como ruidosos hasta anclarlos al TEXTO
(diff/byte-compare). No vendas una mejora medida en 1 corrida de 3 reps sin verificar que
el artefacto difiere; y no describas lo que mergeaste sin haber comparado su contenido real
contra el original (git show BASE:archivo).

## [2026-07-17] — Al delegar implementacion, verifica el LINT ademas de lo funcional
**Contexto:** un subagente escribio `scripts/check_verdict_enums.py`; lo verifique corriendo el check
(funcional, 11/11 OK) + ascii + agents, pero NO corri ruff. El CI fallo en "Ruff (lint + format check)"
por 2 `E501` (lineas >100) -> ida y vuelta extra (fix + re-push + re-watch).
**Leccion:** verificar el output de un subagente no es solo "funciona": el CI tiene ruff/format/mypy y el
subagente no siempre los corre. SIN EVIDENCIA = NO ESTA HECHO incluye el LINT del repo, no solo los tests.
**Como aplicar:** al recibir codigo de un subagente, antes de pushear correr los MISMOS checks que el CI
(`uvx ruff check .` ; `uvx ruff format --check .` ; mypy) ademas de lo funcional — o instruir al subagente
a correrlos y pegar la salida.

## [2026-07-17] — Verifica el remoto REAL (clone --mirror) antes de un force-push de reescritura
**Contexto:** pedido de "sacar un contributor del historial". El repo LOCAL mostraba 21 commits suyos y
autorice reescribir toda la historia + force-push de todas las refs. Antes de disparar, un `git clone
--mirror` del remoto mostro que el remoto YA estaba limpio (0 commits suyos): la reescritura se habia hecho
antes (quedaban `refs/original/*` locales de un filter-branch viejo + remote-tracking stale). El force-push
habria reescrito ~126 commits para NADA, rompiendo los clones del equipo.
**Leccion:** el estado LOCAL (ramas stale, `refs/original/*`, reflog) NO es el del remoto. Antes de una
operacion destructiva/irreversible sobre un repo compartido, verifica el remoto real. La UI de
"Contributors" de GitHub es cache (se computa del remoto, se recalcula asincrono; un push la gatilla;
mailmap no la cambia).
**Como aplicar:** para "sacar X del historial" -> `git clone --mirror <url>` + `git log --author` sobre el
mirror ANTES de tocar nada. `remote prune` + borrar `refs/original/*` + `gc` limpia el residuo LOCAL sin
force-push.

## [2026-07-23] — `cat <tmp> | clip` rompe UTF-8 en Windows (codepage OEM)
**Contexto:** el paso 7 de `/handoff` copiaba al portapapeles con `cat <tmp> | clip`. La captura del
usuario mostraba mojibake (`Sección`->`Secci├│n`). El archivo en disco estaba bien (UTF-8); solo se
rompia la COPIA.
**Leccion:** `clip.exe` decodifica stdin segun la codepage OEM activa de la consola (cp437/cp850); si
no es UTF-8, mis-decodifica los bytes multibyte y guarda mojibake en el portapapeles. `cp437` reproduce
byte-por-byte el mojibake. Es dependiente de la codepage, no siempre falla -> trampa intermitente.
**Como aplicar:** en Windows copiar al portapapeles con `Get-Content -Raw -Encoding UTF8 <tmp> |
Set-Clipboard` (codepage-independiente), NUNCA `| clip`. Fix aplicado en el skill handoff (commit 72570a9).

## [2026-07-23] — Codex CLI adopto el contrato de hooks de Claude, pero sus hooks son TUI-only
**Contexto:** al portar la suite a Codex CLI 0.130.0 (multi-harness), `codex exec` headless NO disparaba
los hooks (ni por `config.toml [hooks]` ni por `hooks.json`), pese a que el `config` parseaba y la feature
`CodexHooks` estaba activa.
**Leccion:** (a) Codex adopto el schema de hooks de Claude casi verbatim (verificable con `grep -a` sobre
el binario: `hook_event_name`/`permission_mode`/`hookSpecificOutput.additionalContext`/enum `plan`...);
el mecanismo real de descubrimiento es `hooks.json` (formato Claude), no `config.toml [hooks]`. (b) Los
hooks de Codex son del TUI interactivo; `codex exec` no los dispara (bug/limitacion conocida, openai/codex
#17532). (c) `codex debug prompt-input` arma el prompt OFFLINE (sin cuenta) pero NO dispara hooks.
**Como aplicar:** para probar hooks de Codex usar el TUI interactivo, no `exec`. Para un turno real sin la
cuenta (workspace 402), `codex exec --oss --local-provider ollama -m <modelo>` corre local/gratis. Verificar
schemas de binarios con `grep -aoE` antes de asumir incompatibilidad.

## [2026-07-23] — Preguntar "mejora o es bloat" antes de construir una feature
**Contexto:** ante "verifica el diff", el impulso fue planear una feature nueva (2 hooks + skill). El
usuario freno: "se puede mejorar el plugin en si, para no meter por meter?". La respuesta correcta fue
AFILAR una pieza existente (`discernment_gate.py`) en vez de agregar maquinaria.
**Leccion:** muchas "features" ya estan cubiertas por piezas existentes (aca: la politica, el gate, los
agentes verificadores ya existian; faltaba conectarlos). Los hooks tienen costo real (latencia 5s, tokens
por turno, mantenimiento). Reusar/afilar > agregar.
**Como aplicar:** antes de planear, chequear si la pieza ya existe y solo falta afilarla, o si una solucion
mas barata (regla, flag, reuso) da el 80%. Ofrecer la altitud minima primero, escalar solo con evidencia.

## [2026-11-02] — PRs apilados + squash: no borrar la rama base al mergear
**Contexto:** se mergeo #19 con `--delete-branch`; GitHub CERRO #20 (apilado sobre esa rama) en vez de
retargetearlo, y como el squash cambia los hashes hubo que rebasear y abrir #21. Ademas el CI solo corre
en PRs contra main: el PR apilado nunca tuvo checks, y al llegar a Ubuntu fallaron 4 tests Win32-only.
**Leccion:** con squash, el PR hijo necesita retarget (`gh pr edit N --base main`) ANTES de borrar la base,
y luego `git rebase --onto origin/main <commit-squasheado>`. Tests con rutas Win32 llevan `skipif(not IS_NT)`.
**Como aplicar:** al mergear una pila: retarget -> merge -> rebase del hijo; no confiar en "sin checks".
Y no confundir el acumulado de tokens del hook de checkpoint con el contexto actual (el del panel).

## [2026-11-02] — Rama ya squasheada en main: no mergear, cherry-pick sobre origin/main
**Contexto:** `feature/multiharness-codex-opencode` (ae3e6e6) se habia mergeado como squash (#16, 9314eed).
Al mergear origin/main encima, 9 conflictos add/add (incluido codigo de plugins). Ademas la `main` LOCAL estaba
vieja: `git rev-list main...HEAD` decia "0 detras" cuando origin/main tenia 4 commits nuevos.
**Leccion:** `git diff <rama> <squash>` vacio => la rama ya esta en main; el merge solo trae conflictos de
historia. Rama nueva desde origin/main + cherry-pick del trabajo nuevo = mismo resultado, sin conflictos.
**Como aplicar:** antes de mergear main, `git fetch` y comparar contra `origin/main` (no `main`); si hubo
squash, chequear el diff de arbol y preferir cherry-pick.

## [2026-11-02] — OpenCode: el contexto inyectado debe ser `synthetic:true` (y otros gotchas)
**Contexto:** el shim empujaba el additionalContext como parte text normal en `chat.message` -> la TUI lo
mostraba como si el usuario lo hubiera escrito. Verificado en el binario: la TUI filtra
`type==="text" && !synthetic`. Otros: Python en Windows lee stdin cp1252 (acentos rompen keywords);
sin `session_id` el state de hooks se fuga entre sesiones; `references/` fuera del proyecto requiere
`permission.external_directory`; los hooks tambien se inyectaban en subagentes.
**Leccion:** "smoke test con harness Node" no es E2E: estos bugs solo aparecen con `opencode run` +
`opencode export <sid>` (ver partes reales) y la TUI. Y un archivo que dice "Generado por X" puede no
serlo: 24 archivos de dist/opencode eran huerfanos; `check_harness` (DRIFT: sobra) lo destapo.
**Como aplicar:** al portar a OpenCode, verificar por export (synthetic, orden de ids, partes del subagente);
spawn de Python con `PYTHONUTF8=1`; correr check_harness ANTES de confiar en un dist/.

## [2026-11-03] — Timeout de hooks: medir el arranque en frío, no la corrida en caliente
**Contexto:** los 4-5 hooks `UserPromptSubmit` (`uv run --script`) dieron timeout a los 5 s en el
primer prompt de una sesión. A mano y en caliente tardaban ~0,3 s (0,5 s los 5 en paralelo), así que
"anda rápido" parecía cierto. Los transcripts (`hook_cancelled` / `hook_additional_context` vs el
timestamp del prompt) mostraron otra cosa: primer prompt p90 ≈ 4 s, pico 5,07 s; el resto p99 ≈ 3,4 s.
**Lección:** el presupuesto de un hook lo fija su peor caso (arranque en frío de uv/Python con la
máquina ocupada abriendo la sesión), no la medición en caliente. Un timeout pegado a la cola descarta
la salida en silencio.
**Cómo aplicar:** antes de fijar o diagnosticar un `timeout`, medir la distribución de latencia desde
los transcripts de `~/.claude/projects/*/*.jsonl` (separar primer prompt del resto) y dejar margen ≥ 2x
sobre el pico. Un valor de timeout compartido entre harnesses (shim OpenCode, Codex) se deriva de
`hooks.json`, no se copia.
