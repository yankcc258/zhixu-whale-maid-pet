"""v12 骨架：在 Cubism 导入 v12 PSD 后保存的 seeko_q_v12_raw.cmo3 上，用 rigedit 建结构、算线性关键形态。
用法：python3 rig_v12.py seeko_q_v12_raw.cmo3 seeko_q_v12.cmo3

做了什么（细节见 骨架规格_v12.md）：
1. 删掉旧的 DressBase / HairBack_L/R / LegStocking_L/R；新图层挂到该在的变形器下、描画顺序排好。
2. 手臂：肩轴心挪到肩球中心，抬手范围 -10~10 → +30°(往后)~-110°(举过头)；肘 -10~10 → -15°~120°。
3. 新关节：手腕（ParamWristL/R ±30°，挂两只手，ParamHandL/R 0 握拳 1 张开）、膝（ParamKneeL/R 0~60°）。
4. 腿摆动 ±10 → ±30°。
5. 躯干：上半身 Z 从「平移」改成绕髋部的弯（顶行 ±5°，底行不动）；X 改成剪切；裙子反向微剪切。
6. 全身拉伸 ParamBodyStretch 0~1（脚底为锚，整体 +10%）；脖子曲面跟着再 +15%。
7. 裙摆曲面 ParamSkirtX（底行 ±40px）/ ParamSkirtY（-1 下垂收窄，+1 鼓起）；围裙曲面 ParamApron。
8. 后发：整体加 ParamHairBackY（上下浮）；左右各三缕各自一个曲面，ParamHairBack1/2/3（底行 ±35/30/25px）。
"""
import sys
import os
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
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


# ---------- 0. 参数 ----------
r.add_param('ParamHandL', '左手 张开', 0, 1, 0, '0 握拳 1 张开')
r.add_param('ParamHandR', '右手 张开', 0, 1, 0, '0 握拳 1 张开')
r.add_param('ParamWristL', '左手腕', -10, 10, 0, '±30°，+ 手掌往外')
r.add_param('ParamWristR', '右手腕', -10, 10, 0, '±30°，+ 手掌往外')
r.add_param('ParamKneeL', '左膝 弯曲', 0, 10, 0, '0~60°，脚往外后甩')
r.add_param('ParamKneeR', '右膝 弯曲', 0, 10, 0, '0~60°，脚往外后甩')
r.add_param('ParamBodyStretch', '全身 拉伸', 0, 1, 0, '拎起来用：整体 +10%，脖子 +15%')
r.add_param('ParamSkirtX', '裙摆 左右', -1, 1, 0, '底边 ±40px')
r.add_param('ParamSkirtY', '裙摆 上下', -1, 1, 0, '-1 下垂收窄，+1 鼓起')
r.add_param('ParamApron', '围裙 摆动', -1, 1, 0, '')
r.add_param('ParamHairBackY', '后发 上下', -1, 1, 0, '-1 下压，+1 飘起')
r.add_param('ParamHairBack1', '后发 外缕', -1, 1, 0, '底端 ±35px')
r.add_param('ParamHairBack2', '后发 中缕', -1, 1, 0, '底端 ±30px')
r.add_param('ParamHairBack3', '后发 内缕', -1, 1, 0, '底端 ±25px')

# ---------- 1. 删旧图层、新图层归位、描画顺序 ----------
ORDER = {
    'HairBack_Under': 290, 'HairBack_R_Inner': 294, 'HairBack_R_Mid': 296, 'HairBack_R_Outer': 298,
    'HairBack_L_Inner': 300, 'HairBack_L_Mid': 302, 'HairBack_L_Outer': 304,
    'LegThigh_R': 310, 'LegShin_R': 312, 'Shoe_R': 320, 'LegThigh_L': 315, 'LegShin_L': 317, 'Shoe_L': 325,
    'SkirtInner': 328, 'SkirtBack': 330, 'SkirtHemLace': 335, 'SkirtFront': 340,
    'ArmUpper_R': 345, 'ArmUpper_L': 355, 'Neck': 358, 'DressTop': 360, 'ApronLace': 361, 'ApronBody': 362,
    'BodiceWhite': 365, 'ChestLace_R': 370, 'ChestLace_L': 375, 'Waistband': 390, 'NeckCollar': 395,
    'HandOpen_R': 653, 'HandOpen_L': 654,
}
for n, o in ORDER.items():
    r.set_draw_order(n, o)
