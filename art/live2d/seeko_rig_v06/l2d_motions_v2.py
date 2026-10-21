"""希可的动作 v2：头跟着身体一起动（同一个节奏、头稍微慢半拍、幅度大一点），
待机分几段随机播放，外加挥手、蹦一下、歪头、伸懒腰、缩一下、点头、摇头、甩头。
输出到 src/live2d/seeko/motions/，并改写 model3.json 的 Motions。"""
import json, math
from pathlib import Path

OUT = Path('/home/claude/zhixu-whale-maid-pet/src/live2d/seeko')
M = OUT / 'motions'
for f in M.glob('*.motion3.json'):
    f.unlink()

DT = 1 / 15  # 每秒 15 个点，线性连起来足够顺


def ease(x):  # 0→1 平滑
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


def env(t, dur, a=0.4, b=0.4):  # 开头结尾淡入淡出，动作衔接不跳
    return ease(t / a) * ease((dur - t) / b)


# 这些参数每个动作都写全（没用到的就是 0），
# 这样上一个动作留下的值会在下一个动作淡入时被盖掉，不会一直举着手
POSE = ['ParamAngleX', 'ParamAngleY', 'ParamAngleZ', 'ParamBodyAngleX', 'ParamBodyAngleZ', 'ParamArmLA', 'ParamArmRA',
        'ParamEyeBallX', 'ParamEyeBallY', 'ParamBrowLY', 'ParamBrowRY', 'ParamMouthForm']


def write(name, dur, curves, loop=False):
    for pid in POSE:  # 所有动作都写全，淡入时把上一个动作留下的值平滑拉回来
        curves.setdefault(pid, lambda t: 0.0)
    out, segs, pts = [], 0, 0
    n = max(2, int(round(dur / DT)))
    for pid, f in curves.items():
        ts = [dur * i / n for i in range(n + 1)]
        s = [0.0, round(f(0.0), 4)]
        for t in ts[1:]:
            s += [0, round(t, 4), round(f(t), 4)]
        out.append({'Target': 'Parameter', 'Id': pid, 'Segments': s})
        segs += n
        pts += n + 1
    m = {'Version': 3, 'Meta': {'Duration': dur, 'Fps': 30, 'Loop': loop, 'AreBeziersRestricted': True,
                                'CurveCount': len(out), 'TotalSegmentCount': segs, 'TotalPointCount': pts,
                                'UserDataCount': 0, 'TotalUserDataSize': 0}, 'Curves': out}
    (M / f'{name}.motion3.json').write_text(json.dumps(m))


sin, pi = math.sin, math.pi
breath = lambda per: (lambda t: 0.5 - 0.5 * math.cos(2 * pi * t / per))

# ---------- 待机（几段轮流随机播放；首尾都回到 0，衔接顺） ----------
D = 8.0
# 1. 轻轻左右摇：身体先动，头跟着、慢半拍、幅度大一点；手臂随身体晃
w = 2 * pi / D
E = lambda t: env(t, D, 1.0, 1.0)
write('idle_sway', D, {
    'ParamBreath': breath(4),
    'ParamBodyAngleZ': lambda t: 4 * sin(w * t) * E(t),
    'ParamAngleZ': lambda t: 7 * sin(w * t - 0.5) * E(t),
    'ParamBodyAngleX': lambda t: 2.5 * sin(w * t + 0.8) * E(t),
    'ParamAngleX': lambda t: 5 * sin(w * t + 0.4) * E(t),
    'ParamArmLA': lambda t: -1.2 * sin(w * t - 0.3) * E(t),
    'ParamArmRA': lambda t: 1.2 * sin(w * t - 0.3) * E(t),
})
# 2. 东张西望：先看左边再看右边，眼睛先到、头再跟上
D2 = 6.0
def look(t, amp, lag):
    a = env(t - lag, D2 - lag, 0.6, 0.6)
    return amp * sin(2 * pi * (t - lag) / D2) * a if t > lag else 0.0
