"""希可表情 v2（15 个）。依赖 v05f 的新图层：MouthCat/MouthPout/MouthWavy/MouthFlat/MouthGrin、EyeSparkle_R/L、Tear_R/L、SweatDrop、AngerMark，
各挂在参数 ParamMouthCat/Pout/Wavy/Flat/Grin、ParamSparkle、ParamTear、ParamSweat、ParamAnger（0=隐藏 1=显示）。
用法：python3 make_expressions_v2.py <桌宠仓库>/src/live2d/seeko
"""
import json, sys
from pathlib import Path
OUT = Path(sys.argv[1]) / 'expressions'
O, A = 'Overwrite', 'Add'
def eyes(open_=1.0, smile=0.0):
    return [('ParamEyeLOpen', open_, O), ('ParamEyeROpen', open_, O), ('ParamEyeLSmile', smile, O), ('ParamEyeRSmile', smile, O)]
def brows(y=0.0, angle=0.0):
    return [('ParamBrowLY', y, O), ('ParamBrowRY', y, O), ('ParamBrowLAngle', angle, O), ('ParamBrowRAngle', -angle, O)]
def mouth(kind=None, open_=0.0, form=0.0):
    ps = [('ParamMouthOpenY', open_, O), ('ParamMouthForm', form, O)]
    for k in ['Cat', 'Pout', 'Wavy', 'Flat', 'Grin']:
        ps.append((f'ParamMouth{k}', 1.0 if k == kind else 0.0, O))
    return ps
def extra(sparkle=0, tear=0, sweat=0, anger=0, cheek=0.0):
    return [('ParamSparkle', sparkle, O), ('ParamTear', tear, O), ('ParamSweat', sweat, O), ('ParamAnger', anger, O), ('ParamCheek', cheek, O)]
def head(x=0, y=0, z=0):
    return [('ParamAngleX', x, A), ('ParamAngleY', y, A), ('ParamAngleZ', z, A)]
def fins(v, ahoge=0):
    return [('ParamFinL', v, A), ('ParamFinR', v, A), ('ParamAhoge', ahoge, A)]

EXP = {
    # 原来 7 个（重做，用新嘴型）
    'happy':     eyes(0, 1) + mouth('Grin') + extra(cheek=0.7) + fins(7),
    'smug':      eyes(0.35) + brows(0.2, 0.3) + mouth('Cat') + extra(cheek=0.3) + head(z=8) + fins(3, 3),
    'angry':     eyes(0.8) + brows(-1, -0.6) + mouth('Pout') + extra(anger=1, cheek=0.6) + head(y=-8) + fins(4, 5),
    'shy':       eyes(0.3, 0.6) + mouth('Wavy') + extra(cheek=1.0) + head(y=-8, z=-5) + fins(-4),
    'sleepy':    eyes(0.2) + brows(0.3) + mouth(None, 0.15) + extra() + head(z=-10, y=-5) + fins(-8, -5),
    'surprised': eyes(1) + brows(1) + mouth(None, 1.0, 1.0) + extra(sweat=1) + head(y=8) + fins(10, 8),
    'pout':      eyes(0.85) + brows(-0.6, -0.3) + mouth('Pout') + extra(cheek=0.7) + head(x=-8, z=6) + fins(-7, -4) + [('ParamEyeBallX', -0.7, O), ('ParamEyeBallY', -0.5, O)],
    # 新 8 个
    'wink':      [('ParamEyeLOpen', 1, O), ('ParamEyeROpen', 0, O), ('ParamEyeLSmile', 0, O), ('ParamEyeRSmile', 1, O)] + mouth('Cat') + extra(cheek=0.3) + head(z=6) + fins(5, 4),
    'teary':     eyes(0.6) + brows(0.6, 0.5) + mouth('Wavy') + extra(tear=1, cheek=0.4) + head(y=-6) + fins(-9, -5),
    'deadpan':   eyes(0.45) + brows(0, 0) + mouth('Flat') + extra(sweat=0) + head(z=-3) + fins(-3) + [('ParamEyeBallX', 0.6, O), ('ParamEyeBallY', 0.3, O)],
    'sparkle':   eyes(1) + brows(0.6) + mouth(None, 0.5, 0.6) + extra(sparkle=1, cheek=0.4) + head(y=4) + fins(9, 6),
    'puff':      eyes(0.7) + brows(-0.4, -0.2) + mouth(None, 0.0, -0.6) + extra(cheek=1.0) + head(x=6, z=-4) + fins(-6, -3),
    'dazed':     eyes(1) + brows(0.2) + mouth(None, 0.3, 0.0) + extra(sweat=1) + head() + fins(0, 0) + [('ParamEyeBallX', 0, O), ('ParamEyeBallY', 0, O)],
    'blush':     eyes(0.5, 0.3) + mouth('Wavy') + extra(cheek=1.0, sweat=1) + head(y=-10, x=10) + fins(-8, -6) + [('ParamEyeBallX', -0.8, O)],
    'grin':      eyes(0.6, 0.4) + brows(0.2, 0.4) + mouth('Grin') + extra(cheek=0.5) + head(z=-6) + fins(6, 5),
}
for name, ps in EXP.items():
    json.dump({'Type': 'Live2D Expression', 'FadeInTime': 0.25, 'FadeOutTime': 0.3,
               'Parameters': [{'Id': i, 'Value': v, 'Blend': b} for i, v, b in ps]},
              open(OUT / f'{name}.exp3.json', 'w'), ensure_ascii=False, indent='\t')
for mj in Path(sys.argv[1]).glob('*.model3.json'):
    d = json.load(open(mj))
    d['FileReferences']['Expressions'] = [{'Name': n, 'File': f'expressions/{n}.exp3.json'} for n in EXP]
    json.dump(d, open(mj, 'w'), ensure_ascii=False, indent='\t')
print('expressions:', list(EXP))
