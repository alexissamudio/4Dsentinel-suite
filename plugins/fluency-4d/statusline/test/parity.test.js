// Paridad de flags 4D con los hooks: mismos casos que el pytest
// tests/fluency-4d/hooks/test_flags_parity.py (fixture compartido).
const test = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const path = require('node:path');
const { REPO_ROOT, tempHome, flagsDir, run } = require('./helpers');

const FIXTURE = path.join(REPO_ROOT, 'tests', 'fluency-4d', 'fixtures', 'flags_parity.json');
const { cases } = JSON.parse(fs.readFileSync(FIXTURE, 'utf8'));

// Segmento "4D <modos>" de la primera linea del modo experto (separado por " │ ").
function shownModes(plain) {
  const first = plain.split('\n')[0];
  const seg = first.split('│').map((s) => s.trim()).find((s) => s.startsWith('4D '));
  return seg ? seg.slice(3).split(' ') : [];
}

test('el fixture tiene casos', () => {
  assert.ok(cases.length >= 15);
});

for (const c of cases) {
  test(`paridad: ${c.name}`, () => {
    const home = tempHome();
    const dir = flagsDir(home);
    for (const [name, data] of Object.entries(c.flags)) {
      fs.writeFileSync(path.join(dir, `${name}.json`), typeof data === 'string' ? data : JSON.stringify(data));
    }
    for (const mode of ['experto', 'normal']) {
      const r = run({ home, input: '{}', mode });
      assert.strictEqual(r.status, 0, r.stderr);
      assert.deepStrictEqual(shownModes(r.plain), c.expected, `${mode}: ${r.plain}`);
    }
  });
}
