"""v12 物理：头发三缕、后发上下浮、裙摆、围裙、呆毛、耳鳍。用法：python3 make_physics_v12.py <输出 seeko.physics3.json>
Cubism 物理的输出值 = 摆角(°) × Scale，再夹到参数范围；±1 的参数用 Scale 0.1 左右（10° 摆到头），±10 的参数用 1。"""
import json
import sys


def inp(pid, w, typ='X', reflect=False):
    return {'Source': {'Target': 'Parameter', 'Id': pid}, 'Weight': w, 'Type': typ, 'Reflect': reflect}


def out(pid, scale, vi=1, typ='Angle', reflect=False):
    return {'Destination': {'Target': 'Parameter', 'Id': pid}, 'VertexIndex': vi, 'Scale': scale, 'Weight': 100, 'Type': typ, 'Reflect': reflect}


def chain(lengths, mobility, delay, accel):
    vs = [{'Position': {'X': 0, 'Y': 0}, 'Mobility': 1, 'Delay': 1, 'Acceleration': 1, 'Radius': 0}]
    y = 0
    for i, L in enumerate(lengths):
        y += L
        vs.append({'Position': {'X': 0, 'Y': y}, 'Mobility': mobility, 'Delay': delay, 'Acceleration': accel, 'Radius': L})
    return vs


def setting(i, name, inputs, outputs, vertices, pos=10, ang=10):
    return {'Id': f'PhysicsSetting{i}', 'Input': inputs, 'Output': outputs, 'Vertices': vertices,
            'Normalization': {'Position': {'Minimum': -pos, 'Default': 0, 'Maximum': pos}, 'Angle': {'Minimum': -ang, 'Default': 0, 'Maximum': ang}}}, name


HEAD = [inp('ParamAngleX', 60), inp('ParamAngleZ', 60, 'Angle'), inp('ParamBodyAngleX', 40), inp('ParamBodyAngleZ', 40, 'Angle')]
S = []
S.append(setting(1, 'HairFront', HEAD, [out('ParamHairFront', 0.1)], chain([3], 0.95, 0.9, 1.5)))
S.append(setting(2, 'HairSide', HEAD, [out('ParamHairSide', 0.1)], chain([15], 0.95, 0.8, 1.5)))
S.append(setting(3, 'HairBack', HEAD, [out('ParamHairBack', 0.08)], chain([15], 0.95, 0.8, 1.5)))
# 三缕：外缕最软、延迟最大，两段摆
S.append(setting(4, 'HairBack1', HEAD + [inp('ParamBodyStretch', 30)], [out('ParamHairBack1', 0.12, 2)], chain([12, 12], 0.96, 0.75, 1.6)))
S.append(setting(5, 'HairBack2', HEAD, [out('ParamHairBack2', 0.11, 2)], chain([11, 11], 0.95, 0.8, 1.5)))
S.append(setting(6, 'HairBack3', HEAD, [out('ParamHairBack3', 0.10, 2)], chain([10, 10], 0.94, 0.85, 1.4)))
# 后发上下：身子上下、拉伸 → 滞后地上下浮（用 Y 方向输入）
S.append(setting(7, 'HairBackY', [inp('ParamBodyAngleY', 70, 'Y', True), inp('ParamBodyStretch', 40, 'Y', True)], [out('ParamHairBackY', 0.12)], chain([10], 0.93, 0.85, 1.6)))
# 裙摆：左右跟身子、头；上下跟身子上下（反向：身子往上跳裙子滞后往下）
S.append(setting(8, 'SkirtX', [inp('ParamBodyAngleX', 60), inp('ParamBodyAngleZ', 50, 'Angle'), inp('ParamAngleX', 15), inp('ParamLegL', 15), inp('ParamLegR', 15)], [out('ParamSkirtX', 0.12)], chain([12], 0.94, 0.8, 1.6)))
S.append(setting(9, 'SkirtY', [inp('ParamBodyAngleY', 70, 'Y', True), inp('ParamBodyStretch', 50, 'Y', True)], [out('ParamSkirtY', 0.10)], chain([10], 0.92, 0.85, 1.7)))
S.append(setting(10, 'Apron', [inp('ParamSkirtX', 60), inp('ParamBodyAngleZ', 30, 'Angle')], [out('ParamApron', 0.12)], chain([8], 0.93, 0.85, 1.5), pos=1))
# 呆毛、耳鳍：±10 的参数
S.append(setting(11, 'Ahoge', [inp('ParamAngleX', 50), inp('ParamAngleZ', 60, 'Angle'), inp('ParamBodyAngleY', 30, 'Y', True)], [out('ParamAhoge', 0.8)], chain([6], 0.97, 0.7, 1.8)))
S.append(setting(12, 'FinL', [inp('ParamAngleX', 40), inp('ParamAngleZ', 50, 'Angle'), inp('ParamBodyAngleY', 30, 'Y', True)], [out('ParamFinL', 0.5)], chain([6], 0.95, 0.8, 1.5)))
S.append(setting(13, 'FinR', [inp('ParamAngleX', 40), inp('ParamAngleZ', 50, 'Angle'), inp('ParamBodyAngleY', 30, 'Y', True)], [out('ParamFinR', 0.5, reflect=True)], chain([6], 0.95, 0.8, 1.5)))

settings = [s for s, _ in S]
meta = {'PhysicsSettingCount': len(settings), 'TotalInputCount': sum(len(s['Input']) for s in settings), 'TotalOutputCount': sum(len(s['Output']) for s in settings),
        'VertexCount': sum(len(s['Vertices']) for s in settings), 'Fps': 60, 'EffectiveForces': {'Gravity': {'X': 0, 'Y': -1}, 'Wind': {'X': 0, 'Y': 0}},
        'PhysicsDictionary': [{'Id': s['Id'], 'Name': n} for s, n in S]}
json.dump({'Version': 3, 'Meta': meta, 'PhysicsSettings': settings}, open(sys.argv[1], 'w'), indent='\t')
print('物理', len(settings), '组 →', sys.argv[1])
