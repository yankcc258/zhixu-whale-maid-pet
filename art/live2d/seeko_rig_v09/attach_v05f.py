"""把 v05f 的 11 个表情图层挂到脸部曲面下，各绑一个 0/1 参数。用法：python3 attach_v05f.py 源.cmo3 目标.cmo3 v05f.psd"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', 'tools', 'live2d-checks'))
from caff import read_xml, write_xml
from rigedit import Rig
src, dst = sys.argv[1:3]
d = open(src, 'rb').read(); r = Rig(read_xml(d)[0].decode())
params = {'ParamMouthCat': '嘴 ω', 'ParamMouthPout': '嘴 撅', 'ParamMouthWavy': '嘴 波浪', 'ParamMouthFlat': '嘴 一字', 'ParamMouthGrin': '嘴 咧笑',
          'ParamSparkle': '眼 闪闪', 'ParamTear': '泪珠', 'ParamSweat': '汗滴', 'ParamAnger': '青筋'}
for pid, nm in params.items():
    r.add_param(pid, nm, 0, 1, 0, '1=显示')
# 嘴：在 MouthLineClosed(580) 之上、MouthCavity(585) 之下
for i, (n, pid) in enumerate([('MouthCat', 'ParamMouthCat'), ('MouthPout', 'ParamMouthPout'), ('MouthWavy', 'ParamMouthWavy'), ('MouthFlat', 'ParamMouthFlat'), ('MouthGrin', 'ParamMouthGrin')]):
    r.mesh_attach_toggle(n, '脸部曲面', pid, draw_order=581 + i * 0)  # 同一层级，互斥显示
# 闪闪眼：高光之上（EyeHighlightLower_R 500 / _L 550）
r.mesh_attach_toggle('EyeSparkle_R', '脸部曲面', 'ParamSparkle', draw_order=501)
r.mesh_attach_toggle('EyeSparkle_L', '脸部曲面', 'ParamSparkle', draw_order=551)
# 泪珠、汗滴、青筋：腮红之上（575）、嘴之下
r.mesh_attach_toggle('Tear_R', '脸部曲面', 'ParamTear', draw_order=576)
r.mesh_attach_toggle('Tear_L', '脸部曲面', 'ParamTear', draw_order=576)
r.mesh_attach_toggle('SweatDrop', '脸部曲面', 'ParamSweat', draw_order=577)
r.mesh_attach_toggle('AngerMark', '脸部曲面', 'ParamAnger', draw_order=577)
# 新图层的网格是整画布 4 点，重铺成贴着图像的小矩形（不然纹理集会把整张画布塞进去）
from psd_tools import PSDImage
import numpy as np
psd = PSDImage.open(sys.argv[3])
for l in psd.descendants():
    if l.is_group() or l.name not in ['MouthCat', 'MouthPout', 'MouthWavy', 'MouthFlat', 'MouthGrin', 'EyeSparkle_R', 'EyeSparkle_L', 'Tear_R', 'Tear_L', 'SweatDrop', 'AngerMark']:
        continue
    a = np.array(l.topil().convert('RGBA'))[..., 3] > 8
    ys, xs = np.nonzero(a)
    r.mesh_fit_bbox(l.name, (l.left + xs.min(), l.top + ys.min(), l.left + xs.max() + 1, l.top + ys.max() + 1))
print('\n'.join(r.log))
open(dst, 'wb').write(write_xml(d, r.s.encode())); print('→', dst)
