# Day 28 — What if you had a pistol shrimp's snap?  Build: python3 episodes/028-pistol-shrimp/scene.py
# Reference style: base (helpers, lawn/soil, house, garden) copied from episodes/003-lift-million-ref/scene.py (via 019)
import bpy, math, random, os, json
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
random.seed(28)
FPS = 24
timing = json.load(open(f"{HERE}/timing.json"))
S = [round(l["start"] * FPS) for l in timing]          # line start frames
FRAMES = round((timing[-1]["end"] + 0.7) * FPS)

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.engine = 'CYCLES'
sc.cycles.device = 'CPU'
sc.cycles.samples = 8
sc.cycles.use_denoising = True
sc.cycles.max_bounces = 4
sc.cycles.diffuse_bounces = 2
sc.cycles.glossy_bounces = 1
sc.cycles.transmission_bounces = 1
sc.render.use_persistent_data = True
sc.render.resolution_x = 1080
sc.render.resolution_y = 1920
sc.render.resolution_percentage = 40
sc.render.fps = FPS
sc.frame_start = 0
sc.frame_end = FRAMES - 1
sc.render.image_settings.file_format = 'PNG'
sc.view_settings.view_transform = 'Standard'
sc.view_settings.exposure = -0.6
sc.cycles.samples = 12

# ---------------- helpers ----------------
def mat(name, color, rough=0.7, emit=None, emit_strength=0.0, metal=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if emit:
        b.inputs["Emission Color"].default_value = (*emit, 1)
        b.inputs["Emission Strength"].default_value = emit_strength
    return m

def glow_mat(name, color, strength):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    N = m.node_tree.nodes; L = m.node_tree.links
    N.remove(N["Principled BSDF"])
    em = N.new("ShaderNodeEmission"); em.inputs["Color"].default_value = (*color, 1)
    em.inputs["Strength"].default_value = strength
    L.new(em.outputs[0], N["Material Output"].inputs["Surface"])
    return m

def stripe_mat(name, c1, c2, axis="Z", freq=10.0, thresh=0.75, rough=0.75, metal=0.0):
    """Two-colour bands along an object axis (stacked bills, coin piles)."""
    m = bpy.data.materials.new(name); m.use_nodes = True
    N = m.node_tree.nodes; L = m.node_tree.links
    bs = N["Principled BSDF"]; bs.inputs["Roughness"].default_value = rough; bs.inputs["Metallic"].default_value = metal
    tc = N.new("ShaderNodeTexCoord"); sp = N.new("ShaderNodeSeparateXYZ"); L.new(tc.outputs["Object"], sp.inputs[0])
    mu = N.new("ShaderNodeMath"); mu.operation = 'MULTIPLY'; mu.inputs[1].default_value = freq
    L.new(sp.outputs[axis], mu.inputs[0])
    sn = N.new("ShaderNodeMath"); sn.operation = 'SINE'; L.new(mu.outputs[0], sn.inputs[0])
    gt = N.new("ShaderNodeMath"); gt.operation = 'GREATER_THAN'; gt.inputs[1].default_value = thresh
    L.new(sn.outputs[0], gt.inputs[0])
    mx = N.new("ShaderNodeMix"); mx.data_type = 'RGBA'
    mx.inputs[6].default_value = (*c1, 1); mx.inputs[7].default_value = (*c2, 1)
    L.new(gt.outputs[0], mx.inputs["Factor"]); L.new(mx.outputs[2], bs.inputs["Base Color"])
    return m

def box(name, loc, size, material, bevel=0.0, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(location=loc, rotation=rot)
    o = bpy.context.object
    o.name = name
    o.scale = (size[0] / 2, size[1] / 2, size[2] / 2)
    bpy.ops.object.transform_apply(scale=True)
    o.data.materials.append(material)
    if bevel:
        mod = o.modifiers.new("bev", 'BEVEL'); mod.width = bevel; mod.segments = 2
    return o

def cyl(name, loc, r, depth, material, rot=(0, 0, 0), verts=24, r2=None):
    if r2 is None:
        bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=depth, location=loc, rotation=rot)
    else:
        bpy.ops.mesh.primitive_cone_add(vertices=verts, radius1=r, radius2=r2, depth=depth, location=loc, rotation=rot)
    o = bpy.context.object
    o.name = name
    o.data.materials.append(material)
    return o

def sphere(name, loc, r, material, scale=(1, 1, 1), sub=2, smooth=True):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=sub, radius=r, location=loc)
    o = bpy.context.object
    o.name = name
    o.scale = scale
    o.data.materials.append(material)
    if smooth:
        bpy.ops.object.shade_smooth()
    return o

def tube(name, pts, radii, material):
    cu = bpy.data.curves.new(name, 'CURVE'); cu.dimensions = '3D'
    cu.bevel_depth = 1.0; cu.bevel_resolution = 2; cu.use_fill_caps = True
    sp = cu.splines.new('POLY'); sp.points.add(len(pts) - 1)
    for p, (co, r) in enumerate(zip(pts, radii)):
        sp.points[p].co = (*co, 1); sp.points[p].radius = r
    ob = bpy.data.objects.new(name, cu); sc.collection.objects.link(ob)
    cu.materials.append(material)
    return ob

def text(name, body, loc, size, material, rot=(math.radians(90), 0, 0), extrude=0.0):
    bpy.ops.object.text_add(location=loc, rotation=rot)
    o = bpy.context.object; o.name = name
    o.data.body = body; o.data.size = size; o.data.extrude = extrude
    o.data.align_x = 'CENTER'; o.data.align_y = 'CENTER'
    o.data.materials.append(material)
    return o

def group(name, loc, rot_z=0.0):
    e = bpy.data.objects.new(name, None); sc.collection.objects.link(e)
    e.location = loc; e["rz"] = rot_z
    return e

def attach(objs, parent):
    rot = tuple(parent.rotation_euler)
    parent.rotation_euler = (0, 0, 0)
    bpy.context.view_layer.update()
    for o in objs:
        o.parent = parent
        o.matrix_parent_inverse = parent.matrix_world.inverted()
    parent.rotation_euler = (0, 0, parent.get("rz", 0.0))

def pop(o, f_in, dur=6, f_out=None, s=1.0):
    o.scale = (0.001,) * 3; o.keyframe_insert("scale", frame=max(f_in - 1, 0))
    o.scale = (1.15 * s,) * 3; o.keyframe_insert("scale", frame=f_in + dur * 0.65)
    o.scale = (s,) * 3; o.keyframe_insert("scale", frame=f_in + dur)
    if f_out is not None:
        o.keyframe_insert("scale", frame=f_out - 4)
        o.scale = (0.001,) * 3; o.keyframe_insert("scale", frame=f_out)

def hide_until(o, f):
    s = tuple(o.scale)
    o.scale = (0.001,) * 3; o.keyframe_insert("scale", frame=0); o.keyframe_insert("scale", frame=f - 1)
    o.scale = s; o.keyframe_insert("scale", frame=f)

def gone_at(o, f, dur=4):
    o.keyframe_insert("scale", frame=f - dur)
    o.scale = (0.001,) * 3; o.keyframe_insert("scale", frame=f)

def key_loc(o, keys):
    for f, p in keys:
        o.location = p; o.keyframe_insert("location", frame=f)

# ---------------- world: bright cartoon day ----------------
w = bpy.data.worlds.new("W"); sc.world = w
w.use_nodes = True
nt = w.node_tree
bg = nt.nodes["Background"]
tc = nt.nodes.new("ShaderNodeTexCoord"); sep = nt.nodes.new("ShaderNodeSeparateXYZ")
ramp = nt.nodes.new("ShaderNodeValToRGB"); el = ramp.color_ramp.elements
el[0].position = 0.0; el[0].color = (0.78, 0.9, 1.0, 1)
el[1].position = 0.45; el[1].color = (0.22, 0.52, 0.95, 1)
nt.links.new(tc.outputs["Generated"], sep.inputs[0])
nt.links.new(sep.outputs["Z"], ramp.inputs[0])
nt.links.new(ramp.outputs["Color"], bg.inputs["Color"])
bg.inputs["Strength"].default_value = 0.85

bpy.ops.object.light_add(type='SUN', rotation=(math.radians(50), 0, math.radians(-30)))
sun = bpy.context.object; sun.data.energy = 4.2; sun.data.color = (1.0, 0.96, 0.88); sun.data.angle = math.radians(5)

# fluffy clouds
cloud_m = mat("Cloud", (1, 1, 1), 0.9, emit=(1, 1, 1), emit_strength=0.4)
for (x, y, z, s) in [(-60, 160, 70, 1.4), (40, 180, 90, 1.8), (-10, 220, 130, 2.0), (90, 150, 55, 1.2), (-120, 200, 110, 1.6)]:
    for k in range(4):
        sphere("Cloud", (x + (k - 1.5) * 7 * s, y, z + random.uniform(-2, 2) * s), random.uniform(5, 8) * s, cloud_m,
               scale=(1.3, 0.8, 0.8), sub=2)

