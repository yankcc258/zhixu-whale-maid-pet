// 鲸鱼娘桌宠（准备版）：戳一下 duang + 吐槽，按住拖动窗口，双击打开知序，右键菜单。
// 后面要搬过来的：躲边、拎起来扑腾、睡觉、乱跑、摸头、番茄钟陪学（见 README 的路线图）。
const tauri = window.__TAURI__;
const win = tauri?.window.getCurrentWindow();
const $ = (s) => document.querySelector(s);
const pick = (a) => a[Math.floor(Math.random() * a.length)];
const pet = $('#pet'),
  img = $('#sprite'),
  bubble = $('#bubble'),
  menu = $('#menu');

const LINES = [
  '哦鲸鲸……戳什么戳，Yank 你很闲吗？',
  '我从网页里搬出来了！……桌面好大，白饭在哪？',
  '双击我就带你去知序，别光顾着玩我。',
  '（duang）……再戳要收费了，一下一碗白饭。',
  '有这功夫不如去背两个单词？',
];
let sayTimer = 0,
  moodTimer = 0;
function setSprite(name, ms) {
  img.src = `sprites/${name}.webp`;
  clearTimeout(moodTimer);
  if (ms) moodTimer = setTimeout(() => setSprite(autoSprite()), ms);
}
function autoSprite() {
  const h = new Date().getHours();
  return h >= 23 || h < 6 ? 'sleep' : 'idle';
}
function say(text, ms = 4000) {
  menu.hidden = true;
  bubble.textContent = text;
  bubble.hidden = false;
  clearTimeout(sayTimer);
  sayTimer = setTimeout(() => (bubble.hidden = true), ms);
}
function duang() {
  img.classList.remove('duang');
  void img.offsetWidth;
  img.classList.add('duang');
}

// 按住拖动窗口；没拖动就算「戳」
let down = null;
pet.addEventListener('mousedown', (e) => {
  if (e.button !== 0) return;
  down = { x: e.screenX, y: e.screenY, dragging: false };
});
addEventListener('mousemove', (e) => {
  if (!down || down.dragging) return;
  if (Math.hypot(e.screenX - down.x, e.screenY - down.y) < 4) return;
  down.dragging = true;
  setSprite('dangle');
  win?.startDragging().finally(() => {
    down = null;
    setSprite(autoSprite());
  });
});
addEventListener('mouseup', () => {
  if (down && !down.dragging) {
    duang();
    setSprite(pick(['happy', 'smug', 'smirk', 'bleh']), 3000);
    say(pick(LINES));
  }
  down = null;
});
pet.addEventListener('dblclick', () => {
  say('走，去知序！', 2500);
  tauri?.core.invoke('open_zhixu').catch((e) => say('没打开：' + e));
});
pet.addEventListener('contextmenu', (e) => {
  e.preventDefault();
  bubble.hidden = true;
  menu.hidden = !menu.hidden;
});
menu.addEventListener('click', (e) => {
  const act = e.target.closest('button')?.dataset.act;
  menu.hidden = true;
  if (act === 'open') tauri?.core.invoke('open_zhixu');
  if (act === 'hide') win?.hide();
});
addEventListener('keydown', (e) => e.key === 'Escape' && (menu.hidden = bubble.hidden = true));

setSprite(autoSprite());
setInterval(() => !down && setSprite(autoSprite()), 60000);
setTimeout(() => say('鲸鱼娘上桌面啦！双击我打开知序，右键看菜单。', 6000), 800);
