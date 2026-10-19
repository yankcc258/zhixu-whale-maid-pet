// 鲸鱼娘桌宠 0.2：戳、拎起来扑腾、躲在屏幕边、睡觉（飘 Z、梦话、吵醒暴怒）、摸头、在任务栏上方乱跑、
// 自己冒话、右键菜单。窗口本身是 240×260 的透明方块，鼠标只有落在她和气泡上才算数（Rust 那边做穿透）。
// 设置存在 localStorage 'whale-prefs'，设置窗口改了会通过 storage 事件同步过来。
const tauri = window.__TAURI__;
const win = tauri?.window.getCurrentWindow();
const invoke = (cmd, args) => tauri?.core.invoke(cmd, args) ?? Promise.resolve();
const $ = (s) => document.querySelector(s);
const pet = $('#pet'),
  img = $('#sprite'),
  bubble = $('#bubble'),
  menu = $('#menu');
const WIN_W = 240,
  WIN_H = 260,
  PET_MARGIN = 10; // #pet 离窗口右边（躲左边时离左边）的距离

// ---------- 设置 ----------
const DEFAULTS = {
  activity: 'normal',
  sleep: '23-6',
  chatty: 'mid',
  gameMode: true,
  quiet: false,
  name: '', // 她怎么叫你，空着就叫 Yank
  siteName: '', // 双击打开的网站，空着就是知序
  siteUrl: '',
  city: '', // 天气用的城市，空着就不查天气
  wardrobe: [], // 见过的节日/季节衣服
  wardrobeLocked: false, // 设置里打开：衣柜只放见过的衣服（收集模式）
  wardrobeMode: 'auto', // 'auto'：节日、晚上自己换；'lock'：一直穿衣柜里选的那套
  outfit: 'maid', // 锁定时穿哪套
  examUntil: 0, // 考试周（必胜头巾）到什么时候
};
let prefs = loadPrefs();
function loadPrefs() {
  try {
    return { ...DEFAULTS, ...JSON.parse(localStorage.getItem('whale-prefs') || '{}') };
  } catch {
    return { ...DEFAULTS };
  }
}
function savePrefs() {
  try {
    localStorage.setItem('whale-prefs', JSON.stringify(prefs));
  } catch {}
}
addEventListener('storage', (e) => {
  if (e.key !== 'whale-prefs') return;
  const resetBefore = prefs.resetAt;
  prefs = loadPrefs();
  renderMenu();
  invoke('set_game_mode', { on: !!prefs.gameMode });
  if (prefs.resetAt !== resetBefore) resetPos();
  weatherTick();
  nextChat = Date.now() + rand(...chatGap()) * 60000;
  nextRoam = 0;
  if (sleep && !isNight()) sleep = null;
  setMood(autoMood());
});
// 台词里的 {n}（称呼）和 {s}（网站名）
function lineVars() {
  return { n: (prefs.name || '').trim() || 'Yank', s: (prefs.siteName || '').trim() || '知序' };
}
const ZHIXU = 'https://yank-study-lab.yank-study-lab.workers.dev';
function openSite() {
  const url = (prefs.siteUrl || '').trim();
  // 打开知序时带上 #desk-whale：网页里那只看到就知道桌面这只在，会自己躲起来
  const target = /^https?:\/\//.test(url) ? url : ZHIXU;
  return invoke('open_zhixu', { url: target.startsWith(ZHIXU) && !target.includes('#') ? target + '/#desk-whale' : target });
}
const ACTIVITY_GAP = { calm: null, normal: [4, 8], lively: [0.75, 1.6] }; // 分钟
const CHAT_GAP = { low: [45, 90], mid: [20, 45], high: [8, 15] };
const chatGap = () => CHAT_GAP[prefs.chatty] || CHAT_GAP.mid;
const rand = (a, b) => a + Math.random() * (b - a);
function isNight(d = new Date()) {
  if (!prefs.sleep || prefs.sleep === 'off') return false;
  // 大晦日陪你跨年：12/31 晚上和元旦凌晨 1 点前不睡
  if ((md(d) === 1231 && d.getHours() >= 20) || (md(d) === 101 && d.getHours() < 1)) return false;
  const [a, b] = prefs.sleep.split('-').map(Number),
    h = d.getHours();
  return a < b ? h >= a && h < b : h >= a || h < b;
}

// ---------- 状态 ----------
let mood = 'idle',
  moodUntil = 0,
  dock = prefs.dock === 'left' || prefs.dock === 'right' ? prefs.dock : null, // 'left' | 'right' | 'bottom'（只在睡觉时）
  dragging = false,
  sleep = null, // null | 'asleep' | 'groggy' | 'mad'
  sleepUntil = 0,
  groggyAt = 0,
  roam = null,
  nextRoam = 0,
  nextChat = Date.now() + rand(...chatGap()) * 20000, // 第一次说话来得快一点
  lastSleepTalk = Date.now(),
  pokes = [],
  warnedAt = 0,
  lastPat = 0,
  sayTimer = 0;
const startedAt = Date.now();

