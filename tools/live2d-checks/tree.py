"""把 cmo3 的变形器树、每个变形器的中立形态、每个网格挂在哪、网格自己有没有关键形态 打印出来。"""
import sys, re, json
sys.path.insert(0, '/tmp/claude-0/-home-claude/5d1ddcc7-fe5e-5109-8e8f-60afaa718bac/scratchpad/caff')
from caff import read_xml
from model import params, deformers, grid, forms

src = sys.argv[1]
s = read_xml(open(src, 'rb').read())[0].decode('utf-8')
P = params(s)
D = deformers(s)
g2n = {d['guid']: n for n, d in D.items()}


def rot_forms(d):
    b = s[d['start']:d['end']]
    out = {}
    for m in re.finditer(r'<CRotationDeformerForm ([^>]*)>', b):
        at = dict(re.findall(r'(\w+)="([^"]*)"', m.group(1)))
        tail = b[m.end():m.end() + 800]
        g = re.search(r'CFormGuid xs\.n="guid" xs\.(?:ref|id)="(#\d+)"', tail).group(1)
        out[g] = {k: float(at[k]) for k in ('angle', 'originX', 'originY', 'scale')}
    return out


info = {}
for n, d in D.items():
    G = grid(s, d['grid'], P)
    neutral = [fg for c, fg in G if all(v == 0 for v in c.values())] or [G[0][1]]
    params_used = sorted({p for c, _ in G for p in c})
    e = dict(kind='warp' if 'Warp' in d['kind'] else 'rot', parent=g2n.get(d['target'], 'ROOT'), params=params_used, nkeys=len(G))
    if e['kind'] == 'warp':
        F = forms(s, d)
        b = s[d['start']:d['end']]
        cols = int(re.search(r'<i xs.n="col">(\d+)</i>', b).group(1))
        rows = int(re.search(r'<i xs.n="row">(\d+)</i>', b).group(1))
        v = F[neutral[0]][2]
        xs, ys = v[0::2], v[1::2]
        e.update(cols=cols, rows=rows, bbox=[min(xs), min(ys), max(xs), max(ys)])
    else:
        R = rot_forms(d)
        e.update(neutral=R.get(neutral[0]))
    info[n] = e

# 网格
meshes = {}
for m in re.finditer(r'<CArtMeshSource xs.id="(#\d+)"', s):
    st = m.start(); en = s.find('</CArtMeshSource>', st); b = s[st:en]
    nm = re.search(r'<s xs.n="localName">([^<]*)</s>', b).group(1)
    t = re.search(r'<CDeformerGuid xs.n="targetDeformerGuid" xs.ref="(#\d+)"', b)
    km = re.search(r'<KeyformGridSource xs.n="keyformGridSource"( xs.ref="(#\d+)")?', b)
    if km.group(2):
        kg = s.find(f'xs.id="{km.group(2)}"'); kg = s.rfind('<KeyformGridSource', 0, kg + 1)
    else:
        kg = st + km.start()
    G = grid(s, kg, P)
    clip = re.search(r'<carray_list xs.n="clipGuidList" count="(\d+)"', b)
    meshes[nm] = dict(parent=g2n.get(t.group(1), 'ROOT') if t else 'ROOT', params=sorted({p for c, _ in G for p in c}), nkeys=len(G), clip=int(clip.group(1)) if clip else 0)


def show(n, ind=0):
    e = info[n]
    extra = f"grid {e['cols']}x{e['rows']} bbox {[round(x, 3) for x in e['bbox']]}" if e['kind'] == 'warp' else f"neutral {e['neutral']}"
    print('  ' * ind + f"[{e['kind']}] {n}  params={e['params']} keys={e['nkeys']}  {extra}")
    for mn, me in meshes.items():
        if me['parent'] == n:
            print('  ' * (ind + 1) + f"- {mn} params={me['params']} keys={me['nkeys']} clip={me['clip']}")
    for c, ce in info.items():
        if ce['parent'] == n:
            show(c, ind + 1)


for n, e in info.items():
    if e['parent'] == 'ROOT':
        show(n)
for mn, me in meshes.items():
    if me['parent'] == 'ROOT':
        print('- ROOT mesh', mn, me)
json.dump(dict(deformers=info, meshes=meshes), open(sys.argv[2], 'w'), ensure_ascii=False, indent=1)
