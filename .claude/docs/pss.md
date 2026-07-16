# Pruebas de Sistema de Software (PSS) — teoría y estado del proyecto

Doc de referencia consolidado (sesión 2026-07-15). Dos partes: **teoría** (el marco)
y **estado real de la suite** (superficie de V&V + registro de gaps con evidencia).

---

## 1. El triángulo: requisitos ↔ código ↔ tests

Todo test vive entre tres vértices. Los tres modos de fallo:

1. **Código y test coinciden pero ignoran la spec** → verificación ✅, validación ❌.
   "Construiste a la perfección lo que el cliente no pidió." El más peligroso: *todo
   está verde*, el bug es que el objetivo estaba mal.
2. **Tests que van por libre y no muerden la implementación** → problema del **oráculo**:
   mocks de más, aserciones tautológicas → el test pasa por construcción, no prueba nada.
3. **Ni spec ni código** → triángulo roto entero: ruido.

Un buen test, cuando falla, **implica a los tres vértices a la vez**.

### V&V
- **Verificación** = "¿construí bien el software?" → coherencia **código ↔ test**.
- **Validación** = "¿construí el software correcto?" → coherencia **producto ↔ requisito**.

### El principio rector: higiene del oráculo
El triángulo **no se rompe en el código ni en el test — se rompe en el ORÁCULO**, que
es el único vértice que una IA no puede originar sin el humano. Si el oráculo se deriva
*leyendo el código* (lo que hace una IA sola), colapsás validación contra verificación
→ verde-mentiroso. El oráculo puede corromperse de dos formas: **débil** (tautológico,
no muerde) o **ruidoso** (flaky, miente al azar).

---

## 2. Verificación estática vs dinámica

| | **Estática** (sin ejecutar) | **Dinámica** (ejecutando) |
|---|---|---|
| Qué es | Revisiones, análisis de flujo, linters, type-checkers, verificación formal, schema/checksum | Unit/integración/E2E, fuzzing, profiling |
| Qué pregunta | ¿está bien formado / cumple reglas? | ¿se comporta bien con esta entrada? |
| Poder | Prueba **AUSENCIA** de una clase de defecto | Solo prueba **PRESENCIA** en las entradas corridas (Dijkstra) |
| Costo | Barato, temprano (shift-left) | Caro, necesita oráculo |
| Vértice | Casi todo verificación | Alcanza validación *si el oráculo viene de la spec* |

La **revisión humana contra la spec es estática** — y es la herramienta de *validación*
más barata que existe.

---

## 3. Diseño de casos de prueba

**Black-box (derivan de la SPEC → atacan validación):** antídoto al sesgo de la IA.
- **Partición de equivalencia:** clases del dominio donde el sistema debería
  comportarse igual; un representante por clase.
- **Valores límite (boundary value analysis):** los bugs viven en los bordes
  (`<` vs `<=`, off-by-one, 0, vacío, máx, máx+1). Altísimo ROI.
- **Tabla de decisión / transición de estados:** para lógica combinatoria y máquinas
  de estado.

**White-box (derivan del CÓDIGO → verificación):** camino básico, coverage-driven.
Necesarias, pero no salvan del fallo #1.

---

## 4. TDD / BDD — poner el oráculo ANTES del código

**TDD (Red / Green / Refactor):** test que falla → código mínimo que pasa → refactor.
No podés congelar un comportamiento que aún no existe → imposibilita la caracterización.
Límite honesto: si entendiste mal el requisito, escribís un oráculo-basura y TDD te lo
pinta de verde. Es *verificación disciplinada*, no validación.

**BDD (Given/When/Then):** sube el oráculo a un artefacto legible por el negocio →
requisito y test son **el mismo documento** (specification by example). Cuando el nombre
del test ES el requisito, tenés BDD de facto.

---

## 5. Dobles de prueba e integración

| Doble | Reemplaza | Controla |
|---|---|---|
| **Stub** | dependencia que el SUT llama | estado (respuestas prefabricadas) |
| **Mock** | ídem + verifica la interacción | comportamiento (esperá que se llame X) |
| **Fake** | implementación liviana real (DB en memoria) | — |
| **Spy** | envuelve el real y registra el uso | — |
| **Driver** | algo que **llama** al SUT (hacia arriba) | — |

