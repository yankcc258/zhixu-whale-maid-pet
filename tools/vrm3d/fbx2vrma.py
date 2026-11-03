"""Mixamo FBX → VRMA (VRM Animation) retarget, headless with bpy + VRM add-on.
usage: python3 fbx2vrma.py model.vrm motion.fbx out.vrma [--start N] [--end N] [--fps 30] [--loop]
Retarget = copy each Mixamo bone's WORLD-space rotation delta (pose vs rest) onto the matching VRM humanoid bone,
so both rigs only need to share a T-pose rest. Hips translation is scaled by hip height.
"""
import sys, math, argparse
import bpy
from mathutils import Quaternion, Vector, Matrix

ap = argparse.ArgumentParser()
ap.add_argument('vrm'); ap.add_argument('fbx'); ap.add_argument('out')
ap.add_argument('--start', type=int); ap.add_argument('--end', type=int); ap.add_argument('--fps', type=int, default=30)
ap.add_argument('--step', type=int, default=1, help='keep every Nth source frame')
ap.add_argument('--root-xz', action='store_true', help='keep hips X/Z travel (default: drop it, the pet moves the window itself)')
ap.add_argument('--hips-y', type=float, default=1.0, help='scale of hips vertical motion')
ap.add_argument('--amp', type=float, default=1.0, help='rotation amplitude (0..1): slerp each bone delta toward rest — tone down game-style motion')
ap.add_argument('--amp-bones', default='', help='comma list of human bones the --amp applies to (default: all except hips)')
ap.add_argument('--amp-hips', action='store_true', help='also scale the hips rotation (whole-body lean)')
a = ap.parse_args()

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.preferences.addon_enable(module="io_scene_vrm")
bpy.context.scene.render.fps = a.fps

before = set(bpy.data.objects)
bpy.ops.import_scene.vrm(filepath=a.vrm, extract_textures_into_folder=False, make_new_texture_folder=False)
vrm_arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE' and o not in before)
before = set(bpy.data.objects)
bpy.ops.import_scene.fbx(filepath=a.fbx, use_anim=True, ignore_leaf_bones=True, automatic_bone_orientation=False)
mix_arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE' and o not in before)
print('VRM armature', vrm_arm.name, 'bones', len(vrm_arm.data.bones), '| FBX armature', mix_arm.name, 'bones', len(mix_arm.data.bones))

# --- humanoid mapping of the VRM armature (addon stores bone names per human bone)
hum = vrm_arm.data.vrm_addon_extension.vrm1.humanoid.human_bones
VRM_BONE = {}
for hb in ['hips','spine','chest','upperChest','neck','head','leftShoulder','leftUpperArm','leftLowerArm','leftHand','rightShoulder','rightUpperArm','rightLowerArm','rightHand','leftUpperLeg','leftLowerLeg','leftFoot','leftToes','rightUpperLeg','rightLowerLeg','rightFoot','rightToes']:
    prop = getattr(hum, ''.join('_' + c.lower() if c.isupper() else c for c in hb), None)
    name = prop.node.bone_name if prop is not None else ''
    if name: VRM_BONE[hb] = name
print('mapped', len(VRM_BONE), 'VRM bones')
MIX = {'hips':'Hips','spine':'Spine','chest':'Spine1','upperChest':'Spine2','neck':'Neck','head':'Head',
       'leftShoulder':'LeftShoulder','leftUpperArm':'LeftArm','leftLowerArm':'LeftForeArm','leftHand':'LeftHand',
       'rightShoulder':'RightShoulder','rightUpperArm':'RightArm','rightLowerArm':'RightForeArm','rightHand':'RightHand',
       'leftUpperLeg':'LeftUpLeg','leftLowerLeg':'LeftLeg','leftFoot':'LeftFoot','leftToes':'LeftToeBase',
       'rightUpperLeg':'RightUpLeg','rightLowerLeg':'RightLeg','rightFoot':'RightFoot','rightToes':'RightToeBase'}
def mix_bone(hb):
    n = MIX[hb]
    for cand in (n, 'mixamorig:' + n, 'mixamorig_' + n, 'mixamorig1:' + n):
        if cand in mix_arm.pose.bones: return cand
    return None
