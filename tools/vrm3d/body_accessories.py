"""Body accessories for Kiko (white fox maid): big white apron bow at the waist back (on the
spine bone) and white frilled wrist cuffs (on each hand bone). Run AFTER add_accessories.py.
usage: python3 body_accessories.py in.vrm out.vrm
env: WBOW (scale of waist bow, default 1), CUFF (0 to skip cuffs)"""
import json, struct, sys, io, math, copy, os
import numpy as np
from PIL import Image, ImageDraw
sys.path.insert(0, __file__.rsplit('/',1)[0]); from gltfmath import world
src, dst = sys.argv[1], sys.argv[2]
d=open(src,'rb').read(); L=struct.unpack('<I',d[12:16])[0]; j=json.loads(d[20:20+L])
b0=20+L; BL=struct.unpack('<I',d[b0:b0+4])[0]; BIN=bytearray(d[b0+8:b0+8+BL])
def add_view(data,target=None):
    while len(BIN)%4: BIN.append(0)
    v={'buffer':0,'byteOffset':len(BIN),'byteLength':len(data)}
    if target: v['target']=target
    BIN.extend(data); j['bufferViews'].append(v); return len(j['bufferViews'])-1
def add_acc(arr,typ,comp=5126,target=34962):
    arr=np.ascontiguousarray(arr); a={'bufferView':add_view(arr.tobytes(),target),'componentType':comp,'count':int(arr.shape[0]),'type':typ}
    if typ=='VEC3': a['min']=arr.min(0).tolist(); a['max']=arr.max(0).tolist()
    j['accessors'].append(a); return len(j['accessors'])-1
def add_tex(img):
    buf=io.BytesIO(); img.save(buf,'PNG'); j['images'].append({'name':'kiko_body_acc','mimeType':'image/png','bufferView':add_view(buf.getvalue())})
    j.setdefault('samplers',[]).append({'magFilter':9729,'minFilter':9987,'wrapS':10497,'wrapT':33071})
    j['textures'].append({'sampler':len(j['samplers'])-1,'source':len(j['images'])-1}); return len(j['textures'])-1
BASE=next(m for m in j['materials'] if 'Tops' in m['name'] or 'CLOTH' in m['name'])
def add_mat(name,tex,shade=(0.78,0.8,0.86),outline=(0.25,0.27,0.35)):
    m=copy.deepcopy(BASE); m['name']=name; m['doubleSided']=True; m['alphaMode']='OPAQUE'; m.pop('alphaCutoff',None)
    mt=m['extensions']['VRMC_materials_mtoon']; mt.pop('transparentWithZWrite',None)
    m['pbrMetallicRoughness']['baseColorTexture']={'index':tex,'texCoord':0}; m['pbrMetallicRoughness']['baseColorFactor']=[1,1,1,1]
    for k in ('normalTexture','emissiveTexture'): m.pop(k,None)
    m['emissiveFactor']=[0,0,0]
    mt['shadeMultiplyTexture']={'index':tex}; mt['shadeColorFactor']=list(shade); mt['outlineColorFactor']=list(outline)
    mt['outlineWidthFactor']=0.0008; mt.pop('matcapTexture',None); mt['matcapFactor']=[0,0,0]
    for k in ('rimMultiplyTexture','uvAnimationMaskTexture'): mt.pop(k,None)
    j['materials'].append(m); return len(j['materials'])-1
def grad_tex(top,bot,size=64):
    im=Image.new('RGBA',(size,size)); dr=ImageDraw.Draw(im)
    for y in range(size):
        t=y/(size-1); dr.line([(0,y),(size,y)],fill=tuple(int(top[k]+(bot[k]-top[k])*t) for k in range(3))+(255,))
    return im
HB=j['extensions']['VRMC_vrm']['humanoid']['humanBones']
def attach(bone,name,mesh,wpos,wrot=None):
    node=HB[bone]['node']; W=world(j,node); INV=np.linalg.inv(W)
    lp=(INV@np.r_[wpos,1.0])[:3]
    n={'name':name,'mesh':mesh,'translation':lp.tolist()}
    if wrot is not None:                      # world rotation matrix -> local quaternion
        R=INV[:3,:3]@wrot
        # orthonormalise (bone scale is 1 in VRoid exports but be safe)
        u,_,vt=np.linalg.svd(R); R=u@vt
        tr=np.trace(R)
        if tr>0: s=math.sqrt(tr+1)*2; q=[(R[2,1]-R[1,2])/s,(R[0,2]-R[2,0])/s,(R[1,0]-R[0,1])/s,0.25*s]
        else:
            i=int(np.argmax(np.diag(R))); k=[(1,2,0),(2,0,1),(0,1,2)][i]; a,b,c=k
            s=math.sqrt(1+R[a,a]-R[b,b]-R[c,c])*2; q=[0,0,0,0]; q[a]=0.25*s; q[b]=(R[b,a]+R[a,b])/s; q[c]=(R[c,a]+R[a,c])/s; q[3]=(R[c,b]-R[b,c])/s
        n['rotation']=[float(x) for x in q]
    j['nodes'].append(n); j['nodes'][node].setdefault('children',[]).append(len(j['nodes'])-1)
