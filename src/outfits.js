// 衣服和立绘：希可现在穿哪套、某个表情/动作该显示哪张图。
// 立绘都是整张图（不分层）。每套衣服只画了一部分动作，缺的按下面的顺序找，**绝不换回女仆装**：
//   1. 这套衣服画了这个动作 → 用它
//   2. alias 里写了用哪张代替（比如睡衣没画「屑笑」以外的坏笑，就用「屑笑」）→ 用那张
//   3. NEAR 里相近的动作（探头 ↔ 其他探头、迷糊 → 睡觉……）这套衣服有 → 用那张
//   4. 用这套衣服的待机图顶上，靠 CSS 动画演：被拎起来照样蹬腿、跑步照样蹦、
//      躲在屏幕边就把整张图往屏幕外推一半（standIn），看起来也是在探头
// 文件放在 sprites/<衣服>/<动作>.webp；女仆装就是 sprites/ 下面原来那些图（什么动作都有）。
// 节日/季节衣服的待机图还是 sprites/<节日>.webp，补画的动作放 sprites/<节日>/<动作>.webp，
// 在 festivals.js 那一项里写 has（和 alias、frames），跟这里的成套衣服一样回退。
// 新画的衣服：加一项到 OUTFITS，把画好的动作写进 has，缺的写 alias，其他的自动回退。
// 每套衣服还可以写 say（专属台词，见 outfitLine）和 fx（穿着时身边飘的装饰）。
const NEAR = {
  peekPhone: 'peek', peekCheek: 'peek', peekHead: 'peek', peekAngry: 'peek', peek: 'peekSleep', peekSleep: 'peek',
  sleepBottom: 'sleep', sleepy: 'sleep', wake: 'angry', angry: 'wake', excited: 'happy', surprised: 'happy',
  smirk: 'smug', bleh: 'smug', newyear: 'happy', hot: 'meh', cold: 'meh', umbrella: 'idle', onigiri: 'happy',
};
const DOCKED = new Set(['peek', 'peekPhone', 'peekCheek', 'peekHead', 'peekAngry', 'peekSleep']);
const BOTTOM = new Set(['peekBottom', 'sleepBottom']);
const OUTFITS = {
  maid: { name: '女仆装' }, // 原来所有的立绘
  pajamas: {
    name: '睡衣',
    off: '晚上', // 不是日子却穿着时说「明明不是晚上……」
    when: () => isNight(),
    has: ['idle', 'sleepy', 'wake', 'smug', 'pat', 'sleep', 'peekSleep', 'dangle', 'happy', 'wave', 'read'],
    alias: { peek: 'peekSleep', peekPhone: 'peekSleep', peekCheek: 'peekSleep', peekHead: 'peekSleep', smirk: 'smug', bleh: 'smug', excited: 'happy', meh: 'idle', pout: 'idle', surprised: 'sleepy', angry: 'wake' },
    fx: ['⭐'],
    say: {
      poke: [['（抱着枕头）……睡衣时间不营业。', 'sleepy'], ['都换睡衣了还戳？{n} 少爷是不想睡吗？', 'smug']],
      pat: ['……睡前摸头，可以。就一下。', '（把睡帽往下拉）……再摸就睡着了哦。'],
      dropped: [['（拖鞋掉了一只）……{n}！我的鲸鱼拖鞋！', 'pout']],
      angry: ['💢 穿着睡衣也会生气的！！'],
      chat: [['（打哈欠）……今天到这里吧，{n}，明天的事明天再说。', 'sleepy']],
    },
  },
  yukata: {
    name: '浴衣',
    off: '夏天',
    when: (d) => inRange(d, 701, 831),
    has: ['idle', 'wave', 'smug', 'angry', 'pat', 'happy', 'run', 'peek', 'dangle', 'read', 'onigiri', 'surprised', 'sleep'],
    frames: { run: ['run1', 'run2'] }, // 跑步两帧轮流换
    alias: {
      smirk: 'smug', bleh: 'smug', meh: 'idle', pout: 'angry', excited: 'happy', wake: 'angry',
      peekPhone: 'peek', peekCheek: 'peek', peekHead: 'peek', peekAngry: 'peek',
    },
    fx: ['🎐', '🎆'],
    say: {
      poke: [['（扇团扇）别戳，浴衣穿起来很费劲的。', 'meh'], ['苹果糖分你一口？……骗你的，自己买。', 'smirk']],
      pat: ['……发型是特意盘的，轻点摸。', '（扇着团扇）……嗯，可以，再一下。'],
      dropped: [['腰带要松了啦！{n}！', 'pout']],
      angry: ['💢 浴衣也挡不住本鲸的怒气！'],
      chat: [['夏天就该穿浴衣去祭典……{n}，你陪我？', 'happy']],
    },
  },
  // 下面四套都画了同一份 11 张（待机、开心、屑笑、生气、摸头、挥手、吓一跳、拎起、探头、跑步两帧）
  gym: {
    name: '体操服',
    has: ['idle', 'happy', 'smug', 'angry', 'pat', 'wave', 'surprised', 'dangle', 'peek', 'run'],
    frames: { run: ['run1', 'run2'] },
    alias: { pout: 'angry', wake: 'angry', meh: 'idle' },
    runLines: ['一、二、一、二！热身跑起来！', '（跑圈）还有三圈……{n} 你也来跑！'],
    fx: ['💦'],
    say: {
      poke: [['体育课不许摸鱼！……我说的是你。', 'smug'], ['（压腿）……够、够不着，别看！', 'pout']],
      pat: ['……出汗了，别摸啦。', '摸头可以，但等会儿你也要跑两圈。'],
      dropped: [['我在热身！不是给你拎着玩的！', 'angry']],
      angry: ['💢 体操服状态的本鲸，生气起来会跑圈追你的！'],
      chat: [['{n}，坐了一天了吧？站起来做十个深蹲。……我做一个就行。', 'smug']],
    },
  },
  jog: {
    name: '慢跑服',
    has: ['idle', 'happy', 'smug', 'angry', 'pat', 'wave', 'surprised', 'dangle', 'peek', 'run', 'hot', 'onigiri'], // onigiri：啃吐司
    frames: { run: ['run1', 'run2'] },
    alias: { pout: 'angry', wake: 'angry', meh: 'idle' },
    runLines: ['（叼着吐司）要迟到了要迟到了——！', '（嘴里叼着面包）唔唔唔！（让一让！）', '早饭边跑边吃才是青春！……{n} 别学我。'],
    fx: ['🍞', '💦'],
    say: {
      poke: [['（原地小跑）别挡道，晨跑中！', 'smug'], ['吐司还没吃完，{n} 别戳！', 'onigiri']],
      pat: ['……跑完步再摸，头发都是汗。', '（停下来喘气）……嗯，这个可以。'],
      dropped: [['我的吐司！掉了啦！！', 'surprised']],
      angry: ['💢 打断别人晨跑是要被吐司砸的！'],
      chat: [['今天走够八千步了没，{n}？……我没走，我是用跑的。', 'smug']],
    },
  },
  winter: {
    name: '冬装',
    off: '冬天',
    when: (d) => inRange(d, 1201, 229),
    has: ['idle', 'happy', 'smug', 'angry', 'pat', 'wave', 'surprised', 'dangle', 'peek', 'run', 'cold'],
    frames: { run: ['run1', 'run2'] },
    alias: { pout: 'angry', wake: 'angry', meh: 'cold' },
    runLines: ['好冷好冷，跑起来就暖和了！', '（围巾飞起来）等等我的帽子——！'],
    fx: ['❄️'],
    say: {
      poke: [['（缩进围巾里）……冷，别戳。', 'cold'], ['{n} 的手好冰！不许戳我脖子！', 'surprised']],
      pat: ['……隔着帽子摸也算数。', '（把围巾拉高）……就、就允许你暖一下手。'],
      dropped: [['帽子掉了！快帮我捡！冷死了！', 'pout']],
      angry: ['💢 冬天的怒气是冰做的！很疼的！'],
      chat: [['今天好冷……{n} 出门多穿一件，别逞强。', 'cold']],
    },
  },
  lab: {
    name: '白大褂',
    has: ['idle', 'happy', 'smug', 'angry', 'pat', 'wave', 'surprised', 'dangle', 'peek', 'run', 'read'], // read：看实验记录本
    frames: { run: ['run1', 'run2'] },
    alias: { pout: 'angry', wake: 'angry', meh: 'idle' },
    runLines: ['实验要炸了！快跑！！', '（抱着锥形瓶）通风橱！通风橱在哪！'],
    fx: ['🫧', '🧪'],
    say: {
      poke: [['实验中！别碰我手里的锥形瓶！', 'surprised'], ['（推眼镜）……这个反应的产率，{n} 算出来了吗？', 'smug']],
      pat: ['……护目镜别碰歪。', '（停下滴定）……嗯，滴定终点前允许摸一下。'],
      dropped: [['试剂要洒了！！实验记录本也要写上「被拎起来」吗？', 'surprised']],
      angry: ['💢 实验室里不许打闹！……我说的是你，{n}。'],
      chat: [['实验报告写了没？数据别等到最后一天才整理。', 'smug'], ['（翻实验记录本）……本鲸的实验，从来不炸。（远处一声巨响）', 'surprised']],
    },
  },
};
// 节日/季节衣服（festivals.js 里那些）默认只有一张待机图；写了 has 的按 has 找，缺的照样回退
const outfitInfo = (id) => OUTFITS[id] || festById(id) || OUTFITS.maid;
const outfitName = (id) => outfitInfo(id).name;
function outfitHas(id) {
  if (id === 'maid') return null;
  const has = outfitInfo(id).has || [];
  return has.includes('idle') ? has : ['idle', ...has];
}
// 这套衣服的某个动作实际用哪张（女仆装返回 null：什么都有）
function outfitKey(outfit, m) {
  const has = outfitHas(outfit);
  if (!has) return null;
  if (has.includes(m)) return m;
  const a = outfitInfo(outfit).alias?.[m];
  if (a && has.includes(a)) return a;
  for (let k = NEAR[m], n = 0; k && n < 3; k = NEAR[k], n++) if (has.includes(k)) return k;
  return 'idle';
}
// 某套衣服的某个动作 → 图片路径（跑步这种多帧的返回数组）
function spriteFor(outfit, m) {
  // 指名要某套节日衣服的那张（抽签、季节闲逛）：只在穿着女仆装或正好是那套时换，别的衣服不换
  if (festById(m)) return outfit === 'maid' || outfit === m ? `sprites/${m}.webp` : spriteFor(outfit, 'idle');
  const k = outfitKey(outfit, m);
  if (k === null) return `sprites/${m === 'angry' ? 'strike' : m}.webp`; // 女仆装
  if (festById(outfit) && k === 'idle') return `sprites/${outfit}.webp`; // 节日衣服的待机图
  const fr = outfitInfo(outfit).frames?.[k];
  return fr ? fr.map((f) => `sprites/${outfit}/${f}.webp`) : `sprites/${outfit}/${k}.webp`;
}
// 躲在边上却没有探头图、只能拿整张图顶上时：'side' 往屏幕外推一半，'bottom' 往下沉一半
function standInFor(outfit, m) {
  const k = outfitKey(outfit, m);
  if (k === null || festById(m)) return '';
  if (DOCKED.has(m) && !DOCKED.has(k)) return 'side';
  if (BOTTOM.has(m) && !BOTTOM.has(k)) return 'bottom';
  return '';
}

// ---------- 衣服专属台词 ----------
// say: { poke, pat, dropped, angry, chat }，每条是 [台词, 表情] 或只写台词（表情按 moodFor 挑）。
// 穿着这身时，戳、摸头、放下来、生气、自己冒话有一定概率说这身的台词。
function outfitLine(outfit, kind) {
  const list = outfitInfo(outfit)?.say?.[kind];
  if (!list?.length) return null;
  const x = pick(list);
  return Array.isArray(x) ? x : [x, moodFor(x)];
}
// 补画动作的优先级：越靠前越常出现。art-todo 按这个列缺图
const ART_CORE = ['happy', 'smug', 'angry', 'pat', 'dangle', 'surprised', 'peek', 'wave', 'run'];
