# ai-fluency-4d

[![validate](https://github.com/alexissamudio/4Dsentinel-suite/actions/workflows/validate.yml/badge.svg)](https://github.com/alexissamudio/4Dsentinel-suite/actions/workflows/validate.yml)

Plugin de Claude Code (en español) que lleva a la práctica el marco **4D de AI Fluency**
(Rick Dakan · Joseph Feller · Anthropic): **Delegación, Descripción, Discernimiento y Diligencia**.

## Qué incluye

| Componente | Qué hace |
|-----------|----------|
| **Skill `/4d`** | Guía una tarea por las 4 dimensiones: reparto humano–IA, prompt en 3 niveles (Performance/Process/Product), checklist de evaluación e informe de diligencia. |
| **Skill `/4d-init`** | Analiza tu proyecto y genera un **CLAUDE.md modular**: raíz corta con una tabla de "puentes" a docs por tema (`.claude/docs/auth.md`, `endpoints.md`, ...) más un manifiesto `bridges.json`. |
| **Hook `bridge_router`** | En cada prompt, si mencionás un tema documentado (p. ej. "auth"), inyecta automáticamente la instrucción de leer `.claude/docs/auth.md` antes de responder. Se desactiva solo en proyectos sin puentes. |
| **Hook `discernment_gate`** | Opcional (`FLUENCY_4D_STRICT=1`): antes de terminar una tarea, exige pasar una vez por la checklist de discernimiento. Apagado por defecto. |
| **Hook `memory_checkpoint`** | ~Cada **50% de contexto** (configurable, `FLUENCY_4D_SAVE_PCT`), instruye guardar el estado de la sesión en `.claude/docs/estado-sesion.md` y consolidar lecciones. Se re-arma: por caída de porcentaje (compactación, modo nativo) o por intervalo de tokens acumulados (modo estimación por transcript). |
| **Hook `doc_drift`** | Si editás archivos bajo las `rutas` de un tema documentado (p. ej. `src/auth/`), te recuerda revisar el doc del tema al terminar. Una vez por tema por sesión. |
| **Skill `/4d-status`** | Reporte de solo lectura: temas puenteados, temas sin `rutas`, lecciones vs límite de 30, edad del estado de sesión, convenciones, **puentes nunca usados** (métricas) y **docs que quedaron detrás del código** (por fecha de commit). |
| **Skill `/4d-quiz`** | Practicá la certificación AI Fluency: 24 preguntas de opción múltiple del marco 4D con corrección explicada, puntaje y detección de secciones débiles. `/4d-quiz [n]` (default 10). |
| **Skill `/adhd`** | Modo de comunicación accionable y estructurado, opt-in: arranca por la acción, numera pasos, termina con un next-step concreto. Nivel AUTO que calibra por turno (más estructura en tareas multi-paso, mínimo en consultas cortas). Mutuamente excluyente con el modo token-eficiente (`/caveman`); lo reinyecta el hook `adhd_injector` cada turno. |
| **`convenciones.md`** | `/4d-init` SIEMPRE genera un doc de style guidelines del proyecto (naming, formato, linters); si hay poca evidencia lo marca honestamente (`evidence: low`). |
| **Reglas-siempre inline** | `/4d-init` separa las **reglas no negociables** (early returns, manejo de errores, prohibiciones de estilo) del conocimiento-por-tema: las reglas van inline en el CLAUDE.md (cargadas en TODA sesión), el detalle a docs con puente. Una regla no negociable nunca queda escondida detrás de un keyword. Clasificación confirmada por vos vía multiSelect. |
| **Autoaprendizaje** | Las correcciones y errores cazados por el Discernimiento se guardan como lecciones en `.claude/docs/lecciones.md`; al arrancar una sesión nueva, el plugin te recuerda leerlas (y retomar `estado-sesion.md` si existe, avisando su antigüedad). |

## Instalación

Requisito: [uv](https://docs.astral.sh/uv/) instalado (los hooks son scripts Python autocontenidos).

```
/plugin marketplace add alexissamudio/4Dsentinel-suite
/plugin install fluency-4d@4Dsentinel-suite
```

## Uso

1. En un proyecto, corré `/4d-init`. El plugin explora el código, te propone los temas
   detectados (auth, endpoints, base de datos...), y genera:
   - `CLAUDE.md` con la tabla de puentes (entre marcadores `<!-- BEGIN/END 4D-BRIDGES -->`,
     sin tocar el resto del archivo; backup previo en `.claude/backups/`).
   - `.claude/docs/<tema>.md` por cada tema, con frontmatter de trazabilidad.
   - `.claude/docs/bridges.json` (tema → keywords → archivo) que usa el hook.
2. En una sesión nueva, preguntá por ejemplo "¿cómo funciona el auth?" — el hook detecta
   la keyword y Claude lee `auth.md` antes de responder.
3. Para tareas grandes, invocá `/4d` y dejate guiar por las 4 dimensiones.
4. Trabajá normal: al cruzar el 50% de contexto el plugin dispara el checkpoint de
   memoria (estado + lecciones), y en la próxima sesión te recuerda retomarlos.

## Variables de entorno

| Variable | Default | Efecto |
|----------|---------|--------|
| `FLUENCY_4D_SAVE_PCT` | `50` | Umbral de contexto del checkpoint de memoria; `0` lo desactiva. |
| `FLUENCY_4D_STRICT` | (apagada) | `1` activa el gate de discernimiento al terminar tareas. |

Notas (v0.3): el checkpoint usa `context_window.used_percentage` si tu versión de
Claude Code lo expone; si no, estima por el tamaño del transcript (conservador y
aproximado: "~cada 50%" puede llegar un poco antes). Los proyectos inicializados con
v0.2 no tienen `rutas` en su bridges.json: el aviso de doc desactualizado queda
inactivo hasta re-correr `/4d-init`.

## Las 4D en una tabla

| D | Pregunta que responde |
|---|----------------------|
| **Delegación** | ¿Qué hago yo y qué la IA? |
| **Descripción** | ¿Cómo le explico lo que quiero? |
| **Discernimiento** | ¿Puedo confiar en lo que me dio? |
| **Diligencia** | ¿Quién se hace responsable del resultado? |

## Desarrollo local

```
git clone https://github.com/alexissamudio/4Dsentinel-suite
claude plugin marketplace add <ruta-local-del-repo>
claude plugin install fluency-4d@4Dsentinel-suite
```

Los plugins se copian a la caché de Claude Code: tras cada cambio, corré
`claude plugin marketplace update 4Dsentinel-suite` y abrí una sesión nueva.
Para releases, sincronizá la versión en los 3 lugares con:

```
uv run scripts/fluency_bump_version.py --set X.Y.Z
```

## Créditos

- Marco AI Fluency: Rick Dakan (Ringling College) y Joseph Feller (University College Cork),
  en colaboración con Anthropic — curso gratuito en Anthropic Academy.
- Patrón de hooks (`hooks/hook_utils.py`) basado en [oh-my-claude](https://github.com/TechDufus/oh-my-claude) (MIT).

## Licencia

MIT
