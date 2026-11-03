// 3D 版希狐（VRM）。和 live2d.js 的 L2D 同一套接口（load / show / hide / active / talk / lookTo / can / has /
// act / poke / sway / setPixel / onLoaded / onStartled），pet.js 按设置在两者之间挑一个用。
// 模型在 vrm/kiko.vrm（VRoid 捏的白狐女仆，tools/vrm3d 后处理），运行库 vendor/three-vrm.bundle.js（three.js + @pixiv/three-vrm，MIT）。
// 做法：透明 WebGL 画布，MToon 卡通材质；眼睛用 three-vrm 的 LookAt 跟鼠标，头和上身跟着转一部分；
// 表情用 VRM 表情（预设 + VRoid 的 57 个脸部 morph 挂成的 m_* 自定义表情）；动作是程序化姿势（关节目标角 + 缓动 + 周期函数），
// 头发、尾巴、裙子靠模型自带的弹簧骨摆动。加载失败就一直用立绘，什么都不坏。
// eslint-disable-next-line no-unused-vars
const VRM3D = (() => {
  // 画布大小（CSS 像素）。正常比例全身，宽留一点给尾巴和甩头
  const W = 260,
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
  const BONES = ['leftUpperArm', 'rightUpperArm', 'leftLowerArm', 'rightLowerArm', 'leftHand', 'rightHand', 'spine', 'chest', 'neck', 'head', 'hips', 'leftUpperLeg', 'rightUpperLeg', 'leftLowerLeg', 'rightLowerLeg'];
  // 关节的目标角（度，x=前后点头/抬臂，y=左右转，z=侧倾）。姿势 = 一组关节角；每帧向目标缓动。
  // 站姿：女仆式，双手交叠放在身前（上臂 y 往内收 40°、前臂弯 95° 伸到身前）
  const STAND = {
    leftUpperArm: [3, -40, -68],
    rightUpperArm: [-3, 40, 68],
    leftLowerArm: [0, -95, 0],
    rightLowerArm: [0, 95, 0],
    leftHand: [0, -15, 0],
    rightHand: [0, 15, 0],
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
  // ---------- 动作 = 关键帧片段 ----------
  // clip: { keys: [{ t 毫秒, pose: {骨骼: [x,y,z]}, hips: 髋骨下沉(米), ease: 进入这一帧的缓动 }], loop: 从哪帧开始循环(毫秒), hold: 播完停在最后一帧, until: 循环最多播多久 }
  // 没写的骨骼沿用上一帧（最前面隐含一帧 = 站姿），所以每段只写变化的关节。
  // 缓动：in 慢起、out 慢停、inout 两头慢（默认）、back 过冲再回来（手脚甩到位的感觉）、snap 直接跳
  const S = (x) => Math.sin(x),
    bump = (t) => S(Math.min(1, Math.max(0, t)) * Math.PI); // 0→1→0
  const EASE = {
    in: (t) => t * t,
    out: (t) => 1 - (1 - t) * (1 - t),
    inout: (t) => 0.5 - 0.5 * Math.cos(t * Math.PI),
    back: (t) => 1 + 2.3 * Math.pow(t - 1, 3) + 1.3 * Math.pow(t - 1, 2),
    snap: () => 1,
  };
  const L = { leftUpperArm: [3, -40, -68], rightUpperArm: [-3, 40, 68], leftLowerArm: [0, -95, 0], rightLowerArm: [0, 95, 0] }; // 站姿手（写短一点）
  const armsDown = (sw = 0) => ({ leftUpperArm: [0, 0, -72 + sw], rightUpperArm: [0, 0, 72 - sw], leftLowerArm: [0, -8, 0], rightLowerArm: [0, 8, 0], leftHand: [0, 0, 0], rightHand: [0, 0, 0] });
  const ACTS = {
    // 挥手：先缩一下肩（预备），手甩上去（过冲），摆三下，放下来
    Wave: { keys: [
      { t: 140, ease: 'in', pose: { rightUpperArm: [-3, 40, 76], head: [2, -4, 3] } },
      { t: 420, ease: 'back', pose: { rightUpperArm: [-10, 0, -22], rightLowerArm: [0, 0, -60], rightHand: [0, 0, -10], head: [0, -6, 8], chest: [0, -4, 0] } },
      { t: 580, ease: 'inout', pose: { rightLowerArm: [0, 0, -100], rightHand: [0, 0, -25] } },
      { t: 740, ease: 'inout', pose: { rightLowerArm: [0, 0, -40], rightHand: [0, 0, 5] } },
      { t: 900, ease: 'inout', pose: { rightLowerArm: [0, 0, -100], rightHand: [0, 0, -25] } },
      { t: 1060, ease: 'inout', pose: { rightLowerArm: [0, 0, -40], rightHand: [0, 0, 5] } },
      { t: 1220, ease: 'inout', pose: { rightLowerArm: [0, 0, -95], rightHand: [0, 0, -20] } },
      { t: 1450, ease: 'inout', pose: { rightLowerArm: [0, 0, -70], rightHand: [0, 0, -10] } },
      { t: 1700, ease: 'inout', pose: { rightUpperArm: [-30, 25, 30], rightLowerArm: [0, 70, -20], rightHand: [0, 10, 0], head: [0, -3, 4] } },
      { t: 2000, ease: 'inout', pose: { rightUpperArm: L.rightUpperArm, rightLowerArm: L.rightLowerArm, rightHand: [0, 15, 0], head: [0, 0, 0], chest: [0, 0, 0] } },
    ] },
    // 蹦一下：下蹲预备 → 起跳伸展（画布本身由 CSS 往上跳）→ 落地压缩 → 回弹
    Hop: { keys: [
      { t: 130, ease: 'in', hips: -0.05, pose: { leftUpperLeg: [-18, 0, 2], rightUpperLeg: [-18, 0, -2], leftLowerLeg: [30, 0, 0], rightLowerLeg: [30, 0, 0], spine: [8, 0, 0], head: [6, 0, 0], leftUpperArm: [6, -40, -60], rightUpperArm: [-6, 40, 60] } },
      { t: 300, ease: 'out', hips: 0.0, pose: { leftUpperLeg: [4, 0, 2], rightUpperLeg: [4, 0, -2], leftLowerLeg: [2, 0, 0], rightLowerLeg: [2, 0, 0], spine: [-6, 0, 0], head: [-8, 0, 0], leftUpperArm: [0, -20, -30], rightUpperArm: [0, 20, 30], leftLowerArm: [0, -70, 0], rightLowerArm: [0, 70, 0] } },
      { t: 520, ease: 'in', hips: -0.04, pose: { leftUpperLeg: [-14, 0, 2], rightUpperLeg: [-14, 0, -2], leftLowerLeg: [24, 0, 0], rightLowerLeg: [24, 0, 0], spine: [9, 0, 0], head: [5, 0, 0], leftUpperArm: [3, -40, -62], rightUpperArm: [-3, 40, 62] } },
      { t: 800, ease: 'back', hips: 0, pose: { leftUpperLeg: [0, 0, 0], rightUpperLeg: [0, 0, 0], leftLowerLeg: [0, 0, 0], rightLowerLeg: [0, 0, 0], spine: [0, 0, 0], head: [0, 0, 0], ...L } },
    ] },
    // 欢呼：收一下 → 双手举起（过冲）→ 举着上下抖三次 → 放下
    Cheer: { keys: [
      { t: 160, ease: 'in', pose: { spine: [6, 0, 0], head: [5, 0, 0], leftUpperArm: [6, -40, -62], rightUpperArm: [-6, 40, 62] } },
      { t: 420, ease: 'back', pose: { spine: [-6, 0, 0], head: [-10, 0, 0], leftUpperArm: [-10, 0, 70], rightUpperArm: [-10, 0, -70], leftLowerArm: [0, 0, 20], rightLowerArm: [0, 0, -20], leftHand: [0, 0, 0], rightHand: [0, 0, 0] } },
      { t: 620, ease: 'inout', pose: { leftLowerArm: [0, 0, 38], rightLowerArm: [0, 0, -38], spine: [-6, 0, 3] } },
      { t: 820, ease: 'inout', pose: { leftLowerArm: [0, 0, 12], rightLowerArm: [0, 0, -12], spine: [-6, 0, -3] } },
      { t: 1020, ease: 'inout', pose: { leftLowerArm: [0, 0, 38], rightLowerArm: [0, 0, -38], spine: [-6, 0, 3] } },
      { t: 1220, ease: 'inout', pose: { leftLowerArm: [0, 0, 12], rightLowerArm: [0, 0, -12], spine: [-6, 0, 0] } },
      { t: 1550, ease: 'inout', pose: { leftUpperArm: [-40, -30, -48], rightUpperArm: [-40, 30, 48], leftLowerArm: [0, -85, 0], rightLowerArm: [0, 85, 0], spine: [0, 0, 0], head: [-2, 0, 0] } },
      { t: 1900, ease: 'inout', pose: { head: [0, 0, 0], ...L, leftHand: [0, -15, 0], rightHand: [0, 15, 0] } },
    ] },
    // 吓一跳：头和上身猛往后、双手收到胸前，停一下再松开
    Flinch: { keys: [
      { t: 90, ease: 'out', pose: { head: [-14, 0, 0], neck: [-6, 0, 0], spine: [-6, 0, 0], leftUpperArm: [-30, -25, -58], rightUpperArm: [-30, 25, 58], leftLowerArm: [0, -115, 0], rightLowerArm: [0, 115, 0], leftHand: [0, -20, 0], rightHand: [0, 20, 0] } },
      { t: 330, ease: 'inout', pose: { head: [-10, 0, 0] } },
      { t: 620, ease: 'inout', pose: { head: [0, 0, 0], neck: [0, 0, 0], spine: [0, 0, 0], ...L, leftHand: [0, -15, 0], rightHand: [0, 15, 0] } },
    ] },
    // 犯困耷拉：慢慢垂下去，然后停住（心情换掉才起来）
    Slump: { hold: true, keys: [
      { t: 900, ease: 'inout', pose: { spine: [10, 0, 0], neck: [8, 0, 0], head: [10, 0, 4], leftUpperArm: [3, -36, -70], rightUpperArm: [-3, 36, 70] } },
      { t: 1600, ease: 'inout', pose: { head: [12, 0, 6] } },
    ] },
    // 生气甩头：双手抱胸，头左右甩，幅度递减
    Shake: { keys: [
      { t: 150, ease: 'out', pose: { spine: [4, 0, 0], leftUpperArm: [-15, -48, -62], rightUpperArm: [-15, 48, 62], leftLowerArm: [0, -118, 0], rightLowerArm: [0, 118, 0], leftHand: [0, -10, 0], rightHand: [0, 10, 0], head: [0, 18, 0] } },
      { t: 300, ease: 'inout', pose: { head: [0, -18, 0] } },
      { t: 450, ease: 'inout', pose: { head: [0, 16, 0] } },
      { t: 600, ease: 'inout', pose: { head: [0, -14, 0] } },
      { t: 750, ease: 'inout', pose: { head: [0, 9, 0] } },
      { t: 900, ease: 'inout', pose: { head: [0, -4, 0] } },
      { t: 1050, ease: 'inout', pose: { head: [4, 0, 0] } },
      { t: 1400, ease: 'inout', pose: { spine: [0, 0, 0], head: [0, 0, 0], ...L } },
    ] },
    // 伸懒腰：先缩一下 → 双手高举、挺胸仰头 → 抖一抖 → 放下
    Stretch: { keys: [
      { t: 220, ease: 'in', pose: { spine: [6, 0, 0], head: [6, 0, 0], leftUpperArm: [6, -40, -60], rightUpperArm: [-6, 40, 60] } },
      { t: 800, ease: 'back', pose: { spine: [-9, 0, 0], chest: [-4, 0, 0], head: [-15, 0, 0], leftUpperArm: [-20, 0, 62], rightUpperArm: [-20, 0, -62], leftLowerArm: [0, 0, 8], rightLowerArm: [0, 0, -8], leftHand: [0, 0, 0], rightHand: [0, 0, 0] } },
      { t: 1000, ease: 'inout', pose: { head: [-15, 0, 3], leftUpperArm: [-20, 0, 66] } },
      { t: 1200, ease: 'inout', pose: { head: [-15, 0, -3], rightUpperArm: [-20, 0, -66] } },
      { t: 1400, ease: 'inout', pose: { head: [-15, 0, 0] } },
      { t: 1800, ease: 'inout', pose: { spine: [2, 0, 0], chest: [0, 0, 0], head: [2, 0, 0], leftUpperArm: [-40, -30, -48], rightUpperArm: [-40, 30, 48], leftLowerArm: [0, -85, 0], rightLowerArm: [0, 85, 0] } },
      { t: 2200, ease: 'inout', pose: { spine: [0, 0, 0], head: [0, 0, 0], ...L, leftHand: [0, -15, 0], rightHand: [0, 15, 0] } },
    ] },
    // 害羞：双手捂脸颊、低头，头小幅左右扭
    Shy: { keys: [
      { t: 350, ease: 'out', pose: { head: [10, 0, 10], leftUpperArm: [-52, -8, -56], rightUpperArm: [-52, 8, 56], leftLowerArm: [0, -128, -10], rightLowerArm: [0, 128, 10], leftHand: [0, 20, 0], rightHand: [0, -20, 0] } },
      { t: 900, ease: 'inout', pose: { head: [10, 0, -8] } },
      { t: 1450, ease: 'inout', pose: { head: [10, 0, 8] } },
      { t: 1900, ease: 'inout', pose: { head: [8, 0, 0] } },
      { t: 2300, ease: 'inout', pose: { head: [0, 0, 0], ...L, leftHand: [0, -15, 0], rightHand: [0, 15, 0] } },
    ] },
    // 歪头看你
    Tilt: { keys: [
      { t: 420, ease: 'back', pose: { head: [0, 6, 16], neck: [0, 0, 5] } },
      { t: 1150, ease: 'inout', pose: { head: [0, 6, 16] } },
      { t: 1500, ease: 'inout', pose: { head: [0, 0, 0], neck: [0, 0, 0] } },
    ] },
    // 不耐烦踢一下：腿先往后收，再踢出去
    Kick: { keys: [
      { t: 180, ease: 'in', pose: { rightUpperLeg: [10, 0, 0], spine: [-3, 0, 0], head: [0, 0, 3] } },
      { t: 400, ease: 'out', pose: { rightUpperLeg: [-35, 0, 0], rightLowerLeg: [25, 0, 0], spine: [5, 0, 0], head: [0, 0, -6] } },
      { t: 700, ease: 'in', pose: { rightUpperLeg: [0, 0, 0], rightLowerLeg: [0, 0, 0] } },
      { t: 950, ease: 'inout', pose: { spine: [0, 0, 0], head: [0, 0, 0] } },
    ] },
    Nod: { keys: [
      { t: 200, ease: 'inout', pose: { head: [14, 0, 0], neck: [4, 0, 0] } },
      { t: 420, ease: 'inout', pose: { head: [-3, 0, 0], neck: [0, 0, 0] } },
      { t: 600, ease: 'inout', pose: { head: [9, 0, 0] } },
      { t: 850, ease: 'inout', pose: { head: [0, 0, 0] } },
    ] },
    // 喘气：手撑膝盖式弯腰，胸口起伏循环，两秒后直起来
    Pant: { loop: 300, until: 2000, keys: [
      { t: 300, ease: 'out', pose: { spine: [10, 0, 0], chest: [2, 0, 0], head: [4, 0, 0], ...armsDown(10), leftLowerArm: [0, -30, 40], rightLowerArm: [0, 30, -40] } },
      { t: 650, ease: 'inout', pose: { spine: [13, 0, 0], chest: [5, 0, 0], head: [2, 0, 0] } },
      { t: 1000, ease: 'inout', pose: { spine: [9, 0, 0], chest: [-1, 0, 0], head: [5, 0, 0] } },
    ] },
    // 被拎着：手脚垂下来晃（循环，直到放下）
    Hang: { loop: 300, keys: [
      { t: 300, ease: 'out', pose: { ...armsDown(-13), leftUpperLeg: [-6, 0, 3], rightUpperLeg: [-6, 0, -3], leftLowerLeg: [18, 0, 0], rightLowerLeg: [18, 0, 0], spine: [-6, 0, 2], head: [12, 0, -5] } },
      { t: 1100, ease: 'inout', pose: { leftUpperLeg: [-2, 0, 3], rightUpperLeg: [-11, 0, -3], spine: [-6, 0, 5], leftUpperArm: [0, 0, -82], rightUpperArm: [0, 0, 88] } },
      { t: 1900, ease: 'inout', pose: { leftUpperLeg: [-11, 0, 3], rightUpperLeg: [-2, 0, -3], spine: [-6, 0, -1], leftUpperArm: [0, 0, -88], rightUpperArm: [0, 0, 82] } },
      { t: 2700, ease: 'inout', pose: { leftUpperLeg: [-6, 0, 3], rightUpperLeg: [-6, 0, -3], spine: [-6, 0, 2], leftUpperArm: [0, 0, -85], rightUpperArm: [0, 0, 85] } },
    ] },
    // 走路循环（一步 440ms）
    Walk: { loop: 0, keys: [
      { t: 0, ease: 'snap', hips: 0, pose: { leftUpperLeg: [-26, 0, 0], rightUpperLeg: [22, 0, 0], leftLowerLeg: [8, 0, 0], rightLowerLeg: [30, 0, 0], leftUpperArm: [14, 0, -64], rightUpperArm: [-14, 0, 64], leftLowerArm: [0, -10, 0], rightLowerArm: [0, 10, 0], leftHand: [0, 0, 0], rightHand: [0, 0, 0], spine: [6, 0, 2], head: [-4, 0, -1] } },
      { t: 220, ease: 'inout', hips: -0.012, pose: { leftUpperLeg: [2, 0, 0], rightUpperLeg: [-4, 0, 0], leftLowerLeg: [34, 0, 0], rightLowerLeg: [6, 0, 0], leftUpperArm: [0, 0, -64], rightUpperArm: [0, 0, 64], spine: [7, 0, 0], head: [-5, 0, 0] } },
      { t: 440, ease: 'inout', hips: 0, pose: { leftUpperLeg: [22, 0, 0], rightUpperLeg: [-26, 0, 0], leftLowerLeg: [30, 0, 0], rightLowerLeg: [8, 0, 0], leftUpperArm: [-14, 0, -64], rightUpperArm: [14, 0, 64], spine: [6, 0, -2], head: [-4, 0, 1] } },
      { t: 660, ease: 'inout', hips: -0.012, pose: { leftUpperLeg: [-4, 0, 0], rightUpperLeg: [2, 0, 0], leftLowerLeg: [6, 0, 0], rightLowerLeg: [34, 0, 0], leftUpperArm: [0, 0, -64], rightUpperArm: [0, 0, 64], spine: [7, 0, 0], head: [-5, 0, 0] } },
      { t: 880, ease: 'inout', hips: 0, pose: { leftUpperLeg: [-26, 0, 0], rightUpperLeg: [22, 0, 0], leftLowerLeg: [8, 0, 0], rightLowerLeg: [30, 0, 0], leftUpperArm: [14, 0, -64], rightUpperArm: [-14, 0, 64], spine: [6, 0, 2], head: [-4, 0, -1] } },
    ] },
    // 往下掉：双手往上抓、腿微张，停住直到落地
    Fall: { hold: true, keys: [
      { t: 180, ease: 'out', pose: { leftUpperArm: [-70, 0, -25], rightUpperArm: [-70, 0, 25], leftLowerArm: [0, -40, 0], rightLowerArm: [0, 40, 0], leftHand: [0, 0, 0], rightHand: [0, 0, 0], leftUpperLeg: [-10, 0, 6], rightUpperLeg: [-10, 0, -6], spine: [-6, 0, 0], head: [-10, 0, 0] } },
    ] },
    // 落地：深蹲缓冲 → 回弹过冲 → 站好
    Land: { keys: [
      { t: 110, ease: 'out', hips: -0.16, pose: { leftUpperLeg: [-42, 0, 4], rightUpperLeg: [-42, 0, -4], leftLowerLeg: [62, 0, 0], rightLowerLeg: [62, 0, 0], spine: [22, 0, 0], head: [-8, 0, 0], leftUpperArm: [-40, 0, -55], rightUpperArm: [-40, 0, 55], leftLowerArm: [0, -20, 0], rightLowerArm: [0, 20, 0] } },
      { t: 260, ease: 'inout', hips: -0.13, pose: { spine: [18, 0, 0] } },
      { t: 700, ease: 'back', hips: 0, pose: { leftUpperLeg: [0, 0, 0], rightUpperLeg: [0, 0, 0], leftLowerLeg: [0, 0, 0], rightLowerLeg: [0, 0, 0], spine: [0, 0, 0], head: [0, 0, 0], ...L, leftHand: [0, -15, 0], rightHand: [0, 15, 0] } },
    ] },
    // ---- 待机小动作（没事干时随机来一个）----
    LookAround: { keys: [
      { t: 500, ease: 'inout', pose: { head: [0, 24, -3], neck: [0, 8, 0] } },
      { t: 1500, ease: 'inout', pose: { head: [0, 24, -3] } },
      { t: 2100, ease: 'inout', pose: { head: [-2, -22, 3], neck: [0, -8, 0] } },
      { t: 3100, ease: 'inout', pose: { head: [-2, -22, 3] } },
      { t: 3700, ease: 'inout', pose: { head: [0, 0, 0], neck: [0, 0, 0] } },
    ] },
    ShiftWeight: { keys: [
      { t: 700, ease: 'inout', hips: -0.012, pose: { hips: [0, 0, 4], spine: [0, 0, -3], chest: [0, 0, -1], rightUpperLeg: [-6, 0, 0], rightLowerLeg: [10, 0, 0], head: [0, 0, 2] } },
      { t: 3200, ease: 'inout', pose: { hips: [0, 0, 4] } },
      { t: 3900, ease: 'inout', hips: 0, pose: { hips: [0, 0, 0], spine: [0, 0, 0], chest: [0, 0, 0], rightUpperLeg: [0, 0, 0], rightLowerLeg: [0, 0, 0], head: [0, 0, 0] } },
    ] },
    Tiptoe: { keys: [
      { t: 350, ease: 'inout', hips: 0.025, pose: { spine: [-2, 0, 0], head: [-3, 0, 0] } },
      { t: 900, ease: 'inout', hips: 0.025, pose: {} },
      { t: 1300, ease: 'back', hips: 0, pose: { spine: [0, 0, 0], head: [0, 0, 0] } },
    ] },
    SmoothSkirt: { keys: [
      { t: 500, ease: 'inout', pose: { ...armsDown(-6), head: [10, 0, 0], spine: [4, 0, 0] } },
      { t: 900, ease: 'inout', pose: { leftUpperArm: [0, 0, -82], rightUpperArm: [0, 0, 82], leftLowerArm: [0, -14, 0], rightLowerArm: [0, 14, 0] } },
      { t: 1300, ease: 'inout', pose: { leftUpperArm: [0, 0, -72], rightUpperArm: [0, 0, 72] } },
      { t: 1700, ease: 'inout', pose: { leftUpperArm: [0, 0, -82], rightUpperArm: [0, 0, 82] } },
      { t: 2400, ease: 'inout', pose: { ...L, leftHand: [0, -15, 0], rightHand: [0, 15, 0], head: [0, 0, 0], spine: [0, 0, 0] } },
    ] },
    FidgetHands: { keys: [
      { t: 400, ease: 'inout', pose: { leftLowerArm: [0, -88, 0], rightLowerArm: [0, 102, 0], leftHand: [0, -25, 0], rightHand: [0, 5, 0] } },
      { t: 900, ease: 'inout', pose: { leftLowerArm: [0, -102, 0], rightLowerArm: [0, 88, 0], leftHand: [0, -5, 0], rightHand: [0, 25, 0] } },
      { t: 1400, ease: 'inout', pose: { ...L, leftHand: [0, -15, 0], rightHand: [0, 15, 0] } },
    ] },
  };
  const IDLE_CLIPS = ['LookAround', 'ShiftWeight', 'Tiptoe', 'SmoothSkirt', 'FidgetHands', 'LookAround', 'ShiftWeight'];
  for (const c of Object.values(ACTS)) c.dur = c.keys[c.keys.length - 1].t; // 片段长度
  // 在 tm 毫秒处求片段的关节角和髋骨下沉；返回 null 表示片段放完了
  function evalClip(clip, tm) {
    const keys = clip.keys,
      last = clip.dur;
    if (tm > last) {
      if (clip.loop !== undefined && !(clip.until && tm > clip.until)) tm = clip.loop + ((tm - clip.loop) % (last - clip.loop));
      else if (clip.hold) tm = last;
      else return null;
    }
    const pose = {};
    for (const bone of BONES) {
      let pv = STAND[bone],
        pt = 0,
        nk = null;
      for (const k of keys) {
        if (!(bone in k.pose)) continue;
        if (k.t <= tm) {
          pv = k.pose[bone];
          pt = k.t;
        } else {
          nk = k;
          break;
        }
      }
      if (!nk) pose[bone] = pv;
      else {
        const u = EASE[nk.ease || 'inout']((tm - pt) / (nk.t - pt));
        const nv = nk.pose[bone];
        pose[bone] = [pv[0] + (nv[0] - pv[0]) * u, pv[1] + (nv[1] - pv[1]) * u, pv[2] + (nv[2] - pv[2]) * u];
      }
    }
    let hv = 0,
      ht = 0,
      hn = null;
    for (const k of keys) {
      if (!('hips' in k)) continue;
      if (k.t <= tm) {
        hv = k.hips;
        ht = k.t;
      } else {
        hn = k;
        break;
      }
    }
    const hips = hn ? hv + (hn.hips - hv) * EASE[hn.ease || 'inout']((tm - ht) / (hn.t - ht)) : hv;
    return { pose, hips };
  }
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
  let hipsBase = 0,
    hipsNow = 0,
    hipsV = 0;
  const earBones = {},
    earRest = {},
    ear = { next: 3000, t: 0, side: 'L' };

  const log = (l) => window.petLog?.('[vrm] ' + l);
  async function load() {
    if (state !== 'off') return;
    state = 'loading';
    log('load() start, TV=' + !!window.TV + ' dpr=' + window.devicePixelRatio + ' ua=' + navigator.userAgent.slice(-60));
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
      const gl = renderer.getContext();
      log('WebGL ok: ' + (gl.getParameter(gl.VERSION) || '') + ' / ' + (gl.getParameter(gl.RENDERER) || ''));
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
    // 非像素模式按 2 倍超采样渲染再由浏览器缩回去，1080p/1440p（dpr 1）的桌面上才不糊
    renderer.setPixelRatio(pixel ? dpr / Math.max(2, Math.round(2 * dpr)) : navigator.webdriver ? 1 : Math.max(dpr, 2)); // 无头测试时不超采样
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
        // Chromium 里 GLTFLoader 默认用 ImageBitmapLoader（fetch blob: 贴图，受 CSP connect-src 管）；
        // 改用 <img> 的 TextureLoader，走 img-src，少一条坑
        loader.register((p) => {
          p.textureLoader = new THREE.TextureLoader(p.options.manager);
          p.textureLoader.setCrossOrigin(p.options.crossOrigin);
          return { name: 'kiko-texture-loader' };
        });
        // 贴图加载失败时 GLTFLoader 只 console.error 一句然后给 null，这里把它记进日志，方便排查
        const ce = console.error;
        console.error = (...a) => {
          log('console.error: ' + a.map((x) => (x && x.message) || String(x)).join(' ').slice(0, 300));
          ce.apply(console, a);
        };
        let gltf, v;
        try {
          log('loading ' + MODELS[outfit] + ' from ' + location.href);
          const t0 = performance.now();
          gltf = await loader.loadAsync(MODELS[outfit]);
          v = gltf.userData.vrm;
          if (!v) throw new Error('文件里没有 VRM 数据');
        // 浅色壁纸上白发/白耳边缘偏淡：描边加粗一点、颜色压成冷灰（描边是单独的材质副本，所以按名字全找一遍）
        v.scene.traverse((o) => {
          if (!o.isMesh) return;
          for (const m of Array.isArray(o.material) ? o.material : [o.material]) {
            if (!m || !m.isMToonMaterial) continue;
            if (/Hair|CatEar|FoxTail|Ahoge/.test(m.name)) {
              m.outlineWidthFactor = Math.max(m.outlineWidthFactor || 0, 0.00022) * 1.5;
              m.outlineColorFactor?.set(0x7f8db0);
            }
            // 深色壁纸上黑裤袜和鞋会融进背景：给身体/鞋加一圈淡淡的冷色边缘光
            if (/Body|Shoes|Legwear|SKIN/.test(m.name)) {
              m.parametricRimColorFactor?.set(0x4a5270);
              m.parametricRimFresnelPowerFactor = 3.5;
              m.parametricRimLiftFactor = 0.0;
            }
            m.needsUpdate = true;
          }
        });
          log(`loaded ${outfit} in ${Math.round(performance.now() - t0)}ms, expressions=${v.expressionManager?.expressions.length}, lookAt=${!!v.lookAt}, springs=${!!v.springBoneManager}`);
        } finally {
          console.error = ce;
        }
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
    for (const sd of ['L', 'R']) {
      earBones[sd] = v.scene.getObjectByName(`J_Opt_${sd}_CatEar1_01`) || null;
      if (earBones[sd]) earRest[sd] = earBones[sd].rotation.clone();
    }
    if (v.lookAt) {
      v.lookAt.target = lookTarget;
      v.lookAt.autoUpdate = true;
    }
    applyPose(0);
    v.update(0);
    frameCamera();
    log('wear ' + outfit + ' cam z=' + cam.position.z.toFixed(2));
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
      // 换心情：停掉持续/循环中的动作（拎着、走路、耷拉），再做新心情的动作
      if (!action || ACTS[action.name].hold || ACTS[action.name].loop !== undefined) action = null;
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
    const now = clock();
    if (name !== 'Flinch' && now < flinchEnd) return void setTimeout(() => act(name), flinchEnd - now);
    if (name === 'Flinch') flinchEnd = now + 620;
    action = { name, start: now };
    idleNext = now + 4000 + Math.random() * 6000;
    if (name === 'Hop') {
      canvas.classList.remove('hop');
      void canvas.offsetWidth;
      canvas.classList.add('hop');
    }
  }
  // 没事干（待机类心情、没在做动作、鼠标也没停在她身上）时隔几秒来个小动作
  let idleNext = 0;
  const IDLE_MOODS = new Set(['idle', 'happy', 'smug', 'smirk', 'meh', 'pout', 'bleh', 'wave']);
  // 姿势预览（设置窗口里选）：反复播放某个动作，直到清掉。给特蕾莎实机检查用
  let previewName = '';
  function preview(name) {
    previewName = ACTS[name] ? name : '';
    if (previewName) act(previewName);
  }
  function idleFidget() {
    if (fakeNow !== null) return;
    const now = clock();
    if (!action && previewName) return act(previewName);
    if (action || !IDLE_MOODS.has(curMood) || now < idleNext || hoverSince) return;
    act(IDLE_CLIPS[Math.floor(Math.random() * IDLE_CLIPS.length)]);
    idleNext = now + 6000 + Math.random() * 9000;
  }
  const poke = () => act('Flinch');

  // 每帧：姿势缓动 + 呼吸 + 看鼠标的头部转动 + 眨眼/说话 + 弹簧骨
  const blink = { next: 2000, t: -1 };
  const vel3 = {}; // 每个关节的角速度（弹簧跟随，有一点过冲）
  let fakeNow = null; // 离线逐帧渲染时用的假时钟（_renderAt）
  const clock = () => (fakeNow === null ? performance.now() : fakeNow);
  function applyPose(dt) {
    const now = clock() / 1000;
    idleFidget();
    let ev = null;
    if (action) {
      ev = evalClip(ACTS[action.name], clock() - action.start);
      if (!ev) action = null;
    }
    const extra = ev ? ev.pose : null;
    // 呼吸 + 慢慢换重心（髋和上身反向微倾）+ 头轻轻晃（待机）
    const br = S(now * 1.6),
      ws = S(now * 0.45);
    const idle = { hips: [0, 0, 1.6 * ws], spine: [1.2 * br, 0, -1.2 * ws], chest: [1.0 * br, 0, -0.6 * ws], head: [-0.6 * br, 0, 0.8 * S(now * 0.7) + 0.4 * ws], leftUpperArm: [0, 0, -1.0 * br], rightUpperArm: [0, 0, 1.0 * br] };
    // 耳朵偶尔抖一下（随机一只，0.25 秒）
    const ms0 = clock();
    if (ms0 > ear.next) {
      ear.side = Math.random() < 0.5 ? 'L' : 'R';
      ear.t = ms0;
      ear.next = ms0 + 3500 + Math.random() * 6000;
    }
    for (const sd of ['L', 'R']) {
      const b = earBones[sd];
      if (!b) continue;
      const p = ear.side === sd ? (ms0 - ear.t) / 260 : 2;
      const a = p < 1 ? bump(p) * 22 : 0; // 度
      b.rotation.set(earRest[sd].x + (sd === 'L' ? -a : a) * 0.4 * D, earRest[sd].y, earRest[sd].z + (sd === 'L' ? a : -a) * D);
    }
    // 看鼠标：头转 60%、脖子 25%、上身 15%
    const lh = { head: [-look.hy * 16, look.hx * 22, -look.hx * 4], neck: [-look.hy * 6, look.hx * 9, 0], chest: [0, look.hx * 5, 0] }; // x 正 = 低头
    // 弹簧跟随：目标变了以后追上去并稍微过冲一点，动作看起来有重量
    const ST = 230,
      DM = 2 * Math.sqrt(ST) * 0.78;
    for (const n of BONES) {
      const a = idle[n] || [0, 0, 0],
        b = extra ? extra[n] : STAND[n],
        c = lh[n] || [0, 0, 0];
      const v = (vel3[n] ||= [0, 0, 0]);
      for (let i = 0; i < 3; i++) {
        const target = b[i] + a[i] * (extra ? 0.4 : 1) + c[i];
        v[i] += ((target - cur3[n][i]) * ST - v[i] * DM) * dt;
        cur3[n][i] += v[i] * dt;
      }
      const nd = bones[n];
      if (!nd) continue;
      // 拎着横拖：整个人以髋为轴往后仰
      const sz = n === 'spine' ? swayNow * 1.2 : n === 'head' ? swayNow * 0.8 : 0;
      nd.rotation.set(cur3[n][0] * D, cur3[n][1] * D, (cur3[n][2] + sz) * D, 'XYZ');
    }
    // 髋骨升降（蹲、踮脚）也用弹簧
    hipsV += ((((ev && ev.hips) || 0) - hipsNow) * ST - hipsV * DM) * dt;
    hipsNow += hipsV * dt;
    if (bones.hips) bones.hips.position.y = hipsBase + hipsNow;
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
    if (fakeNow !== null) return void (raf = requestAnimationFrame(tick)); // 离线渲染中，别动
    const dt = lastT ? Math.min(0.04, (ts - lastT) / 1000) : 1 / 30;
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
  const onFailed = (fn) => (onFail = fn);
  // 调试：离线算到动作 name 的第 tm 毫秒并画一帧（固定 60 步/秒模拟，结果和时间无关）
  let seq = { name: null, tm: -1 };
  function _renderAt(name, tm) {
    if (!vrm) return;
    const step = 1000 / 60;
    if (seq.name !== name || tm < seq.tm) {
      for (const n of BONES) {
        cur3[n] = [...STAND[n]];
        vel3[n] = [0, 0, 0];
      }
      hipsNow = hipsV = 0;
      look.x = look.y = look.hx = look.hy = 0;
      seq = { name, tm: -step };
    }
    action = name ? { name, start: 0 } : null;
    for (let t = seq.tm + step; t <= tm; t += step) {
      fakeNow = t;
      applyPose(step / 1000);
      vrm.update(step / 1000);
      seq.tm = t;
    }
    fakeNow = seq.tm;
    renderer.render(scene, cam); // 画完后保持暂停（fakeNow 不清），实时循环不会把姿势拉回去；_resume() 恢复
  }
  function _resume() {
    fakeNow = null;
    action = null;
    seq = { name: null, tm: -1 };
  } // 加载失败时把原因交给 pet.js（正式版没有 devtools，冒个泡方便排查）
  return { load, show, hide, active, talk, lookTo, can, has, act, poke, sway, setPixel, preview, onLoaded, onStartled, onFailed, _acts: ACTS, _renderAt, _resume, _dbg: () => ({ hipsNow, hipsV, hy: bones.hips?.position.y, cur: cur3, action, seq }) };
})();