r.set_visible('HandOpen_L', True)
r.set_visible('HandOpen_R', True)

r.reparent_to_warp('DressTop', None, '呼吸')
r.reparent_to_warp('SkirtBack', None, '下半身的曲面')
r.reparent_to_warp('SkirtInner', None, '下半身的曲面')
for side in 'LR':
    r.reparent_to_rot(f'LegThigh_{side}', None, f'{"左" if side == "L" else "右"}腿旋转')
    r.reparent_to_rot(f'LegShin_{side}', None, f'{"左" if side == "L" else "右"}腿旋转')
    r.reparent_to_rot(f'HandOpen_{side}', None, f'{"左" if side == "L" else "右"}小臂旋转')
for n in ['HairBack_Under', 'HairBack_L_Outer', 'HairBack_L_Mid', 'HairBack_L_Inner', 'HairBack_R_Outer', 'HairBack_R_Mid', 'HairBack_R_Inner']:
    r.reparent_to_warp(n, None, 'HairBackSway')
for n in ['DressBase', 'HairBack_L', 'HairBack_R', 'LegStocking_L', 'LegStocking_R']:
    r.delete_mesh(n)

# ---------- 2. 手臂：轴心 + 范围 ----------
# 左 = 画面右。抬手：左臂负角度是往外抬（v09 约定），右臂相反
r.rot_move_pivot('左臂旋转', (668, 935))
r.rot_move_pivot('右臂旋转', (392, 935))
r.rot_set_forms('左臂旋转', lambda c, a, ox, oy, s: ({-10: 30.0, 0: 0.0, 10: -110.0}[round(c['ParamArmLA'])], ox, oy, s))
r.rot_set_forms('右臂旋转', lambda c, a, ox, oy, s: ({-10: -30.0, 0: 0.0, 10: 110.0}[round(c['ParamArmRA'])], ox, oy, s))
r.rot_move_pivot('左小臂旋转', (700, 1018))
r.rot_move_pivot('右小臂旋转', (365, 1018))
r.rot_set_forms('左小臂旋转', lambda c, a, ox, oy, s: ({-10: -15.0, 0: 0.0, 10: 120.0}[round(c['ParamArmLB'])], ox, oy, s))
r.rot_set_forms('右小臂旋转', lambda c, a, ox, oy, s: ({-10: 15.0, 0: 0.0, 10: -120.0}[round(c['ParamArmRB'])], ox, oy, s))

# ---------- 3. 手腕 + 两只手切换 ----------
r.add_rot('左手腕旋转', '左小臂旋转', (760, 1075), [('ParamWristL', [-10, 0, 10])],
          lambda v: ({-10: 30.0, 0: 0.0, 10: -30.0}[v[0]], 0, 0, 1.0), ['Hand_L', 'HandOpen_L'], handle=60)
r.add_rot('右手腕旋转', '右小臂旋转', (307, 1065), [('ParamWristR', [-10, 0, 10])],
          lambda v: ({-10: -30.0, 0: 0.0, 10: 30.0}[v[0]], 0, 0, 1.0), ['Hand_R', 'HandOpen_R'], handle=60)
r.mesh_add_hide_axis('Hand_L', 'ParamHandL', hide_at=1)
r.mesh_add_hide_axis('HandOpen_L', 'ParamHandL', hide_at=0)
r.mesh_add_hide_axis('Hand_R', 'ParamHandR', hide_at=1)
r.mesh_add_hide_axis('HandOpen_R', 'ParamHandR', hide_at=0)

