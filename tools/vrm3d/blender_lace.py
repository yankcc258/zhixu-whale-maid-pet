"""Blender (bpy) pass: add a scalloped lace strip along the apron hem (and optionally the skirt hem),
skinned by copying the nearest hem vertex's bone weights. Exports a new VRM.
usage: python3 blender_lace.py in.vrm out.vrm [--skirt]
"""
import sys, math, argparse
import bpy, bmesh
from mathutils import Vector

ap = argparse.ArgumentParser(); ap.add_argument('src'); ap.add_argument('dst')
ap.add_argument('--skirt', action='store_true'); ap.add_argument('--depth', type=float, default=0.032)
ap.add_argument('--tex', default='/home/claude/tex/lace_strip.png')
a = ap.parse_args()
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.preferences.addon_enable(module="io_scene_vrm")
bpy.ops.import_scene.vrm(filepath=a.src, extract_textures_into_folder=False, make_new_texture_folder=False)
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
body = bpy.data.objects['Body']

def hem_loop(mat_sub, tex_png=None):
    """visible hem of the faces using material containing mat_sub. VRoid skirts are longer than the visible cloth —
    the length comes from texture alpha — so visibility is sampled from the texture at each face's UV centre.
    Returns ordered world points (sorted by angle around the body axis) + source vertex indices."""
    from PIL import Image
    bm = bmesh.new(); bm.from_mesh(body.data); bm.verts.ensure_lookup_table(); bm.edges.ensure_lookup_table(); bm.faces.ensure_lookup_table()
    mi = next(i for i, m in enumerate(body.data.materials) if mat_sub in m.name)
    uvl = bm.loops.layers.uv.active
    alpha = None
    if tex_png:
        im = Image.open(tex_png).convert('RGBA'); W, H = im.size; px = im.load()
        def vis(f):
            u = sum(l[uvl].uv.x for l in f.loops) / len(f.loops); v = sum(l[uvl].uv.y for l in f.loops) / len(f.loops)
            return px[int(u * (W - 1)) % W, int((1 - v) * (H - 1)) % H][3] > 128
    else:
        vis = lambda f: True
    faces = [f for f in bm.faces if f.material_index == mi]
    visible = {f.index for f in faces if vis(f)}
    print(mat_sub, 'faces', len(faces), 'visible', len(visible))
    hem = {}
    for f in faces:
        if f.index not in visible: continue
        for e in f.edges:
            others = [ff for ff in e.link_faces if ff.material_index == mi and ff.index != f.index]
            # alpha boundary: a visible face next to an invisible one (that is where the cloth ends)
            if others and all(ff.index not in visible for ff in others):
                hem[e.index] = e
    print('alpha-boundary edges', len(hem))
    zs = sorted((e.verts[0].co.z + e.verts[1].co.z) / 2 for e in hem.values())
    zcut = zs[len(zs) // 2] if zs else 0
    low = [e for e in hem.values() if (e.verts[0].co.z + e.verts[1].co.z) / 2 <= zcut + 0.02]
    vidx = sorted({v.index for e in low for v in e.verts}, key=lambda i: math.atan2(bm.verts[i].co.y, bm.verts[i].co.x))
    pts = [(body.matrix_world @ bm.verts[i].co).copy() for i in vidx]
    print('hem verts', len(vidx), 'z range', round(min(p.z for p in pts), 3), round(max(p.z for p in pts), 3))
    bm.free()
    return pts, vidx

def catmull(pts, n):
    out = []
    P = [pts[0]] + pts + [pts[-1]]
    segs = len(pts) - 1
    for k in range(n + 1):
        t = k / n * segs; i = min(int(t), segs - 1); f = t - i
        p0, p1, p2, p3 = P[i], P[i + 1], P[i + 2], P[i + 3]
        out.append(0.5 * ((2 * p1) + (-p0 + p2) * f + (2 * p0 - 5 * p1 + 4 * p2 - p3) * f * f + (-p0 + 3 * p1 - 3 * p2 + p3) * f ** 3))
    return out

def build_strip(name, pts, src_idx, depth, scallops):
    N = 96
    curve = catmull(pts + [pts[0]], N)   # closed loop around the hem
    # nearest source vertex for each sample (for weights)
    def nearest(p):
        return min(src_idx, key=lambda i: (body.data.vertices[i].co - p).length)
    verts = []; uvs = []; faces = []
    for k, p in enumerate(curve):
        # outward direction: away from the body axis in the XY (Blender ground) plane
        out = Vector((p.x, p.y, 0)); out.z = 0
        if out.length < 1e-4: out = Vector((0, -1, 0))
        out.normalize()
        wobble = 0.004 * math.sin(k / N * scallops * 2 * math.pi)
        top = p + out * 0.002
        bot = p + out * (0.014 + wobble) + Vector((0, 0, -depth))
        verts += [top, bot]; uvs += [(k / N * scallops / 2, 1.0), (k / N * scallops / 2, 0.0)]
    for k in range(N):
        i = 2 * k
        faces.append((i, i + 2, i + 3, i + 1))
    me = bpy.data.meshes.new(name); me.from_pydata([arm.matrix_world.inverted() @ v for v in verts], [], faces); me.update()
    uvl = me.uv_layers.new(name='UVMap')
    for poly in me.polygons:
        for li in poly.loop_indices:
            vi = me.loops[li].vertex_index; uvl.data[li].uv = uvs[vi]
    ob = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(ob)
    ob.parent = arm; mod = ob.modifiers.new('Armature', 'ARMATURE'); mod.object = arm
    # weights: copy groups of the nearest hem vertex
    for k, p in enumerate(curve):
        si = nearest(arm.matrix_world.inverted() @ p) if False else nearest(body.matrix_world.inverted() @ p)
        sv = body.data.vertices[si]
        for g in sv.groups:
            gname = body.vertex_groups[g.group].name
            vg = ob.vertex_groups.get(gname) or ob.vertex_groups.new(name=gname)
            vg.add([2 * k, 2 * k + 1], g.weight, 'REPLACE')
    # material: MToon, cutout, double sided
    mat = bpy.data.materials.new(name + '_mat'); mat.use_nodes = True
    ext = mat.vrm_addon_extension.mtoon1; ext.enabled = True
    img = bpy.data.images.load(a.tex)
    ext.pbr_metallic_roughness.base_color_texture.index.source = img
    ext.alpha_mode = 'MASK'; ext.alpha_cutoff = 0.5; ext.double_sided = True
    ext.extensions.vrmc_materials_mtoon.shade_color_factor = (0.78, 0.8, 0.88)
    ext.extensions.vrmc_materials_mtoon.shading_toony_factor = 0.85
    ext.extensions.vrmc_materials_mtoon.outline_width_mode = 'none'
    me.materials.append(mat)
    print('strip', name, 'verts', len(verts))
    return ob

pts, idx = hem_loop('Tops_01_CLOTH_01', '/home/claude/tex/skirt_v4.png')   # the skirt (its frill is the visible hem)
build_strip('Kiko_Lace_Skirt', pts, idx, a.depth, scallops=40)
bpy.context.view_layer.objects.active = arm
bpy.ops.export_scene.vrm(filepath=a.dst, armature_object_name=arm.name)
print('wrote', a.dst)
