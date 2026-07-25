# Bundle Codex de la suite 4Dsentinel (PoC)

Bundle regenerable que porta parte de la suite de plugins de Claude Code a **Codex CLI 0.130** (que adopto el contrato de hooks de Claude Code). Generado por `tools/multiharness/build_harness.py` desde la fuente canonica en `plugins/*` (read-only).

## Que incluye este PoC

- **Skill** `handoff` -> `.agents/skills/handoff/SKILL.md` (rutas `~/.claude` reescritas a `~/.codex`).
- **Slash command** `handoff` -> `prompts/handoff.md`.
- **Hooks** -> `hooks.json` (formato Claude Code): `UserPromptSubmit` (bridge_router, plan_calibrator, caveman_injector, suite_playbook), `PostToolUse` (doc_drift, memory_checkpoint) y `Stop` (discernment_gate), con rutas absolutas a esta maquina.
- **Subagente** `critic` -> `[agents.critic]` en `config.toml` + `critic.config.toml` + `agents/critic.md`.
- **AGENTS.md** con las reglas duras del proyecto.

## Como descubre Codex los hooks

Codex ejecuta los hooks a partir de un `hooks.json` con el **mismo formato JSON que Claude Code**, buscado en `$CODEX_HOME/hooks.json` o en `<proyecto>/.codex/hooks.json`. Este es el mecanismo real (verificado por E2E). El bloque `[hooks]` de `config.toml` **parsea pero NO ejecuta** nada: por eso el bundle NO declara hooks ahi, solo deja `[features] hooks = true` y emite el `hooks.json`.

> **Los hooks de Codex son de la sesion interactiva (TUI).** `codex exec` (headless) **NO** los dispara -- es una limitacion conocida de Codex (ref issue [openai/codex#17532](https://github.com/openai/codex/issues/17532)), no un defecto de este bundle.

## Instalacion

Codex usa `CODEX_HOME` (default `~/.codex`). Copia el contenido de este bundle ahi (incluido `hooks.json`):

```bash
# Linux/macOS
cp -r dist/codex/. "${CODEX_HOME:-$HOME/.codex}"/
```

```powershell
# Windows PowerShell
$dst = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { "$HOME\.codex" }
Copy-Item -Recurse -Force dist\codex\* $dst
```

Alternativa por proyecto: copia `hooks.json` a `<proyecto>/.codex/hooks.json`. Verifica ademas que `config.toml` tenga `[features] hooks = true`.

## Que se verifico

- El generador corre sin error y es idempotente (`check_harness.py` no reporta drift).
- `hooks.json` parsea como JSON y `config.toml` con `tomllib`.
- Las rutas de los hooks son absolutas y apuntan a `.py` existentes.

## Pendiente / no verificado

- **E2E con Codex**: NO ejecutado aca (lo valida el humano). Recordar que los hooks solo corren en la TUI interactiva, no en `codex exec`.
- **MCP** (codebase-memory / `cbm`): DIFERIDO, binario no instalado.
- **Resto de subagentes** y `references/agent-contract.md`: TODO.
- `~/.claude/plans/`: sin equivalente en Codex -> el paso del plan en `handoff` degrada a "sin plan".
