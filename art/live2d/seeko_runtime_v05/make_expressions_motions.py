"""生成希可的表情 (.exp3.json)、待机动作 (.motion3.json)，并把它们写进 model3.json。"""
import json, math, shutil
from pathlib import Path

SRC = Path('/mnt/user-data/uploads/Seeko_Binding_v03')
OUT = Path('/tmp/claude-0/-home-claude/5d1ddcc7-fe5e-5109-8e8f-60afaa718bac/scratchpad/seeko_runtime')
if OUT.exists():
    shutil.rmtree(OUT)
(OUT / 'expressions').mkdir(parents=True)
(OUT / 'motions').mkdir()
for f in ['seeko.moc3', 'seeko.physics3.json', 'seeko.cdi3.json']:
    shutil.copy(SRC / f, OUT / f)
(OUT / 'seeko.2048').mkdir()
shutil.copy(SRC / 'seeko.2048/texture_00.png', OUT / 'seeko.2048/texture_00.png')

O, A = 'Overwrite', 'Add'
# 名字和桌宠的心情一一对应
EXP = {
    # 开心：^^ 笑眼 + 张嘴 + 脸红
    'happy': [('ParamEyeLOpen', 0, O), ('ParamEyeROpen', 0, O), ('ParamEyeLSmile', 1, O), ('ParamEyeRSmile', 1, O),
              ('ParamMouthForm', 0, O), ('ParamMouthOpenY', 0.7, O), ('ParamCheek', 0.7, O)],
    # 屑笑：^^ 笑眼 + :3 闭嘴 + 歪头（眼睛半眯要等眼皮变形做好，现在用笑眼代替）
    'smug': [('ParamEyeLOpen', 0, O), ('ParamEyeROpen', 0, O), ('ParamEyeLSmile', 1, O), ('ParamEyeRSmile', 1, O),
             ('ParamMouthOpenY', 0, O), ('ParamCheek', 0.3, O), ('ParamAngleZ', 8, A)],
    # 生气：睁眼瞪人 + 气鼓鼓脸红 + 头往前低一点
    'angry': [('ParamEyeLOpen', 1, O), ('ParamEyeROpen', 1, O), ('ParamBrowLY', -1, O), ('ParamBrowRY', -1, O),
              ('ParamMouthOpenY', 0, O), ('ParamCheek', 0.8, O), ('ParamAngleY', -8, A)],
    # 害羞（被摸头）：^^ 笑眼 + 大脸红 + 低头
    'shy': [('ParamEyeLOpen', 0, O), ('ParamEyeROpen', 0, O), ('ParamEyeLSmile', 1, O), ('ParamEyeRSmile', 1, O),
            ('ParamCheek', 1, O), ('ParamMouthOpenY', 0, O), ('ParamAngleY', -8, A), ('ParamAngleZ', -5, A)],
    # 犯困：闭眼（— —）+ 歪头
    'sleepy': [('ParamEyeLOpen', 0, O), ('ParamEyeROpen', 0, O), ('ParamEyeLSmile', 0, O), ('ParamEyeRSmile', 0, O),
               ('ParamMouthOpenY', 0, O), ('ParamAngleZ', -10, A), ('ParamAngleY', -5, A)],
    # 吓一跳：睁大眼 + O 型嘴 + 眉毛抬高 + 头往后仰
    'surprised': [('ParamEyeLOpen', 1, O), ('ParamEyeROpen', 1, O), ('ParamBrowLY', 1, O), ('ParamBrowRY', 1, O),
                  ('ParamMouthForm', 1, O), ('ParamMouthOpenY', 1, O), ('ParamAngleY', 8, A)],
    # 委屈：往旁下方看 + 脸红 + 歪头
    'pout': [('ParamEyeLOpen', 1, O), ('ParamEyeROpen', 1, O), ('ParamBrowLY', -0.6, O), ('ParamBrowRY', -0.6, O),
             ('ParamEyeBallX', -0.7, O), ('ParamEyeBallY', -0.5, O), ('ParamCheek', 0.7, O), ('ParamMouthOpenY', 0, O),
             ('ParamAngleZ', 6, A), ('ParamAngleX', -8, A)],
}
for name, ps in EXP.items():
    json.dump({'Type': 'Live2D Expression', 'FadeInTime': 0.3, 'FadeOutTime': 0.3,
               'Parameters': [{'Id': i, 'Value': v, 'Blend': b} for i, v, b in ps]},
              open(OUT / f'expressions/{name}.exp3.json', 'w'), ensure_ascii=False, indent='\t')


