"""希可 v09 骨架的动作集（.motion3.json）+ 表情里加耳鳍/呆毛 + 写进四个 model3.json。
用法：python3 make_motions_v2.py <桌宠仓库>/src/live2d/seeko

参数约定：ArmLA/RA + 抬起（外侧）；ArmLB/RB + 弯肘（手往身体里）；LegL/R + 外摆；
BodyAngleY + 起身/踮脚、- 蹲下；Ahoge、FinL/R + 往上/屏幕右。
"""
import json
import math
import sys
from pathlib import Path

OUT = Path(sys.argv[1])
MO = OUT / 'motions'
MO.mkdir(exist_ok=True)
for old in MO.glob('*.motion3.json'):
    old.unlink()

PI = math.pi


def motion(name, dur, curves, loop=False, step=0.05):
    out, segs, pts = [], 0, 0
    n = int(round(dur / step))
    for pid, f in curves.items():
        ts = [round(i * dur / n, 4) for i in range(n + 1)]
        s = [ts[0], round(f(ts[0]), 4)]
        for t in ts[1:]:
            s += [0, t, round(f(t), 4)]
        out.append({'Target': 'Parameter', 'Id': pid, 'Segments': s})
        segs += n
        pts += n + 1
    m = {'Version': 3, 'Meta': {'Duration': dur, 'Fps': 30, 'Loop': loop, 'AreBeziersRestricted': True,
                                'CurveCount': len(out), 'TotalSegmentCount': segs, 'TotalPointCount': pts,
                                'UserDataCount': 0, 'TotalUserDataSize': 0}, 'Curves': out}
    json.dump(m, open(MO / f'{name}.motion3.json', 'w'), indent='\t')


# ---------- 小工具 ----------
def S(per, amp, ph=0.0, off=0.0):
    return lambda t: off + amp * math.sin(2 * PI * t / per + ph)


def bump(t0, t1, amp, hold=0.0):
    """t0 起升到 amp，保持 hold，再在 t1 落回 0（正弦肩）"""
    def f(t):
        if t <= t0 or t >= t1:
            return 0.0
        a = (t1 - t0 - hold) / 2
        if t < t0 + a:
            return amp * math.sin(PI / 2 * (t - t0) / a)
        if t > t1 - a:
            return amp * math.sin(PI / 2 * (t1 - t) / a)
        return amp
    return f


def ease(t0, t1, v0, v1):
    """t0~t1 从 v0 平滑到 v1，之外保持"""
    def f(t):
        if t <= t0:
            return v0
        if t >= t1:
            return v1
        x = (t - t0) / (t1 - t0)
        return v0 + (v1 - v0) * (0.5 - 0.5 * math.cos(PI * x))
    return f


def seq(*parts):
    """[(t0,t1,v0,v1),...] 分段 ease，段之间保持"""
    def f(t):
        v = parts[0][2]
        for t0, t1, v0, v1 in parts:
            if t >= t0:
                v = ease(t0, t1, v0, v1)(t)
        return v
    return f


def add(*fs):
    return lambda t: sum(f(t) for f in fs)


def mul(f, k):
    return lambda t: f(t) * (k(t) if callable(k) else k)


def env(dur, a=0.3):
    """整段的淡入淡出（首尾回 0，待机循环才接得上）"""
    return lambda t: min(1.0, t / a, (dur - t) / a) if 0 < t < dur else 0.0


def wrap(dur, curves, a=0.4):
    e = env(dur, a)
    return {k: (lambda f: (lambda t: f(t) * e(t)))(f) for k, f in curves.items()}


breath = lambda per=4.0: (lambda t: 0.5 - 0.5 * math.cos(2 * PI * t / per))

