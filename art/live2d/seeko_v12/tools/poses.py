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
    ('左臂抬 10（110°）', {'ParamArmLA': 10}), ('左臂抬 8（88°）', {'ParamArmLA': 8}), ('左臂 -10（后 30°）', {'ParamArmLA': -10}),
    ('右臂抬 10', {'ParamArmRA': 10}), ('双臂 8 + 肘 8', {'ParamArmLA': 8, 'ParamArmRA': 8, 'ParamArmLB': 8, 'ParamArmRB': 8}),
    ('左肘 10（120°）', {'ParamArmLB': 10}), ('左肘 5', {'ParamArmLB': 5}), ('右肘 10', {'ParamArmRB': 10}),
    ('左腕 ±10', {'ParamWristL': 10, 'ParamWristR': -10}), ('张手', {'ParamHandL': 1, 'ParamHandR': 1}),
    ('挥手：臂 9 肘 6 张手 腕 6', {'ParamArmLA': 9, 'ParamArmLB': 6, 'ParamHandL': 1, 'ParamWristL': 6}),
    ('左腿 10（外 30°）', {'ParamLegL': 10}), ('左腿 -10', {'ParamLegL': -10}), ('双腿外 + 膝 10', {'ParamLegL': 10, 'ParamLegR': 10, 'ParamKneeL': 10, 'ParamKneeR': 10}),
    ('左膝 10', {'ParamKneeL': 10}), ('右膝 5', {'ParamKneeR': 5}),
    ('身 Z +10', {'ParamBodyAngleZ': 10}), ('身 Z -10', {'ParamBodyAngleZ': -10}), ('身 X +10', {'ParamBodyAngleX': 10}), ('身 X -10', {'ParamBodyAngleX': -10}),
    ('身 Y +10', {'ParamBodyAngleY': 10}), ('身 Y -10', {'ParamBodyAngleY': -10}),
    ('拉伸 1', {'ParamBodyStretch': 1}), ('拎起：拉伸1 Y-10 腿 膝', {'ParamBodyStretch': 1, 'ParamBodyAngleY': -6, 'ParamArmLA': 10, 'ParamArmRA': 10, 'ParamLegL': 4, 'ParamLegR': -3, 'ParamKneeL': 6, 'ParamKneeR': 3, 'ParamSkirtY': -1, 'ParamHairBackY': 1}),
    ('裙 X +1', {'ParamSkirtX': 1}), ('裙 X -1', {'ParamSkirtX': -1}), ('裙 Y -1', {'ParamSkirtY': -1}), ('裙 Y +1', {'ParamSkirtY': 1}), ('围裙 +1', {'ParamApron': 1}),
    ('后发 +1', {'ParamHairBack': 1}), ('后发 Y +1', {'ParamHairBackY': 1}), ('后发 Y -1', {'ParamHairBackY': -1}),
    ('外缕 +1', {'ParamHairBack1': 1}), ('中缕 -1', {'ParamHairBack2': -1}), ('内缕 +1', {'ParamHairBack3': 1}), ('三缕 +1', {'ParamHairBack1': 1, 'ParamHairBack2': 1, 'ParamHairBack3': 1}),
    ('头 X30 Z20 身 Z5', {'ParamAngleX': 30, 'ParamAngleZ': 20, 'ParamBodyAngleZ': 5}), ('头 Y-30 X-30', {'ParamAngleY': -30, 'ParamAngleX': -30}),
    ('呼吸 1', {'ParamBreath': 1}),
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
    cols = 8
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
