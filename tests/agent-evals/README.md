# agent-evals — dataset golden para el loop `agent-improver`

Casos con **problemas plantados de ground-truth conocido** para medir el desempeno real
de los agentes de `sentinel-agents` (catch-rate y falsos-positivos), y una rubrica de
calidad de prompt para el meta-review. Lo consume el Workflow `.claude/workflows/agent-improver.js`.

**Esto NO es una suite pytest.** Vive en `tests/` por convencion, pero:
- Los archivos de `input/` se nombran FUERA del patron `test_*.py` (p.ej. `buggy_snippet.py`,
  `vuln.py`, `plan.md`) para no gatillar coleccion de pytest.
- `pyproject.toml` agrega `--ignore=tests/agent-evals` a `addopts` (defensa por si alguien
  corre `pytest tests/`).
- No es contenido shippeado de ningun plugin (vive en `tests/`, dev-only) -> no lo toca
  `check_kb_blank` ni el gate de bump F17.

## Estructura

```
tests/agent-evals/
  README.md              # este archivo
  RUBRIC.md              # dimensiones de calidad de prompt (meta-review)
  <agente>/
    case-NN/
      input/…            # archivos reales que el agente lee (codigo, plan, mini-repo)
      expected.json      # ground truth
```

Agentes piloto: `bug-hunter`, `security-auditor`, `critic`.

## Formato de `expected.json`

```json
{
  "agent": "bug-hunter",
  "notes": "que trata el caso, en una linea",
  "must_catch": [
    { "id": "OB1", "where": "buggy_snippet.py:12", "why": "off-by-one: arr[i+1] desborda en la ultima iteracion" }
  ],
  "decoys": [
    { "where": "buggy_snippet.py:30", "why": "el <= es correcto aca: el limite es inclusivo a proposito" }
  ]
}
```

- **`must_catch`**: problemas plantados que el agente DEBE reportar. `catch-rate = caught / len(must_catch)`.
  - `id`: etiqueta corta y estable del problema (para trackear entre corridas). No es el `id`
    del SENTINEL-REPORT del agente; es del dataset.
  - `where`: `archivo:linea` (relativo a `input/`) donde vive el problema. El judge lo usa para
    matchear un finding del agente contra este item (por cercania de linea + semantica del `why`).
  - `why`: por que es un problema real, en una linea. Es el criterio del judge.
- **`decoys`**: cosas que PARECEN problemas pero NO lo son. Si el agente las reporta como
  finding CONFIRMED, cuenta como **falso-positivo**. Miden la disciplina de scope / calibracion.

## Ground truth = MANUAL

Cada caso se autora a mano con el problema conocido de antemano. NO se derivan de correr un
agente (seria circular). La verificacion #1 del plan corre el agente REAL sobre un caso a mano
solo como *sanity* (que el ground truth sea cazable), no como fuente de verdad.

**Judge-noise:** N chico + judge no determinista = ruido. Por eso el piloto apunta a **>=3-4
casos por agente** y el Workflow promedia varias `reps`. Al escalar, subir cada agente a >=4 casos.

## Como sumar casos (escalado)

1. Crear `tests/agent-evals/<agente>/case-NN/`.
2. Poner en `input/` los archivos reales (nombrados fuera de `test_*.py`).
3. Escribir `expected.json` con el ground truth (must_catch + decoys).
4. Sumar el agente a `targets` al invocar el Workflow. El motor no cambia; solo crece el dataset.

Severidades y verdicts esperables por agente (para calibrar `why` y decoys):
- **bug-hunter**: severidad `Critical|Important|Minor`; verdict `CLEAN|BUGS_FOUND|INCOMPLETE`.
- **security-auditor**: severidad CVSS `Critical|High|Medium|Low` + `CWE-<n>`; verdict `SECURE|CONCERNS|INSECURE|INCOMPLETE`.
- **critic**: severidad `Critical|Important|Minor`; verdict `APPROVED|NEEDS_REVISION|REJECTED|INCOMPLETE`.