function autoMood() {
  if (sleep === 'asleep') return 'sleep';
  if (sleep === 'groggy') return 'sleepy';
  if (sleep === 'mad') return 'wake';
  return wear() || 'idle';
}
// ---------- 衣服（outfits.js 管图，festivals.js 管节日） ----------
// 现在穿哪套。锁定：一直穿选的那套。自动：考试周 > 晚上睡衣 > 节日 > 女仆装
function outfitNow() {
  if (prefs.wardrobeMode === 'lock') return OUTFITS[prefs.outfit] || festById(prefs.outfit) ? prefs.outfit : 'maid';
  if (prefs.examUntil > Date.now()) return 'hisshou';
  if (sleep || isNight()) return 'pajamas';
  const f = festToday();
  if (f) return f.id;
  if (weather && !weather.error && weather.max <= 10) return 'winter'; // 今天最高不到 10°C：穿冬装
  return 'maid';
}
// 身上是不是节日/季节衣服（是的话返回它的 id，节日台词、装饰都看这个）
function wear() {
  const o = outfitNow();
  return festById(o) ? o : '';
}
// 现在身上这身是哪个节日（装饰、台词用）
const wornFest = () => festById(mood) || null;
// 身上这身是衣柜里硬换的、今天并不是它的日子
function offDay() {
  const o = outfitNow(),
    f = outfitInfo(o);
  if (o === 'maid') return false;
  if (o === 'hisshou') return !(prefs.examUntil > Date.now());
  return !!f.when && !f.when(new Date());
}
function unlock(id) {
  if (!festById(id) || prefs.wardrobe.includes(id)) return;
  prefs.wardrobe = [...prefs.wardrobe, id];
  savePrefs();
}
// 躲在左右边时能用的表情（左边会镜像）
const DOCK_MOODS = ['peek', 'peekPhone', 'peekCheek', 'peekHead', 'peekAngry', 'peekSleep'];
function setMood(m, ms) {
  if (dragging) m = 'dangle';
  else if (dock === 'bottom') m = sleep === 'asleep' ? 'sleepBottom' : 'peekBottom';
  else if (dock) {
    if (sleep === 'asleep' || sleep === 'groggy') m = 'peekSleep';
    else if (sleep === 'mad' || m === 'angry') m = 'peekAngry';
    else if (!DOCK_MOODS.includes(m)) m = 'peek';
  } else if (sleep === 'asleep' && m !== 'pat') m = 'sleep';
  else if (m === 'idle' && !sleep && wear()) m = wear();
  else if (sleep === 'groggy' && m !== 'wake') m = 'sleepy';
  else if (sleep === 'mad') m = 'wake';
  mood = m;
  unlock(m);
  moodUntil = ms ? Date.now() + ms : 0;
  showSprite(spriteFor(outfitNow(), m));
  const stand = standInFor(outfitNow(), m);
  document.body.classList.toggle('standin-side', stand === 'side');
  document.body.classList.toggle('standin-bottom', stand === 'bottom');
  document.body.classList.toggle('flip', (dock === 'left') !== (m === 'run' && roam?.dir > 0));
  document.body.classList.toggle('asleep', m === 'sleep' || m === 'peekSleep' || m === 'sleepBottom');
  document.body.classList.toggle('busy', m === 'read' || m === 'onigiri');
  document.body.classList.toggle('angry', m === 'angry' || m === 'wake' || m === 'peekAngry');
}

// 换图；多帧的（浴衣跑步）轮流换
let frameTimer = 0,
  shownFrames = '';
function showSprite(src) {
  const frames = Array.isArray(src) ? src : [src];
  if (frames.join() === shownFrames) return;
  shownFrames = frames.join();
  clearInterval(frameTimer);
  img.src = frames[0];
  if (frames.length < 2) return;
  frames.forEach((f) => (new Image().src = f)); // 先载好，免得闪
  let i = 0;
  frameTimer = setInterval(() => (img.src = frames[(i = (i + 1) % frames.length)]), 170);
}

// ---------- 气泡和菜单 ----------
function say(text, m, ms = 4500) {
  menu.hidden = true;
  bubble.classList.remove('wardrobe');
  bubble.textContent = fill(text);
  bubble.hidden = false;
  if (m) setMood(m, ms);
  clearTimeout(sayTimer);
  sayTimer = setTimeout(() => {
    bubble.hidden = true;
    updateHit();
  }, ms);
  updateHit();
}
// 自己冒出来的话：安静模式、拖着、菜单开着时不说
function pop(text, m, ms) {
  if (prefs.quiet || dragging || !menu.hidden) return;
  if (!bubble.hidden && bubble.querySelector('.acts')) return; // 正在问你问题（比如要不要更新）
  say(text, m, ms);
}
function duang() {
  img.classList.remove('duang');
  void img.offsetWidth;
  img.classList.add('duang');
}

// ---------- 鼠标穿透：告诉 Rust 哪些地方算「她」 ----------
function updateHit() {
  const rects = [];
  const add = (el, pad = 0) => {
    if (!el || el.hidden) return;
    const r = el.getBoundingClientRect();
    if (r.width && r.height) rects.push([r.left + pad, r.top + pad, r.width - pad * 2, r.height - pad * 2]);
  };
  // 按住拖动时整个窗口都算，免得鼠标甩快了穿过去
  if (down) rects.push([0, 0, WIN_W, WIN_H]);
  add(pet, 14);
  add(bubble);
  add(menu);
  invoke('set_hit_rects', { rects });
}

// ---------- 窗口位置 ----------
let pos = { x: 0, y: 0 },
  area = null; // 当前屏幕的工作区（不含任务栏），逻辑像素
