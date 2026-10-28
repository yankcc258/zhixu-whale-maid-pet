"""c：脖子位置 / 面部旋转 的轴心真的挪到脖子（537,875）。之前轴心在父曲面左上角，全身拉伸时头被按 10% 的"到脚底距离"整体抬走，
脖子露出来像乌龟。挪完以后头跟着脖子那一点走。脖子曲面的拉伸量 28px → 10px。
用法：python3 patch_v12c.py 输入.cmo3 输出.cmo3"""
import sys, os
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from caff import read_xml, write_xml
from rigedit import Rig
import model as M
d = open(sys.argv[1], 'rb').read()
x, _ = read_xml(d)
r = Rig(x.decode('utf-8'))
NECK = (537.0, 875.0)
r.rot_move_pivot('脖子位置', NECK)
r.rot_move_pivot('面部旋转', NECK)
# 面部旋转原来靠平移模拟绕脖子转，现在轴心就在脖子：平移归零
r.rot_set_forms('面部旋转', lambda c, a, ox, oy, s: (a, 0.0, 0.0, s))
# 脖子曲面：拉伸量减到 10px
D = M.deformers(r.s); P = M.params(r.s)
F = M.forms(r.s, D['脖子曲面'])
neutral = None
for combo, fg in M.grid(r.s, D['脖子曲面']['grid'], P):
    if abs(combo.get('ParamBodyStretch', 0)) < 1e-9:
        neutral = np.array(F[fg][2]).reshape(-1, 2)
def neck(combo, pos):
    k = combo.get('ParamBodyStretch', 0)
    out = neutral.copy()
    y = out[:, 1]; t = 1 - (y - y.min()) / (y.max() - y.min())
    out[:, 1] -= 10.0 * k * t
    return out
r.warp_edit('脖子曲面', neck)
r.canonicalize_grids()
open(sys.argv[2], 'wb').write(write_xml(d, r.s.encode('utf-8')))
print('\n'.join(r.log))
