# Estado de sesión — 2026-07-16 — REMEDIACIÓN P1 MERGEADA A MAIN

## Objetivo / frase 4D
Diligencia: ejecutar el P1 de la auditoría 2026-07-15 (estructural, alto ROI).
**HECHO Y MERGEADO:** PR #6 (`fix/audit-p1-structural`, 11 commits) → `main`
(merge `b4a074c`), CI verde, branch borrada. 173 passed/4 skipped, ruff+mypy+9
checks verdes, code-review CLEAN sobre #6. Warning conocido en CI: Node 20 (= F18, P2).

## P1 — TODO HECHO (commits, en orden)
- `67acd7f` #6a F8 · `bbdcff8` #6b F9 · `3892aaa` hardening review #6 (verdict CLEAN)
- `9e1d89a` #10a F3 (nombres MCP en commands) · `580a161` #10b F1 (allowlist agentes)
- `7092a61` #8 F14 (bump_suite + check-tag) · `3e4854a` #9a F15 ASCII · `3816b44` #9b
  F15 trailer · `33aabb2` fix regex trailer (falso positivo con prosa) · `ba68810`
  #7 F6 (pin actions por SHA + ruff/mypy/deps fijas)
- Docs actualizadas: release.md (bump_suite, check-tag, supply-chain), testing.md
  (mypy_path, nuevos checks, conteo 177).

## Próximo paso — P2 (sesión nueva)
F16 coverage hooks + mutmut nightly; F11 `.sentinel/` en gitignore; F4/F5/F12 menores
(F4 anclas fallback al flag `fired`; F5 parsers `^---\s*\n` — ya hecho en produccion vía
frontmatter_utils, falta fluency_check_skills si se unifica; F12 content_hash muerto,
docstrings, DRY checks CI, rotulo README); F17/F18/F19 disciplina (bump, Node 24, ADR).

## Objetivo / frase 4D (auditoría previa, cerrada)

## Progreso P1 (esta sesión) — commits en fix/audit-p1-structural
- **#6a · F8 — HECHO (67acd7f):** `scripts/bump_common.py`; los 3 bump scripts son
  fachadas finas que preservan la API testeada (globals + set_version/read_versions/
  _market_entry para el monkeypatch). `mypy_path=["scripts"]` en pyproject.
- **#6b · F9 — HECHO (bbdcff8):** `scripts/frontmatter_utils.py` (frontmatter_body/
  frontmatter/parse_tools/strip_quotes). Migrados check_agents, sentinel_check_skills,
  check_commands (cross-dir vía sys.path+SUITE_ROOT). Regex `^---\s*\n` (F5). parse_tools
  conserva `.strip("'\"")` exacto. fluency_check_skills queda aparte (importlib).
- **Hardening review #6 — HECHO (3892aaa):** quitado `SEMVER` inerte de los wrappers;
  nuevo `test_frontmatter_utils.py` (cubre rama de quotes de parse_tools). El
  code-reviewer dio verdict CLEAN sobre 5ef2c62..bbdcff8 (2 Minor, ambos cerrados).
- **#10 · defensa F3/F1 — HECHO (9e1d89a + 580a161):** check_commands valida NOMBRES de
  tools MCP en allowed-tools (prefijo user-scope + KNOWN_MCP_TOOLS); check_agents suma
  KNOWN_AGENT_TOOLS (allowlist positivo, caza typos). Con tests.
- **#8 · F14 — HECHO (7092a61):** `scripts/bump_suite.py` (--check/--set/--check-tag) +
  validate.yml trigger en tags v* + step `metadata.version == git tag` (solo en tag).

## Pendiente P1 (en esta branch)
- **#9 · F15:** checks de convenciones en CI (ASCII-only en `**/*.py`, trailer de commit).
- **#7 · F6:** pin de actions por SHA + `uv.lock --frozen` + pin ruff/mypy (Dependabot).
- Al cerrar: revisar docs (release.md por bump_suite, testing.md por mypy_path), push + PR.
- Estado verificado: 166 passed / 4 skipped, ruff + mypy strict verdes.

## Objetivo / frase 4D (auditoría previa, cerrada)
Diligencia: auditoría completa 4D (loop-until-dry) de la suite, problemas presentes y
futuros. Deliverable: informe + plan de remediación priorizado. SIN fixes.

## Ya cerrado antes (en main): v1.0.3 (tokens) + endurecimiento V&V (9 gaps) + mypy strict.

## Auditoría — Ronda 1 (4 agentes) COMPLETA + verificada por mí. Ronda 2 (completitud) en curso.

### Hallazgos consolidados (dedupeados)

**PRESENTES — correctitud/seguridad**
- **A1 · BH-01 (Important, CONFIRMED por mí, `check_agents.py:74-81`):** `parse_tools`
  ignora `tools:` en bloque-lista YAML a indentación CERO (`- Write` sin sangría) →
  loop rompe → tools vacío → un agente con Write/Bash PASA el guard read-only. Latente
  (agentes actuales usan inline). El docstring dice que parse_tools cierra el formato
  lista, pero deja el hueco de indent-0.
- **A2 · BH-03 (Important, CONFIRMED):** 3 bump scripts acceden `["version"]` directo
  (`fluency_bump_version.py:55-56` etc.) → KeyError si falta (cf. `check_suite_versions.py:50`
  usa `.get`); `SEMVER ^\d+\.\d+\.\d+$` (`:35`) acepta `1.2.3\n` (usar `\Z`).