async function readGeometry() {
  if (!win) return;
  const scale = await win.scaleFactor();
  const p = await win.outerPosition();
  pos = { x: p.x / scale, y: p.y / scale };
  const m = (await tauri.window.currentMonitor()) || (await tauri.window.primaryMonitor());
  if (m) {
    const wa = m.workArea || { position: m.position, size: m.size };
    area = {
      x: wa.position.x / m.scaleFactor,
      y: wa.position.y / m.scaleFactor,
      w: wa.size.width / m.scaleFactor,
      h: wa.size.height / m.scaleFactor,
    };
  }
}
let posPending = null;
function moveTo(x, y) {
  pos = { x: Math.round(x), y: Math.round(y) };
  if (posPending) return;
  posPending = requestAnimationFrame(() => {
    posPending = null;
    win?.setPosition(new tauri.window.LogicalPosition(pos.x, pos.y));
  });
}
const clampX = (x) => (area ? Math.min(Math.max(x, area.x - PET_MARGIN), area.x + area.w - WIN_W + PET_MARGIN) : x);
const clampY = (y) => (area ? Math.min(Math.max(y, area.y - 100), area.y + area.h - WIN_H) : y);
function rememberPos() {
  prefs.pos = { x: pos.x, y: pos.y };
  prefs.dock = dock;
  savePrefs();
}
async function resetPos() {
  stopRoam();
  dock = null;
  await readGeometry();
  if (area) moveTo(area.x + area.w - WIN_W - 16, area.y + area.h - WIN_H);
  applyDock();
  say('（被拎回右下角）……知道了知道了。', 'pout', 3000);
}
function applyDock() {
  document.body.classList.toggle('dock-left', dock === 'left');
  document.body.classList.toggle('docked', !!dock);
  document.body.classList.toggle('dock-bottom', dock === 'bottom');
  if (dock === 'bottom' && area) moveTo(pos.x, area.y + area.h - WIN_H);
  else if (dock && area) moveTo(dock === 'right' ? area.x + area.w - WIN_W + PET_MARGIN : area.x - PET_MARGIN, pos.y);
  setMood(autoMood());
}

// ---------- 拖动 / 戳 ----------
let down = null;
pet.addEventListener('pointerdown', (e) => {
  if (e.button !== 0) return;
  pet.setPointerCapture(e.pointerId);
  down = { sx: e.screenX, sy: e.screenY, x: pos.x, y: pos.y, moved: false };
  updateHit();
});
pet.addEventListener('pointermove', (e) => {
  if (!down) return patTrack(e);
  const dx = e.screenX - down.sx,
    dy = e.screenY - down.sy;
  if (!down.moved && Math.hypot(dx, dy) < 5) return;
  if (!down.moved) {
    down.moved = true;
    dragging = true;
    stopRoam();
    if (dock) {
      dock = null;
      document.body.classList.remove('dock-left', 'docked', 'dock-bottom');
    }
    menu.hidden = bubble.hidden = true;
    document.body.classList.add('dragging');
    setMood('dangle');
  }
  moveTo(down.x + dx, down.y + dy);
});
pet.addEventListener('pointerup', async () => {
  const d = down;
  down = null;
  updateHit();
  if (!d) return;
  if (!d.moved) return poke();
  dragging = false;
  document.body.classList.remove('dragging');
  await readGeometry();
  const petLeft = pos.x + WIN_W - PET_MARGIN - 140,
    petRight = pos.x + WIN_W - PET_MARGIN;
  if (area && petRight > area.x + area.w - 8) dock = 'right';
  else if (area && petLeft < area.x + 8) dock = 'left';
  // 拖到任务栏上：扒着屏幕底边只露个头（睡着时就钻下去接着睡）
  else if (area && pos.y + WIN_H > area.y + area.h - 4) dock = 'bottom';
  else dock = null;
  if (!dock) moveTo(clampX(pos.x), clampY(pos.y));
  applyDock();
  rememberPos();
  if (dock === 'bottom') {
    if (sleep) {
      sleep = 'asleep';
      return say(pick(LINES.burrow), undefined, 4000);
    }
    return say(pick(LINES.bottomHide), undefined, 3500);
  }
  if (sleep) {
    sleep = 'mad';
    sleepUntil = Date.now() + 15000;
    return say(pick(LINES.mad), 'wake', 8000);
  }
  if (dock) say(pick(LINES.hide), 'peek', 3500);
  else say(pick(LINES.dropped), pick(['pout', 'meh']), 3000);
});
pet.addEventListener('pointercancel', () => {
  down = null;
  dragging = false;
  document.body.classList.remove('dragging');
  setMood(autoMood());
});

