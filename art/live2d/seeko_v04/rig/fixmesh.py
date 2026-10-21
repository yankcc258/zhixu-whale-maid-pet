"""套模板之后的修补：
1. 网格显示开关照旧模型（嘴的各组、闭眼线要显示；眼眶遮罩只当裁剪，不显示）
2. 模板没对上的几块嘴唇：GUI 里已经加好 MouthForm×MouthOpenY 的 9 个关键形态，这里照旧模型填不透明度
用法：python3 fixmesh.py 源.cmo3 目标.cmo3"""
import sys, re
sys.path.insert(0, '/tmp/claude-0/-home-claude/5d1ddcc7-fe5e-5109-8e8f-60afaa718bac/scratchpad/caff')
from caff import read_xml, write_xml
from model import params, grid

src, dst = sys.argv[1], sys.argv[2]
d = open(src, 'rb').read()
s = read_xml(d)[0].decode('utf-8')
P = params(s)

SHOW = ['MouthLipLowerO', 'MouthLipUpperO', 'MouthTongueO', 'MouthCavityO', 'MouthLipLowerMicro', 'MouthLipUpperMicro',
        'MouthTongueMicro', 'MouthCavityMicro', 'MouthLipLower', 'MouthLipUpper', 'MouthTongue', 'MouthCavity',
        'EyeLineClosed_L', 'EyeLineClosed_R']
HIDE = ['EyeSocketMask_L', 'EyeSocketMask_R']


def micro(c):  # 小张嘴：开到一半、不是 O 型嘴时显示
    return 1.0 if c['ParamMouthOpenY'] == 0.5 and c['ParamMouthForm'] < 1 else 0.0


def normal(c):  # 普通张嘴：全开、不是 O 型嘴时显示
    return 1.0 if c['ParamMouthOpenY'] == 1.0 and c['ParamMouthForm'] < 1 else 0.0


OPACITY = {'MouthLipUpper': normal, 'MouthLipUpperMicro': micro, 'MouthLipLowerMicro': micro}

edits = []
for m in re.finditer(r'<CArtMeshSource xs.id="(#\d+)"', s):
    st = m.start(); en = s.find('</CArtMeshSource>', st); b = s[st:en]
    nm = re.search(r'<s xs.n="localName">([^<]*)</s>', b).group(1)
    v = re.search(r'<b xs.n="isVisible">(\w+)</b>', b)
    want = 'true' if nm in SHOW else 'false' if nm in HIDE else None
    if want and v.group(1) != want:
        edits.append((st + v.start(1), st + v.end(1), want))
        print('显示', nm, v.group(1), '→', want)
    if nm in OPACITY:
        km = re.search(r'<KeyformGridSource xs.n="keyformGridSource"( xs.ref="(#\d+)")?', b)
        kg = s.rfind('<KeyformGridSource', 0, s.find(f'xs.id="{km.group(2)}"') + 1) if km.group(2) else st + km.start()
        G = grid(s, kg, P)
        assert len(G) == 9, (nm, len(G))
        for c, fg in G:
            # 这个关键形态对应的 CArtMeshForm
            for mm in re.finditer(r'<CArtMeshForm[^>]*>', b):
                seg = b[mm.end():mm.end() + 600]
                if re.search(rf'CFormGuid xs\.n="guid" xs\.(?:ref|id)="{fg}"', seg):
                    fe = b.find('</CArtMeshForm>', mm.end())
                    op = re.search(r'<f xs.n="opacity">([^<]*)</f>', b[mm.end():fe])
                    val = OPACITY[nm](c)
                    a = st + mm.end() + op.start(1)
                    edits.append((a, a + len(op.group(1)), f'{val}'))
                    print('不透明度', nm, c, '→', val)
                    break
            else:
                raise RuntimeError(f'{nm} 找不到关键形态 {fg}')

for a, b_, t in sorted(edits, reverse=True):
    s = s[:a] + t + s[b_:]
open(dst, 'wb').write(write_xml(d, s.encode('utf-8')))
print('写入', dst, len(edits), '处')