PAIRS = [(hb, VRM_BONE[hb], mix_bone(hb)) for hb in MIX if hb in VRM_BONE and mix_bone(hb)]
print('retarget pairs', len(PAIRS))
# parent (nearest mapped ancestor) for each human bone
ORDER = ['hips','spine','chest','upperChest','neck','head','leftShoulder','leftUpperArm','leftLowerArm','leftHand','rightShoulder','rightUpperArm','rightLowerArm','rightHand','leftUpperLeg','leftLowerLeg','leftFoot','leftToes','rightUpperLeg','rightLowerLeg','rightFoot','rightToes']
PARENT = {'spine':'hips','chest':'spine','upperChest':'chest','neck':'upperChest','head':'neck','leftShoulder':'upperChest','leftUpperArm':'leftShoulder','leftLowerArm':'leftUpperArm','leftHand':'leftLowerArm','rightShoulder':'upperChest','rightUpperArm':'rightShoulder','rightLowerArm':'rightUpperArm','rightHand':'rightLowerArm','leftUpperLeg':'hips','leftLowerLeg':'leftUpperLeg','leftFoot':'leftLowerLeg','leftToes':'leftFoot','rightUpperLeg':'hips','rightLowerLeg':'rightUpperLeg','rightFoot':'rightLowerLeg','rightToes':'rightFoot'}
mapped = {hb for hb, _, _ in PAIRS}
def mapped_parent(hb):
    p = PARENT.get(hb)
    while p and p not in mapped: p = PARENT.get(p)
    return p

def rest_world_q(arm, bname):
    return (arm.matrix_world @ arm.data.bones[bname].matrix_local).to_quaternion()
def pose_world_q(arm, bname):
    return (arm.matrix_world @ arm.pose.bones[bname].matrix).to_quaternion()
def rest_world_pos(arm, bname):
    return (arm.matrix_world @ arm.data.bones[bname].matrix_local).to_translation()
def pose_world_pos(arm, bname):
    return (arm.matrix_world @ arm.pose.bones[bname].matrix).to_translation()

# frame range from the FBX action
act = mix_arm.animation_data.action
f0, f1 = (int(act.frame_range[0]), int(act.frame_range[1]))
if a.start is not None: f0 = a.start
if a.end is not None: f1 = a.end
print('frames', f0, f1)
# rest data
R_rest = {hb: rest_world_q(vrm_arm, vb) for hb, vb, mb in PAIRS}
M_rest = {hb: rest_world_q(mix_arm, mb) for hb, vb, mb in PAIRS}
mix_hip_h = rest_world_pos(mix_arm, mix_bone('hips')).z
vrm_hip_h = rest_world_pos(vrm_arm, VRM_BONE['hips']).z
scale = vrm_hip_h / mix_hip_h if mix_hip_h else 1.0
print('hip height mix %.3f vrm %.3f scale %.3f' % (mix_hip_h, vrm_hip_h, scale))
mix_hip_rest = rest_world_pos(mix_arm, mix_bone('hips'))

# make a fresh action on the VRM armature
vrm_arm.animation_data_create()
new_act = bpy.data.actions.new('retarget')
vrm_arm.animation_data.action = new_act
for pb in vrm_arm.pose.bones:
    pb.rotation_mode = 'QUATERNION'
out_frame = 1
for f in range(f0, f1 + 1, a.step):
    bpy.context.scene.frame_set(f)
    bpy.context.view_layer.update()
    delta = {}
    for hb, vb, mb in PAIRS:
        d = pose_world_q(mix_arm, mb) @ M_rest[hb].inverted()
        if a.amp != 1.0 and (hb != 'hips' or a.amp_hips) and (not a.amp_bones or hb in a.amp_bones.split(',')):
            d = Quaternion().slerp(d, a.amp)
        delta[hb] = d
    for hb, vb, mb in PAIRS:
        pb = vrm_arm.pose.bones[vb]
        dp = delta[mapped_parent(hb)] if mapped_parent(hb) else Quaternion()
        basis = R_rest[hb].inverted() @ dp.inverted() @ delta[hb] @ R_rest[hb]
        pb.rotation_quaternion = basis
        pb.keyframe_insert('rotation_quaternion', frame=out_frame)
        if hb == 'hips':
            dpos = (pose_world_pos(mix_arm, mb) - mix_hip_rest) * scale
            if not a.root_xz: dpos.x = 0; dpos.y = 0   # Blender Z-up: x/y are the ground plane
            dpos.z *= a.hips_y
            pb.location = R_rest[hb].inverted() @ dpos
            pb.keyframe_insert('location', frame=out_frame)
    out_frame += 1
bpy.context.scene.frame_start = 1
bpy.context.scene.frame_end = out_frame - 1
print('keyed', out_frame - 1, 'frames')
# export VRMA
bpy.ops.export_scene.vrma(filepath=a.out, armature_object_name=vrm_arm.name)
print('wrote', a.out)