# ======================= 待机（都 6~8 秒，首尾为 0，随机轮换） =======================
# 1 轻轻晃：重心左右换，胳膊跟着小幅摆，头慢半拍
motion('idle_sway', 8.0, {
    'ParamBreath': breath(),
    **wrap(8.0, {
        'ParamBodyAngleZ': S(8, 3.5),
        'ParamAngleZ': S(8, 4.5, -0.5),
        'ParamAngleX': S(8, 3, 0.3),
        'ParamBodyAngleX': S(8, 1.5, 0.3),
        'ParamArmLA': S(8, 1.5, PI),
        'ParamArmRA': S(8, 1.5, 0),
        'ParamLegL': S(8, 1.8, 0),
        'ParamLegR': S(8, 1.8, PI),
        'ParamBodyAngleY': S(4, 1.2, 0.8),
    }),
})
# 2 东张西望：转头 + 眼珠先到，身子跟一点
motion('idle_look', 6.0, {
    'ParamBreath': breath(3),
    **wrap(6.0, {
        'ParamAngleX': seq((0.4, 1.2, 0, 16), (2.4, 3.4, 16, -16), (4.6, 5.6, -16, 0)),
        'ParamEyeBallX': seq((0.2, 0.7, 0, 0.8), (2.2, 2.8, 0.8, -0.8), (4.4, 5.0, -0.8, 0)),
        'ParamBodyAngleX': seq((0.5, 1.4, 0, 4), (2.5, 3.6, 4, -4), (4.7, 5.8, -4, 0)),
        'ParamAngleY': add(bump(0.8, 2.4, 3), bump(3.0, 4.6, -2)),
        'ParamAngleZ': add(bump(0.6, 2.6, -4), bump(3.0, 4.8, 4)),
        'ParamFinL': bump(0.5, 2.3, 4),
        'ParamFinR': bump(2.7, 4.6, 4),
    }),
})
# 3 想事情：歪头、一只手托腮（抬一点、肘弯到底）、眼睛往上看、眉毛抬
motion('idle_think', 6.0, {
    'ParamBreath': breath(3),
    **wrap(6.0, {
        'ParamAngleZ': bump(0.4, 5.6, 13, hold=3.6),
        'ParamAngleY': bump(0.6, 5.6, 5, hold=3.4),
        'ParamBodyAngleZ': bump(0.4, 5.6, 3, hold=3.6),
        'ParamArmLB': bump(0.3, 5.6, 10, hold=3.8),
        'ParamArmLA': bump(0.3, 5.6, 4, hold=3.8),
        'ParamEyeBallY': bump(0.8, 5.4, 0.9, hold=3.2),
        'ParamEyeBallX': bump(0.8, 5.4, 0.3, hold=3.2),
        'ParamBrowLY': bump(0.8, 5.4, 0.8, hold=3.2),
        'ParamBrowRY': bump(0.8, 5.4, 0.8, hold=3.2),
        'ParamAhoge': add(bump(0.6, 2.0, 6), S(1.3, 2, 0)),
    }),
})
# 4 搓手：两手收到身前，小幅来回蹭，头低一点，眼睛往下看
motion('idle_fidget', 6.0, {
    'ParamBreath': breath(3),
    **wrap(6.0, {
        'ParamArmLB': add(bump(0.3, 5.7, 8.5, hold=4.4), mul(S(0.9, 1.0), lambda t: 1 if 1.2 < t < 4.6 else 0)),
        'ParamArmRB': add(bump(0.3, 5.7, 8.5, hold=4.4), mul(S(0.9, 1.0, PI), lambda t: 1 if 1.2 < t < 4.6 else 0)),
        'ParamArmLA': bump(0.3, 5.7, -1.5, hold=4.4),
        'ParamArmRA': bump(0.3, 5.7, -1.5, hold=4.4),
        'ParamAngleY': bump(0.5, 5.5, -7, hold=4.0),
        'ParamAngleZ': bump(0.5, 5.5, -5, hold=4.0),
        'ParamEyeBallY': bump(0.6, 5.4, -0.8, hold=3.8),
        'ParamEyeBallX': bump(0.6, 5.4, -0.4, hold=3.8),
        'ParamBodyAngleY': bump(0.5, 5.5, -2.5, hold=4.0),
        'ParamFinL': bump(0.5, 5.5, -3, hold=4.0),
        'ParamFinR': bump(0.5, 5.5, -3, hold=4.0),
    }),
})
# 5 踮脚晃：前后重心，踮起来时腿并一点、头抬一点
motion('idle_rock', 7.0, {
    'ParamBreath': breath(3.5),
    **wrap(7.0, {
        'ParamBodyAngleY': add(S(3.5, 4.0, -PI / 2), lambda t: 1.0),
        'ParamAngleY': S(3.5, 3.0, -PI / 2),
        'ParamLegL': S(3.5, -2.0, -PI / 2),
        'ParamLegR': S(3.5, -2.0, -PI / 2),
        'ParamArmLA': S(3.5, -2.0, -PI / 2),
        'ParamArmRA': S(3.5, -2.0, -PI / 2),
        'ParamArmLB': S(3.5, 2.0, -PI / 2),
        'ParamArmRB': S(3.5, 2.0, -PI / 2),
        'ParamAngleZ': S(7, 3, 0.4),
        'ParamBodyAngleZ': S(7, 1.5, 0.4),
    }),
})
# 6 踮脚张望：手搭在额头上（抬手 + 肘弯到底），踮起来，左右扫视
motion('idle_peek', 6.0, {
    'ParamBreath': breath(3),
    **wrap(6.0, {
        'ParamArmRA': bump(0.3, 5.7, 9, hold=4.4),
        'ParamArmRB': bump(0.35, 5.7, 10, hold=4.4),
        'ParamBodyAngleY': bump(0.5, 5.5, 8, hold=4.0),
        'ParamLegL': bump(0.5, 5.5, -2, hold=4.0),
        'ParamLegR': bump(0.5, 5.5, -2, hold=4.0),
        'ParamAngleY': bump(0.5, 5.5, 8, hold=4.0),
        'ParamAngleX': seq((1.0, 2.0, 0, 14), (2.6, 3.8, 14, -14), (4.3, 5.3, -14, 0)),
        'ParamEyeBallX': seq((0.8, 1.6, 0, 0.6), (2.4, 3.4, 0.6, -0.6), (4.2, 5.0, -0.6, 0)),
        'ParamBodyAngleX': seq((1.0, 2.0, 0, 3), (2.6, 3.8, 3, -3), (4.3, 5.3, -3, 0)),
        'ParamAhoge': seq((1.0, 2.2, 0, 5), (2.6, 3.8, 5, -5), (4.3, 5.5, -5, 0)),
    }),
})