def add_mesh(name,pos,uv,tris,mat):
    pos=np.asarray(pos,np.float32); uv=np.asarray(uv,np.float32); tris=np.asarray(tris,np.uint32)
    nrm=np.zeros_like(pos)
    for t in tris:
        p0,p1,p2=pos[t]; nrm[t]+=np.cross(p1-p0,p2-p0)
    nrm/=np.linalg.norm(nrm,axis=1,keepdims=True)+1e-9
    ia=add_acc(tris.reshape(-1,1).astype(np.uint32),'SCALAR',5125,34963)
    prim={'attributes':{'POSITION':add_acc(pos,'VEC3'),'NORMAL':add_acc(nrm,'VEC3'),'TEXCOORD_0':add_acc(uv,'VEC2')},'indices':ia,'material':mat,'mode':4}
    j['meshes'].append({'name':name,'primitives':[prim]}); return len(j['meshes'])-1
def ribbon(path,across,width,closed=False):
    N=len(path); P=[];U=[];T=[]
    for i in range(N):
        for s in (-0.5,0.5):
            P.append(path[i]+across[i]*width[i]*s); U.append((i/(N-1), s+0.5))
    M=N if closed else N-1
    for i in range(M):
        a,b=2*i,2*((i+1)%N); T+= [(a,b,a+1),(a+1,b,b+1)]
    return np.array(P),np.array(U),T
def merge(parts):
    P=[];U=[];T=[];o=0
    for p,u,t in parts:
        P.append(p);U.append(u);T+=[(a+o,b+o,c+o) for a,b,c in t]; o+=len(p)
    return np.vstack(P),np.vstack(U),T
# ---------- skinned world-space vertex positions of a material's mesh (rest pose = node transforms)
def mesh_world_verts(substr):
    out=[]
    for ni,n in enumerate(j['nodes']):
        if 'mesh' not in n: continue
        W=world(j,ni)
        for p in j['meshes'][n['mesh']]['primitives']:
            if substr not in j['materials'][p['material']]['name']: continue
            a=j['accessors'][p['attributes']['POSITION']]; v=j['bufferViews'][a['bufferView']]
            arr=np.frombuffer(BIN[v['byteOffset']:v['byteOffset']+a['count']*12],np.float32).reshape(-1,3)
            out.append((arr@W[:3,:3].T)+W[:3,3])
    return np.vstack(out) if out else None
# ---------- 1) waist-back big white bow
def bow(scale=1.0, facing=(0,0,-1), up=(0,1,0)):
    f=np.array(facing,float); f/=np.linalg.norm(f); u=np.array(up,float); r=np.cross(u,f); r/=np.linalg.norm(r); u=np.cross(f,r)
    Wd=0.026*scale; parts=[]
    for s in (-1,1):                               # loops
        t=np.linspace(0,2*math.pi,48,endpoint=False); Lw=0.075*scale; Hh=0.030*scale
        x=s*(Lw/2)*(1-np.cos(t)); y=Hh*np.sin(t)*(0.55+0.45*(1-np.cos(t))/2)
        path=x[:,None]*r+y[:,None]*u - 0.006*scale*np.cos(t)[:,None]*f
        parts.append(ribbon(path,np.tile(f,(48,1)),np.full(48,Wd),closed=True))
        cen=path.mean(0)
        for side_off in (-0.5,0.5):
            ring=path+f*Wd*side_off*0.9; c=cen+f*Wd*side_off*0.4
            P=np.vstack([ring,c[None]]); U=np.c_[np.linspace(0,1,49),np.full(49,0.5)]
            T=[(i,(i+1)%48,48) for i in range(48)]; parts.append((P,U,T))
    for s in (-1,1):                               # long tails hanging down over the skirt
        k=16; tt=np.linspace(0,1,k); x=s*(0.006+0.030*tt)*scale; y=-(0.006+0.13*tt)*scale
        path=x[:,None]*r+y[:,None]*u + (0.010*np.sin(tt*2.5)+0.02*tt**2)[:,None]*scale*f*-1
        acr=np.tile(r*0.9+f*0.3,(k,1)); acr/=np.linalg.norm(acr,axis=1,keepdims=True)
        w=Wd*(0.9+0.5*tt)
        parts.append(ribbon(path,acr,w))
    t=np.linspace(0,2*math.pi,16,endpoint=False); knot=(0.009*scale)*(np.cos(t)[:,None]*r+np.sin(t)[:,None]*u)
    parts.append(ribbon(knot,np.tile(f,(16,1)),np.full(16,Wd*1.1),closed=True))
    return merge(parts)
