"""v12 骨架的第一批动作（9 个 + 下落），用 motionlib 手调节奏。
用法：python3 make_motions_v3.py <运行时目录>   → 写 motions/*.motion3.json，并把分组写进 seeko.model3.json

v12 参数口径（都是 -10~10 或 0~10 的刻度）：
  ArmLA/RA  +k = 抬 11k°（10 = 举过头 110°），-k = 往后 3k°
  ArmLB/RB  +k = 小臂往身体里弯 12k°，-k = 小臂往外/往上抬 12k°            WristL/R ±k = 手掌 3k°      HandL/R 0 拳 1 张
  LegL/R    +k = 大腿往外 3k°         KneeL/R +k = 小腿 6k°
  BodyAngleY + 踮起 - 蹲下；BodyStretch 0~1 全身拉长；SkirtX/Y、Apron、HairBack1/2/3、HairBackY 主要交给物理
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from motionlib import Motion, body_follow, body_release  # noqa: E402

OUT = Path(sys.argv[1])
MO = OUT / 'motions'
MO.mkdir(exist_ok=True)
for old in MO.glob('*.motion3.json'):
    old.unlink()
groups = {}


def reg(group, m, **fade):
    e = m.write(MO)
    e.update(fade)
    groups.setdefault(group, []).append(e)


# ---------- 待机 1：呼吸 + 偶尔瞟一眼（6 s 循环）----------
m = Motion('idle_breathe', 6.0, loop=True, fade_in=0.8, fade_out=0.8)
br = m.track('ParamBreath')
for t, v, e in [(0, 0, 'linear'), (1.6, 1, 'inout'), (3.4, 0, 'inout'), (4.8, 1, 'inout'), (6.0, 0, 'inout')]:
    br.key(t, v, e)
# 呼吸带着身子和肩一点点
m.track('ParamBodyAngleY').key(0, 0, 'linear').key(1.6, 0.6, 'inout').key(3.4, 0, 'inout').key(4.8, 0.6, 'inout').key(6.0, 0, 'inout')
# 头：不是正弦，是「慢慢偏一点、停、再回来」
hz = m.track('ParamAngleZ')
hz.key(0, 0, 'linear').key(1.2, 2.5, 'inout').key(2.6, 2.5, 'linear').key(3.3, -1.5, 'inout').key(5.0, -1.5, 'linear').key(6.0, 0, 'inout')
# 3.2 s 瞟一眼右边再回来（快去慢回）
hx = m.track('ParamAngleX')
hx.key(0, 0, 'linear').key(3.0, 0, 'linear').key(3.25, 9, 'out').key(4.2, 9, 'linear').key(4.9, 0, 'inout')
m.track('ParamEyeBallX').key(0, 0, 'linear').key(3.0, 0, 'linear').key(3.15, 0.6, 'out').key(4.2, 0.6, 'linear').key(4.8, 0, 'inout')
reg('Idle', m)

# ---------- 待机 2：换重心（7 s 循环）----------
m = Motion('idle_shift', 7.0, loop=True, fade_in=0.8, fade_out=0.8)
bz = m.track('ParamBodyAngleZ')
bz.key(0, 0, 'linear').key(0.9, -1, 'inout').key(1.4, 4, 'back').key(3.6, 4, 'linear').key(4.2, 5, 'inout').key(4.8, -3, 'back').key(6.2, -3, 'linear').key(7.0, 0, 'inout')
m.track('ParamAngleZ').key(0, 0, 'linear').key(1.0, 0.5, 'inout').key(1.6, -5, 'back').key(3.7, -5, 'linear').key(5.0, 4, 'back').key(6.3, 4, 'linear').key(7.0, 0, 'inout')
m.track('ParamBodyAngleX').key(0, 0, 'linear').key(1.4, 3, 'inout').key(3.6, 3, 'linear').key(4.8, -2, 'inout').key(7.0, 0, 'inout')
m.track('ParamLegL').key(0, 0, 'linear').key(1.4, 1.5, 'inout').key(3.6, 1.5, 'linear').key(4.8, -0.5, 'inout').key(7.0, 0, 'inout')
m.track('ParamLegR').key(0, 0, 'linear').key(1.4, 0.5, 'inout').key(3.6, 0.5, 'linear').key(4.8, -1.5, 'inout').key(7.0, 0, 'inout')
m.track('ParamBreath').key(0, 0, 'linear').key(1.8, 1, 'inout').key(3.6, 0, 'inout').key(5.4, 1, 'inout').key(7.0, 0, 'inout')
m.track('ParamArmLA').key(0, 0, 'linear').key(1.4, -0.6, 'inout').key(4.8, 0.3, 'inout').key(7.0, 0, 'inout')
m.track('ParamArmRA').key(0, 0, 'linear').key(1.4, 0.3, 'inout').key(4.8, -0.6, 'inout').key(7.0, 0, 'inout')
reg('Idle', m)

# ---------- 挥手（2.8 s）----------
m = Motion('wave', 2.8, fade_in=0.2, fade_out=0.5)
arm = m.track('ParamArmLA')
t = arm.hit(0.1, 0, 6, antic=0.12, rise=0.2, over=0.12, antic_k=0.12, over_k=0.08, pause=0.05)
el = m.track('ParamArmLB')
el.key(0.1, 0, 'linear').key(0.2, 1, 'inout').key(0.46, -8.5, 'out')
m.track('ParamHandL').key(0, 0, 'hold').key(0.3, 1, 'hold').key(2.35, 1, 'hold').key(2.4, 0, 'hold')
# 手腕摆：不等间隔、越来越小
wr = m.track('ParamWristL')
wr.key(t, 0, 'linear')
for d, a in [(0.15, 8), (0.14, -7), (0.15, 7), (0.13, -5), (0.15, 4), (0.14, -2)]:
    t += d
    wr.key(t, a, 'inout')
wr.key(t + 0.2, 0, 'out')
arm.key(t + 0.25, 6, 'linear').key(t + 0.95, 0, 'inout')
el.key(t + 0.3, -8.5, 'linear').key(t + 0.85, 0, 'inout')
body_follow(m, 0.08, 3.5, head_k=1.3, delay=0.07, dur=0.28)
body_release(m, t + 0.3, 0.7)
ra = m.track('ParamArmRA')
ra.hit(0.15, 0, -1.5, antic=0, rise=0.3, over=0.1, over_k=0.1)
ra.release(t + 0.3, 0, 0.6)
m.track('ParamAngleX').key(0.1, 0, 'linear').key(0.45, -6, 'out').key(t + 0.3, -6, 'linear').key(t + 0.9, 0, 'inout')
reg('Wave', m)

# ---------- 蹦一下（1.15 s）----------
m = Motion('hop', 1.15, fade_in=0.1, fade_out=0.4)
by = m.track('ParamBodyAngleY')
by.key(0, 0, 'linear').key(0.18, -6, 'in').key(0.22, -6, 'linear').key(0.36, 10, 'out').key(0.5, 10, 'linear').key(0.64, -7, 'in').key(0.78, 2, 'out').key(0.95, -1, 'inout').key(1.15, 0, 'out')
m.track('ParamBodyStretch').key(0, 0, 'linear').key(0.2, 0, 'linear').key(0.36, 0.35, 'out').key(0.5, 0.35, 'linear').key(0.64, 0, 'in')
m.track('ParamAngleY').key(0, 0, 'linear').key(0.18, -8, 'in').key(0.4, 8, 'out').key(0.64, -6, 'in').key(0.8, 2, 'out').key(1.15, 0, 'inout')
for pid, s in (('ParamArmLA', 1), ('ParamArmRA', 1)):
    m.track(pid).key(0, 0, 'linear').key(0.18, -2.5, 'in').key(0.38, 5, 'out').key(0.52, 5, 'linear').key(0.7, 1, 'in').key(0.85, 2, 'out').key(1.15, 0, 'inout')
for pid in ('ParamKneeL', 'ParamKneeR'):
    m.track(pid).key(0.2, 0, 'linear').key(0.4, 4, 'out').key(0.55, 4, 'linear').key(0.64, 0, 'in')
m.track('ParamLegL').key(0.2, 0, 'linear').key(0.4, 2, 'out').key(0.64, 0, 'in')
m.track('ParamLegR').key(0.2, 0, 'linear').key(0.4, -2, 'out').key(0.64, 0, 'in')
m.track('ParamSkirtY').key(0, 0, 'linear').key(0.18, 0.3, 'in').key(0.4, -0.8, 'out').key(0.66, 1, 'in').key(0.85, -0.2, 'out').key(1.15, 0, 'inout')
m.track('ParamHairBackY').key(0, 0, 'linear').key(0.2, -0.3, 'in').key(0.45, 1, 'out').key(0.7, -0.6, 'in').key(0.95, 0.2, 'out').key(1.15, 0, 'inout')
reg('Hop', m, FadeInTime=0.1, FadeOutTime=0.3)

# ---------- 害羞（摸头反应，2.3 s）----------
m = Motion('shy', 2.3, fade_in=0.25, fade_out=0.6)
for pid in ('ParamArmLA', 'ParamArmRA'):
    tr = m.track(pid)
    tr.hit(0.05, 0, 2.5, antic=0.1, rise=0.26, over=0.12, antic_k=0.2, over_k=0.1)
    tr.key(1.55, 2.5, 'linear').key(2.25, 0, 'inout')
for pid in ('ParamArmLB', 'ParamArmRB'):
    tr = m.track(pid)
    tr.key(0.1, 0, 'linear').key(0.18, 0.8, 'inout').key(0.5, -9.5, 'back').key(1.55, -9.5, 'linear').key(2.2, 0, 'inout')
m.track('ParamAngleZ').key(0, 0, 'linear').key(0.15, -2, 'inout').key(0.5, 11, 'back').key(1.5, 11, 'linear').key(2.2, 0, 'inout')
m.track('ParamAngleY').key(0, 0, 'linear').key(0.5, -6, 'inout').key(1.5, -6, 'linear').key(2.2, 0, 'inout')
m.track('ParamBodyAngleZ').key(0, 0, 'linear').key(0.55, 3, 'inout').key(1.55, 3, 'linear').key(2.25, 0, 'inout')
m.track('ParamBodyAngleY').key(0, 0, 'linear').key(0.5, -1.5, 'inout').key(1.5, -1.5, 'linear').key(2.2, 0, 'inout')
reg('Shy', m)

# ---------- 吓一跳（0.9 s）----------
m = Motion('flinch', 0.9, fade_in=0.05, fade_out=0.3)
m.track('ParamAngleY').key(0, 0, 'linear').key(0.08, -13, 'out').key(0.22, -11, 'linear').key(0.55, 3, 'inout').key(0.9, 0, 'out')
m.track('ParamBodyAngleY').key(0, 0, 'linear').key(0.08, -3.5, 'out').key(0.25, -3, 'linear').key(0.6, 0.8, 'inout').key(0.9, 0, 'out')
m.track('ParamBodyAngleX').key(0, 0, 'linear').key(0.08, -3, 'out').key(0.3, -2.5, 'linear').key(0.7, 0, 'inout')
for pid in ('ParamArmLA', 'ParamArmRA'):
    m.track(pid).key(0, 0, 'linear').key(0.08, 4.5, 'out').key(0.25, 4, 'linear').key(0.6, -0.5, 'inout').key(0.9, 0, 'out')
for pid in ('ParamArmLB', 'ParamArmRB'):
    m.track(pid).key(0, 0, 'linear').key(0.08, 3, 'out').key(0.25, 3, 'linear').key(0.6, 0, 'inout')
m.track('ParamFinL').key(0, 0, 'linear').key(0.08, 9, 'out').key(0.4, 8, 'linear').key(0.9, 0, 'inout')
m.track('ParamFinR').key(0, 0, 'linear').key(0.08, 9, 'out').key(0.4, 8, 'linear').key(0.9, 0, 'inout')
reg('Flinch', m, FadeInTime=0.05, FadeOutTime=0.3)

# ---------- 拎起来（4 s 循环：被提着领子，晃荡）----------
m = Motion('hang', 4.0, loop=True, fade_in=0.25, fade_out=0.4)
m.track('ParamBodyStretch').key(0, 1, 'linear').key(4.0, 1, 'linear')
m.track('ParamBodyAngleY').key(0, -4, 'linear').key(1.3, -3, 'inout').key(2.6, -4.5, 'inout').key(4.0, -4, 'inout')
# 手臂软软地垂着、跟着晃（被提着领子，肩膀耸起靠 Stretch）
m.track('ParamArmLA').key(0, 1.5, 'linear').key(1.1, 0.3, 'inout').key(2.3, 2.2, 'inout').key(3.3, 0.8, 'inout').key(4.0, 1.5, 'inout')
m.track('ParamArmRA').key(0, 0.8, 'linear').key(0.9, 2.0, 'inout').key(2.0, 0.2, 'inout').key(3.2, 1.8, 'inout').key(4.0, 0.8, 'inout')
m.track('ParamArmLB').key(0, 0.8, 'linear').key(2.0, 0.3, 'inout').key(4.0, 0.8, 'inout')
m.track('ParamArmRB').key(0, 0.4, 'linear').key(2.0, 0.9, 'inout').key(4.0, 0.4, 'inout')
m.track('ParamHandL').key(0, 1, 'hold').key(4.0, 1, 'hold')
m.track('ParamHandR').key(0, 1, 'hold').key(4.0, 1, 'hold')
# 腿：不受控地晃，两条腿节奏不同
ll = m.track('ParamLegL')
ll.key(0, 2, 'linear').key(0.7, -3, 'inout').key(1.6, 3, 'inout').key(2.2, -1, 'inout').key(3.1, 2.5, 'inout').key(4.0, 2, 'inout')
lr = m.track('ParamLegR')
lr.key(0, -1.5, 'linear').key(0.9, 2.5, 'inout').key(1.7, -2.5, 'inout').key(2.8, 1, 'inout').key(4.0, -1.5, 'inout')
m.track('ParamKneeL').key(0, 4, 'linear').key(0.7, 7, 'inout').key(1.6, 3, 'inout').key(2.6, 6, 'inout').key(4.0, 4, 'inout')
m.track('ParamKneeR').key(0, 5, 'linear').key(0.9, 2, 'inout').key(1.9, 7, 'inout').key(3.0, 4, 'inout').key(4.0, 5, 'inout')
m.track('ParamSkirtY').key(0, -0.7, 'linear').key(4.0, -0.7, 'linear')
m.track('ParamHairBackY').key(0, 0.4, 'linear').key(4.0, 0.4, 'linear')
m.track('ParamAngleY').key(0, -6, 'linear').key(1.2, -9, 'inout').key(2.4, 2, 'inout').key(3.2, -4, 'inout').key(4.0, -6, 'inout')
m.track('ParamAngleZ').key(0, 3, 'linear').key(1.5, -4, 'inout').key(3.0, 3, 'inout').key(4.0, 3, 'inout')
m.track('ParamBodyAngleZ').key(0, 1, 'linear').key(1.5, -2, 'inout').key(3.0, 1.5, 'inout').key(4.0, 1, 'inout')
m.track('ParamFinL').key(0, -6, 'linear').key(4.0, -6, 'linear')
m.track('ParamFinR').key(0, -6, 'linear').key(4.0, -6, 'linear')
m.track('ParamAhoge').key(0, -5, 'linear').key(2, -7, 'inout').key(4.0, -5, 'inout')
reg('Hang', m)

# ---------- 下落（1 s 循环）----------
m = Motion('fall', 1.0, loop=True, fade_in=0.15, fade_out=0.15)
m.track('ParamBodyStretch').key(0, 0.7, 'linear').key(1.0, 0.7, 'linear')
for pid in ('ParamArmLA', 'ParamArmRA'):
    m.track(pid).key(0, 10, 'linear').key(0.5, 9, 'inout').key(1.0, 10, 'inout')
m.track('ParamLegL').key(0, 4, 'linear').key(0.5, 2, 'inout').key(1.0, 4, 'inout')
m.track('ParamLegR').key(0, -4, 'linear').key(0.5, -2, 'inout').key(1.0, -4, 'inout')
m.track('ParamSkirtY').key(0, -1, 'linear').key(1.0, -1, 'linear')
m.track('ParamHairBackY').key(0, 1, 'linear').key(1.0, 1, 'linear')
m.track('ParamAngleY').key(0, 10, 'linear').key(1.0, 10, 'linear')
m.track('ParamFinL').key(0, 10, 'linear').key(1.0, 10, 'linear')
m.track('ParamFinR').key(0, 10, 'linear').key(1.0, 10, 'linear')
reg('Fall', m, FadeInTime=0.15, FadeOutTime=0.15)

# ---------- 落地（1.1 s）----------
m = Motion('land', 1.1, fade_in=0.05, fade_out=0.4)
m.track('ParamBodyStretch').key(0, 0.7, 'linear').key(0.1, 0, 'in')
m.track('ParamBodyAngleY').key(0, 0, 'linear').key(0.12, -9, 'in').key(0.22, -9, 'linear').key(0.42, 2, 'out').key(0.6, -1.5, 'inout').key(0.8, 0.5, 'inout').key(1.1, 0, 'out')
m.track('ParamAngleY').key(0, 6, 'linear').key(0.14, -12, 'in').key(0.26, -12, 'linear').key(0.5, 4, 'out').key(0.75, -1, 'inout').key(1.1, 0, 'out')
for pid in ('ParamArmLA', 'ParamArmRA'):
    m.track(pid).key(0, 9, 'linear').key(0.12, 3, 'in').key(0.3, 3, 'linear').key(0.5, 4.5, 'out').key(1.1, 0, 'inout')
m.track('ParamLegL').key(0, 3, 'linear').key(0.12, 3.5, 'linear').key(0.5, 0, 'inout')
m.track('ParamLegR').key(0, -3, 'linear').key(0.12, -3.5, 'linear').key(0.5, 0, 'inout')
m.track('ParamSkirtY').key(0, -1, 'linear').key(0.15, 1, 'out').key(0.45, -0.3, 'inout').key(0.7, 0.3, 'inout').key(1.1, 0, 'inout')
m.track('ParamHairBackY').key(0, 1, 'linear').key(0.14, -1, 'in').key(0.4, 0.4, 'out').key(0.7, -0.2, 'inout').key(1.1, 0, 'inout')
m.track('ParamAhoge').key(0, 8, 'linear').key(0.14, -9, 'in').key(0.4, 5, 'out').key(0.7, -2, 'inout').key(1.1, 0, 'inout')
reg('Land', m, FadeInTime=0.05, FadeOutTime=0.4)

# ---------- 走路（循环 0.84 s = 两步）----------
m = Motion('walk', 0.84, loop=True, fade_in=0.25, fade_out=0.25)
T = 0.42
# 腿：摆到前面快、收回去慢一点；接触瞬间（0、0.42）身子最低
ll, lr = m.track('ParamLegL'), m.track('ParamLegR')
ll.key(0, 5, 'linear').key(0.16, 1, 'in').key(T, -5, 'out').key(T + 0.16, -1, 'in').key(0.84, 5, 'out')
lr.key(0, -5, 'linear').key(0.16, -1, 'in').key(T, 5, 'out').key(T + 0.16, 1, 'in').key(0.84, -5, 'out')
# 膝：腿往后收时弯一下
m.track('ParamKneeL').key(0, 0, 'linear').key(0.1, 0, 'linear').key(0.28, 3.5, 'out').key(T, 0, 'in').key(0.84, 0, 'linear')
m.track('ParamKneeR').key(0, 0, 'linear').key(T + 0.1, 0, 'linear').key(T + 0.28, 3.5, 'out').key(0.84, 0, 'in')
by = m.track('ParamBodyAngleY')
by.key(0, -1.5, 'linear').key(0.12, 1.5, 'out').key(0.3, 1.0, 'linear').key(T, -1.5, 'in').key(T + 0.12, 1.5, 'out').key(T + 0.3, 1.0, 'linear').key(0.84, -1.5, 'in')
m.track('ParamBodyAngleZ').key(0, 1.5, 'linear').key(T, -1.5, 'inout').key(0.84, 1.5, 'inout')
m.track('ParamAngleY').key(0, -1, 'linear').key(0.17, 1.5, 'out').key(T, -1, 'in').key(T + 0.17, 1.5, 'out').key(0.84, -1, 'in')
m.track('ParamAngleX').key(0, 6, 'linear').key(0.84, 6, 'linear')
m.track('ParamAngleZ').key(0, -2, 'linear').key(T, 2, 'inout').key(0.84, -2, 'inout')
m.track('ParamArmLA').key(0, -1.5, 'linear').key(T, 2, 'inout').key(0.84, -1.5, 'inout')
m.track('ParamArmRA').key(0, 2, 'linear').key(T, -1.5, 'inout').key(0.84, 2, 'inout')
m.track('ParamArmLB').key(0, 1, 'linear').key(T, 2.5, 'inout').key(0.84, 1, 'inout')
m.track('ParamArmRB').key(0, 2.5, 'linear').key(T, 1, 'inout').key(0.84, 2.5, 'inout')
m.track('ParamBreath').key(0, 0.3, 'linear').key(T, 0.8, 'inout').key(0.84, 0.3, 'inout')
reg('Walk', m, FadeInTime=0.25, FadeOutTime=0.25)

# ---------- 欢呼（1.6 s）：双手举起来晃两下 ----------
m = Motion('cheer', 1.6, fade_in=0.15, fade_out=0.5)
for pid, sg in (('ParamArmLA', 1), ('ParamArmRA', 1)):
    tr = m.track(pid)
    t = tr.hit(0.05, 0, 9.5, antic=0.12, rise=0.2, over=0.12, antic_k=0.15, over_k=0.08)
    tr.key(1.1, 9.5, 'linear').key(1.6, 0, 'inout')
for pid in ('ParamArmLB', 'ParamArmRB'):
    m.track(pid).key(0.1, 0, 'linear').key(0.4, -3, 'out').key(1.1, -3, 'linear').key(1.55, 0, 'inout')
m.track('ParamHandL').key(0, 0, 'hold').key(0.3, 1, 'hold').key(1.3, 1, 'hold').key(1.35, 0, 'hold')
m.track('ParamHandR').key(0, 0, 'hold').key(0.3, 1, 'hold').key(1.3, 1, 'hold').key(1.35, 0, 'hold')
wl, wr = m.track('ParamWristL'), m.track('ParamWristR')
t = 0.45
wl.key(t, 0, 'linear'); wr.key(t, 0, 'linear')
for d, a in [(0.14, 7), (0.16, -6), (0.15, 6), (0.17, -4)]:
    t += d; wl.key(t, a, 'inout'); wr.key(t, -a, 'inout')
wl.key(t + 0.3, 0, 'out'); wr.key(t + 0.3, 0, 'out')
m.track('ParamBodyAngleY').key(0, 0, 'linear').key(0.15, -3, 'in').key(0.38, 4, 'out').key(0.55, 2, 'inout').key(0.75, 3.5, 'inout').key(1.0, 2, 'inout').key(1.6, 0, 'inout')
m.track('ParamAngleY').key(0, 0, 'linear').key(0.15, -5, 'in').key(0.4, 10, 'out').key(1.1, 8, 'linear').key(1.6, 0, 'inout')
m.track('ParamAngleZ').key(0, 0, 'linear').key(0.5, 4, 'inout').key(0.8, -4, 'inout').key(1.1, 3, 'inout').key(1.6, 0, 'inout')
reg('Cheer', m)

# ---------- 伸懒腰（3.4 s）：手臂举过头、身子拉长、头后仰，停住，松下来 ----------
m = Motion('stretch', 3.4, fade_in=0.3, fade_out=0.6)
for pid in ('ParamArmLA', 'ParamArmRA'):
    m.track(pid).key(0, 0, 'linear').key(0.25, -1, 'inout').key(1.0, 10, 'inout').key(2.2, 10, 'linear').key(2.5, 9, 'inout').key(3.3, 0, 'inout')
for pid in ('ParamArmLB', 'ParamArmRB'):
    m.track(pid).key(0, 0, 'linear').key(1.0, -2, 'inout').key(2.2, -2, 'linear').key(3.3, 0, 'inout')
m.track('ParamBodyStretch').key(0, 0, 'linear').key(0.3, 0, 'linear').key(1.1, 0.8, 'inout').key(2.2, 0.8, 'linear').key(2.6, 0, 'in').key(2.8, 0.1, 'out').key(3.1, 0, 'inout')
m.track('ParamBodyAngleY').key(0, 0, 'linear').key(1.1, 6, 'inout').key(2.2, 6, 'linear').key(2.6, -3, 'in').key(2.9, 0.5, 'out').key(3.4, 0, 'inout')
m.track('ParamAngleY').key(0, 0, 'linear').key(0.3, -3, 'inout').key(1.1, 14, 'inout').key(2.2, 14, 'linear').key(2.6, -6, 'in').key(3.0, 1, 'out').key(3.4, 0, 'inout')
m.track('ParamBodyAngleZ').key(0, 0, 'linear').key(1.1, 3, 'inout').key(2.2, 3, 'linear').key(3.0, 0, 'inout')
m.track('ParamMouthOpenY').key(0, 0, 'linear').key(0.8, 0, 'linear').key(1.2, 0.7, 'inout').key(2.1, 0.7, 'linear').key(2.6, 0, 'inout')
m.track('ParamEyeLOpen').key(0, 1, 'linear').key(0.9, 1, 'linear').key(1.2, 0, 'inout').key(2.3, 0, 'linear').key(2.7, 1, 'inout')
m.track('ParamEyeROpen').key(0, 1, 'linear').key(0.9, 1, 'linear').key(1.2, 0, 'inout').key(2.3, 0, 'linear').key(2.7, 1, 'inout')
reg('Stretch', m)

# ---------- 歪头（1.9 s）：歪过去停一会儿，眼珠跟着 ----------
m = Motion('tilt', 1.9, fade_in=0.2, fade_out=0.5)
m.track('ParamAngleZ').key(0, 0, 'linear').key(0.1, -2, 'inout').key(0.45, 18, 'back').key(1.3, 18, 'linear').key(1.9, 0, 'inout')
m.track('ParamBodyAngleZ').key(0, 0, 'linear').key(0.5, 3, 'inout').key(1.3, 3, 'linear').key(1.9, 0, 'inout')
m.track('ParamAngleX').key(0, 0, 'linear').key(0.5, 5, 'inout').key(1.3, 5, 'linear').key(1.9, 0, 'inout')
m.track('ParamEyeBallX').key(0, 0, 'linear').key(0.35, 0.5, 'out').key(1.3, 0.5, 'linear').key(1.8, 0, 'inout')
m.track('ParamAhoge').key(0, 0, 'linear').key(0.5, -6, 'out').key(0.75, 4, 'inout').key(1.0, -2, 'inout').key(1.3, 0, 'inout')
reg('Tilt', m)

# ---------- 点头（1.4 s）：两下，第二下小 ----------
m = Motion('nod', 1.4, fade_in=0.15, fade_out=0.4)
hy = m.track('ParamAngleY')
hy.key(0, 0, 'linear').key(0.1, 4, 'inout').key(0.3, -14, 'out').key(0.5, 3, 'inout').key(0.75, -9, 'out').key(0.95, 1, 'inout').key(1.4, 0, 'out')
m.track('ParamBodyAngleY').key(0, 0, 'linear').key(0.32, -1.5, 'out').key(0.55, 0.5, 'inout').key(0.78, -1, 'out').key(1.1, 0, 'inout')
m.track('ParamEyeLOpen').key(0, 1, 'linear').key(0.25, 1, 'linear').key(0.32, 0.5, 'out').key(0.5, 1, 'inout')
m.track('ParamEyeROpen').key(0, 1, 'linear').key(0.25, 1, 'linear').key(0.32, 0.5, 'out').key(0.5, 1, 'inout')
reg('Nod', m)

# ---------- 摇头（1.5 s）：三下，幅度递减 ----------
m = Motion('shake', 1.5, fade_in=0.15, fade_out=0.4)
hx = m.track('ParamAngleX')
hx.key(0, 0, 'linear').key(0.12, 6, 'inout').key(0.32, -22, 'out').key(0.55, 18, 'inout').key(0.78, -12, 'inout').key(1.0, 6, 'inout').key(1.5, 0, 'out')
m.track('ParamBodyAngleX').key(0, 0, 'linear').key(0.36, -4, 'out').key(0.6, 3, 'inout').key(0.84, -2, 'inout').key(1.5, 0, 'inout')
m.track('ParamEyeBallX').key(0, 0, 'linear').key(0.3, -0.4, 'out').key(0.55, 0.4, 'inout').key(0.78, -0.3, 'inout').key(1.2, 0, 'inout')
reg('Shake', m)

# ---------- 踢一下（1.4 s）：先收再踢，脚尖带一下 ----------
m = Motion('kick', 1.4, fade_in=0.15, fade_out=0.4)
m.track('ParamLegL').key(0, 0, 'linear').key(0.2, -3, 'in').key(0.42, 8, 'out').key(0.6, 7, 'linear').key(1.1, 0, 'inout')
m.track('ParamKneeL').key(0, 0, 'linear').key(0.2, 5, 'in').key(0.42, 0.5, 'out').key(0.6, 1, 'linear').key(1.1, 0, 'inout')
m.track('ParamLegR').key(0, 0, 'linear').key(0.42, -2, 'out').key(1.1, 0, 'inout')
m.track('ParamBodyAngleZ').key(0, 0, 'linear').key(0.2, 2, 'in').key(0.42, -5, 'out').key(0.6, -4, 'linear').key(1.2, 0, 'inout')
m.track('ParamBodyAngleY').key(0, 0, 'linear').key(0.2, -2, 'in').key(0.42, 1.5, 'out').key(1.0, 0, 'inout')
m.track('ParamAngleZ').key(0, 0, 'linear').key(0.25, -3, 'inout').key(0.5, 6, 'out').key(1.2, 0, 'inout')
m.track('ParamAngleY').key(0, 0, 'linear').key(0.45, -8, 'out').key(0.7, -8, 'linear').key(1.2, 0, 'inout')
m.track('ParamArmLA').key(0, 0, 'linear').key(0.42, 2, 'out').key(1.1, 0, 'inout')
reg('Kick', m)

# ---------- 垂头（3 s）：慢慢塌下去，停住 ----------
m = Motion('slump', 3.0, fade_in=0.4, fade_out=0.8)
m.track('ParamAngleY').key(0, 0, 'linear').key(0.3, 2, 'inout').key(1.2, -22, 'inout').key(2.4, -22, 'linear').key(3.0, -18, 'inout')
m.track('ParamBodyAngleY').key(0, 0, 'linear').key(1.2, -5, 'inout').key(3.0, -5, 'linear')
m.track('ParamBodyAngleX').key(0, 0, 'linear').key(1.3, 2, 'inout').key(3.0, 2, 'linear')
for pid in ('ParamArmLA', 'ParamArmRA'):
    m.track(pid).key(0, 0, 'linear').key(1.2, -1.5, 'inout').key(3.0, -1.5, 'linear')
m.track('ParamFinL').key(0, 0, 'linear').key(1.3, -8, 'inout').key(3.0, -8, 'linear')
m.track('ParamFinR').key(0, 0, 'linear').key(1.3, -8, 'inout').key(3.0, -8, 'linear')
m.track('ParamAhoge').key(0, 0, 'linear').key(1.4, -8, 'inout').key(3.0, -8, 'linear')
m.track('ParamBreath').key(0, 0, 'linear').key(1.5, 1, 'inout').key(2.4, 0.2, 'inout').key(3.0, 0.6, 'inout')
reg('Slump', m)

# ---------- 喘气（1.8 s）：跑完停下，两口大气 ----------
m = Motion('pant', 1.8, fade_in=0.15, fade_out=0.5)
m.track('ParamBodyAngleY').key(0, 0, 'linear').key(0.25, -4, 'out').key(0.6, -2, 'inout').key(0.9, -4.5, 'inout').key(1.3, -2, 'inout').key(1.8, 0, 'inout')
m.track('ParamAngleY').key(0, 0, 'linear').key(0.25, -10, 'out').key(0.6, -6, 'inout').key(0.9, -11, 'inout').key(1.3, -5, 'inout').key(1.8, 0, 'inout')
m.track('ParamBreath').key(0, 0, 'linear').key(0.3, 1, 'out').key(0.6, 0.2, 'inout').key(0.9, 1, 'out').key(1.3, 0.2, 'inout').key(1.8, 0.5, 'inout')
m.track('ParamMouthOpenY').key(0, 0, 'linear').key(0.25, 0.6, 'out').key(0.6, 0.2, 'inout').key(0.9, 0.6, 'out').key(1.4, 0.1, 'inout').key(1.8, 0, 'inout')
for pid in ('ParamArmLA', 'ParamArmRA'):
    m.track(pid).key(0, 0, 'linear').key(0.3, 1.5, 'out').key(1.8, 0, 'inout')
m.track('ParamFinL').key(0, 0, 'linear').key(0.3, -6, 'out').key(1.8, 0, 'inout')
m.track('ParamFinR').key(0, 0, 'linear').key(0.3, -6, 'out').key(1.8, 0, 'inout')
reg('Pant', m)

# ---------- 荡（被拎着横拖，2.4 s）：整个人往后仰、腿甩 ----------
m = Motion('swing', 2.4, fade_in=0.2, fade_out=0.4)
m.track('ParamBodyStretch').key(0, 1, 'linear').key(2.4, 1, 'linear')
m.track('ParamBodyAngleZ').key(0, 0, 'linear').key(0.3, 8, 'out').key(1.2, 6, 'inout').key(2.0, -3, 'inout').key(2.4, 0, 'inout')
m.track('ParamAngleZ').key(0, 0, 'linear').key(0.35, 14, 'out').key(1.2, 10, 'inout').key(2.1, -4, 'inout').key(2.4, 0, 'inout')
m.track('ParamLegL').key(0, 0, 'linear').key(0.35, -8, 'out').key(1.2, -6, 'inout').key(2.0, 2, 'inout').key(2.4, 0, 'inout')
m.track('ParamLegR').key(0, 0, 'linear').key(0.35, -8, 'out').key(1.2, -6, 'inout').key(2.0, 2, 'inout').key(2.4, 0, 'inout')
m.track('ParamKneeL').key(0, 0, 'linear').key(0.4, 5, 'out').key(2.4, 0, 'inout')
m.track('ParamHairBackY').key(0, 0, 'linear').key(0.4, 1, 'out').key(2.4, 0, 'inout')
reg('Swing', m)

# ---------- 待机 3：东张西望（6 s 循环）----------
m = Motion('idle_look', 6.0, loop=True, fade_in=0.8, fade_out=0.8)
m.track('ParamBreath').key(0, 0, 'linear').key(1.7, 1, 'inout').key(3.3, 0, 'inout').key(4.9, 1, 'inout').key(6.0, 0, 'inout')
hx = m.track('ParamAngleX')
hx.key(0, 0, 'linear').key(0.8, 0, 'linear').key(1.1, -14, 'out').key(2.3, -14, 'linear').key(2.6, -10, 'inout').key(3.4, 12, 'out').key(4.6, 12, 'linear').key(5.3, 0, 'inout')
m.track('ParamEyeBallX').key(0, 0, 'linear').key(0.8, 0, 'linear').key(0.95, -0.8, 'out').key(2.3, -0.8, 'linear').key(3.25, 0.8, 'out').key(4.6, 0.8, 'linear').key(5.1, 0, 'inout')
m.track('ParamBodyAngleX').key(0, 0, 'linear').key(1.2, -3, 'inout').key(2.5, -3, 'linear').key(3.5, 3, 'inout').key(4.6, 3, 'linear').key(5.4, 0, 'inout')
m.track('ParamAngleZ').key(0, 0, 'linear').key(1.2, 3, 'inout').key(3.5, -3, 'inout').key(5.4, 0, 'inout')
reg('Idle', m)

# ---------- 写进 model3.json ----------
p = OUT / 'seeko.model3.json'
mj = json.load(open(p))
mj['FileReferences']['Motions'] = groups
json.dump(mj, open(p, 'w'), indent=2, ensure_ascii=False)
print('动作组', {k: len(v) for k, v in groups.items()})
