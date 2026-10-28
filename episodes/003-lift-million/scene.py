# Day 3 — What if you tried to lift a million dollars?
# Build: python3 episodes/003-lift-million/scene.py   (writes scene.blend next to this file)
# Helpers (mat/box/cyl/sphere/tube/group/attach/pop) adapted from episodes/001 + 002.
# Units: 1 Blender unit = 1 metre, real sizes where it matters (bill 15.6 x 6.6 cm, $1M in $1s ~1.1 m3).
import bpy, math, random, os, json
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
random.seed(3)
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
sc.view_settings.exposure = -0.45

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
sun = bpy.context.object; sun.data.energy = 3.0; sun.data.color = (1.0, 0.96, 0.88); sun.data.angle = math.radians(5)

# fluffy clouds
cloud_m = mat("Cloud", (1, 1, 1), 0.9, emit=(1, 1, 1), emit_strength=0.4)
for (x, y, z, s) in [(-60, 160, 70, 1.4), (40, 180, 90, 1.8), (-10, 220, 130, 2.0), (90, 150, 55, 1.2), (-120, 200, 110, 1.6)]:
    for k in range(4):
        sphere("Cloud", (x + (k - 1.5) * 7 * s, y, z + random.uniform(-2, 2) * s), random.uniform(5, 8) * s, cloud_m,
               scale=(1.3, 0.8, 0.8), sub=2)

# ---------------- ground diorama with cut-away front ----------------
FRONT_Y = -6.0
grass_m = bpy.data.materials.new("Grass"); grass_m.use_nodes = True
gn = grass_m.node_tree; N = gn.nodes; L = gn.links
bs = N["Principled BSDF"]; bs.inputs["Roughness"].default_value = 0.95
geo = N.new("ShaderNodeNewGeometry")
sxyz = N.new("ShaderNodeSeparateXYZ"); L.new(geo.outputs["Position"], sxyz.inputs[0])
mul = N.new("ShaderNodeMath"); mul.operation = 'MULTIPLY'; mul.inputs[1].default_value = 1.0
L.new(sxyz.outputs["X"], mul.inputs[0])
sn = N.new("ShaderNodeMath"); sn.operation = 'SINE'; L.new(mul.outputs[0], sn.inputs[0])
gt = N.new("ShaderNodeMath"); gt.operation = 'GREATER_THAN'; gt.inputs[1].default_value = 0.0
L.new(sn.outputs[0], gt.inputs[0])
gmix = N.new("ShaderNodeMix"); gmix.data_type = 'RGBA'
gmix.inputs[6].default_value = (0.28, 0.62, 0.18, 1); gmix.inputs[7].default_value = (0.36, 0.72, 0.22, 1)
L.new(gt.outputs[0], gmix.inputs["Factor"])
cr = N.new("ShaderNodeValToRGB"); cr.color_ramp.interpolation = 'CONSTANT'
ce = cr.color_ramp.elements
ce[0].position = 0.0; ce[0].color = (0.45, 0.27, 0.14, 1)
ce[1].position = 0.55; ce[1].color = (0.6, 0.38, 0.2, 1)
c3 = ce.new(0.85); c3.color = (0.38, 0.22, 0.11, 1)
mr = N.new("ShaderNodeMapRange"); mr.inputs["From Min"].default_value = -4.0; mr.inputs["From Max"].default_value = 0.0
L.new(sxyz.outputs["Z"], mr.inputs["Value"]); L.new(mr.outputs["Result"], cr.inputs["Fac"])
cap = N.new("ShaderNodeMapRange"); cap.inputs["From Min"].default_value = -0.25; cap.inputs["From Max"].default_value = -0.12
L.new(sxyz.outputs["Z"], cap.inputs["Value"])
fin = N.new("ShaderNodeMix"); fin.data_type = 'RGBA'
L.new(cap.outputs["Result"], fin.inputs["Factor"])
L.new(cr.outputs["Color"], fin.inputs[6]); L.new(gmix.outputs[2], fin.inputs[7])
L.new(fin.outputs[2], bs.inputs["Base Color"])
box("Ground", (0, 24.0, -2.0), (64, 60, 4.0), grass_m)
under_m = mat("Underside", (0.3, 0.2, 0.12), 0.9)
bpy.ops.mesh.primitive_plane_add(size=1200, location=(0, 0, -4.05))
bpy.context.object.data.materials.append(under_m)
far = mat("LawnFar", (0.3, 0.6, 0.2), 0.95)
bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 0, -0.03))
fp = bpy.context.object; fp.scale = (4000, 400000, 1); fp.location = (0, 200050, -0.03)
fp.data.materials.append(far)
stone_m = mat("Stone", (0.7, 0.66, 0.6), 0.8)
for i in range(30):
    sphere("Peb", (random.uniform(-30, 30), FRONT_Y - 0.02, random.uniform(-3.6, -0.6)), random.uniform(0.12, 0.3),
           stone_m, scale=(1.3, 0.5, 0.8), sub=1, smooth=False)

