"""直接改 cmo3（main.xml 是个扁平的对象流，xs.id 定义、xs.ref 引用）：加参数、加旋转变形器、
把网格/变形器挂到新变形器下并换算坐标、给曲面变形器加一个参数维度（关键形态复制+平移）、改描画顺序。

坐标约定（从现有工程反推出来，见 rig_v09.py 顶部的说明）：
- 根级变形器：画布像素。
- 曲面变形器的子物件：曲面 bbox 里的 0~1 归一化坐标（neutral 时 bbox 和画布线性对应）。
- 旋转变形器的子物件：相对旋转轴心的画布像素偏移（neutral 角度 0、scale 1）。
- 旋转变形器自己的 originX/Y 用父物件的坐标系；它的 originalShape positions = 轴心的画布像素。
"""
import re
import uuid
import numpy as np


class Rig:
    def __init__(self, xml: str):
        self.s = xml
        self.nid = max(int(x) for x in re.findall(r'xs\.id="#(\d+)"', xml)) + 1
        self.nidx = max(int(x) for x in re.findall(r'xs\.idx="(\d+)"', xml)) + 1
        self.log = []

    # ---------- 基础 ----------
    def new(self):
        i, x = self.nid, self.nidx
        self.nid += 1
        self.nidx += 1
        return f'#{i}', x

    @staticmethod
    def uid():
        return str(uuid.uuid4())

    def find_block(self, tag, name):
        """按 localName 找 <tag xs.id=...> ... </tag>，返回 (start, end_exclusive)"""
        i = self.s.find(f'<s xs.n="localName">{name}</s>')
        assert i > 0, name
        st = self.s.rfind(f'<{tag} xs.id', 0, i)
        en = self.s.find(f'</{tag}>', st) + len(f'</{tag}>')
        # 确认这个 block 里的 localName 就是它（block 之间不嵌套）
        assert self.s.find('<s xs.n="localName">', st, en) == i, name
        return st, en

    def mesh_block(self, name):
        return self.find_block('CArtMeshSource', name)

    def deformer_block(self, name):
        try:
            return self.find_block('CRotationDeformerSource', name), 'rot'
        except AssertionError:
            return self.find_block('CWarpDeformerSource', name), 'warp'

    def deformer_guid(self, name):
        (st, en), _ = self.deformer_block(name)
        return re.search(r'<CDeformerGuid xs.n="guid" xs.ref="(#\d+)"', self.s[st:en]).group(1)

    def part_guid_of(self, st, en):
        return re.search(r'<CPartGuid xs.n="parentGuid" xs.ref="(#\d+)"', self.s[st:en]).group(1)

    def param_guid(self, pid):
        m = re.search(rf'<CParameterGuid uuid="[^"]*" note="{re.escape(pid)}" xs.id="(#\d+)"', self.s)
        assert m, pid
        return m.group(1)

    def bump_count(self, pos, delta):
        """pos 指向某个 <...list xs.n="..." count="N"> 开头；count += delta"""
        m = re.compile(r'count="(\d+)"').search(self.s, pos)
        self.s = self.s[: m.start(1)] + str(int(m.group(1)) + delta) + self.s[m.end(1):]

    def insert_before(self, marker, text, start=0):
        i = self.s.find(marker, start)
        assert i > 0, marker[:60]
        self.s = self.s[:i] + text + self.s[i:]
        return i

    # ---------- 坐标 ----------
    def warp_frame(self, name):
        """曲面变形器 neutral：归一化 0~1 → 画布 的线性映射 (offset, scale)。
        用它的一个子网格的 point(画布) 和 positions(归一化) 拟合。"""
        (st, en), kind = self.deformer_block(name)
        assert kind == 'warp'
        g = self.deformer_guid(name)
        # 找一个子网格
        for m in re.finditer(r'<CDeformerGuid xs.n="targetDeformerGuid" xs.ref="' + re.escape(g) + '"', self.s):
            bst = self.s.rfind('<CArtMeshSource xs.id', 0, m.start())
            ben = self.s.find('</CArtMeshSource>', bst)
            if ben < m.start():
                continue
            b = self.s[bst:ben]
            pts = np.array(re.search(r'<float-array xs.n="point" count="\d+">([^<]*)<', b).group(1).split(), float).reshape(-1, 2)
            ks, ke = self._keyforms_span(b)
            pos = np.array(re.compile(r'<float-array xs.n="positions" count="\d+"[^>]*>([^<]*)<').search(b, ks).group(1).split(), float).reshape(-1, 2)
            if len(pts) != len(pos) or len(pts) < 3:
                continue
            off, sc = [], []
            for ax in (0, 1):
                A = np.c_[pos[:, ax], np.ones(len(pos))]
                sol = np.linalg.lstsq(A, pts[:, ax], rcond=None)[0]
                assert np.abs(A @ sol - pts[:, ax]).max() < 0.05, (name, ax)
                sc.append(sol[0])
                off.append(sol[1])
            return np.array(off), np.array(sc)
        raise RuntimeError('no mesh child: ' + name)

    def rot_pivot(self, name):
        """旋转变形器的轴心（画布像素）"""
        (st, en), kind = self.deformer_block(name)
        assert kind == 'rot'
        pid = re.search(r'<float-array xs.n="positions" xs.ref="(#\d+)"', self.s[st:en]).group(1)
        m = re.search(r'<float-array count="2" xs.id="' + re.escape(pid) + r'"[^>]*>([^<]*)<', self.s)
        return np.array(m.group(1).split(), float)

    def frame_of(self, parent):
        """父物件坐标 → 画布：返回 (offset, scale)。parent=None 是根（画布）。"""
        if parent is None:
            return np.zeros(2), np.ones(2)
        (st, en), kind = self.deformer_block(parent)
        if kind == 'warp':
            return self.warp_frame(parent)
        return self.rot_pivot(parent), np.ones(2)

    # ---------- 参数 ----------
    def add_param(self, pid, name, mn, mx, default, desc=''):
        g, gx = self.new()
        i, ix = self.new()
        self.insert_before('<CParameterGroup xs.id=', f'<CParameterGuid uuid="{self.uid()}" note="{pid}" xs.id="{g}" xs.idx="{gx}" />\n')
        self.insert_before('<CParameterId idstr="ParamAngleX"', f'<CParameterId idstr="{pid}" xs.id="{i}" xs.idx="{ix}" />\n')
        # Root Parameter Group 的 _childGuids
        gp = self.s.find('<s xs.n="name">Root Parameter Group</s>')
        lp = self.s.find('<carray_list xs.n="_childGuids"', gp)
        le = self.s.find('</carray_list>', lp)
        self.s = self.s[:le] + f'<CParameterGuid xs.ref="{g}" />\n' + self.s[le:]
        self.bump_count(lp, 1)
        # CParameterSourceSet
        sp = self.s.find('<CParameterSourceSet')
        lp = self.s.find('<carray_list xs.n="_sources"', sp)
        le = self.s.find('</carray_list>', lp)
        src = (
            '<CParameterSource>\n<i xs.n="decimalPlaces">3</i>\n'
            f'<CParameterGuid xs.n="guid" xs.ref="{g}" />\n<f xs.n="snapEpsilon">0.001</f>\n'
            f'<f xs.n="minValue">{mn}</f>\n<f xs.n="maxValue">{mx}</f>\n<f xs.n="defaultValue">{default}</f>\n'
            f'<b xs.n="isRepeat">false</b>\n<CParameterId xs.n="id" xs.ref="{i}" />\n<Type xs.n="paramType" v="NORMAL" />\n'
            f'<s xs.n="name">{name}</s>\n<s xs.n="description">{desc}</s>\n<b xs.n="combined">false</b>\n'
            '<CParameterGroupGuid xs.n="parentGroupGuid" xs.ref="#0" />\n</CParameterSource>\n'
        )
        self.s = self.s[:le] + src + self.s[le:]
        self.bump_count(lp, 1)
        # 随机姿势设置的两张表
        rp = self.s.find('<CRandomPoseSettingManager')
        lp = self.s.find('<array_list xs.n="parameters.keys"', rp)
        le = self.s.find('</array_list>', lp)
        self.s = self.s[:le] + f'<CParameterId xs.ref="{i}" />\n' + self.s[le:]
        self.bump_count(lp, 1)
        lp = self.s.find('<array_list xs.n="parameters.values"', rp)
        le = self.s.find('</array_list>', lp)
        self.s = self.s[:le] + '<CRandomPoseParamData>\n<b xs.n="isEnable">true</b>\n</CRandomPoseParamData>\n' + self.s[le:]
        self.bump_count(lp, 1)
        self.log.append(f'参数 {pid}（{name}）{mn}~{mx}')
        return g

    # ---------- 关键形态网格（binding + grid）----------
    def _grid(self, axes):
        """axes: [(paramGuid, [keys...]), ...]。返回 (grid_id, grid_text_without_formrefs, binding_texts, combos)
        combos：按网格顺序的 [(keyIndex per axis)]；form guid 由调用方填。"""
        gid, gx = self.new()
        binds = []
        btexts = []
        for pg, keys in axes:
            bid, bx = self.new()
            binds.append(bid)
            ks = ''.join(f'<f>{float(k)}</f>\n' for k in keys)
            btexts.append(
                f'<KeyformBindingSource xs.id="{bid}" xs.idx="{bx}">\n<KeyformGridSource xs.n="_gridSource" xs.ref="{gid}" />\n'
                f'<CParameterGuid xs.n="parameterGuid" xs.ref="{pg}" />\n<array_list xs.n="keys" count="{len(keys)}">\n{ks}</array_list>\n'
                '<InterpolationType xs.n="interpolationType" v="LINEAR" />\n<ExtendedInterpolationType xs.n="extendedInterpolationType" v="LINEAR" />\n'
                '<i xs.n="insertPointCount">1</i>\n<f xs.n="extendedInterpolationScale">1.0</f>\n<s xs.n="description" />\n</KeyformBindingSource>\n'
            )
        import itertools
        combos = list(itertools.product(*[range(len(k)) for _, k in axes]))
        return gid, gx, binds, btexts, combos

    def _grid_text(self, gid, gx, binds, combos, form_ids, axes_n):
        ent = []
        for c, fid in zip(combos, form_ids):
            kp = ''.join(f'<KeyOnParameter>\n<KeyformBindingSource xs.n="binding" xs.ref="{b}" />\n<i xs.n="keyIndex">{k}</i>\n</KeyOnParameter>\n' for b, k in zip(binds, c))
            ent.append(f'<KeyformOnGrid>\n<KeyformGridAccessKey xs.n="accessKey">\n<array_list xs.n="_keyOnParameterList" count="{axes_n}">\n{kp}</array_list>\n</KeyformGridAccessKey>\n<CFormGuid xs.n="keyformGuid" xs.ref="{fid}" />\n</KeyformOnGrid>\n')
        bl = ''.join(f'<KeyformBindingSource xs.ref="{b}" />\n' for b in binds)
        return (f'<KeyformGridSource xs.id="{gid}" xs.idx="{gx}">\n<array_list xs.n="keyformsOnGrid" count="{len(combos)}">\n{"".join(ent)}</array_list>\n'
                f'<array_list xs.n="keyformBindings" count="{len(binds)}">\n{bl}</array_list>\n</KeyformGridSource>\n')

    # ---------- 旋转变形器 ----------
    def add_rot(self, name, parent, pivot, axes, forms, children, handle=100.0, children_parent='SAME'):
        """name：显示名；parent：父变形器名（None=根）；pivot：轴心画布像素 (x,y)
        axes：[(paramId, [keys])]；forms：函数 (keyvalues tuple) -> (angle, dx, dy, scale)，dx/dy 是轴心在画布上的偏移
        children：要挂进来的网格名列表（它们现在的父物件必须就是 parent）。返回变形器 guid ref。"""
        pivot = np.array(pivot, float)
        off, sc = self.frame_of(parent)
        origin = (pivot - off) / sc  # 父坐标系里的轴心
        pguids = [(self.param_guid(p), k) for p, k in axes]
        gid, gx, binds, btexts, combos = self._grid(pguids)
        dg, dgx = self.new()  # CDeformerGuid
        did, dix = self.new()  # CRotationDeformerSource
        pid, pix = self.new()  # positions
        cid, cix = self.new()  # CoordType
        fids = [self.new() for _ in combos]
        if parent:
            parent_ref = self.deformer_guid(parent)
        else:
            parent_ref = re.search(r'<CDeformerGuid uuid="[^"]*" note="ROOT" xs.id="(#\d+)"', self.s).group(1)
        # 父 Part：跟父变形器/第一个子网格一样
        if parent:
            (pst, pen), _ = self.deformer_block(parent)
        else:
            pst, pen = self.mesh_block(children[0])
        part = self.part_guid_of(pst, pen)
        rn = 1 + max([int(x) for x in re.findall(r'idstr="Rotation(\d+)"', self.s)] + [0])
        kf = []
        for c, (fid, fx) in zip(combos, fids):
            vals = tuple(axes[i][1][k] for i, k in enumerate(c))
            ang, dx, dy, scl = forms(vals)
            ox, oy = origin + np.array([dx, dy]) / sc
            kf.append(
                f'<CRotationDeformerForm angle="{ang}" originX="{ox:.7g}" originY="{oy:.7g}" scale="{scl}" isReflectX="false" isReflectY="false">\n'
                f'<ACDeformerForm xs.n="super">\n<ACForm xs.n="super">\n<CFormGuid xs.n="guid" xs.ref="{fid}" />\n<b xs.n="isAnimatedForm">false</b>\n'
                f'<b xs.n="isLocalAnimatedForm">false</b>\n<CRotationDeformerSource xs.n="_source" xs.ref="{did}" />\n<null xs.n="name" />\n<s xs.n="notes" />\n</ACForm>\n'
                '<f xs.n="opacity">1.0</f>\n<CFloatColor xs.n="multiplyColor" red="1.0" green="1.0" blue="1.0" alpha="1.0" />\n'
                f'<CFloatColor xs.n="screenColor" red="0.0" green="0.0" blue="0.0" alpha="1.0" />\n<CoordType xs.n="coordType" xs.ref="{cid}" />\n</ACDeformerForm>\n</CRotationDeformerForm>\n'
            )
        shape = (
            f'<float-array xs.n="positions" xs.ref="{pid}" />\n<s xs.n="lastUpdatedTimeString">2026-10-23T23:00:00.000000000+09:00[Asia/Tokyo]</s>\n'
            '<b xs.n="autoRefreshIsAvailable">true</b>\n<CreationMethod xs.n="creationMethod" v="DEFORMER_CREATED" />\n<f xs.n="baseAngle">0.0</f>\n'
            f'<f xs.n="globalAngle">0.0</f>\n<f xs.n="globalScale">1.0</f>\n<f xs.n="circleRadiusTimesScale">{handle/3:.1f}</f>\n<f xs.n="handleLength">{handle:.1f}</f>\n'
            '<b xs.n="isReflectX">false</b>\n<b xs.n="isReflectY">false</b>\n'
        )
        block = (
            f'<CRotationDeformerSource xs.id="{did}" xs.idx="{dix}">\n<ACDeformerSource xs.n="super">\n<ACParameterControllableSource xs.n="super">\n'
            f'<s xs.n="localName">{name}</s>\n<b xs.n="isVisible">true</b>\n<b xs.n="isLocked">false</b>\n<CPartGuid xs.n="parentGuid" xs.ref="{part}" />\n'
            f'<KeyformGridSource xs.n="keyformGridSource" xs.ref="{gid}" />\n<KeyFormMorphTargetSet xs.n="keyformMorphTargetSet">\n<carray_list xs.n="_morphTargets" count="0" />\n'
            '<MorphTargetBlendWeightConstraintSet xs.n="blendWeightConstraintSet">\n<carray_list xs.n="_constraints" count="0" />\n</MorphTargetBlendWeightConstraintSet>\n</KeyFormMorphTargetSet>\n'
            '<carray_list xs.n="_extensions" count="1">\n<CDeformerOriginalShapeExtension>\n<ACExtension xs.n="super">\n'
            f'<CExtensionGuid xs.n="guid" uuid="{self.uid()}" note="(no debug info)" />\n<CRotationDeformerSource xs.n="_owner" xs.ref="{did}" />\n</ACExtension>\n'
            f'<RotationDeformerOriginalShape xs.n="originalShape">\n<ACDeformerOriginalShape xs.n="super">\n{shape}</ACDeformerOriginalShape>\n{shape}</RotationDeformerOriginalShape>\n'
            '</CDeformerOriginalShapeExtension>\n</carray_list>\n<null xs.n="internalColor_direct_argb" />\n<CLabelColor xs.n="labelColor" customizedColorInt="-1">\n'
            '<CLabelColorType xs.n="labelType" v="GRAY" />\n</CLabelColor>\n</ACParameterControllableSource>\n'
            f'<CDeformerGuid xs.n="guid" xs.ref="{dg}" />\n<CDeformerId xs.n="id" idstr="Rotation{rn}" />\n<CDeformerGuid xs.n="targetDeformerGuid" xs.ref="{parent_ref}" />\n</ACDeformerSource>\n'
            f'<b xs.n="useBoneUi_testImpl">true</b>\n<carray_list xs.n="keyforms" count="{len(kf)}">\n{"".join(kf)}</carray_list>\n'
            f'<f xs.n="handleLengthOnCanvas">{handle:.1f}</f>\n<f xs.n="circleRadiusOnCanvas">{handle/3:.1f}</f>\n<f xs.n="baseAngle">0.0</f>\n</CRotationDeformerSource>\n'
        )
        trail = (
            f'<float-array count="2" xs.id="{pid}" xs.idx="{pix}">{pivot[0]:.7g} {pivot[1]:.7g}</float-array>\n'
            + ''.join(f'<CFormGuid uuid="{self.uid()}" note="Key [  ]" xs.id="{fid}" xs.idx="{fx}" />\n' for fid, fx in fids)
            + f'<CoordType xs.id="{cid}" xs.idx="{cix}">\n<s xs.n="coordName">DeformerLocal</s>\n</CoordType>\n'
        )
        text = (f'<CDeformerGuid uuid="{self.uid()}" note="Rotation{rn}" xs.id="{dg}" xs.idx="{dgx}" />\n'
                + self._grid_text(gid, gx, binds, combos, [f for f, _ in fids], len(axes)) + ''.join(btexts) + block + trail)
        # 所有自由对象都在 <shared> 里
        self.insert_before('</shared>', text)
        # 登记：Part 的 _childGuids、CDeformerSourceSet._sources
        ps = self.s.find(f'<CPartGuid xs.n="guid" xs.ref="{part}"')
        assert ps > 0
        ps = self.s.rfind('<CPartSource xs.id', 0, ps)
        lp = self.s.find('<carray_list xs.n="_childGuids"', ps)
        self.s = self.s[: self.s.find('>', lp) + 1] + f'\n<CDeformerGuid xs.ref="{dg}" />' + self.s[self.s.find('>', lp) + 1:]
        self.bump_count(lp, 1)
        ds = self.s.find('<CDeformerSourceSet xs.n="deformerSourceSet">')
        lp = self.s.find('<carray_list xs.n="_sources"', ds)
        le = self.s.find('</carray_list>', lp)
        self.s = self.s[:le] + f'<CRotationDeformerSource xs.ref="{did}" />\n' + self.s[le:]
        self.bump_count(lp, 1)
        # 子物件挂进来：targetDeformerGuid 换掉，positions 换算到新轴心
        for ch in children:
            self.reparent_mesh(ch, parent if children_parent == 'SAME' else children_parent, pivot, dg)
        self.log.append(f'旋转变形器 {name}（父 {parent}，轴心 {pivot.round(1).tolist()}，{len(kf)} 个关键形态）← {children}')
        return dg

    def reparent_mesh(self, name, old_parent, new_pivot, new_guid):
        st, en = self.mesh_block(name)
        b = self.s[st:en]
        off, sc = self.frame_of(old_parent)
        m = re.search(r'<CDeformerGuid xs.n="targetDeformerGuid" xs.ref="(#\d+)"', b)
        b = b[: m.start(1)] + new_guid + b[m.end(1):]
        # 只改关键形态里的 positions；网格块末尾还有一份画布坐标缓存（给贴图用的），不能动
        ks, ke = self._keyforms_span(b)
        out, p = [], 0
        for pm in re.finditer(r'(<float-array xs.n="positions" count="\d+"[^>]*>)([^<]*)<', b):
            if not (ks <= pm.start() < ke):
                continue
            v = np.array(pm.group(2).split(), float).reshape(-1, 2)
            canvas = off + v * sc
            local = canvas - np.array(new_pivot, float)
            out.append(b[p: pm.start(2)] + ' '.join(f'{x:.7g}' for x in local.reshape(-1)))
            p = pm.end(2)
        out.append(b[p:])
        self.s = self.s[:st] + ''.join(out) + self.s[en:]

    @staticmethod
    def _keyforms_span(b):
        ks = b.find('<carray_list xs.n="keyforms"')
        ke = b.rfind('</CArtMeshForm>')
        assert ks > 0 and ke > ks
        return ks, ke

    # ---------- 曲面变形器加一个参数维度 ----------
    def warp_add_axis(self, name, pid, keys, shift):
        """给曲面变形器 name 的关键形态网格加参数 pid（keys），每个已有关键形态在新轴上复制 len(keys) 份，
        shift(keyvalue, positions ndarray(N,2)) -> positions。要求：现有网格要么 0 轴、要么 1 轴。"""
        (st, en), kind = self.deformer_block(name)
        assert kind == 'warp'
        b = self.s[st:en]
        # 现有 grid
        gm = re.search(r'<KeyformGridSource xs.n="keyformGridSource"( xs.ref="(#\d+)")?', b)
        if gm.group(2):
            gst = self.s.find(f'<KeyformGridSource xs.id="{gm.group(2)}"')
            gen = self.s.find('</KeyformGridSource>', gst) + len('</KeyformGridSource>')
            inline = False
        else:
            gst = st + gm.start()
            gen = self.s.find('</KeyformGridSource>', gst) + len('</KeyformGridSource>')
            inline = True
        gb = self.s[gst:gen]
        old = []  # [(binding_ref, keyIndex, formref)]
        for kog in re.finditer(r'<KeyformOnGrid>(.*?)</KeyformOnGrid>', gb, re.S):
            kp = re.findall(r'<KeyformBindingSource xs.n="binding" xs.ref="(#\d+)" />\s*<i xs.n="keyIndex">(\d+)</i>', kog.group(1))
            fr = re.search(r'<CFormGuid xs.n="keyformGuid" xs.ref="(#\d+)"', kog.group(1)).group(1)
            old.append((kp, fr))
        obinds = re.findall(r'<KeyformBindingSource xs.ref="(#\d+)" />', gb[gb.find('keyformBindings'):])
        # 新 binding
        gid_ref = gm.group(2) or None
        bid, bx = self.new()
        pg = self.param_guid(pid)
        ks = ''.join(f'<f>{float(k)}</f>\n' for k in keys)
        gref = gid_ref
        if inline:
            # 把 grid 抽成独立对象，方便引用
            gref, gx2 = self.new()
        btext = (
            f'<KeyformBindingSource xs.id="{bid}" xs.idx="{bx}">\n<KeyformGridSource xs.n="_gridSource" xs.ref="{gref}" />\n'
            f'<CParameterGuid xs.n="parameterGuid" xs.ref="{pg}" />\n<array_list xs.n="keys" count="{len(keys)}">\n{ks}</array_list>\n'
            '<InterpolationType xs.n="interpolationType" v="LINEAR" />\n<ExtendedInterpolationType xs.n="extendedInterpolationType" v="LINEAR" />\n'
            '<i xs.n="insertPointCount">1</i>\n<f xs.n="extendedInterpolationScale">1.0</f>\n<s xs.n="description" />\n</KeyformBindingSource>\n'
        )
        # 现有关键形态的 form 文本
        kfl = self.s.find('<carray_list xs.n="keyforms"', st)
        kfe = self.s.find('</carray_list>', kfl)
        forms = {}
        for fm in re.finditer(r'<CWarpDeformerForm>(.*?)</CWarpDeformerForm>\n?', self.s[kfl:kfe], re.S):
            fr = re.search(r'<CFormGuid xs.n="guid" xs.ref="(#\d+)"', fm.group(1)).group(1)
            forms[fr] = fm.group(0)
        did = re.search(r'<CWarpDeformerSource xs.id="(#\d+)"', b).group(1)
        new_entries, new_forms, new_guids = [], [], []
        for kp, fr in old:
            ftxt = forms[fr]
            pm = re.search(r'<float-array xs.n="positions" count="\d+">([^<]*)<', ftxt)
            pos = np.array(pm.group(1).split(), float).reshape(-1, 2)
            for ki, kv in enumerate(keys):
                if abs(kv) < 1e-9:
                    fid = fr
                else:
                    fid, fx = self.new()
                    new_guids.append((fid, fx))
                    npos = shift(kv, pos.copy())
                    nf = ftxt[: pm.start(1)] + ' '.join(f'{x:.7g}' for x in npos.reshape(-1)) + ftxt[pm.end(1):]
                    nf = nf.replace(f'<CFormGuid xs.n="guid" xs.ref="{fr}" />', f'<CFormGuid xs.n="guid" xs.ref="{fid}" />')
                    new_forms.append(nf)
                kps = ''.join(f'<KeyOnParameter>\n<KeyformBindingSource xs.n="binding" xs.ref="{bb}" />\n<i xs.n="keyIndex">{kk}</i>\n</KeyOnParameter>\n' for bb, kk in kp)
                kps += f'<KeyOnParameter>\n<KeyformBindingSource xs.n="binding" xs.ref="{bid}" />\n<i xs.n="keyIndex">{ki}</i>\n</KeyOnParameter>\n'
                new_entries.append(f'<KeyformOnGrid>\n<KeyformGridAccessKey xs.n="accessKey">\n<array_list xs.n="_keyOnParameterList" count="{len(kp)+1}">\n{kps}</array_list>\n</KeyformGridAccessKey>\n<CFormGuid xs.n="keyformGuid" xs.ref="{fid}" />\n</KeyformOnGrid>\n')
        bl = ''.join(f'<KeyformBindingSource xs.ref="{bb}" />\n' for bb in obinds + [bid])
        head = f'<KeyformGridSource xs.id="{gref}" xs.idx="{gx2}">\n' if inline else gb[: gb.find('>') + 1] + '\n'
        ngb = (head + f'<array_list xs.n="keyformsOnGrid" count="{len(new_entries)}">\n{"".join(new_entries)}</array_list>\n'
               f'<array_list xs.n="keyformBindings" count="{len(obinds)+1}">\n{bl}</array_list>\n</KeyformGridSource>\n')
        # 写回：先改后面的（keyforms 列表），再改前面的 grid，位置才不乱
        self.s = self.s[:kfe] + ''.join(new_forms) + self.s[kfe:]
        self.bump_count(kfl, len(new_forms))
        if inline:
            self.s = self.s[:gst] + f'<KeyformGridSource xs.n="keyformGridSource" xs.ref="{gref}" />\n' + self.s[gen:]
            # 独立 grid 对象 + binding + 新 form guid 放到变形器 block 后面
            (st2, en2), _ = self.deformer_block(name)
            self.s = self.s[:en2] + '\n' + ngb + btext + ''.join(f'<CFormGuid uuid="{self.uid()}" note="Key [  ]" xs.id="{f}" xs.idx="{x}" />\n' for f, x in new_guids) + self.s[en2:]
        else:
            self.s = self.s[:gst] + ngb + btext + ''.join(f'<CFormGuid uuid="{self.uid()}" note="Key [  ]" xs.id="{f}" xs.idx="{x}" />\n' for f, x in new_guids) + self.s[gen:]
        self.log.append(f'曲面 {name} 加参数 {pid} {keys}：关键形态 {len(old)} → {len(new_entries)}')

    def warp_edit(self, name, fn):
        """对曲面变形器每个关键形态：fn(combo:{param:key}, positions) -> positions。combo 用 model.grid 解析。"""
        import model as M
        (st, en), kind = self.deformer_block(name)
        D = M.deformers(self.s)
        P = M.params(self.s)
        d = D[name]
        g = M.grid(self.s, d['grid'], P)
        F = M.forms(self.s, d)
        edits = []
        for combo, fg in g:
            a, b, vals = F[fg]
            pos = np.array(vals).reshape(-1, 2)
            npos = fn(combo, pos)
            edits.append((a, b, ' '.join(f'{x:.7g}' for x in np.asarray(npos).reshape(-1))))
        for a, b, t in sorted(edits, reverse=True):
            self.s = self.s[:a] + t + self.s[b:]
        self.log.append(f'曲面 {name} 关键形态重算 ×{len(edits)}')

    def rot_set_forms(self, name, fn):
        """旋转变形器每个关键形态：fn(combo, angle, originX, originY, scale) -> (angle, ox, oy, scale)"""
        import model as M
        (st, en), kind = self.deformer_block(name)
        D = M.deformers(self.s)
        P = M.params(self.s)
        d = D[name]
        g = {fg: combo for combo, fg in M.grid(self.s, d['grid'], P)}
        b = self.s[st:en]
        out, p = [], 0
        for m in re.finditer(r'<CRotationDeformerForm angle="([^"]*)" originX="([^"]*)" originY="([^"]*)" scale="([^"]*)"', b):
            tail = b[m.end(): m.end() + 400]
            fg = re.search(r'CFormGuid xs.n="guid" xs.ref="(#\d+)"', tail).group(1)
            ang, ox, oy, sc = fn(g[fg], *[float(x) for x in m.groups()])
            out.append(b[p: m.start()] + f'<CRotationDeformerForm angle="{ang}" originX="{ox:.7g}" originY="{oy:.7g}" scale="{sc}"')
            p = m.end()
        out.append(b[p:])
        self.s = self.s[:st] + ''.join(out) + self.s[en:]
        self.log.append(f'旋转 {name} 关键形态重设')

    def set_draw_order(self, name, order):
        st, en = self.mesh_block(name)
        b = self.s[st:en]
        nb, n = re.subn(r'<i xs.n="drawOrder">\d+</i>', f'<i xs.n="drawOrder">{order}</i>', b)
        self.s = self.s[:st] + nb + self.s[en:]
        self.log.append(f'{name} 描画顺序 → {order}（{n} 处）')

    # ---------- 挪旋转变形器的轴心（子物件跟着换算，画面不变）----------
    def parent_name(self, name):
        import model as M
        D = M.deformers(self.s)
        t = D[name]['target']
        for n, dd in D.items():
            if dd['guid'] == t:
                return n
        return None

    def rot_move_pivot(self, name, new_pivot):
        import model as M
        new_pivot = np.array(new_pivot, float)
        old = self.rot_pivot(name)
        delta = new_pivot - old
        par = self.parent_name(name)
        off, sc = self.frame_of(par)
        dpar = delta / sc
        (st, en), kind = self.deformer_block(name)
        assert kind == 'rot'
        b = self.s[st:en]
        b2 = re.sub(r'originX="([^"]*)" originY="([^"]*)"',
                    lambda m: f'originX="{float(m.group(1)) + dpar[0]:.7g}" originY="{float(m.group(2)) + dpar[1]:.7g}"', b)
        pid = re.search(r'<float-array xs.n="positions" xs.ref="(#\d+)"', b).group(1)
        self.s = self.s[:st] + b2 + self.s[en:]
        m = re.search(r'(<float-array count="2" xs.id="' + re.escape(pid) + r'"[^>]*>)([^<]*)<', self.s)
        self.s = self.s[: m.start(2)] + f'{new_pivot[0]:.7g} {new_pivot[1]:.7g}' + self.s[m.end(2):]
        g = self.deformer_guid(name)
        D = M.deformers(self.s)
        for n, dd in D.items():
            if dd['target'] == g:
                assert dd['kind'] == 'CRotationDeformerSource', ('warp child not supported', n)
                cst, cen = dd['start'], dd['end']
                cb = re.sub(r'originX="([^"]*)" originY="([^"]*)"',
                            lambda m: f'originX="{float(m.group(1)) - delta[0]:.7g}" originY="{float(m.group(2)) - delta[1]:.7g}"', self.s[cst:cen])
                self.s = self.s[:cst] + cb + self.s[cen:]
        # 子网格
        for m in list(re.finditer(r'<CDeformerGuid xs.n="targetDeformerGuid" xs.ref="' + re.escape(g) + '"', self.s))[::-1]:
            bst = self.s.rfind('<CArtMeshSource xs.id', 0, m.start())
            ben = self.s.find('</CArtMeshSource>', bst)
            if ben < m.start() or bst < 0:
                continue
            mb = self.s[bst:ben]
            ks, ke = self._keyforms_span(mb)
            out, p = [], 0
            for pm in re.finditer(r'(<float-array xs.n="positions" count="\d+"[^>]*>)([^<]*)<', mb):
                if not (ks <= pm.start() < ke):
                    continue
                v = np.array(pm.group(2).split(), float).reshape(-1, 2) - delta
                out.append(mb[p: pm.start(2)] + ' '.join(f'{x:.7g}' for x in v.reshape(-1)))
                p = pm.end(2)
            out.append(mb[p:])
            self.s = self.s[:bst] + ''.join(out) + self.s[ben:]
        self.log.append(f'旋转 {name} 轴心 {old.round(1).tolist()} → {new_pivot.tolist()}')