# ---------------- ground diorama with cut-away front ----------------
FRONT_Y = -1.6
grass_m = bpy.data.materials.new("Grass"); grass_m.use_nodes = True
gn = grass_m.node_tree; N = gn.nodes; L = gn.links
bs = N["Principled BSDF"]; bs.inputs["Roughness"].default_value = 0.92
geo = N.new("ShaderNodeNewGeometry")
sxyz = N.new("ShaderNodeSeparateXYZ"); L.new(geo.outputs["Position"], sxyz.inputs[0])
# mowed lawn: wide two-tone bands (ref style), with a little noise inside each band
dg = N.new("ShaderNodeMath"); dg.operation = 'ADD'
L.new(sxyz.outputs["X"], dg.inputs[0]); L.new(sxyz.outputs["Y"], dg.inputs[1])
mul = N.new("ShaderNodeMath"); mul.operation = 'MULTIPLY'; mul.inputs[1].default_value = 1.35
L.new(dg.outputs[0], mul.inputs[0])
sn = N.new("ShaderNodeMath"); sn.operation = 'SINE'; L.new(mul.outputs[0], sn.inputs[0])
gt = N.new("ShaderNodeMath"); gt.operation = 'GREATER_THAN'; gt.inputs[1].default_value = 0.0
L.new(sn.outputs[0], gt.inputs[0])
gmix = N.new("ShaderNodeMix"); gmix.data_type = 'RGBA'
gmix.inputs[6].default_value = (0.22, 0.5, 0.12, 1); gmix.inputs[7].default_value = (0.42, 0.72, 0.22, 1)
L.new(gt.outputs[0], gmix.inputs["Factor"])
gnz = N.new("ShaderNodeTexNoise"); gnz.inputs["Scale"].default_value = 6.0; gnz.inputs["Detail"].default_value = 6.0
L.new(geo.outputs["Position"], gnz.inputs["Vector"])
gvar = N.new("ShaderNodeMix"); gvar.data_type = 'RGBA'; gvar.blend_type = 'MULTIPLY'
gvar.inputs["Factor"].default_value = 0.35
L.new(gmix.outputs[2], gvar.inputs[6]); L.new(gnz.outputs["Color"], gvar.inputs[7])
gfix = N.new("ShaderNodeMix"); gfix.data_type = 'RGBA'; gfix.inputs["Factor"].default_value = 0.6
L.new(gvar.outputs[2], gfix.inputs[6]); L.new(gmix.outputs[2], gfix.inputs[7])
# soil cut face: textured brown with dark cracks (ref style)
snz = N.new("ShaderNodeTexNoise"); snz.inputs["Scale"].default_value = 3.0; snz.inputs["Detail"].default_value = 10.0
snz.inputs["Roughness"].default_value = 0.65
L.new(geo.outputs["Position"], snz.inputs["Vector"])
cr = N.new("ShaderNodeValToRGB"); ce = cr.color_ramp.elements
ce[0].position = 0.3; ce[0].color = (0.33, 0.18, 0.08, 1)
ce[1].position = 0.7; ce[1].color = (0.62, 0.36, 0.17, 1)
L.new(snz.outputs["Fac"], cr.inputs["Fac"])
vor = N.new("ShaderNodeTexVoronoi"); vor.feature = 'DISTANCE_TO_EDGE'; vor.inputs["Scale"].default_value = 0.7
L.new(geo.outputs["Position"], vor.inputs["Vector"])
crk = N.new("ShaderNodeMath"); crk.operation = 'LESS_THAN'; crk.inputs[1].default_value = 0.018
L.new(vor.outputs["Distance"], crk.inputs[0])
soil = N.new("ShaderNodeMix"); soil.data_type = 'RGBA'
L.new(crk.outputs[0], soil.inputs["Factor"]); L.new(cr.outputs["Color"], soil.inputs[6])
soil.inputs[7].default_value = (0.16, 0.08, 0.035, 1)
dark = N.new("ShaderNodeMapRange"); dark.inputs["From Min"].default_value = -10.0; dark.inputs["From Max"].default_value = 0.0
dark.inputs["To Min"].default_value = 0.55; dark.inputs["To Max"].default_value = 1.0
L.new(sxyz.outputs["Z"], dark.inputs["Value"])
sdk = N.new("ShaderNodeMix"); sdk.data_type = 'RGBA'; sdk.blend_type = 'MULTIPLY'; sdk.inputs["Factor"].default_value = 1.0
L.new(soil.outputs[2], sdk.inputs[6])
cmb = N.new("ShaderNodeCombineXYZ"); L.new(dark.outputs["Result"], cmb.inputs[0]); L.new(dark.outputs["Result"], cmb.inputs[1]); L.new(dark.outputs["Result"], cmb.inputs[2])
L.new(cmb.outputs[0], sdk.inputs[7])
bmp = N.new("ShaderNodeBump"); bmp.inputs["Strength"].default_value = 0.6
L.new(snz.outputs["Fac"], bmp.inputs["Height"]); L.new(bmp.outputs["Normal"], bs.inputs["Normal"])
cap = N.new("ShaderNodeMapRange"); cap.inputs["From Min"].default_value = -0.18; cap.inputs["From Max"].default_value = -0.1
L.new(sxyz.outputs["Z"], cap.inputs["Value"])
fin = N.new("ShaderNodeMix"); fin.data_type = 'RGBA'
L.new(cap.outputs["Result"], fin.inputs["Factor"])
L.new(sdk.outputs[2], fin.inputs[6]); L.new(gfix.outputs[2], fin.inputs[7])
L.new(fin.outputs[2], bs.inputs["Base Color"])
# ground split around a big cut-away pool at the front face (pool x PX0..PX1, y FRONT_Y..PY1, floor PZF)
PX0, PX1, PY1, PZB = -3.2, 5.2, 3.6, -1.95
box("GroundBelow", (0, 26.2, (PZB - 12.0) / 2), (400, 55.6, 12.0 + PZB), grass_m)
box("GroundL", ((-200 + PX0) / 2, 26.2, PZB / 2), (200 + PX0, 55.6, -PZB), grass_m)
box("GroundR", ((200 + PX1) / 2, 26.2, PZB / 2), (200 - PX1, 55.6, -PZB), grass_m)
box("GroundB", ((PX0 + PX1) / 2, (PY1 + 54.0) / 2, PZB / 2), (PX1 - PX0, 54.0 - PY1, -PZB), grass_m)
under_m = mat("Underside", (0.3, 0.2, 0.12), 0.9)
bpy.ops.mesh.primitive_plane_add(size=1200, location=(0, 0, -12.05))
bpy.context.object.data.materials.append(under_m)
far = grass_m
bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 0, -0.03))
fp = bpy.context.object; fp.scale = (400000, 400000, 1); fp.location = (0, 200050, -0.03)
fp.data.materials.append(far)
stone_m = mat("Stone", (0.7, 0.66, 0.6), 0.8)
for i in range(30):
    px_, pz_ = random.uniform(-30, 30), random.uniform(-5.6, -0.6)
    if PX0 - 0.4 < px_ < PX1 + 0.4 and pz_ > PZB - 0.4:
        continue
    sphere("Peb", (px_, FRONT_Y - 0.02, pz_), random.uniform(0.12, 0.3),
           stone_m, scale=(1.3, 0.5, 0.8), sub=1, smooth=False)

for sx in (-1, 1):   # lawn beside the diorama (no void at the sides)
    bpy.ops.mesh.primitive_plane_add(size=1, location=(sx * 100016, 26.2, -0.03))
    o = bpy.context.object; o.scale = (199968, 55.6, 1); o.data.materials.append(far)

# ---------------- house + trees ----------------
wall_m = mat("Wall", (0.86, 0.8, 0.7), 0.85)
roof_m = stripe_mat("Roof", (0.78, 0.38, 0.2), (0.6, 0.27, 0.14), axis="Z", freq=28.0, thresh=0.5, rough=0.7)
trim_m = mat("Trim", (0.97, 0.97, 0.95), 0.6)
win_m = mat("Window", (0.15, 0.3, 0.55), 0.08, metal=0.2)
HX, HY, HW, HD, HH = 2.0, 16.0, 8.0, 4.0, 4.6
box("House", (HX, HY, HH / 2), (HW, HD, HH), wall_m)
bpy.ops.mesh.primitive_cube_add()
roof = bpy.context.object; roof.name = "Roof"
rw, rd, rh = HW + 0.8, HD + 1.0, 2.2
verts = [(-rw/2, -rd/2, 0), (rw/2, -rd/2, 0), (rw/2, rd/2, 0), (-rw/2, rd/2, 0), (-rw/2, 0, rh), (rw/2, 0, rh)]
faces = [(0, 1, 5, 4), (3, 4, 5, 2), (0, 4, 3), (1, 2, 5), (0, 3, 2, 1)]
me = bpy.data.meshes.new("RoofMesh"); me.from_pydata(verts, [], faces); me.update()
roof.data = me; roof.location = (HX, HY, HH); roof.data.materials.append(roof_m)
roof.modifiers.new("s", 'SOLIDIFY').thickness = 0.18
fy = HY - HD / 2
for x in (-2.6, -0.9, 0.9, 2.6):
    for z in (1.4, 3.5):
        if x == -0.9 and z == 1.4:
            continue
        box("WinFrame", (HX + x, fy - 0.03, z), (1.05, 0.08, 1.2), trim_m)
        box("WinGlass", (HX + x, fy - 0.07, z), (0.85, 0.04, 1.0), win_m)
box("Door", (HX - 0.9, fy - 0.05, 1.05), (1.0, 0.08, 2.1), mat("DoorM", (0.2, 0.45, 0.85), 0.6))
trunk_m = mat("Trunk", (0.45, 0.28, 0.15), 0.9)
fol = [mat("Fol1", (0.15, 0.5, 0.18), 0.85), mat("Fol2", (0.25, 0.62, 0.22), 0.85)]
def tree(x, y, h=3.4, r=1.4):
    cyl("Trunk", (x, y, h / 2), 0.18, h, trunk_m, verts=8)
    sphere("Crown", (x, y, h + 0.8), r, random.choice(fol), sub=1, smooth=False)
    sphere("Crown", (x + 0.4, y, h + 1.6), r * 0.75, random.choice(fol), sub=1, smooth=False)