# ---------------- house + trees ----------------
wall_m = mat("Wall", (0.98, 0.88, 0.7), 0.85)
roof_m = mat("Roof", (0.88, 0.32, 0.24), 0.75)
trim_m = mat("Trim", (0.97, 0.97, 0.95), 0.6)
win_m = mat("Window", (0.55, 0.8, 0.95), 0.2)
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
for (x, y) in [(-9, 5), (-8, 22), (8.8, 24), (-12, 30), (26, 30), (-1, 26), (12, 34)]:
    tree(x, y, random.uniform(3.0, 4.2), random.uniform(1.3, 1.8))
for x in (-2.2, 6.4):
    sphere("Bush", (x, 13.4, 0.5), 0.8, fol[1], scale=(1.3, 0.9, 0.8), sub=1, smooth=False)

# ---------------- money materials ----------------
bill_m = mat("Bill", (0.3, 0.68, 0.25), 0.8)
bill_ink = mat("BillInk", (0.12, 0.38, 0.16), 0.7)
band100 = mat("Band100", (0.95, 0.75, 0.3), 0.6)
band1 = mat("Band1", (0.35, 0.55, 0.95), 0.6)
cash_stack_m = stripe_mat("CashStack", (0.25, 0.62, 0.2), (0.15, 0.35, 0.9), axis="Z", freq=6.0, thresh=0.8)
cash_cube_m = stripe_mat("CashCube", (0.3, 0.68, 0.25), (0.18, 0.48, 0.15), axis="Z", freq=55.0, thresh=0.3)
copper_m = mat("Copper", (0.85, 0.45, 0.22), 0.35, metal=0.85)
copper2_m = mat("Copper2", (0.95, 0.58, 0.3), 0.3, metal=0.85)

# ---------------- "you" (arms down) ----------------
def person(name, loc, body_c, skin=(0.95, 0.75, 0.6), hair=(0.25, 0.14, 0.06)):
    g = group(name, loc, 0)
    x, y, z = loc
    bm = mat(name + "B", body_c, 0.7)
    lm = mat(name + "L", (0.18, 0.22, 0.38), 0.8)
    sk = mat(name + "S", skin, 0.6)
    dark = mat(name + "E", (0.05, 0.04, 0.05), 0.4)
    parts = [
        cyl("LegL", (x - 0.13, y, 0.38), 0.1, 0.76, lm), cyl("LegR", (x + 0.13, y, 0.38), 0.1, 0.76, lm),
        cyl("Body", (x, y, 1.08), 0.28, 0.75, bm, r2=0.22),
        sphere("Head", (x, y, 1.68), 0.24, sk, sub=2),
        sphere("Hair", (x, y + 0.05, 1.82), 0.22, mat(name + "Hr", hair, 0.8), scale=(1.05, 1.05, 0.6), sub=2),
        sphere("EyeL", (x - 0.08, y - 0.21, 1.72), 0.035, dark, sub=1), sphere("EyeR", (x + 0.08, y - 0.21, 1.72), 0.035, dark, sub=1),
        tube("Smile", [(x - 0.07, y - 0.215, 1.6), (x, y - 0.235, 1.575), (x + 0.07, y - 0.215, 1.6)], [0.012] * 3, dark),
        tube("ArmL", [(x - 0.3, y, 1.35), (x - 0.4, y - 0.02, 1.08), (x - 0.4, y - 0.05, 0.85)], [0.07, 0.065, 0.06], bm),
        tube("ArmR", [(x + 0.3, y, 1.35), (x + 0.4, y - 0.02, 1.08), (x + 0.4, y - 0.05, 0.85)], [0.07, 0.065, 0.06], bm),
        sphere("HandL", (x - 0.4, y - 0.05, 0.82), 0.06, sk, sub=1), sphere("HandR", (x + 0.4, y - 0.05, 0.82), 0.06, sk, sub=1),
    ]
    attach(parts, g)
    return g

you = person("You", (0, 0, 0), (0.95, 0.3, 0.35))

# ---------------- line 0: "$1,000,000" title + raining bills ----------------
title_m = mat("TitleM", (0.35, 0.85, 0.3), 0.4, emit=(0.3, 0.8, 0.25), emit_strength=0.6)
title = text("Title", "$1,000,000", (0, -0.2, 2.75), 0.42, title_m, extrude=0.05)
title_bg = text("TitleBack", "$1,000,000", (0.02, -0.12, 2.73), 0.42, mat("TitleDark", (0.08, 0.25, 0.08), 0.6), extrude=0.05)
for o in (title, title_bg):
    pop(o, 2, 8, S[1] + 2)
fly = []
for i in range(46):
    p = (random.uniform(-2.6, 2.6), random.uniform(-2.5, 1.5), random.uniform(2.5, 5.5))
    b = box("FlyBill", p, (0.31, 0.13, 0.004), bill_m)
    fly.append(b)
    zend = p[2] - random.uniform(2.6, 4.0)
    b.rotation_euler = (random.uniform(-1, 1), random.uniform(-1, 1), random.uniform(0, 6))
    b.keyframe_insert("rotation_euler", frame=0)
    b.rotation_euler = (b.rotation_euler[0] + random.uniform(-3, 3), b.rotation_euler[1] + random.uniform(-3, 3), b.rotation_euler[2] + 3)
    b.keyframe_insert("rotation_euler", frame=S[1] + 4)
    key_loc(b, [(0, p), (S[1] + 4, (p[0] + random.uniform(-0.5, 0.5), p[1], max(zend, 0.05)))])
    gone_at(b, S[1] + 4, 3)

