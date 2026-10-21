// Live2D 版希可（女仆装）。只在穿女仆装、站着的时候用；躲在屏幕边、跑步、看书、啃饭团这些
// 没做成 Live2D 的动作，还是换回立绘图。加载失败（显卡不支持 WebGL 之类）就一直用立绘，什么都不坏。
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
  // 全身像比立绘（半身大头）小，所以 Live2D 时 #pet 加高到 150×180（style.css 的 body.live2d），
  // 头顶那一截和气泡叠一点点没关系
  const W = 150,
    H = 180;
  let canvas = null,
    app = null,
    model = null,
    state = 'off', // 'off' | 'loading' | 'ready' | 'failed'
    curExp = undefined,
    lastMood = '',
    talkUntil = 0,
    lookAt = 0;

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
      model = await PIXI.live2d.Live2DModel.from('live2d/seeko/seeko.model3.json', { autoInteract: false });
      // 原图 1086×1448：按高度缩到 180，左右居中，脚踩到底
      const s = H / model.internalModel.originalHeight;
      model.scale.set(s);
      model.x = (W - model.internalModel.originalWidth * s) / 2;
      model.y = 0;
      app.stage.addChild(model);
      // 说话时嘴一张一合：在动作和表情算完之后覆盖张嘴参数
      model.internalModel.on('beforeModelUpdate', () => {
        const core = model.internalModel.coreModel;
        const now = performance.now();
        if (now < talkUntil) {
          const v = 0.5 + 0.5 * Math.sin(now / 70) * Math.sin(now / 190);
          core.setParameterValueById('ParamMouthOpenY', Math.max(0, v));
        }
      });
      state = 'ready';
    } catch (e) {
      console.warn('Live2D 加载失败，用立绘：', e);
      state = 'failed';
      canvas?.remove();
      canvas = null;
    }
  }

  // 这个心情能不能用 Live2D 演
  const can = (mood) => state === 'ready' && Object.prototype.hasOwnProperty.call(EXP, mood);

  // 显示某个心情。返回 true = Live2D 接管了；false = 请用立绘
  function show(mood) {
    if (!can(mood)) {
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
      else em?.resetExpression();
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

  function hide() {
    if (canvas) canvas.hidden = true;
  }
  const active = () => !!canvas && !canvas.hidden;

  function talk(ms) {
    talkUntil = performance.now() + Math.min(ms, 2500); // 只在冒话头几秒动嘴
  }
  // 眼睛和头跟着鼠标。x、y 是鼠标相对窗口左上角的 CSS 像素。
  // 以她的脸为中心：鼠标越远转得越多（最多 90%），贴着脸时只轻轻看一下；转的过程由运行库自己缓动
  function lookTo(x, y) {
    if (!active()) return;
    const r = canvas.getBoundingClientRect();
    const dx = x - (r.left + r.width / 2),
      dy = y - (r.top + r.height * 0.3);
    const d = Math.hypot(dx, dy);
    if (d < 1) return;
    const k = (0.9 * d) / (d + 120) / d;
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

  return { load, show, hide, active, talk, lookTo, can, act, poke };
})();
