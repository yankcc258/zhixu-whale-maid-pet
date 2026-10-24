"""半闭眼重影修正：睁眼各层在 EyeOpen 0~0.5 之间原本是边压扁边淡出，闭眼线同时淡入，0.2 附近两个都半透明叠成灰影。
改成：睁眼层到 0.15 时还是完全不透明（形状按 0 和 0.5 之间插值），0.15→0 才消失；闭眼线 0.15 时还是 0，0→1 只在最后一段。
用法：python3 fix_blink.py 源.cmo3 目标.cmo3
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', 'tools', 'live2d-checks'))
from caff import read_xml, write_xml
from rigedit import Rig
src, dst = sys.argv[1:3]
d = open(src, 'rb').read(); r = Rig(read_xml(d)[0].decode())
for side in 'LR':
    p = f'ParamEye{side}Open'
    for n in ['EyeLineUpper', 'EyeLineLower', 'EyeWhite', 'IrisPupil', 'EyeHighlightUpper', 'EyeHighlightLower']:
        r.mesh_insert_key(f'{n}_{side}', p, 0.15, opacity=1.0)
    r.mesh_insert_key(f'EyeLineClosed_{side}', p, 0.15, opacity=0.0)
print('\n'.join(r.log))
open(dst, 'wb').write(write_xml(d, r.s.encode())); print('→', dst)