# ---------------- table + two kitchen scales (lines 1-4) ----------------
T = 0.85
wood = mat("Wood", (0.75, 0.5, 0.28), 0.7)
TX, TY = -1.5, -0.6
box("TableTop", (TX, TY, T - 0.03), (1.3, 0.75, 0.06), wood, bevel=0.01)
for dx in (-0.58, 0.58):
    for dy in (-0.3, 0.3):
        box("TableLeg", (TX + dx, TY + dy, (T - 0.06) / 2), (0.06, 0.06, T - 0.06), wood)
scale_m = mat("ScaleBody", (0.97, 0.97, 0.98), 0.4)
plat_m = mat("ScalePlat", (0.75, 0.78, 0.82), 0.25, metal=0.6)
lcd_m = mat("LCD", (0.6, 0.9, 0.62), 0.4, emit=(0.5, 0.9, 0.55), emit_strength=0.8)
lcd_ink = mat("LCDInk", (0.02, 0.06, 0.03), 0.5)
PT = T + 0.0925   # top of the scale platform
SA, SB = (TX - 0.28, TY + 0.02), (TX + 0.32, TY + 0.02)
def kitchen_scale(cx, cy):
    box("ScaleBase", (cx, cy, T + 0.035), (0.42, 0.42, 0.07), scale_m, bevel=0.012)
    box("ScalePlat", (cx, cy, T + 0.085), (0.38, 0.38, 0.015), plat_m, bevel=0.004)
    box("LCD", (cx, cy - 0.215, T + 0.035), (0.24, 0.02, 0.07), lcd_m)
def readout(body, cx, cy, f_in, f_out=None):
    o = text("Readout", body, (cx, cy - 0.226, T + 0.035), 0.05, lcd_ink)
    hide_until(o, f_in)
    if f_out is not None:
        gone_at(o, f_out, 1)
    return o
kitchen_scale(*SA); kitchen_scale(*SB)
readout("0 g", *SA, 0, S[1] + 14)
readout("1 g", *SA, S[1] + 14, S[2] + 6)
readout("10 kg", *SA, S[2] + 30)
readout("0 g", *SB, 0, S[3] + 12)
readout("10 kg", *SB, S[3] + 12)

# one $100 bill (generic cartoon money: just "100", no portrait / no real design)
bill = group("Bill100", (SA[0], SA[1], PT + 0.0015))
bparts = [box("Bill", (SA[0], SA[1], PT + 0.0015), (0.156, 0.066, 0.003), bill_m),
          box("BillOval", (SA[0], SA[1], PT + 0.0032), (0.05, 0.04, 0.0005), mat("BillOvalM", (0.75, 0.9, 0.65), 0.8))]
for sx in (-1, 1):
    bparts.append(text("BillNum", "100", (SA[0] + sx * 0.05, SA[1], PT + 0.0035), 0.022, bill_ink, rot=(0, 0, 0)))
attach(bparts, bill)
key_loc(bill, [(0, (SA[0], SA[1], PT + 0.5)), (S[1] - 1, (SA[0], SA[1], PT + 0.5)), (S[1] + 12, (SA[0], SA[1], PT + 0.0015))])
bill.rotation_euler = (0.4, 0.3, 1.2); bill.keyframe_insert("rotation_euler", frame=S[1])
bill.rotation_euler = (0, 0, 0.15); bill.keyframe_insert("rotation_euler", frame=S[1] + 12)
hide_until(bill, S[1]); gone_at(bill, S[2] + 4, 2)

# 100 bundles x 100 bills = 10,000 bills: 2 (x) x 5 (y) x 10 layers
bundles = []
for k in range(10):
    for i in range(2):
        for j in range(5):
            cx, cy, cz = SA[0] + (i - 0.5) * 0.157, SA[1] + (j - 2) * 0.067, PT + 0.0055 + 0.011 * k
            b = box("Bundle", (cx, cy, cz), (0.155, 0.065, 0.0105), bill_m)
            bd = box("Band", (cx, cy, cz), (0.032, 0.0665, 0.011), band100)
            for o in (b, bd):
                f = S[2] + 2 + 2 * k + (i + j) // 3
                o.scale = (0.001,) * 3; o.keyframe_insert("scale", frame=0); o.keyframe_insert("scale", frame=f - 1)
                o.scale = (1.0,) * 3; o.keyframe_insert("scale", frame=f + 2)
                o.keyframe_insert("scale", frame=S[4] + 4)
                o.scale = (0.001,) * 3; o.keyframe_insert("scale", frame=S[4] + 8)
            bundles.append(b)