function poke() {
  duang();
  // 钻在任务栏下面睡：戳一下就迷迷糊糊地爬出来；醒着扒在底边就嘟囔一句
  if (dock === 'bottom' && !sleep) {
    document.body.classList.add('peeking');
    setTimeout(() => document.body.classList.remove('peeking'), 2500);
    return say(fill(pick(LINES.pokeBottom)), undefined, 3000);
  }
  if (dock === 'bottom') {
    dock = null;
    applyDock();
    rememberPos();
  }
  if (sleep === 'asleep') {
    sleep = 'groggy';
    groggyAt = Date.now();
    sleepUntil = Date.now() + 20000;
    return say(pick(LINES.groggy), 'sleepy', 20000);
  }
  if (sleep === 'groggy' && Date.now() - groggyAt < 12000) {
    sleep = 'mad';
    sleepUntil = Date.now() + 14000;
    return say(pick(LINES.mad), 'wake', 12000);
  }
  if (dock) {
    document.body.classList.add('peeking');
    setTimeout(() => document.body.classList.remove('peeking'), 3500);
  }
  // 乱戳：3 秒内 6 下生气并警告；警告后 30 秒内再戳 4 下就躲进托盘
  const now = Date.now();
  pokes = pokes.filter((t) => now - t < 3000);
  pokes.push(now);
  if (warnedAt && now - warnedAt > 30000) warnedAt = 0;
  if (warnedAt) {
    if (pokes.filter((t) => t > warnedAt).length >= 4) return runAway();
    return say(pick(LINES.bugged), 'angry', 4000);
  }
  if (pokes.length >= 6) {
    warnedAt = now;
    pokes = [];
    return say(pick(LINES.angry), 'angry', 6000);
  }
  // 躲在边上被戳：戳脸或者戳头
  if (dock) {
    const head = Math.random() < 0.5;
    return say(pick(head ? LINES.pokeHead : LINES.pokeCheek), head ? 'peekHead' : 'peekCheek', 3000);
  }
  if (festPoke()) return;
  const h = new Date().getHours();
  if (h < 5) return say(fill(pick(LINES.pokeNight), { h }), 'meh', 3500);
  if (h < 8 && Math.random() < 0.6) return say(pick(LINES.pokeMorning), 'idle', 3500);
  say(pick(LINES.poke), pick(['happy', 'happy', 'smug', 'smirk', 'bleh']), 3500);
}
// 节日里戳她：初詣抽签、节分撒豆，其他节日一半概率说节日台词
function festPoke() {
  const f = festToday(),
    today = new Date().toDateString(),
    w = wear();
  if (f?.id === 'omikuji' && prefs.omikujiDay !== today) {
    const [kuji, line] = pick(OMIKUJI);
    prefs.omikujiDay = today;
    prefs.omikuji = kuji;
    savePrefs();
    burst(['✨', '🎍', '✨'], 6);
    say('（哗啦哗啦摇签筒）……', 'omikuji', 1600);
    setTimeout(() => say(`【${kuji}】${fill(line)}`, kuji === '凶' ? 'pout' : 'omikuji', 7000), 1500);
    return true;
  }
  if (f?.id === 'setsubun' && w === 'setsubun') {
    burst(['🫘'], 8);
    say(pick(f.poke), 'setsubun', 3500);
    return true;
  }
  const worn = festById(w);
  if (offDay() && Math.random() < 0.3) {
    say(fill(offLine(outfitInfo(outfitNow()))), w || 'smug', 4000);
    return true;
  }
  if (worn?.poke && Math.random() < 0.5) {
    say(pick(worn.poke), w, 3500);
    return true;
  }
  return false;
}
function runAway() {
  say(pick(LINES.runAway), 'angry', 1800);
  setTimeout(() => {
    warnedAt = 0;
    bubble.hidden = true;
    win?.hide();
  }, 1600);
}
// ---------- 自动更新：Rust 查到新版本就发 update-available，她来问要不要更新 ----------
function ask(text, buttons, m) {
  menu.hidden = true;
  clearTimeout(sayTimer);
  bubble.classList.remove('wardrobe');
  bubble.textContent = '';
  const p = document.createElement('p');
  p.textContent = fill(text);
  const row = document.createElement('div');
  row.className = 'acts';
  for (const [label, fn] of buttons) {
    const b = document.createElement('button');
    b.textContent = label;
    b.onclick = fn;
    row.append(b);
  }
  bubble.append(p, row);
  bubble.hidden = false;
  if (m) setMood(m, 60000);
  updateHit();
}
function closeBubble() {
  bubble.hidden = true;
  updateHit();
}
tauri?.event.listen('update-available', ({ payload }) => {
  if (sleep === 'asleep') sleep = null; // 有正事就醒一下
  ask(fill(pick(LINES.update), { v: payload.version, c: payload.current }), [
    ['好，更新', installUpdate],
    ['以后再说', () => (closeBubble(), say(pick(LINES.updateLater), 'meh', 3000))],
  ], 'excited');
});
tauri?.event.listen('update-none', () => say(pick(LINES.updateNone), 'smug', 4000));
tauri?.event.listen('update-error', ({ payload }) => say('没查到更新……' + payload, 'pout', 6000));
function installUpdate() {
  say(pick(LINES.updating), 'run', 120000);
  invoke('install_update').catch((e) => say('更新失败了：' + e, 'pout', 8000));
}

tauri?.event.listen('open-site', () => openSite());
tauri?.event.listen('summoned', () => {
  setMood(autoMood());
  say(pick(LINES.summoned), sleep ? undefined : pick(['happy', 'excited']), 4000);
});

pet.addEventListener('dblclick', () => {
  say(pick(LINES.openZhixu), sleep ? undefined : pick(['smug', 'surprised']), 2500);
  openSite().catch((e) => say('没打开：' + e, 'pout'));
});

