"""v09 骨架：在 v08f 上直接改工程文件（用 tools/live2d-checks/rigedit.py），Cubism 只用来检查和导出。
用法：python3 rig_v09.py 源.cmo3 目标.cmo3

改了什么：
1. 歪头的轴心从脸中心挪到脖子（面部旋转的关键形态 origin 重算），下巴不再从脖子上滑开。
2. 转头（头部曲面 AngleX）：下巴那两行的平移打折，头顶照旧，脖子不脱节；抬头低头最下一行也打折。
3. 肩膀轴心从锁骨上方挪到袖子顶端；抬手 -10~10 → +10°~-60°。
4. 新关节（都是旋转变形器）：
   - 左/右小臂旋转：ParamArmLB/RB，挂 ArmLower/Cuff/Hand，+ 往身体里弯 55°
   - 左/右腿旋转（根级）：ParamLegL/R 外摆 15°；同时吃 ParamBodyAngleY：蹲下时腿缩短、起身时拉长，脚底不动
   - 呆毛摆动：ParamAhoge ±18°
   - 左/右耳鳍摆动：ParamFinL/R ±12°（+ 往上）
5. ParamBodyAngleY 真的起作用：上半身曲面和下半身曲面（裙子）整体上下 +10 → 上移 24px，-10 → 下沉 19px。
6. ArmLower 描画顺序挪到围裙前面（弯肘时小臂在身前）。
"""
import sys
import os
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', 'tools', 'live2d-checks'))
from caff import read_xml, write_xml  # noqa: E402
from rigedit import Rig  # noqa: E402
import model as M  # noqa: E402

SRC, DST = sys.argv[1], sys.argv[2]
d = open(SRC, 'rb').read()
x, _ = read_xml(d)
r = Rig(x.decode('utf-8'))


def R(deg):
    t = np.radians(deg)
    return np.array([[np.cos(t), -np.sin(t)], [np.sin(t), np.cos(t)]])


# ---------- 1. 歪头轴心 → 脖子 ----------
NECK = np.array([537.0, 875.0])
P = r.rot_pivot('面部旋转')


def head_forms(combo, ang, ox, oy, sc):
    v = NECK - P
    T = v - R(ang) @ v  # 绕 P 转 ang 再平移 T == 绕 NECK 转 ang
    return ang, T[0], T[1], sc


r.rot_set_forms('面部旋转', head_forms)

# ---------- 2. 转头时下巴少动 ----------
ROWX = [1.0, 1.0, 1.0, 1.0, 0.8, 0.35]  # 6 行，从头顶到下巴
ROWY = [1.0, 1.0, 1.0, 1.0, 1.0, 0.6]
_neutral = {}


def head_warp(combo, pos):
    key = tuple(sorted(combo.items()))
    if all(abs(v) < 1e-9 for v in combo.values()):
        _neutral['n'] = pos.copy()
        return pos
    n = _neutral['n']
    out = pos.copy()
    rows = int(round(len(pos) / 6))
    for i in range(len(pos)):
        row = i // (len(pos) // rows)
        out[i, 0] = n[i, 0] + (pos[i, 0] - n[i, 0]) * ROWX[row]
        out[i, 1] = n[i, 1] + (pos[i, 1] - n[i, 1]) * ROWY[row]
    return out


# grid 顺序不保证中立形态在前：先找中立
D = M.deformers(r.s)
Pm = M.params(r.s)
F = M.forms(r.s, D['头部曲面'])
for combo, fg in M.grid(r.s, D['头部曲面']['grid'], Pm):
    if all(abs(v) < 1e-9 for v in combo.values()):
        _neutral['n'] = np.array(F[fg][2]).reshape(-1, 2)
assert 'n' in _neutral
r.warp_edit('头部曲面', head_warp)

# ---------- 3. 肩膀轴心 ----------
r.rot_move_pivot('左臂旋转', (639, 918))
r.rot_move_pivot('右臂旋转', (419, 918))
r.rot_set_forms('左臂旋转', lambda c, a, ox, oy, s: ({-10: 10.0, 0: 0.0, 10: -60.0}[round(c['ParamArmLA'])], ox, oy, s))
r.rot_set_forms('右臂旋转', lambda c, a, ox, oy, s: ({-10: -10.0, 0: 0.0, 10: 60.0}[round(c['ParamArmRA'])], ox, oy, s))

