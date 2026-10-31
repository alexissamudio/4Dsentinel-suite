// Preload (-r) para los tests: hace fallar fs.renameSync las primeras
// FAIL_RENAMES veces con el codigo FAIL_RENAME_CODE (EPERM por default), como
// Windows cuando otro proceso tiene el destino abierto.
const fs = require('node:fs');

let left = Number(process.env.FAIL_RENAMES) || 0;
const real = fs.renameSync;
fs.renameSync = function renameSync(...args) {
  if (left > 0) {
    left--;
    const e = new Error(`${process.env.FAIL_RENAME_CODE || 'EPERM'}: operation not permitted, rename`);
    e.code = process.env.FAIL_RENAME_CODE || 'EPERM';
    throw e;
  }
  return real.apply(this, args);
};
