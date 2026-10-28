"""v12 运行时的极限姿势检查：每个参数推到两端各截一张，拼成一张图。用法：python3 poses.py <runtime目录> <输出png>"""
import sys, json, subprocess, time, os
from playwright.sync_api import sync_playwright
from PIL import Image, ImageDraw, ImageFont

RT = os.path.abspath(sys.argv[1])
OUT = sys.argv[2]
HERE = os.path.dirname(os.path.abspath(__file__))
# 临时把 runtime 软链进 chk 目录
link = os.path.join(HERE, 'runtime_v12')
if os.path.islink(link):
    os.unlink(link)
os.symlink(RT, link)
POSES = [
    ('默认', {}),
    ('拉伸 1', {'ParamBodyStretch': 1}),
    ('身 Y -4', {'ParamBodyAngleY': -4}),
    ('头 Y -6', {'ParamAngleY': -6}),
    ('拉伸1 + 身Y-4', {'ParamBodyStretch': 1, 'ParamBodyAngleY': -4}),
    ('拉伸1 + 头Y-6', {'ParamBodyStretch': 1, 'ParamAngleY': -6}),
    ('拉伸 0.5', {'ParamBodyStretch': 0.5}),
    ('头 Y -9', {'ParamAngleY': -9}),
]
srv = subprocess.Popen([sys.executable, '-m', 'http.server', '8767', '--bind', '127.0.0.1', '-d', HERE], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(0.8)
font = ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc', 15)
try:
    with sync_playwright() as p:
        b = p.chromium.launch(args=['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'])
        pg = b.new_page(viewport={'width': 360, 'height': 480})
        errs = []
        pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.goto('http://127.0.0.1:8767/pview.html?m=../runtime_v12/seeko')
        r = pg.evaluate('window.ready'); assert r == 'ok', r
        ids = pg.evaluate("() => { const c = window.model.internalModel.coreModel; return c._parameterIds || c.getModel().parameters.ids; }")
        print('参数', len(ids))
        missing = set()
        pg.evaluate("() => { window.model.internalModel.eyeBlink = undefined; window.model.internalModel.breath = undefined; window.model.internalModel.physics = undefined; window.model.internalModel.motionManager.stopAllMotions(); window._ps = {}; window.model.internalModel.on('beforeModelUpdate', () => { const c = window.model.internalModel.coreModel; for (let k=0;k<c.getParameterCount();k++) c.setParameterValueByIndex(k, c.getParameterDefaultValue(k)); for (const [k, v] of Object.entries(window._ps)) c.setParameterValueById(k, v); }); }")
        tiles = []
        for name, ps in POSES:
            for k in ps:
                if k not in ids: missing.add(k)
            pg.evaluate("(ps) => { window._ps = ps; window.step(400); }", ps)
            f = f'/tmp/pose_{len(tiles)}.png'
            pg.screenshot(path=f)
            tiles.append((name, Image.open(f).convert('RGB')))
        b.close()
    cols = 4
    w, h = tiles[0][1].size
    rows = (len(tiles) + cols - 1) // cols
    S = Image.new('RGB', (w * cols, (h + 22) * rows), 'white'); d = ImageDraw.Draw(S)
    for i, (name, im) in enumerate(tiles):
        x, y = (i % cols) * w, (i // cols) * (h + 22)
        S.paste(im, (x, y + 22)); d.text((x + 4, y + 2), name, fill='black', font=font)
    S.save(OUT)
    print('缺参数:', sorted(missing)); print('页面错误:', errs); print('写出', OUT)
finally:
    srv.terminate()
