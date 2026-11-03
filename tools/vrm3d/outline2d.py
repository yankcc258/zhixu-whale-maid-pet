"""Add a clean outer contour to a transparent render (hand-drawn look), then downscale to 220px WebP.
usage: outline2d.py in.png out.webp [width_px_at_220=1.6] [color=2A3146]"""
import sys,numpy as np
from PIL import Image, ImageFilter
src,dst=sys.argv[1:3]; W=float(sys.argv[3]) if len(sys.argv)>3 else 1.6; col=sys.argv[4] if len(sys.argv)>4 else '2A3146'
col=tuple(int(col[i:i+2],16) for i in (0,2,4))
im=Image.open(src).convert('RGBA'); S=im.width/220
a=np.array(im)[...,3].astype(np.float32)/255
m=Image.fromarray((a*255).astype(np.uint8))
r=int(round(W*S))
dil=np.array(m.filter(ImageFilter.MaxFilter(2*r+1))).astype(np.float32)/255
ring=np.clip(dil-a,0,1)
out=np.array(im).astype(np.float32)
line=np.zeros_like(out); line[...,0],line[...,1],line[...,2]=col; line[...,3]=ring*255
# composite: original over line
oa=out[...,3:4]/255; la=line[...,3:4]/255
res=np.empty_like(out); res[...,:3]=out[...,:3]*oa+line[...,:3]*la*(1-oa); ra=oa+la*(1-oa); res[...,3:4]=ra*255
res[...,:3]=np.where(ra>0,res[...,:3]/np.maximum(ra,1e-6),0)
Image.fromarray(res.clip(0,255).astype(np.uint8)).resize((220,220),Image.LANCZOS).save(dst,'WEBP',quality=92,method=6)
