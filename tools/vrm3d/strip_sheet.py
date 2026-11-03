import sys, glob
from PIL import Image, ImageDraw
names = sys.argv[1].split(',')
rows = []
for n in names:
    fs = sorted(glob.glob(f'strips/{n}_*.png'))
    ims = [Image.open(f).convert('RGB').crop((40, 0, 260, 330)).resize((110, 165)) for f in fs]
    rows.append((n, ims))
W = max(len(r[1]) for r in rows) * 110 + 90
s = Image.new('RGB', (W, 170 * len(rows)), (214, 222, 236)); d = ImageDraw.Draw(s)
for r, (n, ims) in enumerate(rows):
    d.text((4, r * 170 + 4), n, fill=(30, 30, 50))
    for i, im in enumerate(ims): s.paste(im, (90 + i * 110, r * 170))
s.save(sys.argv[2]); print(s.size)
