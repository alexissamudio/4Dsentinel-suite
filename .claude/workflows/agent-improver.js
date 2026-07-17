export const meta = {
  name: 'agent-improver',
  description: 'Mide y mejora los prompts de los agentes sentinel: eval de conducta (catch-rate sobre casos golden) + meta-review vs contrato/rubrica -> propone diffs; loop-until-dry. El conductor revisa/aplica via PR.',
  whenToUse: 'Cuando queres mejorar los prompts de sentinel-agents con evidencia. args: {targets:[...], rounds, reps}. Propone diffs; NO auto-edita.',
  phases: [
    { title: 'Load' },
    { title: 'Baseline' },
    { title: 'Meta-review' },
    { title: 'Synthesis' },
    { title: 'Candidate' },
  ],
}

// ------------------------------------------------------------------ constantes
const MARGIN = 0.05 // el candidato debe superar al baseline por >=5 puntos de catch-rate

// -------------------------------------------------------------------- schemas
const LOAD_SCHEMA = {
  type: 'object',
  required: ['agentFileFull', 'cases'],
  properties: {
    agentFileFull: { type: 'string', description: 'texto EXACTO y completo de la ficha .md, con frontmatter' },
    cases: {
      type: 'array',
      items: {
        type: 'object',
        required: ['caseId', 'inputs', 'must_catch', 'decoys'],
        properties: {
          caseId: { type: 'string' },
          inputs: {
            type: 'array',
            items: {
              type: 'object',
              required: ['name', 'content'],
              properties: { name: { type: 'string' }, content: { type: 'string' } },
            },
          },
          must_catch: {
            type: 'array',
            items: {
              type: 'object',
              required: ['id', 'where', 'why'],
              properties: { id: { type: 'string' }, where: { type: 'string' }, why: { type: 'string' } },
            },
          },
          decoys: {
            type: 'array',
            items: {
              type: 'object',
              required: ['where', 'why'],
              properties: { where: { type: 'string' }, why: { type: 'string' } },
            },
          },
        },
      },
    },
  },
}

const FINDINGS_SCHEMA = {
  type: 'object',
  required: ['findings'],
  properties: {
    findings: {
      type: 'array',
      items: {
        type: 'object',
        required: ['where', 'severity', 'status', 'summary'],
        properties: {
          where: { type: 'string', description: 'archivo:linea' },
          severity: { type: 'string' },
          status: { type: 'string', enum: ['CONFIRMED', 'PLAUSIBLE'] },
          summary: { type: 'string' },
        },
      },
    },
  },
}

const JUDGE_SCHEMA = {
  type: 'object',
  required: ['caught', 'missed', 'false_positives'],
  properties: {
    caught: { type: 'array', items: { type: 'string' }, description: 'ids de must_catch cazados' },
    missed: { type: 'array', items: { type: 'string' }, description: 'ids de must_catch NO cazados' },
    false_positives: { type: 'array', items: { type: 'string' }, description: 'wheres reportados que son decoy o invento' },
  },
}

const META_SCHEMA = {
  type: 'object',
  required: ['findings'],
  properties: {
    findings: {
      type: 'array',
      items: {
        type: 'object',
        required: ['dimension', 'weakness', 'suggestion', 'severity', 'evidence'],
        properties: {
          dimension: { type: 'string' },
          weakness: { type: 'string' },
          suggestion: { type: 'string' },
          severity: { type: 'string', enum: ['Critical', 'Important', 'Minor'] },
          evidence: { type: 'string', description: 'agente.md:linea' },
        },
      },
    },
  },
}

const SYNTH_SCHEMA = {
  type: 'object',
  required: ['candidateFileFull', 'diff', 'rationale'],
  properties: {
    candidateFileFull: { type: 'string', description: 'ficha .md candidata COMPLETA (con frontmatter intacto)' },
    diff: { type: 'string', description: 'diff unificado minimo contra la ficha actual' },
    rationale: { type: 'string' },
  },
}

// ------------------------------------------------------------------- helpers
// Separa el frontmatter YAML (--- ... ---) del cuerpo (el system prompt real).
function deriveBody(full) {
  const m = full.match(/^---\n[\s\S]*?\n---\n?/)
  return m ? full.slice(m[0].length) : full
}

