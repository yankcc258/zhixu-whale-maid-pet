// Live2D 版希狐。只在穿着做成 Live2D 的衣服（MODELS 里的）、站着的时候用；躲在屏幕边、跑步、看书、
// 啃饭团这些没做成 Live2D 的动作，还有没做成 Live2D 的衣服，还是换回立绘图。加载失败（显卡不支持 WebGL 之类）就一直用立绘，什么都不坏。
// 模型在 live2d/seeko/，运行库在 vendor/（Cubism Core 是 Live2D 的专有许可，见 vendor/README.md）。
// eslint-disable-next-line no-unused-vars
const L2D = (() => {
  // 桌宠的心情 → 模型的表情（null = 不加表情，只放待机动作）
  const EXP = {
    idle: null,
    run: null, // 跑动：Live2D 走路循环（往右跑时画布镜像，见 pet.js 的 flip）
    happy: 'happy',
    excited: 'sparkle',
    wave: 'grin',
    newyear: 'sparkle',
    smug: 'smug',
    smirk: 'smug',
    bleh: 'wink',
    angry: 'angry',
    wake: 'dazed',
    pat: 'blush',
    sleepy: 'sleepy',
    sleep: 'sleepy',
    surprised: 'surprised',
    dangle: 'teary',
    pout: 'pout',
    meh: 'deadpan',
    hot: 'dazed',
    cold: 'puff',
  };
  // 心情刚变成这个时顺便做的动作（motions/ 里的分组）；之后回到随机的待机动作
  const ACT = {
    wave: 'Wave',
    happy: 'Hop',
    excited: 'Cheer',
    newyear: 'Cheer',
    surprised: 'Flinch',
    sleepy: 'Slump',
    sleep: 'Slump',
    angry: 'Shake',
    wake: 'Stretch',
    pat: 'Shy',
    smug: 'Tilt',
    smirk: 'Tilt',
    pout: 'Kick',
    meh: 'Kick',
    bleh: 'Tilt',
    dangle: 'Hang',
    run: 'Walk',
  };
  // 全身像比立绘（半身大头）小，所以 Live2D 时 #pet 加高到 170×180（style.css 的 body.live2d），
  // 头顶那一截和气泡叠一点点没关系。人只有 135 宽，左右各留一截，转头时耳鳍和头发不会被切掉
  const W = 170,
    H = 180;
  // 眼珠：新身体的眼珠几乎占满眼白，骨架里的眼珠位移是给旧的小眼睛放大过的，这里缩回去，
  // 不然一转眼就露出一大片眼白、像在瞪人
  const EYE_GAIN = 0.4;
  // 头和身子：v09 骨架里歪头的轴心已经在脖子上、转头时下巴跟着脖子走，所以转头只轻轻打一点折（HEAD_GAIN），
  // 身子跟着头转一部分（BODY_FOLLOW），再把整个人以脚底为轴跟着身体的歪斜倾一下（BODY_TILT 度 / 每单位 ParamBodyAngleZ，最多 MAX_TILT 度）
  const HEAD_GAIN = 0.8,
    BODY_FOLLOW = 0.3,
    BODY_TILT = 0.4,
    MAX_TILT = 4;
  // 这几个表情是闭着眼的（见 live2d/seeko/expressions/）；模型自带的自动眨眼存在 blinks 里
  const EYES_SHUT = new Set(['happy', 'smug', 'shy', 'sleepy']);
  const blinks = new WeakMap();
  // 做成 Live2D 的衣服（桌宠的衣服 id → 模型）。每套衣服一个模型：同一副骨架、同样的参数，
  // 只有贴图和网格不一样，所以动作、表情、物理都共用 live2d/seeko/ 里的那一份。
  // 没在这里的衣服照旧用立绘。
  const MODELS = {
    maid: 'live2d/seeko/seeko.model3.json',
    pajamas: 'live2d/seeko/seeko_pajamas.model3.json', // 睡衣（晚上、睡觉时自动换上）
    winter: 'live2d/seeko/seeko_winter.model3.json', // 冬装（最高气温不到 10°C）
    kotatsu: 'live2d/seeko/seeko_kotatsu.model3.json', // 被炉（12～2 月；下半身画在被炉里，不跳）
  };
  // 坐在被炉里跳不起来：这几套衣服把「蹦一下」换成点头、「欢呼」换成挥手
  const NO_HOP = new Set(['kotatsu']);
  // 被炉桌画在下半身的槽位里，身子上下、腿摆动会把桌子一起带走：这几套衣服把这些参数钉在 0
  const FROZEN = { kotatsu: ['ParamBodyAngleY', 'ParamLegL', 'ParamLegR'] };
  // 拖着走时整个人往后仰（拎着她横着跑）：目标值由 pet.js 按拖动速度给，这里慢慢追上去
  let swayTarget = 0,
    swayNow = 0,
    finNow = 0;
  // 像素模式（红白机画风）：画布按低分辨率画（每个格子约 2 个 CSS 像素，凑成整数个屏幕像素，
  // 格子才会一样大），再交给 CSS 的 image-rendering: pixelated 放大成马赛克；颜色用下面的着色器压成
  // 明暗 LEVELS 级（色相、饱和度留着，不然偏灰的蓝头发会变成灰紫色），半透明边缘一刀切掉，格子才会干干净净。
  // 模型本身、动作、表情都不变，只是画出来的样子变了。170×180 的她大约是 70～85 格高
  const PIX_CSS = 2,
    LEVELS = 7;
  const PIXEL_FRAG = `
precision mediump float;
varying vec2 vTextureCoord;
uniform sampler2D uSampler;
uniform float levels;
void main() {
  vec4 c = texture2D(uSampler, vTextureCoord);
  if (c.a < 0.5) { gl_FragColor = vec4(0.0); return; }
  vec3 rgb = c.rgb / c.a;
  float y = dot(rgb, vec3(0.299, 0.587, 0.114));
  float yq = floor(y * levels + 0.5) / levels;
  gl_FragColor = vec4(clamp(yq + (rgb - y) * 1.15, 0.0, 1.0), 1.0);
}`;
  let pixel = false,
    posterize = null;
  let canvas = null,
    app = null,
    model = null, // 现在台上的那个
    cur = '', // 它是哪套衣服
    state = 'off', // 'off' | 'loading' | 'ready' | 'failed'（运行库和画布）
    curExp = undefined,
    lastMood = '',
    talkUntil = 0,
    lookAt = 0;
  const models = {}, // 衣服 id → 加载好的模型
    pending = {}, // 衣服 id → 正在加载的 Promise
    broken = new Set(); // 加载失败的衣服，不再重试，一直用立绘

  // 某套衣服的模型加载好以后调一下（桌宠那边重新摆一次表情，从立绘换成 Live2D）
  let onModel = null;

  async function load() {
    if (state !== 'off') return;
    state = 'loading';
    try {
      if (!window.PIXI?.live2d || !window.Live2DCubismCore) throw new Error('运行库没加载');
      canvas = document.createElement('canvas');
      canvas.id = 'l2d';
      canvas.hidden = true;
      document.getElementById('pet').appendChild(canvas);
      app = new PIXI.Application({
        view: canvas,
        width: W,
        height: H,
        backgroundAlpha: 0,
        antialias: true,
        resolution: Math.min(window.devicePixelRatio || 1, 2),
        autoDensity: true,
      });
      app.ticker.maxFPS = 30; // 桌宠不需要 60 帧，省电
      applyPixel();
      state = 'ready';
      await ensure('maid'); // 女仆装先加载好，其他衣服用到时再加载
    } catch (e) {
      console.warn('Live2D 加载失败，用立绘：', e);
      state = 'failed';
      canvas?.remove();
      canvas = null;
    }
  }

  // 开/关像素模式。还没建画布就先记着，建好时再套上
  function setPixel(on) {
    pixel = !!on;
    if (app) applyPixel();
  }
  function applyPixel() {
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const block = Math.max(2, Math.round(PIX_CSS * dpr)); // 一格几个屏幕像素
    const res = pixel ? dpr / block : dpr;
    app.renderer.resolution = res;
    app.renderer.resize(W, H); // autoDensity：画布的 CSS 尺寸不变，只有像素数变
    canvas.classList.toggle('pixel', pixel);
    if (pixel) {
      posterize ||= new PIXI.Filter(undefined, PIXEL_FRAG, { levels: LEVELS });
      posterize.resolution = res; // 滤镜的中间纹理也用低分辨率，不然先高清上色再缩小会糊
      app.stage.filters = [posterize];
      app.stage.filterArea = app.renderer.screen;
    } else {
      app.stage.filters = null;
      app.stage.filterArea = null;
    }
  }

  // 加载某套衣服的模型（加载过就直接返回）
  function ensure(outfit) {
    if (models[outfit]) return Promise.resolve(models[outfit]);
    if (pending[outfit]) return pending[outfit];
    pending[outfit] = (async () => {
      try {
        const m = await PIXI.live2d.Live2DModel.from(MODELS[outfit], { autoInteract: false });
        // 原图 1086×1448：按高度缩到 180，左右居中，脚踩到底。轴心放在脚底，整个人倾斜时脚不离地
        const ow = m.internalModel.originalWidth,
          oh = m.internalModel.originalHeight;
        const s = H / oh;
        m.scale.set(s);
        m.pivot.set(ow / 2, oh * 0.97);
        m.x = W / 2;
        m.y = oh * 0.97 * s;
        // 看鼠标这一步在物理之前：在这里把转头打折、让身子跟着转，头发的物理也就跟着变温和
        const im = m.internalModel;
        const focus = im.updateFocus.bind(im);
        im.updateFocus = () => {
          const core = im.coreModel;
          const get = (id) => core.getParameterValueById(id);
          const set = (id, v) => core.setParameterValueById(id, v);
          focus();
          const hx = get('ParamAngleX') * HEAD_GAIN,
            hy = get('ParamAngleY') * HEAD_GAIN,
            hz = get('ParamAngleZ') * HEAD_GAIN;
          set('ParamAngleX', hx);
          set('ParamAngleY', hy);
          set('ParamAngleZ', hz);
          set('ParamBodyAngleX', get('ParamBodyAngleX') + hx * BODY_FOLLOW);
          set('ParamBodyAngleZ', get('ParamBodyAngleZ') + hz * BODY_FOLLOW);
        };
        // 动作、表情、看鼠标都算完以后、画之前：调眼珠、加小眼神、说话动嘴
        m.internalModel.on('beforeModelUpdate', () => {
          if (m !== model) return;
          const core = m.internalModel.coreModel;
          const now = performance.now();
          const [ex, ey] = saccade(now);
          core.setParameterValueById('ParamEyeBallX', core.getParameterValueById('ParamEyeBallX') * EYE_GAIN + ex);
          core.setParameterValueById('ParamEyeBallY', core.getParameterValueById('ParamEyeBallY') * EYE_GAIN + ey);
          if (now < talkUntil) {
            const v = 0.5 + 0.5 * Math.sin(now / 70) * Math.sin(now / 190);
            core.setParameterValueById('ParamMouthOpenY', Math.max(0, v));
          }
          // 新嘴型（ω、撅嘴、波浪、一字、咧笑）亮着的时候，把默认的 :3 嘴线藏掉（它是按张嘴程度淡出的）
          const alt = ['ParamMouthCat', 'ParamMouthPout', 'ParamMouthWavy', 'ParamMouthFlat', 'ParamMouthGrin'].reduce((a, id) => Math.max(a, core.getParameterValueById(id)), 0);
          core.setParameterValueById('ParamMouthAlt', alt);
          finNow += (near * 7 - finNow) * 0.08;
          if (Math.abs(finNow) > 0.01) {
            core.setParameterValueById('ParamFinL', core.getParameterValueById('ParamFinL') + finNow);
            core.setParameterValueById('ParamFinR', core.getParameterValueById('ParamFinR') + finNow);
            core.setParameterValueById('ParamAhoge', core.getParameterValueById('ParamAhoge') + finNow * 0.5);
          }
          swayNow += (swayTarget - swayNow) * 0.12;
          if (Math.abs(swayNow) > 0.01) {
            core.setParameterValueById('ParamBodyAngleZ', core.getParameterValueById('ParamBodyAngleZ') + swayNow);
            core.setParameterValueById('ParamAngleZ', core.getParameterValueById('ParamAngleZ') + swayNow * 1.5);
            core.setParameterValueById('ParamLegL', core.getParameterValueById('ParamLegL') - swayNow * 0.5);
            core.setParameterValueById('ParamLegR', core.getParameterValueById('ParamLegR') + swayNow * 0.5);
          }
          for (const id of FROZEN[cur] || []) core.setParameterValueById(id, 0);
          const tilt = core.getParameterValueById('ParamBodyAngleZ') * BODY_TILT;
          m.rotation = (-Math.max(-MAX_TILT, Math.min(MAX_TILT, tilt)) * Math.PI) / 180;
        });
        blinks.set(m, m.internalModel.eyeBlink);
        models[outfit] = m;
        onModel?.(outfit);
        return m;
      } catch (e) {
        console.warn(`Live2D 模型（${outfit}）加载失败，这套衣服用立绘：`, e);
        broken.add(outfit);
        throw e;
      } finally {
        delete pending[outfit];
      }
    })();
    return pending[outfit];
  }

  // 换上某套衣服的模型。还没加载好就先开始加载、返回 false（这一下先用立绘，加载好了会叫 onModel）
  function wearOutfit(outfit) {
    if (cur === outfit && model) return true;
    const m = models[outfit];
    if (!m) {
      if (!broken.has(outfit)) ensure(outfit).catch(() => {});
      return false;
    }
    const prev = model;
    if (prev) {
      prev.internalModel.motionManager.stopAllMotions();
      app.stage.removeChild(prev);
    }
    model = m;
    cur = outfit;
    app.stage.addChild(m);
    // 新模型的表情、动作从头来；眼睛接着看原来的方向
    curExp = undefined;
    lastMood = '';
    if (prev) {
      const f = prev.internalModel.focusController;
      m.internalModel.focusController.focus(f.targetX, f.targetY, true);
    }
    return true;
  }

  // 这套衣服做没做成 Live2D
  const has = (outfit) => Object.prototype.hasOwnProperty.call(MODELS, outfit) && !broken.has(outfit);
  // 这个心情能不能用 Live2D 演。节日/季节衣服平时的心情就是衣服 id 本身（比如 'kotatsu'），当待机演
  const can = (mood, outfit = 'maid') =>
    state === 'ready' && has(outfit) && (Object.prototype.hasOwnProperty.call(EXP, mood) || mood === outfit);

  // 显示某个心情。返回 true = Live2D 接管了；false = 请用立绘
  function show(mood, outfit = 'maid') {
    if (!can(mood, outfit) || !wearOutfit(outfit)) {
      if (canvas) canvas.hidden = true;
      lastMood = '';
      return false;
    }
    canvas.hidden = false;
    const e = EXP[mood] ?? null;
    if (e !== curExp) {
      curExp = e;
      const em = model.internalModel.motionManager.expressionManager;
      if (e) model.expression(e);
      else if (em) {
        em.resetExpression();
        // 运行库的 resetExpression 不会清掉「当前表情」，下次再设同一个表情会被当成没变而跳过
        em.currentExpression = em.defaultExpression;
      }
      // 闭着眼的表情（^^ 笑眼、犯困）：自动眨眼会每帧把眼睛重新设成睁开，盖掉表情，所以先停掉
      model.internalModel.eyeBlink = EYES_SHUT.has(e) ? undefined : blinks.get(model);
    }
    if (mood !== lastMood) {
      // 刚从拎着放下来 / 刚跑完：停掉甩头、走路，回到待机
      if (lastMood === 'dangle' || lastMood === 'run') model.internalModel.motionManager.stopAllMotions();
      lastMood = mood;
      act(ACT[mood]);
    }
    return true;
  }
  // 做一个动作（强制打断待机；做完自动回到随机待机）。蹦一下时整个人往上跳一下
  let flinchEnd = 0;
  function act(group) {
    if (!group || !active()) return;
    if (NO_HOP.has(cur)) group = { Hop: 'Nod', Cheer: 'Wave', Kick: 'Tilt', Stretch: 'Stretch' }[group] || group;
    const now = performance.now();
    // 刚被戳了一下：让「缩一下」做完再做下一个动作
    if (group !== 'Flinch' && now < flinchEnd) return void setTimeout(() => act(group), flinchEnd - now);
    if (group === 'Flinch') flinchEnd = now + 550;
    model.motion(group, 0, 3);
    if (group === 'Hop') {
      canvas.classList.remove('hop');
      void canvas.offsetWidth;
      canvas.classList.add('hop');
    }
  }
  const poke = () => act('Flinch');

  // 小眼神：真人的眼睛不会一直定住，隔一两秒会很快地瞟一下别处再停住。
  // 鼠标在动的时候只轻轻瞟，鼠标停着时瞟得大一点；切换只用几十毫秒（眼珠是「跳」过去的）
  let sac = { x: 0, y: 0, tx: 0, ty: 0, next: 0, last: 0 };
  function saccade(now) {
    if (now > sac.next) {
      const idle = !lookAt || Date.now() - lookAt > 1500;
      const r = idle ? 0.35 : 0.12;
      const back = Math.random() < 0.35; // 有时候瞟回正中
      sac.tx = back ? 0 : (Math.random() * 2 - 1) * r;
      sac.ty = back ? 0 : (Math.random() * 2 - 1) * r * 0.6;
      sac.next = now + 900 + Math.random() * 2600;
    }
    const dt = Math.min(100, now - (sac.last || now));
    sac.last = now;
    const a = Math.min(1, dt / 60);
    sac.x += (sac.tx - sac.x) * a;
    sac.y += (sac.ty - sac.y) * a;
    return [sac.x, sac.y];
  }

  function hide() {
    if (canvas) canvas.hidden = true;
  }
  const active = () => !!canvas && !canvas.hidden && !!model;

  function talk(ms) {
    talkUntil = performance.now() + Math.min(ms, 2500); // 只在冒话头几秒动嘴
  }
  // 眼睛和头跟着鼠标。x、y 是鼠标相对窗口左上角的 CSS 像素。
  // 以她的脸为中心：鼠标越远转得越多（最多 70%），贴着脸时只轻轻看一下；转的过程由运行库自己缓动
  // 鼠标离她多近（0 = 很远，1 = 贴着脸）、停在她身上多久、刚才有没有从她面前飞快划过
  let near = 0,
    hoverSince = 0,
    tilted = false,
    lastCur = null,
    startleAt = -1e9;
  function lookTo(x, y) {
    if (!active()) return;
    const r = canvas.getBoundingClientRect();
    const dx = x - (r.left + r.width / 2),
      dy = y - (r.top + r.height * 0.3);
    const d = Math.hypot(dx, dy);
    if (d < 1) return;
    const k = (0.7 * d) / (d + 120) / d;
    model.internalModel.focusController.focus(dx * k, -dy * k);
    lookAt = Date.now();
    // 靠近：耳鳍慢慢竖起来（160px 以内开始，贴着时最大）
    near = Math.max(0, 1 - d / 160);
    // 快速划过脸前（200ms 内移动超过 260px、而且擦着她过去）：吓一跳，8 秒内不重复
    const now = performance.now();
    if (lastCur && now - lastCur.t < 200 && Math.hypot(x - lastCur.x, y - lastCur.y) > 260 && d < 140 && now - startleAt > 8000) {
      startleAt = now;
      act('Flinch');
      onStartle?.();
    }
    lastCur = { x, y, t: now };
    // 停在她身上：1.8 秒后歪头看你（鼠标离开 60px 外就复位）
    const on = d < 70;
    if (on && !hoverSince) hoverSince = now;
    if (!on) hoverSince = 0;
    if (on && !tilted && now - hoverSince > 1800) {
      tilted = true;
      act('Tilt');
    }
    if (!on) tilted = false;
  }
  let onStartle = null;
  // 鼠标 5 秒没动：慢慢看回正前方，耳鳍放下
  setInterval(() => {
    if (active() && lookAt && Date.now() - lookAt > 5000) {
      lookAt = 0;
      near = 0;
      hoverSince = 0;
      tilted = false;
      model.internalModel.focusController.focus(0, 0);
    }
  }, 1000);

  // 拎着她横着拖：按速度（CSS 像素/秒）往后仰，最多 ±8
  const sway = (vx) => (swayTarget = Math.max(-8, Math.min(8, -vx / 120)));

  const onLoaded = (fn) => (onModel = fn);
  const onStartled = (fn) => (onStartle = fn);
  return { load, show, hide, active, talk, lookTo, can, has, act, poke, sway, setPixel, onLoaded, onStartled };
})();
