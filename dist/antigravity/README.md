# Bundle Antigravity de la suite 4Dsentinel (PoC)

Bundle regenerable que porta parte de la suite de plugins de Claude Code a **Google Antigravity**. Generado por `tools/multiharness/build_harness.py` desde la fuente canonica en `plugins/*` (read-only).

## Que incluye este PoC

- **Manifest** -> `plugin.json` (schema nativo de plugins de Antigravity: `name`, `displayName`, `version`, `description`, `author`, `homepage`, `repository`).
- **Skill** `handoff` -> `skills/handoff/SKILL.md` (rutas `~/.claude` reescritas a `~/.gemini/antigravity`).
- **Agentes** `critic` y `advisor` -> `agents/*.md` (frontmatter `name` + `description`; los subagentes Markdown en Antigravity son read-only por defecto).
- **Rules** -> `rules/AGENTS.md` (reglas duras y tabla de puentes de `CLAUDE.md`, sin frontmatter YAML para que Antigravity las aplique como `always_on`).
- **Hooks** -> `hooks.json` (en la raiz del plugin, clave superior `"fluency-4d"`) + `hooks/fluency_hooks.py` (shim Python que puentea `PreInvocation` -> `UserPromptSubmit` y `Stop` -> `discernment_gate` por subprocess, sin duplicar la logica).

## Como descubre Antigravity los hooks

A diferencia de Claude Code (donde `hooks.json` vive en `hooks/` y usa `"hooks"` como clave raiz), Antigravity exige `hooks.json` en la **raiz del plugin** (`<plugin_dir>/hooks.json`) con el nombre del grupo como clave superior (`"fluency-4d"`). Al disparar un hook, Antigravity ejecuta el comando con `cwd = <plugin_dir>` y pasa el payload en protojson camelCase por stdin (`conversationId`, `workspacePaths`, `transcriptPath`, `lastUserInput`, `invocationNum`).

El shim `hooks/fluency_hooks.py` traduce ese payload al contrato de Claude Code (`session_id`, `cwd`, `transcript_path`, `prompt`) y adapta la salida:

- En `PreInvocation` (solo cuando `invocationNum == 0`, inicio del turno del usuario): corre `bridge_router`, `plan_calibrator`, `caveman_injector`, `adhd_injector` y `suite_playbook`, y devuelve `{"injectSteps": [{"ephemeralMessage": "..."}]}`.
- En `Stop`: corre `discernment_gate` y traduce `{"decision": "block", "reason": "..."}` a `{"decision": "continue", "reason": "..."}`.

## Instalacion

1. Regenera el bundle en tu maquina para que las rutas absolutas de `hooks/fluency_hooks.py` apunten a tu clon local:

```bash
uv run --script tools/multiharness/build_harness.py
```

2. Copia `dist/antigravity/` al directorio de plugins de Antigravity (global en `~/.gemini/config/plugins/4dsentinel-suite/` o por proyecto en `<proyecto>/.agents/plugins/4dsentinel-suite/`):

```bash
# Linux/macOS (global)
mkdir -p "$HOME/.gemini/config/plugins/4dsentinel-suite"
cp -r dist/antigravity/. "$HOME/.gemini/config/plugins/4dsentinel-suite/"
```

```powershell
# Windows PowerShell (global)
$dst = "$HOME\.gemini\config\plugins\4dsentinel-suite"
New-Item -ItemType Directory -Force $dst | Out-Null
Copy-Item -Recurse -Force dist\antigravity\* $dst
```

## Que se verifico

- El generador corre sin error y es idempotente (`check_harness.py` no reporta drift).
- `plugin.json` y `hooks.json` parsean como JSON y respetan las claves top-level de Antigravity.
- Las rutas de los hooks en `hooks/fluency_hooks.py` son absolutas y apuntan a `.py` existentes.
- El shim `hooks/fluency_hooks.py` fue probado extremo a extremo por subprocess simulando `PreInvocation` (`invocationNum` 0 y >0) y `Stop`.

## Pendiente / no verificado

- **Hooks `PostToolUse`** (`doc_drift`, `memory_checkpoint`): en Antigravity `PostToolUse` solo acepta `{}` en stdout (no soporta `injectSteps`), por lo que correr `doc_drift` ahi consumiria el estado de sesion sin poder inyectar el aviso. Queda como TODO puentearlos via cola hacia `PostInvocation`/`PreInvocation`.
- **Resto de skills** (`4d`, `4d-init`, `4d-status`, `caveman`, `adhd`, `verify-diff`) y **resto de subagentes**: TODO.
- **MCP** (codebase-memory / `cbm`): DIFERIDO, binario no instalado.
