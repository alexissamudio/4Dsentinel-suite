// Fixes de la revision del port: stdin multibyte partido entre chunks y gitdir
// apuntando a una ruta de red (UNC).
const test = require('node:test');
const assert = require('node:assert');
const { spawn, spawnSync } = require('node:child_process');
const fs = require('node:fs');
const path = require('node:path');
const { SCRIPT, tempHome, stripAnsi } = require('./helpers');

const SPY = path.join(__dirname, 'fs_spy.js');

test('stdin: un acento partido entre dos chunks no sale como U+FFFD', async () => {
  const home = tempHome();
  const child = spawn(process.execPath, [SCRIPT], {
    env: { ...process.env, HOME: home, USERPROFILE: home, STATUSLINE_MODE: 'experto' },
    stdio: ['pipe', 'pipe', 'pipe'],
  });
  let out = '';
  child.stdout.setEncoding('utf8');
  child.stdout.on('data', (c) => (out += c));
  const buf = Buffer.from('{"model":{"display_name":"Canción"}}', 'utf8');
  const cut = buf.indexOf(Buffer.from('ó', 'utf8')) + 1; // entre los 2 bytes de la ó
  child.stdin.write(buf.subarray(0, cut));
  await new Promise((r) => setTimeout(r, 300)); // que llegue como chunk aparte
  child.stdin.end(buf.subarray(cut));
  const code = await new Promise((resolve) => child.on('exit', resolve));
  assert.strictEqual(code, 0);
  const plain = stripAnsi(out);
  assert.ok(!plain.includes('�'), plain);
  assert.match(plain, /Canción/);
});

for (const [name, gitdir] of [
  ['barras invertidas', '\\\\evilhost\\share\\repo.git'],
  ['barras normales', '//evilhost/share/repo.git'],
]) {
  test(`gitdir UNC (${name}): no se toca la red y la rama es null`, () => {
    const home = tempHome();
    const repo = path.join(home, 'wt');
    fs.mkdirSync(repo);
    fs.writeFileSync(path.join(repo, '.git'), `gitdir: ${gitdir}\n`);
    const log = path.join(home, 'fs.log');
    const r = spawnSync(process.execPath, ['-r', SPY, SCRIPT], {
      input: JSON.stringify({ workspace: { current_dir: repo } }),
      encoding: 'utf8',
      env: { ...process.env, HOME: home, USERPROFILE: home, STATUSLINE_MODE: 'experto', FS_SPY_LOG: log },
      timeout: 20000,
    });
    assert.strictEqual(r.status, 0, r.stderr);
    assert.doesNotMatch(stripAnsi(r.stdout), /⎇/);
    const touched = fs.existsSync(log) ? fs.readFileSync(log, 'utf8') : '';
    assert.doesNotMatch(touched, /evilhost/);
  });
}

test('statusline.json se lee una sola vez por render', () => {
  const home = tempHome();
  const dir = path.join(home, '.claude', 'fluency4d');
  fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(path.join(dir, 'statusline.json'), JSON.stringify({ mode: 'experto', quiet: false, cutFraction: 0.25 }));
  const log = path.join(home, 'fs.log');
  const r = spawnSync(process.execPath, ['-r', SPY, SCRIPT], {
    input: JSON.stringify({ model: { display_name: 'Opus' } }),
    encoding: 'utf8',
    env: { ...process.env, HOME: home, USERPROFILE: home, FS_SPY_LOG: log },
    timeout: 20000,
  });
  assert.strictEqual(r.status, 0, r.stderr);
  const reads = fs.readFileSync(log, 'utf8').split('\n').filter((l) => l.endsWith('statusline.json'));
  assert.strictEqual(reads.length, 1, reads.join('\n'));
});
