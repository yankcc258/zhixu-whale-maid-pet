import struct
def parse(d):
    key=struct.unpack('>I',d[14:18])[0]; kb=d[17]
    ri=lambda o: struct.unpack('>I',d[o:o+4])[0]^key
    cnt=ri(54); o=58; ents=[]
    for n in range(cnt):
        L=d[o]^kb; name=bytes(b^kb for b in d[o+1:o+1+L]).decode(); o+=1+L
        tl=d[o]^kb; tag=bytes(b^kb for b in d[o+1:o+1+tl]).decode(); o+=1+tl
        st=ri(o+4); sz=ri(o+8); ob=d[o+12]^kb; co=d[o+13]^kb
        ents.append(dict(name=name,tag=tag,start=st,size=sz,obf=ob,comp=co,eoff=o,hi=d[o:o+4])); o+=22
    return key,kb,ents,o

import zlib
def read_xml(d):
    key,kb,ents,end=parse(d)
    m=[e for e in ents if e['tag']=='main_xml'][0]
    blob=bytes(b^kb for b in d[m['start']:m['start']+m['size']])
    do=zlib.decompressobj(-15); x=do.decompress(blob[38:])
    return x, blob[:38]
def write_xml(d, xml):
    key,kb,ents,end=parse(d)
    m=[e for e in ents if e['tag']=='main_xml'][0]
    assert m['start']+m['size']==len(d)-2, 'main.xml 不是最后一个'
    blob=bytes(b^kb for b in d[m['start']:m['start']+m['size']])
    head=blob[:38]
    co=zlib.compressobj(9, zlib.DEFLATED, -15); comp=co.compress(xml)+co.flush()
    desc=b'PK\x07\x08'+struct.pack('<III', zlib.crc32(xml)&0xffffffff, len(comp), len(xml))
    nb=head+comp+desc
    enc=bytes(b^kb for b in nb)
    out=bytearray(d[:m['start']])+enc+d[-2:]
    o=m['eoff']+8
    out[o:o+4]=struct.pack('>I', len(nb)^key)
    return bytes(out)
