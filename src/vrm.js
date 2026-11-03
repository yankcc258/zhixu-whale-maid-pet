// 3D 版希狐（VRM）。和 live2d.js 的 L2D 同一套接口（load / show / hide / active / talk / lookTo / can / has /
// act / poke / sway / setPixel / onLoaded / onStartled），pet.js 按设置在两者之间挑一个用。
// 模型在 vrm/kiko.vrm（VRoid 捏的白狐女仆，tools/vrm3d 后处理），运行库 vendor/three-vrm.bundle.js（three.js + @pixiv/three-vrm，MIT）。
// 做法：透明 WebGL 画布，MToon 卡通材质；眼睛用 three-vrm 的 LookAt 跟鼠标，头和上身跟着转一部分；
// 表情用 VRM 表情（预设 + VRoid 的 57 个脸部 morph 挂成的 m_* 自定义表情）；动作是程序化姿势（关节目标角 + 缓动 + 周期函数），
// 头发、尾巴、裙子靠模型自带的弹簧骨摆动。加载失败就一直用立绘，什么都不坏。
// eslint-disable-next-line no-unused-vars
const VRM3D = (() => {
  // 画布大小（CSS 像素）。正常比例全身，宽留一点给尾巴和甩头
  const W = 220,
    H = 400;
  // 心情 → 表情（VRM 表情名 → 权重）。null = 没表情（待机）
  const EXP = {
    idle: null,
    run: null,
    happy: { happy: 1 },
    excited: { happy: 0.8, aa: 0.35 },
    wave: { happy: 0.9 },
    newyear: { happy: 0.9, aa: 0.2 },
    smug: { m_Fcl_MTH_SkinFung_R: 1, m_Fcl_MTH_Fun: 0.35, m_Fcl_HA_Fung1: 0.8, m_Fcl_BRW_Fun: 0.5, m_Fcl_EYE_Fun: 0.3, blinkRight: 0.5, blinkLeft: 0.1 },
    smirk: { m_Fcl_MTH_SkinFung_R: 1, m_Fcl_MTH_Fun: 0.35, m_Fcl_HA_Fung1: 0.8, m_Fcl_BRW_Fun: 0.5, m_Fcl_EYE_Fun: 0.3, blinkRight: 0.5, blinkLeft: 0.1 },
    bleh: { blinkLeft: 1, ih: 0.5, m_Fcl_BRW_Fun: 0.4 },
    angry: { angry: 1 },
    wake: { sad: 0.35, blink: 0.45 },
    pat: { happy: 0.5, relaxed: 0.5 },
    sleepy: { blink: 0.75, relaxed: 0.3 },
    sleep: { blink: 1, relaxed: 0.2 },
    surprised: { surprised: 1 },
    dangle: { sad: 0.7, oh: 0.3 },
    pout: { angry: 0.35, ou: 0.7 },
    meh: { blink: 0.35, m_Fcl_MTH_Neutral: 0.5 },
    hot: { sad: 0.3, aa: 0.25, blink: 0.2 },
    cold: { ou: 0.5, blink: 0.25, m_Fcl_BRW_Sorrow: 0.4 },
  };
  // 闭着眼的心情：自动眨眼停掉
  const EYES_SHUT = new Set(['happy', 'wave', 'newyear', 'sleepy', 'sleep', 'pat']);
  // 心情刚变成这个时顺便做的动作（见下面 ACTS）；之后回到待机
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
  // 做成 3D 的衣服（现在只有女仆装；换装以后按衣服切贴图/模型）
  const MODELS = { maid: 'vrm/kiko.vrm' };
  const D = Math.PI / 180;
  // 关节的目标角（度，x=前后点头/抬臂，y=左右转，z=侧倾）。姿势 = 一组关节角；每帧向目标缓动。
  // 站姿（手臂自然下垂，略带八字）
  const STAND = {
    leftUpperArm: [0, 0, -68],
    rightUpperArm: [0, 0, 68],
    leftLowerArm: [0, -8, -6],
    rightLowerArm: [0, 8, 6],
    leftHand: [0, 0, -6],
    rightHand: [0, 0, 6],
    spine: [0, 0, 0],
    chest: [0, 0, 0],
    neck: [0, 0, 0],
    head: [0, 0, 0],
    hips: [0, 0, 0],
    leftUpperLeg: [0, 0, 0],
    rightUpperLeg: [0, 0, 0],
    leftLowerLeg: [0, 0, 0],
    rightLowerLeg: [0, 0, 0],
  };
  // 动作：name → { dur 毫秒（0 = 持续到心情换掉）, pose(t 0..1, now 秒) → 部分关节角（叠在站姿上）}
  const S = (x) => Math.sin(x),
    ease = (t) => 0.5 - 0.5 * Math.cos(Math.min(1, t) * Math.PI),
    bump = (t) => S(Math.min(1, t) * Math.PI); // 0→1→0
  const ACTS = {
    Wave: { dur: 1800, pose: (t, now) => ({ rightUpperArm: [-10, 0, -20 - 15 * bump(t)], rightLowerArm: [0, 0, -50 - 30 * S(now * 14)], rightHand: [0, 0, -15 * S(now * 14)], head: [0, -6, 8] }) },
    Hop: { dur: 700, pose: (t) => ({ leftUpperArm: [0, 0, -68 + 35 * bump(t)], rightUpperArm: [0, 0, 68 - 35 * bump(t)], spine: [-4 * bump(t), 0, 0] }) },
    Cheer: { dur: 1600, pose: (t, now) => ({ leftUpperArm: [-10, 0, 55], rightUpperArm: [-10, 0, -55], leftLowerArm: [0, 0, 25 + 12 * S(now * 12)], rightLowerArm: [0, 0, -25 - 12 * S(now * 12)], spine: [-5, 0, 3 * S(now * 6)], head: [-8, 0, 0] }) },
    Flinch: { dur: 550, pose: (t) => ({ head: [-14 * bump(t * 1.3), 0, 0], neck: [-6 * bump(t * 1.3), 0, 0], spine: [-6 * bump(t * 1.3), 0, 0], leftUpperArm: [0, 0, -50], rightUpperArm: [0, 0, 50], leftLowerArm: [0, -50, 50], rightLowerArm: [0, 50, -50] }) },
    Slump: { dur: 1500, pose: (t) => ({ spine: [10 * ease(t), 0, 0], neck: [8 * ease(t), 0, 0], head: [10 * ease(t), 0, 4 * ease(t)] }) },
    Shake: { dur: 1300, pose: (t, now) => ({ head: [0, 18 * S(now * 16) * bump(t), 0], spine: [4, 0, 0], leftUpperArm: [0, 0, -55], rightUpperArm: [0, 0, 55], leftLowerArm: [0, -30, 80], rightLowerArm: [0, 30, -80] }) },
    Stretch: { dur: 1800, pose: (t) => ({ leftUpperArm: [-20 * ease(t * 2), 0, -68 + 130 * ease(t * 2)], rightUpperArm: [-20 * ease(t * 2), 0, 68 - 130 * ease(t * 2)], spine: [-8 * bump(t), 0, 0], head: [-14 * bump(t), 0, 0] }) },
    Shy: { dur: 1600, pose: (t) => ({ head: [10 * ease(t * 2), 0, 10 * ease(t * 2)], leftUpperArm: [-70, 0, -52], rightUpperArm: [-70, 0, 52], leftLowerArm: [0, -125, -20], rightLowerArm: [0, 125, 20], leftHand: [0, 20, 0], rightHand: [0, -20, 0] }) }, // 双手捂脸颊
    Tilt: { dur: 1400, pose: (t) => ({ head: [0, 6 * ease(t * 2), 16 * ease(t * 2)], neck: [0, 0, 5 * ease(t * 2)] }) },
    Kick: { dur: 900, pose: (t) => ({ rightUpperLeg: [-30 * bump(t), 0, 0], rightLowerLeg: [25 * bump(t), 0, 0], spine: [4 * bump(t), 0, 0], head: [0, 0, -6 * bump(t)] }) },
    Nod: { dur: 800, pose: (t) => ({ head: [14 * bump(t), 0, 0], neck: [4 * bump(t), 0, 0] }) },
    Pant: { dur: 1800, pose: (t, now) => ({ spine: [8 + 3 * S(now * 9), 0, 0], chest: [3 * S(now * 9), 0, 0], head: [6, 0, 0], leftUpperArm: [0, 0, -60], rightUpperArm: [0, 0, 60], leftLowerArm: [0, -30, 40], rightLowerArm: [0, 30, -40] }) },
    // 被拎着：整个人挂着，手脚放松，轻轻晃（持续）
    Hang: { dur: 0, pose: (t, now) => ({ leftUpperArm: [0, 0, -85 + 5 * S(now * 3)], rightUpperArm: [0, 0, 85 - 5 * S(now * 3)], leftUpperLeg: [-6 + 5 * S(now * 2.5), 0, 3], rightUpperLeg: [-6 - 5 * S(now * 2.5), 0, -3], leftLowerLeg: [18, 0, 0], rightLowerLeg: [18, 0, 0], spine: [-6, 0, 2 + 3 * S(now * 2)], head: [12, 0, -5] }) },
    // 走路循环（持续）：腿前后、手臂反向、上身轻轻起伏
    Walk: { dur: 0, pose: (t, now) => ({ leftUpperLeg: [-28 * S(now * 9), 0, 0], rightUpperLeg: [28 * S(now * 9), 0, 0], leftLowerLeg: [18 + 16 * S(now * 9 - 1.2), 0, 0], rightLowerLeg: [18 - 16 * S(now * 9 - 1.2), 0, 0], leftUpperArm: [16 * S(now * 9), 0, -62], rightUpperArm: [-16 * S(now * 9), 0, 62], spine: [6, 0, 2 * S(now * 9)], head: [-4, 0, 0] }) },
    Fall: { dur: 0, pose: (t, now) => ({ leftUpperArm: [-30, 0, 50], rightUpperArm: [-30, 0, -50], leftUpperLeg: [-10, 0, 6], rightUpperLeg: [-10, 0, -6], spine: [-6, 0, 0], head: [-10, 0, 0] }) },
    Land: { dur: 700, pose: (t) => ({ hips: [0, 0, 0], leftUpperLeg: [-40 * bump(t), 0, 4], rightUpperLeg: [-40 * bump(t), 0, -4], leftLowerLeg: [60 * bump(t), 0, 0], rightLowerLeg: [60 * bump(t), 0, 0], spine: [22 * bump(t), 0, 0], head: [-8 * bump(t), 0, 0], leftUpperArm: [-30 * bump(t), 0, -60 + 30 * bump(t)], rightUpperArm: [-30 * bump(t), 0, 60 - 30 * bump(t)] }) },
  };
  // 落地蹲下时整个人要往下沉（髋骨降低），用 hipsY 表示（米）
  const HIPS_DROP = { Land: (t) => -0.16 * bump(t), Walk: (t, now) => 0.01 * Math.abs(S(now * 9)) - 0.01 };

  let canvas = null,
    renderer = null,
    scene = null,
    cam = null,
    vrm = null,
    cur = '',
    state = 'off', // 'off' | 'loading' | 'ready' | 'failed'
    curMood = '',
    lastMood = '',
    talkUntil = 0,
    lookAt = 0,
    pixel = false,
    raf = 0,
    lastT = 0;
  const models = {},
    pending = {},
    broken = new Set();
  let onModel = null,
    onStartle = null,
    onFail = null;
  const bones = {}; // 名字 → 规范化骨骼节点
  const cur3 = {}; // 名字 → 现在的角（缓动中）
  let action = null; // { name, start, dur }
  let flinchEnd = 0;
  let swayTarget = 0,
    swayNow = 0;
  let near = 0,
    hoverSince = 0,
    tilted = false,
    lastCur = null,
    startleAt = -1e9;
  // 看向哪（头/眼睛的目标，-1..1）
  const look = { x: 0, y: 0, hx: 0, hy: 0 };
  let lookTarget = null;
  let hipsBase = 0;

  async function load() {
    if (state !== 'off') return;
    state = 'loading';
    try {
      const TV = window.TV;
      if (!TV) throw new Error('three-vrm 运行库没加载');
      const { THREE } = TV;
      canvas = document.createElement('canvas');
      canvas.id = 'vrm3d';
      canvas.hidden = true;
      document.getElementById('pet').appendChild(canvas);
      renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true, premultipliedAlpha: true, powerPreference: 'low-power' });
      renderer.setClearColor(0x000000, 0);
      renderer.outputColorSpace = THREE.SRGBColorSpace;
      applyPixel();
      scene = new THREE.Scene();
      scene.add(new THREE.AmbientLight(0xffffff, 1.1));
      const key = new THREE.DirectionalLight(0xffffff, 1.6);
      key.position.set(0.6, 1.4, 1.8);
      scene.add(key);
      const fill = new THREE.DirectionalLight(0xdde6ff, 0.5);
      fill.position.set(-1, 0.4, -0.6);
      scene.add(fill);
      cam = new THREE.PerspectiveCamera(20, W / H, 0.1, 20);
      lookTarget = new THREE.Object3D();
      scene.add(lookTarget);
      state = 'ready';
      await ensure('maid');
    } catch (e) {
      console.warn('3D 模型加载失败，用立绘：', e);
      state = 'failed';
      onFail?.(String(e?.message || e));
      canvas?.remove();
      canvas = null;
    }
  }

  function setPixel(on) {
    pixel = !!on;
    if (renderer) applyPixel();
  }
  function applyPixel() {
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    // 像素模式：每格约 2 个 CSS 像素，由 CSS image-rendering: pixelated 放大
    renderer.setPixelRatio(pixel ? dpr / Math.max(2, Math.round(2 * dpr)) : dpr);
    renderer.setSize(W, H, false);
    canvas.classList.toggle('pixel', pixel);
  }

  function ensure(outfit) {
    if (models[outfit]) return Promise.resolve(models[outfit]);
    if (pending[outfit]) return pending[outfit];
    pending[outfit] = (async () => {
      try {
        const { THREE, GLTFLoader, VRMLoaderPlugin, VRMUtils } = window.TV;
        const loader = new GLTFLoader();
        loader.register((p) => new VRMLoaderPlugin(p));
        const gltf = await loader.loadAsync(MODELS[outfit]);
        const v = gltf.userData.vrm;
        VRMUtils.removeUnnecessaryVertices(gltf.scene);
        if (VRMUtils.combineSkeletons) VRMUtils.combineSkeletons(gltf.scene);
        VRMUtils.rotateVRM0(v); // VRM0 转成面向 +Z，VRM1 不动
        v.scene.traverse((o) => (o.frustumCulled = false));
        models[outfit] = v;
        onModel?.(outfit);
        return v;
      } catch (e) {
        console.warn(`3D 模型（${outfit}）加载失败，这套衣服用立绘：`, e);
        broken.add(outfit);
        onFail?.(String(e?.message || e));
        throw e;
      } finally {
        delete pending[outfit];
      }
    })();
    return pending[outfit];
  }

  function wearOutfit(outfit) {
    if (cur === outfit && vrm) return true;
    const v = models[outfit];
    if (!v) {
      if (!broken.has(outfit)) ensure(outfit).catch(() => {});
      return false;
    }
    if (vrm) scene.remove(vrm.scene);
    vrm = v;
    cur = outfit;
    scene.add(v.scene);
    const h = v.humanoid;
    for (const n of Object.keys(STAND)) {
      bones[n] = h.getNormalizedBoneNode(n);
      cur3[n] = [...STAND[n]];
    }
    hipsBase = bones.hips?.position.y ?? 0;
    if (v.lookAt) {
      v.lookAt.target = lookTarget;
      v.lookAt.autoUpdate = true;
    }
    applyPose(0);
    v.update(0);
    frameCamera();
    curMood = '';
    lastMood = '';
    return true;
  }
  // 相机：全身入镜，脚踩画布底边，头顶留一截给耳朵/呆毛
  function frameCamera() {
    const { THREE } = window.TV;
    const box = new THREE.Box3().setFromObject(vrm.scene);
    const size = box.getSize(new THREE.Vector3());
    const c = box.getCenter(new THREE.Vector3());
    const hh = size.y * 1.06; // 画面高度（米）
    const dist = hh / 2 / Math.tan((cam.fov / 2) * D);
    const cy = box.min.y + hh / 2 - size.y * 0.02;
    cam.position.set(c.x, cy + 0.05, c.z + dist);
    cam.lookAt(c.x, cy, c.z);
    cam.updateProjectionMatrix();
    lookTarget.position.set(c.x, cy + size.y * 0.42, c.z + dist);
  }

  const has = (outfit) => Object.prototype.hasOwnProperty.call(MODELS, outfit) && !broken.has(outfit);
  const can = (mood, outfit = 'maid') => state === 'ready' && has(outfit) && (Object.prototype.hasOwnProperty.call(EXP, mood) || mood === outfit);

  function show(mood, outfit = 'maid') {
    if (!can(mood, outfit) || !wearOutfit(outfit)) {
      hide();
      lastMood = '';
      return false;
    }
    if (canvas.hidden) {
      canvas.hidden = false;
      lastT = 0;
      raf ||= requestAnimationFrame(tick);
    }
    if (mood !== curMood) {
      curMood = mood;
      setExpression(EXP[mood] ?? null);
    }
    if (mood !== lastMood) {
      if (lastMood === 'dangle' || lastMood === 'run') action = null;
      lastMood = mood;
      act(ACT[mood]);
    }
    return true;
  }
  // 表情：先把所有表情清零（眨眼、嘴型另算），再按权重设
  let expNow = null;
  function setExpression(e) {
    expNow = e;
    const em = vrm?.expressionManager;
    if (!em) return;
    for (const x of em.expressions) if (!/^(blink|aa|ih|ou|ee|oh|lookUp|lookDown|lookLeft|lookRight)$/.test(x.expressionName)) em.setValue(x.expressionName, 0);
    if (e) for (const [k, w] of Object.entries(e)) if (!/^blink/.test(k)) em.setValue(k, w);
  }

  function act(name) {
    if (!name || !active() || !ACTS[name]) return;
    const now = performance.now();
    if (name !== 'Flinch' && now < flinchEnd) return void setTimeout(() => act(name), flinchEnd - now);
    if (name === 'Flinch') flinchEnd = now + 550;
    action = { name, start: now, dur: ACTS[name].dur };
    if (name === 'Hop') {
      canvas.classList.remove('hop');
      void canvas.offsetWidth;
      canvas.classList.add('hop');
    }
  }
  const poke = () => act('Flinch');

  // 每帧：姿势缓动 + 呼吸 + 看鼠标的头部转动 + 眨眼/说话 + 弹簧骨
  const blink = { next: 2000, t: -1 };
  function applyPose(dt) {
    const now = performance.now() / 1000;
    const t = action ? (action.dur ? (performance.now() - action.start) / action.dur : 0.5) : 1;
    if (action && action.dur && t >= 1) action = null;
    const extra = action ? ACTS[action.name].pose(Math.min(1, t), now) : {};
    // 呼吸 + 轻微重心移动（待机）
    const br = S(now * 1.6);
    const idle = { spine: [1.2 * br, 0, 0], chest: [1.0 * br, 0, 0], head: [-0.6 * br, 0, 0.8 * S(now * 0.7)], leftUpperArm: [0, 0, -1.5 * br], rightUpperArm: [0, 0, 1.5 * br] };
    // 看鼠标：头转 60%、脖子 25%、上身 15%
    const lh = { head: [look.hy * 18, look.hx * 22, -look.hx * 4], neck: [look.hy * 7, look.hx * 9, 0], chest: [0, look.hx * 5, 0] };
    const k = 1 - Math.pow(0.001, dt); // 缓动：约 0.15 秒追上大半
    for (const n of Object.keys(STAND)) {
      const base = STAND[n],
        a = idle[n] || [0, 0, 0],
        b = extra[n],
        c = lh[n] || [0, 0, 0];
      for (let i = 0; i < 3; i++) {
        const target = b ? base[i] * 0 + b[i] + c[i] : base[i] + a[i] + c[i];
        cur3[n][i] += (target - cur3[n][i]) * (b && action?.dur ? Math.min(1, k * 2) : k);
      }
      const nd = bones[n];
      if (!nd) continue;
      // 拎着横拖：整个人以髋为轴往后仰
      const sz = n === 'spine' ? swayNow * 1.2 : n === 'head' ? swayNow * 0.8 : 0;
      nd.rotation.set(cur3[n][0] * D, cur3[n][1] * D, (cur3[n][2] + sz) * D, 'XYZ');
    }
    const drop = action && HIPS_DROP[action.name] ? HIPS_DROP[action.name](Math.min(1, t), now) : 0;
    if (bones.hips) bones.hips.position.y = hipsBase + drop;
    // 眨眼（闭眼表情时不眨）+ 小眼神 + 说话
    const em = vrm.expressionManager;
    if (em) {
      const ms = performance.now();
      const shut = EYES_SHUT.has(curMood);
      let bl = expNow?.blink ?? 0;
      if (!shut) {
        if (blink.t < 0 && ms > blink.next) blink.t = ms;
        if (blink.t >= 0) {
          const p = (ms - blink.t) / 150;
          if (p >= 1) {
            blink.t = -1;
            blink.next = ms + 1800 + Math.random() * 3500;
          } else bl = Math.max(bl, bump(p));
        }
      }
      em.setValue('blink', bl);
      em.setValue('blinkLeft', expNow?.blinkLeft ?? 0);
      em.setValue('blinkRight', expNow?.blinkRight ?? 0);
      const talking = ms < talkUntil;
      const mouth = talking ? Math.max(0, 0.5 + 0.5 * S(ms / 70) * S(ms / 190)) : 0;
      em.setValue('aa', Math.max(expNow?.aa ?? 0, mouth * 0.7));
      for (const m of ['ih', 'ou', 'ee', 'oh']) em.setValue(m, expNow?.[m] ?? 0);
    }
  }
  let sac = { x: 0, y: 0, tx: 0, ty: 0, next: 0 };
  function tick(ts) {
    raf = 0;
    if (!canvas || canvas.hidden || !vrm) return;
    const dt = lastT ? Math.min(0.05, (ts - lastT) / 1000) : 1 / 30;
    // 30 帧够了，省电
    if (lastT && ts - lastT < 30) return void (raf = requestAnimationFrame(tick));
    lastT = ts;
    // 小眼神：隔一两秒瞟一下
    if (ts > sac.next) {
      const idleEyes = !lookAt || Date.now() - lookAt > 1500;
      const r = idleEyes ? 0.3 : 0.1;
      const back = Math.random() < 0.35;
      sac.tx = back ? 0 : (Math.random() * 2 - 1) * r;
      sac.ty = back ? 0 : (Math.random() * 2 - 1) * r * 0.6;
      sac.next = ts + 900 + Math.random() * 2600;
    }
    sac.x += (sac.tx - sac.x) * 0.5;
    sac.y += (sac.ty - sac.y) * 0.5;
    // 头慢慢追上视线
    look.hx += (look.x - look.hx) * Math.min(1, dt * 5);
    look.hy += (look.y - look.hy) * Math.min(1, dt * 5);
    swayNow += (swayTarget - swayNow) * Math.min(1, dt * 7);
    // 眼睛的目标点：在相机前方，按视线左右上下偏（眼睛比头多转一点）
    const { THREE } = window.TV;
    const hp = new THREE.Vector3();
    bones.head?.getWorldPosition(hp);
    const ex = look.x + sac.x,
      ey = look.y + sac.y;
    lookTarget.position.set(hp.x + ex * 1.2, hp.y + ey * 0.6, hp.z + 1.2);
    applyPose(dt);
    vrm.update(dt);
    renderer.render(scene, cam);
    raf = requestAnimationFrame(tick);
  }

  function hide() {
    if (canvas) canvas.hidden = true;
  }
  const active = () => !!canvas && !canvas.hidden && !!vrm;
  function talk(ms) {
    talkUntil = performance.now() + Math.min(ms, 2500);
  }
  // 眼睛和头跟着鼠标（x、y：鼠标相对窗口左上角的 CSS 像素）。以脸为中心，越远转得越多
  function lookTo(x, y) {
    if (!active()) return;
    const r = canvas.getBoundingClientRect();
    const dx = x - (r.left + r.width / 2),
      dy = y - (r.top + r.height * 0.18);
    const d = Math.hypot(dx, dy);
    if (d < 1) return;
    const k = (0.85 * d) / (d + 140) / d;
    look.x = Math.max(-1, Math.min(1, dx * k));
    look.y = Math.max(-1, Math.min(1, -dy * k));
    lookAt = Date.now();
    near = Math.max(0, 1 - d / 160);
    const now = performance.now();
    if (lastCur && now - lastCur.t < 200 && Math.hypot(x - lastCur.x, y - lastCur.y) > 260 && d < 140 && now - startleAt > 8000) {
      startleAt = now;
      act('Flinch');
      onStartle?.();
    }
    lastCur = { x, y, t: now };
    const on = d < 90;
    if (on && !hoverSince) hoverSince = now;
    if (!on) hoverSince = 0;
    if (on && !tilted && now - hoverSince > 1800) {
      tilted = true;
      act('Tilt');
    }
    if (!on) tilted = false;
  }
  setInterval(() => {
    if (active() && lookAt && Date.now() - lookAt > 5000) {
      lookAt = 0;
      near = 0;
      hoverSince = 0;
      tilted = false;
      look.x = look.y = 0;
    }
  }, 1000);
  const sway = (vx) => (swayTarget = Math.max(-10, Math.min(10, -vx / 100)));
  const onLoaded = (fn) => (onModel = fn);
  const onStartled = (fn) => (onStartle = fn);
  const onFailed = (fn) => (onFail = fn); // 加载失败时把原因交给 pet.js（正式版没有 devtools，冒个泡方便排查）
  return { load, show, hide, active, talk, lookTo, can, has, act, poke, sway, setPixel, onLoaded, onStartled, onFailed, _acts: ACTS };
})();
