import * as THREE from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { VRMLoaderPlugin, VRMUtils } from '@pixiv/three-vrm';
const W=480,H=640;
const renderer=new THREE.WebGLRenderer({antialias:true,preserveDrawingBuffer:true});
renderer.setSize(W,H); renderer.setClearColor(0xe9ecf2,1); document.body.appendChild(renderer.domElement);
const scene=new THREE.Scene();
scene.add(new THREE.AmbientLight(0xffffff,0.6));
const dl=new THREE.DirectionalLight(0xffffff,2.2); dl.position.set(1,2,3); scene.add(dl);
const cam=new THREE.PerspectiveCamera(22,W/H,0.1,50);
const loader=new GLTFLoader(); loader.register(p=>new VRMLoaderPlugin(p));
const MODEL=new URLSearchParams(location.search).get('m')||'model.vrm';
loader.load(MODEL,g=>{
  const vrm=g.userData.vrm; VRMUtils.rotateVRM0(vrm); scene.add(vrm.scene);
  const STYLE=new URLSearchParams(location.search).get('s')||'mtoon';
  if(STYLE==='soft'){
    renderer.toneMapping=THREE.ACESFilmicToneMapping; renderer.toneMappingExposure=1.05;
    scene.add(new THREE.HemisphereLight(0xf2f5ff,0xb8a8a0,1.6));
    const rim=new THREE.DirectionalLight(0xdfe8ff,1.2); rim.position.set(-2,1.5,-2); scene.add(rim);
    vrm.scene.traverse(o=>{ if(!o.isMesh) return; const ms=Array.isArray(o.material)?o.material:[o.material];
      const nm=ms.map(m=>{ if(!m.map && !m.color) return m; const n=new THREE.MeshStandardMaterial({map:m.map||null,color:m.color?m.color.clone():0xffffff,roughness:0.55,metalness:0,transparent:m.transparent,alphaTest:m.alphaTest||0,side:m.side});
        if(m.name&&/outline/i.test(m.name)) n.visible=false; return n;});
      o.material=Array.isArray(o.material)?nm:nm[0]; });
  }
  // relaxed arms (A-pose)
  const h=vrm.humanoid;
  h.getNormalizedBoneNode('leftUpperArm').rotation.z=-1.15;
  h.getNormalizedBoneNode('rightUpperArm').rotation.z=1.15;
  vrm.update(0); for(let i=0;i<60;i++) vrm.update(1/30);
  const box=new THREE.Box3().setFromObject(vrm.scene); const c=box.getCenter(new THREE.Vector3()); const sz=box.getSize(new THREE.Vector3());
  const dist=(window.FIXH||sz.y)/2/Math.tan(THREE.MathUtils.degToRad(11))*1.12; c.y=(window.FIXH? window.FIXH/2 : c.y);
  window.shots={};
  if(new URLSearchParams(location.search).get('face')){ const hp=new THREE.Vector3(); h.getNormalizedBoneNode('head').getWorldPosition(hp);
    cam.position.set(hp.x,hp.y+0.06,hp.z+0.9); cam.lookAt(hp.x,hp.y+0.06,hp.z); renderer.render(scene,cam); window.shots.face=renderer.domElement.toDataURL('image/png'); window.done=true; return; } // FACE
  for(const [name,ang] of [['front',0],['q',Math.PI/5],['back',Math.PI],['bq',Math.PI*0.8]]){
    cam.position.set(c.x+Math.sin(ang)*dist,c.y,c.z+Math.cos(ang)*dist); cam.lookAt(c);
    renderer.render(scene,cam); window.shots[name]=renderer.domElement.toDataURL('image/png');
  }
  window.done=true;
},undefined,e=>{window.err=String(e);window.done=true});
