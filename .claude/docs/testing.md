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
