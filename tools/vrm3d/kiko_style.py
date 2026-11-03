"""Kiko (white fox) finishing pass on materials + tail pose.
usage: python3 kiko_style.py in.vrm out.vrm
env: TAIL_SIDE (deg per tail bone sideways, default 14), TAIL_UP (deg per bone upward, default 8),
     HAIR_OUT (hair outline color hex, default 97A6C4), HAIR_OW (outline width, default 0.0003)"""
import json, struct, sys, os, math
import numpy as np
src, dst = sys.argv[1], sys.argv[2]
d=open(src,'rb').read(); L=struct.unpack('<I',d[12:16])[0]; j=json.loads(d[20:20+L])
b0=20+L; BL=struct.unpack('<I',d[b0:b0+4])[0]; BIN=d[b0+8:b0+8+BL]
hexc=lambda h:[int(h[i:i+2],16)/255 for i in (0,2,4)]
# ---- 1) hair/ear/tail materials: soft light outlines, no matcap highlight band, gentle rim
oc=hexc(os.environ.get('HAIR_OUT','97A6C4')); ow=float(os.environ.get('HAIR_OW','0.0003'))
for m in j['materials']:
    n=m['name']; mt=m['extensions']['VRMC_materials_mtoon']
    if any(k in n for k in ('Hair','CatEar','FoxTail','Seeko_Ahoge')):
        mt['outlineWidthMode']='worldCoordinates'; mt['outlineWidthFactor']=ow if 'HairBack' not in n else ow*0.6
        mt['outlineColorFactor']=oc; mt['outlineLightingMixFactor']=0.6
        mt.pop('matcapTexture',None); mt['matcapFactor']=[0,0,0]
        mt['parametricRimColorFactor']=[0.18,0.2,0.26]; mt['parametricRimFresnelPowerFactor']=6; mt['parametricRimLiftFactor']=0
        mt['shadeColorFactor']=[0.80,0.83,0.90]; mt['shadingToonyFactor']=0.92; mt['shadingShiftFactor']=-0.12
# ---- 2) tail pose: curve sideways + lift the tip (rest rotations; spring bones keep this as rest)
def qmul(a,b):
    x1,y1,z1,w1=a; x2,y2,z2,w2=b
    return [w1*x2+x1*w2+y1*z2-z1*y2, w1*y2-x1*z2+y1*w2+z1*x2, w1*z2+x1*y2-y1*x2+z1*w2, w1*w2-x1*x2-y1*y2-z1*z2]
def qaxis(ax,deg):
    s=math.sin(math.radians(deg)/2); return [ax[0]*s,ax[1]*s,ax[2]*s,math.cos(math.radians(deg)/2)]
side=float(os.environ.get('TAIL_SIDE','14')); up=float(os.environ.get('TAIL_UP','8'))
names=['J_Opt_C_FoxTail2_01','J_Opt_C_FoxTail3_01','J_Opt_C_FoxTail4_01','J_Opt_C_FoxTail5_01']
w=[1.0,1.0,0.8,0.6]
for nm,k in zip(names,w):
    for i,n in enumerate(j['nodes']):
        if n['name']==nm:
            q=n.get('rotation',[0,0,0,1])
            q=qmul(q,qaxis([0,1,0],side*k)); q=qmul(q,qaxis([1,0,0],-up*k))
            n['rotation']=q
while len(BIN)%4: BIN+=b'\0'
js=json.dumps(j,separators=(',',':')).encode()
while len(js)%4: js+=b' '
open(dst,'wb').write(struct.pack('<4sII',b'glTF',2,12+8+len(js)+8+len(BIN))+struct.pack('<I4s',len(js),b'JSON')+js+struct.pack('<I4s',len(BIN),b'BIN\x00')+BIN)
print('style ->',dst)