for (x, y) in [(-17, 12), (-8, 22), (8.8, 24), (-12, 30), (26, 30), (-1, 26), (12, 34)]:
    tree(x, y, random.uniform(3.0, 4.2), random.uniform(1.3, 1.8))
for x in (-2.2, 6.4):
    sphere("Bush", (x, 13.4, 0.5), 0.8, fol[1], scale=(1.3, 0.9, 0.8), sub=1, smooth=False)


# ---------------- garden detail (ref style): patio, pots, chairs, hedges, pool, shutters ----------------
stone_p = mat("Patio", (0.78, 0.72, 0.62), 0.8)
box("Patio", (HX, fy - 1.6, 0.04), (9.0, 3.0, 0.08), stone_p, bevel=0.02)
shut_m = mat("Shutter", (0.12, 0.28, 0.55), 0.6)
for x in (-2.6, -0.9, 0.9, 2.6):
    for z in (1.4, 3.5):
        if x == -0.9 and z == 1.4:
            continue
        for sxs in (-1, 1):
            box("Shutter", (HX + x + sxs * 0.66, fy - 0.06, z), (0.26, 0.05, 1.2), shut_m)
pot_m = mat("Pot", (0.72, 0.36, 0.2), 0.7)
for (x, y) in [(HX - 3.8, fy - 0.8), (HX + 3.8, fy - 0.8), (HX - 2.0, fy - 2.7), (HX + 1.2, fy - 2.7)]:
    cyl("Pot", (x, y, 0.28), 0.26, 0.5, pot_m, r2=0.2, verts=14)
    sphere("PotPlant", (x, y, 0.72), 0.34, fol[1], sub=1, smooth=False)
chair_m = mat("Chair", (0.96, 0.96, 0.94), 0.5)
for x in (HX + 2.6, HX + 3.4):
    box("ChairSeat", (x, fy - 1.9, 0.45), (0.5, 0.5, 0.06), chair_m)
    box("ChairBack", (x, fy - 1.66, 0.75), (0.5, 0.05, 0.6), chair_m)
    for dx in (-0.22, 0.22):
        for dy in (-0.22, 0.22):
            box("ChairLeg", (x + dx, fy - 1.9 + dy, 0.22), (0.04, 0.04, 0.44), chair_m)
hedge_m = mat("Hedge", (0.16, 0.4, 0.14), 0.9)
box("HedgeBack", (0, HY + 6.0, 0.6), (40, 0.9, 1.2), hedge_m, bevel=0.15)
box("HedgeL", (-19.5, HY - 4, 0.6), (0.9, 20, 1.2), hedge_m, bevel=0.15)

from mathutils import Quaternion, Matrix
def keyscale(o, keys):
    for f, s in keys:
        o.scale = (s,) * 3 if not isinstance(s, tuple) else s
        o.keyframe_insert("scale", frame=f)
def keyrot(o, keys):
    for f, r in keys:
        o.rotation_euler = r; o.keyframe_insert("rotation_euler", frame=f)
def parent_to(o, p):
    bpy.context.view_layer.update()
    o.parent = p
    o.matrix_parent_inverse = p.matrix_world.inverted()

lab_m = mat("LabelM", (1.0, 0.85, 0.2), 0.4, emit=(1.0, 0.8, 0.2), emit_strength=0.8)
white_lab = mat("LabW", (1, 1, 1), 0.4, emit=(1, 1, 1), emit_strength=0.7)
red_lab = mat("LabR", (0.95, 0.1, 0.08), 0.4, emit=(1.0, 0.1, 0.05), emit_strength=1.2)
pink_lab = mat("LabP", (1.0, 0.45, 0.7), 0.4, emit=(1.0, 0.4, 0.7), emit_strength=1.0)
blue_lab = mat("LabB", (0.2, 0.5, 1.0), 0.4, emit=(0.2, 0.5, 1.0), emit_strength=1.0)
green_lab = mat("LabG", (0.2, 0.9, 0.3), 0.4, emit=(0.2, 0.9, 0.3), emit_strength=1.0)
spark_m = glow_mat("Spark", (1.0, 0.95, 0.7), 5.0)
pspark_m = glow_mat("PSpark", (1.0, 0.5, 0.8), 5.0)
bud_m = glow_mat("Bud", (1.0, 0.35, 0.65), 1.7)
eyew = mat("EyeW", (1, 1, 1), 0.3)
eyeb = mat("EyeB", (0.03, 0.03, 0.04), 0.3)
shoe_m = mat("Shoe", (0.15, 0.15, 0.18), 0.6)
bubble_m = mat("Bubble", (0.92, 0.97, 1.0), 0.04, emit=(0.75, 0.9, 1.0), emit_strength=0.6)

def burst(loc, f, n=10, r=0.12, size=0.012, f_out=None, material=None, yoff=-0.02):
    for k in range(n):
        a = k / n * 6.283
        s_ = sphere("Burst", (loc[0] + r * math.cos(a), loc[1] + yoff, loc[2] + r * math.sin(a)), size, material or spark_m, sub=1)
        pop(s_, f, 3, f_out if f_out else f + 10)

# ---------------- camera helpers (subject in the lower third, labels in the upper part) ----------------
def overhead(cl, tl):
    dx, dy = cl[0] - tl[0], cl[1] - tl[1]
    hd = math.hypot(dx, dy)
    if cl[2] > 60 or hd > 40:
        return cl
    z = max(cl[2], tl[2] + 0.62 * hd)
    return (cl[0], cl[1], z)
LIFT = math.atan(0.36 * math.tan(math.atan(18 / 26)))
def aim(cl, subj):
    d = Vector(subj) - Vector(cl)
    ax_ = d.cross(Vector((0, 0, 1))).normalized()
    return tuple(Vector(cl) + Quaternion(ax_, LIFT) @ d)
TANV = 18 / 26
def SP(view, D, v, u=0.0):
    cl = Vector(overhead(*view)); t = Vector(aim(overhead(*view), view[1]))
    fwd = (t - cl).normalized()
    right = fwd.cross(Vector((0, 0, 1))).normalized(); up = right.cross(fwd)
    d = fwd + up * ((0.5 - v) * 2 * TANV) + right * (u * 2 * TANV * 9 / 16)
    return tuple(cl + d.normalized() * D)
def CL(view):
    return overhead(*view)
def label(name, body, view, D, v, size, m_, f_in, f_out, u=0.0):
    loc = SP(view, D, v, u); c = CL(view)
    fwd = Vector(loc) - Vector(c)
    t = text(name, body, loc, size, m_, extrude=size * 0.08)
    t.rotation_euler = (math.radians(90) - math.atan2(-fwd.z, math.hypot(fwd.x, fwd.y)) * 1.0, 0, math.atan2(-fwd.x, fwd.y) if False else math.atan2(fwd.x, -fwd.y) + math.pi)
    pop(t, f_in, 5, f_out)
    return t
def fit(body, D, size):
    return min(size, 0.72 * D * 2 * TANV * 9 / 16 / (max(len(body), 7) * 0.66))

# ---------------- people ----------------
def person(name, base, K_, shirt, pants, skin, hair):
    PX_, PY_, PZ_ = base
    g = group(name, base)
    def Q(dx, dy, dz):
        return (PX_ + dx * K_, PY_ + dy * K_, PZ_ + dz * K_)
    d = {"P": Q, "arms": [], "legs": []}
    allp = []
    for sx in (-1, 1):
        lg = group(name + "LegG", Q(sx * 0.13, 0, 0.78))
        attach([tube(name + "Leg", [Q(sx * 0.13, 0, 0.8), Q(sx * 0.14, 0, 0.08)], [0.1 * K_, 0.09 * K_], pants),
                box(name + "Shoe", Q(sx * 0.14, -0.06, 0.05), (0.17 * K_, 0.3 * K_, 0.1 * K_), shoe_m, bevel=0.03)], lg)
        d["legs"].append(lg)
        ag = group(name + "ArmG", Q(sx * 0.3, 0, 1.33))
        attach([tube(name + "Arm", [Q(sx * 0.3, 0, 1.35), Q(sx * 0.38, -0.03, 1.05), Q(sx * 0.38, -0.06, 0.8)], [0.075 * K_] * 3, shirt),
                sphere(name + "Hand", Q(sx * 0.38, -0.06, 0.76), 0.07 * K_, skin, sub=2)], ag)
        d["arms"].append(ag)
        allp += [sphere(name + "EyeW", Q(sx * 0.085, -0.21, 1.72), 0.055 * K_, eyew, scale=(1, 0.6, 1.2), sub=2),
                 sphere(name + "EyeB", Q(sx * 0.085, -0.25, 1.72), 0.028 * K_, eyeb, sub=1)]
    torso = sphere(name + "Torso", Q(0, 0, 1.1), 1.0, shirt, scale=(0.3 * K_, 0.22 * K_, 0.4 * K_), sub=3)
    head = sphere(name + "Head", Q(0, 0, 1.68), 0.25 * K_, skin, sub=3)
    hr = sphere(name + "Hair", Q(0, 0.04, 1.81), 0.24 * K_, hair, scale=(1.05, 1.0, 0.55), sub=2)
    sm = tube(name + "Smile", [Q(-0.08, -0.23, 1.6), Q(0, -0.26, 1.56), Q(0.08, -0.23, 1.6)], [0.014 * K_] * 3, eyeb)
    d.update(torso=torso, head=head, smile=sm)
    attach(allp + [torso, head, hr, sm] + d["arms"] + d["legs"], g)
    return g, d
skin_m = mat("Skin", (0.95, 0.74, 0.58), 0.6)

def E(i):
    return S[i + 1] if i + 1 < len(S) else FRAMES
