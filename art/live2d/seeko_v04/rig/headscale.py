"""把某个旋转变形器（默认「面部旋转」）所有关键形态的 scale 改成指定倍率：整颗头（脸、头发、耳鳍、头饰）
以它的中心为准一起缩放，用来调头身比例。
用法：python3 headscale.py 源.cmo3 目标.cmo3 0.85 [变形器名]"""
import sys, re
sys.path.insert(0, '/tmp/claude-0/-home-claude/5d1ddcc7-fe5e-5109-8e8f-60afaa718bac/scratchpad/caff')
from caff import read_xml, write_xml

src, dst, k = sys.argv[1], sys.argv[2], float(sys.argv[3])
name = sys.argv[4] if len(sys.argv) > 4 else '面部旋转'
d = open(src, 'rb').read()
s = read_xml(d)[0].decode('utf-8')

# 找到这个变形器 → 它的关键形态网格 → 网格里每个关键形态的 guid
i = s.find(f'<s xs.n="localName">{name}</s>')
assert i > 0, '找不到变形器 ' + name
head = s.rfind('<CRotationDeformerSource', 0, i)
seg = s[i:i + 3000]
g = re.search(r'<KeyformGridSource xs\.n="keyformGridSource" (?:xs\.ref="(#\d+)"|xs\.id="(#\d+)")', seg)
gid = g.group(1) or g.group(2)
gi = s.find(f'<KeyformGridSource xs.id="{gid}"')
gj = s.find('</KeyformGridSource>', gi)
guids = re.findall(r'<CFormGuid xs\.n="keyformGuid" xs\.ref="(#\d+)"', s[gi:gj])
print(name, '网格', gid, '关键形态', guids)

edits = []
for m in re.finditer(r'<CRotationDeformerForm [^>]*>', s):
    tail = s[m.end():m.end() + 800]
    gg = re.search(r'CFormGuid xs\.n="guid" xs\.(?:ref|id)="(#\d+)"', tail)
    if gg and gg.group(1) in guids:
        tag = m.group(0)
        new = re.sub(r'scale="[^"]*"', f'scale="{k}"', tag)
        edits.append((m.start(), m.end(), new))
        print('  ', tag[23:110], '→ scale', k)
assert len(edits) == len(guids), (len(edits), len(guids))
for a, b, t in sorted(edits, reverse=True):
    s = s[:a] + t + s[b:]
open(dst, 'wb').write(write_xml(d, s.encode('utf-8')))
print('写入', dst)
