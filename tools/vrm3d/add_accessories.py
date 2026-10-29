"""Seeko accessories as procedural meshes on the head bone:
white frilled maid headdress, big blue back bow, two small side bows, ahoge.
usage: python3 add_accessories.py in.vrm out.vrm"""
import json, struct, sys, io, math, copy
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
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
    buf=io.BytesIO(); img.save(buf,'PNG'); j['images'].append({'name':'seeko_acc','mimeType':'image/png','bufferView':add_view(buf.getvalue())})
    j.setdefault('samplers',[]).append({'magFilter':9729,'minFilter':9987,'wrapS':10497,'wrapT':33071})
    j['textures'].append({'sampler':len(j['samplers'])-1,'source':len(j['images'])-1}); return len(j['textures'])-1
BASE=next(m for m in j['materials'] if '_Hair_' in m['name'] and 'HairBack' not in m['name'])
def add_mat(name,tex,shade=(0.8,0.82,0.9),outline=(0.1,0.1,0.15)):
    m=copy.deepcopy(BASE); m['name']=name; m['doubleSided']=True
    m['pbrMetallicRoughness']['baseColorTexture']={'index':tex,'texCoord':0}
    for k in ('normalTexture','emissiveTexture'): m.pop(k,None)
    m['emissiveFactor']=[0,0,0]; mt=m['extensions']['VRMC_materials_mtoon']
    mt['shadeMultiplyTexture']={'index':tex}; mt['shadeColorFactor']=list(shade); mt['outlineColorFactor']=list(outline)
    mt.pop('matcapTexture',None); mt['matcapFactor']=[0,0,0]
    j['materials'].append(m); return len(j['materials'])-1
def grad_tex(top,bot,size=64,frill=None):
    im=Image.new('RGBA',(size,size)); dr=ImageDraw.Draw(im)
    for y in range(size):
        t=y/(size-1); dr.line([(0,y),(size,y)],fill=tuple(int(top[k]+(bot[k]-top[k])*t) for k in range(3))+(255,))
    return im
HEAD=j['extensions']['VRMC_vrm']['humanoid']['humanBones']['head']['node']
INV=np.linalg.inv(world(j,HEAD))
def attach(name,mesh,wpos=(0,0,0)):
    lp=(INV@np.r_[wpos,1.0])[:3]
    j['nodes'].append({'name':name,'mesh':mesh,'translation':lp.tolist()}); j['nodes'][HEAD].setdefault('children',[]).append(len(j['nodes'])-1)
def add_mesh(name,pos,uv,tris,mat):
    pos=np.asarray(pos,np.float32); uv=np.asarray(uv,np.float32); tris=np.asarray(tris,np.uint32)
    nrm=np.zeros_like(pos)
    for t in tris:
        p0,p1,p2=pos[t]; nrm[t]+=np.cross(p1-p0,p2-p0)
    nrm/=np.linalg.norm(nrm,axis=1,keepdims=True)+1e-9
    ia=add_acc(tris.reshape(-1,1).astype(np.uint32),'SCALAR',5125,34963)
    prim={'attributes':{'POSITION':add_acc(pos,'VEC3'),'NORMAL':add_acc(nrm,'VEC3'),'TEXCOORD_0':add_acc(uv,'VEC2')},'indices':ia,'material':mat,'mode':4}
    j['meshes'].append({'name':name,'primitives':[prim]}); return len(j['meshes'])-1
def ribbon(path,across,width,closed=False,v0=0.0):
    """path: (N,3) centerline; across: (N,3) unit vectors; width: (N,) -> verts, uvs, tris"""
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
# ---------------- geometry anchors (world, metres)
hb=j['extensions']['VRMC_vrm']['humanoid']['humanBones']
eyeY=world(j,hb['leftEye']['node'])[1,3] if 'leftEye' in hb else 1.23
hair=[m for m in j['meshes'] if m['name'].startswith('Hair')][0]
ha=j['accessors'][hair['primitives'][0]['attributes']['POSITION']]
TOP=ha['max'][1]; BACKZ=ha['min'][2]; HX=ha['max'][0]
_bv=j['bufferViews'][ha['bufferView']]
HP=np.frombuffer(bytes(BIN[_bv.get('byteOffset',0)+ha.get('byteOffset',0):]),np.float32,ha['count']*3).reshape(-1,3)
def surf_r(cx,cy,z0,theta,tol=0.015):
    sel=np.abs(HP[:,2]-z0)<tol; P=HP[sel]; dx=P[:,0]-cx; dy=P[:,1]-cy
    a=np.arctan2(dy,dx); m=np.abs((a-theta+np.pi)%(2*np.pi)-np.pi)<math.radians(4)
    return float(np.sqrt(dx[m]**2+dy[m]**2).max()) if m.any() else None
