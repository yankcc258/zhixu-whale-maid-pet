"""After V-Chibi: scale the Face mesh morph-target deltas by the head enlargement so blink/expressions still close fully.
usage: fix_chibi_morphs.py chibi.vrm original.vrm out.vrm"""
import json,struct,sys,numpy as np
src,ref,dst=sys.argv[1:4]
def load(p):
    d=open(p,'rb').read(); L=struct.unpack('<I',d[12:16])[0]; j=json.loads(d[20:20+L]); b0=20+L; BL=struct.unpack('<I',d[b0:b0+4])[0]
    return j,bytearray(d[b0+8:b0+8+BL])
j,BIN=load(src); jr,_=load(ref)
def face_h(jj):
    m=[m for m in jj['meshes'] if m['name'].startswith('Face')][0]; a=jj['accessors'][m['primitives'][0]['attributes']['POSITION']]; return a['max'][1]-a['min'][1], a['max'][0]-a['min'][0]
(h1,w1),(h0,w0)=face_h(j),face_h(jr); sy,sx=h1/h0,w1/w0; print('face scale x %.3f y %.3f'%(sx,sy))
S=np.array([sx,sy,(sx+sy)/2],np.float32)
done=set()
for m in j['meshes']:
    if not m['name'].startswith('Face'): continue
    for p in m['primitives']:
        for t in p.get('targets',[]):
            ai=t.get('POSITION')
            if ai is None or ai in done: continue
            done.add(ai); a=j['accessors'][ai]; bv=j['bufferViews'][a['bufferView']]
            off=bv.get('byteOffset',0)+a.get('byteOffset',0); n=a['count']*3
            arr=np.frombuffer(bytes(BIN[off:off+n*4]),np.float32).reshape(-1,3)*S
            BIN[off:off+n*4]=arr.astype(np.float32).tobytes(); a['min']=arr.min(0).tolist(); a['max']=arr.max(0).tolist()
print('scaled targets',len(done))
js=json.dumps(j,separators=(',',':')).encode()
while len(js)%4: js+=b' '
open(dst,'wb').write(struct.pack('<4sII',b'glTF',2,12+8+len(js)+8+len(BIN))+struct.pack('<I4s',len(js),b'JSON')+js+struct.pack('<I4s',len(BIN),b'BIN\x00')+bytes(BIN))
