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

    # ---------- 新建曲面变形器 ----------
    def add_warp(self, name, parent, bbox, axes, forms, children, cols=5, rows=5, child_deformers=()):
        """新建一个曲面变形器。
        name：显示名；parent：父变形器名（None=根）；bbox：画布像素 (x0,y0,x1,y1)，neutral 时格点均匀铺满它
        axes：[(paramId, [keys])]（可为空 → 只有一个关键形态）
        forms：函数 (keyvalues tuple, grid ndarray((rows+1)*(cols+1),2) 画布像素) -> 画布像素 ndarray；None = 全部等于 neutral
        children：要挂进来的网格名（现在的父物件必须是 parent）；child_deformers：要挂进来的变形器名（同上）
        返回变形器 guid ref。"""
        bbox = np.array(bbox, float)
        off, sc = self.frame_of(parent)
        # neutral 格点（画布）
        xs = np.linspace(bbox[0], bbox[2], cols + 1)
        ys = np.linspace(bbox[1], bbox[3], rows + 1)
        grid = np.array([[x, y] for y in ys for x in xs])
        pguids = [(self.param_guid(p), k) for p, k in axes]
        if axes:
            gid, gx, binds, btexts, combos = self._grid(pguids)
        else:
            gid, gx, binds, btexts, combos = (*self.new(), [], [], [()])
        dg, dgx = self.new()
        did, dix = self.new()
        pid, pix = self.new()
        cid, cix = self.new()
        fids = [self.new() for _ in combos]
        if parent:
            parent_ref = self.deformer_guid(parent)
            (pst, pen), _ = self.deformer_block(parent)
        else:
            parent_ref = re.search(r'<CDeformerGuid uuid="[^"]*" note="ROOT" xs.id="(#\d+)"', self.s).group(1)
            pst, pen = self.mesh_block(children[0]) if children else self.deformer_block(child_deformers[0])[0]
        part = self.part_guid_of(pst, pen)
        wn = 1 + max([int(x) for x in re.findall(r'idstr="Warp(\d+)"', self.s)] + [0])
        kf = []
        for c, (fid, fx) in zip(combos, fids):
            vals = tuple(axes[i][1][k] for i, k in enumerate(c))
            g = grid.copy() if forms is None else np.asarray(forms(vals, grid.copy()), float)
            local = (g - off) / sc  # 父坐标系
            pos = ' '.join(f'{x:.7g}' for x in local.reshape(-1))
            kf.append(
                '<CWarpDeformerForm>\n<ACDeformerForm xs.n="super">\n<ACForm xs.n="super">\n'
                f'<CFormGuid xs.n="guid" xs.ref="{fid}" />\n<b xs.n="isAnimatedForm">false</b>\n<b xs.n="isLocalAnimatedForm">false</b>\n'
                f'<CWarpDeformerSource xs.n="_source" xs.ref="{did}" />\n<null xs.n="name" />\n<s xs.n="notes" />\n</ACForm>\n'
                '<f xs.n="opacity">1.0</f>\n<CFloatColor xs.n="multiplyColor" red="1.0" green="1.0" blue="1.0" alpha="1.0" />\n'
                f'<CFloatColor xs.n="screenColor" red="0.0" green="0.0" blue="0.0" alpha="1.0" />\n<CoordType xs.n="coordType" xs.ref="{cid}" />\n</ACDeformerForm>\n'
                f'<float-array xs.n="positions" count="{len(local)*2}">{pos}</float-array>\n</CWarpDeformerForm>\n'
            )
        shape = (
            f'<float-array xs.n="positions" xs.ref="{pid}" />\n<s xs.n="lastUpdatedTimeString">2026-10-28T17:00:00.000000000+09:00[Asia/Tokyo]</s>\n'
            '<b xs.n="autoRefreshIsAvailable">true</b>\n<CreationMethod xs.n="creationMethod" v="DEFORMER_CREATED" />\n'
            f'<i xs.n="col">{cols}</i>\n<i xs.n="row">{rows}</i>\n'
        )
        def bez(level, n):
            return ('<CWarpDeformerBezierExtension>\n<ACExtension xs.n="super">\n'
                    f'<CExtensionGuid xs.n="guid" uuid="{self.uid()}" note="(no debug info)" />\n<CWarpDeformerSource xs.n="_owner" xs.ref="{did}" />\n</ACExtension>\n'
                    f'<i xs.n="editLevel">{level}</i>\n<i xs.n="bezierCol">{n}</i>\n<i xs.n="bezierRow">{n}</i>\n</CWarpDeformerBezierExtension>\n')
        block = (
            f'<CWarpDeformerSource xs.id="{did}" xs.idx="{dix}">\n<ACDeformerSource xs.n="super">\n<ACParameterControllableSource xs.n="super">\n'
            f'<s xs.n="localName">{name}</s>\n<b xs.n="isVisible">true</b>\n<b xs.n="isLocked">false</b>\n<CPartGuid xs.n="parentGuid" xs.ref="{part}" />\n'
            f'<KeyformGridSource xs.n="keyformGridSource" xs.ref="{gid}" />\n<KeyFormMorphTargetSet xs.n="keyformMorphTargetSet">\n<carray_list xs.n="_morphTargets" count="0" />\n'
            '<MorphTargetBlendWeightConstraintSet xs.n="blendWeightConstraintSet">\n<carray_list xs.n="_constraints" count="0" />\n</MorphTargetBlendWeightConstraintSet>\n</KeyFormMorphTargetSet>\n'
            '<carray_list xs.n="_extensions" count="3">\n' + bez(2, 2) + bez(3, 1) +
            '<CDeformerOriginalShapeExtension>\n<ACExtension xs.n="super">\n'
            f'<CExtensionGuid xs.n="guid" uuid="{self.uid()}" note="(no debug info)" />\n<CWarpDeformerSource xs.n="_owner" xs.ref="{did}" />\n</ACExtension>\n'
            f'<WarpDeformerOriginalShape xs.n="originalShape">\n<ACDeformerOriginalShape xs.n="super">\n{shape}</ACDeformerOriginalShape>\n{shape}</WarpDeformerOriginalShape>\n'
            '</CDeformerOriginalShapeExtension>\n</carray_list>\n<null xs.n="internalColor_direct_argb" />\n<CLabelColor xs.n="labelColor" customizedColorInt="-1">\n'
            '<CLabelColorType xs.n="labelType" v="GRAY" />\n</CLabelColor>\n</ACParameterControllableSource>\n'
            f'<CDeformerGuid xs.n="guid" xs.ref="{dg}" />\n<CDeformerId xs.n="id" idstr="Warp{wn}" />\n<CDeformerGuid xs.n="targetDeformerGuid" xs.ref="{parent_ref}" />\n</ACDeformerSource>\n'
            f'<i xs.n="col">{cols}</i>\n<i xs.n="row">{rows}</i>\n<b xs.n="isQuadTransform">true</b>\n'
            f'<carray_list xs.n="keyforms" count="{len(kf)}">\n{"".join(kf)}</carray_list>\n</CWarpDeformerSource>\n'
        )
        orig = ' '.join(f'{x:.7g}' for x in grid.reshape(-1))
        trail = (
            f'<float-array count="{len(grid)*2}" xs.id="{pid}" xs.idx="{pix}">{orig}</float-array>\n'
            + ''.join(f'<CFormGuid uuid="{self.uid()}" note="Key [  ]" xs.id="{fid}" xs.idx="{fx}" />\n' for fid, fx in fids)
            + f'<CoordType xs.id="{cid}" xs.idx="{cix}">\n<s xs.n="coordName">DeformerLocal</s>\n</CoordType>\n'
        )
        if axes:
            gtext = self._grid_text(gid, gx, binds, combos, [f for f, _ in fids], len(axes))
        else:
            gtext = (f'<KeyformGridSource xs.id="{gid}" xs.idx="{gx}">\n<array_list xs.n="keyformsOnGrid" count="1">\n<KeyformOnGrid>\n'
                     '<KeyformGridAccessKey xs.n="accessKey">\n<array_list xs.n="_keyOnParameterList" count="0" />\n</KeyformGridAccessKey>\n'
                     f'<CFormGuid xs.n="keyformGuid" xs.ref="{fids[0][0]}" />\n</KeyformOnGrid>\n</array_list>\n<array_list xs.n="keyformBindings" count="0" />\n</KeyformGridSource>\n')
        text = f'<CDeformerGuid uuid="{self.uid()}" note="Warp{wn}" xs.id="{dg}" xs.idx="{dgx}" />\n' + gtext + ''.join(btexts) + block + trail
        self.insert_before('</shared>', text)
        ps = self.s.find(f'<CPartGuid xs.n="guid" xs.ref="{part}"')
        assert ps > 0
        ps = self.s.rfind('<CPartSource xs.id', 0, ps)
        lp = self.s.find('<carray_list xs.n="_childGuids"', ps)
        self.s = self.s[: self.s.find('>', lp) + 1] + f'\n<CDeformerGuid xs.ref="{dg}" />' + self.s[self.s.find('>', lp) + 1:]
        self.bump_count(lp, 1)
        ds = self.s.find('<CDeformerSourceSet xs.n="deformerSourceSet">')
        lp = self.s.find('<carray_list xs.n="_sources"', ds)
        le = self.s.find('</carray_list>', lp)
        self.s = self.s[:le] + f'<CWarpDeformerSource xs.ref="{did}" />\n' + self.s[le:]
        self.bump_count(lp, 1)
        # 子物件：画布 → 新曲面的 0~1
        for ch in children:
            self._reparent_to_warp(ch, parent, bbox, dg, kind='mesh')
        for ch in child_deformers:
            self._reparent_to_warp(ch, parent, bbox, dg, kind='deformer')
        self.log.append(f'曲面变形器 {name}（父 {parent}，bbox {bbox.round(1).tolist()}，{cols}×{rows}，{len(kf)} 个关键形态）← {list(children) + list(child_deformers)}')
        return dg

    def warp_bbox(self, name):
        off, sc = self.warp_frame(name)
        return (off[0], off[1], off[0] + sc[0], off[1] + sc[1])

    def reparent_to_warp(self, name, old_parent, warp, kind='mesh'):
        """把网格/变形器从 old_parent 挂到已有的曲面变形器 warp 下"""
        self._reparent_to_warp(name, old_parent, self.warp_bbox(warp), self.deformer_guid(warp), kind)
        self.log.append(f'{name} → {warp}')

    def reparent_to_rot(self, name, old_parent, rot):
        self.reparent_mesh(name, old_parent, self.rot_pivot(rot), self.deformer_guid(rot))
        self.log.append(f'{name} → {rot}')

    def set_visible(self, name, on=True):
        st, en = self.mesh_block(name)
        b = self.s[st:en]
        b = re.sub(r'<b xs.n="isVisible">\w+</b>', f'<b xs.n="isVisible">{"true" if on else "false"}</b>', b, count=1)
        self.s = self.s[:st] + b + self.s[en:]

    def set_param_range(self, pid, mn, mx, default=None):
        g = self.param_guid(pid)
        i = self.s.find(f'<CParameterGuid xs.n="guid" xs.ref="{g}" />')
        st = self.s.rfind('<CParameterSource>', 0, i)
        en = self.s.find('</CParameterSource>', i)
        b = self.s[st:en]
        b = re.sub(r'<f xs.n="minValue">[^<]*<', f'<f xs.n="minValue">{float(mn)}<', b)
        b = re.sub(r'<f xs.n="maxValue">[^<]*<', f'<f xs.n="maxValue">{float(mx)}<', b)
        if default is not None:
            b = re.sub(r'<f xs.n="defaultValue">[^<]*<', f'<f xs.n="defaultValue">{float(default)}<', b)
        self.s = self.s[:st] + b + self.s[en:]
        self.log.append(f'参数 {pid} 范围 → {mn}~{mx}')

    def _reparent_to_warp(self, name, old_parent, bbox, new_guid, kind):
        """把网格或变形器挂到新曲面下：positions（或旋转轴心）从旧父坐标换算到新曲面的 0~1。"""
        off, sc = self.frame_of(old_parent)
        bmin = np.array(bbox[:2], float)
        bsz = np.array(bbox[2:], float) - bmin
        if kind == 'mesh':
            st, en = self.mesh_block(name)
            b = self.s[st:en]
            m = re.search(r'<CDeformerGuid xs.n="targetDeformerGuid" xs.ref="(#\d+)"', b)
            b = b[: m.start(1)] + new_guid + b[m.end(1):]
            ks, ke = self._keyforms_span(b)
            out, p = [], 0
            for pm in re.finditer(r'(<float-array xs.n="positions" count="\d+"[^>]*>)([^<]*)<', b):
                if not (ks <= pm.start() < ke):
                    continue
                v = np.array(pm.group(2).split(), float).reshape(-1, 2)
                local = (off + v * sc - bmin) / bsz
                out.append(b[p: pm.start(2)] + ' '.join(f'{x:.7g}' for x in local.reshape(-1)))
                p = pm.end(2)
            out.append(b[p:])
            self.s = self.s[:st] + ''.join(out) + self.s[en:]
            return
        (st, en), dk = self.deformer_block(name)
        b = self.s[st:en]
        m = re.search(r'<CDeformerGuid xs.n="targetDeformerGuid" xs.ref="(#\d+)"', b)
        b = b[: m.start(1)] + new_guid + b[m.end(1):]
        if dk == 'rot':
            out, p = [], 0
            for rm in re.finditer(r'originX="([^"]*)" originY="([^"]*)"', b):
                o = off + np.array([float(rm.group(1)), float(rm.group(2))]) * sc
                l = (o - bmin) / bsz
                out.append(b[p: rm.start()] + f'originX="{l[0]:.7g}" originY="{l[1]:.7g}"')
                p = rm.end()
            out.append(b[p:])
            b = ''.join(out)
        else:
            kl = b.find('<carray_list xs.n="keyforms"')
            out, p = [], 0
            for pm in re.finditer(r'(<float-array xs.n="positions" count="\d+">)([^<]*)<', b):
                if pm.start() < kl:
                    continue
                v = np.array(pm.group(2).split(), float).reshape(-1, 2)
                local = (off + v * sc - bmin) / bsz
                out.append(b[p: pm.start(2)] + ' '.join(f'{x:.7g}' for x in local.reshape(-1)))
                p = pm.end(2)
            out.append(b[p:])
            b = ''.join(out)
        self.s = self.s[:st] + b + self.s[en:]

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

    # ---------- 给网格的关键形态插一个新的参数键（在相邻两键之间线性插值得到形态，透明度可指定）----------
    def mesh_insert_key(self, name, pid, newkey, opacity=None):
        import model as M
        st, en = self.mesh_block(name)
        b = self.s[st:en]
        P = M.params(self.s)
        km = re.search(r'<KeyformGridSource xs.n="keyformGridSource"( xs.ref="(#\d+)")?', b)
        if km.group(2):
            gst = self.s.find(f'<KeyformGridSource xs.id="{km.group(2)}"')
            gen = self.s.find('</KeyformGridSource>', gst) + len('</KeyformGridSource>')
            inline = False
        else:
            gst = st + km.start()
            gen = self.s.find('</KeyformGridSource>', gst) + len('</KeyformGridSource>')
            inline = True
        gb = self.s[gst:gen]
        pg = self.param_guid(pid)
        # 这个参数的 binding
        bref = None
        for br in re.findall(r'<KeyformBindingSource xs.ref="(#\d+)" />', gb[gb.find('keyformBindings'):]):
            k = self.s.find(f'<KeyformBindingSource xs.id="{br}"')
            kb = self.s[k:self.s.find('</KeyformBindingSource>', k)]
            if re.search(r'parameterGuid" xs.ref="' + re.escape(pg) + '"', kb):
                bref = br
                keys = [float(v) for v in re.findall(r'<f>([^<]*)</f>', kb)]
                kst, ken = k, self.s.find('</KeyformBindingSource>', k)
        assert bref, (name, pid)
        assert newkey not in keys
        nk = sorted(keys + [newkey])
        ni = nk.index(newkey)
        lo, hi = nk[ni - 1], nk[ni + 1]
        w = (newkey - lo) / (hi - lo)
        # 现有 KeyformOnGrid 条目
        entries = []
        for kog in re.finditer(r'<KeyformOnGrid>(.*?)</KeyformOnGrid>\n?', gb, re.S):
            kp = re.findall(r'<KeyformBindingSource xs.n="binding" xs.ref="(#\d+)" />\s*<i xs.n="keyIndex">(\d+)</i>', kog.group(1))
            fr = re.search(r'<CFormGuid xs.n="keyformGuid" xs.ref="(#\d+)"', kog.group(1)).group(1)
            entries.append((dict(kp), fr, kog.group(0)))
        # 这个 binding 的 keyIndex 重排：>= ni 的 +1
        def remap(kp):
            kp = dict(kp)
            if int(kp[bref]) >= ni:
                kp[bref] = str(int(kp[bref]) + 1)
            return kp
        # forms 文本
        kfl = b.find('<carray_list xs.n="keyforms"')
        kfe = b.find('</carray_list>', kfl)
        forms = {}
        for fm in re.finditer(r'<CArtMeshForm>(.*?)</CArtMeshForm>\n?', b[kfl:kfe], re.S):
            fr = re.search(r'<CFormGuid xs.n="guid" xs.ref="(#\d+)"', fm.group(1)).group(1)
            forms[fr] = fm.group(0)
        new_entries, new_forms, new_guids = [], [], []
        # 按其它 binding 的组合分组，找 lo/hi 两个 form
        others = lambda kp: tuple(sorted((k, v) for k, v in kp.items() if k != bref))
        groups = {}
        for kp, fr, txt in entries:
            groups.setdefault(others(kp), {})[int(kp[bref])] = fr
        for kp, fr, txt in entries:
            new_entries.append((remap(kp), fr))
        for og, m in groups.items():
            flo, fhi = forms[m[ni - 1]], forms[m[ni]]  # 原索引：lo 是 ni-1，hi 是 ni（插入前）
            plo = np.array(re.search(r'<float-array xs.n="positions" count="\d+">([^<]*)<', flo).group(1).split(), float)
            phi = np.array(re.search(r'<float-array xs.n="positions" count="\d+">([^<]*)<', fhi).group(1).split(), float)
            pos = plo * (1 - w) + phi * w
            olo = float(re.search(r'<f xs.n="opacity">([^<]*)<', flo).group(1))
            ohi = float(re.search(r'<f xs.n="opacity">([^<]*)<', fhi).group(1))
            op = opacity if opacity is not None else olo * (1 - w) + ohi * w
            fid, fx = self.new()
            new_guids.append((fid, fx))
            nf = re.sub(r'(<float-array xs.n="positions" count="\d+">)[^<]*<', lambda mm: mm.group(1) + ' '.join(f'{x:.7g}' for x in pos) + '<', fhi)
            nf = re.sub(r'<f xs.n="opacity">[^<]*<', f'<f xs.n="opacity">{op}<', nf)
            nf = nf.replace(f'<CFormGuid xs.n="guid" xs.ref="{m[ni]}" />', f'<CFormGuid xs.n="guid" xs.ref="{fid}" />')
            new_forms.append(nf)
            kp = dict(og)
            kp[bref] = str(ni)
            new_entries.append((kp, fid))
        # 写回 grid（条目必须按 keyIndex 的字典序排列，Cubism 按位置读）
        binds_order = re.findall(r'<KeyformBindingSource xs.ref="(#\d+)" />', gb[gb.find('keyformBindings'):])
        new_entries.sort(key=lambda e: tuple(int(e[0][bb]) for bb in reversed(binds_order)))  # 第一个 binding 变得最快
        ent = []
        for kp, fr in new_entries:
            kps = ''.join(f'<KeyOnParameter>\n<KeyformBindingSource xs.n="binding" xs.ref="{bb}" />\n<i xs.n="keyIndex">{kp[bb]}</i>\n</KeyOnParameter>\n' for bb in binds_order)
            ent.append(f'<KeyformOnGrid>\n<KeyformGridAccessKey xs.n="accessKey">\n<array_list xs.n="_keyOnParameterList" count="{len(binds_order)}">\n{kps}</array_list>\n</KeyformGridAccessKey>\n<CFormGuid xs.n="keyformGuid" xs.ref="{fr}" />\n</KeyformOnGrid>\n')
        head = gb[: gb.find('>') + 1] + '\n'
        bl = ''.join(f'<KeyformBindingSource xs.ref="{bb}" />\n' for bb in binds_order)
        ngb = head + f'<array_list xs.n="keyformsOnGrid" count="{len(ent)}">\n{"".join(ent)}</array_list>\n<array_list xs.n="keyformBindings" count="{len(binds_order)}">\n{bl}</array_list>\n</KeyformGridSource>\n'
        # 顺序：先改靠后的
        edits = []
        # keys 列表（binding 块）
        kb = self.s[kst:ken]
        nkb = re.sub(r'<array_list xs.n="keys" count="\d+">.*?</array_list>', '<array_list xs.n="keys" count="%d">\n%s</array_list>' % (len(nk), ''.join(f'<f>{k}</f>\n' for k in nk)), kb, flags=re.S)
        edits.append((kst, ken, nkb))
        # forms 追加
        edits.append((st + kfe, st + kfe, ''.join(new_forms)))
        edits.append((gst, gen, ngb))
        for a, e, t in sorted(edits, key=lambda x: -x[0]):
            self.s = self.s[:a] + t + self.s[e:]
        # keyforms count
        st2, en2 = self.mesh_block(name)
        kfl2 = self.s.find('<carray_list xs.n="keyforms"', st2)
        self.bump_count(kfl2, len(new_forms))
        # 新 form guid 定义
        (st3, en3) = self.mesh_block(name)
        self.s = self.s[:en3] + '\n' + ''.join(f'<CFormGuid uuid="{self.uid()}" note="Key [  ]" xs.id="{f}" xs.idx="{x}" />\n' for f, x in new_guids) + self.s[en3:]
        self.log.append(f'{name}: {pid} 插键 {newkey}（{len(new_forms)} 个形态，透明度 {opacity}）')

    # ---------- 把根级网格挂到曲面变形器下，并绑一个 0/1 显隐参数 ----------
    def mesh_attach_toggle(self, name, parent, pid, draw_order=None, visible=True):
        """name：根级网格（关键形态只有 1 个，坐标=画布）；parent：曲面变形器；pid：参数（0 隐 1 显，已存在）。
        结果：网格挂到 parent 下（坐标换算到 0~1），关键形态变成 2 个（pid=0 透明度 0，pid=1 透明度 1）。"""
        st, en = self.mesh_block(name)
        b = self.s[st:en]
        off, sc = self.frame_of(parent)
        pg_ref = self.deformer_guid(parent)
        # 1) targetDeformerGuid
        b = re.sub(r'(<CDeformerGuid xs.n="targetDeformerGuid" xs.ref=")#\d+(")', r'\g<1>' + pg_ref + r'\2', b, count=1)
        # 2) isVisible
        b = re.sub(r'<b xs.n="isVisible">\w+</b>', f'<b xs.n="isVisible">{"true" if visible else "false"}</b>', b, count=1)
        # 3) 关键形态：原来 1 个（画布坐标）→ 复制成 2 个，坐标换算，透明度 0 / 1
        ks, ke = self._keyforms_span(b)
        kfl = b.find('<carray_list xs.n="keyforms"')
        fm = re.search(r'<CArtMeshForm>(.*?)</CArtMeshForm>\n?', b[kfl:], re.S)
        ftxt = fm.group(0)
        fr0 = re.search(r'<CFormGuid xs.n="guid" xs.ref="(#\d+)"', ftxt).group(1)
        pm = re.search(r'<float-array xs.n="positions" count="\d+">([^<]*)<', ftxt)
        pos = np.array(pm.group(1).split(), float).reshape(-1, 2)
        local = (pos - off) / sc
        ltxt = ' '.join(f'{x:.7g}' for x in local.reshape(-1))
        def mk(fid, op):
            t = ftxt[: pm.start(1)] + ltxt + ftxt[pm.end(1):]
            t = re.sub(r'<f xs.n="opacity">[^<]*<', f'<f xs.n="opacity">{op}<', t)
            t = t.replace(f'<CFormGuid xs.n="guid" xs.ref="{fr0}" />', f'<CFormGuid xs.n="guid" xs.ref="{fid}" />')
            if draw_order is not None:
                t = re.sub(r'<i xs.n="drawOrder">\d+</i>', f'<i xs.n="drawOrder">{draw_order}</i>', t)
            return t
        f1, f1x = self.new()
        forms_txt = mk(fr0, 0.0) + mk(f1, 1.0)
        b = b[:kfl + fm.start()] + forms_txt + b[kfl + fm.end():]
        b = re.sub(r'(<carray_list xs.n="keyforms" count=")1(")', r'\g<1>2\2', b, count=1)
        # 4) 关键形态网格：binding on pid, keys [0,1]
        pg = self.param_guid(pid)
        gid, gx = self.new()
        bid, bx = self.new()
        btext = (
            f'<KeyformBindingSource xs.id="{bid}" xs.idx="{bx}">\n<KeyformGridSource xs.n="_gridSource" xs.ref="{gid}" />\n'
            f'<CParameterGuid xs.n="parameterGuid" xs.ref="{pg}" />\n<array_list xs.n="keys" count="2">\n<f>0.0</f>\n<f>1.0</f>\n</array_list>\n'
            '<InterpolationType xs.n="interpolationType" v="LINEAR" />\n<ExtendedInterpolationType xs.n="extendedInterpolationType" v="LINEAR" />\n'
            '<i xs.n="insertPointCount">1</i>\n<f xs.n="extendedInterpolationScale">1.0</f>\n<s xs.n="description" />\n</KeyformBindingSource>\n'
        )
        gtext = self._grid_text(gid, gx, [bid], [(0,), (1,)], [fr0, f1], 1)
        b = re.sub(r'<KeyformGridSource xs.n="keyformGridSource">.*?</KeyformGridSource>', f'<KeyformGridSource xs.n="keyformGridSource" xs.ref="{gid}" />', b, count=1, flags=re.S)
        self.s = self.s[:st] + b + self.s[en:]
        st2, en2 = self.mesh_block(name)
        self.s = self.s[:en2] + '\n' + gtext + btext + f'<CFormGuid uuid="{self.uid()}" note="Key [  ]" xs.id="{f1}" xs.idx="{f1x}" />\n' + self.s[en2:]
        self.log.append(f'{name} → {parent}，参数 {pid} 0/1，描画 {draw_order}')

    # ---------- 把一个「整画布 4 点」的网格重铺成贴着图像 bbox 的小矩形（新导入的小图层用）----------
    def mesh_fit_bbox(self, name, bbox, margin=6, canvas=(1086, 1448)):
        """bbox：(x0,y0,x1,y1) 画布像素。网格重铺为 4 点 2 三角；关键形态 positions 按当前父坐标系换算；uv 对应整张图层画布。"""
        import model as M
        st, en = self.mesh_block(name)
        b = self.s[st:en]
        x0, y0, x1, y1 = bbox
        x0 -= margin; y0 -= margin; x1 += margin; y1 += margin
        pts = np.array([[x0, y0], [x1, y0], [x1, y1], [x0, y1]], float)
        W, H = canvas
        uvs = np.c_[pts[:, 0] / W, pts[:, 1] / H]
        # 父坐标
        par = self.parent_name_of_mesh(name)
        off, sc = self.frame_of(par)
        local = (pts - off) / sc
        P = ' '.join(f'{v:.7g}' for v in pts.reshape(-1))
        L = ' '.join(f'{v:.7g}' for v in local.reshape(-1))
        U = ' '.join(f'{v:.7g}' for v in uvs.reshape(-1))
        b = re.sub(r'<float-array xs.n="point" count="\d+">[^<]*<', f'<float-array xs.n="point" count="8">{P}<', b, count=1)
        b = re.sub(r'<short-array xs.n="edge" count="\d+">[^<]*<', '<short-array xs.n="edge" count="10">0 1 1 2 2 3 0 3 0 2<', b, count=1)
        b = re.sub(r'<byte-array xs.n="edgePriority" count="\d+">[^<]*<', '<byte-array xs.n="edgePriority" count="5">30 30 30 30 30<', b, count=1)
        b = re.sub(r'<byte-array xs.n="pointPriority" count="\d+">[^<]*<', '<byte-array xs.n="pointPriority" count="4">10 10 10 10<', b, count=1)
        b = re.sub(r'<int-array xs.n="pointUid" count="\d+">[^<]*<', '<int-array xs.n="pointUid" count="4">0 1 2 3<', b, count=1)
        b = re.sub(r'nextPointUid="\d+"', 'nextPointUid="4"', b, count=1)
        b = re.sub(r'<int-array xs.n="indices" count="\d+">[^<]*<', '<int-array xs.n="indices" count="6">0 1 2 0 2 3<', b, count=1)
        ks, ke = self._keyforms_span(b)
        b = b[:ks] + re.sub(r'(<float-array xs.n="positions" count=")\d+(">)[^<]*<', r'\g<1>8\g<2>' + L + '<', b[ks:ke]) + b[ke:]
        # 末尾缓存：画布坐标 + uv
        tail = b[ke:]
        tail = re.sub(r'(<float-array xs.n="positions" count=")\d+(">)[^<]*<', r'\g<1>8\g<2>' + P + '<', tail, count=1)
        tail = re.sub(r'(<float-array xs.n="uvs" count=")\d+(">)[^<]*<', r'\g<1>8\g<2>' + U + '<', tail, count=1)
        b = b[:ke] + tail
        self.s = self.s[:st] + b + self.s[en:]
        self.log.append(f'{name} 网格重铺到 bbox {bbox}')

    def parent_name_of_mesh(self, name):
        import model as M
        st, en = self.mesh_block(name)
        t = re.search(r'<CDeformerGuid xs.n="targetDeformerGuid" xs.ref="(#\d+)"', self.s[st:en]).group(1)
        for n, dd in M.deformers(self.s).items():
            if dd['guid'] == t:
                return n
        return None

    # ---------- 把所有关键形态网格的条目按规范顺序排好（第一个 binding 变得最快）----------
    def canonicalize_grids(self):
        n = 0
        out, p = [], 0
        for m in re.finditer(r'<KeyformGridSource( xs.n="keyformGridSource")?( xs.id="#\d+" xs.idx="\d+")?>\r?\n<array_list xs.n="keyformsOnGrid" count="(\d+)">\r?\n(.*?)</array_list>\r?\n<array_list xs.n="keyformBindings" count="\d+">\r?\n(.*?)</array_list>', self.s, re.S):
            binds = re.findall(r'<KeyformBindingSource xs.ref="(#\d+)" />', m.group(5))
            if len(binds) < 1:
                continue
            ents = [(dict(re.findall(r'<KeyformBindingSource xs.n="binding" xs.ref="(#\d+)" />\s*<i xs.n="keyIndex">(\d+)</i>', k.group(1))), k.group(0)) for k in re.finditer(r'<KeyformOnGrid>(.*?)</KeyformOnGrid>\r?\n?', m.group(4), re.S)]
            if len(ents) != int(m.group(3)):
                continue
            key = lambda e: tuple(int(e[0].get(bb, 0)) for bb in reversed(binds))
            srt = sorted(ents, key=key)
            if [e[1] for e in srt] != [e[1] for e in ents]:
                n += 1
                out.append(self.s[p:m.start(4)] + ''.join(e[1] for e in srt))
                p = m.end(4)
        out.append(self.s[p:])
        self.s = ''.join(out)
        self.log.append(f'关键形态网格重新排序 ×{n}')
        return n

    # ---------- 给一个网格加一个「隐藏」参数轴：pid=1 时所有关键形态透明度 0 ----------
    def mesh_add_hide_axis(self, name, pid, hide_at=1):
        """现有网格可能已有 1 个或多个 binding；新加 pid [0,1] 轴，复制全部关键形态，pid=hide_at 的副本透明度 0。"""
        import model as M
        st, en = self.mesh_block(name)
        b = self.s[st:en]
        km = re.search(r'<KeyformGridSource xs.n="keyformGridSource"( xs.ref="(#\d+)")?', b)
        inline = not km.group(2)
        if inline:
            gst = st + km.start()
        else:
            gst = self.s.find(f'<KeyformGridSource xs.id="{km.group(2)}"')
        gen = self.s.find('</KeyformGridSource>', gst) + len('</KeyformGridSource>')
        gb = self.s[gst:gen]
        binds = re.findall(r'<KeyformBindingSource xs.ref="(#\d+)" />', gb[gb.find('keyformBindings'):])
        ents = [(dict(re.findall(r'<KeyformBindingSource xs.n="binding" xs.ref="(#\d+)" />\s*<i xs.n="keyIndex">(\d+)</i>', k.group(1))), re.search(r'<CFormGuid xs.n="keyformGuid" xs.ref="(#\d+)"', k.group(1)).group(1)) for k in re.finditer(r'<KeyformOnGrid>(.*?)</KeyformOnGrid>', gb, re.S)]
        pg = self.param_guid(pid)
        gref = km.group(2)
        if inline:
            gref, gx2 = self.new()
        bid, bx = self.new()
        btext = (f'<KeyformBindingSource xs.id="{bid}" xs.idx="{bx}">\n<KeyformGridSource xs.n="_gridSource" xs.ref="{gref}" />\n'
                 f'<CParameterGuid xs.n="parameterGuid" xs.ref="{pg}" />\n<array_list xs.n="keys" count="2">\n<f>0.0</f>\n<f>1.0</f>\n</array_list>\n'
                 '<InterpolationType xs.n="interpolationType" v="LINEAR" />\n<ExtendedInterpolationType xs.n="extendedInterpolationType" v="LINEAR" />\n'
                 '<i xs.n="insertPointCount">1</i>\n<f xs.n="extendedInterpolationScale">1.0</f>\n<s xs.n="description" />\n</KeyformBindingSource>\n')
        kfl = b.find('<carray_list xs.n="keyforms"')
        kfe = b.rfind('</CArtMeshForm>') + len('</CArtMeshForm>')
        forms = {}
        for fm in re.finditer(r'<CArtMeshForm>(.*?)</CArtMeshForm>\r?\n?', b[kfl:kfe + 2], re.S):
            forms[re.search(r'<CFormGuid xs.n="guid" xs.ref="(#\d+)"', fm.group(1)).group(1)] = fm.group(0)
        new_forms, new_guids, new_entries = [], [], []
        for kp, fr in ents:
            fid, fx = self.new()
            new_guids.append((fid, fx))
            t = re.sub(r'<f xs.n="opacity">[^<]*<', '<f xs.n="opacity">0.0<', forms[fr])
            t = t.replace(f'<CFormGuid xs.n="guid" xs.ref="{fr}" />', f'<CFormGuid xs.n="guid" xs.ref="{fid}" />')
            new_forms.append(t)
            if hide_at == 1:
                new_entries.append((dict(kp, **{bid: '0'}), fr))
                new_entries.append((dict(kp, **{bid: '1'}), fid))
            else:
                new_entries.append((dict(kp, **{bid: '0'}), fid))
                new_entries.append((dict(kp, **{bid: '1'}), fr))
        binds2 = binds + [bid]
        new_entries.sort(key=lambda e: tuple(int(e[0][bb]) for bb in reversed(binds2)))
        ent = ''.join(f'<KeyformOnGrid>\n<KeyformGridAccessKey xs.n="accessKey">\n<array_list xs.n="_keyOnParameterList" count="{len(binds2)}">\n'
                      + ''.join(f'<KeyOnParameter>\n<KeyformBindingSource xs.n="binding" xs.ref="{bb}" />\n<i xs.n="keyIndex">{kp[bb]}</i>\n</KeyOnParameter>\n' for bb in binds2)
                      + f'</array_list>\n</KeyformGridAccessKey>\n<CFormGuid xs.n="keyformGuid" xs.ref="{fr}" />\n</KeyformOnGrid>\n' for kp, fr in new_entries)
        bl = ''.join(f'<KeyformBindingSource xs.ref="{bb}" />\n' for bb in binds2)
        head = f'<KeyformGridSource xs.id="{gref}" xs.idx="{gx2}">\n' if inline else gb[: gb.find('>') + 1] + '\n'
        ngb = head + f'<array_list xs.n="keyformsOnGrid" count="{len(new_entries)}">\n{ent}</array_list>\n<array_list xs.n="keyformBindings" count="{len(binds2)}">\n{bl}</array_list>\n</KeyformGridSource>\n'
        # 写回：forms 追加（在 mesh 内，靠后）→ grid（inline 在 mesh 内靠前 / 独立对象在 mesh 外）
        b2 = b[:kfe] + ''.join(new_forms) + b[kfe:]
        b2 = re.sub(r'(<carray_list xs.n="keyforms" count=")(\d+)(")', lambda m: m.group(1) + str(int(m.group(2)) + len(new_forms)) + m.group(3), b2, count=1)
        if inline:
            b2 = b2[:km.start()] + f'<KeyformGridSource xs.n="keyformGridSource" xs.ref="{gref}" />' + b2[gen - st:]
            self.s = self.s[:st] + b2 + self.s[en:]
            st2, en2 = self.mesh_block(name)
            self.s = self.s[:en2] + '\n' + ngb + btext + ''.join(f'<CFormGuid uuid="{self.uid()}" note="Key [  ]" xs.id="{f}" xs.idx="{x}" />\n' for f, x in new_guids) + self.s[en2:]
        else:
            self.s = self.s[:st] + b2 + self.s[en:]
            gst = self.s.find(f'<KeyformGridSource xs.id="{gref}"')
            gen = self.s.find('</KeyformGridSource>', gst) + len('</KeyformGridSource>')
            self.s = self.s[:gst] + ngb + btext + ''.join(f'<CFormGuid uuid="{self.uid()}" note="Key [  ]" xs.id="{f}" xs.idx="{x}" />\n' for f, x in new_guids) + self.s[gen:]
        self.log.append(f'{name}: 加隐藏轴 {pid}（{len(new_forms)} 个形态）')