# watermelon on scale B
melon_m = stripe_mat("Melon", (0.15, 0.45, 0.12), (0.35, 0.68, 0.25), axis="X", freq=40.0, thresh=0.2, rough=0.4)
melon = sphere("Melon", (SB[0], SB[1], PT + 0.14), 0.15, melon_m, scale=(1.0, 1.25, 0.95), sub=3)
key_loc(melon, [(0, (SB[0], SB[1], PT + 1.2)), (S[3] - 1, (SB[0], SB[1], PT + 1.2)), (S[3] + 10, (SB[0], SB[1], PT + 0.14))])
hide_until(melon, S[3])

# briefcase (table version swaps in around the cash, then a copy appears in your hand)
leather = mat("Leather", (0.42, 0.24, 0.12), 0.55)
gold = mat("Latch", (1.0, 0.8, 0.25), 0.3, metal=0.9)
def briefcase(name, cx, cy, cz, rz=0.0):
    g = group(name, (cx, cy, cz), rz)
    parts = [box("Case", (cx, cy, cz), (0.46, 0.13, 0.34), leather, bevel=0.015),
             box("Seam", (cx, cy, cz + 0.12), (0.47, 0.135, 0.012), mat(name + "Sm", (0.3, 0.16, 0.08), 0.6)),
             tube("Handle", [(cx - 0.07, cy, cz + 0.17), (cx - 0.06, cy, cz + 0.22), (cx + 0.06, cy, cz + 0.22), (cx + 0.07, cy, cz + 0.17)],
                  [0.012] * 4, mat(name + "H", (0.2, 0.1, 0.05), 0.5))]
    for sx in (-1, 1):
        parts.append(box("Latch", (cx + sx * 0.14, cy - 0.068, cz + 0.12), (0.04, 0.01, 0.03), gold))
    attach(parts, g)
    return g
case_t = briefcase("CaseTable", SA[0], SA[1], PT + 0.17)
pop(case_t, S[4] + 4, 6, S[5] + 3)
case_h = briefcase("CaseHand", 0.4, -0.05, 0.6, math.radians(90))
attach([case_h], you)
hide_until(case_h, S[5] + 3)
# "Easy!" hop
for f, z in [(S[5] + 2, 0), (S[5] + 7, 0.35), (S[5] + 12, 0), (S[5] + 15, 0.12), (S[5] + 18, 0)]:
    you.location = (0, 0, z); you.keyframe_insert("location", frame=f)

# ---------------- seesaw: $1M in $1 bills vs a small car (lines 5-7) ----------------
PX, PZ = 4.2, 0.76
steel = mat("Steel", (0.95, 0.75, 0.2), 0.5)
pivot = cyl("Pivot", (PX, 0, 0.15), 0.55, 0.7, mat("PivotM", (0.3, 0.32, 0.38), 0.6), verts=3)
pivot.rotation_mode = 'ZXY'; pivot.rotation_euler = (math.radians(90), 0, math.radians(90))
plank = group("Plank", (PX, 0, PZ))
pl = box("PlankBoard", (PX, 0, PZ), (7.5, 0.9, 0.12), steel, bevel=0.02)
cube = group("CashCube", (PX - 3.0, 0, PZ + 0.06))
cparts = [box("Cube", (PX - 3.0, 0, PZ + 0.06 + 0.52), (1.04, 1.04, 1.04), cash_cube_m, bevel=0.01)]
for dx in (-0.35, 0, 0.35):
    cparts.append(box("CubeBand", (PX - 3.0 + dx, 0, PZ + 0.06 + 0.52), (0.08, 1.06, 1.045), band1))
attach(cparts, cube)
attach([pl, cube], plank)
for o in (pivot, plank):
    pop(o, S[5] + 14, 7, S[10] + 6)
# cube drops in (local z) then the plank slams down on the cash side
cube.location = (PX - 3.0, 0, PZ + 6.0); cube.keyframe_insert("location", frame=S[6] - 1)
cube.location = (PX - 3.0, 0, PZ + 0.06); cube.keyframe_insert("location", frame=S[6] + 6)
hide_until(cube, S[6])
TILT = math.radians(-10.6)
plank.rotation_euler = (0, 0, 0); plank.keyframe_insert("rotation_euler", frame=S[6] + 6)
plank.rotation_euler = (0, TILT, 0); plank.keyframe_insert("rotation_euler", frame=S[6] + 11)
plank.keyframe_insert("rotation_euler", frame=S[7] + 6)
plank.rotation_euler = (0, math.radians(2.5), 0); plank.keyframe_insert("rotation_euler", frame=S[7] + 11)
plank.rotation_euler = (0, math.radians(-1.0), 0); plank.keyframe_insert("rotation_euler", frame=S[7] + 15)
plank.rotation_euler = (0, 0, 0); plank.keyframe_insert("rotation_euler", frame=S[7] + 19)
# you strain against the ton of cash
for f, a in [(S[6] + 6, 0), (S[6] + 10, 14), (S[6] + 16, 10), (S[6] + 22, 15), (S[7] + 4, 0)]:
    you.rotation_euler = (0, math.radians(a), 0); you.keyframe_insert("rotation_euler", frame=f)

