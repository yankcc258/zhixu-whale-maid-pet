"""在 Cubism 里铺好网格/纹理集之后的 seeko_q_v12.cmo3 上做小改（不回到 raw 重跑，免得丢网格）。
用法：python3 patch_v12b.py 输入.cmo3 输出.cmo3
b：肘 -10~10 → -120°(往外/往上)~+120°(往身体里)"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from caff import read_xml, write_xml
from rigedit import Rig
d = open(sys.argv[1], 'rb').read()
x, _ = read_xml(d)
r = Rig(x.decode('utf-8'))
r.rot_set_forms('左小臂旋转', lambda c, a, ox, oy, s: ({-10: -120.0, 0: 0.0, 10: 120.0}[round(c['ParamArmLB'])], ox, oy, s))
r.rot_set_forms('右小臂旋转', lambda c, a, ox, oy, s: ({-10: 120.0, 0: 0.0, 10: -120.0}[round(c['ParamArmRB'])], ox, oy, s))
r.canonicalize_grids()
open(sys.argv[2], 'wb').write(write_xml(d, r.s.encode('utf-8')))
print('\n'.join(r.log))
