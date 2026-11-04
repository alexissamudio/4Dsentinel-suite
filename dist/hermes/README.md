# Bundle Hermes de la suite 4Dsentinel

Bundle regenerable que porta la suite COMPLETA de plugins de Claude Code a
**Hermes Agent**. Generado por `tools/multiharness/build_harness.py` desde la
fuente canónica en `plugins/*` (read-only).

## Qué incluye

### fluency-4d (8 skills)
Marco 4D de AI Fluency: Delegación, Descripción, Discernimiento, Diligencia.
- `/4d`, `/4d-init`, `/4d-status`, `/4d-quiz`
- `/adhd`, `/caveman`, `/handoff`, `/verify-diff`

### sentinel-agents (12 skills)
Agentes de auditoría read-only + ejecutores:
- **Auditores**: `/advisor`, `/critic`, `/code-review`, `/bug-hunt`,
  `/security-audit`, `/compliance`, `/risk`, `/audit-text`, `/librarian`
- **Ejecutores**: `/validate`, `/debug`
- **Orquestador**: `/sentinel-audit tipo=X`

### Referencias incluidas
- `agent-contract.md` — contrato de evidencia dura, rúbricas, auto-verificación
- Instrucciones completas de cada agente en `references/<agent>.md`
- Banco de 24 preguntas para certificación AI Fluency
- Referencias del marco 4D (delegación, descripción, discernimiento, diligencia, fundamentos)

## Instalación

### Windows (PowerShell)
```powershell
cd dist/hermes
.\install-hermes.ps1
```

### Linux/macOS / manual
```bash
cp -r dist/hermes/skills/* ~/.hermes/skills/productivity/
```

### .hermes.md (opcional)
Copiá `dist/hermes/.hermes.md` a la raíz de tu proyecto para tener los puentes
de documentación y la lista de skills disponibles:
```bash
cp dist/hermes/.hermes.md ./.hermes.md
```

## Cómo usar

Una vez instalados, en tu próxima sesión de Hermes:

```
/4d                          # flujo guiado 4D
/sentinel-audit tipo=full    # pipeline completo de auditoría
/handoff                     # checkpoint de cierre de sesión
/adhd                        # modo comunicación accionable
```

## Qué se verificó

- Los 20 skills parsean correctamente en Hermes (frontmatter YAML válido)
- `skills_list` y `skill_view` los descubren
- Las references están enlazadas correctamente
- El instalador copia sin errores

## Adaptaciones Claude → Hermes

| Original (Claude Code) | Hermes Agent |
|---|---|
| `~/.claude/docs/` | `.hermes/docs/` |
| Hooks automáticos (UserPromptSubmit) | Skills bajo demanda + `memory` |
| Agent tool (subagentes nativos) | `delegate_task` vía skill |
| Flags JSON (caveman/adhd/verify) | Toggle en sesión |
| `AskUserQuestion` | `clarify` |
| `Write` tool | `write_file` |

## Pendiente

- **MCP codebase-memory**: DIFERIDO (binario `cbm` no instalado en Hermes)
- **Multiharness target hermes**: el build_harness.py aún no regenera `dist/hermes/`
  automáticamente; los skills se copian manualmente por ahora