def W(i, fr):
    return int(S[i] + fr * (E(i) - S[i]))

def fcurves(o_):
    ad = o_.animation_data
    if ad is None or ad.action is None:
        return []
    try:
        return list(ad.action.fcurves)
    except AttributeError:
        from bpy_extras import anim_utils
        return list(anim_utils.action_get_channelbag_for_slot(ad.action, ad.action_slot).fcurves)

def vis(o, spans, s=1.0):
    """Object visible (scale s) only inside the given [a, b) frame spans; hard switches."""
    s = s if isinstance(s, tuple) else (s,) * 3
    keys = [(0, (0.001,) * 3)]
    for a, b in spans:
        keys += [(max(a - 1, 0), (0.001,) * 3), (a, s), (b - 1, s), (b, (0.001,) * 3)]
    keys.sort(key=lambda k: k[0])
    for f, v in keys:
        o.scale = v; o.keyframe_insert("scale", frame=f)
    for fc in fcurves(o):
        if fc.data_path == "scale":
            for p in fc.keyframe_points:
                p.interpolation = 'CONSTANT'

def jumps(o, keys, path="location"):
    """Hard-cut positions: list of (frame, value) held until the next key."""
    for f, v in keys:
        setattr(o, path, v); o.keyframe_insert(path, frame=f)
    for fc in fcurves(o):
        if fc.data_path == path:
            for p in fc.keyframe_points:
                p.interpolation = 'CONSTANT'

def jitter(o, strength=0.15, scale=6.0, path="location"):
    for fc in fcurves(o):
        if fc.data_path == path:
            m = fc.modifiers.new('NOISE'); m.strength = strength; m.scale = scale; m.phase = random.uniform(0, 100)
def seg(name, a, b, r, material, verts=6):
    a, b = Vector(a), Vector(b); d = b - a
    o = cyl(name, tuple((a + b) / 2), r, d.length, material, verts=verts)
    o.rotation_mode = 'QUATERNION'; o.rotation_quaternion = d.to_track_quat('Z', 'Y')
    return o

def boxc(name, loc, size, material, bevel=0.0):
    """box() bakes its location into the mesh; this keeps the origin at loc so rotations pivot in place."""
    o = box(name, loc, size, material, bevel)
    o.data.transform(Matrix.Translation((-loc[0], -loc[1], -loc[2])))
    o.location = loc
    return o

tile_m = stripe_mat("Tile", (0.93, 0.97, 1.0), (0.7, 0.85, 0.95), axis="Z", freq=18.0, thresh=0.85, rough=0.3)
coping_m = mat("Coping", (0.92, 0.9, 0.84), 0.6)
water_m = bpy.data.materials.new("Water"); water_m.use_nodes = True
wb = water_m.node_tree.nodes["Principled BSDF"]
wb.inputs["Base Color"].default_value = (0.25, 0.68, 0.95, 1); wb.inputs["Roughness"].default_value = 0.3
wb.inputs["Alpha"].default_value = 0.32
wb.inputs["Emission Color"].default_value = (0.2, 0.6, 0.9, 1); wb.inputs["Emission Strength"].default_value = 0.12
# ---------------- the pool ----------------
PZF, PZW = -1.75, -0.15
box("PoolFloor", ((PX0 + PX1) / 2, (FRONT_Y + PY1) / 2, (PZB + PZF) / 2), (PX1 - PX0, PY1 - FRONT_Y, PZF - PZB), tile_m)
box("PoolWallL", (PX0 + 0.1, (FRONT_Y + PY1) / 2, PZB / 2), (0.2, PY1 - FRONT_Y, -PZB), tile_m)
box("PoolWallR", (PX1 - 0.1, (FRONT_Y + PY1) / 2, PZB / 2), (0.2, PY1 - FRONT_Y, -PZB), tile_m)
box("PoolWallB", ((PX0 + PX1) / 2, PY1 - 0.1, PZB / 2), (PX1 - PX0, 0.2, -PZB), tile_m)
box("Water", ((PX0 + PX1) / 2, (FRONT_Y + PY1 - 0.2) / 2 - 0.005, (PZF + PZW) / 2), (PX1 - PX0 - 0.42, PY1 - 0.2 - FRONT_Y - 0.01, PZW - PZF), water_m)
for (x, y, sx_, sy_) in [(PX0 - 0.15, (FRONT_Y + PY1) / 2, 0.5, PY1 - FRONT_Y), (PX1 + 0.15, (FRONT_Y + PY1) / 2, 0.5, PY1 - FRONT_Y),
                         ((PX0 + PX1) / 2, PY1 + 0.15, PX1 - PX0 + 0.8, 0.5)]:
    box("Coping", (x, y, 0.04), (sx_, sy_, 0.1), coping_m, bevel=0.02)
for x in (PX0 + 0.1, PX1 - 0.1):
    box("GlassFrame", (x, FRONT_Y - 0.03, PZB / 2), (0.24, 0.06, -PZB), trim_m)
box("GlassFrameB", ((PX0 + PX1) / 2, FRONT_Y - 0.03, PZB + 0.1), (PX1 - PX0, 0.06, 0.2), trim_m)

# =====================================================================================
# Day 28 — What if you had a pistol shrimp's snap?
# Facts used (Versluis et al. 2000 Science "How snapping shrimp snap: through cavitating bubbles";
# Lohse et al. 2001 Nature "Snapping shrimp make flashing bubbles"; Au & Banks 1998 JASA; NOAA / Smithsonian Ocean):
#   snapping (pistol) shrimp, Alpheidae: typically ~3-5 cm long; one oversized snapping claw, up to about half the body
#   length. The claw closes extremely fast (well under a millisecond; far faster than a ~100-400 ms blink) and shoots a
#   water jet at ~25 m/s (~90-100 km/h). Low pressure in the jet opens a cavitation bubble; its collapse makes the bang
#   (peak-to-peak source levels measured up to ~210-218 dB re 1 uPa at 1 m — one of the loudest sounds in the ocean),
#   a tiny flash ("shrimpoluminescence") and, for an instant, an estimated ~4,700 C (>5,000 K) inside the bubble
#   (the Sun's surface is ~5,500 C). The shock stuns or kills small prey. Large colonies crackle loudly enough to
#   interfere with sonar (noted since WWII).  The human part is a playful "what if".
# =====================================================================================
orange_m = mat("ShOrange", (1.0, 0.42, 0.12), 0.4)
band_m = mat("ShBand", (1.0, 0.93, 0.85), 0.45)
red_m = mat("ShRed", (0.95, 0.14, 0.12), 0.35)
yel_m = mat("ShYellow", (1.0, 0.85, 0.15), 0.4)
sand_m = mat("Sand", (0.95, 0.85, 0.58), 0.9)
rock_ms = [mat(f"PRock{i}", c, 0.85) for i, c in enumerate([(0.55, 0.5, 0.48), (0.8, 0.45, 0.4), (0.45, 0.55, 0.62)])]
weed_m = mat("Weed", (0.2, 0.75, 0.35), 0.6)
flash_m = glow_mat("FlashM", (0.85, 0.95, 1.0), 6.0)
shock_m = glow_mat("Shock", (0.85, 0.97, 1.0), 3.0)
jet_m = mat("JetM", (0.8, 0.95, 1.0), 0.1, emit=(0.7, 0.92, 1.0), emit_strength=1.6)
heat_m = glow_mat("HeatM", (1.0, 0.55, 0.12), 8.0)
sun_m = glow_mat("SunM", (1.0, 0.75, 0.15), 6.0)
ray_m = glow_mat("RayM", (1.0, 0.85, 0.3), 4.0)
fish_m = mat("Fish", (0.2, 0.75, 1.0), 0.45)
fin_m = mat("Fin", (1.0, 0.85, 0.15), 0.5)
sub_m = mat("SubM", (1.0, 0.82, 0.1), 0.35)
port_m = mat("Port", (0.25, 0.6, 0.95), 0.1)
db_m = stripe_mat("DbBar", (1.0, 0.2, 0.1), (1.0, 0.8, 0.1), axis="Z", freq=9.0, thresh=0.6, rough=0.4)
lounger_m = mat("Lounger", (0.2, 0.6, 0.95), 0.5)
glove_m = mat("Glove", (1.0, 0.35, 0.1), 0.35, emit=(1.0, 0.3, 0.05), emit_strength=0.25)
HID = (0, 60, -30)
wb.inputs["Alpha"].default_value = 0.24; wb.inputs["Emission Strength"].default_value = 0.04

def torus(name, loc, R, r, material, rot=(math.radians(90), 0, 0)):
    bpy.ops.mesh.primitive_torus_add(major_radius=R, minor_radius=r, location=loc, rotation=rot, major_segments=40, minor_segments=8)
    o = bpy.context.object; o.name = name; o.data.materials.append(material)
    return o

def shock(loc, f, R1=1.0, n=1, gap=4, dur=10, r=0.03, rot=(math.radians(90), 0, 0)):
    """expanding glowing shock rings facing the camera."""
    for k in range(n):
        t = torus("Shock", loc, 1.0, r, shock_m, rot)
        f0 = f + k * gap
        keyscale(t, [(0, 0.001), (f0 - 1, 0.001), (f0, 0.08), (f0 + dur, R1), (f0 + dur + 1, 0.001)])

