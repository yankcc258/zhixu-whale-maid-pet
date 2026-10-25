// 红白机风格音效：没有音频文件，全部用 Web Audio 当场合成（方波、三角波、一点白噪声），
// 所以安装包不变大，音量也随便调。只在你碰她（戳、摸头、拎、放、双击、开菜单）
// 和「通关」（衣柜收到新衣服）时响，自己冒话不出声。音量在设置里（关 / 小 / 中 / 大），安静模式也不响。
// 曲子都是露娜现编的几个音，不是哪个游戏里的。
// eslint-disable-next-line no-unused-vars
const SFX = (() => {
  const VOL = { off: 0, low: 0.16, mid: 0.32, high: 0.55 };
  let level = 'low',
    muted = false,
    unlocked = false, // 浏览器规定：页面被点过（或按过键）以后才准出声，之前的音效直接跳过
    ctx = null,
    master = null;
  for (const ev of ['pointerdown', 'keydown']) addEventListener(ev, () => (unlocked = true), { capture: true, passive: true });

  // 音名 → 频率（A4 = 440）。'C5' 'G#4' 'Bb3' 这种写法
  const SEMI = { C: -9, D: -7, E: -5, F: -4, G: -2, A: 0, B: 2 };
  function hz(n) {
    if (typeof n === 'number') return n;
    const m = /^([A-G])([#b]?)(\d)$/.exec(n);
    let s = SEMI[m[1]] + (m[2] === '#' ? 1 : m[2] === 'b' ? -1 : 0) + (Number(m[3]) - 4) * 12;
    return 440 * 2 ** (s / 12);
  }

  function ready() {
    if (!VOL[level] || muted || !unlocked || document.hidden) return null; // 藏进托盘时不出声
    try {
      if (!ctx) {
        const AC = window.AudioContext || window.webkitAudioContext;
        if (!AC) return null;
        ctx = new AC();
        master = ctx.createGain();
        master.gain.value = VOL[level];
        // 几个音叠在一起时压一下，不会爆
        const comp = ctx.createDynamicsCompressor();
        master.connect(comp).connect(ctx.destination);
      }
      // 挂起了就叫醒（比如系统休眠过）
      if (ctx.state === 'suspended') ctx.resume().catch(() => {});
      return ctx;
    } catch {
      return null;
    }
  }

  // 一个音：f 频率（或音名；[f0, f1] 表示从 f0 滑到 f1），t 从现在起几秒后开始，d 长度（秒），
  // type 波形（square 方波最像红白机，triangle 三角波软一点），g 响度（相对）
  function tone(c, { f, t = 0, d = 0.08, type = 'square', g = 1, decay = true }) {
    const o = c.createOscillator(),
      a = c.createGain(),
      at = c.currentTime + t;
    o.type = type;
    const [f0, f1] = Array.isArray(f) ? f.map(hz) : [hz(f), null];
    o.frequency.setValueAtTime(f0, at);
    if (f1) o.frequency.exponentialRampToValueAtTime(f1, at + d);
    a.gain.setValueAtTime(0.0001, at);
    a.gain.exponentialRampToValueAtTime(g * 0.5, at + 0.006);
    if (decay) a.gain.exponentialRampToValueAtTime(0.0001, at + d);
    else {
      a.gain.setValueAtTime(g * 0.5, at + d - 0.015);
      a.gain.exponentialRampToValueAtTime(0.0001, at + d);
    }
    o.connect(a).connect(master);
    o.start(at);
    o.stop(at + d + 0.02);
  }
  // 一声「噗」：白噪声 + 低通，落地、撞到用
  function thud(c, { t = 0, d = 0.09, g = 1, cut = 900 }) {
    const n = Math.ceil(c.sampleRate * d),
      buf = c.createBuffer(1, n, c.sampleRate),
      ch = buf.getChannelData(0);
    for (let i = 0; i < n; i++) ch[i] = (Math.random() * 2 - 1) * (1 - i / n) ** 2;
    const s = c.createBufferSource(),
      lp = c.createBiquadFilter(),
      a = c.createGain(),
      at = c.currentTime + t;
    s.buffer = buf;
    lp.type = 'lowpass';
    lp.frequency.value = cut;
    a.gain.value = g * 0.8;
    s.connect(lp).connect(a).connect(master);
    s.start(at);
  }
  // 一串音：每个 [音名, 长度(秒), 可选响度]，顺着排
  function seq(c, notes, type = 'square', gap = 0.01) {
    let t = 0;
    for (const [f, d, g = 1] of notes) {
      tone(c, { f, t, d, type, g });
      t += d + gap;
    }
  }

  const S = {
    // 戳一下：两个很短的音，像按了下按钮
    poke: (c) => seq(c, [['E6', 0.045], ['A6', 0.06]]),
    // 摸头：三角波，软软地往上爬三格
    pat: (c) => seq(c, [['C5', 0.09, 0.8], ['E5', 0.09, 0.8], ['G5', 0.16, 0.9]], 'triangle'),
    // 被拎起来：「咻」一下往上滑
    pickup: (c) => tone(c, { f: ['D4', 'A5'], d: 0.17, g: 0.9 }),
    // 落地：噗（噪声）+ 低音往下坠
    land: (c) => {
      thud(c, { d: 0.08, g: 1, cut: 700 });
      tone(c, { f: ['G3', 'C2'], d: 0.13, g: 0.9 });
    },
    // 吓一跳：一个尖的「！」
    startle: (c) => seq(c, [['B6', 0.04], ['E7', 0.07]]),
    // 双击欢呼 / 蹦起来：往上一串短琶音
    cheer: (c) => seq(c, [['C5', 0.055], ['E5', 0.055], ['G5', 0.055], ['C6', 0.14]]),
    // 通关！衣柜收到新衣服：露娜编的一小段结束曲
    fanfare: (c) => seq(c, [['G5', 0.09], ['E5', 0.09], ['C5', 0.09], ['G5', 0.09], ['A5', 0.13], ['G5', 0.06], ['C6', 0.4, 1.1]], 'square', 0.015),
    // 被吵醒发火：低低的「嗡」，带一点抖
    angry: (c) => {
      tone(c, { f: ['A2', 'G2'], d: 0.22, type: 'sawtooth', g: 0.55 });
      tone(c, { f: ['A2', 'G2'], d: 0.22, type: 'square', g: 0.25 });
    },
    // 睡着了：三角波，轻轻地往下走
    sleep: (c) => seq(c, [['E5', 0.14, 0.5], ['C5', 0.14, 0.5], ['G4', 0.3, 0.5]], 'triangle', 0.03),
    // 迷迷糊糊醒来：往上，但很轻
    wake: (c) => seq(c, [['G4', 0.1, 0.5], ['C5', 0.1, 0.5], ['E5', 0.18, 0.6]], 'triangle', 0.03),
    // 打开菜单 / 点菜单：咔哒
    menu: (c) => tone(c, { f: 'C7', d: 0.03, g: 0.6 }),
    // 跑完停下喘气：两声短的
    pant: (c) => seq(c, [['E4', 0.06, 0.5], ['D4', 0.06, 0.5]], 'triangle', 0.08),
    // 挥手再见
    bye: (c) => seq(c, [['E5', 0.08], ['C5', 0.14]], 'triangle'),
  };

  // 放一个音效（名字见上面）。没开声音 / 安静模式 / 浏览器不支持就什么也不做
  function play(name) {
    const c = S[name] && ready();
    if (!c) return;
    try {
      S[name](c);
    } catch (e) {
      console.warn('音效出错：', name, e);
    }
  }
  // 音量档：'off' | 'low' | 'mid' | 'high'
  function setLevel(l) {
    level = VOL[l] === undefined ? 'low' : l;
    if (master) master.gain.value = VOL[level];
  }
  // 安静模式：连带不出声
  const setMuted = (m) => (muted = !!m);
  const on = () => !!VOL[level] && !muted;
  return { play, setLevel, setMuted, on, names: Object.keys(S) };
})();