# ======================= 动作（心情切换时做一次） =======================
# 挥手：抬起右臂，从肘部挥，头歪一点，笑眼
motion('wave', 2.6, {
    'ParamArmRA': bump(0.0, 2.6, 9.5, hold=1.8),
    'ParamArmRB': add(bump(0.1, 2.5, 6.5, hold=1.7), mul(S(0.42, 3.2), bump(0.5, 2.1, 1.0, hold=1.2))),
    'ParamArmLA': bump(0.0, 2.6, -1.5, hold=1.8),
    'ParamAngleZ': bump(0.1, 2.5, -8, hold=1.6),
    'ParamBodyAngleZ': bump(0.1, 2.5, -3, hold=1.6),
    'ParamAngleX': bump(0.1, 2.5, -5, hold=1.6),
    'ParamEyeLSmile': bump(0.2, 2.4, 1, hold=1.6),
    'ParamEyeRSmile': bump(0.2, 2.4, 1, hold=1.6),
    'ParamEyeLOpen': lambda t: 1 - bump(0.2, 2.4, 1, hold=1.6)(t),
    'ParamEyeROpen': lambda t: 1 - bump(0.2, 2.4, 1, hold=1.6)(t),
    'ParamFinL': bump(0.1, 2.5, 6, hold=1.6),
    'ParamFinR': bump(0.1, 2.5, 6, hold=1.6),
})
# 蹦一下：先蹲（蓄力）再起，腿并拢，手往上甩，落地再缩一下
motion('hop', 1.2, {
    'ParamBodyAngleY': seq((0.0, 0.18, 0, -8), (0.18, 0.4, -8, 10), (0.4, 0.62, 10, 10), (0.62, 0.78, 10, -6), (0.78, 1.2, -6, 0)),
    'ParamLegL': seq((0.18, 0.4, 0, -4), (0.62, 0.9, -4, 0)),
    'ParamLegR': seq((0.18, 0.4, 0, -4), (0.62, 0.9, -4, 0)),
    'ParamArmLA': seq((0.0, 0.18, 0, -3), (0.18, 0.45, -3, 8), (0.62, 1.1, 8, 0)),
    'ParamArmRA': seq((0.0, 0.18, 0, -3), (0.18, 0.45, -3, 8), (0.62, 1.1, 8, 0)),
    'ParamAngleY': seq((0.0, 0.18, 0, -5), (0.18, 0.45, -5, 10), (0.62, 1.1, 10, 0)),
    'ParamAhoge': seq((0.2, 0.45, 0, -8), (0.62, 1.0, -8, 4), (1.0, 1.2, 4, 0)),
    'ParamFinL': seq((0.2, 0.45, 0, -6), (0.62, 1.0, -6, 3), (1.0, 1.2, 3, 0)),
    'ParamFinR': seq((0.2, 0.45, 0, -6), (0.62, 1.0, -6, 3), (1.0, 1.2, 3, 0)),
    'ParamBodyAngleZ': S(1.2, 3, 0),
})
# 欢呼：双手举高，原地蹦两下
motion('cheer', 2.0, {
    'ParamArmLA': bump(0.0, 2.0, 10, hold=1.4),
    'ParamArmRA': bump(0.0, 2.0, 10, hold=1.4),
    'ParamArmLB': bump(0.1, 1.9, 2, hold=1.3),
    'ParamArmRB': bump(0.1, 1.9, 2, hold=1.3),
    'ParamBodyAngleY': add(bump(0.3, 0.8, 10), bump(0.9, 1.4, 10), bump(1.4, 1.9, -4)),
    'ParamAngleY': bump(0.1, 1.9, 10, hold=1.3),
    'ParamAngleZ': S(1.0, 5),
    'ParamBodyAngleZ': S(1.0, 2),
    'ParamEyeLSmile': bump(0.1, 1.9, 1, hold=1.3),
    'ParamEyeRSmile': bump(0.1, 1.9, 1, hold=1.3),
    'ParamEyeLOpen': lambda t: 1 - bump(0.1, 1.9, 1, hold=1.3)(t),
    'ParamEyeROpen': lambda t: 1 - bump(0.1, 1.9, 1, hold=1.3)(t),
    'ParamMouthOpenY': bump(0.1, 1.9, 0.8, hold=1.3),
    'ParamFinL': bump(0.1, 1.9, 9, hold=1.3),
    'ParamFinR': bump(0.1, 1.9, 9, hold=1.3),
})
# 伸懒腰：手举过头，踮脚，仰头，闭眼张嘴，然后松下来
motion('stretch', 3.6, {
    'ParamArmLA': seq((0.0, 0.8, 0, 10), (2.3, 3.2, 10, 0)),
    'ParamArmRA': seq((0.0, 0.8, 0, 10), (2.3, 3.2, 10, 0)),
    'ParamArmLB': seq((0.0, 0.8, 0, 3), (2.3, 3.2, 3, 0)),
    'ParamArmRB': seq((0.0, 0.8, 0, 3), (2.3, 3.2, 3, 0)),
    'ParamBodyAngleY': seq((0.1, 0.9, 0, 9), (2.3, 2.9, 9, -5), (2.9, 3.6, -5, 0)),
    'ParamAngleY': seq((0.0, 0.8, 0, 14), (2.3, 3.2, 14, -3), (3.2, 3.6, -3, 0)),
    'ParamAngleZ': mul(S(3.6, 5, 0.3), env(3.6, 0.5)),
    'ParamBodyAngleZ': mul(S(3.6, 2, 0.3), env(3.6, 0.5)),
    'ParamEyeLOpen': seq((0.0, 0.6, 1, 0), (2.4, 3.0, 0, 1)),
    'ParamEyeROpen': seq((0.0, 0.6, 1, 0), (2.4, 3.0, 0, 1)),
    'ParamMouthOpenY': seq((0.2, 0.9, 0, 1), (2.0, 2.8, 1, 0)),
    'ParamMouthForm': seq((0.2, 0.9, 0, 1), (2.0, 2.8, 1, 0)),
    'ParamFinL': seq((0.0, 0.8, 0, 8), (2.3, 3.2, 8, 0)),
    'ParamFinR': seq((0.0, 0.8, 0, 8), (2.3, 3.2, 8, 0)),
    'ParamAhoge': seq((0.0, 0.8, 0, 6), (2.3, 3.2, 6, 0)),
})
# 缩一下（被戳）：蹲下、手抬到胸前、耳鳍压下，然后慢慢恢复
motion('flinch', 0.9, {
    'ParamBodyAngleY': seq((0.0, 0.08, 0, -7), (0.3, 0.9, -7, 0)),
    'ParamArmLB': seq((0.0, 0.1, 0, 10), (0.35, 0.9, 10, 0)),
    'ParamArmRB': seq((0.0, 0.1, 0, 10), (0.35, 0.9, 10, 0)),
    'ParamArmLA': seq((0.0, 0.1, 0, 2), (0.35, 0.9, 2, 0)),
    'ParamArmRA': seq((0.0, 0.1, 0, 2), (0.35, 0.9, 2, 0)),
    'ParamAngleY': seq((0.0, 0.08, 0, -7), (0.3, 0.9, -7, 0)),
    'ParamAngleX': seq((0.0, 0.08, 0, -5), (0.3, 0.9, -5, 0)),
    'ParamFinL': seq((0.0, 0.08, 0, -10), (0.35, 0.9, -10, 0)),
    'ParamFinR': seq((0.0, 0.08, 0, -10), (0.35, 0.9, -10, 0)),
    'ParamAhoge': seq((0.0, 0.1, 0, -6), (0.3, 0.9, -6, 0)),
    'ParamEyeLOpen': lambda t: 1.0,
    'ParamEyeROpen': lambda t: 1.0,
})
# 点头两下
motion('nod', 1.6, {
    'ParamAngleY': lambda t: -14 * math.sin(PI * t / 0.8) ** 2,
    'ParamBodyAngleY': lambda t: -2 * math.sin(PI * t / 0.8) ** 2,
    'ParamEyeBallY': lambda t: -0.3 * math.sin(PI * t / 0.8) ** 2,
    'ParamAhoge': lambda t: 5 * math.sin(2 * PI * t / 0.8 + 0.8) * math.sin(PI * t / 1.6),
})
# 摇头两下（生气）：头左右，手微微握在身前
motion('shake', 1.6, {
    'ParamAngleX': lambda t: 20 * math.sin(2 * PI * t / 0.8) * math.sin(PI * t / 1.6),
    'ParamBodyAngleX': lambda t: 4 * math.sin(2 * PI * t / 0.8) * math.sin(PI * t / 1.6),
    'ParamArmLB': bump(0.0, 1.6, 4, hold=1.0),
    'ParamArmRB': bump(0.0, 1.6, 4, hold=1.0),
    'ParamArmLA': bump(0.0, 1.6, -3, hold=1.0),
    'ParamArmRA': bump(0.0, 1.6, -3, hold=1.0),
    'ParamFinL': bump(0.0, 1.6, 5, hold=1.0),
    'ParamFinR': bump(0.0, 1.6, 5, hold=1.0),
})
# 歪头：手托脸，眉毛抬，一边耳鳍翘
motion('tilt', 1.8, {
    'ParamAngleZ': bump(0.0, 1.8, 16, hold=1.0),
    'ParamAngleX': bump(0.0, 1.8, 6, hold=1.0),
    'ParamBodyAngleZ': bump(0.0, 1.8, 4, hold=1.0),
    'ParamArmLB': bump(0.0, 1.8, 10, hold=1.0),
    'ParamArmLA': bump(0.0, 1.8, 5, hold=1.0),
    'ParamBrowLY': bump(0.1, 1.7, 1, hold=0.9),
    'ParamBrowRY': bump(0.1, 1.7, 1, hold=0.9),
    'ParamFinL': bump(0.1, 1.7, 7, hold=0.9),
    'ParamFinR': bump(0.1, 1.7, -4, hold=0.9),
    'ParamAhoge': bump(0.1, 1.7, 7, hold=0.9),
})
# 被拎起来：整个人晃，腿来回蹬，手臂跟着甩
motion('swing', 2.4, {
    'ParamAngleZ': lambda t: 16 * math.sin(2 * PI * t / 0.7) * math.exp(-t * 0.9),
    'ParamAngleX': lambda t: 10 * math.sin(2 * PI * t / 0.9) * math.exp(-t * 0.9),
    'ParamBodyAngleZ': lambda t: 8 * math.sin(2 * PI * t / 0.7) * math.exp(-t * 0.9),
    'ParamLegL': lambda t: 9 * math.sin(2 * PI * t / 0.5) * math.exp(-t * 0.7),
    'ParamLegR': lambda t: -9 * math.sin(2 * PI * t / 0.5) * math.exp(-t * 0.7),
    'ParamArmLA': lambda t: 6 * math.sin(2 * PI * t / 0.7 + 1) * math.exp(-t * 0.9) + 3 * math.exp(-t),
    'ParamArmRA': lambda t: -6 * math.sin(2 * PI * t / 0.7 + 1) * math.exp(-t * 0.9) + 3 * math.exp(-t),
    'ParamArmLB': lambda t: 4 * math.exp(-t),
    'ParamArmRB': lambda t: 4 * math.exp(-t),
    'ParamAhoge': lambda t: 10 * math.sin(2 * PI * t / 0.45) * math.exp(-t * 0.8),
    'ParamFinL': lambda t: 8 * math.sin(2 * PI * t / 0.5) * math.exp(-t * 0.8),
    'ParamFinR': lambda t: -8 * math.sin(2 * PI * t / 0.5) * math.exp(-t * 0.8),
})
# 害羞捂脸：手举到脸前，低头，身子缩一点
motion('shy', 2.2, {
    'ParamArmRA': bump(0.0, 2.2, 7, hold=1.4),
    'ParamArmRB': bump(0.05, 2.2, 10, hold=1.4),
    'ParamArmLB': bump(0.0, 2.2, 5, hold=1.4),
    'ParamAngleY': bump(0.1, 2.1, -9, hold=1.3),
    'ParamAngleZ': bump(0.1, 2.1, 7, hold=1.3),
    'ParamAngleX': bump(0.1, 2.1, 6, hold=1.3),
    'ParamBodyAngleY': bump(0.1, 2.1, -3, hold=1.3),
    'ParamBodyAngleZ': bump(0.1, 2.1, 3, hold=1.3),
    'ParamFinL': bump(0.1, 2.1, -6, hold=1.3),
    'ParamFinR': bump(0.1, 2.1, -6, hold=1.3),
    'ParamEyeBallX': bump(0.1, 2.1, -0.6, hold=1.3),
    'ParamEyeBallY': bump(0.1, 2.1, -0.4, hold=1.3),
})
# 犯困瘫下去：蹲一点、头耷拉、手垂下、耳鳍耷拉
motion('slump', 3.0, {
    'ParamBodyAngleY': seq((0.0, 1.2, 0, -8), (2.2, 3.0, -8, 0)),
    'ParamAngleY': seq((0.0, 1.2, 0, -10), (2.2, 3.0, -10, 0)),
    'ParamAngleZ': seq((0.0, 1.2, 0, 10), (2.2, 3.0, 10, 0)),
    'ParamBodyAngleZ': seq((0.0, 1.2, 0, 3), (2.2, 3.0, 3, 0)),
    'ParamArmLA': seq((0.0, 1.2, 0, -3), (2.2, 3.0, -3, 0)),
    'ParamArmRA': seq((0.0, 1.2, 0, -3), (2.2, 3.0, -3, 0)),
    'ParamFinL': seq((0.0, 1.2, 0, -9), (2.2, 3.0, -9, 0)),
    'ParamFinR': seq((0.0, 1.2, 0, -9), (2.2, 3.0, -9, 0)),
    'ParamAhoge': seq((0.0, 1.2, 0, -5), (2.2, 3.0, -5, 0)),
    'ParamEyeLOpen': seq((0.0, 1.0, 1, 0.3), (2.0, 3.0, 0.3, 1)),
    'ParamEyeROpen': seq((0.0, 1.0, 1, 0.3), (2.0, 3.0, 0.3, 1)),
})
# 蹬腿（不爽）：一条腿来回蹬，手背后面（手臂往后一点），头别开
motion('kick', 2.0, {
    'ParamLegL': lambda t: 8 * max(0.0, math.sin(2 * PI * t / 0.6)) * math.sin(PI * t / 2.0),
    'ParamBodyAngleZ': lambda t: -3 * math.sin(PI * t / 2.0),
    'ParamBodyAngleY': lambda t: -1.5 * max(0.0, math.sin(2 * PI * t / 0.6)) * math.sin(PI * t / 2.0),
    'ParamAngleX': bump(0.0, 2.0, -12, hold=1.4),
    'ParamAngleZ': bump(0.0, 2.0, 6, hold=1.4),
    'ParamArmLA': bump(0.0, 2.0, -3, hold=1.4),
    'ParamArmRA': bump(0.0, 2.0, -3, hold=1.4),
    'ParamEyeBallX': bump(0.0, 2.0, -0.7, hold=1.4),
    'ParamFinL': bump(0.0, 2.0, -5, hold=1.4),
    'ParamFinR': bump(0.0, 2.0, -5, hold=1.4),
    'ParamAhoge': lambda t: 6 * math.sin(2 * PI * t / 0.6) * math.sin(PI * t / 2.0),
})

