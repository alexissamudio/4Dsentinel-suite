// Preload (-r) para los tests: anota en FS_SPY_LOG cada ruta que la barra
// toca con fs.statSync / existsSync / readFileSync, para ver si intenta abrir
// una ruta de red sin depender de que haya red.
const fs = require('node:fs');

const LOG = process.env.FS_SPY_LOG;
for (const name of ['statSync', 'existsSync', 'readFileSync', 'lstatSync', 'openSync']) {
  const orig = fs[name];
  fs[name] = function spy(p, ...rest) {
    if (LOG && (typeof p === 'string' || p instanceof URL)) {
      try { fs.appendFileSync(LOG, `${String(p)}\n`); } catch { /* sin log */ }
    }
    return orig.call(this, p, ...rest);
  };
}
