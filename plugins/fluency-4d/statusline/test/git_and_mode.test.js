// Rama git (repo normal, worktree con `.git` archivo, HEAD detached) y CLI `mode`.
const test = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const path = require('node:path');
const { tempHome, flagsDir, run } = require('./helpers');

function branchOf(dir) {
  const r = run({ input: { workspace: { current_dir: dir } } });
  assert.strictEqual(r.status, 0, r.stderr);
  const m = r.plain.match(/⎇ (\S+)/);
  return m ? m[1] : null;
}

test('rama en un repo normal (.git carpeta), tambien desde un subdir', () => {
  const root = tempHome();
  fs.mkdirSync(path.join(root, '.git'));
  fs.writeFileSync(path.join(root, '.git', 'HEAD'), 'ref: refs/heads/main\n');
  fs.mkdirSync(path.join(root, 'src', 'a'), { recursive: true });
  assert.strictEqual(branchOf(root), 'main');
  assert.strictEqual(branchOf(path.join(root, 'src', 'a')), 'main');
});

test('rama en un worktree: .git archivo con gitdir absoluto', () => {
  const base = tempHome();
  const gitdir = path.join(base, 'main', '.git', 'worktrees', 'port');
  fs.mkdirSync(gitdir, { recursive: true });
  fs.writeFileSync(path.join(gitdir, 'HEAD'), 'ref: refs/heads/feat/fluency-statusline-panel\n');
  const wt = path.join(base, 'port');
  fs.mkdirSync(path.join(wt, 'sub'), { recursive: true });
  fs.writeFileSync(path.join(wt, '.git'), `gitdir: ${gitdir}\n`);
  assert.strictEqual(branchOf(wt), 'feat/fluency-statusline-panel');
  assert.strictEqual(branchOf(path.join(wt, 'sub')), 'feat/fluency-statusline-panel');
});

test('rama en un worktree: gitdir relativo al dir del .git', () => {
  const base = tempHome();
  const gitdir = path.join(base, 'main', '.git', 'worktrees', 'rel');
  fs.mkdirSync(gitdir, { recursive: true });
  fs.writeFileSync(path.join(gitdir, 'HEAD'), 'ref: refs/heads/rel-branch\n');
  const wt = path.join(base, 'rel');
  fs.mkdirSync(wt);
  fs.writeFileSync(path.join(wt, '.git'), 'gitdir: ../main/.git/worktrees/rel\r\n');
  assert.strictEqual(branchOf(wt), 'rel-branch');
});

test('HEAD detached: primeros 7 caracteres del sha', () => {
  const root = tempHome();
  fs.mkdirSync(path.join(root, '.git'));
  fs.writeFileSync(path.join(root, '.git', 'HEAD'), '9314eed1234567890abcdef\n');
  assert.strictEqual(branchOf(root), '9314eed');
});

test('.git archivo sin gitdir valido: no rompe', () => {
  const root = tempHome();
  fs.writeFileSync(path.join(root, '.git'), 'basura\n');
  const r = run({ input: { workspace: { current_dir: root } } });
  assert.strictEqual(r.status, 0, r.stderr);
});

test('mode escribe statusline.json de forma atomica y conserva las otras claves', () => {
  const home = tempHome();
  const dir = flagsDir(home);
  const file = path.join(dir, 'statusline.json');
  fs.writeFileSync(file, JSON.stringify({ theme: 'nord', cutFraction: 0.25 }));
  const r = run({ home, mode: null, args: ['mode', 'experto'] });
  assert.strictEqual(r.status, 0, r.stderr);
  assert.match(r.plain, /modo "experto"/);
  assert.deepStrictEqual(JSON.parse(fs.readFileSync(file, 'utf8')), { theme: 'nord', cutFraction: 0.25, mode: 'experto' });
  for (const arg of ['silencio', 'gruvbox']) {
    assert.strictEqual(run({ home, mode: null, args: ['mode', arg] }).status, 0);
  }
  const st = JSON.parse(fs.readFileSync(file, 'utf8'));
  assert.strictEqual(st.quiet, true);
  assert.strictEqual(st.theme, 'gruvbox');
  assert.deepStrictEqual(fs.readdirSync(dir).filter((f) => f.endsWith('.tmp')), []);
});

test('mode crea el dir si no existe', () => {
  const home = tempHome();
  const r = run({ home, mode: null, args: ['mode', 'simple'] });
  assert.strictEqual(r.status, 0, r.stderr);
  const st = JSON.parse(fs.readFileSync(path.join(home, '.claude', 'fluency4d', 'statusline.json'), 'utf8'));
  assert.strictEqual(st.mode, 'simple');
});

test('mode invalido: muestra Uso, sale 1 y no escribe', () => {
  const home = tempHome();
  const r = run({ home, mode: null, args: ['mode', 'cualquiera'] });
  assert.strictEqual(r.status, 1);
  assert.match(r.plain, /Uso:/);
  assert.ok(!fs.existsSync(path.join(home, '.claude', 'fluency4d', 'statusline.json')));
  const bare = run({ home, mode: null, args: ['mode'] });
  assert.strictEqual(bare.status, 0);
  assert.match(bare.plain, /Modo actual: experto \(silencio, tema templado\)/);
});