# 走路（跑动时循环；桌宠横着移动，身子和头朝屏幕左边，往右走时画布镜像）：
# 每步 0.42 秒，腿交替，身子每步颠一下，手臂反向摆，头跟着轻轻点
STEP = 0.42
def walk_curves():
    tri = lambda ph: (lambda t: math.sin(2 * PI * t / (2 * STEP) + ph))
    bob = lambda t: -3.2 * abs(math.sin(PI * t / STEP)) + 1.6
    return {
        'ParamLegL': lambda t: 10 * tri(0)(t),
        'ParamLegR': lambda t: 10 * tri(PI)(t),
        'ParamBodyAngleY': bob,
        'ParamArmLA': lambda t: -2.5 + 4.5 * tri(PI)(t),
        'ParamArmRA': lambda t: -2.5 + 4.5 * tri(0)(t),
        'ParamArmLB': lambda t: 3 + 1.5 * tri(PI)(t),
        'ParamArmRB': lambda t: 3 + 1.5 * tri(0)(t),
        'ParamAngleX': lambda t: -14.0,
        'ParamBodyAngleX': lambda t: -6.0,
        'ParamAngleY': lambda t: -1.5 * abs(math.sin(PI * t / STEP + 0.6)),
        'ParamAngleZ': lambda t: 2.0 * tri(0.4)(t),
        'ParamBodyAngleZ': lambda t: 1.5 * tri(0.4)(t),
        'ParamEyeBallX': lambda t: -0.5,
        'ParamBreath': lambda t: 0.5 + 0.5 * math.sin(2 * PI * t / 1.2),
    }
