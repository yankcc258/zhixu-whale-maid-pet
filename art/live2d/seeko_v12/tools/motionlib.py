"""motion3.json 的手调关键帧工具（v3）：不用正弦，用关键帧 + 缓动 + 预备/过冲/停顿 + 关节错帧。

用法：
    from motionlib import Motion, Track
    m = Motion('wave', dur=2.4)
    arm = m.track('ParamArmLA')
    arm.hit(t0=0.2, base=0, peak=100, antic=0.12, rise=0.22, over=0.1, settle=0.5)   # 一次「甩出去」
    arm.key(1.9, 0, ease='inout')                                                       # 缓慢放下
    m.write('out/motions')

曲线：每个 Track 是一串 (t, v, ease) 关键帧，相邻两帧之间按 ease 做三次缓动（out/in/inout/linear/hold），
最后按 step 采样成 motion3 的线性段（Cubism 运行库照样平滑，节奏来自曲线本身）。
"""
import json
import math
from pathlib import Path


def _ease(kind, u):
    if kind == 'linear':
        return u
    if kind == 'hold':
        return 0.0 if u < 1 else 1.0
    if kind == 'in':
        return u * u * u
    if kind == 'out':
        return 1 - (1 - u) ** 3
    if kind == 'inout':
        return 4 * u * u * u if u < 0.5 else 1 - (-2 * u + 2) ** 3 / 2
    if kind == 'back':  # 带一点过冲的 out
        c1, c3 = 1.70158, 2.70158
        return 1 + c3 * (u - 1) ** 3 + c1 * (u - 1) ** 2
    if kind == 'bounce':
        return 1 - abs(math.cos(u * math.pi * 1.5)) * (1 - u) ** 2 if u < 1 else 1.0
    raise ValueError(kind)


class Track:
    def __init__(self, pid):
        self.pid = pid
        self.keys = []  # (t, v, ease_into_this_key)

    def key(self, t, v, ease='out'):
        self.keys.append((float(t), float(v), ease))
        self.keys.sort(key=lambda k: k[0])
        return self

    def hold(self, t, dur):
        """在 t 处保持当前值 dur 秒（停顿）"""
        v = self.at(t)
        self.key(t, v, 'linear')
        self.key(t + dur, v, 'hold' if False else 'linear')
        return self

    def hit(self, t0, base, peak, antic=0.12, rise=0.22, over=0.12, settle=0.45, antic_k=0.15, over_k=0.12, pause=0.0):
        """一次有节奏的动作：预备（反向 antic_k）→ 主动作（快）→ 过冲（over_k）→ 回到 peak 停住。
        之后想放下就自己再 key。返回停稳的时刻。"""
        d = peak - base
        if antic > 0:
            self.key(t0, base, 'linear')
            self.key(t0 + antic, base - d * antic_k, 'inout')
        else:
            self.key(t0, base, 'linear')
        t1 = t0 + antic + rise
        self.key(t1, peak + d * over_k, 'out')
        t2 = t1 + over
        self.key(t2, peak, 'inout')
        if pause > 0:
            self.key(t2 + pause, peak, 'linear')
        return t2 + pause

    def release(self, t0, v_to=0.0, dur=0.5, ease='inout'):
        """从当前值缓慢回到 v_to"""
        self.key(t0, self.at(t0), 'linear')
        self.key(t0 + dur, v_to, ease)
        return t0 + dur

    def shift(self, dt):
        self.keys = [(t + dt, v, e) for t, v, e in self.keys]
        return self

    def scale(self, k):
        self.keys = [(t, v * k, e) for t, v, e in self.keys]
        return self

    def at(self, t):
        ks = self.keys
        if not ks:
            return 0.0
        if t <= ks[0][0]:
            return ks[0][1]
        if t >= ks[-1][0]:
            return ks[-1][1]
        for (t0, v0, _), (t1, v1, e) in zip(ks, ks[1:]):
            if t0 <= t <= t1:
                if t1 == t0:
                    return v1
                u = (t - t0) / (t1 - t0)
                return v0 + (v1 - v0) * _ease(e, u)
        return ks[-1][1]


class Motion:
    def __init__(self, name, dur, loop=False, step=0.04, fade_in=0.3, fade_out=0.4):
        self.name, self.dur, self.loop, self.step = name, float(dur), loop, step
        self.fade_in, self.fade_out = fade_in, fade_out
        self.tracks = {}

    def track(self, pid):
        if pid not in self.tracks:
            self.tracks[pid] = Track(pid)
        return self.tracks[pid]

    def fn(self, pid, f):
        """直接给函数 t -> v（比如循环用的）"""
        tr = self.track(pid)
        n = int(round(self.dur / self.step))
        for i in range(n + 1):
            t = i * self.dur / n
            tr.key(t, f(t), 'linear')
        return tr

    def sample(self, pid, t):
        return self.tracks[pid].at(t)

    def to_json(self):
        out, segs, pts = [], 0, 0
        n = int(round(self.dur / self.step))
        for pid, tr in self.tracks.items():
            ts = [round(i * self.dur / n, 4) for i in range(n + 1)]
            s = [ts[0], round(tr.at(ts[0]), 4)]
            for t in ts[1:]:
                s += [0, t, round(tr.at(t), 4)]
            out.append({'Target': 'Parameter', 'Id': pid, 'Segments': s})
            segs += n
            pts += n + 1
        return {'Version': 3, 'Meta': {'Duration': self.dur, 'Fps': 30, 'Loop': self.loop, 'AreBeziersRestricted': True,
                                       'CurveCount': len(out), 'TotalSegmentCount': segs, 'TotalPointCount': pts,
                                       'UserDataCount': 0, 'TotalUserDataSize': 0}, 'Curves': out}

    def write(self, folder):
        Path(folder).mkdir(parents=True, exist_ok=True)
        json.dump(self.to_json(), open(Path(folder) / f'{self.name}.motion3.json', 'w'), indent='\t')
        return {'File': f'motions/{self.name}.motion3.json', 'FadeInTime': self.fade_in, 'FadeOutTime': self.fade_out}


# ---------- 常用「身体一起动」的小配方 ----------
def body_follow(m, t0, amount, head_k=1.0, delay=0.06, dur=0.3, settle=0.6):
    """核心先动、腰胸头依次跟上：BodyAngleZ → (ChestZ) → AngleZ。amount 是 BodyAngleZ 的目标。
    参数名不存在的模型会忽略多余曲线（运行库跳过没有的 Id），所以可以放心写。"""
    m.track('ParamBodyAngleZ').hit(t0, 0, amount, antic=0.08, rise=dur, over=0.1, antic_k=0.2, over_k=0.15)
    m.track('ParamChestZ').hit(t0 + delay, 0, amount * 0.8, antic=0.08, rise=dur, over=0.1, antic_k=0.2, over_k=0.2)
    m.track('ParamAngleZ').hit(t0 + delay * 2, 0, -amount * 1.2 * head_k, antic=0.08, rise=dur, over=0.12, antic_k=0.2, over_k=0.25)


def body_release(m, t0, dur=0.6):
    for pid in ('ParamBodyAngleZ', 'ParamChestZ', 'ParamAngleZ'):
        if pid in m.tracks:
            m.tracks[pid].release(t0, 0, dur)
