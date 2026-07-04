---
generated: 2026-07-03
source: 4d-init
content_hash: 5a96a81ac79fd05f7581b399ee45b470df2facf262d8f60dba2b388bb37c5293
---

# Release y versionado en este proyecto

## La versión vive en TRES lugares (deben coincidir siempre)

1. `.claude-plugin/marketplace.json` → `metadata.version`
2. `.claude-plugin/marketplace.json` → `plugins[0].version`
3. `plugins/fluency-4d/.claude-plugin/plugin.json` → `version`

Nunca editarlos a mano: `uv run scripts/bump_version.py --set X.Y.Z`
(y `--check` para verificar). El CI falla si divergen.

## Ciclo de desarrollo local

El marketplace está registrado como directorio local (Directory source). Tras
cada cambio al plugin: `claude plugin marketplace update ai-fluency-4d` +
`claude plugin update fluency-4d@ai-fluency-4d` + sesión nueva — el plugin se
copia a caché versionada (`~/.claude/plugins/cache/ai-fluency-4d/...`), los
cambios NO se ven en el lugar.

## Orden de release (NO alterarlo)

1. `bump_version.py --set X.Y.Z` + commits convencionales (subject ≤ 50 chars,
   sin atribución de IA — el hook de oh-my-claude los rechaza).
2. `claude plugin marketplace update` + `plugin update`; verificar que la caché
   nueva contiene el código nuevo (grep de un string distintivo).
3. Smokes locales: `uv run --with pytest pytest tests/ -q` verde + prueba en
   vivo del feature (hooks: por stdin y/o `claude -p` en un toy project).
4. `git push` y esperar el CI: `gh run watch` hasta verde. Si falla, corregir
   y re-pushear ANTES de taggear.
5. Recién con CI verde: `git tag vX.Y.Z` + `git push origin vX.Y.Z` +
   `gh release create vX.Y.Z --notes "..."`.

## CI (.github/workflows/validate.yml)

Dos jobs: `validate` en ubuntu (JSON válidos, versión sincronizada, sin rutas
`../` en plugin.json, ruff, pytest) y `test-windows` (pytest en la plataforma
real de uso). Requiere `astral-sh/setup-uv@v5`: uv no viene en los runners.