# ---------- 4. 腿：摆动 ±30°，膝 ----------
def leg_fn(sign):
    def f(c, a, ox, oy, s):
        k = round(c['ParamLegL'] if 'ParamLegL' in c else c['ParamLegR'])
        return ({-10: 30.0 * sign, 0: 0.0, 10: -30.0 * sign}[k], ox, oy, s)
    return f


r.rot_set_forms('左腿旋转', leg_fn(+1))   # 左腿（画面右）往外 = 逆时针 = 负角度
r.rot_set_forms('右腿旋转', leg_fn(-1))
r.add_rot('左小腿旋转', '左腿旋转', (620, 1255), [('ParamKneeL', [0, 10])],
          lambda v: ({0: 0.0, 10: -60.0}[v[0]], 0, 0, 1.0), ['LegShin_L', 'Shoe_L'], handle=70)
r.add_rot('右小腿旋转', '右腿旋转', (450, 1255), [('ParamKneeR', [0, 10])],
          lambda v: ({0: 0.0, 10: 60.0}[v[0]], 0, 0, 1.0), ['LegShin_R', 'Shoe_R'], handle=70)

# ---------- 5. 躯干：Z 变弯、X 变剪切 ----------
HIP = np.array([543.0, 1170.0])
TOP = 231.0


def row_w(y):
    return np.clip((HIP[1] - y) / (HIP[1] - TOP), 0.0, 1.0)


D = M.deformers(r.s)
P = M.params(r.s)


def neutral_of(name):
    F = M.forms(r.s, D[name])
    for combo, fg in M.grid(r.s, D[name]['grid'], P):
        if all(abs(v) < 1e-9 for v in combo.values()):
            return np.array(F[fg][2]).reshape(-1, 2)
    raise RuntimeError(name)


NZ = neutral_of('上半身的曲面Z')
NY = neutral_of('上半身的曲面Y')
BODY_DY = {-10: 19.0, 0: 0.0, 10: -24.0}


def bodyZ(combo, pos):
    y = combo.get('ParamBodyAngleY', 0.0)
    z = combo.get('ParamBodyAngleZ', 0.0)
    out = NZ.copy()
    w = row_w(NZ[:, 1])
    ang = -0.5 * z  # ±10 → ∓5°：Z 正 = 身子往画面右倾（和原来的平移方向一致：原来 +Z 顶部右移）
    for i in range(len(out)):
        v = NZ[i] - HIP
        out[i] = HIP + R(ang * w[i]) @ v
    out[:, 1] += BODY_DY[round(y)]
    return out


r.warp_edit('上半身的曲面Z', bodyZ)


def bodyX(combo, pos):
    xk = combo.get('ParamBodyAngleX', 0.0)
    out = NY.copy()
    # 子物件坐标是 0~1：顶行往 X 方向剪 2.2% ≈ 24px
    w = row_w(231.0 + NY[:, 1] * (1579.5 - 231.0))  # 子坐标 0~1 → 画布 y（父曲面 Z 的范围）
    out[:, 0] += 0.0022 * xk * w
    return out


r.warp_edit('上半身的曲面Y', bodyX)


def skirt_counter(k, pos):
    # 下半身曲面是根级（画布）：底行反向剪 6px（身子往右倾时裙子往左甩一点）
    w = np.clip((pos[:, 1] - 1010.0) / (1240.0 - 1010.0), 0, 1)
    pos[:, 0] += -0.6 * k * w
    return pos


r.warp_add_axis('下半身的曲面', 'ParamBodyAngleZ', [-10, 0, 10], skirt_counter)

# ---------- 6. 裙摆 / 围裙 ----------
SK = (285.0, 1000.0, 785.0, 1245.0)