carbody = mat("CarBody", (0.2, 0.55, 0.95), 0.35)
glass = mat("CarGlass", (0.25, 0.35, 0.45), 0.1)
tyre_m = mat("Tyre", (0.06, 0.06, 0.06), 0.9)
head_m = glow_mat("HeadL", (1.0, 0.95, 0.7), 3.0)
CX = PX + 2.1
car = group("Car", (CX, 0, 0))
cp = [box("CarBody", (CX, 0, 0.62), (3.2, 1.55, 0.6), carbody, bevel=0.12),
      box("CarCab", (CX + 0.15, 0, 1.15), (1.8, 1.4, 0.6), carbody, bevel=0.12),
      box("CarWin", (CX + 0.15, 0, 1.15), (1.6, 1.44, 0.42), glass),
      box("CarWinF", (CX - 0.62, 0, 1.15), (0.3, 1.3, 0.44), glass, rot=(0, math.radians(-30), 0))]
for dx in (-1.05, 1.05):
    for dy in (-0.72, 0.72):
        cp.append(cyl("Wheel", (CX + dx, dy, 0.32), 0.32, 0.25, tyre_m, rot=(math.radians(90), 0, 0), verts=16))
for dy in (-0.5, 0.5):
    cp.append(sphere("Headlight", (CX - 1.6, dy, 0.7), 0.1, head_m, sub=1))
attach(cp, car)
up_z = PZ + 0.06 + 2.1 * math.sin(-TILT)
key_loc(car, [(S[7] - 1, (CX, 0, 9.0)), (S[7] + 6, (CX, 0, up_z)), (S[7] + 11, (CX, 0, PZ + 0.06 - 2.1 * math.sin(math.radians(2.5)))),
              (S[7] + 15, (CX, 0, PZ + 0.06 + 2.1 * math.sin(math.radians(1.0)))), (S[7] + 19, (CX, 0, PZ + 0.06))])
car.rotation_euler = (0, 0.4, 0); car.keyframe_insert("rotation_euler", frame=S[7])
car.rotation_euler = (0, TILT, 0); car.keyframe_insert("rotation_euler", frame=S[7] + 6)
car.rotation_euler = (0, math.radians(2.5), 0); car.keyframe_insert("rotation_euler", frame=S[7] + 11)
car.rotation_euler = (0, math.radians(-1.0), 0); car.keyframe_insert("rotation_euler", frame=S[7] + 15)
car.rotation_euler = (0, 0, 0); car.keyframe_insert("rotation_euler", frame=S[7] + 19)
hide_until(car, S[7]); gone_at(car, S[10] + 6, 4)

# ---------------- 110 m tower of $1 bills + statue (lines 8-10) ----------------
TWX, TWY = -4.0, 3.0
TW_H = 110.0
tower = group("Tower", (TWX, TWY, 0))
tw = box("TowerBox", (TWX, TWY, TW_H / 2), (2.6, 1.6, TW_H), cash_stack_m)
attach([tw], tower)
tower.scale = (1, 1, 0.001); tower.keyframe_insert("scale", frame=0); tower.keyframe_insert("scale", frame=S[8])
tower.scale = (1, 1, 0.15); tower.keyframe_insert("scale", frame=S[8] + 10)
tower.scale = (1, 1, 1.0); tower.keyframe_insert("scale", frame=S[8] + 34)
# tips over toward +y at line 10, lands flat ("laid end to end")
tower.rotation_euler = (0, 0, 0); tower.keyframe_insert("rotation_euler", frame=S[10] + 1)
tower.rotation_euler = (math.radians(-20), 0, 0); tower.keyframe_insert("rotation_euler", frame=S[10] + 8)
tower.rotation_euler = (math.radians(-90), 0, 0); tower.keyframe_insert("rotation_euler", frame=S[10] + 16)
key_loc(tower, [(S[10] + 1, (TWX, TWY, 0)), (S[10] + 16, (TWX, TWY, 0.8))])
# ribbon of bills to the horizon (156 km)
rib = group("Ribbon", (TWX, TWY + TW_H, 0))
rb = box("RibbonBox", (TWX, TWY + TW_H + 78000, 0.05), (2.6, 156000, 0.1), cash_stack_m)
attach([rb], rib)
rib.scale = (1, 0.0001, 1); rib.keyframe_insert("scale", frame=0); rib.keyframe_insert("scale", frame=S[10] + 15)
rib.scale = (1, 0.004, 1); rib.keyframe_insert("scale", frame=S[10] + 26)
rib.scale = (1, 1, 1); rib.keyframe_insert("scale", frame=S[11] - 2)
hide_until(rib, S[10] + 15)

