"""把拆层 PSD 里的孤立碎块清掉，另存一份新 PSD（层名、顺序、显隐、画布都不变），给 Cubism 导入用。
不清：本来就是分开几笔的层（腮红、眉毛、眼珠/高光、嘴、阴影）。
用法：python3 -I cleanpsd.py 源.psd 新.psd"""
import sys
import numpy as np
from PIL import Image
from psd_tools import PSDImage
from psd_tools.api.layers import PixelLayer
from scipy import ndimage

KEEP = ('CheekBlush', 'Eyebrow', 'IrisPupil', 'EyeHighlight', 'Mouth', 'FaceHairShadow')
src, dst = sys.argv[1], sys.argv[2]
psd = PSDImage.open(src)
W, H = psd.size
n_changed = 0
for l in list(psd.descendants()):
    if l.is_group() or l.name.startswith(KEEP):
        continue
    im = l.topil()
    if im is None:
        continue
    a0 = np.array(im.convert('RGBA'))
    a = a0[..., 3].copy()
    a[a < 12] = 0
    lab, n = ndimage.label(a > 0, structure=np.ones((3, 3)))
    if n > 1:
        sizes = ndimage.sum(np.ones_like(a), lab, range(1, n + 1))
        big = sizes.max()
        drop = [i + 1 for i, s in enumerate(sizes) if s < max(400, 0.02 * big) and s < big]
        a[np.isin(lab, drop)] = 0
    if (a != a0[..., 3]).any():
        a0[..., 3] = a
        new = PixelLayer.frompil(Image.fromarray(a0), psd, l.name, l.top, l.left)
        new.visible = l.visible
        parent = l.parent
        i = list(parent).index(l)
        parent[i] = new
        n_changed += 1
psd.save(dst)
print('改了', n_changed, '层 →', dst)
chk = PSDImage.open(dst)
print('检查：层数', len([x for x in chk.descendants() if not x.is_group()]), '画布', chk.size,
      '名字顺序一致', [x.name for x in chk.descendants() if not x.is_group()] == [x.name for x in PSDImage.open(src).descendants() if not x.is_group()],
      '显隐一致', [x.visible for x in chk.descendants() if not x.is_group()] == [x.visible for x in PSDImage.open(src).descendants() if not x.is_group()])