def flash_at(loc, f, size=0.25, energy=60):
    size *= 0.6; energy *= 0.25
    fs = sphere("Flash", loc, size, flash_m, sub=2)
    keyscale(fs, [(0, 0.001), (f - 1, 0.001), (f, 1.3), (f + 2, 0.7), (f + 4, 1.0), (f + 7, 0.001)])
    bpy.ops.object.light_add(type='POINT', location=(loc[0], loc[1] - 0.6, loc[2] + 0.2))
    L_ = bpy.context.object; L_.data.color = (0.8, 0.92, 1.0); L_.data.shadow_soft_size = 0.2
    L_.data.energy = 0; L_.data.keyframe_insert("energy", frame=f - 1)
    L_.data.energy = energy; L_.data.keyframe_insert("energy", frame=f)
    L_.data.energy = 0; L_.data.keyframe_insert("energy", frame=f + 7)
    L_.data.keyframe_insert("energy", frame=0)

# ---------------- pool floor dressing: sand, rocks, weeds ----------------
box("SandBed", ((PX0 + PX1) / 2, 1.0, PZF + 0.03), (PX1 - PX0 - 0.42, 5.0, 0.06), sand_m)
for i in range(16):
    x = random.uniform(PX0 + 0.4, PX1 - 0.4)
    if -2.4 < x < 2.0 and random.random() < 0.6:
        x = random.choice([-2.7, 2.3]) + random.uniform(-0.3, 0.3)
    sphere("PRock", (x, random.uniform(2.0, 3.2), PZF + 0.05), random.uniform(0.1, 0.22), random.choice(rock_ms),
           scale=(1.3, 1, 0.7), sub=1, smooth=False)
for x in (-2.8, -2.5, -0.2, 0.3, 2.0, 4.7):
    y = random.uniform(2.6, 3.2)
    tube("Weed", [(x, y, PZF), (x + 0.08, y, PZF + 0.35), (x - 0.05, y, PZF + 0.7)], [0.04, 0.035, 0.02], weed_m)
for i in range(14):
    p0 = (random.uniform(PX0 + 0.5, PX1 - 0.5), random.uniform(0.0, 2.8), PZF + 0.1)
    b_ = sphere("PoolBub", p0, random.uniform(0.02, 0.04), bubble_m, sub=1)
    off = random.randint(0, 72)
    for f in range(-off, FRAMES + 72, 72):
        b_.location = p0; b_.keyframe_insert("location", frame=max(f, 0))
        b_.location = (p0[0] + 0.1, p0[1], PZW - 0.05); b_.keyframe_insert("location", frame=f + 71)

# ---------------- the cartoon pistol shrimp (big cartoon scale) ----------------
SH = Vector((-1.25, 0.6, -1.42))
K = 0.72
def P(x, y, z):
    return tuple(SH + Vector((x, y, z)) * K)
shr = group("Shrimp", tuple(SH))
sp = [sphere("Cara", P(0.1, 0, 0.02), K * 0.3, orange_m, scale=(1.55, 0.85, 0.82), sub=3),
      cyl("Rostrum", P(0.62, 0, 0.08), K * 0.07, K * 0.25, orange_m, rot=(0, math.radians(90), 0), r2=K * 0.01, verts=10)]
for i in range(6):
    x = -0.32 - i * 0.17; r = 0.23 - i * 0.017
    sp.append(sphere("Seg", P(x, 0, 0.02 - i * 0.012), K * r, orange_m, scale=(0.8, 1, 0.9), sub=2))
    sp.append(box("Band", P(x - 0.07, 0, 0.02 - i * 0.012), (K * 0.03, K * 2 * r * 0.95, K * 2 * r * 0.85), band_m))
for i, dz in enumerate([0.1, -0.05, 0.22]):
    sp.append(sphere("Fan", P(-1.42, 0, dz - 0.04), K * 0.15, [red_m, yel_m, red_m][i], scale=(1.3, 0.35, 0.6), sub=2))
for i in range(5):
    x = 0.15 - i * 0.16
    sp.append(tube("Leg", [P(x, -0.1, -0.12), P(x + 0.03, -0.14, -0.24), P(x + 0.06, -0.14, -0.34)], [K * 0.025] * 3, red_m))
for sy in (-1, 1):
    sp.append(sphere("ShEyeW", P(0.42, sy * 0.1, 0.28), K * 0.11, eyew, sub=2))
    sp.append(sphere("ShEyeB", P(0.45, sy * 0.1 - 0.09, 0.29), K * 0.05, eyeb, sub=1))
    sp.append(tube("Ant", [P(0.5, sy * 0.05, 0.18), P(0.9, sy * 0.14, 0.45), P(1.3, sy * 0.24, 0.8)], [K * 0.014] * 3, red_m))
# small claw (far side)
sp.append(tube("SArm", [P(0.3, 0.2, -0.08), P(0.62, 0.26, -0.12)], [K * 0.04] * 2, red_m))
sp.append(sphere("SClaw", P(0.72, 0.26, -0.12), K * 0.08, orange_m, scale=(1.5, 0.8, 0.8), sub=2))
# the BIG snapping claw (camera side)
sp += [tube("BArm", [P(0.25, -0.22, -0.08), P(0.5, -0.32, -0.05)], [K * 0.07, K * 0.07], red_m),
       sphere("Palm", P(0.86, -0.34, -0.03), K * 0.24, red_m, scale=(1.75, 0.85, 1.0), sub=3),
       sphere("PalmSpot", P(0.86, -0.53, 0.0), K * 0.09, yel_m, scale=(1.5, 0.3, 1.0), sub=2),
       cyl("Fixed", P(1.42, -0.34, -0.1), K * 0.11, K * 0.36, red_m, rot=(0, math.radians(90), 0), r2=K * 0.03, verts=14)]
DPV = P(1.2, -0.34, 0.08)
dac = group("Dactyl", DPV)
attach([cyl("DacF", P(1.43, -0.34, 0.08), K * 0.1, K * 0.44, orange_m, rot=(0, math.radians(90), 0), r2=K * 0.03, verts=14),
        sphere("DacTip", P(1.65, -0.34, 0.08), K * 0.045, yel_m, sub=1)], dac)
attach(sp + [dac], shr)
CT = Vector(P(1.66, -0.34, -0.02))          # claw tip (world)
OPEN, SHUT = (0, -0.8, 0), (0, 0.0, 0)
SNAPS = sorted([9, W(3, 0.5), S[4] + 3, W(11, 0.45), S[16] + 8])
dac.rotation_euler = OPEN; dac.keyframe_insert("rotation_euler", frame=0)
for i, f in enumerate(SNAPS):
    dac.rotation_euler = OPEN; dac.keyframe_insert("rotation_euler", frame=f - 4)
    dac.rotation_euler = SHUT; dac.keyframe_insert("rotation_euler", frame=f)
    nxt = SNAPS[i + 1] - 4 if i + 1 < len(SNAPS) else f + 30
    if nxt - f > 10:
        dac.keyframe_insert("rotation_euler", frame=f + 4)
        dac.rotation_euler = OPEN; dac.keyframe_insert("rotation_euler", frame=min(f + 14, nxt))
for f in range(0, FRAMES, 18):      # little bob
    shr.location = tuple(SH); shr.keyframe_insert("location", frame=f)
    shr.location = tuple(SH + Vector((0, 0, 0.02))); shr.keyframe_insert("location", frame=f + 9)
def snap_fx(f, size=0.18, rings=1):
    loc = tuple(CT + Vector((0.12, -0.02, 0)))
    flash_at(loc, f, size, 40)
    shock(loc, f, R1=0.6, n=rings)
    burst(loc, f, n=10, r=0.3, size=0.03, material=spark_m, f_out=f + 9)

# ---- line 0: hook snap
snap_fx(9, 0.2, 2)
# ---- line 1: ruler "5 cm"
rul = group("Ruler", (SH.x - 0.2, SH.y - 0.55, PZF + 0.08))
rp = [box("RulerB", (SH.x - 0.05, SH.y - 0.55, PZF + 0.08), (2.1, 0.3, 0.06), mat("RulerM", (1.0, 0.92, 0.3), 0.5))]
for i in range(11):
    rp.append(box("Tick", (SH.x - 1.0 + i * 0.19, SH.y - 0.7, PZF + 0.12), (0.025, 0.02, 0.02), eyeb, ))
    if i % 5 == 0:
        rp.append(box("TickL", (SH.x - 1.0 + i * 0.19, SH.y - 0.66, PZF + 0.12), (0.035, 0.1, 0.02), eyeb))
attach(rp, rul)
vis(rul, [(S[1], E(1) + 4)])
t5 = text("T5", "5 cm", (SH.x - 0.05, SH.y - 0.72, PZF + 0.32), 0.26, red_lab, extrude=0.02)
pop(t5, S[1] + 4, 5, E(1) + 4)
# ---- line 2: giant claw pulses + glow ring
palm = sp[[o.name for o in sp].index("Palm") if "Palm" in [o.name for o in sp] else 0]
cring = torus("ClawRing", tuple(Vector(P(1.0, -0.34, -0.03)) + Vector((0, -0.25, 0))), 0.62, 0.035, lab_m)
keyscale(cring, [(0, 0.001), (S[2] + 1, 0.001), (S[2] + 5, 1.2), (S[2] + 8, 1.0), (E(2) - 1, 1.0), (E(2), 0.001)])
cring.scale = (1.0, 1.0, 1.0)
keyscale(shr, [(0, 1.0), (S[2] + 2, 1.0), (S[2] + 6, 1.08), (S[2] + 10, 1.0)])
# ---- line 3: faster than a blink — a big cartoon eye blinks slowly while the claw snaps
EYC = (0.75, 0.5, -0.78)
eyeg = group("BlinkEye", EYC)
ep_ = [sphere("BEw", EYC, 0.3, eyew, scale=(1.3, 0.6, 1.0), sub=3),
       sphere("BEb", (EYC[0], EYC[1] - 0.16, EYC[2]), 0.13, mat("Iris", (0.15, 0.45, 0.9), 0.3), scale=(1, 0.4, 1), sub=2),
       sphere("BEp", (EYC[0], EYC[1] - 0.2, EYC[2]), 0.06, eyeb, scale=(1, 0.4, 1), sub=1)]
