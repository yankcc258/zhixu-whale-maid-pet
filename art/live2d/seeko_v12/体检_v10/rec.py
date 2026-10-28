import sys, json, subprocess, time, os
from playwright.sync_api import sync_playwright
from PIL import Image, ImageDraw, ImageFont
OUT='/home/claude/v12/chk/out'; os.makedirs(OUT, exist_ok=True)
srv=subprocess.Popen([sys.executable,'-m','http.server','8766','--bind','127.0.0.1','-d','/home/claude/v12/chk'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); time.sleep(0.8)
MOTIONS=['Idle:0','Idle:1','Idle:2','Idle:3','Idle:4','Idle:5','Wave','Hop','Cheer','Tilt','Stretch','Flinch','Nod','Shake','Swing','Shy','Slump','Kick','Walk','Pant','Hang','Fall','Land']
font=ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',14) if os.path.exists('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc') else None
try:
  with sync_playwright() as p:
    b=p.chromium.launch(args=['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
    pg=b.new_page(viewport={'width':360,'height':480})
    pg.goto('http://127.0.0.1:8766/pview.html'); 
    r=pg.evaluate('window.ready'); assert r=='ok', r
    pg.evaluate("() => { window.model.internalModel.eyeBlink = undefined; window.step(500); }")
    for m in MOTIONS:
        g,i=(m.split(':')+['0'])[:2]
        # 先回中立
        pg.evaluate("() => { window.model.internalModel.motionManager.stopAllMotions(); const c=window.model.internalModel.coreModel; for (let k=0;k<c.getParameterCount();k++) c.setParameterValueByIndex(k, c.getParameterDefaultValue(k)); window.step(300); }")
        dur = pg.evaluate("async ([g,i]) => { const mm=window.model.internalModel.motionManager; await window.model.motion(g, i, 3); const def = mm.definitions[g][i]; const j = await fetch('runtime/'+def.File).then(r=>r.json()); return j.Meta.Duration; }", [g,int(i)])
        dur=min(dur, 6.0)
        n=max(12, min(40, round(dur/0.1)))
        frames=[]
        for k in range(n):
            pg.evaluate("window.step(100)")
            f=f'{OUT}/f_{g}{i}_{k:02d}.png'; pg.screenshot(path=f); frames.append(f)
        ims=[Image.open(f).convert('RGB') for f in frames]
        # GIF (actual 100ms/frame)
        ims[0].save(f'{OUT}/{g}{i}.gif', save_all=True, append_images=ims[1:], duration=100, loop=0)
        # contact sheet, half size, 10 per row
        th=[im.resize((180,240)) for im in ims]
        cols=10; rows=(len(th)+cols-1)//cols
        S=Image.new('RGB',(180*cols,(240+18)*rows),'white'); d=ImageDraw.Draw(S)
        for k,im in enumerate(th):
            x,y=(k%cols)*180,(k//cols)*258; S.paste(im,(x,y+18)); d.text((x+4,y+1),f'{g}{i} {k*100}ms',fill='black',font=font)
        S.save(f'{OUT}/sheet_{g}{i}.png')
        for f in frames: os.remove(f)
        print(m, 'dur', round(dur,2), 'frames', n)
    b.close()
finally:
    srv.terminate()
