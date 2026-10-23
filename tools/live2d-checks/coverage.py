"""哪些网格盖不住 PSD 里同名图层的图（导入新图后要重铺的）。用法：python3 coverage.py 工程.cmo3 底稿.psd"""
import sys, re
import numpy as np
sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.abspath(__file__)))
from caff import read_xml
from psd_tools import PSDImage
from matplotlib.path import Path
from scipy.spatial import ConvexHull

s = read_xml(open(sys.argv[1], 'rb').read())[0].decode()
psd = PSDImage.open(sys.argv[2])
bad = []
for l in psd.descendants():
    if l.is_group():
        continue
    m = re.search(rf'<s xs.n="localName">{re.escape(l.name)}</s>', s)
    st = s.rfind('<CArtMeshSource', 0, m.start()); b = s[st:s.find('</CArtMeshSource>', st)]
    pts = np.array([float(v) for v in re.search(r'<float-array xs.n="point" count="\d+">([^<]*)<', b).group(1).split()]).reshape(-1, 2)
    im = l.topil()
    if im is None:
        continue
    a = np.array(im.convert('RGBA'))[..., 3]
    ys, xs = np.nonzero(a > 40)
    if len(xs) == 0:
        continue
    xs = xs + l.left; ys = ys + l.top
    path = Path(pts[ConvexHull(pts).vertices])
    idx = np.random.default_rng(0).choice(len(xs), min(4000, len(xs)), replace=False)
    out = 1 - path.contains_points(np.c_[xs[idx], ys[idx]], radius=2).mean()
    if out > 0.005:
        bad.append((l.name, round(out * 100, 1)))
print(sorted(bad, key=lambda x: -x[1]))
