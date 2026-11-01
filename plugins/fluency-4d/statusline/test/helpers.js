// Helpers compartidos de los tests de la status line (sin dependencias).
// Cada test corre el script REAL por subprocess con HOME/USERPROFILE aislados en
// un dir temporal, asi nunca lee ni escribe el ~/.claude/fluency4d/ real.
const { spawnSync } = require('node:child_process');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const SCRIPT = path.resolve(__dirname, '..', 'statusline.js');
const REPO_ROOT = path.resolve(__dirname, '..', '..', '..', '..');

function tempHome() {
  return fs.mkdtempSync(path.join(os.tmpdir(), 'fluency4d-sl-'));
}

function flagsDir(home) {
  const dir = path.join(home, '.claude', 'fluency4d');
  fs.mkdirSync(dir, { recursive: true });
  return dir;
}

// Corre la barra. input: string crudo para stdin (objeto -> JSON.stringify).
// avisos: true escribe statusline.json con quiet:false (el default es silencio).
function run({ home, input = '', mode = 'experto', args = [], env = {}, avisos = false } = {}) {
  const h = home || tempHome();
  if (avisos) fs.writeFileSync(path.join(flagsDir(h), 'statusline.json'), '{"quiet":false}');
  const childEnv = { ...process.env, HOME: h, USERPROFILE: h, ...env };
  delete childEnv.STATUSLINE_THEME;
  delete childEnv.STATUSLINE_CUT_TOKENS;
  if (mode) childEnv.STATUSLINE_MODE = mode;
  else delete childEnv.STATUSLINE_MODE;
  const res = spawnSync(process.execPath, [SCRIPT, ...args], {
    input: typeof input === 'string' ? input : JSON.stringify(input),
    encoding: 'utf8',
    env: childEnv,
    timeout: 20000,
  });
  return { ...res, home: h, plain: stripAnsi(res.stdout || '') };
}

function stripAnsi(s) {
  return s.replace(/\x1b\[[0-9;]*m/g, '');
}

module.exports = { SCRIPT, REPO_ROOT, tempHome, flagsDir, run, stripAnsi };