function rolePlayPrompt(body, c, target, rep) {
  const material = c.inputs
    .map((f) => `--- archivo: ${f.name} ---\n${f.content}`)
    .join('\n\n')
  return `Vas a ACTUAR como un agente de revision cuyo prompt de sistema es EXACTAMENTE el delimitado abajo. Segui SUS instrucciones para analizar el material, con estas RESTRICCIONES DURAS del entorno de evaluacion:
- Sos READ-ONLY: NO ejecutes codigo, NO edites archivos, NO uses shell. Razonas ESTATICAMENTE sobre el material provisto (igual que el agente real, que solo tiene Read/Grep/Glob).
- Analiza SOLO el material de abajo; no inventes archivos que no esten.
- Devolve tus hallazgos EN EL SCHEMA pedido (no el bloque === SENTINEL-REPORT ===; el schema captura los mismos campos).

=== SYSTEM PROMPT DEL AGENTE (${target}) ===
${body}
=== FIN SYSTEM PROMPT ===

=== MATERIAL A ANALIZAR (caso ${c.caseId}) ===
${material}
=== FIN MATERIAL ===

(pasada de evaluacion ${rep}) Reporta cada problema REAL que encuentres, uno por finding: where (archivo:linea del material), severity (segun la rubrica del propio agente), status (CONFIRMED si re-leiste y lo sostenes; PLAUSIBLE si no), summary (una linea). Respeta el scope del agente y su disciplina de falsos-positivos: un patron sospechoso sin camino real alcanzable NO es un hallazgo CONFIRMED.`
}

function judgePrompt(c, findings) {
  const mc = c.must_catch.map((m) => `- id=${m.id} @ ${m.where}: ${m.why}`).join('\n')
  const dc = c.decoys.length
    ? c.decoys.map((d) => `- @ ${d.where}: ${d.why}`).join('\n')
    : '(ninguno)'
  const fs = findings.length
    ? findings.map((f) => `- @ ${f.where} [${f.severity}/${f.status}]: ${f.summary}`).join('\n')
    : '(ninguno)'
  return `Sos un evaluador determinista. Compara los HALLAZGOS de un agente contra el GROUND TRUTH de un caso. No premies ni castigues wording; juzga por semantica y ubicacion.

GROUND TRUTH (caso ${c.caseId})
must_catch (problemas que DEBIA cazar):
${mc}
decoys (NO son problemas; reportarlos = falso positivo):
${dc}

HALLAZGOS DEL AGENTE:
${fs}

Reglas de matcheo:
- Un must_catch esta "caught" si algun hallazgo apunta al MISMO problema: misma linea aprox (+-3) Y misma causa semantica que el 'why'. No exijas linea exacta ni el mismo wording.
- Un decoy es "false_positive" si algun hallazgo lo reporta como problema (usa el where del decoy).
- Un hallazgo que no matchea ningun must_catch ni decoy es ruido neutro y se IGNORA, salvo que claramente invente un bug donde no hay ninguno: en ese caso es false_positive (usa el where del hallazgo).

Devolve: caught (ids de must_catch cazados), missed (ids no cazados), false_positives (wheres).`
}

function metaPrompt(target, reviewer) {
  return `Sos un revisor critico de la CALIDAD DEL PROMPT de un agente sentinel (revisor #${reviewer}). Trabajas read-only.

Leé estos 3 archivos del repo (con Read):
1. La ficha del agente: plugins/sentinel-agents/agents/${target}.md
2. El contrato compartido: plugins/sentinel-agents/references/agent-contract.md
3. La rubrica: tests/agent-evals/RUBRIC.md

Evalua la ficha del agente '${target}' contra las 8 dimensiones de la RUBRIC. Por cada debilidad CONCRETA, un finding: dimension, weakness (que falta o esta mal, con evidencia ${target}.md:linea), suggestion (mejora concreta y aplicable AL TEXTO del prompt; ej: "agregar la clase X de bug en la lista de la linea N", no "mejorar cobertura"), severity (Critical|Important|Minor), evidence (${target}.md:linea).

GUARDAS DURAS (no las violes en tus sugerencias): NO propongas cambiar el delimitador === SENTINEL-REPORT === / === END ===, sus campos (§6), ni el enum de verdict del agente (§4). Tampoco propongas duplicar teoria que ya vive en agent-contract.md (dimension 4): si algo ya esta en el contrato, la ficha debe CITARLO, no reescribirlo.`
}

