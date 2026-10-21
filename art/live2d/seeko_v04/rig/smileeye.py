"""笑眼修补：模板把旧模型「笑眼」关键形态的形状搬过来后位置不对，闭眼线一笑就跑没了。
这里把 EyeLineClosed_L/R 在 Smile=1 的关键形态，改成同一开合下 Smile=0 形状的上下翻转（︶ 变 ︵，就是 ^^）。
用法：python3 smileeye.py 源.cmo3 目标.cmo3"""
import sys, re
sys.path.insert(0, '/tmp/claude-0/-home-claude/5d1ddcc7-fe5e-5109-8e8f-60afaa718bac/scratchpad/caff')
from caff import read_xml, write_xml
from model import params, grid

src, dst = sys.argv[1], sys.argv[2]
d = open(src, 'rb').read()
s = read_xml(d)[0].decode('utf-8')
P = params(s)
edits = []
for m in re.finditer(r'<CArtMeshSource xs.id="(#\d+)"', s):
    st = m.start(); en = s.find('</CArtMeshSource>', st); b = s[st:en]
    nm = re.search(r'<s xs.n="localName">([^<]*)</s>', b).group(1)
    if not nm.startswith('EyeLineClosed_'):
        continue
    side = nm[-1]
    km = re.search(r'<KeyformGridSource xs.n="keyformGridSource"( xs.ref="(#\d+)")?', b)
    kg = s.rfind('<KeyformGridSource', 0, s.find(f'xs.id="{km.group(2)}"') + 1) if km.group(2) else st + km.start()
    G = grid(s, kg, P)
    pos = {}
    for c, fg in G:
        for mm in re.finditer(r'<CArtMeshForm[^>]*>', b):
            if re.search(rf'CFormGuid xs\.n="guid" xs\.(?:ref|id)="{fg}"', b[mm.end():mm.end() + 600]):
                fe = b.find('</CArtMeshForm>', mm.end())
                pm = re.search(r'<float-array xs.n="positions" count="\d+">([^<]*)</float-array>', b[mm.end():fe])
                a = st + mm.end() + pm.start(1)
                pos[(c[f'ParamEye{side}Open'], c[f'ParamEye{side}Smile'])] = (a, a + len(pm.group(1)), [float(v) for v in pm.group(1).split()])
                break
    for (op, sm), (a, e, v) in pos.items():
        if sm != 1:
            continue
        base = pos[(op, 0)][2]
        ys = base[1::2]
        cy = (min(ys) + max(ys)) / 2
        new = []
        for i in range(0, len(base), 2):
            new += [base[i], 2 * cy - base[i + 1]]
        old_ys = v[1::2]
        print(nm, f'open={op}', '原来 y 范围', round(min(old_ys), 4), round(max(old_ys), 4), '→ 翻转后', round(min(new[1::2]), 4), round(max(new[1::2]), 4))
        edits.append((a, e, ' '.join(f'{x:.7g}' for x in new)))
for a, e, t in sorted(edits, reverse=True):
    s = s[:a] + t + s[e:]
open(dst, 'wb').write(write_xml(d, s.encode('utf-8')))
print('写入', dst, len(edits), '处')
