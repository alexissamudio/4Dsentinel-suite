# Bundle OpenCode de la suite 4Dsentinel (PoC)

Bundle regenerable que porta parte de la suite de plugins de Claude Code a **OpenCode 1.17.11**. Generado por `tools/multiharness/build_harness.py` desde la fuente canonica en `plugins/*` (read-only).

## Que incluye este PoC

- **Command** `handoff` -> `command/handoff.md` (frontmatter `description` + `agent`; cuerpo que dispara el flujo del skill `handoff`).
- **Agentes** `critic` y `advisor` -> `agent/*.md` (`mode: subagent`, `permission: { edit: deny, bash: deny, webfetch: deny }` derivado del allowlist read-only Read/Grep/Glob del frontmatter fuente).
- **Hooks** -> `plugin/fluency-hooks.js`: shim que puentea los hooks Python de `UserPromptSubmit` por subprocess (no reescribe la logica).
- **Config** -> `opencode.json` (MCP diferido).

## Instalacion

Copia los directorios `command/`, `agent/` y `plugin/` bajo la carpeta `.opencode/` del proyecto (o de `~/.config/opencode/` para uso global), y `opencode.json` a la raiz del proyecto (o `~/.config/opencode/`):

```bash
# por proyecto
mkdir -p .opencode
cp -r dist/opencode/command dist/opencode/agent dist/opencode/plugin .opencode/
cp dist/opencode/opencode.json ./opencode.json
```

```powershell
# Windows PowerShell (por proyecto)
New-Item -ItemType Directory -Force .opencode | Out-Null
Copy-Item -Recurse -Force dist\opencode\command,dist\opencode\agent,dist\opencode\plugin .opencode\
Copy-Item -Force dist\opencode\opencode.json .\opencode.json
```

## Que se verifico

- El generador corre sin error y es idempotente (`check_harness.py` no reporta drift).
- `opencode.json` parsea como JSON.
- Las rutas de los hooks en el shim JS son absolutas y apuntan a `.py` existentes.

## Pendiente / no verificado

- **E2E con OpenCode**: shim smoke-tested (harness Node que importa `fluency-hooks.js`, simula `chat.message` y verifica la inyeccion en `output.parts` corriendo los hooks Python reales) -> PASS. Falta solo el E2E en runtime real de `opencode` (lo valida el humano).
- **API de plugins de OpenCode**: VERIFICADA (1.17.11) e implementada. El shim `fluency-hooks.js` usa el hook `chat.message` (equivalente a `UserPromptSubmit`): lee el texto del usuario de `output.parts` e inyecta contexto con `output.parts.push({type:'text', text})`. Degrada a NO-OP seguro ante fallos. Falta solo el E2E (ver arriba).
- **Resto de skills** (`4d`, `4d-init`, `4d-status`, `4d-quiz`, `caveman`) y **resto de subagentes**: TODO.
- **MCP** (codebase-memory / `cbm`): DIFERIDO, binario no instalado.
