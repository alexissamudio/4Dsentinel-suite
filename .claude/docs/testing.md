---
generated: 2026-07-03
source: 4d-init
---

# Testing en este proyecto

~177 tests (173 pasan, 4 se saltean por ser POSIX-only) repartidos en
`tests/fluency-4d/` (los 7 hooks + `hook_utils` + el validador de skills) y
`tests/scripts/` (los bump/`bump_suite`, `frontmatter_utils`, y las guardas
`check_*`: agents, commands, kb_blank, suite_versions, ascii, commit_trailer).
Congelan el comportamiento observado (caracterización) más tests requisito-derivados
de seguridad. Correr con:

```
uv run --with pytest pytest tests/ -q
```

## El patrón (conftest.py)

Cada test ejecuta el hook REAL por subprocess (`uv run --script`) pasándole el
payload JSON por stdin — no se importan los hooks como módulos. Fixtures:

- `run_hook(nombre, payload, env_extra)`: corre el hook con un env aislado. Bajo
  `FLUENCY_COV` (solo el CI ubuntu la setea) envuelve el subprocess con
  `coverage run --parallel-mode` para medir cobertura real de los hooks (F16); la
  ruta default `uv run --script` queda intacta para dev local y Windows. Fija
  `cwd=REPO_ROOT` para que los `.coverage.*` caigan donde el combine los espera.
  Detalle del mecanismo en `pss.md` sec 9.
- `state_of(session_id, sufijo)`: lee el archivo de estado que dejó el hook
  (`-ckpt`, `-drift` o sin sufijo para el router).
- `project`: proyecto de juguete con `.claude/docs/` en tmp_path;
  `write_bridges(project)` le agrega un bridges.json de 3 temas.

## Aislamiento (lo que hace que no flakeen)

El env del subprocess redirige TODO lo persistente a `tmp_path`:

- `TMPDIR` + `TEMP` + `TMP` → estado de sesión (Linux usa TMPDIR; setear solo
  TEMP pasa en Windows y flakea en CI ubuntu).
- `HOME` + `USERPROFILE` → `~/.claude/fluency4d/stats.json` (telemetría).
- `PYTHONUTF8=1` y se limpian `FLUENCY_4D_SAVE_PCT`/`FLUENCY_4D_STRICT`.

## Trampas conocidas

- Paths con backslashes en los payloads: SOLO en Windows (`os.name == "nt"`);
  en Linux el backslash no es separador y el test falla en el runner ubuntu
  aunque pase local (ya pasó: ver commit "fix: portabilidad de paths").
- Los tamaños de transcript falsos van en BYTES EXACTOS (92_000, 420_000...)
  para que la aritmética de tokens (bytes/4 sobre 200k) sea inequívoca.
- Al tocar `bridge_router.py`, los 4 tests que congelan el bloque de emisión
  única (trailer una vez, vacío-pero-estado-guardado, cap 2 temas, bridges
  malformado) son los que avisan si rompiste algo.
- **Imports hermanos en `scripts/` + mypy strict:** los scripts se importan por
  nombre plano (`from bump_common import ...`, `from frontmatter_utils import ...`);
  funciona en runtime porque `uv run --script` pone el dir del script en `sys.path[0]`,
  y los tests hacen `sys.path.insert(0, scripts)`. Para que mypy los resuelva con
  tipos reales (y no como `Any` → `no-any-return`) el `pyproject.toml` tiene
  `mypy_path = ["scripts"]`. `check_commands.py` (en `plugins/memory/scripts/`) hace
  su propio `sys.path.insert(SUITE_ROOT/"scripts")` para el import cross-dir.

## Panel 4D (hooks module TSX, gate local)

El panel (`/panel`) es un hooks module del engine de mods de Claude
Code, declarado en `plugins/fluency-4d/hooks/hooks.json` bajo `"modules"` junto
a los hooks Python. Archivos (todos relativos a `plugins/fluency-4d/`):

