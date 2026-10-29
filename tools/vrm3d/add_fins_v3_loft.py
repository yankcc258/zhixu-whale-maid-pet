"""Add whale ear fins (Seeko) to a VRoid VRM: python3 add_fins.py in.vrm out.vrm"""
import json, struct, sys, io, math, copy
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
sys.path.insert(0, __file__.rsplit('/',1)[0]); from gltfmath import world
src, dst = sys.argv[1], sys.argv[2]
d = open(src,'rb').read(); L = struct.unpack('<I', d[12:16])[0]; j = json.loads(d[20:20+L])
b0 = 20+L; BL = struct.unpack('<I', d[b0:b0+4])[0]; BIN = bytearray(d[b0+8:b0+8+BL])
def add_view(data, target=None):
    while len(BIN) % 4: BIN.append(0)
    v = {'buffer':0,'byteOffset':len(BIN),'byteLength':len(data)}
    if target: v['target'] = target
    BIN.extend(data); j['bufferViews'].append(v); return len(j['bufferViews'])-1
def add_acc(arr, typ, comp=5126, target=34962):
    arr = np.ascontiguousarray(arr); bv = add_view(arr.tobytes(), target)
    a = {'bufferView':bv,'componentType':comp,'count':int(arr.shape[0]),'type':typ}
    if typ == 'VEC3': a['min'] = arr.min(0).tolist(); a['max'] = arr.max(0).tolist()
    j['accessors'].append(a); return len(j['accessors'])-1
# ---- geometry v3: volumetric floppy ear (lofted cross-sections), root buried under hair.
# local frame: +x outward, +y up, +z forward.
NU, NP = 44, 28
LEN = 0.090
def frame_at(u):
    c = np.array([LEN*u, -0.030*u**1.7, -0.010*u])           # centerline: out, droop with gravity, slightly back
    dc = np.array([LEN, -0.030*1.7*max(u,1e-3)**0.7, -0.010]); T = dc/np.linalg.norm(dc)
    up = np.array([0,1.0,0]); B = up - T*np.dot(up,T); B/=np.linalg.norm(B)
    N = np.cross(T,B)
    tilt = math.radians(58)                                  # inner face looks forward-down
    B2 = B*math.cos(tilt) + N*math.sin(tilt); N2 = np.cross(T,B2)
    return c, B2, N2
def width(u):  return 0.050*(math.sin(math.pi*(0.18+0.82*u))**0.65)*(1-0.15*u) + 0.004
def thick(u):  return 0.016*(1-u)**0.9 + 0.0025
V=[]; UV=[]
for i in range(NU):
    u=i/(NU-1); c,B,N=frame_at(u); w=width(u); t=thick(u)
    for k in range(NP):
        ph=2*math.pi*k/NP
        # slightly cupped section: inner (N+) face concave
        p = c + B*(w/2)*math.cos(ph) + N*(t/2)*math.sin(ph) - N*0.004*(math.cos(ph)**2)*u
        V.append(p); UV.append((u, k/NP))
tip_c,_,_=frame_at(1.0); tip=frame_at(1.0)[0]+ (frame_at(1.0)[0]-frame_at(0.97)[0])*0.6
V.append(tip); UV.append((1.0,0.5)); tip_i=len(V)-1
V.append(frame_at(0)[0]); UV.append((0.0,0.5)); root_i=len(V)-1
T=[]
for i in range(NU-1):
    for k in range(NP):
        a=i*NP+k; b=i*NP+(k+1)%NP; c2=(i+1)*NP+k; d=(i+1)*NP+(k+1)%NP
        T+=[(a,c2,b),(b,c2,d)]
for k in range(NP):
    T.append(((NU-1)*NP+k, tip_i, (NU-1)*NP+(k+1)%NP)); T.append((k+0, (k+1)%NP, root_i))
pos=np.array(V,np.float32); uv=np.array(UV,np.float32)
nrm=np.zeros_like(pos)
for t in T:
    p0,p1,p2=pos[list(t)]; nrm[list(t)]+=np.cross(p1-p0,p2-p0)
