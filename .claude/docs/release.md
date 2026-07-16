---
generated: 2026-07-14
source: 4d-init
---

# Release y versionado en este proyecto (monorepo 4Dsentinel-suite)

## Dos niveles de versión (independientes)

La suite es un **monorepo** con 3 plugins. Hay dos niveles de versión que NO están acoplados:

1. **Versión por-plugin** (semver X.Y.Z de cada plugin). Cada plugin la tiene en DOS lugares
   que deben coincidir:
   - `.claude-plugin/marketplace.json` → `plugins[name=="<plugin>"].version`
   - `plugins/<dir>/.claude-plugin/plugin.json` → `version`

   (dirs: `fluency-4d`, `sentinel-agents`, `memory`)

2. **Versión paraguas de la suite** = `.claude-plugin/marketplace.json` → `metadata.version`.
   Es la versión del **release de la suite** (tags `vX.Y.Z`), INDEPENDIENTE de los plugins.

## Bumpear un plugin (nunca a mano)

Cada plugin tiene su script. Indexan la entrada del marketplace por `name` (NO por índice) y
**NO tocan** `metadata.version`:

- `uv run scripts/fluency_bump_version.py --set X.Y.Z`
- `uv run scripts/sentinel_bump_version.py --set X.Y.Z`
- `uv run scripts/memory_bump_version.py --set X.Y.Z`

`--check` verifica la sincronía de los 2 lugares. `scripts/check_suite_versions.py` cruza, por
cada plugin, la entrada del marketplace contra su `plugin.json` (imprime `paraguas == subtree`).
El CI corre este check y falla si divergen.

## Bumpear el paraguas (release de la suite)

`metadata.version` la maneja **`scripts/bump_suite.py`** (ningún bump per-plugin la toca):

- `uv run scripts/bump_suite.py --set X.Y.Z` → escribe `metadata.version`.
- `uv run scripts/bump_suite.py --check` → la imprime.
- `uv run scripts/bump_suite.py --check-tag vX.Y.Z` → valida `metadata.version == tag`.

`check_suite_versions.py` NO valida el paraguas (es independiente de los plugins). El tag y el
release de GitHub usan esta versión (`vX.Y.Z`); en un **push de tag** el CI corre
`bump_suite.py --check-tag` y **frena el release si el tag no coincide** con `metadata.version`.

## Ciclo de desarrollo local

El marketplace está registrado (`alexissamudio/4Dsentinel-suite` desde GitHub, o como Directory
local en dev). Tras cambiar un plugin:
`claude plugin marketplace update 4Dsentinel-suite` +
`claude plugin update <plugin>@4Dsentinel-suite` + sesión nueva — el plugin se copia a una caché
versionada (`~/.claude/plugins/cache/4Dsentinel-suite/<plugin>/<version>/`); los cambios NO se ven
en el lugar sin ese update.

## Orden de release (NO alterarlo)

1. **Bump** lo que cambió: `<plugin>_bump_version.py --set X.Y.Z` por cada plugin tocado, y/o
   `bump_suite.py --set X.Y.Z` para el release de la suite. Commits convencionales (subject ≤ 50
   chars, SIN atribución de IA — el CI lo verifica con `check_commit_trailer.py`).
2. **Verificar**: `uv run scripts/check_suite_versions.py` + `uv run pytest tests/ -q` verde.
   Prueba en vivo del feature si aplica (hooks por stdin y/o `claude -p` en un toy project).
3. **Push y CI**: `git push origin main`; esperar `gh run watch <run-id> --exit-status` hasta
   verde. Si falla, corregir y re-pushear ANTES de taggear.
4. **Recién con CI verde**: `git tag vX.Y.Z` (la versión paraguas) + `git push origin vX.Y.Z` +
   `gh release create vX.Y.Z --title "..." --notes "..."`.

## CI (.github/workflows/validate.yml)

Cuatro jobs: `fluency-4d` (ubuntu) y `fluency-4d-windows` (pytest en la plataforma real de uso),
`sentinel-agents` (agentes/skills/KB), y `suite` (JSON válidos, `check_suite_versions.py`,
`check_ascii.py`, `check_commit_trailer.py`, y en push de tag `bump_suite.py --check-tag`).
Requiere `setup-uv`: uv no viene en los runners. Los tests POSIX-only (p. ej. ownership del
temp dir, CWE-377) corren en los jobs ubuntu y se saltean en Windows.

**Supply-chain (F6):** las actions están pineadas por **SHA de commit** (no por tag mutable) y
`ruff`/`mypy`/deps de pytest tienen **versión fija** en el workflow. El trigger incluye
`tags: [v*]`. Al subir una action o el tooling, actualizar el SHA/versión a conciencia.

**Coverage de hooks (F16):** el job `fluency-4d` corre con `FLUENCY_COV=1`, que hace que la fixture
`run_hook` instrumente el subprocess de cada hook con `coverage run` y mida su cobertura REAL
(ver `pss.md` sec 9). `coverage` está pineado a la misma versión que arrastra `pytest-cov` para que
el combine no falle por mismatch de schema. Es **report-only** (sin `fail_under`).

**Mutation nightly (F16, `.github/workflows/mutation.yml`):** workflow SEPARADO en `schedule`
(diario) + `workflow_dispatch`, **no bloqueante** (nunca es required-check de PRs). Corre `mutmut`
**pineado 2.x** (muta in-place → el subprocess `uv run --script` lee la mutación; mutmut 3.x aísla
en `mutants/` y NO serviría) sobre hooks + guardas de seguridad; surface = step summary + artifact,
permisos `contents: read`. Sobrevivientes ahí son informativos, no rompen nada.

**Manifests DRY (F12):** la validación de JSON de manifests + la guarda anti-`../` viven en un
único `scripts/check_manifests.py` (descubre los manifests por glob), invocado una sola vez en el
job `suite`. Antes se repetían inline en 3 jobs.

**Gate de bump (F17):** `scripts/check_bump_on_change.py` (job `suite`) FALLA si un PR cambia
contenido **shippeado** de un plugin (cualquier archivo bajo su `source` del marketplace: código,
hooks, skills, agents, commands, plugin.json) **sin** bumpear su `version`. Compara `BASE..HEAD`
(mismo `BASE` que `check_commit_trailer`). Docs internos del repo (`.claude/docs/`, `README`,
`docs/adr/`, auditoría) no son contenido de plugin → no cuentan. Un plugin nuevo (sin versión en
`BASE`) no exige bump. Cierra "todo cambio shippeado ⇒ bump".

**Matriz Python (F18):** el job `fluency-4d` corre en matriz `python-version: [3.12, 3.13]` (vía
`UV_PYTHON`) para adelantarse al EOL de 3.11. Los pins de actions ya están en **Node 24**
(`checkout` v7, `setup-uv` v8).

**ADR versionados (F19):** las decisiones de arquitectura viven en `docs/adr/` como archivos fuente
versionados (MADR liviano); el grafo `.codebase-memory/graph.db.zst` es caché reconstruible, no su
hogar. Ver `docs/adr/README.md`.
