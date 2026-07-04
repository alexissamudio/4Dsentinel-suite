---
generated: 2026-07-03
source: 4d-init
content_hash: db831c75349f4cb0dab869f195329e81beb748db358f2ce155390e9504aa6e7a
---

# Convenciones de este proyecto

## Python (hooks, scripts, tests)

- Lint: ruff con `select = ["E", "F", "W", "I"]`, línea máx. 100, target py311
  (config en `pyproject.toml`). Correr: `uvx ruff check plugins/fluency-4d/hooks/ scripts/ tests/`.
- Scripts autocontenidos PEP-723 (`# /// script` + `requires-python >= 3.11`,
  `dependencies = []`): los hooks NO usan dependencias externas.
- `from __future__ import annotations` al tope; type hints en firmas públicas.
- **ASCII en el código Python**: strings de hooks sin acentos ("inyeccion",
  "sesion") — la consola Windows cp1252 rompe con Unicode; los acentos viven
  en los .md, no en los .py. `json.dumps(..., ensure_ascii=True)` siempre.
- Docstring de módulo en cada hook explicando evento y comportamiento.

## Markdown (skills, docs, README)

- Español rioplatense (voseo: "leé", "corré"), acentos correctos.
- SKILL.md < 150 líneas; el contenido extenso va a `references/`.
- Reglas duras en listas con NUNCA/SIEMPRE en mayúsculas.

## Git

- Commits convencionales en español sin acentos: subject ≤ 50 caracteres,
  cuerpo envuelto a 72, sin atribución de IA (el hook commit_quality_enforcer
  de oh-my-claude los valida y rechaza).
- Nunca commitear `__pycache__/`, `.venv/`, `.pytest_cache/` (gitignored).

## Herramientas de la máquina

- `jq` NO está instalado: validar JSON con `uv run python -m json.tool`.
- El `python` del PATH apunta al venv de hermes-agent: usar SIEMPRE `uv run`.
