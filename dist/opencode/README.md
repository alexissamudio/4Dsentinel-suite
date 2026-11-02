# Bundle OpenCode de la suite 4Dsentinel

Bundle regenerable que porta la suite de plugins de Claude Code a **OpenCode 1.19.x / 2.2.5**. Generado por `tools/multiharness/build_harness.py` desde la fuente canonica en `plugins/*` (read-only). NO editar a mano: `check_harness.py` falla si el bundle no coincide con el generador.

## Que incluye

- **Commands** (`command/*.md`, 15): `/4d`, `/4d-init`, `/4d-quiz`, `/4d-status`, `/adhd`, `/arquitectura`, `/buscar`, `/caveman`, `/handoff`, `/impacto`, `/indexar`, `/proyectos`, `/rastrear`, `/sentinel-audit`, `/suite-setup`. Cada command INCRUSTA el cuerpo real del skill/command fuente (y sus `references/`), traducido a OpenCode: nombres de agente calificados con el plugin sentinel-agents -> subagente `X` via la tool `task` (`subagent` en 2.x); la variable de raiz de plugin de Claude Code -> ruta absoluta del plugin en el repo; `AskUserQuestion` -> tool `question`; planes -> `.opencode/plans/` / `~/.local/share/opencode/plans/`.
- **Agentes** (`agent/*.md`, 11, `mode: subagent`): permisos derivados del allowlist `tools` fuente (read-only -> `edit/bash/webfetch: deny`) + `external_directory` permitido SOLO sobre `C:/Users/samud/.config/opencode/references/*` (el contrato y la KB viven fuera del proyecto; sin ese permiso `opencode run` lo auto-rechaza).
- **References** (`references/`): `agent-contract.md` (seccion 7 reescrita a la KB instalada) + KB ISO 27000 (`iso-27000/`, copia byte-a-byte, incluido `.manifest.sha256`).
- **Hooks** -> `plugin/fluency-hooks.js`: shim que puentea los hooks Python de `UserPromptSubmit` (bridge_router, plan_calibrator, caveman_injector, adhd_injector, suite_playbook). UN archivo con los dos contratos de plugin: `export default { id, server, setup }`. **v1 (1.x)** lee `server` y usa `chat.message`: inyecta una parte `synthetic: true` (el modelo la ve; la TUI no la muestra como texto del usuario) con id ascendente posterior al prompt. **v2 (2.x)** lee `setup(api)` y usa `api.session.hook("context")`: inserta un mensaje user SIN persistir despues del prompt, cacheado por id de mensaje (los hooks corren una vez por prompt, no en cada paso de tool). Payload: `session_id`, `hook_event_name`, `prompt`, `cwd`, `permission_mode` (`plan` si el agente es `plan`). Hooks en paralelo y sin bloquear el event loop. No inyecta en subagentes. Fuerza `PYTHONUTF8=1` para que los acentos lleguen bien.
- **Config** -> `opencode.json`: solo documenta el MCP; NO lo copies encima de tu config.

## Skills que NO se emiten (y por que)

- `verify-diff`: solo escribe el flag que lee el hook `Stop` (discernment_gate.py). El shim de OpenCode puentea UNICAMENTE `UserPromptSubmit` (`chat.message`) y OpenCode no tiene un evento que pueda bloquear el cierre del turno: el toggle no tendria ningun efecto, asi que emitirlo seria mentir.
- `barra`: cambia el modo/tema de la status line de Claude Code (no existe en OpenCode).
- `statusline`: instala la status line y el Panel 4D en settings.json de Claude Code (engine de mods exclusivo de Claude Code).

## Notas de portabilidad

- `caveman` / `adhd` escriben su flag en `~/.claude/fluency4d/` A PROPOSITO: es la ruta que leen `caveman_injector.py` / `adhd_injector.py`, que en OpenCode corren via el shim. Lo mismo `stats.json` (`/4d-status`).
- Los puentes siguen en `.claude/docs/` del proyecto (los lee `bridge_router.py`). OpenCode usa `AGENTS.md`; si no existe, cae a `CLAUDE.md`.
- Hooks `PostToolUse` (doc_drift, memory_checkpoint) y `Stop` (discernment_gate) NO se puentean: solo `UserPromptSubmit`.
- Rutas absolutas de ESTA maquina (repo y `~/.config/opencode`): regenerar si cambian.

## Instalacion (global)

Los agentes apuntan a `C:/Users/samud/.config/opencode/references` por ruta absoluta: instala en el dir global de OpenCode. Copia `command/`, `agent/`, `plugin/` y `references/` (NO `opencode.json`):

```bash
cp -r dist/opencode/command dist/opencode/agent dist/opencode/plugin dist/opencode/references ~/.config/opencode/
```

```powershell
Copy-Item -Recurse -Force dist/opencode/command,dist/opencode/agent,dist/opencode/plugin,dist/opencode/references "$HOME/.config/opencode/"
```

Al actualizar, borra en destino los archivos que instalo un bundle anterior y ya no se generan (p. ej. `command/verify-diff.md`).

## Verificacion

- `check_harness.py`: sin drift, JSON/TOML validos, hooks `.py` existentes, y guardas OpenCode (default `{ id, server, setup }`, parte `synthetic` en v1, hook `context` en v2, `session_id` y `PYTHONUTF8` en el shim, sin nombres calificados de sentinel-agents ni la variable de raiz de plugin de Claude, commands autocontenidos).
- `tests/scripts/opencode_shim_contract.mjs`: importa el plugin en Node y ejercita ambos contratos con mocks (lo corre `test_build_harness.py`).
- E2E en runtime real de `opencode 1.19.x / 2.2.5` (v1: `opencode run` + `opencode export`; v2: `opencode run --standalone` + `opencode session export`).
- OpenCode 2.x carga `command/` (o `commands/`), `agent/` y `plugin/` del dir global; `opencode run` de 2.x no tiene `--command`: los commands se usan desde la TUI (`/nombre`) o la API `session.command`.
- MCP (codebase-memory): fuera del bundle; se registra en el `opencode.json` del usuario.