function synthPrompt(target, currentFull, missed, falsePositives, meta) {
  const missedTxt = missed.length
    ? missed.map((m) => `- [${m.caseId}] ${m.id} @ ${m.where}: ${m.why}`).join('\n')
    : '(el baseline no perdio ningun must_catch)'
  const fpTxt = falsePositives.length
    ? falsePositives.map((w) => `- ${w}`).join('\n')
    : '(el baseline no genero falsos positivos)'
  const metaTxt = meta.length
    ? meta
        .map((f) => `- [${f.severity}] ${f.dimension} (${f.evidence}): ${f.weakness} -> ${f.suggestion}`)
        .join('\n')
    : '(sin findings de meta-review)'
  return `Sos un ingeniero de prompts. Proponé una version MEJORADA de la ficha del agente sentinel '${target}', con evidencia de dos fuentes.

FICHA ACTUAL (completa, con frontmatter):
<<<FICHA
${currentFull}
FICHA

EVIDENCIA DE CONDUCTA (del eval sobre casos golden):
- must_catch PERDIDOS por el baseline (deberia cazarlos y no lo hizo):
${missedTxt}
- FALSOS POSITIVOS del baseline (reporto cosas que no eran problema):
${fpTxt}

EVIDENCIA DE META-REVIEW (calidad de prompt vs contrato + rubrica):
${metaTxt}

Tu tarea: reescribir el CUERPO de la ficha para que el agente cace lo que perdio y evite los falsos positivos, incorporando las sugerencias de meta-review pertinentes. Restricciones INNEGOCIABLES (las valida check_agents.py y el conductor):
- Mantene el frontmatter EXACTO (name, description, model: inherit, tools, maxTurns, color): no cambies tools ni model.
- El cuerpo DEBE seguir citando 'agent-contract' (referencia al contrato compartido).
- NO cambies el bloque de salida === SENTINEL-REPORT === / === END === ni sus campos, ni el enum de verdict del agente.
- NO dupliques teoria que ya vive en agent-contract.md: cita, no reescribas.
- Cambio MINIMO y quirurgico: toca solo lo que la evidencia justifica.

Devolve: candidateFileFull (la ficha .md completa nueva, frontmatter intacto), diff (unificado, minimo, contra la ficha actual) y rationale (por que cada cambio, ligado a la evidencia).`
}

// Evalua un cuerpo sobre todos los casos, `reps` veces. Devuelve un array por rep:
// [{ rate, fp, missed: [{caseId,id,where,why}] }]
async function evalBody(body, cases, reps, target, tag) {
  const perRep = await parallel(
    Array.from({ length: reps }, (_, r) => async () => {
      const caseResults = await parallel(
        cases.map((c) => async () => {
          const rp = await agent(rolePlayPrompt(body, c, target, r), {
            schema: FINDINGS_SCHEMA,
            phase: tag === 'base' ? 'Baseline' : 'Candidate',
            label: `${tag}:${target}:${c.caseId}:r${r}`,
          })
          if (!rp) return null
          const jg = await agent(judgePrompt(c, rp.findings), {
            schema: JUDGE_SCHEMA,
            effort: 'low',
            phase: tag === 'base' ? 'Baseline' : 'Candidate',
            label: `judge:${tag}:${target}:${c.caseId}:r${r}`,
          })
          if (!jg) return null
          const missed = (jg.missed || []).map((id) => {
            const m = c.must_catch.find((x) => x.id === id) || {}
            return { caseId: c.caseId, id, where: m.where || '?', why: m.why || '' }
          })
          return {
            caught: (jg.caught || []).length,
            total: c.must_catch.length,
            fp: (jg.false_positives || []).length,
            missed,
          }
        })
      )
      const ok = caseResults.filter(Boolean)
      const caught = ok.reduce((s, x) => s + x.caught, 0)
      const total = ok.reduce((s, x) => s + x.total, 0)
      const fp = ok.reduce((s, x) => s + x.fp, 0)
      const missed = ok.flatMap((x) => x.missed)
      return { rate: total ? caught / total : 0, fp, missed }
    })
  )
  return perRep.filter(Boolean)
}

