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
  nextChat = Date.now() + rand(...chatGap()) * 60000;
  nextRoam = 0;
  if (sleep && !isNight()) sleep = null;
  setMood(autoMood());
});
// 台词里的 {n}（称呼）和 {s}（网站名）
function lineVars() {
  return { n: (prefs.name || '').trim() || 'Yank', s: (prefs.siteName || '').trim() || '知序' };
}
function openSite() {
  const url = (prefs.siteUrl || '').trim();
  return invoke('open_zhixu', { url: /^https?:\/\//.test(url) ? url : null });
}
const ACTIVITY_GAP = { calm: null, normal: [4, 8], lively: [0.75, 1.6] }; // 分钟
const CHAT_GAP = { low: [45, 90], mid: [20, 45], high: [8, 15] };
const chatGap = () => CHAT_GAP[prefs.chatty] || CHAT_GAP.mid;
const rand = (a, b) => a + Math.random() * (b - a);
function isNight(d = new Date()) {
  if (!prefs.sleep || prefs.sleep === 'off') return false;
  const [a, b] = prefs.sleep.split('-').map(Number),
    h = d.getHours();
  return a < b ? h >= a && h < b : h >= a || h < b;
}

// ---------- 状态 ----------
let mood = 'idle',
  moodUntil = 0,
  dock = prefs.dock === 'left' || prefs.dock === 'right' ? prefs.dock : null,
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
  return 'idle';
}
function setMood(m, ms) {
  if (dragging) m = 'dangle';
  else if (dock) m = 'peek';
  else if (sleep === 'asleep' && m !== 'pat') m = 'sleep';
  else if (sleep === 'groggy' && m !== 'wake') m = 'sleepy';
  else if (sleep === 'mad') m = 'wake';
  mood = m;
  moodUntil = ms ? Date.now() + ms : 0;
  const src = `sprites/${m === 'angry' ? 'strike' : m}.webp`;
  if (img.getAttribute('src') !== src) img.src = src;
  document.body.classList.toggle('flip', (dock === 'left') !== (m === 'run' && roam?.dir > 0));
  document.body.classList.toggle('asleep', m === 'sleep');
  document.body.classList.toggle('angry', m === 'angry' || m === 'wake');
}

// ---------- 气泡和菜单 ----------
function say(text, m, ms = 4500) {
  menu.hidden = true;
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
  if (dock && area) moveTo(dock === 'right' ? area.x + area.w - WIN_W + PET_MARGIN : area.x - PET_MARGIN, pos.y);
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
      document.body.classList.remove('dock-left', 'docked');
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
  else dock = null;
  if (!dock) moveTo(clampX(pos.x), clampY(pos.y));
  applyDock();
  rememberPos();
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
  const h = new Date().getHours();
  if (h < 5) return say(fill(pick(LINES.pokeNight), { h }), 'meh', 3500);
  if (h < 8 && Math.random() < 0.6) return say(pick(LINES.pokeMorning), 'idle', 3500);
  say(pick(LINES.poke), pick(['happy', 'happy', 'smug', 'smirk', 'bleh']), 3500);
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
  ], 'smug');
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
  say(pick(LINES.summoned), sleep ? undefined : 'happy', 4000);
});

pet.addEventListener('dblclick', () => {
  say(pick(LINES.openZhixu), sleep ? undefined : 'smug', 2500);
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
  if (act === 'quiet') {
    prefs.quiet = !prefs.quiet;
    savePrefs();
    say(prefs.quiet ? '好吧，我安静待着。（安静模式）' : '提醒打开了，我要开始唠叨了哦。', 'idle', 3000);
    renderMenu();
  }
  if (act === 'hide') win?.hide();
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
    sleep = null;
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
  let to = rand(min, max);
  if (Math.abs(to - pos.x) < 200) to = pos.x + (to > pos.x ? 200 : -200);
  to = Math.round(Math.min(max, Math.max(min, to)));
  const from = pos.x,
    ms = (Math.abs(to - from) / 160) * 1000,
    t0 = performance.now();
  roam = { dir: Math.sign(to - from) };
  document.body.classList.add('running');
  setMood('run');
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

// ---------- 启动 ----------
(async () => {
  invoke('set_game_mode', { on: !!prefs.gameMode });
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
  setTimeout(() => (sleep ? null : pop(pick(LINES.hello), 'happy', 6000)), 800);
})();
setInterval(() => {
  sleepTick();
  roamTick();
  if (!dragging && !roam && Date.now() > moodUntil && mood !== autoMood()) setMood(autoMood());
  if (Date.now() > nextChat) {
    nextChat = Date.now() + rand(...chatGap()) * 60000;
    chat();
  }
  updateHit();
}, 3000);
addEventListener('resize', updateHit);