def waist_bow():
    sc=float(os.environ.get('WBOW','1'))
    spine=world(j,HB['spine']['node'])[:3,3]; hips=world(j,HB['hips']['node'])[:3,3]
    wy=spine[1]+float(os.environ.get("WBOW_UP","0.06"))           # apron waistband height
    V=mesh_world_verts('CLOTH')
    sel=V[(np.abs(V[:,0])<0.04)&(np.abs(V[:,1]-wy)<0.02)]
    bz=sel[:,2].min() if len(sel) else hips[2]-0.09
    img=grad_tex((252,252,255),(222,226,236)); mat=add_mat('Kiko_WaistBow',add_tex(img))
    P,U,T=bow(sc,facing=(0,-0.25,-1)); attach('spine','Kiko_WaistBow',add_mesh('Kiko_WaistBow',P,U,T,mat),(0,wy,bz-0.012-float(os.environ.get("WBOW_OUT","0"))))
    print('waist bow at y',round(wy,3),'z',round(bz,3))
# ---------- 2) wrist cuffs (white frilled ring on each hand bone)
def cuff(side):
    hand='rightHand' if side<0 else 'leftHand'; low='rightLowerArm' if side<0 else 'leftLowerArm'
    h=world(j,HB[hand]['node'])[:3,3]; l=world(j,HB[low]['node'])[:3,3]
    ax=h-l; ax/=np.linalg.norm(ax)                      # along the forearm toward the hand
    r0=np.cross(ax,[0,0,1.0]); r0/=np.linalg.norm(r0); u0=np.cross(r0,ax)
    k=40; t=np.linspace(0,2*math.pi,k,endpoint=False)
    parts=[]
    # band: short cylinder slightly behind the wrist, flared frill at the hand end
    for (off,rad,wid) in ((-0.028,0.030,0.020),):
        ring=h+ax*off+rad*(np.cos(t)[:,None]*r0+np.sin(t)[:,None]*u0)
        parts.append(ribbon(ring,np.tile(ax,(k,1)),np.full(k,wid),closed=True))
    # frill: scalloped flared ring
    scal=1+0.18*np.abs(np.sin(t*5))
    inner=h+ax*(-0.018)+0.031*(np.cos(t)[:,None]*r0+np.sin(t)[:,None]*u0)
    outer=h+ax*(-0.006)+(0.042*scal)[:,None]*(np.cos(t)[:,None]*r0+np.sin(t)[:,None]*u0)
    P=np.vstack([inner,outer]); U=np.c_[np.r_[t/(2*math.pi),t/(2*math.pi)],np.r_[np.zeros(k),np.ones(k)]]
    T=[]
    for i in range(k):
        a,b=i,(i+1)%k; T+=[(a,b,k+a),(k+a,b,k+b)]
    parts.append((P,U,T))
    return merge(parts), h
def cuffs():
    img=grad_tex((255,255,255),(228,231,240)); mat=add_mat('Kiko_Cuff',add_tex(img))
    for s in (-1,1):
        (P,U,T),h=cuff(s)
        attach('rightHand' if s<0 else 'leftHand','Kiko_Cuff_'+('R' if s<0 else 'L'),add_mesh('Kiko_Cuff',P-h,U,T,mat),tuple(h))
waist_bow()
if os.environ.get('CUFF','1')!='0': cuffs()
while len(BIN)%4: BIN.append(0)
j['buffers'][0]['byteLength']=len(BIN)
js=json.dumps(j,separators=(',',':')).encode()
while len(js)%4: js+=b' '
open(dst,'wb').write(struct.pack('<4sII',b'glTF',2,12+8+len(js)+8+len(BIN))+struct.pack('<I4s',len(js),b'JSON')+js+struct.pack('<I4s',len(BIN),b'BIN\x00')+bytes(BIN))
print('body accessories ->',dst)
