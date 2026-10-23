"""清理拆层碎片：每层只保留大块（去掉小于主块 2%、且少于 400 像素的孤立碎片），去掉 alpha<12 的灰尘。
输入 seeko_manifest.py 导出的 PNG 目录（原地写回到新目录）。用法：python3 -I cleanlayers.py 源目录 新目录"""
import sys, os, json, shutil
import numpy as np
from PIL import Image
from scipy import ndimage

src, dst = sys.argv[1], sys.argv[2]
os.makedirs(dst, exist_ok=True)
man = json.load(open(os.path.join(src, 'manifest.json')))
report = []
KEEP = ('blush', 'eyebrow', 'irides', 'mouth', 'tongue', 'face detail')  # 本来就是几笔分开的，不清
for l in man['layers']:
    if l['name'].startswith(KEEP):
        shutil.copy(os.path.join(src, l['path']), os.path.join(dst, l['path']))
        continue
    im = np.array(Image.open(os.path.join(src, l['path'])).convert('RGBA'))
    a = im[..., 3]
    a[a < 12] = 0
    lab, n = ndimage.label(a > 0, structure=np.ones((3, 3)))
    if n > 1:
        sizes = ndimage.sum(np.ones_like(a), lab, range(1, n + 1))
        big = sizes.max()
        drop = [i + 1 for i, s in enumerate(sizes) if s < max(400, 0.02 * big) and s < big]
        removed = int(sum(sizes[i - 1] for i in drop))
        if drop:
            a[np.isin(lab, drop)] = 0
            report.append((l['name'], len(drop), removed))
    im[..., 3] = a
    Image.fromarray(im).save(os.path.join(dst, l['path']))
json.dump(man, open(os.path.join(dst, 'manifest.json'), 'w'), ensure_ascii=False, indent=1)
for r in sorted(report, key=lambda r: -r[2]):
    print(f'{r[0]:24s} 去掉 {r[1]:3d} 块碎片，{r[2]} 像素')
