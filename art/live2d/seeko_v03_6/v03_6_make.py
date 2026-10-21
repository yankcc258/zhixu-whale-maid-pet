"""v03.6：v03.4 + 特蕾莎 v03.5 候选的混合。
- HairBack_L/R：以 v03.4 为底（保留原来看得见的发束、高光、蝴蝶结旁那缕头发）。
  手臂/手/袖口/耳鳍附近的碎片：
    * 默认画面露出来、且贴着部件（8px 内）的 → 其实是部件的描边，挪进最近的部件层（垫在部件下面），之后跟着部件动；
    * 其余（被挡住的、离部件远的）→ 换成 v03.5 的干净头发。
- 手臂、手、袖口、耳鳍：不用 v03.5 拷进去的像素（里面混了头发），只接收上面挪进来的描边。
"""
import json, shutil, hashlib
from pathlib import Path
import numpy as np
from PIL import Image
from scipy import ndimage

S = Path('/tmp/claude-0/-home-claude/5d1ddcc7-fe5e-5109-8e8f-60afaa718bac/scratchpad/')
B = Path('/home/claude/art-wt/art/live2d/')
V4, V5 = B / 'seeko_v03_4', B / 'seeko_v03_5'
OUT = S / 'l2d_v036/seeko_v03_6'
if OUT.exists():
    shutil.rmtree(OUT)
OUT.mkdir(parents=True)
m = json.load(open(V4 / 'layer_manifest_v03_4.json'))
names = [s['name'] for s in m]
W, H = 1086, 1448
rel = lambda s: s.get('png') or f"layers_png/{s['group']}/{s['name']}.png"
L4 = {s['name']: np.asarray(Image.open(V4 / rel(s)).convert('RGBA')).astype(np.float32) for s in m}
L5 = {s['name']: np.asarray(Image.open(V5 / rel(s)).convert('RGBA')).astype(np.float32) for s in m if (V5 / rel(s)).exists()}
L = {k: v.copy() for k, v in L4.items()}
log = []
lum = lambda a: a[..., 0] * .3 + a[..., 1] * .59 + a[..., 2] * .11
PARTS = ['ArmUpper_R', 'ArmLower_R', 'Hand_R', 'Cuff_R', 'ArmUpper_L', 'ArmLower_L', 'Hand_L', 'Cuff_L', 'FinEar_R', 'FinEar_L']

partmask = np.zeros((H, W), bool)
for n in PARTS:
    partmask |= L4[n][..., 3] > 30
zone = ndimage.binary_dilation(partmask, iterations=24)
dstack = np.stack([ndimage.distance_transform_edt(~(L4[p][..., 3] > 30)) for p in PARTS])
nearest, mind = np.argmin(dstack, axis=0), dstack.min(axis=0)
moved_total = {p: 0 for p in PARTS}

