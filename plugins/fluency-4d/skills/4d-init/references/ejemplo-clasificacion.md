# Ejemplo: clasificar reglas-siempre vs conocimiento-por-tema

Caso ilustrativo (un monorepo TypeScript con API + frontend). NO es un stack
específico: muestra cómo aplicar la regla de decisión sección por sección.
Recordá la regla: es **regla-siempre** sii es imperativa/prohibitiva Y un revisor
marcaría su violación en un diff SIN saber qué feature implementa. Ante la duda,
inline.

## Contenido de origen (un CLAUDE.md monolítico típico)

Secciones que suele traer: arquitectura de módulos, ubicaciones compartidas,
sistema de diseño (tokens de color, tipografía), backend (ORM, auth, storage),
estilo de código (early returns, manejo de errores, fallbacks), y una lista de
"no hacer".

## Cómo se parte

| Contenido de origen | Clasificación | Destino |
|---------------------|---------------|---------|
| "SIEMPRE early returns; NUNCA if/else anidado" | Regla | inline |
| "NUNCA throw fuera de la capa de data; en el resto try/catch + toast" | Regla | inline |
| "NUNCA `?? []` que oculte data faltante; early return para vacíos" | Regla | inline |
| "Componentes en orden error → loading → empty → data" | Regla | inline |
| "Sin dark mode; primary SIEMPRE neutro, nunca color de marca" | Regla | inline |
| "Solo la librería de componentes; NUNCA botones/inputs manuales" | Regla | inline |
| "Tipos en `module/types.ts`, NUNCA inline (salvo Props)" | Regla | inline |
| "Sin emojis en código/UI; NO sobre-ingeniería" | Regla | inline |
| Estructura de módulos: qué carpeta contiene qué | Tema | `arquitectura.md` |
| Ubicaciones compartidas (dónde vive cada helper) | Tema | `arquitectura.md` |
| Tabla de tokens de color con sus valores hex | Tema | `design.md` |
| Tipografía, spacing, radius concretos | Tema | `design.md` |
| ORM, decoradores de auth, storage, rate limiting | Tema | `backend.md` |

## El caso que se PARTE (ojo con estos)

"Usá la capa X para el estado de servidor" mezcla regla y tema:

- **Imperativo** ("el estado de servidor va por la capa de data, nunca fetch
  crudo en componentes") → **regla**, inline.
- **Configuración** (cómo se arma el cliente, opciones de caché, claves) →
  **tema**, va a `backend.md` o `arquitectura.md`.

## Resultado

- El bloque centinela del CLAUDE.md queda con ~8 reglas inline (siempre cargadas)
  + una tabla de 3 puentes.
- El detalle pesado (valores de tokens, ejemplos bien/mal de manejo de errores,
  las ubicaciones compartidas) baja a los docs, que solo se cargan al tocar su
  tema.
- Una regla no negociable como "sin dark mode" NUNCA queda escondida detrás de la
  keyword "diseño": está inline, se respeta aunque el prompt no mencione estilo.

## Por qué importa

Si "sin dark mode" o "early returns" vivieran solo en `convenciones.md` (gated por
la keyword "convenciones/estilo/lint"), Claude NO los cargaría al escribir, p. ej.,
un endpoint de auth — y los violaría sin saberlo. Inline garantiza que las reglas
no negociables estén presentes en cada tarea de código.