- `hooks/register.tsx`: el modulo (el path de `modules` es relativo a hooks.json).
- `types/index.d.ts`: contrato de `$.state` (`PluginState['fluency-4d']`). SE COMMITEA.
- `tests/panel.test.tsx`: los tests del panel; `claude plugin test` busca `*.test.ts(x)`
  en la carpeta del plugin. El home falso es `/home/t` (neutro; el helper
  `slash` normaliza `\` y la letra de unidad que agrega Windows).
- `tsconfig.json`: extiende `./.claude-plugin/types/tsconfig.json`.

Correr desde `plugins/fluency-4d/`:

```
claude plugin validate .
claude plugin test
npx -p typescript@5.6.3 tsc -p tsconfig.json --noEmit
```

Tipos del engine (`.claude-plugin/types/`): NO se commitean (gitignored). Los
escribe el engine por build de Claude Code (~23k lineas, cambian con cada
version). Para regenerarlos: `claude --plugin-dir plugins/fluency-4d` (al cargar
el plugin los deja en `.claude-plugin/types/` con su tsconfig), o cargar la skill
`plugin-authoring`, que escribe `types/claude-code.d.ts` de este build en su
carpeta temporal (el header trae el tsconfig a usar). Sin esos tipos el `tsc`
falla: por eso el typecheck es gate local, no de CI. `claude plugin validate`
y `claude plugin test` no los necesitan.

Multiharness: `register.tsx`, `tests/`, `types/`, `tsconfig.json`,
`statusline/`, `themes/` y las skills `barra`/`statusline` estan en
`CLAUDE_CODE_ONLY` de `tools/multiharness/build_harness.py`, y la clave
`modules` de hooks.json se quita antes de emitir Codex/OpenCode
(`tests/scripts/test_build_harness.py`).

## /statusline setup (statusline_setup.py)

`plugins/fluency-4d/hooks/statusline_setup.py` no es un hook de evento (lo invoca la
skill `/statusline`), pero vive en `hooks/` para compartir `hook_utils.atomic_write_json`
y quedar bajo ruff, mypy y coverage. `tests/fluency-4d/hooks/test_statusline_setup.py`
lo corre por subprocess (mismo wrapper `FLUENCY_COV` que `run_hook`) con HOME y
USERPROFILE en `tmp_path`, y compara byte a byte los JSON del usuario tras
setup → remove. Requiere `node` en el PATH (se saltean sin node; el CI lo instala con
`setup-node`). Node ausente se simula con `FLUENCY_4D_NODE_BIN=<inexistente>`.

Variables y mecanismos que los tests ejercitan:

- `CLAUDE_CONFIG_DIR`: si está definido, `settings.json`, `keybindings.json` y
  `themes/` se resuelven desde ahí (como hace Claude Code y el panel en
  `register.tsx`). La copia fija, `setup.json`, `backups/` y el lock siguen SIEMPRE en
  `~/.claude/fluency4d/` (igual que los flags de `hook_utils`). El runner limpia la
  variable del entorno salvo que el test la pase.
- Lock `fluency4d/.setup.lock` (`O_CREAT|O_EXCL`, token pid+uuid): setup y remove lo
  toman; status no. Uno de más de 60 s es huérfano: se renombra atómicamente a
  `.setup.lock.stale.<uuid>` (solo un proceso gana el rename) y, si no es el mismo que
  se vio (mtime + contenido), se devuelve con `os.link`. El `mkdir` de `fluency4d/` va
  dentro del bucle (el dueño hace `rmdir` si lo creó vacío). Las carreras se testean
  importando el módulo en proceso y parcheando `os.replace`/`os.open`.
- `FLUENCY_4D_LOCK_WAIT=<s>`: acota la espera del lock (default 65 s).
- `FLUENCY_4D_FAIL_WRITE=<nombre>`: la escritura de ese archivo del usuario falla como
  si fuera de solo lectura (fault-injection del rollback). Solo tests.
- `.orig.bak`: `setup.json` anota en `orig_backups` los que creó ESTA instalación;
  remove borra solo esos y solo si restauró limpio. Uno previo ajeno se renombra a
  `<archivo>.orig.<ts>.bak` y nunca se borra (la poda solo matchea `<archivo>.<ts>.bak`).
- remove y status ignoran `copy` y `theme.path` de `setup.json`: borran solo las rutas
  calculadas. En Windows, setup rechaza rutas con caracteres fuera de la lista blanca
  (ASCII `[A-Za-z0-9_ ./:-]` + letras Unicode); por eso el test de `$` en HOME es POSIX.