// ---------- 摸头：鼠标不按键，在她上半身左右来回划 ----------
let patMoves = [];
function patTrack(e) {
  if (e.buttons || dock) return;
  const r = pet.getBoundingClientRect();
  if (e.clientY > r.top + r.height * 0.55) return;
  const now = Date.now();
  patMoves = patMoves.filter((m) => now - m.t < 1200);
  const last = patMoves.at(-1);
  patMoves.push({ t: now, x: e.clientX, dir: last ? Math.sign(e.clientX - last.x) : 0 });
  let flips = 0;
  for (let i = 1; i < patMoves.length; i++)
    if (patMoves[i].dir && patMoves[i - 1].dir && patMoves[i].dir !== patMoves[i - 1].dir) flips++;
  if (flips < 3 || now - lastPat < 4000) return;
  lastPat = now;
  patMoves = [];
  if (sleep === 'asleep') return say(pick(LINES.patSleep), undefined, 3000);
  pokes = [];
  warnedAt = 0;
  say(pick(LINES.pat), 'pat', 3500);
}

// ---------- 右键菜单 ----------
pet.addEventListener('contextmenu', (e) => {
  e.preventDefault();
  bubble.hidden = true;
  menu.hidden = !menu.hidden;
  updateHit();
});
menu.addEventListener('click', (e) => {
  const act = e.target.closest('button')?.dataset.act;
  if (!act) return;
  menu.hidden = true;
  updateHit();
  if (act === 'open') openSite();
  if (act === 'chat') chat(true);
  if (act === 'settings') invoke('open_settings');
  if (act === 'wardrobe') wardrobe();
  if (act === 'quiet') {
    prefs.quiet = !prefs.quiet;
    savePrefs();
    say(prefs.quiet ? '好吧，我安静待着。（安静模式）' : '提醒打开了，我要开始唠叨了哦。', 'idle', 3000);
    renderMenu();
  }
  if (act === 'hide') {
    say(pick(LINES.bye), 'wave', 1500);
    setTimeout(() => (bubble.hidden = true, win?.hide()), 1300);
  }
});
function renderMenu() {
  const site = lineVars().s;
  menu.querySelector('[data-act="open"]').textContent = '🌐 打开' + site;
  pet.title = `戳一下 · 双击打开${site} · 右键菜单`;
  const q = menu.querySelector('[data-act="quiet"]');
  if (q) q.textContent = prefs.quiet ? '🔔 打开提醒' : '🔕 安静模式';
}
addEventListener('keydown', (e) => {
  if (e.key === 'Escape') {
    menu.hidden = bubble.hidden = true;
    updateHit();
  }
});

// ---------- 自己冒话 ----------
function chatLine() {
  const h = new Date().getHours(),
    m = Math.round((Date.now() - startedAt) / 60000);
  const pool = [...LINES.chatAny];
  if (h < 5) pool.push(...LINES.chatNight, ...LINES.chatNight);
  else if (h < 7) pool.push(...LINES.chatEarly);
  else if (h < 11) pool.push(...LINES.chatMorning);
  else if (h < 14) pool.push(...LINES.chatNoon);
  else if (h < 18) pool.push(...LINES.chatAfternoon);
  else if (h < 22) pool.push(...LINES.chatEvening);
  else pool.push(...LINES.chatLate);
  if (m >= 90) pool.push(...LINES.chatLong);
  return fill(pick(pool), { h, m });
}
function chat(force = false) {
  if (sleep) return force && say(pick(LINES.sleepTalk), undefined, 5000);
  const worn = festById(wear()),
    soon = festSoon();
  if (offDay() && Math.random() < 0.3) {
    const line = offLine(outfitInfo(outfitNow()));
    return force ? say(line, wear() || 'smug', 8000) : pop(line, wear() || 'smug', 12000);
  }
  if (worn?.chat && !offDay() && Math.random() < 0.35) return force ? say(pick(worn.chat), wear(), 8000) : pop(pick(worn.chat), wear(), 12000);
  if (soon && Math.random() < 0.25) {
    const line = soon.days === 1 ? `明天就是${soon.fest.name}了！{n} 准备好了没？` : `还有 ${soon.days} 天就是${soon.fest.name}了，嘿嘿。`;
    return force ? say(line, 'excited', 8000) : pop(line, 'excited', 12000);
  }
  const w = weatherLine();
  if (w && Math.random() < 0.4) return force ? say(w[0], w[1], 8000) : pop(w[0], w[1], 12000);
  const line = chatLine();
  const m = /还不睡|恨现在|关灯/.test(line) ? 'meh' : /吃|饿|饭/.test(line) ? 'smug' : pick(['happy', 'smirk', 'idle']);
  force ? say(line, m, 8000) : pop(line, m, 12000);
}