for n in ['HairBack_L', 'HairBack_R']:
    a4, a5 = L4[n], L5[n]
    r, g, b, al = [a4[..., k] for k in range(4)]
    hair = (b > r + 75) & (b > 140) & (al > 128)  # 耳鳍的藏青 (67,78,125) 不算头发
    dark = (lum(a4) < 70) & (al > 60)
    thick = ndimage.binary_opening(dark, structure=np.ones((6, 6)))
    thin_ol = dark & ~ndimage.binary_dilation(thick, iterations=2) & ndimage.binary_dilation(hair, iterations=4)
    keep = (hair & ~ndimage.binary_dilation(thick, iterations=3)) | thin_ol
    foreign = zone & ~keep & ((al > 0) | (a5[..., 3] > 0))
    # 耳鳍的藏青色块（离耳鳍 160px 内）也算碎片，不管在不在 zone 里
    fin = (L4['FinEar_L'][..., 3] > 30) | (L4['FinEar_R'][..., 3] > 30)
    navy = (np.abs(r - 67) < 14) & (np.abs(g - 78) < 14) & (np.abs(b - 125) < 16) & (al > 0)
    navy = ndimage.binary_dilation(navy, iterations=2) & (al > 0) & ~hair & ndimage.binary_dilation(fin, iterations=160)
    navy = navy | (ndimage.binary_dilation(navy, iterations=5) & dark & ~hair)  # 色块自己的描边
    foreign = foreign | navy
    cov = np.zeros((H, W), np.float32)
    for s2 in m[names.index(n) + 1:]:
        if s2.get('visible', True) and not s2['name'].startswith('Reserve'):
            cov = cov + L4[s2['name']][..., 3] / 255 * (1 - cov)
    move = foreign & (al > 0) & (cov < 0.6) & ((mind <= 30) | navy)
    foreign = foreign | (zone & (cov >= 0.6) & ((al > 0) | (a5[..., 3] > 0)))  # 被部件挡住的全部用干净头发
    for i, pn in enumerate(PARTS):
        mk = move & (nearest == i)
        if not mk.any():
            continue
        dst = L[pn]
        sa = a4[mk][:, 3:4] / 255
        da = dst[mk][:, 3:4] / 255
        oa = da + sa * (1 - da)
        dst[mk, :3] = np.where(oa > 0, (dst[mk][:, :3] * da + a4[mk][:, :3] * sa * (1 - da)) / np.maximum(oa, 1e-3), 0)
        dst[mk, 3] = (oa * 255)[:, 0]
        moved_total[pn] += int(mk.sum())
    out = a4.copy()
    out[foreign] = a5[foreign]
    # 换完以后，耳鳍附近剩下的孤立深色线（旁边 3px 内已经没有头发）也去掉
    o_hair = (out[..., 2] > out[..., 0] + 75) & (out[..., 2] > 140) & (out[..., 3] > 128)
    o_dark = (lum(out) < 80) & (out[..., 3] > 0)
    lone = o_dark & ~ndimage.binary_dilation(o_hair, iterations=3) & ndimage.binary_dilation(fin, iterations=160)
    lone = ndimage.binary_dilation(lone, iterations=1) & (out[..., 3] > 0) & ~o_hair
    # 默认画面看得见的那段，其实是耳鳍的上边描边：挪进最近的耳鳍层
    vis_lone = lone & (cov < 0.6)
    fins = ['FinEar_L', 'FinEar_R']
    fd = np.stack([ndimage.distance_transform_edt(~(L4[f][..., 3] > 30)) for f in fins])
    fn = np.argmin(fd, axis=0)
    vis_lone &= fd.min(axis=0) <= 6  # 只挪紧贴耳鳍的那条边线，旁边头发的描边不动
    lone &= ~(lone & (cov < 0.6) & ~vis_lone)
    for i, f in enumerate(fins):
        mk = vis_lone & (fn == i)
        if mk.any():
            dst = L[f]
            sa = out[mk][:, 3:4] / 255
            da = dst[mk][:, 3:4] / 255
            oa = da + sa * (1 - da)
            dst[mk, :3] = np.where(oa > 0, (dst[mk][:, :3] * da + out[mk][:, :3] * sa * (1 - da)) / np.maximum(oa, 1e-3), 0)
            dst[mk, 3] = (oa * 255)[:, 0]
            moved_total[f] += int(mk.sum())
    out[lone] = a5[lone]
    foreign = foreign | lone
    # 手和袖口周围（下半截）整块用 v03.5 的干净头发，避免新旧发束拼接出锯齿；边缘 6px 羽化
    lowparts = np.zeros((H, W), bool)
    for pn in ['Hand_R', 'Cuff_R', 'ArmLower_R', 'Hand_L', 'Cuff_L', 'ArmLower_L']:
        lowparts |= L4[pn][..., 3] > 30
    blk = ndimage.binary_dilation(lowparts, iterations=45)
    t = ndimage.gaussian_filter(blk.astype(np.float32), 4)[..., None]
    pa = a5[..., 3:4] * t + out[..., 3:4] * (1 - t)
    pr = a5[..., :3] * a5[..., 3:4] * t + out[..., :3] * out[..., 3:4] * (1 - t)
    out = np.dstack([np.where(pa > 0, pr / np.maximum(pa, 1e-3), 0), pa])
    L[n] = out
    log.append(f'{n}：手臂/耳鳍附近的碎片 {int(foreign.sum())} 像素换成 v03.5 的干净头发，其中默认画面露出、贴着部件的 {int(move.sum())} 像素先挪进部件层当描边；其余保持 v03.4')
for p in PARTS:
    log.append(f'{p}：接收从后发挪来的描边 {moved_total[p]} 像素（不采用 v03.5 拷进来的像素）')

changed = []
for s in m:
    n = s['name']
    if n in L5:
        p = OUT / rel(s)
        p.parent.mkdir(parents=True, exist_ok=True)
        Image.fromarray(np.clip(L[n], 0, 255).astype(np.uint8), 'RGBA').save(p)
        changed.append(dict(name=n, png=rel(s), sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
json.dump(changed, open(OUT / 'changed_layers_v03_6.json', 'w'), ensure_ascii=False, indent=1)


def comp(Ls, skip=()):
    c = Image.new('RGBA', (W, H), (255, 255, 255, 255))
    for s in m:
        if s.get('visible', True) and not s['name'].startswith('Reserve') and s['name'] not in skip:
            c.alpha_composite(Image.fromarray(np.clip(Ls[s['name']], 0, 255).astype(np.uint8)))
    return c


a, c = comp(L4), comp(L)
d = (np.abs(np.asarray(a).astype(int) - np.asarray(c).astype(int))[..., :3].max(2) > 12)
log.append(f'默认画面和 v03.4 比：{int(d.sum())} 个像素颜色差超过 12')
c.save(OUT / 'seeko_neutral_v03_6.png')
comp(L, PARTS).save(OUT / 'seeko_behind_parts_v03_6.png')
open(OUT / 'v03_6_说明.md', 'w').write('# v03.6（露娜，v03.4 + 特蕾莎 v03.5 候选混合）\n\n' + '\n'.join('- ' + x for x in log) + '\n')
print('\n'.join(log))