# generic green robed statue with a torch (public-domain landmark, simple low-poly)
patina = mat("Patina", (0.38, 0.7, 0.58), 0.6)
stone2 = mat("Pedestal", (0.82, 0.78, 0.68), 0.8)
flame_m = glow_mat("Flame", (1.0, 0.7, 0.15), 8.0)
STX, STY = -22.0, 14.0
statue = group("Statue", (STX, STY, 0))
stp = [box("Ped1", (STX, STY, 14), (16, 16, 28), stone2, bevel=0.4),
       box("Ped2", (STX, STY, 37.5), (11, 11, 19), stone2, bevel=0.3),
       cyl("Robe", (STX, STY, 47 + 15), 5.2, 30, patina, r2=2.6, verts=12),
       sphere("Shoulders", (STX, STY, 77.5), 3.2, patina, scale=(1.1, 0.8, 0.7), sub=1, smooth=False),
       sphere("HeadS", (STX, STY - 0.3, 81.5), 2.0, patina, sub=1, smooth=False),
       tube("Arm", [(STX + 2.6, STY, 77.5), (STX + 3.6, STY - 0.3, 83), (STX + 3.8, STY - 0.4, 88.5)], [1.0, 0.9, 0.8], patina),
       cyl("TorchCup", (STX + 3.8, STY - 0.4, 90), 1.4, 2.2, patina, r2=0.6, verts=10, rot=(math.radians(180), 0, 0)),
       sphere("TorchFlame", (STX + 3.8, STY - 0.4, 92.0), 1.2, flame_m, scale=(1, 1, 1.4), sub=1, smooth=False),
       box("Tablet", (STX - 3.0, STY - 1.2, 72), (1.6, 0.8, 4.0), patina, rot=(0, math.radians(-15), 0))]
for k in range(7):
    a = math.radians(-90 + (k - 3) * 28)
    stp.append(cyl("Spike", (STX + 2.0 * math.cos(a), STY - 0.3 + 0.6 * math.sin(a) * 0, 83.2 + 1.3 * math.sin(a + math.pi / 2) * 0 + 1.4),
                   0.35, 2.4, patina, r2=0.02, verts=6, rot=(0, math.radians((k - 3) * 22), 0)))
attach(stp, statue)
statue.scale = (0.001,) * 3; statue.keyframe_insert("scale", frame=0); statue.keyframe_insert("scale", frame=S[9])
statue.scale = (1, 1, 1.06); statue.keyframe_insert("scale", frame=S[9] + 10)
statue.scale = (1, 1, 1.0); statue.keyframe_insert("scale", frame=S[9] + 14)

# ---------------- pennies (lines 11-16) ----------------
PNX, PNY = 4.5, 4.5
def coin(name, loc, r, th, rot=(0, 0, 0)):
    o = cyl(name, loc, r, th, copper_m, rot=rot, verts=20)
    return o
penny = group("GiantPenny", (13, 0.8, 1.15))
gp = [cyl("PennyBody", (13, 0.8, 1.15), 1.15, 0.2, copper_m, rot=(math.radians(90), 0, 0), verts=40),
      cyl("PennyFace", (13, 0.8 - 0.06, 1.15), 0.92, 0.1, copper2_m, rot=(math.radians(90), 0, 0), verts=40),
      text("PennyText", "1¢", (13, 0.8 - 0.115, 1.15), 0.9, mat("PennyInk", (0.55, 0.25, 0.1), 0.4, metal=0.6), extrude=0.01)]
attach(gp, penny)
key_loc(penny, [(S[11] - 1, (13, 0.8, 1.15)), (S[11] + 14, (5.0, 0.8, 1.15)), (S[12] + 2, (4.6, 0.8, 1.15))])
penny.rotation_euler = (0, math.radians(-540), 0); penny.keyframe_insert("rotation_euler", frame=S[11] - 1)
penny.rotation_euler = (0, 0, 0); penny.keyframe_insert("rotation_euler", frame=S[11] + 14)
hide_until(penny, S[11]); gone_at(penny, S[12] + 5, 4)

pile = group("Pile", (PNX, PNY, 0))
PR, PH = 4.6, 2.6
pile_m = stripe_mat("PileM", (0.85, 0.45, 0.22), (0.98, 0.62, 0.32), axis="X", freq=9.0, thresh=0.6, rough=0.35, metal=0.8)
pparts = [cyl("PileCone", (PNX, PNY, PH / 2), PR, PH, pile_m, r2=0.25, verts=40)]
for i in range(170):
    rho = PR * math.sqrt(random.uniform(0.0, 0.95))
    a = random.uniform(0, 2 * math.pi)
    z = PH * (1 - rho / PR) + 0.02
    pparts.append(coin("PileCoin", (PNX + rho * math.cos(a), PNY + rho * math.sin(a), z), 0.17, 0.04,
                       rot=(random.uniform(-0.6, 0.6), random.uniform(-0.6, 0.6), 0)))
