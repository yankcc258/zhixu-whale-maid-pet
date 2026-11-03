"""Shrink a VRM for shipping inside the desktop pet: textures > MAX px are downscaled,
thumbnail to 256, PNGs re-encoded with optimize. Geometry untouched.
usage: python3 pack_vrm.py in.vrm out.vrm [MAX=1024]"""
import json, struct, sys, io
from PIL import Image
src, dst = sys.argv[1], sys.argv[2]; MAX=int(sys.argv[3]) if len(sys.argv)>3 else 1024
d=open(src,'rb').read(); L=struct.unpack('<I',d[12:16])[0]; j=json.loads(d[20:20+L])
b0=20+L; BL=struct.unpack('<I',d[b0:b0+4])[0]; BIN=d[b0+8:b0+8+BL]
views=j['bufferViews']; chunks=[]      # rebuild BIN: copy every view, replacing image views
newBIN=bytearray()
imgview={im['bufferView']:i for i,im in enumerate(j['images'])}
for vi,v in enumerate(views):
    data=BIN[v['byteOffset']:v['byteOffset']+v['byteLength']]
    if vi in imgview:
        im=Image.open(io.BytesIO(data)); name=j['images'][imgview[vi]].get('name','')
        lim=256 if name=='Thumbnail' else MAX
        if max(im.size)>lim:
            s=lim/max(im.size); im=im.resize((max(1,round(im.size[0]*s)),max(1,round(im.size[1]*s))),Image.LANCZOS)
        buf=io.BytesIO(); im.save(buf,'PNG',optimize=True); data=buf.getvalue(); j['images'][imgview[vi]]['mimeType']='image/png'
    while len(newBIN)%4: newBIN.append(0)
    v['byteOffset']=len(newBIN); v['byteLength']=len(data); newBIN.extend(data)
while len(newBIN)%4: newBIN.append(0)
j['buffers'][0]['byteLength']=len(newBIN)
js=json.dumps(j,separators=(',',':')).encode()
while len(js)%4: js+=b' '
open(dst,'wb').write(struct.pack('<4sII',b'glTF',2,12+8+len(js)+8+len(newBIN))+struct.pack('<I4s',len(js),b'JSON')+js+struct.pack('<I4s',len(newBIN),b'BIN\x00')+bytes(newBIN))
print('packed',dst,len(d)//1024,'KB ->',(28+len(js)+len(newBIN))//1024,'KB')