attach(ep_, eyeg)
vis(eyeg, [(S[3], E(3) + 2)])
keyscale(eyeg, [(S[3], 1.0), (W(3, 0.35), 1.0), (W(3, 0.7), (1, 1, 0.08)), (W(3, 0.95), 1.0)])
snap_fx(W(3, 0.5), 0.18, 1)
# ---- lines 4-6: the jet, the bubble, the bang
J0 = CT + Vector((0.05, 0, 0))
jet = cyl("Jet", tuple(J0), 0.13, 1.0, jet_m, rot=(0, math.radians(90), 0), r2=0.05, verts=16)
jet.data.transform(Matrix.Translation((0, 0, 0.5)))      # base at the claw, grows along +x
jet.data.transform(Matrix.Rotation(0, 4, 'Z'))
JF = S[4] + 3
keyscale(jet, [(0, 0.001), (JF - 1, 0.001), (JF, (1, 1, 0.1)), (JF + 6, (1.2, 1.2, 1.5)), (E(5) - 2, (1.2, 1.2, 1.5)), (E(5), 0.001)])
for k in range(5):
    st = box("Streak", (0, 0, 0), (0.5, 0.05, 0.05), glow_mat(f"Strk{k}", (1, 1, 1), 2.5))
    z_ = J0.z - 0.12 + k * 0.06
    for c in range(3):
        f0 = JF + c * 9 + k
        key_loc(st, [(f0, (J0.x + 0.2, J0.y - 0.05, z_)), (f0 + 8, (J0.x + 1.6, J0.y - 0.05, z_))])
    vis(st, [(JF + k, E(4))])
snap_fx(JF, 0.16, 1)
BUB = Vector((CT.x + 0.85, CT.y, CT.z + 0.05))
bub = sphere("BigBubble", tuple(BUB), 0.32, bubble_m, sub=3)
BC = W(6, 0.35)                                   # collapse frame
keyscale(bub, [(0, 0.001), (S[5] - 1, 0.001), (S[5] + 3, 0.2), (S[5] + 12, 0.9), (E(5), 1.0), (BC - 3, 1.05), (BC, 0.05), (BC + 1, 0.001)])
for i in range(10):
    p_ = tuple(BUB + Vector((random.uniform(-0.3, 0.3), -0.05, random.uniform(-0.25, 0.25))))
    bb = sphere("SmallBub", p_, random.uniform(0.03, 0.06), bubble_m, sub=1)
    vis(bb, [(S[5] + 4 + i, BC)])
flash_at(tuple(BUB), BC, 0.35, 120)
shock(tuple(BUB), BC, R1=1.6, n=3, gap=3, dur=10, r=0.04)
burst(tuple(BUB), BC, n=14, r=0.6, size=0.04, material=spark_m, f_out=BC + 10)
# ---- line 7: 210 dB meter + rings keep coming
DBX = BUB.x + 1.25
for f in (S[7] + 2, S[7] + 14, S[7] + 26):
    shock(tuple(BUB), f, R1=1.3, n=1, dur=10, r=0.035)
bar = box("DbBar", (DBX, 0.5, PZF + 0.06), (0.4, 0.4, 1.0), db_m)
bar.data.transform(Matrix.Translation((0, 0, 0.5)))
keyscale(bar, [(0, 0.001), (S[7] - 1, 0.001), (S[7], (1, 1, 0.02)), (S[7] + 16, (1, 1, 1.35)), (E(7) - 1, (1, 1, 1.35)), (E(7), 0.001)])
cap_ = box("DbCap", (DBX, 0.5, PZF + 1.45), (0.55, 0.5, 0.06), white_lab)
vis(cap_, [(S[7] + 16, E(7))])
# ---- line 8: a colony crackles; a toy submarine's sonar gets confused
minis = [(1.5, 1.6), (2.3, 2.3), (3.1, 1.3), (3.9, 2.0), (4.6, 1.2), (-2.4, 2.0), (-0.3, 2.4), (0.8, 2.6)]
for j, (x, y) in enumerate(minis):
    c = (x, y, PZF + 0.16)
    g = group("Mini", c)
    mp = [sphere("MiniB", c, 0.13, orange_m, scale=(1.6, 0.7, 0.7), sub=2),
          sphere("MiniC", (x + 0.28, y - 0.08, PZF + 0.15), 0.08, red_m, scale=(1.6, 0.8, 0.9), sub=2),
          sphere("MiniE", (x + 0.12, y - 0.1, PZF + 0.27), 0.04, eyew, sub=1),
          sphere("MiniP", (x + 0.14, y - 0.13, PZF + 0.27), 0.02, eyeb, sub=1)]
    attach(mp, g)
    pop(g, S[8] + j, 4, E(8) + 2)
    for f in range(S[8] + 4 + j * 3, E(8) - 2, 11):
        burst((x + 0.4, y - 0.1, PZF + 0.16), f, n=6, r=0.15, size=0.025, material=spark_m, f_out=f + 5)
SUBC = Vector((3.0, 1.0, -0.78))
subg = group("Sub", tuple(SUBC))
spp = [sphere("SubB", tuple(SUBC), 0.3, sub_m, scale=(2.2, 1.0, 1.0), sub=3),
       box("SubT", tuple(SUBC + Vector((0.05, 0, 0.32))), (0.32, 0.18, 0.28), sub_m, bevel=0.04),
       cyl("SubPer", tuple(SUBC + Vector((0.1, 0, 0.56))), 0.025, 0.25, post_m if False else trim_m, verts=8),
       box("SubFin", tuple(SUBC + Vector((-0.66, 0, 0))), (0.12, 0.05, 0.4), sub_m)]
for k in range(3):
    spp.append(cyl("SubPort", tuple(SUBC + Vector((0.3 - k * 0.28, -0.29, 0.02))), 0.07, 0.04, port_m, rot=(math.radians(90), 0, 0), verts=14))
attach(spp, subg)
vis(subg, [(S[8], E(8) + 2)])
for k, f in enumerate(range(S[8] + 3, E(8) - 6, 7)):
    shock(tuple(SUBC + Vector((-0.75 - 0.0, 0, 0))), f, R1=0.9 + 0.3 * (k % 2), n=1, dur=7, r=0.025)
qs = text("SubQ", "?!", tuple(SUBC + Vector((0.0, -0.3, 0.75))), 0.4, red_lab, extrude=0.03)
pop(qs, S[8] + 10, 4, E(8) + 2)
keyrot(subg, [(S[8], (0, 0, 0)), (S[8] + 12, (0.15, 0, 0)), (S[8] + 20, (-0.15, 0, 0)), (S[8] + 28, (0.15, 0, 0)), (E(8), (0, 0, 0))])
# ---- lines 9-10: inside the bubble: 4,700 C — like the Sun's surface
HB = BUB
hb = sphere("HotBubble", tuple(HB), 0.3, heat_m, sub=3)
keyscale(hb, [(0, 0.001), (S[9] - 1, 0.001), (S[9] + 3, 0.6), (S[9] + 8, 1.0), (W(9, 0.6), 0.8), (W(9, 0.8), 1.05), (E(10) - 2, 1.0), (E(10), 0.001)])
bpy.ops.object.light_add(type='POINT', location=(HB.x, HB.y - 0.6, HB.z + 0.2))
hl = bpy.context.object; hl.data.color = (1.0, 0.6, 0.2); hl.data.shadow_soft_size = 0.3
hl.data.energy = 0; hl.data.keyframe_insert("energy", frame=S[9] - 1); hl.data.keyframe_insert("energy", frame=0)
hl.data.energy = 40; hl.data.keyframe_insert("energy", frame=S[9] + 4); hl.data.keyframe_insert("energy", frame=E(10) - 2)
hl.data.energy = 0; hl.data.keyframe_insert("energy", frame=E(10))
THX = HB.x + 0.8
thermo = group("Thermo", (THX, 0.5, PZF))
tp_ = [cyl("ThGlass", (THX, 0.55, PZF + 0.75), 0.08, 1.1, white_lab), sphere("ThBulb", (THX, 0.5, PZF + 0.2), 0.15, red_lab, sub=2)]
attach(tp_, thermo)
merc = box("Merc", (THX, 0.45, PZF + 0.2), (0.08, 0.04, 1.0), red_lab)
merc.data.transform(Matrix.Translation((0, 0, 0.5)))
vis(thermo, [(S[9], E(9))])
keyscale(merc, [(0, 0.001), (S[9] - 1, 0.001), (S[9], (1, 1, 0.05)), (S[9] + 18, (1, 1, 1.05)), (E(9) - 1, (1, 1, 1.05)), (E(9), 0.001)])
SUNC = Vector((HB.x + 1.35, 0.5, HB.z + 0.05))
sung = group("Sun", tuple(SUNC))
sunp = [sphere("SunB", tuple(SUNC), 0.42, sun_m, sub=3)]
for k in range(12):
    a = k / 12 * 6.283
    sunp.append(seg("Ray", tuple(SUNC + Vector((0.52 * math.cos(a), 0, 0.52 * math.sin(a)))),
                    tuple(SUNC + Vector((0.72 * math.cos(a), 0, 0.72 * math.sin(a)))), 0.03, ray_m))
