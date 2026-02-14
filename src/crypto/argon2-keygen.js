// Derive key from voice
const argon = require('argon2');
const hash = crypto.subtle.digest('SHA-256', new TextEncoder().encode("FORTRESS ON"));
argon.hash(new TextEncoder().encode("voice"), {
  type: argon.Argon2id,
  memoryCost: 2*1024*1024,
  timeCost: 3,
  outputLen: 32
}).then(console.log);