motion('walk', 20.0, wrap(20.0, walk_curves(), a=0.3), step=0.05)
# 停下喘口气：身子一下一下塌，张嘴，手撑一下
motion('pant', 1.8, {
    'ParamBodyAngleY': lambda t: -3.5 * abs(math.sin(2 * PI * t / 0.9)) * math.sin(PI * t / 1.8),
    'ParamAngleY': lambda t: -6 * math.sin(PI * t / 1.8),
    'ParamMouthOpenY': lambda t: 0.6 * math.sin(PI * t / 1.8),
    'ParamArmLB': lambda t: 4 * math.sin(PI * t / 1.8),
    'ParamArmRB': lambda t: 4 * math.sin(PI * t / 1.8),
    'ParamFinL': lambda t: -4 * math.sin(PI * t / 1.8),
    'ParamFinR': lambda t: -4 * math.sin(PI * t / 1.8),
})

# 被拎着（拖拽时一直播）：手举过头像被提着领子，一开始晃几下然后慢慢稳住，腿一直轻轻荡
def hang_curves():
    dec = lambda t: math.exp(-t * 0.9)
    return {
        'ParamArmLA': lambda t: 9.5 + 0.5 * math.sin(2 * PI * t / 1.7),
        'ParamArmRA': lambda t: 9.5 + 0.5 * math.sin(2 * PI * t / 1.7 + 1),
        'ParamArmLB': lambda t: 2.0,
        'ParamArmRB': lambda t: 2.0,
        'ParamAngleZ': lambda t: 14 * math.sin(2 * PI * t / 0.7) * dec(t) + 3 * math.sin(2 * PI * t / 2.3),
        'ParamAngleX': lambda t: 8 * math.sin(2 * PI * t / 0.9) * dec(t),
        'ParamAngleY': lambda t: -4 + 2 * math.sin(2 * PI * t / 2.9),
        'ParamBodyAngleZ': lambda t: 7 * math.sin(2 * PI * t / 0.7) * dec(t) + 2.5 * math.sin(2 * PI * t / 2.3),
        'ParamLegL': lambda t: 8 * math.sin(2 * PI * t / 0.5) * dec(t) + 3.5 * math.sin(2 * PI * t / 1.6),
        'ParamLegR': lambda t: -8 * math.sin(2 * PI * t / 0.5) * dec(t) + 3.5 * math.sin(2 * PI * t / 1.6 + 0.9),
        'ParamBodyAngleY': lambda t: 3.0,
        'ParamAhoge': lambda t: 8 * math.sin(2 * PI * t / 0.45) * dec(t),
        'ParamFinL': lambda t: -5 + 6 * math.sin(2 * PI * t / 0.5) * dec(t),
        'ParamFinR': lambda t: -5 - 6 * math.sin(2 * PI * t / 0.5) * dec(t),
        'ParamEyeBallY': lambda t: -0.4,
    }