def surf_back(x,y,tol=0.02):
    m=(np.abs(HP[:,0]-x)<tol)&(np.abs(HP[:,1]-y)<tol)&(HP[:,2]<0); return float(HP[m,2].min())
def surf_side(y,z,s,tol=0.02):
    m=(np.abs(HP[:,1]-y)<tol)&(np.abs(HP[:,2]-z)<tol)&(HP[:,0]*s>0); return float(np.abs(HP[m,0]).max())

def ear_base(side):
    """outer-lower base of the VRoid animal-ear accessory on this side (world coords), or None"""
    for m in j['meshes']:
        for p in m['primitives']:
            if 'Ear' not in j['materials'][p['material']]['name']: continue
            a=j['accessors'][p['attributes']['POSITION']]; bv=j['bufferViews'][a['bufferView']]
            V=np.frombuffer(bytes(BIN[bv.get('byteOffset',0)+a.get('byteOffset',0):]),np.float32,a['count']*3).reshape(-1,3)
            ia=j['accessors'][p['indices']]; ib=j['bufferViews'][ia['bufferView']]
            dt={5123:np.uint16,5125:np.uint32}[ia['componentType']]
            I=np.unique(np.frombuffer(bytes(BIN[ib.get('byteOffset',0)+ia.get('byteOffset',0):]),dt,ia['count']))
            E=V[I]; E=E[E[:,0]*side>0.01]
            if len(E)<10: continue
            lo=E[E[:,1]<np.percentile(E[:,1],25)]
            o=lo[np.argmax(lo[:,0]*side)]
            return np.array([o[0]+side*0.004, o[1]+0.004, o[2]+0.012])
    return None
# ---- 1) maid headdress: band arc over the head + pleated frill
def headdress():
    cy=eyeY+0.01; z0=-0.012
    n=72; ang=np.linspace(math.radians(18),math.radians(162),n)
    rr=np.array([ (surf_r(0,cy,z0,a) or 0.1) for a in ang ]); rr=np.convolve(np.pad(rr,3,mode='edge'),np.ones(7)/7,'valid')+0.003
    dirs=np.c_[np.cos(ang),np.sin(ang),np.zeros(n)]
    band=np.c_[rr*np.cos(ang), cy+rr*np.sin(ang), np.full(n,z0)]
    zax=np.tile([0,0,1.0],(n,1))
    p1=ribbon(band,zax,np.full(n,0.020))
    # frill: soft ruffle standing out from the band, ~22 pleats, leaning slightly back
    m=n*3; a2=np.linspace(ang[0],ang[-1],m); r2=np.interp(a2,ang,rr)
    ow=np.c_[np.cos(a2),np.sin(a2),np.full(m,-0.35)]; ow/=np.linalg.norm(ow,axis=1,keepdims=True)
    pleat=0.0045*np.sin(a2*44)
    mid=np.c_[r2*np.cos(a2), cy+r2*np.sin(a2), np.full(m,z0)]+ow*0.011+np.c_[np.zeros(m),np.zeros(m),pleat]
    p2=ribbon(mid,ow,np.full(m,0.020))
    P,U,T=merge([p1,p2])
    img=Image.new('RGBA',(64,64),(250,250,252,255)); dr=ImageDraw.Draw(img)
    for x in range(0,64,8): dr.arc([x-4,40,x+12,60],0,180,fill=(205,210,225,255),width=2)   # lace scallops
    dr.line([(0,2),(64,2)],fill=(215,220,235,255),width=2)
    mat=add_mat('Seeko_Headdress',add_tex(img),shade=(0.82,0.84,0.92),outline=(0.35,0.37,0.45))
    attach('Seeko_Headdress',add_mesh('Seeko_Headdress',P,U,T,mat))
