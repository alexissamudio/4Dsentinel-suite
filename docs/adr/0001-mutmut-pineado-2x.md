# 0001. mutmut pineado a 2.x para mutar los hooks-subprocess

- **Estado:** accepted
- **Fecha:** 2026-07-16
- **Deciders:** Alexis Samudio

## Contexto

Los 7 hooks de `fluency-4d` corren por **subprocess** (`uv run --script`): la fixture
`run_hook` (`tests/fluency-4d/hooks/conftest.py`) lanza el hook como proceso hijo y le
pasa el payload por stdin. El mutation testing (F16 de la auditoría 2026-07-15) tiene que
mutar esos hooks de verdad para tener valor: si la mutación no llega al archivo que el
subprocess ejecuta, todos los mutantes "sobreviven" falsamente y el score es basura.

`mutmut` cambió de mecanismo entre majors:

- **2.x** muta el archivo **in-place en disco**; el subprocess `uv run --script` lee la
  versión mutada al arrancar → la mutación llega al código que realmente se ejecuta.
- **3.x** copia el fuente a un directorio aislado `mutants/` y corre ahí. El subprocess
  de `run_hook` abre la ruta **absoluta real** del hook (no la copia), así que leería el
  fuente **sin mutar** → mutantes vivos falsos.

## Decisión

Pineamos **`mutmut==2.5.1`** en el nightly `mutation.yml`.

Es una versión más vieja y menos mantenida que la 3.x, pero es la única que, con la
invocación actual de los hooks (`uv run --script` sobre la ruta real), muta el código que
el subprocess ejecuta. Adoptar 3.x exigiría reconfigurar la fixture para que el subprocess
lea la copia de `mutants/` — más trabajo, más acoplamiento a un detalle interno de mutmut,
y sin beneficio para este caso de uso.

Verificado en WSL sobre `check_kb_blank.py`: 27/55 mutantes muertos (el mutante de lógica
real `not in` → `in` muere; los sobrevivientes son strings de mensajes / equivalentes).

## Consecuencias

- **A favor:** el nightly muta los hooks-subprocess de verdad; el mutation score es real.
- **En contra / deuda:** quedamos en una major vieja de mutmut. Si 2.x deja de instalar o
  de correr en un Python futuro, hay que (a) migrar a 3.x reconfigurando la fixture para
  leer de `mutants/`, o (b) reemplazar la herramienta. Este ADR es el punto de partida de
  esa futura decisión.
- El pin vive en `.github/workflows/mutation.yml`; el mecanismo está documentado en
  `.claude/docs/pss.md` sec 7 y `release.md`.
