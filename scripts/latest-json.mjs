// 生成 Tauri 更新插件读的 latest.json：版本号、更新说明、Windows 安装包的下载地址和签名。
// 用法：node scripts/latest-json.mjs v0.3.0 yankcc258/zhixu-whale-maid-pet-releases
import { readFileSync, readdirSync } from 'node:fs';
const [tag, repo] = process.argv.slice(2);
const dir = 'src-tauri/target/release/bundle/nsis';
const exe = readdirSync(dir).find((f) => f.endsWith('-setup.exe'));
if (!tag || !repo || !exe) throw Error('需要标签、仓库名，以及打包好的 *-setup.exe');
const notes = readFileSync('release-notes.md', 'utf8').trim();
const out = {
  version: tag.replace(/^v/, ''),
  notes,
  pub_date: new Date().toISOString(),
  platforms: {
    'windows-x86_64': {
      signature: readFileSync(`${dir}/${exe}.sig`, 'utf8').trim(),
      url: `https://github.com/${repo}/releases/download/${tag}/${encodeURIComponent(exe)}`,
    },
  },
};
process.stdout.write(JSON.stringify(out, null, 2) + '\n');