attach(pparts, pile)
pile.scale = (0.001,) * 3; pile.keyframe_insert("scale", frame=0); pile.keyframe_insert("scale", frame=S[12])
pile.scale = (0.35,) * 3; pile.keyframe_insert("scale", frame=S[12] + 8)
pile.scale = (0.75,) * 3; pile.keyframe_insert("scale", frame=S[13])
pile.scale = (1.0,) * 3; pile.keyframe_insert("scale", frame=S[13] + 14)
# coin rain
for i in range(90):
    rho = PR * math.sqrt(random.uniform(0, 0.8)); a = random.uniform(0, 2 * math.pi)
    x, y = PNX + rho * math.cos(a), PNY + rho * math.sin(a)
    zl = PH * (1 - rho / PR) * 0.9
    f0 = S[12] + random.randint(0, S[14] - S[12] - 8)
    c = coin("RainCoin", (x, y, 14), 0.17, 0.04)
    key_loc(c, [(f0, (x + random.uniform(-1, 1), y, random.uniform(10, 16))), (f0 + 9, (x, y, zl + 0.1))])
    c.rotation_euler = (random.uniform(0, 6), random.uniform(0, 6), 0); c.keyframe_insert("rotation_euler", frame=f0)
    c.rotation_euler = (c.rotation_euler[0] + 8, c.rotation_euler[1] + 5, 0); c.keyframe_insert("rotation_euler", frame=f0 + 9)
    hide_until(c, f0); gone_at(c, f0 + 14, 3)

# two cartoon blue whales (~25 m each)
whale_m = mat("Whale", (0.25, 0.45, 0.85), 0.5)
belly_m = mat("Belly", (0.8, 0.88, 0.95), 0.6)
eye_w = mat("EyeW", (1, 1, 1), 0.4); eye_k = mat("EyeK", (0.03, 0.03, 0.05), 0.3)
whales = []
for k, wx in enumerate((14.0, 20.0)):
    WY = 10.0
    g = group(f"Whale{k}", (wx, WY, 0))
    wp = [sphere("WBody", (wx, WY, 2.1), 1.0, whale_m, scale=(2.4, 11.0, 2.1), sub=3),
          sphere("WBelly", (wx, WY - 1.5, 1.5), 1.0, belly_m, scale=(2.0, 8.5, 1.4), sub=3),
          tube("WTail", [(wx, WY + 9.5, 2.1), (wx, WY + 13.0, 2.4)], [1.0, 0.45], whale_m),
          box("WFluke", (wx, WY + 13.6, 2.4), (5.2, 1.4, 0.3), whale_m, bevel=0.3),
          box("WFinL", (wx - 2.6, WY - 3.5, 1.2), (2.4, 1.0, 0.25), whale_m, bevel=0.2, rot=(0, math.radians(-25), math.radians(20))),
          box("WFinR", (wx + 2.6, WY - 3.5, 1.2), (2.4, 1.0, 0.25), whale_m, bevel=0.2, rot=(0, math.radians(25), math.radians(-20)))]
    for sx in (-1, 1):
        wp.append(sphere("WEye", (wx + sx * 1.75, WY - 7.6, 2.0), 0.4, eye_w, sub=2))
        wp.append(sphere("WPupil", (wx + sx * 1.95, WY - 7.85, 2.0), 0.22, eye_k, sub=1))
    wp.append(tube("WMouth", [(wx - 1.6, WY - 9.2, 1.5), (wx, WY - 10.3, 1.35), (wx + 1.6, WY - 9.2, 1.5)], [0.08] * 3, eye_k))
    attach(wp, g)
    f0 = S[14] + 1 + 4 * k
    key_loc(g, [(f0 - 1, (wx, WY, 26)), (f0 + 7, (wx, WY, -0.2)), (f0 + 10, (wx, WY, 0.4)), (f0 + 13, (wx, WY, 0))])
    hide_until(g, f0); gone_at(g, S[15] + 3, 3)
    whales.append(g)