// ---------- 睡觉 ----------
function sleepTick() {
  const night = isNight(),
    now = Date.now();
  if (sleep && sleep !== 'asleep' && now > sleepUntil && menu.hidden) {
    const wasMad = sleep === 'mad';
    sleep = night ? 'asleep' : null;
    if (sleep) {
      lastSleepTalk = now;
      if (wasMad) pop(pick(LINES.backToSleep), 'sleep', 4000);
    }
    setMood(autoMood());
  } else if (!sleep && night && now > sleepUntil && !dragging && menu.hidden) {
    stopRoam();
    sleep = 'asleep';
    lastSleepTalk = now;
    setMood('sleep');
  } else if (sleep === 'asleep' && !night) {
    sleep = null; // 在任务栏下面睡的话，醒了就扒着底边探头
    pop(pick(LINES.wakeUp), 'happy', 8000);
    setMood('happy', 6000);
  }
  if (sleep === 'asleep') {
    spawnZ();
    if (now - lastSleepTalk > rand(8, 15) * 60000) {
      lastSleepTalk = now;
      pop(pick(LINES.sleepTalk), undefined, 6000);
    }
  }
}
function spawnZ() {
  if (matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  const z = document.createElement('span');
  z.className = 'z';
  z.textContent = Math.random() < 0.5 ? 'Z' : 'z';
  z.style.setProperty('--dx', Math.round(rand(-18, 18)) + 'px');
  document.body.append(z);
  setTimeout(() => z.remove(), 3200);
}

// ---------- 在任务栏上方乱跑 ----------
function stopRoam() {
  if (!roam) return;
  cancelAnimationFrame(roam.raf);
  document.body.classList.remove('running');
  roam = null;
}
async function roamTick() {
  const gap = ACTIVITY_GAP[prefs.activity] ?? ACTIVITY_GAP.normal,
    now = Date.now();
  if (!gap) return;
  if (!nextRoam) nextRoam = now + rand(...gap) * 60000;
  if (now < nextRoam || roam) return;
  nextRoam = now + rand(...gap) * 60000;
  if (sleep || dock || dragging || !menu.hidden || !bubble.hidden || down) return;
  await readGeometry();
  if (!area) return;
  const min = area.x - PET_MARGIN,
    max = area.x + area.w - WIN_W + PET_MARGIN;
  // 多半跑到屏幕另一头，偶尔在半路停下；至少跑三分之一个屏幕
  const span = max - min,
    left = pos.x < min + span / 2;
  let to = Math.random() < 0.7 ? (left ? rand(max - span * 0.15, max) : rand(min, min + span * 0.15)) : rand(min, max);
  if (Math.abs(to - pos.x) < span / 3) to = pos.x + (left ? span / 3 : -span / 3);
  to = Math.round(Math.min(max, Math.max(min, to)));
  const from = pos.x,
    ms = (Math.abs(to - from) / 160) * 1000,
    t0 = performance.now();
  roam = { dir: Math.sign(to - from) };
  document.body.classList.add('running');
  setMood('run');
  const runLines = OUTFITS[outfitNow()]?.runLines;
  if (runLines && Math.random() < 0.5) {
    pop(pick(runLines), undefined, Math.min(ms, 5000));
    setMood('run');
  }
  const step = (t) => {
    if (!roam) return;
    const k = Math.min(1, (t - t0) / ms);
    moveTo(from + (to - from) * k, pos.y);
    if (k < 1) roam.raf = requestAnimationFrame(step);
    else {
      stopRoam();
      rememberPos();
      setMood(autoMood());
    }
  };
  roam.raf = requestAnimationFrame(step);
}

// ---------- 躲在边上偷偷玩手机 ----------
let nextPhone = Date.now() + rand(3, 6) * 60000;
function phoneTick() {
  if (Date.now() < nextPhone) return;
  nextPhone = Date.now() + rand(3, 6) * 60000;
  if (dock !== 'left' && dock !== 'right') return;
  if (sleep || dragging || !menu.hidden || !bubble.hidden) return;
  const ms = rand(30, 90) * 1000;
  setMood('peekPhone', ms);
  if (Math.random() < 0.5) pop(pick(LINES.phone), 'peekPhone', 5000);
}

// ---------- 闲着的时候：戴耳机看书、饭点啃饭团、过年拿福袋 ----------
const newYear = (d = new Date()) => d.getMonth() === 0 && d.getDate() <= 7;
let nextIdle = Date.now() + rand(4, 8) * 60000;
function idleTick() {
  if (Date.now() < nextIdle) return;
  nextIdle = Date.now() + rand(6, 12) * 60000;
  if (dock || sleep || dragging || roam || !menu.hidden || !bubble.hidden || Date.now() < moodUntil) return;
  const h = new Date().getHours() + new Date().getMinutes() / 60;
  const meal = (h >= 11.5 && h < 13.5) || (h >= 17.5 && h < 19.5);
  if (meal && Math.random() < 0.5) {
    setMood('onigiri', rand(40, 90) * 1000);
    return pop(pick(LINES.onigiri), 'onigiri', 5000);
  }
  const season = seasonToday();
  if (season && outfitNow() === 'maid' && Math.random() < 0.4) {
    setMood(season.id, rand(60, 150) * 1000);
    return pop(pick(season.lines), season.id, 5000);
  }
  if (newYear() && Math.random() < 0.4) {
    setMood('newyear', rand(60, 120) * 1000);
    return pop(pick(LINES.newYear), 'newyear', 5000);
  }
  setMood('read', rand(60, 180) * 1000);
  if (Math.random() < 0.4) pop(pick(LINES.read), 'read', 5000);
}

// ---------- 天气（设置里填了城市才查；用 open-meteo，不需要密钥） ----------
var weather = null; // { rain, rainTomorrow, max, min, at }
async function weatherTick() {
  const city = (prefs.city || '').trim();
  if (!city) return (weather = null);
  if (weather && weather.city === city && Date.now() - weather.at < 30 * 60000) return;
  try {
    let geo = prefs.geo;
    if (!geo || geo.city !== city) {
      const g = await (await fetch('https://geocoding-api.open-meteo.com/v1/search?count=1&language=zh&name=' + encodeURIComponent(city))).json();
      const r = g.results?.[0];
      if (!r) return (weather = { city, at: Date.now(), error: '找不到这个城市' });
      geo = { city, lat: r.latitude, lon: r.longitude };
      prefs.geo = geo;
      savePrefs();
    }
    const q = new URLSearchParams({
      latitude: geo.lat,
      longitude: geo.lon,
      daily: 'temperature_2m_max,temperature_2m_min,precipitation_probability_max',
      hourly: 'precipitation_probability',
      timezone: 'auto',
      forecast_days: '2',
    });
    const w = await (await fetch('https://api.open-meteo.com/v1/forecast?' + q)).json();
    const now = new Date(),
      hourNow = now.getHours(),
      todayHours = (w.hourly?.precipitation_probability || []).slice(hourNow, 24).filter(Number.isFinite);
    weather = {
      city,
      at: Date.now(),
      rain: todayHours.length ? Math.max(...todayHours) : w.daily?.precipitation_probability_max?.[0] || 0,
      rainTomorrow: w.daily?.precipitation_probability_max?.[1] || 0,
      max: Math.round(w.daily?.temperature_2m_max?.[0]),
      min: Math.round(w.daily?.temperature_2m_min?.[0]),
    };
  } catch {
    weather = { city, at: Date.now(), error: '天气暂时查不到' };
  }
}
// 早上 7–10 点要下雨：提醒一次带伞
function umbrellaTick() {
  const d = new Date(),
    today = d.toDateString();
  if (!weather || weather.error || d.getHours() < 7 || d.getHours() >= 10 || prefs.umbrellaDay === today) return;
  if (sleep || dock || weather.rain < 50) return;
  prefs.umbrellaDay = today;
  savePrefs();
  pop(fill(pick(LINES.umbrella), { p: weather.rain }), 'umbrella', 12000);
}
function weatherLine() {
  if (!weather || weather.error) return null;
  const h = new Date().getHours();
  if (h < 20 && weather.rain >= 50) return [fill(pick(LINES.umbrella), { p: weather.rain }), 'umbrella'];
  if (weather.max >= 28 && h < 18) return [fill(pick(LINES.hot), { t: weather.max }), 'hot'];
  if (weather.min <= 5 && h < 12) return [fill(pick(LINES.cold), { t: weather.min }), 'cold'];
  if (h >= 20 && weather.rainTomorrow >= 50) return [fill(pick(LINES.rainTomorrow), { p: weather.rainTomorrow }), 'umbrella'];
  return null;
}

// ---------- 节日：过了零点换衣服打招呼、飘装饰、大晦日倒数 ----------
function festTick() {
  const d = new Date(),
    f = festById(wear());
  if (f?.hello && !offDay() && !sleep && prefs.festDay !== d.toDateString() + f.id && menu.hidden && bubble.hidden) {
    prefs.festDay = d.toDateString() + f.id;
    savePrefs();
    setMood(autoMood());
    pop(pick(f.hello), f.id, 8000);
  }
  // 大晦日：23:59 开始倒数，零点放烟花
  const y = d.getFullYear();
  if (md(d) === 1231 && d.getHours() === 23 && d.getMinutes() === 59 && prefs.countdown !== y) {
    prefs.countdown = y;
    savePrefs();
    if (sleep) sleep = null;
    say('还有一分钟！！{n}，倒数准备——', 'excited', 20000);
  }
  if (md(d) === 101 && d.getHours() === 0 && d.getMinutes() < 2 && prefs.happyNewYear !== y) {
    prefs.happyNewYear = y;
    savePrefs();
    if (sleep) sleep = null;
    for (let i = 0; i < 6; i++) setTimeout(() => burst(['🎆', '🎇', '✨'], 5, true), i * 700);
    say('🎆 新年快乐！！{n}，今年也请多关照！', 'excited', 15000);
  }
  if (!f?.fx?.length || sleep || dock || dragging || Math.random() < 0.4) return;
  if (matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  for (let i = Math.floor(rand(1, 3)); i > 0; i--) setTimeout(() => fall(pick(f.fx)), rand(0, 2500));
}
// 从窗口上方慢慢飘下来的装饰（不挡鼠标）
// 有画好的装饰图就用图（fx/<名字>-<几号>.webp），没有就用 emoji
const FX_IMG = {
  '❄️': ['snow', 2], '🌸': ['petal', 2], '🍁': ['maple', 2], '⭐': ['star', 2], '💧': ['rain', 2], '🦇': ['bat', 3], '🎆': ['firework', 3], '🎇': ['firework', 3],
  '💗': ['heart', 2], '💝': ['heart', 2], '🏮': ['lantern', 2], '🧧': ['envelope', 2], '🎃': ['pumpkin', 2], '🍡': ['dango', 2], '🫘': ['bean', 2] };
function fxEl(ch) {
  const pic = FX_IMG[ch],
    e = document.createElement(pic ? 'img' : 'span');
  if (pic) {
    e.src = `fx/${pic[0]}-${1 + Math.floor(Math.random() * pic[1])}.webp`;
    e.className = 'pic ' + pic[0];
  } else e.textContent = ch;
  return e;
}
function fall(ch) {
  const e = fxEl(ch);
  e.classList.add('fx');
  e.style.left = Math.round(rand(20, WIN_W - 30)) + 'px';
  e.style.setProperty('--dx', Math.round(rand(-30, 30)) + 'px');
  e.style.animationDuration = rand(4, 6.5).toFixed(1) + 's';
  document.body.append(e);
  setTimeout(() => e.remove(), 7000);
}
// 从她身上往外蹦的（撒豆子、抽签、烟花）
function burst(chars, n, high = false) {
  if (matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  const r = pet.getBoundingClientRect();
  for (let i = 0; i < n; i++) {
    const e = fxEl(pick(chars)),
      a = rand(-Math.PI * 0.95, -Math.PI * 0.05);
    e.classList.add('fx', 'burst');
    e.style.left = Math.round(r.left + r.width / 2 - 8) + 'px';
    e.style.top = Math.round(r.top + (high ? 10 : r.height * 0.45)) + 'px';
    const dist = rand(50, high ? 110 : 90);
    e.style.setProperty('--dx', Math.round(Math.cos(a) * dist) + 'px');
    e.style.setProperty('--dy', Math.round(Math.sin(a) * dist) + 'px');
    document.body.append(e);
    setTimeout(() => e.remove(), 1400);
  }
}
// 👘 衣柜：点一套就锁定穿它；「自动换装」让她按节日、晚上自己换。考试周的必胜头巾两周后自动摘
function wardrobe() {
  const fests = FESTS.filter((f) => f.kind !== 'manual' && (!prefs.wardrobeLocked || prefs.wardrobe.includes(f.id))),
    locked = FESTS.filter((f) => f.kind !== 'manual').length - fests.length,
    now = outfitNow(),
    auto = prefs.wardrobeMode !== 'lock';
  const choose = (id) => () => {
    if (id === 'auto') {
      prefs.wardrobeMode = 'auto';
      prefs.outfit = 'maid';
    } else if (id === 'hisshou') {
      prefs.examUntil = Date.now() + 14 * 86400000;
      prefs.wardrobeMode = 'auto';
    } else {
      prefs.wardrobeMode = 'lock';
      prefs.outfit = id;
      if (id === 'maid') prefs.examUntil = 0;
    }
    savePrefs();
    closeBubble();
    setMood(autoMood());
    if (id === 'auto') return say('好，那我自己看日子换衣服。节日穿节日的，晚上穿睡衣，冷天穿冬装。', 'happy', 5000);
    if (id === 'hisshou') return say(pick(festById('hisshou').hello) + '（两周后自动摘下）', 'hisshou', 6000);
    if (id === 'maid') return say('换回女仆装啦，还是这身最舒服。（锁定了，节日也不换哦）', 'happy', 5000);
    say(offDay() ? offLine(outfitInfo(id)) : `换好了！${outfitName(id)}，好看吗？`, 'smug', 5000);
  };
  const mark = (id, name) => [(!auto && now === id ? '✓ ' : '') + name, choose(id)];
  ask(
    `衣柜 · 现在：${outfitName(now)}${auto ? '（自动）' : '（锁定）'}${locked ? `，还有 ${locked} 套没见过` : ''}`,
    [
      [(auto ? '✓ ' : '') + '🔄 自动换装', choose('auto')],
      ...Object.keys(OUTFITS).map((id) => mark(id, OUTFITS[id].name)),
      ...fests.map((f) => mark(f.id, f.name)),
      ['🔥 考试周', choose('hisshou')],
      ['关上', closeBubble],
    ],
  );
  bubble.classList.add('wardrobe');
  bubble.querySelector('.acts')?.classList.add('wrap');
}

// ---------- 启动 ----------
(async () => {
  invoke('set_game_mode', { on: !!prefs.gameMode });
  weatherTick();
  setInterval(weatherTick, 10 * 60000);
  await readGeometry();
  if (prefs.pos && area) {
    // 回到上次的位置（屏幕变了就夹在工作区里）
    moveTo(clampX(prefs.pos.x), clampY(prefs.pos.y));
    pos = { x: clampX(prefs.pos.x), y: clampY(prefs.pos.y) };
  }
  applyDock();
  sleepTick();
  setMood(autoMood());
  renderMenu();
  updateHit();
  setTimeout(() => {
    if (sleep) return;
    const f = festById(wear());
    if (f?.hello && !offDay()) {
      prefs.festDay = new Date().toDateString() + f.id;
      savePrefs();
      return pop(pick(f.hello), f.id, 8000);
    }
    newYear() ? pop(pick(LINES.newYear), 'newyear', 8000) : pop(pick(LINES.hello), 'excited', 6000);
  }, 800);
})();
let lastOutfit = outfitNow();
setInterval(() => {
  sleepTick();
  // 衣服变了（入夜换睡衣、过了零点换节日衣服）：就算表情没变也要换图
  const o = outfitNow();
  if (o !== lastOutfit) {
    lastOutfit = o;
    if (!dragging && !roam && Date.now() > moodUntil) setMood(autoMood());
    else setMood(mood, Math.max(0, moodUntil - Date.now()));
    if (o === 'winter' && !sleep && prefs.wardrobeMode !== 'lock')
      pop('（裹上大衣和围巾）今天好冷……{n} 出门也多穿一件。', 'cold', 8000);
    if (o === 'pajamas' && !sleep && prefs.wardrobeMode !== 'lock')
      pop('（换上睡衣，抱着鲸鱼枕头）……我先准备睡了，{n} 也别熬太晚。', 'idle', 8000);
  }
  roamTick();
  if (!dragging && !roam && Date.now() > moodUntil && mood !== autoMood()) setMood(autoMood());
  phoneTick();
  idleTick();
  umbrellaTick();
  festTick();
  if (Date.now() > nextChat) {
    nextChat = Date.now() + rand(...chatGap()) * 60000;
    chat();
  }
  updateHit();
}, 3000);
addEventListener('resize', updateHit);