attach(sunp, sung)
keyscale(sung, [(0, 0.001), (S[10] - 1, 0.001), (S[10] + 3, 1.2), (S[10] + 6, 1.0), (E(10) - 1, 1.0), (E(10), 0.001)])
keyrot(sung, [(S[10], (0, 0, 0)), (E(10), (0, math.radians(40), 0))])
eqs = text("Eq", "=", tuple((HB + SUNC) / 2 + Vector((0, -0.2, 0))), 0.35, white_lab, extrude=0.03)
pop(eqs, S[10] + 4, 4, E(10))
# ---- line 11: a small fish swims up, SNAP, stunned (belly up, dizzy stars)
FHIT = W(11, 0.45)
FP0 = Vector((2.8, 0.45, -1.3)); FP1 = Vector((CT.x + 0.55, 0.45, -1.35))
fishg = group("Fish", tuple(FP1))
fpp = [sphere("FBody", tuple(FP1), 0.22, fish_m, scale=(1.6, 0.6, 1.0), sub=3),
       cyl("FTail", tuple(FP1 + Vector((0.42, 0, 0))), 0.18, 0.2, fin_m, rot=(0, math.radians(90), 0), r2=0.02, verts=12),
       sphere("FFin", tuple(FP1 + Vector((0.0, 0, 0.22))), 0.1, fin_m, scale=(1.4, 0.3, 0.6), sub=1),
       sphere("FEyeW", tuple(FP1 + Vector((-0.2, -0.12, 0.06))), 0.07, eyew, sub=2),
       sphere("FEyeB", tuple(FP1 + Vector((-0.22, -0.17, 0.06))), 0.035, eyeb, sub=1)]
attach(fpp, fishg)
vis(fishg, [(S[11], E(11) + 2)])
key_loc(fishg, [(S[11], tuple(FP0)), (FHIT, tuple(FP1)), (FHIT + 4, tuple(FP1 + Vector((0.15, 0, 0.05)))), (E(11) + 2, tuple(FP1 + Vector((0.35, 0, 0.35))))])
keyrot(fishg, [(FHIT, (0, 0, 0)), (FHIT + 6, (math.radians(180), 0, 0))])
snap_fx(FHIT, 0.2, 2)
for k in range(5):
    a = k / 5 * 6.283
    st_ = sphere("Dizzy", (FP1.x + 0.2 + 0.32 * math.cos(a), 0.2, -0.85 + 0.1 * math.sin(a)), 0.05, lab_m, sub=1)
    pop(st_, FHIT + 6 + k, 3, E(11) + 2)

# ---------------- lines 12-16: YOU in the pool ----------------
STEP = (3.7, 2.7)
PB = (STEP[0], STEP[1], -1.15)
box("Step", (STEP[0], STEP[1] + 0.3, (PZF - 1.15) / 2 - 0.0), (1.5, 1.6, -1.15 - PZF + 0.0), tile_m)
shirt_m = mat("Shirt", (0.95, 0.3, 0.25), 0.6); pants_m = mat("Pants", (0.2, 0.3, 0.55), 0.7)
you, YD = person("You", (0, 0, 0), 1.0, shirt_m, pants_m, skin_m, mat("Hair", (0.25, 0.14, 0.07), 0.8))
RA = YD["arms"][1]
Q = YD["P"]
glove = group("Glove", Q(0.38, -0.06, 0.76))
gp = [sphere("GPalm", Q(0.42, -0.06, 0.74), 0.16, glove_m, scale=(1.5, 0.9, 1.0), sub=3),
      cyl("GFix", Q(0.64, -0.06, 0.68), 0.07, 0.22, glove_m, rot=(0, math.radians(90), 0), r2=0.02, verts=12),
      cyl("GDac", Q(0.66, -0.06, 0.8), 0.065, 0.26, mat("GloveY", (1.0, 0.8, 0.15), 0.4), rot=(0, math.radians(90), 0), r2=0.02, verts=12)]
attach(gp, glove)
parent_to(glove, RA)
keyscale(glove, [(0, 0.001), (S[13] + 2, 0.001), (S[13] + 6, 1.5), (S[13] + 9, 1.25)])
jumps(you, [(0, HID), (S[12], PB)])
you.rotation_euler = (0, 0, math.radians(-12)); you.keyframe_insert("rotation_euler", frame=0)
UP, DOWN = (0, math.radians(-150), 0), (0, math.radians(-30), 0)
SN12 = W(12, 0.62)
keyrot(RA, [(0, (0, 0, 0)), (S[12], (0, 0, 0)), (S[12] + 6, UP), (S[13] + 10, UP), (S[13] + 16, DOWN), (S[15] + 10, DOWN), (S[16] + 2, UP)])
HAND_UP = Vector(PB) + Vector((0.62, -0.3, 2.0))
clk = text("Click", "click", tuple(HAND_UP + Vector((0.35, -0.1, 0.2))), 0.2, white_lab, extrude=0.015)
pop(clk, SN12, 3, E(12))
burst(tuple(HAND_UP), SN12, n=6, r=0.12, size=0.02, material=spark_m, f_out=SN12 + 6)
tiny = torus("Ripple", (PB[0] + 0.6, PB[1] - 0.2, PZW + 0.02), 0.25, 0.015, shock_m, rot=(0, 0, 0))
keyscale(tiny, [(0, 0.001), (SN12, 0.001), (SN12 + 1, 0.3), (SN12 + 10, 1.0), (SN12 + 11, 0.001)])
burst(tuple(HAND_UP), S[13] + 4, n=14, r=0.5, size=0.05, material=spark_m, f_out=S[13] + 16)
# line 14: the underwater mega snap -> giant bubble -> blast -> water column
MB = S[14] + 4
GBC = Vector((2.3, 1.9, -0.95))
gb = sphere("GiantBubble", tuple(GBC), 0.8, bubble_m, sub=3)
GC = MB + 9
keyscale(gb, [(0, 0.001), (MB - 1, 0.001), (MB, 0.15), (MB + 6, 1.0), (GC - 1, 1.08), (GC + 1, 0.001)])
flash_at(tuple(GBC + Vector((0, -0.5, 0))), GC, 0.7, 600)
shock(tuple(GBC + Vector((0, -0.6, 0))), GC, R1=3.5, n=3, gap=3, dur=10, r=0.07)
shock((GBC.x, GBC.y, PZW + 0.05), GC + 1, R1=4.5, n=2, gap=4, dur=12, r=0.06, rot=(0, 0, 0))
gey_m = mat("GeyM", (0.55, 0.85, 1.0), 0.1, emit=(0.4, 0.75, 1.0), emit_strength=0.7)
col = cyl("Geyser", (GBC.x, GBC.y, PZW), 0.75, 1.0, gey_m, verts=24, r2=0.45)
col.data.transform(Matrix.Translation((0, 0, 0.5)))
keyscale(col, [(0, 0.001), (GC, 0.001), (GC + 1, (1, 1, 0.3)), (GC + 7, (1.1, 1.1, 5.5)), (S[15] + 8, (1.0, 1.0, 5.0)), (S[15] + 18, (0.6, 0.6, 0.3)), (S[15] + 19, 0.001)])
crown = sphere("GeyserTop", (GBC.x, GBC.y, PZW), 0.9, gey_m, scale=(1.3, 1.3, 0.7), sub=2, smooth=False)
key_loc(crown, [(GC + 1, (GBC.x, GBC.y, PZW + 0.3)), (GC + 7, (GBC.x, GBC.y, PZW + 5.5)), (S[15] + 8, (GBC.x, GBC.y, PZW + 5.0)), (S[15] + 18, (GBC.x, GBC.y, PZW + 0.3))])
vis(crown, [(GC + 1, S[15] + 18)])
for i in range(36):
    a = random.uniform(0, 6.283); dist = random.uniform(2.0, 6.5)
    p0 = (GBC.x, GBC.y, PZW + random.uniform(1.0, 5.0))
    p2 = (GBC.x + dist * math.cos(a), GBC.y + dist * math.sin(a) * 0.8, -0.0 if dist * abs(math.sin(a)) > 1 else PZW)
    pm = ((p0[0] + p2[0]) / 2, (p0[1] + p2[1]) / 2, p0[2] + random.uniform(1.0, 2.5))
    d_ = sphere("Drop", p0, random.uniform(0.12, 0.25), jet_m, sub=1)
    f0 = GC + 4 + i // 4
    key_loc(d_, [(f0, p0), (f0 + 9, pm), (f0 + 20, p2)])
    vis(d_, [(f0, f0 + 20)])
# line 15: chairs fly, pots fly, hedges flatten (all placed around the pool)
CHAIRS = []
for (x, y) in [(5.9, 0.2), (6.0, 1.6), (5.9, 3.0)]:
    c = (x, y, 0.0)
    g = group("Lounger", c)
    lp = [box("LSeat", (x, y, 0.32), (0.7, 1.6, 0.08), lounger_m, bevel=0.02),
          box("LBack", (x, y + 0.9, 0.55), (0.7, 0.08, 0.6), lounger_m, bevel=0.02)]
    for dx in (-0.3, 0.3):
        for dy in (-0.7, 0.7):
            lp.append(box("LLeg", (x + dx, y + dy, 0.14), (0.05, 0.05, 0.28), chair_m))
    attach(lp, g)
    CHAIRS.append(g)
for (x, y) in [(-3.9, 0.0), (-4.0, 1.4), (-3.9, 2.8)]:
    c = (x, y, 0.0)
    g = group("PoolChair", c)
    cp = [box("CSeat", (x, y, 0.45), (0.55, 0.55, 0.06), chair_m), box("CBack", (x - 0.25, y, 0.75), (0.05, 0.55, 0.6), chair_m)]
    for dx in (-0.22, 0.22):
        for dy in (-0.22, 0.22):
            cp.append(box("CLeg", (x + dx, y + dy, 0.22), (0.04, 0.04, 0.44), chair_m))
    attach(cp, g)
    CHAIRS.append(g)
