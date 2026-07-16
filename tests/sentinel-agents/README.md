# Validación de sentinel-agents

Los agentes son PROMPTS (no deterministas): no hay pytest para su correctness. La
validación tiene dos capas.

## 1. Estructural (determinista, CI)

`.github/workflows/validate.yml`:
- JSON de manifests válido + versión sincronizada (`sentinel_bump_version.py --check`).
- Cada `agents/*.md` tiene frontmatter requerido (`name`, `description`, `tools`
  sin Write/Edit/Bash, `maxTurns`, `model: inherit`) y referencia el contrato.
- `check_kb_blank.py`: la KB bajo `references/iso-27000/` coincide con
  `references/iso-27000/.manifest.sha256` (guarda anti-write-back por checksum).

## 2. Semántica (gated, manual — no es CI gratis)

Correr cada agente sobre `tests/fixtures/target-vulnerable/` y medir contra el
ground truth de su README:
- **recall:** encuentra los 3 hallazgos plantados.
- **precision:** no alucina hallazgos ausentes (XSS/SSRF/etc.).
- **contrato:** la salida cierra con un bloque `=== SENTINEL-REPORT ===` parseable,
  con verdict del enum correcto y evidencia `archivo:línea`/control-ID.

Invocación (desde un cwd cualquiera, con el plugin instalado):
```
claude -p "Invocá el subagente sentinel-agents:security-auditor sobre tests/fixtures/target-vulnerable/ y pegá su bloque SENTINEL-REPORT" --allowedTools "Agent,Read,Grep,Glob"
```

## 3. Cadencia (cuándo correr la capa 2 — si no se agenda, se pierde)

La capa semántica es el vértice del triángulo PSS que NO se puede cubrir con pytest
(prompts no deterministas; ver `.claude/docs/pss.md` §G6). Se gobierna con proceso:
corré la eval manual **antes de**:
- cada release que toque `agents/*.md`, `references/agent-contract.md`, o la KB ISO;
- mergear un cambio en el prompt de un agente (aunque el CI estructural pase).

Registrá `recall`/`precision`/`contrato` del run en el PR. Si el recall baja de los 3
hallazgos plantados o aparecen alucinaciones, NO mergear. La capa 1 (estructural, CI)
NO sustituye esto: valida la FORMA del agente, no que ENCUENTRE lo que debe.
