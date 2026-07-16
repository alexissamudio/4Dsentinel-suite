# RUBRIC — calidad de prompt de un agente sentinel (meta-review)

Dimensiones para criticar la ficha `.md` de un agente contra el contrato compartido
(`plugins/sentinel-agents/references/agent-contract.md`) + buenas practicas de prompt.
El meta-review del Workflow `agent-improver` produce, por dimension, findings
`{ dimension, weakness, suggestion, severity }` con evidencia `agente.md:linea`.

Regla transversal: la ficha **no debe re-explicar** lo que ya vive en `agent-contract.md`
(evidencia §1, severidad §2, auto-verificacion §3, verdict §4, handoff §5, formato §6). Debe
CITARLO y agregar solo lo especifico del agente. Duplicar teoria del contrato es un defecto
(riesgo de drift entre ficha y contrato).

## Dimensiones

### 1. Cobertura de failure-modes
- **Bien**: enumera las clases de problema que el agente debe cazar, concretas y accionables
  (p.ej. bug-hunter lista off-by-one, null deref, races…). Cubre el espacio del dominio sin huecos obvios.
- **Mal**: lista vaga ("buscar problemas"), o le faltan clases que un experto del dominio esperaria.

### 2. Calibracion de severidad
- **Bien**: usa la escala del contrato §2 EXACTA para su tipo (bug-hunter `Critical|Important|Minor`;
  security CVSS+CWE; critic `Critical|Important|Minor`) y da el criterio de cada nivel en terminos de impacto.
- **Mal**: inventa niveles no contemplados, o no da criterio para separar un nivel de otro (queda a "vibes").

### 3. Fidelidad al contrato de salida (§6 + §4)
- **Bien**: cierra con el bloque `=== SENTINEL-REPORT ===` … `=== END ===` con los campos del §6 y
  un `verdict:` del enum EXACTO de §4 para ese agente. No altera tokens ni nombres de campo.
- **Mal**: cambia el delimitador, omite campos (`status`, `evidence`, `uncertainty`), o usa un verdict
  fuera del enum. Esto rompe el parser/orquestador -> es de las fallas mas graves.

### 4. No-duplicacion del contrato
- **Bien**: cita `agent-contract` para la teoria compartida; el cuerpo agrega solo lo del agente.
- **Mal**: reescribe la regla de evidencia, la de auto-verificacion o la rubrica generica -> drift latente.

### 5. Disciplina de scope
- **Bien**: dice explicitamente que NO es su trabajo y a quien pertenece (bug-hunter: no seguridad
  -> security-auditor; no estilo -> code-reviewer). Reduce solapamiento y ruido entre agentes.
- **Mal**: scope difuso; invita a reportar cosas de otro agente (dobles reportes, ruido).

### 6. Manejo de falsos-positivos / decoys
- **Bien**: exige camino alcanzable entrada->efecto antes de CONFIRMED; un patron sospechoso sin
  camino real es a lo sumo `PLAUSIBLE`. Baja el ruido de falsos-positivos.
- **Mal**: no distingue "patron que parece malo" de "bug/vuln real alcanzable" -> infla falsos-positivos.

### 7. Accionabilidad
- **Bien**: cada finding lleva a una accion concreta (que arreglar / donde). El `summary` es una linea util.
- **Mal**: findings descriptivos sin salida ("hay un problema de logica") que no orientan el fix.

### 8. Claridad e instruccion-following
- **Bien**: instrucciones sin ambiguedad, orden logico, sin contradicciones internas; el agente
  sabe exactamente que hacer y en que orden. Read-only reforzado si corresponde.
- **Mal**: pasos contradictorios, ambiguos, o que dejan al modelo adivinar el procedimiento.

## Uso en el meta-review

El panel de revisores puntua cada dimension y propone la mejora CONCRETA (no "mejorar la cobertura"
sino "agregar la clase X de bug, que hoy no esta, ver linea N"). Esos findings alimentan el
`synthesis`, que los combina con la evidencia de conducta (missed / false_positives del eval) para
proponer el diff. Las dimensiones 3 y 4 son **guardas duras**: una sugerencia que rompa el formato
de salida o el enum de verdict se rechaza en la revision humana (no-regresion de contrato).
