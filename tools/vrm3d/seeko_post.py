"""VRM post-process for Seeko: wavy hair (vertex displacement) + blue gradient to light tips.
usage: python3 seeko_post.py in.vrm out.vrm [amp] [wavelen] [MatSubstr=tex.png ...]"""
import json, struct, sys, io, math
import numpy as np
from PIL import Image
src, dst = sys.argv[1], sys.argv[2]
args=[a for a in sys.argv[3:] if '=' not in a]; TEXOVR=dict(a.split('=',1) for a in sys.argv[3:] if '=' in a)  # MaterialSubstring=path.png
AMP = float(args[0]) if len(args) > 0 else 0.018
WL = float(args[1]) if len(args) > 1 else 0.09
import os; FLUFF = float(os.environ.get("FLUFF", "0.028"))
CURL = os.environ.get('CURL','sine')   # sine = old ripple; s = layered big S-curls (bundles by azimuth, amplitude grows toward tips)
d = open(src, 'rb').read()
L = struct.unpack('<I', d[12:16])[0]; j = json.loads(d[20:20+L])
b0 = 20 + L; BL = struct.unpack('<I', d[b0:b0+4])[0]; BIN = bytearray(d[b0+8:b0+8+BL])
views = [bytes(BIN[v.get('byteOffset',0):v.get('byteOffset',0)+v['byteLength']]) for v in j['bufferViews']]
def acc_arr(i):
    a = j['accessors'][i]; n = {'VEC2':2,'VEC3':3,'VEC4':4}[a['type']]
    raw = views[a['bufferView']]; off = a.get('byteOffset', 0)
    return np.frombuffer(raw, np.float32, a['count']*n, off).reshape(-1, n).copy()
def acc_set(i, arr):
    a = j['accessors'][i]; v = bytearray(views[a['bufferView']]); off = a.get('byteOffset', 0)
    b = arr.astype(np.float32).tobytes(); v[off:off+len(b)] = b; views[a['bufferView']] = bytes(v)
    a['min'] = arr.min(0).tolist(); a['max'] = arr.max(0).tolist()
# find hair primitive(s)
hair_mats = set()
for mi, m in enumerate(j['meshes']):
    for p in m['primitives']:
        mn = j['materials'][p['material']]['name']
        if '_Hair_' in mn and 'HairBack' not in mn:
            hair_mats.add(p['material'])
            pa = p['attributes']['POSITION']; pos = acc_arr(pa); uv = acc_arr(p['attributes']['TEXCOORD_0'])
            ytop = pos[:,1].max() - 0.075            # ~ below crown / ear level
            Lh = max(ytop - pos[:,1].min(), 1e-3)
            s = np.clip((ytop - pos[:,1]) / Lh, 0, 1)
            amp = AMP * np.clip((s - 0.05) / 0.35, 0, 1) ** 1.2
            cx, cz = 0.0, (pos[:,2].max() + pos[:,2].min()) / 2 - 0.02
            dx, dz = pos[:,0] - cx, pos[:,2] - cz
            r = np.sqrt(dx*dx + dz*dz) + 1e-6; rx, rz = dx/r, dz/r; tx, tz = -rz, rx
            az = np.arctan2(dx, dz)
            if CURL == 's':
                ph = pos[:,1] * 2*math.pi / WL + 1.2*np.sin(az*3.0) + az*1.0 + 0.9*np.sin(az*7.3+1.0) + 0.5*np.sin(az*13.1)   # smooth around the head (no bundle seams → no flipped faces); extra terms stagger neighbouring locks
                grow = np.clip((s - 0.15) / 0.6, 0, 1)
                radial = amp * (0.5 + 1.2*grow) * np.sin(ph) + FLUFF * s**1.3
                tang = amp * 0.5 * np.cos(ph)
            else:
                ph = pos[:,1] * 2*math.pi / WL + az * 2.0
                radial = amp * np.sin(ph) + FLUFF * s**1.3          # wave + slight fluff outward
                tang = amp * 0.6 * np.cos(ph)
            pos[:,0] += rx*radial + tx*tang; pos[:,2] += rz*radial + tz*tang
            acc_set(pa, pos)
            # keep upper hair (bangs/crown) in the dark part of the gradient: clamp v by height
            ta = p['attributes']['TEXCOORD_0']
            g = 0.40 + np.clip((ytop - 0.09 - pos[:,1]) / 0.12, 0, 1) * 0.60
            uv[:,1] = np.minimum(uv[:,1], g)
            acc_set(ta, uv)
            print('hair verts', len(pos), 'ytop', round(float(ytop),3))
