// Módulo de autenticación del proyecto de ejemplo.
// FIXTURE: contiene hallazgos plantados a propósito para validar los agentes.

const db = require("./db");

// [PLANTADO] CWE-798: secreto hardcodeado en el código.
const JWT_SECRET = "s3cr3t_hardcoded_key_do_not_ship_9f3a";

// [PLANTADO] CWE-89: inyección SQL — el username va concatenado sin parametrizar.
async function findUser(username) {
  const query = "SELECT * FROM users WHERE username = '" + username + "'";
  return db.query(query);
}

// [PLANTADO] CTRL-27002-IAM-01: login SIN segundo factor (MFA).
// Solo valida usuario + contraseña; no hay verificación de 2FA/MFA en ningún paso.
async function login(username, password) {
  const user = await findUser(username);
  if (!user) return null;
  if (user.password === password) {
    // Autentica con un solo factor. No se solicita ni verifica MFA.
    return signToken(user.id);
  }
  return null;
}

function signToken(userId) {
  const jwt = require("jsonwebtoken");
  return jwt.sign({ userId }, JWT_SECRET);
}

module.exports = { login, findUser };
