"""Paint over-knee socks (过膝袜) onto the VRoid body texture by rasterizing the body mesh in UV space
with interpolated rest-pose height per pixel.
usage: python3 paint_socks.py model.vrm body_tex_in.png body_tex_out.png [--top 0.50] [--band 0.022] [--lace 1]
Height bands (metres, rest pose):
  > HIPS_TOP (0.70)        : untouched (torso; the safety-short part under the skirt stays as painted)
  top .. HIPS_TOP          : bare thigh (skin)          -> the 绝对领域
  top-band .. top          : opaque elastic band (+ thin white lace scallop on its upper edge)
  < top-band               : sheer sock, alpha marker 0.7 (the vrm.js tights shader shows skin through where alpha<0.85)
"""
import json, struct, argparse, math
import numpy as np
from PIL import Image

ap = argparse.ArgumentParser(); ap.add_argument('vrm'); ap.add_argument('src'); ap.add_argument('dst')
ap.add_argument('--top', type=float, default=0.50); ap.add_argument('--band', type=float, default=0.022)
ap.add_argument('--lace', type=int, default=1); ap.add_argument('--hips-top', type=float, default=0.70)
a = ap.parse_args()

d = open(a.vrm, 'rb').read(); L = struct.unpack('<I', d[12:16])[0]; j = json.loads(d[20:20 + L])
b0 = 20 + L; BL = struct.unpack('<I', d[b0:b0 + 4])[0]; BIN = d[b0 + 8:b0 + 8 + BL]
def acc(i):
    A = j['accessors'][i]; v = j['bufferViews'][A['bufferView']]; off = v['byteOffset'] + A.get('byteOffset', 0)
    n = {'VEC2': 2, 'VEC3': 3, 'SCALAR': 1}[A['type']]; dt = {5126: np.float32, 5123: np.uint16, 5125: np.uint32}[A['componentType']]
    return np.frombuffer(BIN[off:off + A['count'] * n * np.dtype(dt).itemsize], dt).reshape(A['count'], n)

img = Image.open(a.src).convert('RGBA'); W, H = img.size
px = np.array(img).astype(np.float32)
# skin colour: median of the arm skin region (upper-left column of the VRoid body atlas)
skin = np.median(px[300:900, 60:440, :3].reshape(-1, 3), axis=0)
print('skin colour', skin.round())
height = np.full((H, W), np.nan, np.float32)   # interpolated rest height per texel
around = np.full((H, W), np.nan, np.float32)   # angle around the leg (for the lace scallops)

mi = [i for i, m in enumerate(j['materials']) if 'Body_00_SKIN' in m['name']][0]
for mesh in j['meshes']:
    for p in mesh['primitives']:
        if p['material'] != mi: continue
        uv = acc(p['attributes']['TEXCOORD_0']).astype(np.float64); pos = acc(p['attributes']['POSITION']).astype(np.float64)
        tri = acc(p['indices']).reshape(-1, 3)
        for t in tri:
            if pos[t, 1].max() > a.hips_top + 0.03: continue        # only legs
            P = uv[t] * [W, H]
            x0, y0 = np.floor(P.min(0)).astype(int); x1, y1 = np.ceil(P.max(0)).astype(int)
            x0 = max(x0, 0); y0 = max(y0, 0); x1 = min(x1, W - 1); y1 = min(y1, H - 1)
            if x1 < x0 or y1 < y0: continue
            gx, gy = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
            (ax, ay), (bx, by), (cx, cy) = P
            den = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
            if abs(den) < 1e-12: continue
            w1 = ((by - cy) * (gx - cx) + (cx - bx) * (gy - cy)) / den
            w2 = ((cy - ay) * (gx - cx) + (ax - cx) * (gy - cy)) / den
            w3 = 1 - w1 - w2
            inside = (w1 >= -0.02) & (w2 >= -0.02) & (w3 >= -0.02)
            h = w1 * pos[t[0], 1] + w2 * pos[t[1], 1] + w3 * pos[t[2], 1]
            # angle around the leg axis (x offset of each leg ~ ±0.08)
            lx = w1 * pos[t[0], 0] + w2 * pos[t[1], 0] + w3 * pos[t[2], 0]
            lz = w1 * pos[t[0], 2] + w2 * pos[t[1], 2] + w3 * pos[t[2], 2]
            ang = np.arctan2(lz, lx - np.sign(lx) * 0.08)
            sub_h = height[y0:y1 + 1, x0:x1 + 1]; sub_a = around[y0:y1 + 1, x0:x1 + 1]
            sub_h[inside] = h[inside]; sub_a[inside] = ang[inside]

legs = ~np.isnan(height)
print('leg texels', int(legs.sum()))
top = a.top; band = a.band
lace_h = 0.010 * (0.55 + 0.45 * np.abs(np.sin(np.nan_to_num(around) * 14)))   # scalloped lace height
out = px.copy()
H_ = np.nan_to_num(height, nan=9)
thigh = legs & (H_ > top + (lace_h if a.lace else 0)) & (H_ <= a.hips_top)
lace = legs & (H_ > top) & (H_ <= top + lace_h) if a.lace else np.zeros_like(legs)
bandm = legs & (H_ > top - band) & (H_ <= top)
sock = legs & (H_ <= top - band)
# thigh: skin with a soft warm shade toward the inner/back side
out[thigh, :3] = skin; out[thigh, 3] = 255
# lace: off-white with tiny eyelets
eye = (np.abs(np.sin(np.nan_to_num(around) * 42)) > 0.86)
out[lace & ~eye, :3] = [246, 246, 250]; out[lace & ~eye, 3] = 255
out[lace & eye, :3] = skin; out[lace & eye, 3] = 255
# elastic band: opaque, slightly darker, faint ribbing
rib = 3 * np.sin(np.nan_to_num(around) * 60)
out[bandm, 0] = 16 + rib[bandm]; out[bandm, 1] = 15 + rib[bandm]; out[bandm, 2] = 21 + rib[bandm]; out[bandm, 3] = 255
# sheer sock: charcoal + shin sheen, alpha marker 0.7
t = np.clip((top - H_) / (top - 0.05), 0, 1)
front = np.cos(np.nan_to_num(around) - (-math.pi / 2))         # +1 at the front of the leg (−z faces front in VRM rest? sign checked visually)
sheen = np.clip(front, 0, 1) ** 3 * 12 * np.clip(t * 1.4, 0, 1)
for c, base in enumerate((24, 22, 31)):
    out[sock, c] = base + 5 * np.sin(np.pi * t[sock]) + sheen[sock] * (1.1 if c == 2 else 1.0)
out[sock, 3] = 178
Image.fromarray(np.clip(out, 0, 255).astype(np.uint8)).save(a.dst)
print('thigh', int(thigh.sum()), 'lace', int(np.sum(lace)), 'band', int(bandm.sum()), 'sock', int(sock.sum()))
