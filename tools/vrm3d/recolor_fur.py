"""Recolor Kiko's 'fur' textures (hair, hair-back, fox ears, fox tail, ahoge, brows) to a new palette.
usage: recolor_fur.py in.vrm out.vrm DARKHEX LIGHTHEX   (dark = roots, light = tips)"""
import json, struct, sys, io, colorsys
import numpy as np
from PIL import Image
src, dst, dark, light = sys.argv[1:5]
dark = np.array([int(dark[i:i+2],16) for i in (0,2,4)], np.float32); light = np.array([int(light[i:i+2],16) for i in (0,2,4)], np.float32)
d=open(src,'rb').read(); L=struct.unpack('<I',d[12:16])[0]; j=json.loads(d[20:20+L])
b0=20+L; BL=struct.unpack('<I',d[b0:b0+4])[0]; BIN=bytearray(d[b0+8:b0+8+BL])
views=[bytes(BIN[v.get('byteOffset',0):v.get('byteOffset',0)+v['byteLength']]) for v in j['bufferViews']]
KEYS=['_Hair_','HairBack','CatEar','FoxTail','Ahoge','FaceBrow']
imgs=set()
for m in j['materials']:
    if not any(k in m['name'] for k in KEYS): continue
    t=m.get('pbrMetallicRoughness',{}).get('baseColorTexture')
    if t: imgs.add(j['textures'][t['index']]['source'])
    sh=m.get('extensions',{}).get('VRMC_materials_mtoon',{}).get('shadeMultiplyTexture')
    if sh: imgs.add(j['textures'][sh['index']]['source'])
for ii in sorted(imgs):
    bv=j['images'][ii]['bufferView']
    a=np.array(Image.open(io.BytesIO(views[bv])).convert('RGBA')).astype(np.float32)
    rgb=a[...,:3]/255; mx=rgb.max(-1); mn=rgb.min(-1); s=np.where(mx>0,(mx-mn)/np.maximum(mx,1e-6),0)
    col=(s>0.18)&(a[...,3]>8)          # the colored (blue) fur pixels; white inner fur / highlights stay
    if col.sum()<50: continue
    lum=(0.3*rgb[...,0]+0.59*rgb[...,1]+0.11*rgb[...,2])
    lo,hi=np.percentile(lum[col],2),np.percentile(lum[col],98)
    t=np.clip((lum-lo)/max(hi-lo,1e-3),0,1)
    new=dark[None,None,:]*(1-t[...,None])+light[None,None,:]*t[...,None]
    w=np.clip((s-0.18)/0.12,0,1)[...,None]*(a[...,3:4]>8)
    a[...,:3]=a[...,:3]*(1-w)+new*w
    buf=io.BytesIO(); Image.fromarray(a.clip(0,255).astype(np.uint8)).save(buf,'PNG'); views[bv]=buf.getvalue()
    print('recolored image',ii,j['images'][ii].get('name'))
out=bytearray()
for i,v in enumerate(j['bufferViews']):
    while len(out)%4: out.append(0)
    v['byteOffset']=len(out); v['byteLength']=len(views[i]); out+=views[i]
while len(out)%4: out.append(0)
j['buffers'][0]['byteLength']=len(out)
js=json.dumps(j,separators=(',',':')).encode()
while len(js)%4: js+=b' '
open(dst,'wb').write(struct.pack('<4sII',b'glTF',2,12+8+len(js)+8+len(out))+struct.pack('<I4s',len(js),b'JSON')+js+struct.pack('<I4s',len(out),b'BIN\x00')+bytes(out))
print('wrote',dst)
