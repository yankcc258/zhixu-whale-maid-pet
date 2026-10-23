"""换装 PSD 的 25 个衣服槽位 + 底稿 PSD 的其余 57 层 → 新 PSD（层名、顺序、显隐跟底稿）。
用法：python3 -I mixpsd.py 底稿.psd 换装.psd 输出.psd"""
import sys
from psd_tools import PSDImage
from psd_tools.api.layers import PixelLayer

SLOTS = set('DressBase SkirtFront SkirtHemLace BodiceWhite ChestLace_R ChestLace_L ApronBody ApronLace Waistband NeckCollar ArmUpper_R ArmUpper_L ArmLower_R ArmLower_L Cuff_R Cuff_L LegStocking_R LegStocking_L Shoe_R Shoe_L Headband HairRibbon_L NeckBow_R NeckBow_L Sapphire'.split())
base, outfit, dst = sys.argv[1:4]
B = PSDImage.open(base)
O = {l.name: l for l in PSDImage.open(outfit).descendants() if not l.is_group()}
n = 0
for l in list(B.descendants()):
    if l.is_group() or l.name not in SLOTS:
        continue
    src = O[l.name]
    im = src.topil()
    if im is None:
        from PIL import Image
        im = Image.new('RGBA', (1, 1), (0, 0, 0, 0))
    new = PixelLayer.frompil(im.convert('RGBA'), B, l.name, src.top, src.left)
    new.visible = l.visible
    p = l.parent
    p[list(p).index(l)] = new
    n += 1
B.save(dst)
chk = [x.name for x in PSDImage.open(dst).descendants() if not x.is_group()]
print('换了', n, '个槽位；层数', len(chk), '名字顺序跟底稿一致', chk == [x.name for x in PSDImage.open(base).descendants() if not x.is_group()])
