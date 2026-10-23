"""把希可的 82 层 PSD 转成 psd2live（agent kit 版）的 PNG 清单：按它认得的名字改层名、按 PSD 顺序给 z。
psd2live 一种嘴只能有一套张嘴图，所以小张嘴、O 型嘴先不放；眼眶遮罩、闭眼眼皮也不放（它自己做闭眼变形）。
用法：python3 -I seeko_manifest.py 输入.psd 输出目录"""
import sys, json, os
from psd_tools import PSDImage

MAP = {
    'HairBack_R': 'back hair-r', 'HairBack_L': 'back hair-l',
    'LegStocking_R': 'legwear-r', 'LegStocking_L': 'legwear-l', 'Shoe_R': 'footwear-r', 'Shoe_L': 'footwear-l',
    'DressBase': 'topwear 1', 'SkirtHemLace': 'bottomwear 1', 'SkirtFront': 'bottomwear 2',
    'BodiceWhite': 'topwear 2', 'ChestLace_R': 'topwear 3', 'ChestLace_L': 'topwear 4', 'ApronLace': 'topwear 5',
    'ApronBody': 'topwear 6', 'Waistband': 'topwear 7', 'NeckCollar': 'neckwear 1',
    'ArmUpper_R': 'handwear 1-r', 'ArmLower_R': 'handwear 2-r', 'ArmUpper_L': 'handwear 1-l', 'ArmLower_L': 'handwear 2-l',
    'Hand_R': 'handwear 3-r', 'Hand_L': 'handwear 3-l', 'Cuff_R': 'handwear 4-r', 'Cuff_L': 'handwear 4-l',
    'Neck': 'neck', 'FaceBase': 'face', 'FaceHairShadow': 'face detail 1',
    'FinEar_R': 'ears-r', 'FinEar_L': 'ears-l',
    'EyeWhite_R': 'eyewhite-r', 'IrisPupil_R': 'irides-r', 'EyeLineLower_R': 'eyelash 2-r', 'EyeLineUpper_R': 'eyelash-r',
    'EyeHighlightUpper_R': 'irides 2-r', 'EyeHighlightLower_R': 'irides 3-r', 'EyeLineClosed_R': 'eye_close-r',
    'EyeWhite_L': 'eyewhite-l', 'IrisPupil_L': 'irides-l', 'EyeLineLower_L': 'eyelash 2-l', 'EyeLineUpper_L': 'eyelash-l',
    'EyeHighlightUpper_L': 'irides 2-l', 'EyeHighlightLower_L': 'irides 3-l', 'EyeLineClosed_L': 'eye_close-l',
    'CheekBlush_R': 'blush-r', 'CheekBlush_L': 'blush-l',
    'MouthLineClosed': 'mouth_close', 'MouthCavity': 'mouth_open', 'MouthTongue': 'tongue',
    'MouthLipUpper': 'mouth_open 2', 'MouthLipLower': 'mouth_open 3',
    'HairSide_R': 'front hair-side-r', 'HairSide_L': 'front hair-side-l',
    'HairFront_Center': 'front hair-bangs', 'HairFront_R': 'front hair-bangs 2-r', 'HairFront_L': 'front hair-bangs 2-l',
    'Ahoge': 'front hair-ahoge', 'Eyebrow_R': 'eyebrow-r', 'Eyebrow_L': 'eyebrow-l',
    'Headband': 'headwear 1', 'HairRibbon_L': 'headwear 2-l',
    'NeckBow_R': 'neckwear 2-r', 'NeckBow_L': 'neckwear 2-l', 'Sapphire': 'neckwear 3',
}
src, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)
psd = PSDImage.open(src)
W, H = psd.size
layers = []
for z, l in enumerate([l for l in psd.descendants() if not l.is_group()]):
    if l.name not in MAP:
        continue
    im = l.topil()
    if im is None or im.convert('RGBA').getbbox() is None:
        continue
    fn = f'{l.name}.png'
    im.convert('RGBA').save(os.path.join(out, fn))
    layers.append({'name': MAP[l.name], 'path': fn, 'x': l.left, 'y': l.top, 'z': z * 10})
man = {'name': 'SeekoAuto', 'width': W, 'height': H,
       'config': {'atlas_size': 2048, 'texture_padding': 8, 'texture_edge_extrusion': 8},
       'layers': layers}
json.dump(man, open(os.path.join(out, 'manifest.json'), 'w'), ensure_ascii=False, indent=1)
print(len(layers), '层写入', out)