function avg(xs) {
  return xs.length ? xs.reduce((s, x) => s + x, 0) / xs.length : 0
}

// Une los missed de todas las reps sin duplicar (por caseId+id).
function unionMissed(perRep) {
  const seen = new Set()
  const out = []
  for (const rep of perRep) {
    for (const m of rep.missed) {
      const k = `${m.caseId}::${m.id}`
      if (!seen.has(k)) {
        seen.add(k)
        out.push(m)
      }
    }
  }
  return out
}

// ------------------------------------------------------------- accept-gate
// Decision PURA de aceptacion del candidato vs baseline. Sin efectos, sin API:
// solo aritmetica sobre las tasas por rep + los conteos de falsos positivos.
// Extraida de runRound para poder testearla offline (ver
// tests/workflows/agent-improver.test.js). Semantica EXACTA (no cambiar):
//  (A) RECALL: el candidato sube el catch-rate por MARGIN en la MAYORIA de reps
//      y no empeora FP.
//  (B) PRECISION: cuando el recall ya esta al techo (o no puede subir), aceptar
//      si MANTIENE el recall en la mayoria de reps y BAJA los falsos positivos.
//      Sin esta via, una mejora real de precision (menos FP a igual catch)
//      quedaba descartada (caso critic del piloto).
function acceptGate({ baseRates, candRates, baseFpCount, candFpCount }) {
  // pareo por rep: cuantas reps mejoran el catch-rate por MARGIN, y en cuantas no lo degradan.
  const n = Math.min(baseRates.length, candRates.length)
  let winReps = 0
  let heldReps = 0
  for (let i = 0; i < n; i++) {
    const d = candRates[i] - baseRates[i]
    if (d > MARGIN) winReps++
    if (d >= -1e-9) heldReps++
  }
  const fpOk = candFpCount <= baseFpCount + 1e-9
  const fpImproved = candFpCount < baseFpCount - 1e-9
  const recallHeld = heldReps > n / 2
  const acceptedByRecall = winReps > n / 2 && fpOk
  const acceptedByPrecision = recallHeld && fpImproved
  const accepted = acceptedByRecall || acceptedByPrecision
  const via = acceptedByRecall ? 'RECALL' : acceptedByPrecision ? 'PRECISION' : null
  return { accepted, via, winReps, heldReps, reps: n }
}

// -------------------------------------------------------------- una ronda
async function runRound(target, currentFull, cases, reps) {
  const currentBody = deriveBody(currentFull)

  // 1) Baseline eval (evidencia de conducta + rate base)
  const baseReps = await evalBody(currentBody, cases, reps, target, 'base')
  const baseRates = baseReps.map((r) => r.rate)
  const baseFps = baseReps.map((r) => r.fp)
  const baseRate = avg(baseRates)
  const missed = unionMissed(baseReps)
  // evalBody agrega la CANTIDAD de falsos positivos por rep (JUDGE da wheres; para el brief
  // del synthesis basta la senal de cuantos hubo por rep).
  const baseFpCount = avg(baseFps)

  // 2) Meta-review (panel de 3 revisores independientes)
  const metaResults = await parallel(
    [1, 2, 3].map((i) => () =>
      agent(metaPrompt(target, i), {
        schema: META_SCHEMA,
        agentType: 'general-purpose',
        phase: 'Meta-review',
        label: `meta:${target}:rev${i}`,
      })
    )
  )
  const metaFindings = metaResults.filter(Boolean).flatMap((m) => m.findings)

  // 3) Synthesis (propone ficha candidata + diff)
  const synth = await agent(
    synthPrompt(target, currentFull, missed, baseFps.map((n) => `~${n} fp/rep`), metaFindings),
    { schema: SYNTH_SCHEMA, phase: 'Synthesis', label: `synth:${target}` }
  )
  if (!synth) {
    return { accepted: false, reason: 'synthesis fallo', baseRate, metaFindings }
  }

  // 4) Candidate eval (MISMO host/encuadre que el baseline) + select por delta
  const candBody = deriveBody(synth.candidateFileFull)
  const candReps = await evalBody(candBody, cases, reps, target, 'cand')
  const candRates = candReps.map((r) => r.rate)
  const candFps = candReps.map((r) => r.fp)
  const candRate = avg(candRates)
  const candFpCount = avg(candFps)

  // pareo por rep + decision de aceptacion: delegado a acceptGate() (funcion pura,
  // misma semantica, testeada offline en tests/workflows/agent-improver.test.js).
  const { accepted, via, winReps, heldReps, reps: n } = acceptGate({
    baseRates,
    candRates,
    baseFpCount,
    candFpCount,
  })

  return {
    accepted,
    via,
    reason: accepted
      ? `aceptado via ${via}: win ${winReps}/${n} reps, held ${heldReps}/${n}, fp base=${baseFpCount.toFixed(2)} cand=${candFpCount.toFixed(2)}`
      : `no aceptado (win ${winReps}/${n}, held ${heldReps}/${n}, fp base=${baseFpCount.toFixed(2)} cand=${candFpCount.toFixed(2)})`,
    baseRate,
    candRate,
    deltaCatch: candRate - baseRate,
    deltaFp: candFpCount - baseFpCount,
    winReps,
    reps: n,
    diff: synth.diff,
    rationale: synth.rationale,
    candidateFileFull: synth.candidateFileFull,
    metaFindings,
    missed,
  }
}

