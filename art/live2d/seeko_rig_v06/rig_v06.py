"""v06 骨架加强：直接改 cmo3 里的关键形态坐标（中立形态不动）。
- 头部曲面（像素坐标）：转头整体平移 ±40px + 透视压缩；抬头低头 ±15px + 上下透视
- 脸部曲面（头部曲面里的 0~1 坐标）：圆柱投影，五官再多走 ±25px，远侧压缩近侧拉开；下巴那几行动得少，脖子不脱节
- 眼珠 Gaze_L/R：位移放大（X 2.5 倍，Y 1.8 倍）
- 身体：BodyAngleX、BodyAngleZ 位移 ×2
"""
import sys, math, re
import numpy as np
sys.path.insert(0, '/tmp/claude-0/-home-claude/5d1ddcc7-fe5e-5109-8e8f-60afaa718bac/scratchpad/caff')
from model import params, deformers, grid, forms
from caff import read_xml, write_xml

SRC, DST = sys.argv[1], sys.argv[2]
d = open(SRC, 'rb').read()
x, _ = read_xml(d)
s = x.decode('utf-8')
P = params(s)
edits = []  # (start, end, newtext)
log = []


def fmt(a):
    return ' '.join(f'{v:.7g}' for v in a.reshape(-1))


def keyforms(name):
    D = deformers(s)
    dd = D[name]
    g = grid(s, dd['grid'], P)
    F = forms(s, dd)
    return [(c, F[fg]) for c, fg in g]


def neutral(kfs):
    for c, f in kfs:
        if all(v == 0 for v in c.values()):
            return np.array(f[2]).reshape(-1, 2)
    raise RuntimeError('没有中立形态')


def apply(name, fn):
    kfs = keyforms(name)
    N = neutral(kfs)
    for c, (st, en, vals) in kfs:
        if all(v == 0 for v in c.values()):
            continue
        new = fn(N.copy(), c, np.array(vals).reshape(-1, 2))
        edits.append((st, en, fmt(new)))
        log.append(f'{name} {c}: 最大位移 {np.abs(new - N).max():.4g}（原来 {np.abs(np.array(vals).reshape(-1,2) - N).max():.4g}）')


# ---- 头部曲面（像素） ----
def head(N, c, old):
    t = c.get('ParamAngleX', 0) / 30
    v = c.get('ParamAngleY', 0) / 30
    cx, cy = N[:, 0].mean(), N[:, 1].mean()
    hw = (N[:, 0].max() - N[:, 0].min()) / 2
    hh = (N[:, 1].max() - N[:, 1].min()) / 2
    xr, yr = N[:, 0] - cx, N[:, 1] - cy
    nx = cx + xr * (1 - 0.05 * t * xr / hw) + 40 * t
    ny = cy + yr * (1 + 0.04 * v * yr / hh) - 15 * v
    return np.c_[nx, ny]


# ---- 脸部曲面（0~1） ----
def face(N, c, old):
    t = c.get('ParamAngleX', 0) / 30
    v = c.get('ParamAngleY', 0) / 30
    cx, cy = N[:, 0].mean(), N[:, 1].mean()
    hw = (N[:, 0].max() - N[:, 0].min()) / 2
    hh = (N[:, 1].max() - N[:, 1].min()) / 2
    xr = np.clip((N[:, 0] - cx) / hw, -1, 1)
    yr = np.clip((N[:, 1] - cy) / hh, -1, 1)
    k = 0.92
    nx = cx + hw * np.sin(np.arcsin(k * xr) + 0.07 * t) / k
    ny = cy + hh * np.sin(np.arcsin(k * yr) - 0.06 * v) / k
    w = 1 - 0.35 * np.clip(yr, 0, 1)  # 下巴附近少动
    return np.c_[N[:, 0] + (nx - N[:, 0]) * w, N[:, 1] + (ny - N[:, 1]) * w]


def scaled(kx, ky):
    def f(N, c, old):
        dlt = old - N
        return N + dlt * np.array([kx, ky])
    return f


apply('头部曲面', head)
apply('脸部曲面', face)
apply('Gaze_L', scaled(2.5, 1.8))
apply('Gaze_R', scaled(2.5, 1.8))
apply('上半身的曲面Y', scaled(2, 2))
apply('上半身的曲面Z', scaled(2, 2))

for st, en, t in sorted(edits, reverse=True):
    s = s[:st] + t + s[en:]
open(DST, 'wb').write(write_xml(d, s.encode('utf-8')))
print('\n'.join(log))
print('写入', DST)