motion('hang', 20.0, wrap(20.0, hang_curves(), a=0.25), step=0.05)
# 掉下去：手举高、腿张开蹬、仰头，呆毛耳鳍被风吹起
motion('fall', 3.0, {
    'ParamArmLA': lambda t: 10.0,
    'ParamArmRA': lambda t: 10.0,
    'ParamLegL': lambda t: 6 + 3 * math.sin(2 * PI * t / 0.35),
    'ParamLegR': lambda t: 6 - 3 * math.sin(2 * PI * t / 0.35),
    'ParamAngleY': lambda t: 9.0,
    'ParamAngleZ': lambda t: 4 * math.sin(2 * PI * t / 0.6),
    'ParamBodyAngleY': lambda t: 6.0,
    'ParamAhoge': lambda t: 10.0,
    'ParamFinL': lambda t: 10.0,
    'ParamFinR': lambda t: 10.0,
    'ParamEyeLOpen': lambda t: 1.0,
    'ParamEyeROpen': lambda t: 1.0,
    'ParamMouthOpenY': lambda t: 0.8,
    'ParamMouthForm': lambda t: 1.0,
}, step=0.05)
# 落地：蹲下去弹一下再站直，手放下，呆毛耳鳍甩一下
motion('land', 1.0, {
    'ParamBodyAngleY': seq((0.0, 0.1, 6, -10), (0.1, 0.45, -10, 2), (0.45, 0.75, 2, -1), (0.75, 1.0, -1, 0)),
    'ParamLegL': seq((0.0, 0.1, 6, 4), (0.1, 0.6, 4, 0)),
    'ParamLegR': seq((0.0, 0.1, 6, 4), (0.1, 0.6, 4, 0)),
    'ParamArmLA': seq((0.0, 0.12, 10, 2), (0.12, 0.7, 2, 0)),
    'ParamArmRA': seq((0.0, 0.12, 10, 2), (0.12, 0.7, 2, 0)),
    'ParamArmLB': seq((0.0, 0.12, 0, 4), (0.12, 0.7, 4, 0)),
    'ParamArmRB': seq((0.0, 0.12, 0, 4), (0.12, 0.7, 4, 0)),
    'ParamAngleY': seq((0.0, 0.1, 9, -8), (0.1, 0.5, -8, 2), (0.5, 1.0, 2, 0)),
    'ParamAhoge': lambda t: 10 * math.cos(2 * PI * t / 0.4) * math.exp(-t * 3),
    'ParamFinL': lambda t: 10 * math.cos(2 * PI * t / 0.45) * math.exp(-t * 3),
    'ParamFinR': lambda t: 10 * math.cos(2 * PI * t / 0.45) * math.exp(-t * 3),
    'ParamEyeLOpen': seq((0.0, 0.1, 1, 0.2), (0.3, 0.6, 0.2, 1)),
    'ParamEyeROpen': seq((0.0, 0.1, 1, 0.2), (0.3, 0.6, 0.2, 1)),
})

