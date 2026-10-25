// 设置窗口：改 localStorage 'whale-prefs'，鲸鱼娘的窗口收到 storage 事件后马上生效。开机自启走 Rust。
const tauri = window.__TAURI__;
const invoke = (cmd, args) => tauri?.core.invoke(cmd, args) ?? Promise.resolve();
const DEFAULTS = { activity: 'normal', sleep: '23-6', chatty: 'mid', gameMode: true, quiet: false, wardrobeLocked: false, figure: 'q', qStyle: 'live2d', pixel: false, sfx: 'low' };
// 文字框：称呼、网站名、网址（输入停下 0.4 秒后保存）
for (const t of document.querySelectorAll('input[type="text"][data-key], input[type="url"][data-key]')) {
  let timer = 0;
  t.addEventListener('input', () => {
    clearTimeout(timer);
    timer = setTimeout(() => {
      const p = load();
      p[t.dataset.key] = t.value.trim();
      save(p);
    }, 400);
  });
}
const load = () => {
  try {
    const p = { ...DEFAULTS, ...JSON.parse(localStorage.getItem('whale-prefs') || '{}') };
    if (p.live2d === false && !('qStyleSet' in p)) p.qStyle = 'static'; // 0.6.x 关掉过 Live2D 的
    return p;
  } catch {
    return { ...DEFAULTS };
  }
};
const save = (p) => localStorage.setItem('whale-prefs', JSON.stringify(p));
function render() {
  const p = load();
  for (const seg of document.querySelectorAll('.seg'))
    for (const b of seg.querySelectorAll('button'))
      b.classList.toggle('selected', String(p[seg.dataset.key]) === b.dataset.v);
  for (const c of document.querySelectorAll('input[type="checkbox"][data-key]')) c.checked = !!p[c.dataset.key];
  for (const t of document.querySelectorAll('input[type="text"][data-key], input[type="url"][data-key]'))
    if (document.activeElement !== t) t.value = p[t.dataset.key] || '';
}
document.addEventListener('click', (e) => {
  const b = e.target.closest('.seg button');
  if (!b) return;
  const p = load();
  p[b.closest('.seg').dataset.key] = b.dataset.v;
  if (b.closest('.seg').dataset.key === 'qStyle') p.qStyleSet = true;
  save(p);
  render();
});
for (const c of document.querySelectorAll('input[type="checkbox"][data-key]'))
  c.addEventListener('change', () => {
    const p = load();
    p[c.dataset.key] = c.checked;
    save(p);
  });
const auto = document.querySelector('#autostart');
invoke('autostart_get').then((on) => (auto.checked = !!on));
auto.addEventListener('change', async () => {
  try {
    auto.checked = await invoke('autostart_set', { on: auto.checked });
  } catch (e) {
    auto.checked = !auto.checked;
    document.querySelector('#autostart-err').textContent = '没设置成功：' + e;
  }
});
document.querySelector('#reset').addEventListener('click', () => {
  const p = load();
  delete p.pos;
  p.dock = null;
  p.resetAt = Date.now();
  save(p);
});
tauri?.app.getVersion().then((v) => (document.querySelector('#ver').textContent = v));
addEventListener('storage', render);
render();