write('idle_look', D2, {
    'ParamBreath': breath(3),
    'ParamEyeBallX': lambda t: look(t, 0.9, 0.0),
    'ParamAngleX': lambda t: look(t, 18, 0.25),
    'ParamBodyAngleX': lambda t: look(t, 4, 0.45),
    'ParamAngleY': lambda t: 4 * sin(2 * pi * t / D2 * 2) * env(t, D2),
})
# 3. 歪头想事情：慢慢歪过去、眼睛往上看、停一下、回来
D3 = 5.0
tilt = lambda t: ease(t / 1.2) * ease((D3 - t) / 1.2)
write('idle_think', D3, {
    'ParamBreath': breath(5),
    'ParamAngleZ': lambda t: 14 * tilt(t),
    'ParamAngleY': lambda t: 8 * tilt(t),
    'ParamEyeBallY': lambda t: 0.7 * tilt(t),
    'ParamEyeBallX': lambda t: 0.4 * tilt(t),
    'ParamBodyAngleZ': lambda t: 3 * tilt(t),
    'ParamBrowLY': lambda t: 0.6 * tilt(t),
    'ParamBrowRY': lambda t: 0.6 * tilt(t),
})
# 4. 晃手：两只手轻轻前后摆，身体跟着点节奏
D4 = 6.0
write('idle_swing', D4, {
    'ParamBreath': breath(3),
    'ParamArmLA': lambda t: 2.5 * sin(2 * pi * t / 1.5) * env(t, D4, 0.8, 0.8),
    'ParamArmRA': lambda t: -2.5 * sin(2 * pi * t / 1.5) * env(t, D4, 0.8, 0.8),
    'ParamBodyAngleZ': lambda t: 2.5 * sin(2 * pi * t / 3) * env(t, D4, 0.8, 0.8),
    'ParamAngleZ': lambda t: 4 * sin(2 * pi * t / 3 - 0.5) * env(t, D4, 0.8, 0.8),
})