// ------------------------------------------------- ronda meta-review-only
// Para agentes que NO encajan en el eval de deteccion sobre material estatico
// (validator/debugger necesitan Bash; librarian extrae, no caza; risk-assessor da
// un verdict escalar). Corre SOLO meta-review + synthesis (sin baseline/candidate
// eval): el reviewDiff queda para revision humana; no hay delta que auto-aceptar.
async function runMetaOnly(target, currentFull) {
  const metaResults = await parallel(
    [1, 2, 3].map((i) => () =>
      agent(metaPrompt(target, i), {
        schema: META_SCHEMA,
        agentType: 'general-purpose',
        phase: 'Meta-review',
        label: `meta:${target}:rev${i}`,
      })
    )
  )
  const metaFindings = metaResults.filter(Boolean).flatMap((m) => m.findings)
  const synth = await agent(synthPrompt(target, currentFull, [], [], metaFindings), {
    schema: SYNTH_SCHEMA,
    phase: 'Synthesis',
    label: `synth:${target}`,
  })
  return {
    accepted: false,
    metaOnly: true,
    reason: 'meta-review-only (sin casos golden): reviewDiff para revision humana',
    baseRate: null,
    metaFindings,
    diff: synth ? synth.diff : null,
    rationale: synth ? synth.rationale : 'synthesis fallo',
    candidateFileFull: synth ? synth.candidateFileFull : null,
  }
}

// --------------------------------------------------------------- por agente
async function improveAgent(target, rounds, reps) {
  phase('Load')
  const loaded = await agent(loadPrompt(target), {
    schema: LOAD_SCHEMA,
    agentType: 'general-purpose',
    phase: 'Load',
    label: `load:${target}`,
  })
  if (!loaded || !loaded.agentFileFull) {
    return { target, error: 'no se pudo cargar la ficha del agente' }
  }

  let currentFull = loaded.agentFileFull
  const cases = loaded.cases || []
  const history = []
  let changed = false

  // Sin casos golden -> modo meta-review-only (una pasada, sin eval/loop).
  if (!cases.length) {
    log(`[${target}] sin casos golden -> meta-review-only`)
    const res = await runMetaOnly(target, currentFull)
    history.push({
      round: 1,
      accepted: false,
      metaOnly: true,
      via: null,
      reason: res.reason,
      baseRate: null,
      candRate: null,
      deltaCatch: null,
      deltaFp: null,
      diff: res.diff,
      rationale: res.rationale,
      metaFindings: res.metaFindings,
    })
    return {
      target,
      baselineRate: null,
      metaOnly: true,
      changed: false,
      finalFileFull: null,
      rounds: history,
    }
  }

  for (let round = 0; round < rounds; round++) {
    log(`[${target}] ronda ${round + 1}/${rounds}`)
    const res = await runRound(target, currentFull, cases, reps)
    history.push({
      round: round + 1,
      accepted: res.accepted,
      via: res.via || null,
      reason: res.reason,
      baseRate: res.baseRate,
      candRate: res.candRate,
      deltaCatch: res.deltaCatch,
      deltaFp: res.deltaFp,
      diff: res.diff,
      rationale: res.rationale,
      metaFindings: res.metaFindings,
    })
    if (res.accepted) {
      currentFull = res.candidateFileFull
      changed = true
      log(`[${target}] ronda ${round + 1}: candidato ACEPTADO (delta ${res.deltaCatch.toFixed(2)})`)
    } else {
      log(`[${target}] ronda ${round + 1}: sin mejora -> loop-until-dry corta`)
      break
    }
  }

  return {
    target,
    baselineRate: history.length ? history[0].baseRate : null,
    changed,
    finalFileFull: changed ? currentFull : null,
    rounds: history,
  }
}