# gradient on hair textures (base + shade share the image)
imgs = set()
for mi in hair_mats:
    m = j['materials'][mi]
    imgs.add(j['textures'][m['pbrMetallicRoughness']['baseColorTexture']['index']]['source'])
    sh = m.get('extensions',{}).get('VRMC_materials_mtoon',{}).get('shadeMultiplyTexture')
    if sh: imgs.add(j['textures'][sh['index']]['source'])
TIP = np.array([int(os.environ.get('TIP','6BAEEE')[i:i+2],16) for i in (0,2,4)], np.float32)
for ii in imgs:
    bv = j['images'][ii]['bufferView']
    im = Image.open(io.BytesIO(views[bv])).convert('RGBA'); a = np.array(im).astype(np.float32)
    H = a.shape[0]; v = (np.arange(H) + 0.5) / H
    t = np.clip((v - 0.40) / 0.42, 0, 1); t = t*t*(3 - 2*t)
    lum = a[..., :3].mean(-1, keepdims=True); ref = lum.mean()
    tip = TIP[None, None, :] * np.clip(lum / ref, 0.7, 1.25)
    a[..., :3] = a[..., :3] * (1 - t[:, None, None]) + tip * t[:, None, None]
    buf = io.BytesIO(); Image.fromarray(a.clip(0,255).astype(np.uint8)).save(buf, 'PNG'); views[bv] = buf.getvalue()
    print('gradient img', ii)
# normal-map override: key 'N:<MaterialSubstr>' → replace the material's normalTexture image (added as a new image)
for key, path in list(TEXOVR.items()):
    if not key.startswith('N:'): continue
    sub=key[2:]; del TEXOVR[key]
    buf=io.BytesIO(); Image.open(path).convert('RGB').save(buf,'PNG')
    j['bufferViews'].append({'buffer':0,'byteOffset':0,'byteLength':0}); views.append(buf.getvalue())
    j['images'].append({'name':'normal_'+sub,'mimeType':'image/png','bufferView':len(j['bufferViews'])-1})
    j.setdefault('samplers',[]).append({'magFilter':9729,'minFilter':9987,'wrapS':10497,'wrapT':10497})
    j['textures'].append({'sampler':len(j['samplers'])-1,'source':len(j['images'])-1}); ti=len(j['textures'])-1
    for m in j['materials']:
        if sub in m['name']:
            m['normalTexture']={'index':ti,'texCoord':0,'scale':1.0}; print('normal override', m['name'], '<-', path)
# texture overrides by material-name substring
for key, path in TEXOVR.items():
    hit=False
    for m in j['materials']:
        if key in m['name']:
            t=m.get('pbrMetallicRoughness',{}).get('baseColorTexture')
            if not t: continue
            ii=j['textures'][t['index']]['source']; bv=j['images'][ii]['bufferView']
            buf=io.BytesIO(); Image.open(path).convert('RGBA').save(buf,'PNG'); views[bv]=buf.getvalue(); hit=True
            # 阴影贴图也指到同一张（VRoid 导出的 shade 贴图还是旧底色，不改会穿帮）
            mt=m.get('extensions',{}).get('VRMC_materials_mtoon',{})
            if 'shadeMultiplyTexture' in mt: mt['shadeMultiplyTexture']={'index': t['index']}
            print('override', m['name'], '<-', path)
    if not hit: print('WARN no material matches', key)
# rebuild BIN
out = bytearray(); 
for i, v in enumerate(j['bufferViews']):
    while len(out) % 4: out.append(0)
    v['byteOffset'] = len(out); v['byteLength'] = len(views[i]); out += views[i]
while len(out) % 4: out.append(0)
j['buffers'][0]['byteLength'] = len(out)
js = json.dumps(j, separators=(',', ':')).encode()
while len(js) % 4: js += b' '
glb = struct.pack('<4sII', b'glTF', 2, 12 + 8 + len(js) + 8 + len(out)) + struct.pack('<I4s', len(js), b'JSON') + js + struct.pack('<I4s', len(out), b'BIN\x00') + bytes(out)
open(dst, 'wb').write(glb); print('wrote', dst, len(glb))
