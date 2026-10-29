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
# ---- geometry (fin local: +x outward, +y up, +z forward)
S = 1.15
outline = [(0,0.014),(0.016,0.026),(0.034,0.032),(0.052,0.031),(0.068,0.024),(0.080,0.012),(0.085,-0.002),(0.082,-0.014),
           (0.074,-0.022),(0.066,-0.019),(0.058,-0.028),(0.049,-0.022),(0.040,-0.030),(0.031,-0.024),(0.022,-0.030),(0.012,-0.022),(0.004,-0.024),(0,-0.014)]
P = np.array(outline, np.float32)*S; c = np.array([0.038,-0.002], np.float32)*S
pts2 = np.vstack([c[None], P])
# subdivide fan once (midpoints) for a smoother cup
verts=[]; tris=[]
n=len(P)
ring=[]
for i in range(n):
    ring.append(len(verts)); verts.append(P[i])
mid=[]
for i in range(n):
    mid.append(len(verts)); verts.append((P[i]+c)/2)
ci=len(verts); verts.append(c)
for i in range(n-1):
    a,b=ring[i],ring[i+1]; ma,mb=mid[i],mid[i+1]
    tris += [(a,b,mb),(a,mb,ma),(ma,mb,ci)]
V2=np.array(verts,np.float32)
z = 0.008*np.sin(np.pi*np.clip(V2[:,0]/(0.085*S),0,1)) - 0.007*((V2[:,1]/(0.031*S))**2)
pos=np.c_[V2[:,0],V2[:,1],z].astype(np.float32)
uv=np.c_[V2[:,0]/(0.086*S), 1-(V2[:,1]+0.031*S)/(0.064*S)].astype(np.float32)
idx=np.array(tris,np.uint16).reshape(-1)
# normals
nrm=np.zeros_like(pos)
for t in np.array(tris):
    p0,p1,p2=pos[t]; fn=np.cross(p1-p0,p2-p0); nrm[t]+=fn
nrm/=np.linalg.norm(nrm,axis=1,keepdims=True)+1e-9
# ---- texture
W,H=256,256; im=Image.new('RGBA',(W,H),(43,53,102,255)); dr=ImageDraw.Draw(im)
for y in range(H):
    t=y/H; col=(int(43+20*(1-t)),int(53+25*(1-t)),int(102+40*(1-t)),255); dr.line([(0,y),(W,y)],fill=col)
# inner lighter lobe + scalloped lavender underside
dr.ellipse([W*0.15,H*0.42,W*0.85,H*0.82],fill=(122,132,196,255))
dr.rectangle([0,H*0.72,W,H],fill=(200,206,240,255))
im=im.filter(ImageFilter.GaussianBlur(6))
buf=io.BytesIO(); im.save(buf,'PNG')
ibv=add_view(buf.getvalue()); j['images'].append({'name':'Seeko_EarFin','mimeType':'image/png','bufferView':ibv})
j.setdefault('samplers',[]).append({'magFilter':9729,'minFilter':9987,'wrapS':33071,'wrapT':33071})
j['textures'].append({'sampler':len(j['samplers'])-1,'source':len(j['images'])-1}); tex=len(j['textures'])-1
# material: clone hair MToon material
base=next(m for m in j['materials'] if '_Hair_' in m['name'] and 'HairBack' not in m['name'])
m=copy.deepcopy(base); m['name']='Seeko_EarFin'; m['doubleSided']=True
m['pbrMetallicRoughness']['baseColorTexture']={'index':tex,'texCoord':0}
for k in ('normalTexture','emissiveTexture'): m.pop(k,None)
m['emissiveFactor']=[0,0,0]
mt=m['extensions']['VRMC_materials_mtoon']; mt['shadeMultiplyTexture']={'index':tex}; mt['shadeColorFactor']=[0.78,0.80,0.92]
mt['outlineColorFactor']=[0.06,0.07,0.15]
j['materials'].append(m); mat=len(j['materials'])-1
prim={'attributes':{'POSITION':add_acc(pos,'VEC3'),'NORMAL':add_acc(nrm,'VEC3'),'TEXCOORD_0':add_acc(uv,'VEC2')},
      'indices':add_acc(idx.reshape(-1,1).astype(np.uint16),'SCALAR',5123,34963),'material':mat,'mode':4}
j['accessors'][prim['indices']].pop('min',None)
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
    wp=np.array([0.076*side, EYE_Y+0.030, -0.024, 1.0]); lp=(inv@wp)[:3]
    q=qmul(quat([0,1,0],22*side), quat([0,0,1],-38*side))   # sweep back + droop
    node={'name':'Seeko_EarFin_'+('L' if side>0 else 'R'),'mesh':mesh,'translation':lp.tolist(),'rotation':q.tolist()}
    if side<0: node['scale']=[-1,1,1]
    j['nodes'].append(node); j['nodes'][head].setdefault('children',[]).append(len(j['nodes'])-1)
# write
while len(BIN)%4: BIN.append(0)
j['buffers'][0]['byteLength']=len(BIN)
js=json.dumps(j,separators=(',',':')).encode()
while len(js)%4: js+=b' '
open(dst,'wb').write(struct.pack('<4sII',b'glTF',2,12+8+len(js)+8+len(BIN))+struct.pack('<I4s',len(js),b'JSON')+js+struct.pack('<I4s',len(BIN),b'BIN\x00')+bytes(BIN))
print('fins added ->',dst)