# ======================= 表情里加耳鳍 / 呆毛 =======================
A = 'Add'
FINS = {
    'happy': 7, 'smug': 3, 'angry': 4, 'shy': -4, 'sleepy': -8, 'surprised': 10, 'pout': -7,
}
AHOGE = {'surprised': 8, 'sleepy': -5, 'pout': -4, 'angry': 5}
for name, v in FINS.items():
    p = OUT / 'expressions' / f'{name}.exp3.json'
    d = json.load(open(p))
    d['Parameters'] = [x for x in d['Parameters'] if x['Id'] not in ('ParamFinL', 'ParamFinR', 'ParamAhoge')]
    d['Parameters'] += [{'Id': 'ParamFinL', 'Value': v, 'Blend': A}, {'Id': 'ParamFinR', 'Value': v, 'Blend': A}]
    if name in AHOGE:
        d['Parameters'].append({'Id': 'ParamAhoge', 'Value': AHOGE[name], 'Blend': A})
    json.dump(d, open(p, 'w'), ensure_ascii=False, indent='\t')

# ======================= model3.json =======================
IDLE = ['idle_sway', 'idle_look', 'idle_think', 'idle_fidget', 'idle_rock', 'idle_peek']
ACTS = {'Wave': ('wave', 0.25, 0.4), 'Hop': ('hop', 0.12, 0.3), 'Cheer': ('cheer', 0.2, 0.4), 'Tilt': ('tilt', 0.3, 0.4),
        'Stretch': ('stretch', 0.4, 0.6), 'Flinch': ('flinch', 0.05, 0.3), 'Nod': ('nod', 0.2, 0.4), 'Shake': ('shake', 0.2, 0.4),
        'Swing': ('swing', 0.1, 0.5), 'Shy': ('shy', 0.3, 0.5), 'Slump': ('slump', 0.5, 0.8), 'Kick': ('kick', 0.25, 0.4),
        'Walk': ('walk', 0.25, 0.3), 'Pant': ('pant', 0.2, 0.5),
        'Hang': ('hang', 0.15, 0.3), 'Fall': ('fall', 0.1, 0.1), 'Land': ('land', 0.0, 0.4)}
motions = {'Idle': [{'File': f'motions/{n}.motion3.json', 'FadeInTime': 0.8, 'FadeOutTime': 0.8} for n in IDLE]}
for g, (n, fi, fo) in ACTS.items():
    motions[g] = [{'File': f'motions/{n}.motion3.json', 'FadeInTime': fi, 'FadeOutTime': fo}]
for mj in OUT.glob('*.model3.json'):
    d = json.load(open(mj))
    d['FileReferences']['Motions'] = motions
    json.dump(d, open(mj, 'w'), ensure_ascii=False, indent='\t')
print('motions:', sorted(p.stem.replace('.motion3', '') for p in MO.glob('*.json')))
