# Auditoría 4D de la suite — 2026-07-15

> **Estado de remediación:** los **P0 quick-wins** (F1, F2, F3, F7, F10) fueron
> ejecutados en la branch `fix/audit-p0-quickwins` (con tests para F1 y F2). P1/P2
> pendientes de decisión.

Auditoría completa (marco 4D, loop-until-dry) del monorepo 4Dsentinel-suite.
**Delegación:** fan-out de 5 agentes read-only (bug-hunter, security-auditor,
code-reviewer, risk-assessor + un crítico de completitud). **Descripción:** cada uno con
brief anclado en el repo. **Discernimiento:** cada hallazgo CONFIRMED fue re-leído y
verificado por el conductor (evidencia archivo:línea). **Diligencia:** este informe +
plan de remediación priorizado. **Sin fixes** — se deciden aparte.

Cobertura: correctitud (hooks+scripts), seguridad (superficie de ataque + supply-chain
CI), calidad/mantenibilidad, riesgo futuro/operacional, skills como orquestadores,
manifests, el generador 4d-init, licencias/secretos.

**Nota de completitud (honestidad):** se corrieron **2 rondas**. La ronda 2 aún halló
material (F3), así que NO se alcanzó el criterio estricto de "2 rondas consecutivas sin
hallazgos". Se **cortó por cap de contexto**, no por dry. Áreas de baja probabilidad de
más hallazgos (bien cubiertas): manifests, orquestación de skills, secretos. Límite
irreducible: la **calidad semántica de los prompts** de agentes/skills no se audita con
análisis estático (se gobierna con eval manual — ver `pss.md` §G6).

---

## Lo que AGUANTA (verificado, sin bypass)

El endurecimiento de sesiones previas fue re-leído por el security-auditor sin encontrar
bypass: `sanitize_field` (template-escape), `safe_doc_path` (traversal/absoluto),
`_state_path` (CWE-377, con sticky-bit + symlink/uid check), `_command_is_safe`
(CWE-427, allowlist con separador obligatorio), checksum de la KB (`check_kb_blank`),
y ausencia de ReDoS/zip-bomb en los hooks. **Manifests** consistentes (versiones
cruzadas por `check_suite_versions.py`, los 7 hooks de `hooks.json` existen). **Skills**
no escriben fuera del proyecto sin intención (caveman → flag global; 4d-init con backup +
confirmación). **Sin secretos hardcodeados, sin TODO/FIXME peligrosos, LICENSE MIT
presente.**

---

## Hallazgos PRESENTES