# ---------- 4. 新参数 ----------
r.add_param('ParamArmLB', '左臂 弯肘', -10, 10, 0, '+小臂往身体里弯')
r.add_param('ParamArmRB', '右臂 弯肘', -10, 10, 0, '+小臂往身体里弯')
r.add_param('ParamLegL', '左腿 摆动', -10, 10, 0, '+往外摆')
r.add_param('ParamLegR', '右腿 摆动', -10, 10, 0, '+往外摆')
r.add_param('ParamAhoge', '呆毛 摆动', -10, 10, 0, '+往屏幕右侧')
r.add_param('ParamFinL', '左耳鳍 摆动', -10, 10, 0, '+往上')
r.add_param('ParamFinR', '右耳鳍 摆动', -10, 10, 0, '+往上')

# ---------- 肘 ----------
r.add_rot('左小臂旋转', '左臂旋转', (693, 1010), [('ParamArmLB', [-10, 0, 10])],
          lambda v: ({-10: -12.0, 0: 0.0, 10: 55.0}[v[0]], 0, 0, 1.0), ['ArmLower_L', 'Cuff_L', 'Hand_L'], handle=80)
r.add_rot('右小臂旋转', '右臂旋转', (361, 1008), [('ParamArmRB', [-10, 0, 10])],
          lambda v: ({-10: 12.0, 0: 0.0, 10: -55.0}[v[0]], 0, 0, 1.0), ['ArmLower_R', 'Cuff_R', 'Hand_R'], handle=80)
r.set_draw_order('ArmLower_L', 398)
r.set_draw_order('ArmLower_R', 396)

# ---------- 5. 身子上下 ----------
BODY_DY = {-10: 19.0, 0: 0.0, 10: -24.0}


def body_shift(k, pos):
    pos[:, 1] += BODY_DY[k]
    return pos


r.warp_add_axis('上半身的曲面Z', 'ParamBodyAngleY', [-10, 0, 10], body_shift)
r.warp_add_axis('下半身的曲面', 'ParamBodyAngleY', [-10, 0, 10], body_shift)

# ---------- 腿（根级；吃摆动 + 身子上下）----------
FOOT = 1400.0


def leg_forms(sign):
    def f(v):
        leg, body = v
        ang = {-10: -10.0 * sign, 0: 0.0, 10: 15.0 * sign}[leg]
        sc = {-10: 0.92, 0: 1.0, 10: 1.10}[body]
        dy = (FOOT - 1162.0) * (1 - sc)  # 脚底不动
        return ang, 0.0, dy, sc
    return f


r.add_rot('左腿旋转', None, (618, 1162), [('ParamLegL', [-10, 0, 10]), ('ParamBodyAngleY', [-10, 0, 10])],
          leg_forms(-1), ['LegStocking_L', 'Shoe_L'], handle=120, children_parent='下半身的曲面')
r.add_rot('右腿旋转', None, (445, 1162), [('ParamLegR', [-10, 0, 10]), ('ParamBodyAngleY', [-10, 0, 10])],
          leg_forms(+1), ['LegStocking_R', 'Shoe_R'], handle=120, children_parent='下半身的曲面')

# ---------- 呆毛、耳鳍 ----------
r.add_rot('呆毛摆动', '头部曲面', (505, 305), [('ParamAhoge', [-10, 0, 10])],
          lambda v: ({-10: -18.0, 0: 0.0, 10: 18.0}[v[0]], 0, 0, 1.0), ['Ahoge'], handle=90)
r.add_rot('左耳鳍摆动', '头部曲面', (832, 770), [('ParamFinL', [-10, 0, 10])],
          lambda v: ({-10: 12.0, 0: 0.0, 10: -12.0}[v[0]], 0, 0, 1.0), ['FinEar_L'], handle=90)
r.add_rot('右耳鳍摆动', '头部曲面', (228, 770), [('ParamFinR', [-10, 0, 10])],
          lambda v: ({-10: -12.0, 0: 0.0, 10: 12.0}[v[0]], 0, 0, 1.0), ['FinEar_R'], handle=90)

print('\n'.join(r.log))
open(DST, 'wb').write(write_xml(d, r.s.encode('utf-8')))
print('→', DST)