def motion(name, dur, curves, loop=True, fps=30):
    """curves: {id: f(t)}，每 0.1 秒取一个点，线性连接"""
    out, segs, pts = [], 0, 0
    for pid, f in curves.items():
        n = int(round(dur / 0.1))
        ts = [round(i * dur / n, 4) for i in range(n + 1)]
        s = [ts[0], round(f(ts[0]), 4)]
        for t in ts[1:]:
            s += [0, t, round(f(t), 4)]
        out.append({'Target': 'Parameter', 'Id': pid, 'Segments': s})
        segs += n
        pts += n + 1
    m = {'Version': 3, 'Meta': {'Duration': dur, 'Fps': fps, 'Loop': loop, 'AreBeziersRestricted': True,
                                'CurveCount': len(out), 'TotalSegmentCount': segs, 'TotalPointCount': pts,
                                'UserDataCount': 0, 'TotalUserDataSize': 0}, 'Curves': out}
    json.dump(m, open(OUT / f'motions/{name}.motion3.json', 'w'), indent='\t')


S = lambda per, amp, ph=0: (lambda t: amp * math.sin(2 * math.pi * t / per + ph))
# 待机：8 秒一圈，呼吸 4 秒一次，头和身体慢慢晃，正好首尾相接
motion('idle', 8.0, {
    'ParamBreath': lambda t: 0.5 - 0.5 * math.cos(2 * math.pi * t / 4),
    'ParamAngleX': S(8, 4),
    'ParamAngleY': S(4, 2, 0.6),
    'ParamAngleZ': S(8, 5, 1.2),
    'ParamBodyAngleX': S(8, 2, 0.4),
    'ParamBodyAngleZ': S(8, 3, 1.6),
    'ParamEyeBallX': S(8, 0.25, 0.3),
})


def bump(t0, t1, amp, per=None):
    def f(t):
        if t <= t0 or t >= t1:
            return 0.0
        x = (t - t0) / (t1 - t0)
        return amp * math.sin(math.pi * x) ** 2
    return f


# 点头：两下
motion('nod', 1.6, {'ParamAngleY': lambda t: -12 * math.sin(math.pi * t / 0.8) ** 2,
                    'ParamBodyAngleY': lambda t: -3 * math.sin(math.pi * t / 0.8) ** 2}, loop=False)
# 摇头：左右两下
motion('shake', 1.6, {'ParamAngleX': lambda t: 18 * math.sin(2 * math.pi * t / 0.8) * math.sin(math.pi * t / 1.6),
                      'ParamBodyAngleX': lambda t: 3 * math.sin(2 * math.pi * t / 0.8) * math.sin(math.pi * t / 1.6)}, loop=False)
# 甩头（被拎起来时）：大幅摆动，头发跟着物理甩
motion('swing', 2.0, {'ParamAngleZ': lambda t: 20 * math.sin(2 * math.pi * t / 0.7) * math.exp(-t),
                      'ParamAngleX': lambda t: 15 * math.sin(2 * math.pi * t / 0.9) * math.exp(-t),
                      'ParamBodyAngleZ': lambda t: 8 * math.sin(2 * math.pi * t / 0.7) * math.exp(-t)}, loop=False)

model = json.load(open(SRC / 'seeko.model3.json'))
fr = model['FileReferences']
fr['Expressions'] = [{'Name': n, 'File': f'expressions/{n}.exp3.json'} for n in EXP]
fr['Motions'] = {'Idle': [{'File': 'motions/idle.motion3.json', 'FadeInTime': 0.5, 'FadeOutTime': 0.5}],
                 'Nod': [{'File': 'motions/nod.motion3.json'}],
                 'Shake': [{'File': 'motions/shake.motion3.json'}],
                 'Swing': [{'File': 'motions/swing.motion3.json'}]}
model['Groups'] = [{'Target': 'Parameter', 'Name': 'EyeBlink', 'Ids': ['ParamEyeLOpen', 'ParamEyeROpen']},
                   {'Target': 'Parameter', 'Name': 'LipSync', 'Ids': ['ParamMouthOpenY']}]
model['HitAreas'] = []
json.dump(model, open(OUT / 'seeko.model3.json', 'w'), ensure_ascii=False, indent='\t')
print('ok', sorted(p.name for p in OUT.rglob('*') if p.is_file()))