nrm/=np.linalg.norm(nrm,axis=1,keepdims=True)+1e-9
idx=np.array(T,np.uint16).reshape(-1)
# texture: x=u (root->tip), y=phi. phi in (0,0.5) = inner face (N+). navy outside, lavender inner with cloud-scallop edge
W,H=256,128; tx=np.zeros((H,W,4),np.float32)
uu=np.linspace(0,1,W)[None,:]; pp=np.linspace(0,1,H,endpoint=False)[:,None]
navy=np.array([36,46,96.]); navy2=np.array([60,72,132.]); lav=np.array([168,174,226.]); lav2=np.array([224,228,248.])
base=navy+(navy2-navy)*np.clip(uu,0,1)[...,None]*0.6+np.zeros((H,W,1))
sinp=np.sin(2*np.pi*pp)                                       # >0 inner face
edge=0.10+0.10*np.abs(np.sin(uu*np.pi*3.5))                   # scallop boundary near the lower edge
inner=np.clip((sinp+0.10)/0.25,0,1)
lower=np.clip((np.cos(2*np.pi*pp)*-1+1-edge*4)/0.35,0,1)       # lavender spills over the bottom rim in scallops
m=np.clip(np.maximum(inner*np.clip(uu*6,0,1), lower*inner*0+0),0,1)
lc=lav+(lav2-lav)*np.clip((np.cos(2*np.pi*pp)*-0.5+0.5),0,1)[...,None]
col=base*(1-m[...,None])+lc*m[...,None]
tx[...,:3]=col; tx[...,3]=255
im=Image.fromarray(tx.clip(0,255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.2))
buf=io.BytesIO(); im.save(buf,'PNG')
ibv=add_view(buf.getvalue()); j['images'].append({'name':'Seeko_EarFin','mimeType':'image/png','bufferView':ibv})
j.setdefault('samplers',[]).append({'magFilter':9729,'minFilter':9987,'wrapS':33071,'wrapT':10497})
j['textures'].append({'sampler':len(j['samplers'])-1,'source':len(j['images'])-1}); tex=len(j['textures'])-1
base_m=next(mm for mm in j['materials'] if '_Hair_' in mm['name'] and 'HairBack' not in mm['name'])
m_=copy.deepcopy(base_m); m_['name']='Seeko_EarFin'; m_['doubleSided']=False
m_['pbrMetallicRoughness']['baseColorTexture']={'index':tex,'texCoord':0}
for kk in ('normalTexture','emissiveTexture'): m_.pop(kk,None)
m_['emissiveFactor']=[0,0,0]; mt=m_['extensions']['VRMC_materials_mtoon']
mt['shadeMultiplyTexture']={'index':tex}; mt['shadeColorFactor']=[0.78,0.8,0.95]; mt['outlineColorFactor']=[0.06,0.06,0.16]
mt.pop('matcapTexture',None); mt['matcapFactor']=[0,0,0]; mt['shadingToonyFactor']=0.75
j['materials'].append(m_)
prim={'attributes':{'POSITION':add_acc(pos,'VEC3'),'NORMAL':add_acc(nrm,'VEC3'),'TEXCOORD_0':add_acc(uv,'VEC2')},
      'indices':add_acc(idx.reshape(-1,1).astype(np.uint16),'SCALAR',5123,34963),'material':len(j['materials'])-1,'mode':4}
j['meshes'].append({'name':'Seeko_EarFin','primitives':[prim]}); mesh=len(j['meshes'])-1
# ---- attach to head
head=j['extensions']['VRMC_vrm']['humanoid']['humanBones']['head']['node']
Wh=world(j,head); inv=np.linalg.inv(Wh)
def quat(axis,deg):
    a=math.radians(deg)/2; ax=np.array(axis,float); ax/=np.linalg.norm(ax); return np.r_[ax*math.sin(a),math.cos(a)]
def qmul(a,b):
    x1,y1,z1,w1=a; x2,y2,z2,w2=b
    return np.array([w1*x2+x1*w2+y1*z2-z1*y2, w1*y2-x1*z2+y1*w2+z1*x2, w1*z2+x1*y2-y1*x2+z1*w2, w1*w2-x1*x2-y1*y2-z1*z2])
EYE_Y=1.2311
for side in (1,-1):
    wp=np.array([0.060*side, EYE_Y+0.026, -0.030, 1.0]); lp=(inv@wp)[:3]
    q=qmul(quat([0,1,0],14*side), quat([0,0,1],-4*side))   # sweep back + droop
    node={'name':'Seeko_EarFin_'+('L' if side>0 else 'R'),'mesh':mesh,'translation':lp.tolist(),'rotation':q.tolist()}
    node['scale']=[-1.0 if side<0 else 1.0,1.0,1.0]
    j['nodes'].append(node); j['nodes'][head].setdefault('children',[]).append(len(j['nodes'])-1)
# write
while len(BIN)%4: BIN.append(0)
j['buffers'][0]['byteLength']=len(BIN)
js=json.dumps(j,separators=(',',':')).encode()
while len(js)%4: js+=b' '
open(dst,'wb').write(struct.pack('<4sII',b'glTF',2,12+8+len(js)+8+len(BIN))+struct.pack('<I4s',len(js),b'JSON')+js+struct.pack('<I4s',len(BIN),b'BIN\x00')+bytes(BIN))
print('fins added ->',dst)