FLY = S[15] + 2
for k, g in enumerate(CHAIRS):
    p0 = Vector(g.location)
    dirv = Vector(((GBC.x - p0.x) * 0.22, 1.0, 0)).normalized()
    p2 = p0 + dirv * random.uniform(3.5, 5.5)
    pm = (p0 + p2) / 2 + Vector((0, 0, random.uniform(1.5, 2.5)))
    f0 = FLY + k
    key_loc(g, [(f0, tuple(p0)), (f0 + 9, tuple(pm)), (f0 + 20, tuple(p2))])
    keyrot(g, [(f0, (0, 0, 0)), (f0 + 20, (random.uniform(3, 7), random.uniform(3, 7), random.uniform(1, 3)))])
for k in range(5):     # hedge segments behind the pool fall flat away from the blast
    x = -2.6 + k * 1.75
    hg = group("HedgeSeg", (x, 4.55, 0.0))
    attach([box("HedgeS", (x, 4.55, 0.55), (1.7, 0.6, 1.1), hedge_m, bevel=0.12),
            sphere("HedgeTop", (x, 4.55, 1.05), 0.45, fol[1], scale=(1.8, 0.7, 0.5), sub=1, smooth=False)], hg)
    f0 = FLY + 2 + k
    keyrot(hg, [(0, (0, 0, 0)), (f0, (0, 0, 0)), (f0 + 5, (math.radians(-95), 0, 0)), (f0 + 8, (math.radians(-84), 0, 0)), (f0 + 10, (math.radians(-88), 0, 0))])
for k in range(6):     # wind streaks
    st = box("Wind", (0, 0, 0), (1.6, 0.04, 0.04), glow_mat(f"Wind{k}", (1, 1, 1), 2.0))
    z_ = 0.6 + k * 0.35; side = 1 if k % 2 else -1
    key_loc(st, [(FLY + k, (GBC.x + side * 1.0, 0.0, z_)), (FLY + k + 10, (GBC.x + side * 7.0, 2.0, z_ + 0.4))])
    vis(st, [(FLY + k, FLY + k + 10)])
# line 16: water rains down, claw up, question mark
for i in range(20):
    x, y = random.uniform(0.0, 6.0), random.uniform(-0.5, 3.5)
    r_ = sphere("Rain", (x, y, 4.0), 0.05, jet_m, scale=(1, 1, 2.2), sub=1)
    f0 = S[16] + (i % 10) * 2
    key_loc(r_, [(f0, (x, y, 4.0)), (f0 + 10, (x, y, 0.0))])
    vis(r_, [(f0, f0 + 10)])
qm = text("QMark", "?", (PB[0] - 0.9, PB[1] - 0.5, 1.2), 1.0, lab_m, extrude=0.1)
pop(qm, S[16] + 6, 5)
keyrot(qm, [(S[16] + 6, (math.radians(90), 0, math.radians(-25))), (FRAMES, (math.radians(90), 0, math.radians(25)))])

# =================== views (camera start V -> end V2 per line, hard cut between lines) ===================
V, V2 = {}, {}
SX = SH.x
V[0] = ((-3.2, -4.6, 0.0), (SX + 0.6, 0.6, -1.35));    V2[0] = ((0.0, -3.9, 0.0), (SX + 0.8, 0.6, -1.35))
V[1] = ((0.2, -3.6, 0.0), (SX + 0.1, 0.6, -1.45));     V2[1] = ((-2.4, -3.3, 0.0), (SX + 0.1, 0.6, -1.45))
V[2] = ((1.4, -3.2, 0.0), (SX + 1.0, 0.5, -1.4));      V2[2] = ((-0.8, -2.8, 0.0), (SX + 1.0, 0.5, -1.4))
V[3] = ((-2.2, -3.9, 0.0), (-0.1, 0.55, -1.25));       V2[3] = ((0.9, -3.6, 0.0), (-0.1, 0.55, -1.25))
V[4] = ((-1.8, -4.2, 0.0), (0.3, 0.5, -1.4));          V2[4] = ((2.0, -3.9, 0.0), (0.7, 0.5, -1.4))
V[5] = ((2.6, -3.3, 0.0), tuple(BUB));                 V2[5] = ((0.3, -2.9, 0.0), tuple(BUB))
V[6] = ((-0.8, -3.7, 0.0), tuple(BUB));                V2[6] = ((2.4, -4.4, 0.0), tuple(BUB))
V[7] = ((-0.4, -5.2, 0.3), (BUB.x + 0.6, 0.5, -1.2));  V2[7] = ((2.8, -4.9, 0.3), (BUB.x + 0.7, 0.5, -1.2))
V[8] = ((-1.6, -6.6, 0.8), (1.6, 1.2, -1.05));         V2[8] = ((4.6, -6.4, 0.8), (2.2, 1.2, -1.05))
V[9] = ((2.6, -3.3, 0.0), (HB.x + 0.35, 0.5, -1.3));   V2[9] = ((0.0, -3.0, 0.0), (HB.x + 0.35, 0.5, -1.3))
V[10] = ((-0.2, -4.2, 0.0), (HB.x + 0.7, 0.5, -1.25)); V2[10] = ((2.8, -4.0, 0.0), (HB.x + 0.7, 0.5, -1.25))
V[11] = ((1.8, -3.8, 0.0), (CT.x + 0.4, 0.5, -1.3));   V2[11] = ((0.0, -3.6, 0.0), (CT.x + 0.4, 0.5, -1.3))
V[12] = ((5.6, -3.4, 0.6), (PB[0] + 0.3, PB[1], 0.3)); V2[12] = ((2.6, -3.2, 0.6), (PB[0] + 0.3, PB[1], 0.35))
V[13] = ((2.4, -3.0, 0.4), (PB[0] + 0.5, PB[1], 0.0)); V2[13] = ((5.0, -2.8, 0.4), (PB[0] + 0.5, PB[1], -0.1))
V[14] = ((-0.5, -8.6, 1.0), (2.6, 1.6, -0.3));         V2[14] = ((5.0, -9.6, 1.5), (2.8, 1.8, 0.6))
V[15] = ((-1.4, -9.4, 2.0), (2.8, 2.4, 0.6));          V2[15] = ((6.4, -9.0, 2.0), (2.8, 2.4, 0.6))
V[16] = ((5.8, -4.4, 0.6), (PB[0], PB[1], 0.3));       V2[16] = ((2.2, -4.8, 0.8), (PB[0] - 0.2, PB[1], 0.3))

def LB(i, name, body, m_, size=None, f_in=None, f_out=None, Dk=0.55, end=False, v=0.26, u=0.0):
    mid = lambda a, b: tuple((Vector(a) + Vector(b)) / 2)
    view = V2[i] if end else (mid(V[i][0], V2[i][0]), mid(V[i][1], V2[i][1]))
    cl = Vector(CL(view)); D = (Vector(view[1]) - cl).length * Dk
    s_ = 0.9 * fit(body, D, size if size else 1e9)
    return label(name, body, view, D, v, s_, m_, (S[i] + 3) if f_in is None else f_in,
                 E(i) if f_out is None else f_out, u)
LB(0, "L0", "SNAP!", lab_m, f_in=10)
LB(1, "L1", "ONLY 5 cm", white_lab)
LB(2, "L2", "GIANT CLAW", lab_m)
LB(3, "L3", "FASTER THAN A BLINK", white_lab)
LB(4, "L4", "~100 km/h JET", blue_lab)
LB(5, "L5", "BUBBLE!", blue_lab)
LB(6, "L6", "BANG!", red_lab, f_in=BC)
LB(7, "L7", "210 dB", lab_m)
LB(8, "L8", "SONAR: ???", blue_lab)
LB(9, "L9", "4,700 °C", red_lab)
LB(10, "L10", "LIKE THE SUN!", lab_m)
LB(11, "L11", "STUNNED!", lab_m, f_in=FHIT + 2)
LB(12, "L12", "NORMAL SNAP", white_lab)
LB(13, "L13", "SHRIMP POWER", lab_m)
LB(14, "L14", "BOOM!", red_lab, f_in=GC)
LB(15, "L15", "WHOOSH!", lab_m)
LB(16, "L16", "WHAT WOULD YOU SNAP?", lab_m, end=True, f_in=S[16] + 6, Dk=0.45)

# ---------------- camera ----------------
bpy.ops.object.camera_add()
cam = bpy.context.object
sc.camera = cam
cam.data.lens = 26
cam.data.sensor_fit = 'VERTICAL'
cam.data.sensor_height = 36
cam.data.clip_start = 0.02
cam.data.clip_end = 200000
target = bpy.data.objects.new("Target", None); sc.collection.objects.link(target)
tr = cam.constraints.new('TRACK_TO'); tr.target = target
tr.track_axis = 'TRACK_NEGATIVE_Z'; tr.up_axis = 'UP_Y'
for i in range(len(S)):
    for f, view in ((S[i], V[i]), (E(i) - 1, V2[i])):
        cl = CL(view)
        cam.location = cl; cam.keyframe_insert("location", frame=f)
        target.location = aim(cl, view[1]); target.keyframe_insert("location", frame=f)
CUTS = tuple(S[1:])
for o_ in (cam, target):
    for fc in fcurves(o_):
        pts_ = fc.keyframe_points
        for i in range(len(pts_) - 1):
            if int(round(pts_[i + 1].co[0])) in CUTS:
                pts_[i].interpolation = 'CONSTANT'
for o in bpy.data.objects:
    if o.type == 'FONT':
        o.visible_shadow = False
sc.frame_set(0)
bpy.ops.wm.save_as_mainfile(filepath=f"{HERE}/scene.blend")
print("SCENE OK", FRAMES, S)