**Reglas:** no mockees lo que no poseés (usá contract tests); mockeá **bordes** (red,
disco, reloj), no el **dominio**. Sobre-mockear = testear el mock (= fallo #2).

**Estrategias de integración:** big-bang (malo, no localiza fallas); **top-down**
(stubea lo de abajo no integrado); **bottom-up** (drivers ejercitan las hojas);
sándwich.

**V-model** (el triángulo estirado): Requisitos↔Aceptación (validación) · Diseño↔Integración · Código↔Unit (verificación).

---

## 6. Property-based testing — de "ejemplo" a "propiedad"

Declarás un **invariante que vale para TODO input** y el framework **genera** entradas
para falsificarlo. Encuentra el bug que no imaginaste. Tooling: **Hypothesis** (Python).

- **Shrinking:** minimiza el fallo al contraejemplo más chico (debug casi gratis).
- **Familias de propiedades:** invariante, round-trip/idempotencia, conmutatividad,
  metamórfica, "oráculo fácil de verificar aunque difícil de calcular".
- Resuelve un pedazo del **problema del oráculo**: no necesitás el valor exacto, solo
  una relación.
- Caveats: cuesta encontrar la propiedad; pinear semilla en CI (`derandomize`); más lento.

---

## 7. Mutation testing — probar que los tests MUERDEN

Metés un **mutante** (bug artificial) y corrés la suite: falla → mutante **muerto** ✅;
pasa → **sobrevive** ❌ (cobertura sin aserción → agujero). **Mutation score =
muertos / (total − equivalentes).**

- **Operadores:** ROR (`<`→`<=`), AOR (`+`→`-`), LCR (`and`→`or`), statement deletion,
  constant replacement, UOI (insertar `not`).
- **Mutante equivalente:** semánticamente idéntico, no se puede matar; detectarlo es
  **indecidible** en general → el score nunca llega limpio a 100%.
- Coverage dice "lo ejecuté"; mutation dice "lo habría atrapado si estuviera mal".
- Costo alto → correr sobre **código crítico** y **archivos cambiados**. Tooling:
  `mutmut`, `cosmic-ray`.

---

## 8. Test smells & flakiness — cuándo un test miente

**Flaky** = pasa/falla sin cambiar el código. Erosiona la confianza → la gente ignora el
rojo → la suite se vuelve un oráculo que nadie cree.

**Causas:** no-determinismo (reloj/random/UUID); estado compartido / orden; concurrencia
/`sleep`; recursos externos / fuga de entorno; plataforma (locale, timezone, separador
de path, orden de iteración).

**Smells:** tautológico / sin assert; mystery guest; eager test (asevera de más);
frágil / sobre-especificado; lógica (`if`/`for`) en el test; ice-cream cone.

**Fixes:** aislar todo estado (tmp dirs, env fresco); inyectar reloj/random; nada de
`sleep` (poll con timeout); semillas deterministas; correr en orden aleatorio
(`pytest-randomly`) para exponer dependencia de orden; cuarentena + arreglo, **nunca**
retry-until-green.

---

## 9. Cobertura (breve)
Statement < branch < condition < **MC-DC** (criterio de aviónica). Mide **ejecución, no
validación**: 100% de cobertura con oráculos vacíos sigue siendo fallo #2. Es métrica de
verificación; nada dice del vértice de negocio.

---

## 10. Estado real de la suite (superficie de V&V)

**Estática: fuerte y a medida** (lo mejor del proyecto):
- `ruff` lint (`validate.yml:24-25`), JSON válido, guarda `! grep ../` de path-traversal.
- Guardas bespoke: `check_suite_versions.py` (sync versión), `check_kb_blank.py`
  (checksum anti-write-back), `check_agents.py` (allowlist read-only), `check_commands.py`
  (**guarda CWE-427**: ningún `plugin.json` con `mcpServers.command` resoluble por PATH).

**Dinámica: sólida donde importa:**
- Los 7 hooks corren por **subprocess real con stdin** y aislamiento de `temp`/`HOME`
  (`conftest.py:19-49`) → muerde el código real, no mockea el sujeto. `run_hook` es un
  **driver**; `tmp_path` es un **fake** del entorno.
- Mezcla de caracterización + tests requisito-derivados de seguridad
  (`test_bridge_security.py:1` — "F1 - Prompt injection de 2do orden").

**Cicatrices de flakiness ya resueltas** (docs de testing): `TMPDIR` vs solo `TEMP`
(flakeaba en CI ubuntu); paths con backslash por `os.name == "nt"`; tamaños de transcript
en bytes exactos (derandomización de borde).

### Registro de gaps (evidencia)
| # | Gap | Evidencia |
|---|-----|-----------|
| G1 | **Sin type-checking** en todo el repo (hints declarados, nada los verifica) | sin mypy/pyright en `pyproject.toml`/CI |
| G2 | **`ruff` incompleto**: no cubre `plugins/memory/` ni `plugins/sentinel-agents/`; sin `ruff format` | `validate.yml:25` |
| G3 | **`check_kb_blank.py` sin test dinámico** (la guarda de la KB no está probada) | no hay test en `tests/` |
| G4 | **Jobs `sentinel-agents` y `suite` no corren ruff ni pytest**; `plugins/memory/scripts/` nunca linteado | `validate.yml:41-75` |
| G5 | **Cero coverage medido, cero mutation testing** — no se sabe si los tests muerden | sin pytest-cov/mutmut |
| G6 | **Agentes/skills solo validados en estructura**, no comportamiento; eval semántica manual/gated, no CI | `tests/sentinel-agents/README.md:3-4` |
| G7 | **Tests de seguridad por ejemplo** (3 paths) donde una propiedad cubriría el dominio | `test_bridge_security.py` |
| G8 | **Sin `pytest-randomly`**: dependencia de orden no se expone | `pyproject.toml` |
| G9 | **Drift documental**: `testing.md` decía "30 tests / 4 hooks" vs 128/7 real (fallo #1 a nivel doc) | `testing.md:9` (histórico) |

### Mapeo a 4D
- **Property testing** → Descripción más fuerte del requisito (todo el dominio).
- **TDD/BDD** → Descripción primero (mata el fallo #1).
- **Mutation / coverage** → Discernimiento sobre los propios tests (mata el fallo #2).
- **Stubs/drivers/V-model** → Delegación correcta (mockeá bordes, no el dominio).
- **Aislamiento / anti-flaky** → Diligencia (un oráculo honesto y trazable).

**Síntesis:** todo PSS es higiene del oráculo — que sea fuerte, honesto y trazable a la
spec. El vértice semántico (prompts de agentes/skills) es irreducible a pytest: se
gobierna con contrato + revisión humana agendada, no con un test determinista.