| ID | Severidad | Estado | Área | Evidencia | Resumen |
|----|-----------|--------|------|-----------|---------|
| **F1** | Important | CONFIRMED | seguridad/correctitud | `scripts/check_agents.py:74-81` | `parse_tools` exige `^\s+-` → una lista YAML a **indentación cero** (`- Write` bajo `tools:`) rompe el loop → tools vacío → un agente con `Write`/`Bash` **pasa el guard read-only**. Latente (agentes actuales usan inline). |
| **F2** | Important | CONFIRMED | correctitud | `scripts/fluency_bump_version.py:55-56,35` (+memory/sentinel) | `["version"]` por subscript directo → `KeyError` si falta (cf. `check_suite_versions.py:50` usa `.get`); `SEMVER ^\d+\.\d+\.\d+$` acepta `1.2.3\n` (usar `\Z`). |
| **F3** | Medium | CONFIRMED (evidencia de entorno) | funcional | `plugins/memory/commands/indexar.md:4` (+buscar/rastrear/impacto/arquitectura/proyectos) | Los 6 comandos declaran `allowed-tools` con el prefijo **plugin-scoped** `mcp__plugin_4dsentinel-memory_codebase-memory__*`, pero el fix CWE-427 movió el registro a user-scope (`/suite-setup` → `claude mcp add codebase-memory`) → las tools reales son `mcp__codebase-memory__*`. **Allowlists muertos** → cada comando cae en prompt de permiso en vez de correr pre-aprobado. Rompe "un install, todo funciona". `check_commands.py` solo valida que la clave exista, no los nombres. |
| **F6** | Medium (CVSS 6.1) | CONFIRMED | seguridad CI | `.github/workflows/validate.yml:13-14,26-29,35,50` | Actions por **tag mutable** (checkout@v4, setup-uv@v5) + `uvx ruff/mypy` y `uv run --with ...` **sin pin/lock/hash** → code-exec en CI si se compromete un tag/paquete. También causa **rotura por update upstream** (ruff/mypy nuevos → CI rojo → bloquea releases). Atenuado: sin secrets ni publicación en el workflow. |
| **F8** | Important | CONFIRMED | mantenibilidad | `scripts/{fluency,memory,sentinel}_bump_version.py:37-95` | Triplicación casi total de los 3 bump scripts (5 funciones ×3), ya divergiendo en naming e impl de `check()`. Un fix hay que aplicarlo 3 veces. |
| **F9** | Important | CONFIRMED | mantenibilidad | `check_agents.py:35`, `sentinel_check_skills.py:23`, `check_commands.py:40`, `fluency_check_skills.py:41` | `frontmatter()` duplicado 4× (una variante ya divergió). Origen de F1/F2 no propagándose. |
| **F10** | Important | CONFIRMED | testing | `pyproject.toml:12` | `testpaths=["tests/fluency-4d"]` → `pytest` pelado local **no corre `tests/scripts/`** (solo el CI, por `tests/` posicional). **Verde falso local** para cambios a scripts. |
| **F7** | Low | CONFIRMED | seguridad CI | `.github/workflows/validate.yml` (jobs sin `permissions:`) | GITHUB_TOKEN hereda el default del repo (potencial write). Falta least-privilege. |
| **F4** | Minor | PLAUSIBLE | correctitud | `plugins/fluency-4d/hooks/memory_checkpoint.py:162-189` | Re-dispara al alternar modo nativo↔fallback (anclas de fallback ignoran el flag `fired`). Requiere que el host togglee `used_percentage`. |
| **F5** | Minor | MITIGADO | robustez | parsers `^---\n` + `.gitattributes:6` | Los parsers no toleran CRLF, PERO `.gitattributes` fuerza `*.md eol=lf` → no reproduce en el repo. Endurecer como `fluency_check_skills.py:41` (`^---\s*\n`) por defensa. |
| **F11** | Low | CONFIRMED | higiene | `sentinel-audit/SKILL.md:18-25`, `.gitignore` | El relay escribe `<target>/.sentinel/<run-id>/*.md` en el repo auditado sin `.gitignore` ni gate opt-in explícito → riesgo de dejar artefactos commiteados en repos de terceros. (Introducido esta sesión.) |
| **F12** | Trivial | CONFIRMED | varios | — | `content_hash` de docs obsoleto y no validado; docstrings de bump apuntan a `scripts/bump_version.py` inexistente; checks JSON/`../` duplicados en 3 jobs del CI; `check_kb_blank` excluye `.manifest.sha256` en subdirs (evasión teórica); `4d-init/SKILL.md:77` dice min-keyword 4 vs `bridge_router.py:50` `MIN_KEYWORD_LEN=3`; `README:279` rotula "11 auditores" (son 9+2); `marketplace.json:35-41` array `skills` asimétrico. |

## Hallazgos FUTUROS (riesgo operacional)

| ID | Riesgo (1-10) | Área | Resumen |
|----|---------------|------|---------|
| **F13** | 6 | tooling | `uv` es **punto único de fallo**: hooks (runtime del usuario) + scripts + CI. Un cambio de CLI/PEP-723 rompe todo a la vez. |
| **F14** | 5 | release | `metadata.version` (paraguas, usada por el tag) se bumpea **a mano**, sin script ni check en CI → release inconsistente probable con 1 maintainer. `SEMVER` rechaza pre-releases/rc. |
| **F15** | 5 | proceso | **Bus factor 1**: reglas críticas (ASCII en `.py`, `uv run` obligatorio, no co-author) viven en CLAUDE.md sin enforcement automático → un contribuidor (o el mismo, sin contexto) las viola sin señal. |
| **F16** | 4 | testing | Cobertura ciega: `pytest-cov` no ve los hooks (subprocess); `mutmut` solo WSL/manual → regresiones de hook pueden shippear en verde. |
| **F17** | 4 | install | Caché de plugins **versionada**: si se olvida el bump, el usuario corre código stale o versión distinta a la del catálogo, sin señal. |
| **F18** | 3 | EOL | Node 20 deprecado en runners (warning visible) + Python 3.11 acercándose a EOL. Mecánico y anunciado. |
| **F19** | 3 | persistencia | El ADR no persiste en `.codebase-memory/graph.db.zst` (lo regenera `index_repository`). Decisiones que vivan solo en el grafo se pierden. |

