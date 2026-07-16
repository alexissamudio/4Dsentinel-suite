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