# ---- 2) bows
def bow(scale=1.0, facing=(0,0,-1), up=(0,1,0)):
    f=np.array(facing,float); f/=np.linalg.norm(f); u=np.array(up,float); r=np.cross(u,f); r/=np.linalg.norm(r); u=np.cross(f,r)
    Wd=0.020*scale; parts=[]
    for s in (-1,1):                               # loops
        t=np.linspace(0,2*math.pi,48,endpoint=False); Lw=0.045*scale; Hh=0.020*scale
        x=s*(Lw/2)*(1-np.cos(t)); y=Hh*np.sin(t)*(0.55+0.45*(1-np.cos(t))/2)
        path=x[:,None]*r+y[:,None]*u - 0.004*scale*np.cos(t)[:,None]*f
        parts.append(ribbon(path,np.tile(f,(48,1)),np.full(48,Wd),closed=True))
        cen=path.mean(0)
        for side_off in (-0.5,0.5):                 # fill loop faces so the bow looks solid
            ring=path+f*Wd*side_off*0.9; c=cen+f*Wd*side_off*0.4
            P=np.vstack([ring,c[None]]); U=np.c_[np.linspace(0,1,49),np.full(49,0.5)]
            T=[(i,(i+1)%48,48) for i in range(48)]; parts.append((P,U,T))
    for s in (-1,1):                               # tails
        k=12; tt=np.linspace(0,1,k); x=s*(0.004+0.018*tt)*scale; y=-(0.004+0.05*tt)*scale
        path=x[:,None]*r+y[:,None]*u + 0.004*scale*np.sin(tt*3)[:,None]*f
        acr=np.tile(f,(k,1))*0+r*np.cos(0.5)[None]+u*0.0; acr=np.tile(r*0.35+f*0.94,(k,1))
        parts.append(ribbon(path,acr,np.full(k,Wd*0.9)))
    t=np.linspace(0,2*math.pi,16,endpoint=False); knot=(0.007*scale)*(np.cos(t)[:,None]*r+np.sin(t)[:,None]*u)  # knot ring
    parts.append(ribbon(knot,np.tile(f,(16,1)),np.full(16,Wd*1.1),closed=True))
    return merge(parts)
def bows():
    img=grad_tex((110,185,250),(45,120,215)); mat=add_mat('Seeko_Bow',add_tex(img),shade=(0.7,0.8,0.95),outline=(0.05,0.12,0.3))
    P,U,T=bow(1.8,facing=(0,0,-1)); by=eyeY+0.025; attach('Seeko_BackBow',add_mesh('Seeko_BackBow',P,U,T,mat),(0,by,surf_back(0,by)-0.006))
    for s in (1,-1):
        ear=ear_base(s)
        if ear is not None:
            P,U,T=bow(0.6,facing=(s*0.5,0.0,0.85)); attach('Seeko_SideBow_'+('L' if s>0 else 'R'),add_mesh('Seeko_SideBow',P,U,T,mat),tuple(ear))
        else:
            ang=math.radians(22 if s>0 else 158); cy=eyeY+0.01; r=(surf_r(0,cy,-0.012,ang) or 0.1)+0.008; P,U,T=bow(0.6,facing=(s*0.45,0.0,0.9)); attach('Seeko_SideBow_'+('L' if s>0 else 'R'),add_mesh('Seeko_SideBow',P,U,T,mat),(r*math.cos(ang),cy+r*math.sin(ang),0.004))
# ---- 3) ahoge (crescent curl, faces front)
def ahoge():
    k=40; t=np.linspace(0,1,k)
    # cubic bezier in x-y (front view), slight z drift
    P0=np.array([0.004,TOP-0.006,-0.02]); P1=np.array([0.004,TOP+0.07,-0.015]); P2=np.array([-0.05,TOP+0.075,-0.01]); P3=np.array([-0.045,TOP+0.035,-0.005])
    path=((1-t)**3)[:,None]*P0+(3*(1-t)**2*t)[:,None]*P1+(3*(1-t)*t**2)[:,None]*P2+(t**3)[:,None]*P3
    tan=np.gradient(path,axis=0); tan/=np.linalg.norm(tan,axis=1,keepdims=True)
    acr=np.cross(tan,np.array([0,0,1.0])); acr/=np.linalg.norm(acr,axis=1,keepdims=True)
    w=0.016*(1-t)**0.8+0.001
    P,U,T=ribbon(path,acr,w)
    U=np.c_[U[:,1]*0.3+0.35, 0.05+U[:,0]*0.3]          # sample dark root part of hair-like gradient
    img=grad_tex((40,56,140),(52,74,160)); mat=add_mat('Seeko_Ahoge',add_tex(img),shade=(0.75,0.78,0.9),outline=(0.06,0.04,0.12))
    attach('Seeko_Ahoge',add_mesh('Seeko_Ahoge',P,U,T,mat))
headdress(); bows(); ahoge()
while len(BIN)%4: BIN.append(0)
j['buffers'][0]['byteLength']=len(BIN)
js=json.dumps(j,separators=(',',':')).encode()
while len(js)%4: js+=b' '
open(dst,'wb').write(struct.pack('<4sII',b'glTF',2,12+8+len(js)+8+len(BIN))+struct.pack('<I4s',len(js),b'JSON')+js+struct.pack('<I4s',len(BIN),b'BIN\x00')+bytes(BIN))
print('accessories ->',dst,'TOP',round(TOP,3),'BACKZ',round(BACKZ,3),'HX',round(HX,3))