function loadPrompt(target) {
  return `Read-only. Recopila el material de evaluacion del agente '${target}' del repo 4Dsentinel-suite.

1. Lee su ficha COMPLETA: plugins/sentinel-agents/agents/${target}.md -> devolvela textual en agentFileFull (con frontmatter incluido, sin recortar).
2. Lista las carpetas de caso en tests/agent-evals/${target}/ (case-NN). Para CADA caso:
   - Lee expected.json -> extrae must_catch y decoys tal cual.
   - Lee TODOS los archivos bajo su input/ (recursivo). Por cada archivo: name = ruta relativa a input/ (ej "buggy_snippet.py" o "repo/app.py"), content = su texto EXACTO y completo.
   Si la carpeta tests/agent-evals/${target}/ NO existe o no tiene casos, devolve cases: [] (lista vacia). Es valido: ese agente corre en modo meta-review-only.
3. Devolve el schema. NO resumas ni recortes: el content de cada input y la ficha deben ir textuales (otro agente los va a analizar byte a byte).`
}

// ------------------------------------------------------------------- main
// `args` puede llegar como objeto o, segun como se invoque, como string JSON: normalizar.
let cfg = args
if (typeof cfg === 'string') {
  try {
    cfg = JSON.parse(cfg)
  } catch (e) {
    cfg = {}
  }
}
if (!cfg || typeof cfg !== 'object') cfg = {}

const targets =
  cfg.targets && cfg.targets.length ? cfg.targets : ['bug-hunter', 'security-auditor', 'critic']
const rounds = cfg.rounds ? cfg.rounds : 2
const reps = cfg.reps ? cfg.reps : 3

log(`agent-improver: targets=[${targets.join(', ')}] rounds=${rounds} reps=${reps}`)

const results = await parallel(targets.map((t) => () => improveAgent(t, rounds, reps)))

const report = results.filter(Boolean).map((r) => ({
  target: r.target,
  error: r.error || null,
  metaOnly: r.metaOnly || false,
  baselineRate: r.baselineRate,
  changed: r.changed,
  rounds: (r.rounds || []).map((rd) => ({
    round: rd.round,
    accepted: rd.accepted,
    via: rd.via,
    reason: rd.reason,
    baseRate: rd.baseRate,
    candRate: rd.candRate,
    deltaCatch: rd.deltaCatch,
    deltaFp: rd.deltaFp,
    rationale: rd.rationale,
    diff: rd.diff,
    metaFindings: rd.metaFindings,
  })),
  // El diff del ULTIMO candidato aceptado por el gate (el que se aplicaria en el loop).
  proposedDiff:
    (r.rounds || []).filter((rd) => rd.accepted).map((rd) => rd.diff).slice(-1)[0] || null,
  // El diff de la PRIMERA ronda SIEMPRE (aceptado o no): el conductor lo revisa a mano aunque el
  // gate automatico no lo haya aceptado (p.ej. mejora de calidad sin delta de catch-rate medible).
  reviewDiff: (r.rounds || [])[0] ? (r.rounds || [])[0].diff : null,
  finalFileFull: r.finalFileFull || null,
}))

return report
