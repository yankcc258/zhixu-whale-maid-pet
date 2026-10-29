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
# ---- geometry (fin local: +x outward, +y up, +z forward). Two layers: dark outer ear + lavender scalloped inner.
def bez(p0,p1,p2,n):
    t=np.linspace(0,1,n)[:,None]; return (1-t)**2*p0+2*(1-t)*t*p1+t*t*p2
def cupped(outline, center, cup, zoff):
    P=np.asarray(outline,np.float32); c=np.asarray(center,np.float32); n=len(P)
    V=[*P]+[(p+c)/2 for p in P]+[c]; ci=2*n
    T=[]
    for i in range(n):
        a,b=i,(i+1)%n; ma,mb=n+a,n+b; T+=[(a,b,mb),(a,mb,ma),(ma,mb,ci)]
    V=np.array(V,np.float32)
    span=V[:,0].max()+1e-6
    z=zoff+cup*np.sin(np.pi*np.clip(V[:,0]/span,0,1))*0.6 - cup*((V[:,1]-c[1])/0.03)**2
    pos=np.c_[V[:,0],V[:,1],z].astype(np.float32)
    uv=np.c_[V[:,0]/span, 1-(V[:,1]-V[:,1].min())/(np.ptp(V[:,1])+1e-6)].astype(np.float32)
    nrm=np.zeros_like(pos)
    for t in T:
        p0,p1,p2=pos[list(t)]; nrm[list(t)]+=np.cross(p1-p0,p2-p0)
    nrm/=np.linalg.norm(nrm,axis=1,keepdims=True)+1e-9
    return pos,nrm,uv,np.array(T,np.uint16).reshape(-1)
S=1.0
root_top=np.array([0.0,0.020]); tip=np.array([0.078,-0.016]); root_bot=np.array([0.0,-0.018])
top=bez(root_top,np.array([0.045,0.034]),tip,22)
bot=bez(tip,np.array([0.040,-0.030]),root_bot,22)[1:-1]
outer=[*top,*bot]
# inner lavender: lower part, scalloped bottom (round bumps)
it0=np.array([0.004,-0.002]); it1=np.array([0.070,-0.014])
itop=bez(it0,np.array([0.040,0.006]),it1,14)
base=bez(it1,np.array([0.040,-0.036]),np.array([0.002,-0.022]),60)
k=np.arange(len(base)); bump=0.0042*np.abs(np.sin(k/len(base)*np.pi*4.0))
ibot=base-np.c_[np.zeros(len(base)),bump]
inner=[*itop,*ibot[1:-1]]
meshes=[]
for name,ol,cen,cup,zo,cols in [('outer',outer,(0.034,0.0),0.006,0.0,((38,48,98),(58,70,130))),
                                ('inner',inner,(0.034,-0.016),0.005,0.0025,((150,158,215),(214,218,245)))]:
    pos,nrm,uv,idx=cupped(ol,cen,cup,zo)
    im=Image.new('RGBA',(64,64)); dr=ImageDraw.Draw(im)
    for y in range(64):
        t=y/63; dr.line([(0,y),(64,y)],fill=tuple(int(cols[0][q]+(cols[1][q]-cols[0][q])*t) for q in range(3))+(255,))
    buf=io.BytesIO(); im.save(buf,'PNG')
    ibv=add_view(buf.getvalue()); j['images'].append({'name':'Seeko_EarFin_'+name,'mimeType':'image/png','bufferView':ibv})
    j.setdefault('samplers',[]).append({'magFilter':9729,'minFilter':9987,'wrapS':33071,'wrapT':33071})
    j['textures'].append({'sampler':len(j['samplers'])-1,'source':len(j['images'])-1}); tex=len(j['textures'])-1
    base_m=next(m for m in j['materials'] if '_Hair_' in m['name'] and 'HairBack' not in m['name'])
    m=copy.deepcopy(base_m); m['name']='Seeko_EarFin_'+name; m['doubleSided']=True
    m['pbrMetallicRoughness']['baseColorTexture']={'index':tex,'texCoord':0}
    for kk in ('normalTexture','emissiveTexture'): m.pop(kk,None)
    m['emissiveFactor']=[0,0,0]; mt=m['extensions']['VRMC_materials_mtoon']
    mt['shadeMultiplyTexture']={'index':tex}; mt['shadeColorFactor']=[0.8,0.82,0.94]; mt['outlineColorFactor']=[0.05,0.06,0.15]
    mt.pop('matcapTexture',None); mt['matcapFactor']=[0,0,0]
    j['materials'].append(m)
    meshes.append({'attributes':{'POSITION':add_acc(pos,'VEC3'),'NORMAL':add_acc(nrm,'VEC3'),'TEXCOORD_0':add_acc(uv,'VEC2')},
                   'indices':add_acc(idx.reshape(-1,1).astype(np.uint16),'SCALAR',5123,34963),'material':len(j['materials'])-1,'mode':4})
j['meshes'].append({'name':'Seeko_EarFin','primitives':meshes}); mesh=len(j['meshes'])-1
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
    wp=np.array([0.078*side, EYE_Y+0.022, -0.026, 1.0]); lp=(inv@wp)[:3]
    q=qmul(qmul(quat([0,1,0],12*side), quat([0,0,1],-6*side)), quat([1,0,0],12))   # sweep back + droop
    node={'name':'Seeko_EarFin_'+('L' if side>0 else 'R'),'mesh':mesh,'translation':lp.tolist(),'rotation':q.tolist()}
    node['scale']=[-1.3 if side<0 else 1.3,1.3,1.3]
    j['nodes'].append(node); j['nodes'][head].setdefault('children',[]).append(len(j['nodes'])-1)
# write
while len(BIN)%4: BIN.append(0)
j['buffers'][0]['byteLength']=len(BIN)
js=json.dumps(j,separators=(',',':')).encode()
while len(js)%4: js+=b' '
open(dst,'wb').write(struct.pack('<4sII',b'glTF',2,12+8+len(js)+8+len(BIN))+struct.pack('<I4s',len(js),b'JSON')+js+struct.pack('<I4s',len(BIN),b'BIN\x00')+bytes(BIN))
print('fins added ->',dst)