# ---------- 动作 ----------
# 挥手：右手举起来来回摆，头歪向挥手那边，身体一起晃
DW = 2.6
up = lambda t: ease(t / 0.35) * ease((DW - t) / 0.45)
write('wave', DW, {
    'ParamArmRA': lambda t: up(t) * (8.5 + 1.5 * sin(2 * pi * t / 0.45)),
    'ParamArmLA': lambda t: -1.5 * up(t),
    'ParamAngleZ': lambda t: -9 * up(t),
    'ParamBodyAngleZ': lambda t: -3 * up(t) + 1.5 * sin(2 * pi * t / 0.9) * up(t),
    'ParamAngleX': lambda t: -6 * up(t),
    'ParamEyeLSmile': lambda t: up(t),
    'ParamEyeRSmile': lambda t: up(t),
})
# 蹦一下（开心）：两手往上一甩，身体往两边扭（上下跳交给 CSS）
DH = 1.2
pulse = lambda t, c, w_: math.exp(-((t - c) / w_) ** 2) * ease(t / 0.1) * ease((DH - t) / 0.2)
write('hop', DH, {
    'ParamArmLA': lambda t: 7 * pulse(t, 0.35, 0.18),
    'ParamArmRA': lambda t: 7 * pulse(t, 0.35, 0.18),
    'ParamAngleY': lambda t: 10 * pulse(t, 0.35, 0.2) - 5 * pulse(t, 0.8, 0.15),
    'ParamBodyAngleZ': lambda t: 3 * sin(2 * pi * t / 0.6) * env(t, DH, 0.2, 0.3),
})
# 歪头疑惑
DT2 = 1.8
tt = lambda t: ease(t / 0.35) * ease((DT2 - t) / 0.5)
write('tilt', DT2, {
    'ParamAngleZ': lambda t: 16 * tt(t),
    'ParamAngleX': lambda t: 6 * tt(t),
    'ParamBodyAngleZ': lambda t: 4 * tt(t),
    'ParamEyeBallY': lambda t: 0.5 * tt(t),
    'ParamBrowLY': lambda t: 0.8 * tt(t),
    'ParamBrowRY': lambda t: 0.8 * tt(t),
})
# 伸懒腰 + 打哈欠（犯困）
DS = 3.6
st = lambda t: ease((t - 0.2) / 0.9) * ease((DS - t) / 0.9)
write('stretch', DS, {
    'ParamArmLA': lambda t: 10 * st(t),
    'ParamArmRA': lambda t: 10 * st(t),
    'ParamAngleY': lambda t: 14 * st(t),
    'ParamAngleZ': lambda t: 6 * st(t) * sin(2 * pi * t / DS),
    'ParamBodyAngleZ': lambda t: 3 * st(t) * sin(2 * pi * t / DS),
    'ParamEyeLOpen': lambda t: 1 - st(t),
    'ParamEyeROpen': lambda t: 1 - st(t),
    'ParamMouthForm': lambda t: ease((t - 0.1) / 0.3) * ease((DS - t) / 0.3),
    'ParamMouthOpenY': lambda t: 0.9 * st(t),
})
# 被戳/吓到：一缩，手往里收，头往后
DF = 0.9
fl = lambda t: math.exp(-t * 4.5) * ease(t / 0.06) * ease((DF - t) / 0.25)
write('flinch', DF, {
    'ParamAngleY': lambda t: -10 * fl(t),
    'ParamAngleX': lambda t: -8 * fl(t),
    'ParamBodyAngleZ': lambda t: -5 * fl(t) * math.cos(2 * pi * t / 0.45),
    'ParamArmLA': lambda t: -8 * fl(t),
    'ParamArmRA': lambda t: -8 * fl(t),
    'ParamEyeLOpen': lambda t: 1 - 0.6 * fl(t),
    'ParamEyeROpen': lambda t: 1 - 0.6 * fl(t),
})
# 点头两下
write('nod', 1.6, {
    'ParamAngleY': lambda t: -14 * sin(pi * t / 0.8) ** 2,
    'ParamBodyAngleZ': lambda t: 0.0,
    'ParamEyeBallY': lambda t: -0.3 * sin(pi * t / 0.8) ** 2,
})
# 摇头（生气、不要）
write('shake', 1.6, {
    'ParamAngleX': lambda t: 22 * sin(2 * pi * t / 0.55) * sin(pi * t / 1.6),
    'ParamBodyAngleX': lambda t: 4 * sin(2 * pi * t / 0.55 - 0.5) * sin(pi * t / 1.6),
    'ParamArmLA': lambda t: -4 * sin(pi * t / 1.6),
    'ParamArmRA': lambda t: -4 * sin(pi * t / 1.6),
})
# 被拎起来：手脚乱挥、头甩，头发跟着物理甩
DG = 2.4
write('swing', DG, {
    'ParamAngleZ': lambda t: 20 * sin(2 * pi * t / 0.7) * math.exp(-t * 0.6),
    'ParamAngleX': lambda t: 15 * sin(2 * pi * t / 0.9) * math.exp(-t * 0.6),
    'ParamBodyAngleZ': lambda t: 8 * sin(2 * pi * t / 0.7 - 0.6) * math.exp(-t * 0.6),
    'ParamArmLA': lambda t: 6 + 4 * sin(2 * pi * t / 0.35),
    'ParamArmRA': lambda t: 6 - 4 * sin(2 * pi * t / 0.35),
}, loop=True)

model = json.loads((OUT / 'seeko.model3.json').read_text())
fr = model['FileReferences']
mo = lambda n, fi=0.4, fo=0.4: {'File': f'motions/{n}.motion3.json', 'FadeInTime': fi, 'FadeOutTime': fo}
fr['Motions'] = {
    'Idle': [mo('idle_sway', 0.8, 0.8), mo('idle_look', 0.8, 0.8), mo('idle_think', 0.8, 0.8), mo('idle_swing', 0.8, 0.8)],
    'Wave': [mo('wave', 0.25, 0.4)],
    'Hop': [mo('hop', 0.15, 0.3)],
    'Tilt': [mo('tilt', 0.3, 0.4)],
    'Stretch': [mo('stretch', 0.4, 0.6)],
    'Flinch': [mo('flinch', 0.05, 0.3)],
    'Nod': [mo('nod', 0.2, 0.3)],
    'Shake': [mo('shake', 0.2, 0.3)],
    'Swing': [mo('swing', 0.2, 0.5)],
}
(OUT / 'seeko.model3.json').write_text(json.dumps(model, ensure_ascii=False, indent='\t'))
print(sorted(p.name for p in M.iterdir()))
