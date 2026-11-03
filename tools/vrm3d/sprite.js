// Sprite renderer for the web pet: bust-up (or full) transparent renders with expression + pose presets.
import * as THREE from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { VRMLoaderPlugin, VRMUtils } from '@pixiv/three-vrm';
const q = new URLSearchParams(location.search);
const MODEL = q.get('m') || 'model.vrm', S = Number(q.get('size') || 880);
const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, preserveDrawingBuffer: true });
renderer.setSize(S, S); renderer.setClearColor(0x000000, 0); renderer.outputColorSpace = THREE.SRGBColorSpace;
document.body.appendChild(renderer.domElement);
const scene = new THREE.Scene();
scene.add(new THREE.AmbientLight(0xffffff, 0.7));
const key = new THREE.DirectionalLight(0xffffff, 2.0); key.position.set(0.6, 1.5, 2.5); scene.add(key);
const fill = new THREE.DirectionalLight(0xdde8ff, 0.6); fill.position.set(-1.5, 0.5, 1.5); scene.add(fill);
const cam = new THREE.PerspectiveCamera(22, 1, 0.05, 20);
const D = (d) => THREE.MathUtils.degToRad(d);
// presets: expression weights + bone euler rotations (deg) + framing
const PRESETS = {
  idle:     { ex: { relaxed: 0.15 }, bones: { head: [0, 0, 0] }, frame: 'bust' },
  happy:    { ex: { happy: 0.8, aa: 0.2 }, bones: { head: [-3, 0, 4], neck: [0, 0, 2] }, frame: 'bust' },
  smirk:    { ex: { blinkRight: 0.5, blinkLeft: 0.1, m_Fcl_MTH_SkinFung_R: 1.0, m_Fcl_MTH_Fun: 0.35, m_Fcl_HA_Fung1: 0.8, m_Fcl_BRW_Fun: 0.5, m_Fcl_EYE_Fun: 0.3 }, bones: { head: [3, 12, -6], neck: [0, 4, 0] }, frame: 'bust' },
  meh:      { ex: { blink: 0.45, m_Fcl_BRW_Angry: 0.35, m_Fcl_MTH_Small: 0.5 }, bones: { head: [2, -16, 4], neck: [0, -6, 0] }, frame: 'bust' },
  dangle:   { ex: { surprised: 0.35, angry: 0.3, aa: 0.4 }, bones: { hips: [0, 10, 9], spine: [-5, 8, -6], chest: [0, 4, 0], head: [5, -6, -12],
              leftUpperArm: [-45, 0, -30], rightUpperArm: [-45, 0, 30], leftLowerArm: [0, -118, 0], rightLowerArm: [0, 118, 0],
              leftUpperLeg: [-40, 0, -18], rightUpperLeg: [15, 0, 14], leftLowerLeg: [70, 0, 0], rightLowerLeg: [8, 0, 0] }, frame: 'full' },
  sleep:    { ex: { blink: 1.0, relaxed: 0.5 }, bones: { head: [10, 0, 14], neck: [3, 0, 4] }, frame: 'bust' },
  angry:    { ex: { angry: 1.0, ee: 0.4 }, bones: { head: [-6, 0, 0] }, frame: 'bust' },
  surprised:{ ex: { surprised: 1.0, oh: 0.6 }, bones: { head: [-8, 0, 0] }, frame: 'bust' },
};
const loader = new GLTFLoader(); loader.register((p) => new VRMLoaderPlugin(p));
loader.load(MODEL, (g) => {
  const vrm = g.userData.vrm; VRMUtils.rotateVRM0(vrm); scene.add(vrm.scene);
  const h = vrm.humanoid, em = vrm.expressionManager;
  const TOON = Number(q.get('toon') || 0);   // 0 = as exported; 1 = thicker outline + flatter shading (hand-drawn feel)
  if (TOON) vrm.scene.traverse((o) => { if (!o.isMesh) return; for (const m of (Array.isArray(o.material) ? o.material : [o.material])) {
    if (!m || !m.isMToonMaterial) continue;
    const isHair = /Hair|Ahoge|Ear|Tail/.test(m.name || '');
    if (TOON >= 2 && isHair) { m.outlineWidthFactor = 0; m.normalMap = null; if (m.matcapFactor) m.matcapFactor.setScalar(0); if (m.shadeColorFactor) m.shadeColorFactor.setRGB(0.86, 0.88, 0.94); if (m.rimLightingMixFactor !== undefined) m.rimLightingMixFactor = 0; }
    else if (m.outlineWidthFactor !== undefined) m.outlineWidthFactor = m.outlineWidthFactor * (1 + 1.2 * Math.min(TOON, 1));
    if (m.shadingToonyFactor !== undefined) m.shadingToonyFactor = 1.0;
    if (m.shadingShiftFactor !== undefined) m.shadingShiftFactor = Math.max(m.shadingShiftFactor, -0.15);
    if (m.outlineColorFactor && m.outlineColorFactor.isColor) m.outlineColorFactor.multiplyScalar(0.6);
    m.needsUpdate = true; } });
  const rest = {};
  for (const b of ['hips','spine','chest','neck','head','leftUpperArm','rightUpperArm','leftLowerArm','rightLowerArm','leftUpperLeg','rightUpperLeg','leftLowerLeg','rightLowerLeg']) {
    const n = h.getNormalizedBoneNode(b); if (n) rest[b] = n.rotation.clone();
  }
  window.shots = {};
  const names = (q.get('p') || Object.keys(PRESETS).join(',')).split(',');
  for (const name of names) {
    const P = PRESETS[name]; if (!P) continue;
    for (const b in rest) h.getNormalizedBoneNode(b).rotation.copy(rest[b]);
    // relaxed A-pose arms by default
    h.getNormalizedBoneNode('leftUpperArm').rotation.z = D(-62); h.getNormalizedBoneNode('rightUpperArm').rotation.z = D(62);
    for (const b in P.bones) { const n = h.getNormalizedBoneNode(b); if (!n) continue; const [x, y, z] = P.bones[b];
      if (b.endsWith('UpperArm')) n.rotation.set(D(x), D(y), D(z)); else n.rotation.set(rest[b].x + D(x), rest[b].y + D(y), rest[b].z + D(z)); }
    for (const e of em.expressions) em.setValue(e.expressionName, 0);
    for (const e in P.ex) em.setValue(e, P.ex[e]);
    vrm.update(0); for (let i = 0; i < 90; i++) vrm.update(1 / 30);   // let spring bones settle
    const hp = new THREE.Vector3(); h.getNormalizedBoneNode('head').getWorldPosition(hp);
    if (P.frame === 'bust') { cam.fov = 24; const HS = Number(q.get('hs') || 1), UP = Number(q.get('up') || 0.045); cam.position.set(hp.x, hp.y + UP + 0.045 * HS, hp.z + 0.98 * HS); cam.lookAt(hp.x, hp.y + UP, hp.z); }
    else { const box = new THREE.Box3().setFromObject(vrm.scene); const c = box.getCenter(new THREE.Vector3()); const sz = box.getSize(new THREE.Vector3());
      cam.fov = 22; const dist = Math.max(sz.y, sz.x) / 2 / Math.tan(D(11)) * 1.08; cam.position.set(c.x, c.y, c.z + dist); cam.lookAt(c); }
    cam.updateProjectionMatrix();
    renderer.render(scene, cam); window.shots[name] = renderer.domElement.toDataURL('image/png');
  }
  window.done = true;
}, undefined, (e) => { window.err = String(e); window.done = true; });
