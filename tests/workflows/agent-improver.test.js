// Selftest offline del accept-gate de .claude/workflows/agent-improver.js.
//
// El motor de workflow no se puede importar directamente: coexisten `export
// const meta` (ESM), top-level `await` (ESM) y un `return report` al final
// (ilegal en ESM puro) -> el runtime lo transforma; Node no lo carga como
// modulo. Para NO tocar como carga el motor (cero riesgo en produccion) el
// motor deja acceptGate como funcion LOCAL (sin export). Este test lee el
// fuente, extrae MARGIN + la funcion acceptGate y la reconstruye con
// `new Function`: asi ejercita la funcion REAL de produccion (sin duplicar
// logica ni riesgo de drift) y sin gastar API.
//
// Correr:  node --test tests/workflows/agent-improver.test.js

import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'

const here = dirname(fileURLToPath(import.meta.url))
const enginePath = resolve(here, '..', '..', '.claude', 'workflows', 'agent-improver.js')
const src = readFileSync(enginePath, 'utf8')

// Extrae la constante MARGIN y el cuerpo de acceptGate del fuente del motor.
const marginMatch = src.match(/const MARGIN = ([0-9.]+)/)
assert.ok(marginMatch, 'no se encontro la constante MARGIN en el motor')
const MARGIN = Number(marginMatch[1])

const fnMatch = src.match(/\nfunction acceptGate[\s\S]*?\n\}/)
assert.ok(fnMatch, 'no se encontro la funcion acceptGate en el motor')

// Reconstruye la funcion pura con su dependencia (MARGIN) en scope.
const acceptGate = new Function(`const MARGIN = ${MARGIN};${fnMatch[0]}\nreturn acceptGate;`)()

test('MARGIN es 0.05 (contrato del gate)', () => {
  assert.equal(MARGIN, 0.05)
})

test('(a) candidato que sube recall sobre el margen -> aceptado por RECALL', () => {
  // +0.20 de catch-rate en las 3 reps (> MARGIN=0.05), FP igual.
  const r = acceptGate({
    baseRates: [0.5, 0.5, 0.5],
    candRates: [0.7, 0.7, 0.7],
    baseFpCount: 1,
    candFpCount: 1,
  })
  assert.equal(r.accepted, true)
  assert.equal(r.via, 'RECALL')
  assert.equal(r.winReps, 3)
  assert.equal(r.reps, 3)
})

test('(a2) recall sube pero FP empeora -> RECALL bloqueado (fpOk falla) y sin precision -> rechazado', () => {
  const r = acceptGate({
    baseRates: [0.5, 0.5, 0.5],
    candRates: [0.7, 0.7, 0.7],
    baseFpCount: 1,
    candFpCount: 2, // FP sube -> fpOk=false
  })
  assert.equal(r.accepted, false)
  assert.equal(r.via, null)
})

test('(b) candidato que degrada recall -> rechazado', () => {
  const r = acceptGate({
    baseRates: [0.8, 0.8, 0.8],
    candRates: [0.5, 0.5, 0.5],
    baseFpCount: 1,
    candFpCount: 1,
  })
  assert.equal(r.accepted, false)
  assert.equal(r.via, null)
  assert.equal(r.winReps, 0)
  assert.equal(r.heldReps, 0)
})

test('(c) mismo recall pero baja FP -> aceptado por PRECISION', () => {
  const r = acceptGate({
    baseRates: [0.6, 0.6, 0.6],
    candRates: [0.6, 0.6, 0.6], // recall se mantiene (held en las 3)
    baseFpCount: 2,
    candFpCount: 1, // FP baja -> fpImproved
  })
  assert.equal(r.accepted, true)
  assert.equal(r.via, 'PRECISION')
  assert.equal(r.winReps, 0)
  assert.equal(r.heldReps, 3)
})

test('(c2) mismo recall, FP igual -> ni recall ni precision -> rechazado', () => {
  const r = acceptGate({
    baseRates: [0.6, 0.6, 0.6],
    candRates: [0.6, 0.6, 0.6],
    baseFpCount: 2,
    candFpCount: 2, // FP no mejora -> fpImproved=false
  })
  assert.equal(r.accepted, false)
  assert.equal(r.via, null)
})

test('(d) borde EXACTO en MARGIN: delta == MARGIN NO gana (usa estricto > MARGIN)', () => {
  // delta = 0.05 - 0 == MARGIN EXACTO en IEEE-754 (evita el ruido de 0.55-0.5).
  // La via RECALL exige d > MARGIN (estricto) -> no cuenta como win. held sigue
  // verdadero (d >= 0) pero sin fpImproved no hay precision -> rechazado.
  const r = acceptGate({
    baseRates: [0, 0, 0],
    candRates: [0.05, 0.05, 0.05],
    baseFpCount: 1,
    candFpCount: 1,
  })
  assert.equal(r.winReps, 0, 'delta == MARGIN no debe contar como win (estricto >)')
  assert.equal(r.heldReps, 3, 'delta == MARGIN si mantiene el recall (>= 0)')
  assert.equal(r.accepted, false)
  assert.equal(r.via, null)
})

test('(d2) borde apenas por encima de MARGIN en la mayoria -> RECALL gana', () => {
  // delta = 0.06 (> 0.05) en 2 de 3 reps -> winReps=2 > 3/2 -> aceptado por recall.
  const r = acceptGate({
    baseRates: [0.5, 0.5, 0.5],
    candRates: [0.56, 0.56, 0.5],
    baseFpCount: 1,
    candFpCount: 1,
  })
  assert.equal(r.winReps, 2)
  assert.equal(r.accepted, true)
  assert.equal(r.via, 'RECALL')
})

test('mayoria estricta: win en 1 de 3 (empate-ish) NO alcanza (winReps > n/2)', () => {
  const r = acceptGate({
    baseRates: [0.5, 0.5, 0.5],
    candRates: [0.9, 0.5, 0.5], // solo 1 rep gana
    baseFpCount: 1,
    candFpCount: 1,
  })
  assert.equal(r.winReps, 1)
  assert.equal(r.accepted, false, '1/3 no es mayoria (> 1.5 requiere >=2)')
})

test('RECALL tiene prioridad sobre PRECISION cuando ambas aplican', () => {
  // recall sube en las 3 (win) Y FP baja (precision) -> via debe ser RECALL.
  const r = acceptGate({
    baseRates: [0.5, 0.5, 0.5],
    candRates: [0.7, 0.7, 0.7],
    baseFpCount: 2,
    candFpCount: 1,
  })
  assert.equal(r.accepted, true)
  assert.equal(r.via, 'RECALL')
})
