---
generated: 2026-07-14
source: 4d-init
content_hash: 9a255cd7af81bd00354bf2d2dc269ec7015d162bc0b170b430db50a1f06955a1
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

`metadata.version` **no tiene script** (ningún bump per-plugin la toca, a propósito). Para un
release de la suite, editá `metadata.version` **a mano** en `marketplace.json`.
`check_suite_versions.py` NO la valida (es independiente de los plugins); solo tiene que ser
semver válido. El tag y el release de GitHub usan esta versión (`vX.Y.Z`).

## Ciclo de desarrollo local

El marketplace está registrado (`alexissamudio/4Dsentinel-suite` desde GitHub, o como Directory
local en dev). Tras cambiar un plugin:
`claude plugin marketplace update 4Dsentinel-suite` +
`claude plugin update <plugin>@4Dsentinel-suite` + sesión nueva — el plugin se copia a una caché
versionada (`~/.claude/plugins/cache/4Dsentinel-suite/<plugin>/<version>/`); los cambios NO se ven
en el lugar sin ese update.

## Orden de release (NO alterarlo)

1. **Bump** lo que cambió: `<plugin>_bump_version.py --set X.Y.Z` por cada plugin tocado, y/o
   `metadata.version` a mano para el release de la suite. Commits convencionales (subject ≤ 50
   chars, SIN atribución de IA).
2. **Verificar**: `uv run scripts/check_suite_versions.py` + `uv run pytest tests/ -q` verde.
   Prueba en vivo del feature si aplica (hooks por stdin y/o `claude -p` en un toy project).
3. **Push y CI**: `git push origin main`; esperar `gh run watch <run-id> --exit-status` hasta
   verde. Si falla, corregir y re-pushear ANTES de taggear.
4. **Recién con CI verde**: `git tag vX.Y.Z` (la versión paraguas) + `git push origin vX.Y.Z` +
   `gh release create vX.Y.Z --title "..." --notes "..."`.

## CI (.github/workflows/validate.yml)

Cuatro jobs: `fluency-4d` (ubuntu) y `fluency-4d-windows` (pytest en la plataforma real de uso),
`sentinel-agents` (agentes/skills/KB), y `suite` (JSON válidos, versiones per-plugin
sincronizadas vía `check_suite_versions.py`, ruff). Requiere `astral-sh/setup-uv@v5`: uv no viene
en los runners. Los tests POSIX-only (p. ej. ownership del temp dir, CWE-377) corren en los jobs
ubuntu y se saltean en Windows.
