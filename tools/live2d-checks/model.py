import re
def load(path):
    return open(path,encoding='utf-8').read()
def params(s):
    return {m.group(2):m.group(1) for m in re.finditer(r'<CParameterGuid uuid="[^"]*" note="([^"]*)" xs.id="(#\d+)"',s)}
def deformers(s):
    """name -> dict(kind, block span, guid ref, target ref, grid ref)"""
    out={}
    for m in re.finditer(r'<(CWarpDeformerSource|CRotationDeformerSource) xs.id="(#\d+)"',s):
        tag=m.group(1); st=m.start(); en=s.find(f'</{tag}>',st)
        b=s[st:en]
        nm=re.search(r'<s xs.n="localName">([^<]*)</s>',b).group(1)
        g=re.search(r'<CDeformerGuid xs.n="guid" xs.ref="(#\d+)"',b).group(1)
        tm=re.search(r'<CDeformerGuid xs.n="targetDeformerGuid" (?:xs.ref="(#\d+)"|uuid="[^"]*" note="([^"]*)")',b)
        t=tm.group(1) or tm.group(2)  # Cubism 保存后第一个引用 ROOT 的地方会把定义内联进来（没有 xs.ref）
        km=re.search(r'<KeyformGridSource xs.n="keyformGridSource"( xs.ref="(#\d+)")?',b)
        if km.group(2):
            kg=s.find(f'xs.id="{km.group(2)}"'); kg=s.rfind('<KeyformGridSource',0,kg+1)
        else:
            kg=st+km.start()
        out[nm]=dict(kind=tag,start=st,end=en,guid=g,target=t,grid=kg,id=m.group(2))
    return out
def guid_names(s,defs):
    return {d['guid']:n for n,d in defs.items()}
def grid(s,st,P):
    """keyform grid: list of (combo{param:keyvalue}, formGuidRef)"""
    en=s.find('</KeyformGridSource>',st); b=s[st:en]
    # bindings
    binds={}
    for m in re.finditer(r'<KeyformBindingSource[^>]*xs.id="(#\d+)"[^>]*>',s):
        e=s.find('</KeyformBindingSource>',m.end()); bb=s[m.end():e]
        pg=re.search(r'<CParameterGuid xs.n="parameterGuid" xs.ref="(#\d+)"',bb)
        ks=re.search(r'<array_list xs.n="keys" count="\d+">(.*?)</array_list>',bb,re.S)
        if pg and ks: binds[m.group(1)]=(P.get(pg.group(1),pg.group(1)),[float(v) for v in re.findall(r'<f>([^<]*)</f>',ks.group(1))])
    res=[]
    for kog in re.finditer(r'<KeyformOnGrid>(.*?)</KeyformOnGrid>',b,re.S):
        kb=kog.group(1)
        combo={}
        for kp in re.finditer(r'<KeyformBindingSource xs.n="binding" xs.(?:ref|id)="(#\d+)".*?<i xs.n="keyIndex">(\d+)</i>',kb,re.S):
            p,keys=binds[kp.group(1)]; combo[p]=keys[int(kp.group(2))]
        fg=re.search(r'<CFormGuid xs.n="keyformGuid" xs.ref="(#\d+)"',kb).group(1)
        res.append((combo,fg))
    return res
def forms(s,d):
    """deformer keyforms: formGuidRef -> (span of positions text, values)"""
    b0=d['start']; b=s[b0:d['end']]
    out={}
    for m in re.finditer(r'<CFormGuid xs.n="guid" xs.ref="(#\d+)" />',b):
        fs=b0+m.start()
        pm=re.compile(r'<float-array xs.n="positions" count="(\d+)">([^<]*)</float-array>').search(s,fs)
        if pm and pm.start()<d['end']:
            out[m.group(1)]=(pm.start(2),pm.end(2),[float(v) for v in pm.group(2).split()])
    return out
