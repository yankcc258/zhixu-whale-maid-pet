"""模板套骨架后，部分网格的关键形态还是旧底稿的形状（:3 嘴缩成一点、眼睛半闭时变形怪）。
这里按新底稿重算：
- 用同一父变形器下一个形状没问题的网格（FaceBase / EyeSocketMask），拟合「画布像素 → 父变形器坐标」的仿射变换；
- MouthLineClosed：三个关键形态都设成新底稿的原样；
- 眼睛（眼皮往下压的闭眼，学 PSD2Live）：
    EyeLineUpper  open=1 原样，0.5 往下移半只眼，0 移到闭眼线的位置（透明度照旧 1/1/0）
    EyeWhite      open=1 原样，0.5 以下眼线为底压扁一半，0 压成一条（眼珠被它裁掉，自然跟着变小）
用法：python3 refit.py 源.cmo3 目标.cmo3"""
import sys, re
import numpy as np
sys.path.insert(0, '/tmp/claude-0/-home-claude/5d1ddcc7-fe5e-5109-8e8f-60afaa718bac/scratchpad/caff')
from caff import read_xml, write_xml
from model import params, grid

src, dst = sys.argv[1], sys.argv[2]
d = open(src, 'rb').read()
s = read_xml(d)[0].decode('utf-8')
P = params(s)


def mesh(name):
    m = re.search(rf'<CArtMeshSource xs.id="#\d+"[^>]*>\s*<ACDrawableSource xs.n="super">\s*<ACParameterControllableSource xs.n="super">\s*<s xs.n="localName">{re.escape(name)}</s>', s)
    st = m.start(); en = s.find('</CArtMeshSource>', st); b = s[st:en]
    pts = np.array([float(v) for v in re.search(r'<float-array xs.n="point" count="\d+">([^<]*)<', b).group(1).split()]).reshape(-1, 2)
    km = re.search(r'<KeyformGridSource xs.n="keyformGridSource"( xs.ref="(#\d+)")?', b)
    kg = s.rfind('<KeyformGridSource', 0, s.find(f'xs.id="{km.group(2)}"') + 1) if km.group(2) else st + km.start()
    forms = []
    for c, fg in grid(s, kg, P):
        for mm in re.finditer(r'<CArtMeshForm[^>]*>', b):
            if re.search(rf'CFormGuid xs\.n="guid" xs\.(?:ref|id)="{fg}"', b[mm.end():mm.end() + 600]):
                fe = b.find('</CArtMeshForm>', mm.end())
                pm = re.search(r'<float-array xs.n="positions" count="\d+">([^<]*)<', b[mm.end():fe])
                a = st + mm.end() + pm.start(1)
                forms.append((c, a, a + len(pm.group(1)), np.array([float(v) for v in pm.group(1).split()]).reshape(-1, 2)))
                break
    parent = re.search(r'<CDeformerGuid xs.n="targetDeformerGuid" xs.ref="(#\d+)"', b).group(1)
    return dict(pts=pts, forms=forms, parent=parent)


def affine(ref):
    """画布 → 父坐标：用一个只有一个关键形态、形状正确的网格拟合"""
    M = mesh(ref)
    X = np.c_[M['pts'], np.ones(len(M['pts']))]
    Y = M['forms'][0][3]
    A, res, *_ = np.linalg.lstsq(X, Y, rcond=None)
    err = np.abs(X @ A - Y).max() / (np.ptp(Y, axis=0).max())
    print(f'  仿射 {ref}: 最大误差 {err:.3%}')
    return lambda p: np.c_[p, np.ones(len(p))] @ A


edits = []
def put(form, arr):
    edits.append((form[1], form[2], ' '.join(f'{v:.7g}' for v in arr.reshape(-1))))


# 嘴：:3
mo = mesh('MouthLineClosed')
fb = mesh('FaceBase')
assert mo['parent'] == fb['parent']
T = affine('FaceBase')
rest = T(mo['pts'])
for f in mo['forms']:
    put(f, rest)
print('MouthLineClosed: 关键形态', len(mo['forms']), '个 → 原样')

# 眼睛
for side in 'LR':
    ref = f'EyeSocketMask_{side}'
    T = affine(ref)
    up, wh, lo, cl = (mesh(f'{n}_{side}') for n in ('EyeLineUpper', 'EyeWhite', 'EyeLineLower', 'EyeLineClosed'))
    for M in (up, wh, lo, cl):
        assert M['parent'] == mesh(ref)['parent'], '父变形器不一样'
    upR, whR, loR, clR = T(up['pts']), T(wh['pts']), T(lo['pts']), T(cl['pts'])
    eye_top = upR[:, 1].min(); bottom = loR[:, 1].min()  # y 往下变大
    close_y = (clR[:, 1].min() + clR[:, 1].max()) / 2
    shift_full = close_y - (upR[:, 1].min() + upR[:, 1].max()) / 2
    for f in up['forms']:
        o = f[0][f'ParamEye{side}Open']
        put(f, upR + [0, shift_full * (1 - o)])
    for f in wh['forms']:
        o = f[0][f'ParamEye{side}Open']
        base = close_y + 0.25 * (bottom - close_y)
        y = base + (whR[:, 1] - base) * max(o, 0.04)
        put(f, np.c_[whR[:, 0], y])
    print(f'眼睛 {side}: 上眼线下移 {shift_full:.4f}，眼白以 y={close_y:.4f} 为底压扁')

for a, b_, t in sorted(edits, reverse=True):
    s = s[:a] + t + s[b_:]
open(dst, 'wb').write(write_xml(d, s.encode('utf-8')))
print('写入', dst, len(edits), '个关键形态')
