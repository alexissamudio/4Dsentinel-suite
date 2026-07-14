---
generated: 2026-07-03
source: 4d-init
content_hash: b3f21db0aeb82c6da7662a10dbedb61fea954056ca6763fccc02307ea7b156d3
---

# Testing en este proyecto

30 tests en `tests/hooks/` que congelan el comportamiento de los 4 hooks.
Correr con:

```
uv run --with pytest pytest tests/ -q
```

## El patrón (conftest.py)

Cada test ejecuta el hook REAL por subprocess (`uv run --script`) pasándole el
payload JSON por stdin — no se importan los hooks como módulos. Fixtures:

- `run_hook(nombre, payload, env_extra)`: corre el hook con un env aislado.
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