def skirt_forms(vals, g):
    sx, sy = vals
    t = (g[:, 1] - SK[1]) / (SK[3] - SK[1])  # 0 顶 1 底
    cx = (SK[0] + SK[2]) / 2
    g[:, 0] += 40.0 * sx * t
    if sy < 0:  # 下垂收窄
        g[:, 1] += 25.0 * (-sy) * t
        g[:, 0] += (cx - g[:, 0]) * 0.08 * (-sy) * t
    elif sy > 0:  # 鼓起
        g[:, 1] -= 15.0 * sy * t
        g[:, 0] += (g[:, 0] - cx) * 0.10 * sy * t
    return g


r.add_warp('裙摆曲面', '下半身的曲面', SK, [('ParamSkirtX', [-1, 0, 1]), ('ParamSkirtY', [-1, 0, 1])], skirt_forms,
           ['SkirtInner', 'SkirtBack', 'SkirtHemLace', 'SkirtFront'])

AP = (425.0, 1015.0, 635.0, 1170.0)


def apron_forms(vals, g):
    t = (g[:, 1] - AP[1]) / (AP[3] - AP[1])
    g[:, 0] += 20.0 * vals[0] * t
    return g


r.add_warp('围裙曲面', '呼吸', AP, [('ParamApron', [-1, 0, 1])], apron_forms, ['ApronLace', 'ApronBody'])

# ---------- 7. 全身拉伸 + 脖子 ----------
FOOT = 1400.0


def stretch_forms(vals, g):
    k = vals[0]
    g[:, 1] = FOOT - (FOOT - g[:, 1]) * (1 + 0.10 * k)
    return g


r.add_warp('全身拉伸', None, (-200.0, -450.0, 1300.0, 1650.0), [('ParamBodyStretch', [0, 1])], stretch_forms, [],
           child_deformers=['上半身的曲面Z', '下半身的曲面', '左腿旋转', '右腿旋转'])


def neck_stretch(k, pos):
    # 脖子曲面是 脖子位置(rot) 的子物件：坐标 = 画布 - 轴心。顶行往上 15%（约 28px）
    y = pos[:, 1]
    t = 1 - (y - y.min()) / (y.max() - y.min())
    pos[:, 1] -= 28.0 * k * t
    return pos


r.warp_add_axis('脖子曲面', 'ParamBodyStretch', [0, 1], neck_stretch)

# ---------- 8. 后发 ----------
def hair_y(k, pos):
    y = pos[:, 1]
    t = (y - y.min()) / (y.max() - y.min())
    pos[:, 1] += (-25.0 if k > 0 else 15.0) * abs(k) * t
    return pos


r.warp_add_axis('HairBackSway', 'ParamHairBackY', [-1, 0, 1], hair_y)

STRANDS = {
    'HairBack_L_Outer': ((700, 480, 1040, 1210), 'ParamHairBack1', 35.0),
    'HairBack_L_Mid': ((600, 460, 985, 1285), 'ParamHairBack2', 30.0),
    'HairBack_L_Inner': ((490, 455, 845, 1270), 'ParamHairBack3', 25.0),
    'HairBack_R_Outer': ((50, 480, 386, 1210), 'ParamHairBack1', 35.0),
    'HairBack_R_Mid': ((100, 460, 486, 1285), 'ParamHairBack2', 30.0),
    'HairBack_R_Inner': ((240, 455, 596, 1270), 'ParamHairBack3', 25.0),
}
for n, (bb, pid, amp) in STRANDS.items():
    def mk(bb, amp):
        def f(vals, g):
            t = (g[:, 1] - bb[1]) / (bb[3] - bb[1])
            g[:, 0] += amp * vals[0] * t * t  # 发根不动、越到发梢越甩
            return g
        return f
    r.add_warp(n.replace('HairBack_', '后发') + '曲面', 'HairBackSway', tuple(map(float, bb)), [(pid, [-1, 0, 1])], mk(bb, amp), [n], cols=3, rows=6)

r.canonicalize_grids()
open(DST, 'wb').write(write_xml(d, r.s.encode('utf-8')))
print('\n'.join(r.log))
print('写出', DST)