# a dozen dump trucks full of pennies
cab_m = mat("TruckCab", (1.0, 0.75, 0.1), 0.5)
bed_m = mat("TruckBed", (0.55, 0.58, 0.62), 0.5, metal=0.3)
for k in range(12):
    tx = 13.5 if k % 2 == 0 else 19.5
    ty = -1.0 + 4.6 * (k // 2)
    g = group(f"Truck{k}", (tx, ty, 0))
    tp = [box("Cab", (tx, ty - 1.5, 1.2), (2.2, 1.4, 1.6), cab_m, bevel=0.1),
          box("CabWin", (tx, ty - 2.21, 1.5), (1.8, 0.04, 0.6), glass),
          box("Chassis", (tx, ty, 0.55), (2.2, 4.4, 0.3), tyre_m),
          box("Bed", (tx, ty + 0.75, 1.3), (2.3, 2.9, 1.2), bed_m, bevel=0.06),
          sphere("Load", (tx, ty + 0.75, 1.85), 1.0, pile_m, scale=(1.1, 1.4, 0.55), sub=2, smooth=False)]
    for dx in (-1.1, 1.1):
        for dy in (-1.5, 0.3, 1.5):
            tp.append(cyl("TWheel", (tx + dx, ty + dy, 0.45), 0.45, 0.35, tyre_m, rot=(0, math.radians(90), 0), verts=16))
    attach(tp, g)
    f0 = S[15] + 2 + k
    key_loc(g, [(f0 - 1, (tx, ty - 10, 0)), (f0 + 6, (tx, ty, 0)), (FRAMES, (tx, ty + 6, 0))])
    hide_until(g, f0)

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

A = (SA[0], SA[1], PT + 0.04)
cam_keys = [
    (0,          (0.8, -7.2, 1.9),    (0, 0, 1.75)),            # hook: you + $1,000,000 + money rain
    (S[1] - 4,   (0.1, -4.9, 1.9),    (0, 0, 1.9)),
    (S[1] + 6,   (SA[0] + 0.35, SA[1] - 0.95, PT + 0.45), A),   # one bill on the scale
    (S[2] - 2,   (SA[0] - 0.25, SA[1] - 0.85, PT + 0.38), A),
    (S[2] + 8,   (SA[0] + 0.45, SA[1] - 1.0, PT + 0.5), (SA[0], SA[1], PT + 0.06)),   # 10,000 bills stack up
    (S[3] - 2,   (SA[0] - 0.4, SA[1] - 0.95, PT + 0.42), (SA[0], SA[1], PT + 0.06)),
    (S[3] + 8,   (TX + 0.05, TY - 1.35, PT + 0.5), (TX + 0.02, TY, PT + 0.1)),       # both scales: 10 kg = melon
    (S[4] - 2,   (TX - 0.2, TY - 1.25, PT + 0.42), (TX + 0.02, TY, PT + 0.1)),
    (S[4] + 7,   (SA[0] - 0.55, SA[1] - 1.0, PT + 0.45), (SA[0], SA[1], PT + 0.17)),  # briefcase
    (S[5] - 2,   (SA[0] + 0.2, SA[1] - 1.1, PT + 0.4), (SA[0], SA[1], PT + 0.17)),
    (S[5] + 6,   (1.4, -4.4, 1.6),    (0.6, 0, 1.0)),            # Easy! hop with the case
    (S[6] - 2,   (2.6, -8.0, 2.3),    (2.6, 0, 0.9)),
    (S[6] + 8,   (1.8, -6.2, 1.9),    (1.2, 0, 0.9)),            # a ton of singles slams the seesaw
    (S[7] - 2,   (3.0, -8.4, 2.4),    (3.3, 0, 0.9)),
    (S[7] + 8,   (4.6, -9.6, 2.9),    (4.2, 0, 1.2)),            # small car balances it
    (S[8] - 2,   (3.6, -9.2, 2.5),    (4.2, 0, 1.2)),
    (S[8] + 4,   (2.0, -11.0, 1.2),   (TWX, TWY, 3.0)),          # tower shoots up
    (S[8] + 20,  (4.0, -42.0, 16),    (TWX, TWY, 30)),
    (S[9] - 2,   (6.0, -92.0, 48),    (-7, 4, 55)),
    (S[9] + 12,  (-12.0, -96.0, 52),  (-11, 6, 52)),            # taller than the statue
    (S[10] - 2,  (-16.0, -98.0, 55),  (-11, 6, 52)),
    (S[10] + 10, (16.0, -48.0, 34),   (TWX, 45, 6)),             # it tips over
    (S[10] + 24, (-3.4, -16.0, 16.0), (TWX, 260, 0)),            # skim along the 156 km ribbon
    (S[11] - 2,  (-4.4, -12.0, 12.0), (TWX, 420, 0)),
    (S[11] + 5,  (6.5, -6.5, 1.6),    (9.0, 0.8, 1.1)),          # giant penny rolls in
    (S[12] - 2,  (4.0, -6.2, 1.5),    (5.0, 0.8, 1.15)),
    (S[12] + 8,  (0.0, -10.0, 5.0),   (PNX, PNY, 1.2)),          # 100 million coins rain down
    (S[13] - 2,  (2.0, -11.0, 4.6),   (PNX, PNY, 1.2)),
    (S[13] + 10, (12.0, -9.5, 4.6),   (PNX - 1, PNY - 1, 1.4)),  # 250 tons (you for scale)
    (S[14] - 2,  (12.5, -6.0, 4.2),   (PNX - 1, PNY - 1, 1.4)),
    (S[14] + 10, (-3.0, -28.0, 14),   (11, 8, 2.5)),             # two blue whales
    (S[15] - 2,  (0.0, -29.0, 12),    (11, 8, 2.5)),
    (S[15] + 10, (30.0, -20.0, 15),   (14, 9, 1.5)),             # a dozen trucks
    (S[16] - 2,  (26.0, -26.0, 13),   (14, 9, 1.5)),
    (S[16] + 12, (2.2, -5.6, 1.8),    (0.8, 0.5, 1.2)),          # you, the case, the pile
    (FRAMES - 1, (1.3, -3.8, 1.5),    (0.6, 0.3, 1.2)),
]
for f, cl, tl in cam_keys:
    cam.location = cl; cam.keyframe_insert("location", frame=f)
    target.location = tl; target.keyframe_insert("location", frame=f)

bpy.ops.wm.save_as_mainfile(filepath=f"{HERE}/scene.blend")
print("SCENE OK", FRAMES, S)
