"""Expose every Face morph target as a VRM custom expression 'm_<targetName>' so renderers/pets can mix them.
usage: add_expressions.py in.vrm out.vrm"""
import json,struct,sys
src,dst=sys.argv[1:3]
d=open(src,'rb').read(); L=struct.unpack('<I',d[12:16])[0]; j=json.loads(d[20:20+L]); b0=20+L; BL=struct.unpack('<I',d[b0:b0+4])[0]; BIN=d[b0+8:b0+8+BL]
mi=[i for i,m in enumerate(j['meshes']) if m['name'].startswith('Face')][0]; m=j['meshes'][mi]
node=[i for i,n in enumerate(j['nodes']) if n.get('mesh')==mi][0]
names=m.get('extras',{}).get('targetNames') or m['primitives'][0].get('extras',{}).get('targetNames')
ex=j['extensions']['VRMC_vrm']['expressions']; cus=ex.setdefault('custom',{})
for i,n in enumerate(names):
    cus['m_'+n]={'morphTargetBinds':[{'node':node,'index':i,'weight':1.0}],'isBinary':False,'overrideBlink':'none','overrideLookAt':'none','overrideMouth':'none'}
print('custom expressions',len(cus))
js=json.dumps(j,separators=(',',':')).encode()
while len(js)%4: js+=b' '
open(dst,'wb').write(struct.pack('<4sII',b'glTF',2,12+8+len(js)+8+len(BIN))+struct.pack('<I4s',len(js),b'JSON')+js+struct.pack('<I4s',len(BIN),b'BIN\x00')+BIN)
