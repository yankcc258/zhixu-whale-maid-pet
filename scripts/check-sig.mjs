// 用 tauri.conf.json 里的公钥验证一个 .sig 签名（minisign 格式），确认 CI 里的私钥和配置里的公钥是一对。
// 用法：node scripts/check-sig.mjs 文件 文件.sig
import { readFileSync } from 'node:fs';
import { createHash, createPublicKey, verify } from 'node:crypto';
const [file, sigFile] = process.argv.slice(2);
const conf = JSON.parse(readFileSync('src-tauri/tauri.conf.json', 'utf8'));
const b64lines = (s) => Buffer.from(s.trim(), 'base64').toString('utf8').trim().split('\n');
const pk = Buffer.from(b64lines(conf.plugins.updater.pubkey)[1], 'base64'); // "Ed" + keyid(8) + key(32)
const sigLines = b64lines(readFileSync(sigFile, 'utf8'));
const sig = Buffer.from(sigLines[1], 'base64'); // "ED"/"Ed" + keyid(8) + sig(64)
const hex = (b) => Buffer.from(b).reverse().toString('hex').toUpperCase();
const pkId = hex(pk.subarray(2, 10)),
  sigId = hex(sig.subarray(2, 10));
if (pkId !== sigId) {
  console.log(`::error::私钥和配置里的公钥不是一对：签名的钥匙 ${sigId}，配置的公钥 ${pkId}。请把 TAURI_SIGNING_PRIVATE_KEY 换成和公钥同一次生成的私钥。`);
  process.exit(1);
}
const msg = readFileSync(file);
const data = sig.subarray(0, 2).toString() === 'ED' ? createHash('blake2b512').update(msg).digest() : msg;
const key = createPublicKey({ key: { kty: 'OKP', crv: 'Ed25519', x: pk.subarray(10, 42).toString('base64url') }, format: 'jwk' });
if (!verify(null, data, key, sig.subarray(10, 74))) {
  console.log('::error::签名验证失败');
  process.exit(1);
}
console.log(`签名和公钥对得上（钥匙 ${pkId}）`);
