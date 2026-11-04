# Estado de sesión — 2026-11-02 — port OpenCode 1.19.1 arreglado (rama fix/opencode-runtime)

## Objetivo / frase 4D
Discernimiento + Diligencia: "muchos errores dentro de OpenCode" → reproducido con `opencode run` +
`opencode export`, diagnosticado por origen (WIP vs commiteado vs generador) y arreglado en el generador.

## Hecho
- `3985868` snapshot del WIP de 2026-08-03 (cherry-pick sobre origin/main; el original quedó en
  `bf88e6d` en la rama vieja `feature/multiharness-codex-opencode`, que ya estaba squasheada en main como #16).
- `9d2eef6` fix: shim con `synthetic:true` (la TUI ya no muestra el contexto como texto del usuario),
  id ascendente, `PYTHONUTF8=1`, payload con `session_id`/`hook_event_name`/`permission_mode`, sin
  inyección en subagentes. Generador produce los 45 archivos de `dist/opencode` (commands con SKILL.md
  incrustado, agentes con `external_directory`, `verify-diff` no se emite). `check_harness` con guardas.
- Verificado: check_harness OK, 7/7 tests, E2E (i)-(vii) con sessionIDs, E2E propio
  (`ses_e61d9a26dffey75oga85chzvbu`) y **prueba visual del usuario en la TUI: PASS**.
- Bundle instalado global en `~/.config/opencode/{command,agent,plugin,references}` (backup previo en el
  scratchpad de la sesión, `backup-oc`).

## Pendiente
1. Push de `fix/opencode-runtime` + PR a main (pedir OK al usuario).
2. `/caveman` y `/adhd` en `opencode run` no pueden escribir el flag (`external_directory` auto-reject);
   en la TUI piden permiso. No se amplió el permiso (en `~/.claude/fluency4d/` está statusline.js).
3. Sin E2E: `/4d-quiz`, `/sentinel-audit`, `/handoff`, `/suite-setup`.
4. Cada build reescribe `dist/hermes/.hermes.md` y check_harness no lo detecta (hermes solo valida frontmatter).
5. Hooks en serie (~1,2 s/mensaje): paralelizar. `dist/` sigue con rutas absolutas de la máquina.
6. Prueba visual del Panel 4D (Claude Code) tras reiniciar (`/panel`, `ctrl+x ctrl+p`).
7. Opcionales: setup rechaza rutas Windows con `( + ~`; pytest-xdist; idea `/statusline explicar`.

## Rutas
| Qué | Dónde |
|---|---|
| repo / rama | `C:\Users\samud\dev\4Dsentinel-suite` / `fix/opencode-runtime` |
| remote | https://github.com/alexissamudio/4Dsentinel-suite.git |
| generador | `tools/multiharness/build_harness.py`, `mappings.py`, `check_harness.py` |
| bundle OpenCode | `dist/opencode/` → instalado en `~/.config/opencode/` |
| repro E2E | `opencode run -m deepseek/deepseek-flash --format json "<msg>"` + `opencode export <sid>` |
| lecciones | `.claude/docs/lecciones.md` |

## Próximo paso
Con OK del usuario: push + PR a main. Después, pendientes 2-5.