---

## Plan de remediación priorizado (severidad × esfuerzo)

### P0 — Quick-wins de alto valor (trivial, hacer ya)
1. **F3** — reemplazar el prefijo en los 6 `plugins/memory/commands/*.md` por
   `mcp__codebase-memory__<tool>`. Restaura la función del plugin. *(Edición trivial.)*
2. **F1** — arreglar el regex de `parse_tools` para aceptar items a indentación cero
   (`^\s*-\s+`). Cierra el agujero del guard read-only.
3. **F2** — `.get("version")` con manejo de `None` en los 3 bumps + `SEMVER` con `\Z`.
4. **F7** — agregar `permissions: contents: read` a `validate.yml`.
5. **F10** — que `pytest` local recolecte `tests/scripts/` (ampliar `testpaths` o quitar
   la restricción) para matar el verde falso.

### P1 — Estructural / cierra clases de bug (esfuerzo medio)
6. **F8 + F9** — extraer un módulo común de bump (parametrizado por
   `PLUGIN_NAME`/`PATH`) y un helper único de `frontmatter`/`parse_tools`. Mata la
   divergencia que originó F1/F2 y la triplicación.
7. **F6** — pinear actions por **SHA** + `uv.lock` con `--frozen`/`--locked` y versiones
   fijas de ruff/mypy; renovar vía Dependabot controlado. Cierra supply-chain **y** la
   rotura por update upstream.
8. **F14** — `bump_suite.py` + check de CI que exija `metadata.version == git tag` en
   eventos de tag.
9. **F15** — convertir las reglas verificables en **checks de CI**: lint ASCII-only sobre
   `**/*.py`, check del trailer de commit. Mueve "convención" a "guarda ejecutable".
10. **Defensa de clase para F3/F1**: un check que valide los **nombres de tools MCP** en
    `allowed-tools` y los tools declarados en agentes (no solo la presencia de la clave).

### P2 — Defensivo / futuro (bajo esfuerzo o diferible)
11. **F16** — medir coverage de hooks vía `coverage run` del subprocess
    (`COVERAGE_PROCESS_START`/`.pth`) o E2E con assert de efectos; job nightly de mutmut
    en Linux (no bloqueante).
12. **F11** — agregar `.sentinel/` al `.gitignore` y un gate opt-in en `sentinel-audit`.
13. **F4** (atar anclas de fallback al flag `fired`), **F5** (endurecer parsers a
    `^---\s*\n`), **F12** (menores: borrar/validar `content_hash`, arreglar docstrings,
    DRY de los checks del CI, rótulo del README, alinear min-keyword).
14. **F17** — documentar/automatizar "todo cambio shippeado ⇒ bump" como precondición de
    release. **F18** — actions con Node 24 al salir + matriz 3.12/3.13. **F19** — ADR como
    archivos fuente versionados, el grafo como caché reconstruible.

---

## Resumen ejecutivo
- **0 hallazgos High/Critical de seguridad explotable.** Todo el hardening runtime aguanta.
- **3 Important presentes de correctitud/mantenibilidad** (F1 guard read-only, F2 bumps,
  F8/F9 duplicación) + **1 Medium funcional** (F3, comandos de memory rotos) + **1 Medium
  de supply-chain CI** (F6).
- El tema transversal: **duplicación** (bumps ×3, frontmatter ×4) que ya materializó bugs
  (F1/F2 no propagados) → P1 #6 es el de mayor ROI estructural.
- Riesgo futuro dominante: **fragilidad de tooling/proceso** (uv, deps sin pin, release
  manual, bus factor) más que deuda de código.