- **A3 · BH-04 (Minor, PLAUSIBLE, `memory_checkpoint.py:162-189`):** re-dispara al
  alternar modo nativo↔fallback (anclas fallback ignoran el flag `fired`).
- **A4 · BH-02 (Minor, MITIGADO):** parsers `^---\n` no toleran CRLF PERO `.gitattributes:6`
  fuerza `*.md eol=lf` → no reproduce en el repo. Solo robustez (endurecer como
  `fluency_check_skills.py:41` que ya usa `^---\s*\n`).

**PRESENTES — seguridad CI (supply-chain)**
- **A5 · SEC-CI-01 / R1 / R3 (Medium CVSS 6.1, CONFIRMED, `validate.yml:13-14,26-29,35,50`):**
  actions por tag mutable (checkout@v4, setup-uv@v5) + `uvx ruff/mypy` y `uv run --with ...`
  sin pin/lock/hash → code-exec en CI si se compromete un tag/paquete. Atenuado: sin
  secrets ni publicación en el workflow. **También es R1 (rotura por update upstream:
  ruff/mypy nuevos vuelven el CI rojo y bloquean releases).**
- **A6 · SEC-CI-02 (Low, CONFIRMED, `validate.yml` jobs sin `permissions:`):** GITHUB_TOKEN
  con default (potencial write); agregar `permissions: contents: read`.

**PRESENTES — calidad/mantenibilidad**
- **A7 · CR1 (Important, CONFIRMED):** triplicación casi total de los 3 bump scripts
  (~95 líneas ×3, ya divergen en naming e impl de `check()`). Extraer módulo común.
- **A8 · CR2 (Important, CONFIRMED):** `frontmatter()` duplicado 4× (`check_agents.py:35`,
  `sentinel_check_skills.py:23`, `check_commands.py:40`, +variante `fluency_check_skills.py:41`).
  Centralizar. (Matiz: parse_tools es solo de check_agents; el dup real es frontmatter.)
- **A9 · CR3 (Important, CONFIRMED, `pyproject.toml:12`):** `testpaths=["tests/fluency-4d"]`
  → `pytest` pelado local NO corre `tests/scripts/`; solo el CI (por `tests/` posicional).
  Verde falso local para cambios a scripts.
- **A10 · Minors:** content_hash muerto (no validado) · docstrings de bump apuntan a
  `scripts/bump_version.py` inexistente · checks JSON/`../` duplicados en 3 jobs del CI ·
  `check_kb_blank` excluye `.manifest.sha256` en subdirs (evasión teórica, no frontera).

**FUTUROS — riesgo operacional (risk-assessor)**
- **R2 (6):** `uv` punto único de fallo (hooks+scripts+CI). **R4 (5):** `metadata.version`
  paraguas se bumpea a mano, sin script ni check en CI → release inconsistente.
  **R5 (4):** coverage ciego (hooks subprocess) + mutmut solo WSL. **R6 (5):** bus factor 1;
  reglas ASCII/uv sin enforcement (convertir a checks de CI). **R7 (3):** Node20 dep +
  Python 3.11 EOL. **R8 (4):** caché versionada → correr stale si se olvida el bump.
  **R9 (3):** ADR no persiste en el `.zst`.

### Verificado por HOLDS (security re-leyó, sin bypass): sanitize_field, safe_doc_path,
CWE-377 `_state_path`, CWE-427 `_command_is_safe`, checksum KB, ReDoS/zip-bomb. El
endurecimiento de la sesión previa AGUANTA.

## Auditoría COMPLETA
Informe final en **`.claude/docs/auditoria-2026-07-15.md`** (19 hallazgos: 12 presentes +
7 futuros, dedupeados y verificados; plan de remediación P0/P1/P2). Ronda 2 sumó F3
(comandos memory con allowed-tools muertos — prefijo MCP plugin-scoped vs user-scope
`mcp__codebase-memory__*`, confirmado por el entorno) y F11 (.sentinel/ sin gitignore).
Cortada en 2 rondas por cap de contexto (no por dry) — declarado en el informe.

## Remediación P0 — HECHA y mergeada (PR #5, merge fe99238)
F1 (parse_tools indent-0 + test), F2 (bump .get + SEMVER \Z + 2 tests), F3 (prefijo MCP
en los 6 comandos → mcp__codebase-memory__), F7 (permissions CI), F10 (testpaths incluye
tests/scripts). CI verde, 142 tests. Informe con banner de remediación.

## Pendiente (P1/P2, opcional, decide el usuario)
- **P1:** extraer módulo común de bumps + helper único de frontmatter/parse_tools (F8/F9,
  mata la clase de bug); pin de deps/actions por SHA + uv.lock (F6); bump_suite.py + check
  metadata.version==tag (F14); checks de convenciones ASCII/commit en CI (F15); check de
  nombres de tools MCP en allowed-tools (defensa de F3).
- **P2:** coverage de hooks vía subprocess + mutmut nightly (F16); .sentinel/ en gitignore
  (F11); F4/F5/F12 menores; disciplina de bump/EOL/ADR (F17/F18/F19).
- Informe completo: `.claude/docs/auditoria-2026-07-15.md`.
