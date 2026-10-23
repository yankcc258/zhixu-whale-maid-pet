// Live2D 版希可。只在穿着做成 Live2D 的衣服（MODELS 里的）、站着的时候用；躲在屏幕边、跑步、看书、
// 啃饭团这些没做成 Live2D 的动作，还有没做成 Live2D 的衣服，还是换回立绘图。加载失败（显卡不支持 WebGL 之类）就一直用立绘，什么都不坏。
// 模型在 live2d/seeko/，运行库在 vendor/（Cubism Core 是 Live2D 的专有许可，见 vendor/README.md）。
// eslint-disable-next-line no-unused-vars
const L2D = (() => {
  // 桌宠的心情 → 模型的表情（null = 不加表情，只放待机动作）
  const EXP = {
    idle: null,
    happy: 'happy',
    excited: 'happy',
    wave: 'happy',
    newyear: 'happy',
    smug: 'smug',
    smirk: 'smug',
    bleh: 'smug',
    angry: 'angry',
    wake: 'angry',
    pat: 'shy',
    sleepy: 'sleepy',
    sleep: 'sleepy',
    surprised: 'surprised',
    dangle: 'surprised',
    pout: 'pout',
    meh: 'pout',
    hot: 'pout',
    cold: 'pout',
  };
  // 心情刚变成这个时顺便做的动作（motions/ 里的分组）；之后回到随机的待机动作
  const ACT = {
    wave: 'Wave',
    happy: 'Hop',
    excited: 'Hop',
    newyear: 'Hop',
    surprised: 'Flinch',
    sleepy: 'Stretch',
    angry: 'Shake',
    wake: 'Shake',
    pat: 'Nod',
    smug: 'Tilt',
    smirk: 'Tilt',
    pout: 'Tilt',
    dangle: 'Swing',
  };
  // 全身像比立绘（半身大头）小，所以 Live2D 时 #pet 加高到 170×180（style.css 的 body.live2d），
  // 头顶那一截和气泡叠一点点没关系。人只有 135 宽，左右各留一截，转头时耳鳍和头发不会被切掉
  const W = 170,
    H = 180;
  // 眼珠：新身体的眼珠几乎占满眼白，骨架里的眼珠位移是给旧的小眼睛放大过的，这里缩回去，
  // 不然一转眼就露出一大片眼白、像在瞪人
  const EYE_GAIN = 0.4;
  // 这几个表情是闭着眼的（见 live2d/seeko/expressions/）；模型自带的自动眨眼存在 blinks 里
  const EYES_SHUT = new Set(['happy', 'smug', 'shy', 'sleepy']);
  const blinks = new WeakMap();
  // 做成 Live2D 的衣服（桌宠的衣服 id → 模型）。每套衣服一个模型：同一副骨架、同样的参数，
  // 只有贴图和网格不一样，所以动作、表情、物理都共用 live2d/seeko/ 里的那一份。
  // 没在这里的衣服照旧用立绘。
  const MODELS = {
    maid: 'live2d/seeko/seeko.model3.json',
    pajamas: 'live2d/seeko/seeko_pajamas.model3.json', // 睡衣（晚上、睡觉时自动换上）
  };
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
      state = 'ready';
      await ensure('maid'); // 女仆装先加载好，其他衣服用到时再加载
    } catch (e) {
      console.warn('Live2D 加载失败，用立绘：', e);
      state = 'failed';
      canvas?.remove();
      canvas = null;
    }
  }

  // 加载某套衣服的模型（加载过就直接返回）
  function ensure(outfit) {
    if (models[outfit]) return Promise.resolve(models[outfit]);
    if (pending[outfit]) return pending[outfit];
    pending[outfit] = (async () => {
      try {
        const m = await PIXI.live2d.Live2DModel.from(MODELS[outfit], { autoInteract: false });
        // 原图 1086×1448：按高度缩到 180，左右居中，脚踩到底
        const s = H / m.internalModel.originalHeight;
        m.scale.set(s);
        m.x = (W - m.internalModel.originalWidth * s) / 2;
        m.y = 0;
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
  // 这个心情能不能用 Live2D 演
  const can = (mood, outfit = 'maid') =>
    state === 'ready' && has(outfit) && Object.prototype.hasOwnProperty.call(EXP, mood);

  // 显示某个心情。返回 true = Live2D 接管了；false = 请用立绘
  function show(mood, outfit = 'maid') {
    if (!can(mood, outfit) || !wearOutfit(outfit)) {
      if (canvas) canvas.hidden = true;
      lastMood = '';
      return false;
    }
    canvas.hidden = false;
    const e = EXP[mood];
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
      // 刚从拎着放下来：停掉甩头，回到待机
      if (lastMood === 'dangle') model.internalModel.motionManager.stopAllMotions();
      lastMood = mood;
      act(ACT[mood]);
    }
    return true;
  }
  // 做一个动作（强制打断待机；做完自动回到随机待机）。蹦一下时整个人往上跳一下
  let flinchEnd = 0;
  function act(group) {
    if (!group || !active()) return;
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
  }
  // 鼠标 5 秒没动：慢慢看回正前方
  setInterval(() => {
    if (active() && lookAt && Date.now() - lookAt > 5000) {
      lookAt = 0;
      model.internalModel.focusController.focus(0, 0);
    }
  }, 1000);

  const onLoaded = (fn) => (onModel = fn);
  return { load, show, hide, active, talk, lookTo, can, has, act, poke, onLoaded };
})();
