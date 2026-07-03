# ai-fluency-4d

Plugin de Claude Code (en español) que lleva a la práctica el marco **4D de AI Fluency**
(Rick Dakan · Joseph Feller · Anthropic): **Delegación, Descripción, Discernimiento y Diligencia**.

## Qué incluye

| Componente | Qué hace |
|-----------|----------|
| **Skill `/4d`** | Guía una tarea por las 4 dimensiones: reparto humano–IA, prompt en 3 niveles (Performance/Process/Product), checklist de evaluación e informe de diligencia. |
| **Skill `/4d-init`** | Analiza tu proyecto y genera un **CLAUDE.md modular**: raíz corta con una tabla de "puentes" a docs por tema (`.claude/docs/auth.md`, `endpoints.md`, ...) más un manifiesto `bridges.json`. |
| **Hook `bridge_router`** | En cada prompt, si mencionás un tema documentado (p. ej. "auth"), inyecta automáticamente la instrucción de leer `.claude/docs/auth.md` antes de responder. Se desactiva solo en proyectos sin puentes. |
| **Hook `discernment_gate`** | Opcional (`FLUENCY_4D_STRICT=1`): antes de terminar una tarea, exige pasar una vez por la checklist de discernimiento. Apagado por defecto. |
| **Hook `memory_checkpoint`** | Al cruzar el **50% de contexto** (configurable, `FLUENCY_4D_SAVE_PCT`), instruye guardar el estado de la sesión en `.claude/docs/estado-sesion.md` y consolidar lecciones. Una vez por sesión. |
| **Autoaprendizaje** | Las correcciones y errores cazados por el Discernimiento se guardan como lecciones en `.claude/docs/lecciones.md`; al arrancar una sesión nueva, el plugin te recuerda leerlas (y retomar `estado-sesion.md` si existe, avisando su antigüedad). |

## Instalación

Requisito: [uv](https://docs.astral.sh/uv/) instalado (los hooks son scripts Python autocontenidos).

```
/plugin marketplace add alexissamudio/ai-fluency-4d
/plugin install fluency-4d@ai-fluency-4d
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

Limitaciones conocidas (v0.2): el checkpoint dispara **una vez por sesión** (no se
re-arma tras una compactación) y requiere una versión de Claude Code que exponga
`context_window.used_percentage` a los hooks.

## Las 4D en una tabla

| D | Pregunta que responde |
|---|----------------------|
| **Delegación** | ¿Qué hago yo y qué la IA? |
| **Descripción** | ¿Cómo le explico lo que quiero? |
| **Discernimiento** | ¿Puedo confiar en lo que me dio? |
| **Diligencia** | ¿Quién se hace responsable del resultado? |

## Desarrollo local

```
git clone https://github.com/alexissamudio/ai-fluency-4d
claude plugin marketplace add <ruta-local-del-repo>
claude plugin install fluency-4d@ai-fluency-4d
```

Los plugins se copian a la caché de Claude Code: tras cada cambio, corré
`claude plugin marketplace update ai-fluency-4d` y abrí una sesión nueva.
Para releases, sincronizá la versión en los 3 lugares con:

```
uv run scripts/bump_version.py --set X.Y.Z
```

## Créditos

- Marco AI Fluency: Rick Dakan (Ringling College) y Joseph Feller (University College Cork),
  en colaboración con Anthropic — curso gratuito en Anthropic Academy.
- Patrón de hooks (`hooks/hook_utils.py`) basado en [oh-my-claude](https://github.com/TechDufus/oh-my-claude) (MIT).

## Licencia

MIT
