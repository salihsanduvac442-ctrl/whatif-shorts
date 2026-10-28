# Day 3 — What if you tried to lift a million dollars? ($1M -> $10M -> $100M -> $1B, updated Oct 28)
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
fp = bpy.context.object; fp.scale = (400000, 400000, 1); fp.location = (0, 200050, -0.03)
fp.data.materials.append(far)
stone_m = mat("Stone", (0.7, 0.66, 0.6), 0.8)
for i in range(30):
    sphere("Peb", (random.uniform(-30, 30), FRONT_Y - 0.02, random.uniform(-3.6, -0.6)), random.uniform(0.12, 0.3),
           stone_m, scale=(1.3, 0.5, 0.8), sub=1, smooth=False)

for sx in (-1, 1):   # lawn beside the diorama (no void at the sides)
    bpy.ops.mesh.primitive_plane_add(size=1, location=(sx * 100016, 22, -0.03))
    o = bpy.context.object; o.scale = (199968, 56, 1); o.data.materials.append(far)

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

# ---------------- money scale-up (lines 5-17) ----------------
# Real numbers ($100 bills: 1 g, 15.6 x 6.6 cm, 0.11 mm, ~1.13 cm3 each):
#   $10M  = 100,000 bills = 100 kg, 0.113 m3 (cube ~0.48 m), stack 11 m
#   $100M = 1,000,000 bills = 1 t, 1.13 m3 (one pallet 1.2 x 1.0 x ~0.95 m)
#   $1B   = 10,000,000 bills = 10 t, 10 pallets, stack 1.1 km (Burj-class tallest building ~830 m)
band_green = stripe_mat("Stack100", (0.3, 0.68, 0.25), (0.95, 0.75, 0.3), axis="Z", freq=6.0, thresh=0.8)
band_big = stripe_mat("Stack1B", (0.3, 0.68, 0.25), (0.95, 0.75, 0.3), axis="Z", freq=0.06, thresh=0.8)

def lerp_plank(theta, off):
    """World position of a point `off` m from the pivot along the plank top, for plank angle theta (rad)."""
    return (PX + off * math.cos(theta), PZ + 0.06 - off * math.sin(theta))

# "Easy!" hop with the case, then a jump onto the seesaw's right end
for f, z in [(S[5] + 1, 0), (S[5] + 5, 0.35), (S[5] + 9, 0)]:
    you.location = (0, 0, z); you.keyframe_insert("location", frame=f)

# ---------------- seesaw ----------------
PX, PZ = 4.2, 0.76
steel = mat("Steel", (0.95, 0.75, 0.2), 0.5)
pivot = cyl("Pivot", (PX, 0, 0.15), 0.55, 0.7, mat("PivotM", (0.3, 0.32, 0.38), 0.6), verts=3)
pivot.rotation_mode = 'ZXY'; pivot.rotation_euler = (math.radians(90), 0, math.radians(90))
plank = group("Plank", (PX, 0, PZ))
pl = box("PlankBoard", (PX, 0, PZ), (7.5, 1.15, 0.12), steel, bevel=0.02)

# $10M cube (100 kg) on the left end
C10 = 0.48
cube = group("Cube10M", (PX - 3.0, 0, PZ + 0.06))
cparts = [box("Cube", (PX - 3.0, 0, PZ + 0.06 + C10 / 2), (C10, C10, C10), cash_cube_m, bevel=0.008)]
for dx in (-0.12, 0.12):
    cparts.append(box("CubeBand", (PX - 3.0 + dx, 0, PZ + 0.06 + C10 / 2), (0.05, C10 + 0.01, C10 + 0.005), band100))
attach(cparts, cube)

# $100M pallet (1 ton) on the left end
pallet_wood = mat("PalletWood", (0.78, 0.6, 0.38), 0.85)
def pallet(name, cx, cy, cz):
    g = group(name, (cx, cy, cz))
    pp = []
    for dy in (-0.42, 0, 0.42):
        pp.append(box("Runner", (cx, cy + dy, cz + 0.05), (1.2, 0.12, 0.1), pallet_wood))
    pp.append(box("Deck", (cx, cy, cz + 0.12), (1.2, 1.0, 0.04), pallet_wood))
    pp.append(box("Cash", (cx, cy, cz + 0.14 + 0.475), (1.16, 0.98, 0.95), cash_cube_m, bevel=0.01))
    for dx in (-0.4, 0, 0.4):
        pp.append(box("PBand", (cx + dx, cy, cz + 0.14 + 0.475), (0.06, 0.99, 0.955), band100))
    attach(pp, g)
    return g
pal = pallet("Pallet100M", PX - 2.8, 0, PZ + 0.06)
attach([pl, cube, pal], plank)
pop(pivot, S[5] + 8, 7)
pop(plank, S[5] + 8, 7)

T6 = math.radians(5.0)        # you alone: right end dips
TILT = math.radians(-10.6)    # cash side slams down
def plank_rot(keys):
    for f, a in keys:
        plank.rotation_euler = (0, a, 0); plank.keyframe_insert("rotation_euler", frame=f)
plank_rot([(S[5] + 16, 0), (S[5] + 20, T6), (S[6] + 3, T6), (S[6] + 8, TILT),
           (S[8] + 1, TILT), (S[8] + 6, 0), (S[8] + 11, 0), (S[8] + 15, TILT),
           (S[10] + 6, TILT), (S[10] + 11, math.radians(2.5)), (S[10] + 15, math.radians(-1.0)), (S[10] + 19, 0)])

# cube: drops in on line 5, gone on line 8
cube.location = (PX - 3.0, 0, PZ + 5.0); cube.keyframe_insert("location", frame=S[6] - 3)
cube.location = (PX - 3.0, 0, PZ + 0.06); cube.keyframe_insert("location", frame=S[6] + 3)
hide_until(cube, S[6] - 3); gone_at(cube, S[8] + 2, 3)
# pallet: drops on line 8
pal.location = (PX - 2.8, 0, PZ + 7.0); pal.keyframe_insert("location", frame=S[8] + 5)
pal.location = (PX - 2.8, 0, PZ + 0.06); pal.keyframe_insert("location", frame=S[8] + 11)
hide_until(pal, S[8] + 5)

# you: jump onto the right end, ride it, get launched, hop off on line 8
OFF = 2.6
def on_plank(theta, lift=0.0):
    x, z = lerp_plank(theta, OFF)
    return (x, 0, z + lift)
you_keys = [
    (S[5] + 9,  (0, 0, 0), 0),
    (S[5] + 13, (3.4, 0, 2.0), 0),
    (S[5] + 16, on_plank(0), 0),
    (S[5] + 20, on_plank(T6), T6),
    (S[6] + 3,  on_plank(T6), T6),
    (S[6] + 8,  on_plank(TILT, 0.9), TILT),      # boing!
    (S[6] + 12, on_plank(TILT, 0.15), TILT),
    (S[6] + 14, on_plank(TILT), TILT),
    (S[8] + 1,  on_plank(TILT), TILT),
    (S[8] + 5,  (8.2, -0.6, 2.0), 0),
    (S[8] + 9,  (8.8, -1.2, 0), 0),
]
for f, p, a in you_keys:
    you.location = p; you.keyframe_insert("location", frame=f)
    you.rotation_euler = (0, a, 0); you.keyframe_insert("rotation_euler", frame=f)
# wobble on top while the cube outweighs you
for f, a in [(S[6] + 14, 0), (S[6] + 18, 8), (S[6] + 22, -6), (S[7], 0)]:
    you.rotation_euler = (0, TILT + math.radians(a), 0); you.keyframe_insert("rotation_euler", frame=f)

# ---------------- line 7: $10M stacked = 11 m next to the house ----------------
SX, SY = 7.6, 14.5
st10 = group("Stack10M", (SX, SY, 0))
sb = box("Stack10MBox", (SX, SY, 5.5), (0.34, 0.2, 11.0), band_green)
attach([sb], st10)
st10.scale = (1, 1, 0.001); st10.keyframe_insert("scale", frame=0); st10.keyframe_insert("scale", frame=S[7])
st10.scale = (1, 1, 1.08); st10.keyframe_insert("scale", frame=S[7] + 18)
st10.scale = (1, 1, 1.0); st10.keyframe_insert("scale", frame=S[7] + 23)
gone_at(st10, S[11], 4)
lab_m = mat("LabelM", (1.0, 0.85, 0.2), 0.4, emit=(1.0, 0.8, 0.2), emit_strength=0.8)
lab11 = text("Lab11", "11 m", (SX + 1.6, SY - 0.2, 11.0), 1.5, lab_m, extrude=0.04)
pop(lab11, S[7] + 18, 6, S[8] + 2)

# ---------------- line 10: small car balances the pallet ----------------
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
key_loc(car, [(S[10] - 1, (CX, 0, 9.0)), (S[10] + 6, (CX, 0, up_z)), (S[10] + 11, (CX, 0, PZ + 0.06 - 2.1 * math.sin(math.radians(2.5)))),
              (S[10] + 15, (CX, 0, PZ + 0.06 + 2.1 * math.sin(math.radians(1.0)))), (S[10] + 19, (CX, 0, PZ + 0.06))])
car.rotation_euler = (0, 0.4, 0); car.keyframe_insert("rotation_euler", frame=S[10])
car.rotation_euler = (0, TILT, 0); car.keyframe_insert("rotation_euler", frame=S[10] + 6)
car.rotation_euler = (0, math.radians(2.5), 0); car.keyframe_insert("rotation_euler", frame=S[10] + 11)
car.rotation_euler = (0, math.radians(-1.0), 0); car.keyframe_insert("rotation_euler", frame=S[10] + 15)
car.rotation_euler = (0, 0, 0); car.keyframe_insert("rotation_euler", frame=S[10] + 19)
hide_until(car, S[10])

# ---------------- lines 11-12: $1B = ten pallets (10 tons) ----------------
BX, BY = 14.0, 6.0
for k in range(10):
    i, lvl = k % 5, k // 5
    px, pz = BX + (i - 2) * 1.3, lvl * 1.12
    g = pallet(f"PalletB{k}", px, BY, pz)
    f0 = S[11] + 3 + 2 * k
    key_loc(g, [(f0 - 1, (px, BY, pz + 9.0)), (f0 + 6, (px, BY, pz)), (f0 + 8, (px, BY, pz + 0.08)), (f0 + 10, (px, BY, pz))])
    hide_until(g, f0)

# ---------------- line 13: cartoon elephant (~6 t) ----------------
ele_m = mat("Elephant", (0.6, 0.62, 0.68), 0.75)
ear_m = mat("EarIn", (0.85, 0.62, 0.65), 0.7)
tusk_m = mat("Tusk", (0.98, 0.96, 0.9), 0.4)
EX, EY = 20.8, 6.6
ele = group("Elephant", (EX, EY, 0))
ep = [sphere("EBody", (EX, EY, 2.4), 1.0, ele_m, scale=(1.45, 2.1, 1.3), sub=3),
      sphere("EHead", (EX, EY - 2.0, 3.0), 0.95, ele_m, sub=3),
      tube("ETrunk", [(EX, EY - 2.75, 2.75), (EX, EY - 3.15, 1.9), (EX, EY - 3.05, 0.9), (EX, EY - 3.35, 0.55)],
           [0.33, 0.25, 0.18, 0.14], ele_m),
      tube("ETail", [(EX, EY + 2.05, 2.7), (EX + 0.1, EY + 2.4, 1.8)], [0.07, 0.05], ele_m)]
for sx in (-1, 1):
    ep.append(sphere("EEar", (EX + sx * 1.15, EY - 1.75, 3.05), 1.0, ele_m, scale=(0.95, 0.16, 1.05), sub=2))
    ep.append(sphere("EEarIn", (EX + sx * 1.12, EY - 1.86, 3.0), 1.0, ear_m, scale=(0.72, 0.06, 0.82), sub=2))
    ep.append(cyl("ETusk", (EX + sx * 0.4, EY - 2.85, 2.25), 0.09, 0.7, tusk_m, r2=0.02, verts=10,
                  rot=(math.radians(120), 0, 0)))
    ep.append(sphere("EEye", (EX + sx * 0.42, EY - 2.82, 3.3), 0.1, eye_k := mat("EyeK", (0.03, 0.03, 0.05), 0.3), sub=1))
    for dy in (-1.15, 1.15):
        ep.append(cyl("ELeg", (EX + sx * 0.75, EY + dy, 0.85), 0.4, 1.7, ele_m, verts=14))
attach(ep, ele)
f0 = S[13] + 2
key_loc(ele, [(f0 - 1, (EX, EY, 14)), (f0 + 7, (EX, EY, -0.15)), (f0 + 10, (EX, EY, 0.25)), (f0 + 13, (EX, EY, 0))])
hide_until(ele, f0)

# ---------------- lines 14-16: $1B stack (1.1 km) vs the tallest building (~830 m) ----------------
TBX, TBY = 0.0, 420.0
tb = group("Stack1B", (TBX, TBY, 0))
tbp = [box("Stack1BBox", (TBX, TBY, 550), (6.0, 4.0, 1100), band_big),
       box("Stack1BCap", (TBX, TBY, 1100.6), (6.6, 4.6, 1.2), mat("CapGold", (1.0, 0.8, 0.25), 0.3, metal=0.9))]
tbp.append(text("Lab1B", "$1B", (TBX, TBY - 2.5, 1112), 14, lab_m, extrude=0.6))
attach(tbp, tb)
tb.scale = (1, 1, 0.001); tb.keyframe_insert("scale", frame=0); tb.keyframe_insert("scale", frame=S[14])
tb.scale = (1, 1, 0.25); tb.keyframe_insert("scale", frame=S[14] + 8)
tb.scale = (1, 1, 1.0); tb.keyframe_insert("scale", frame=S[15] + 6)

# cloud layer the stack pokes through (~450-520 m)
for k in range(46):
    a = random.uniform(0, 2 * math.pi); r = random.uniform(18, 260)
    cx, cy = TBX + r * math.cos(a) + 60, TBY + r * math.sin(a) + 40
    sphere("HiCloud", (cx, cy, random.uniform(450, 520)), random.uniform(14, 30), cloud_m, scale=(1.5, 1.1, 0.55), sub=2)

# generic tallest building: stepped glass tower + spire (no specific real design)
glass_t = stripe_mat("TowerGlass", (0.62, 0.78, 0.9), (0.3, 0.42, 0.55), axis="Z", freq=1.6, thresh=0.6, rough=0.15, metal=0.4)
KX, KY = 150.0, 520.0
sky = group("Skyscraper", (KX, KY, 0))
segs = [(70, 60, 150), (56, 48, 150), (44, 38, 150), (32, 28, 130), (22, 20, 110), (13, 12, 70)]
kp, z = [], 0.0
for wx, wy, h in segs:
    kp.append(box("KSeg", (KX, KY, z + h / 2), (wx, wy, h), glass_t))
    z += h
kp.append(cyl("KSpire", (KX, KY, z + 34), 4.0, 68, mat("Spire", (0.85, 0.88, 0.92), 0.3, metal=0.8), r2=0.4, verts=10))
attach(kp, sky)
sky.scale = (1, 1, 0.001); sky.keyframe_insert("scale", frame=0); sky.keyframe_insert("scale", frame=S[16])
sky.scale = (1, 1, 1.0); sky.keyframe_insert("scale", frame=S[16] + 12)
lab_k = text("LabK", "830 m", (KX, KY - 10, 870), 22, mat("LabKM", (1, 1, 1), 0.4, emit=(1, 1, 1), emit_strength=0.8), extrude=0.8)
pop(lab_k, S[16] + 12, 6)
lab_b = text("LabB", "1,100 m", (TBX - 40, TBY - 10, 1150), 22, lab_m, extrude=0.8)
pop(lab_b, S[16] + 14, 6)

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
    (S[5] + 5,   (1.4, -4.4, 1.6),    (0.6, 0, 1.0)),            # Easy! hop with the case
    (S[5] + 16,  (3.6, -8.6, 2.3),    (4.0, 0, 1.0)),            # seesaw, you jump on
    (S[6] + 2,   (2.6, -7.0, 2.0),    (2.8, 0, 1.0)),            # $10M cube lands
    (S[6] + 12,  (4.6, -9.4, 2.7),    (4.3, 0, 1.3)),            # you get launched
    (S[7] - 2,   (5.2, -9.8, 2.9),    (4.6, 0, 1.4)),
    (S[7] + 4,   (11.0, 4.0, 1.4),    (SX, SY, 4.0)),            # 11 m stack by the house
    (S[7] + 20,  (12.0, 2.5, 3.0),    (SX - 1.0, SY, 5.6)),
    (S[8] - 2,   (11.0, 1.5, 3.4),    (SX - 1.5, SY, 5.4)),
    (S[8] + 8,   (2.4, -6.4, 2.8),    (1.6, 0, 1.3)),            # pallet drops on the left end
    (S[9] - 2,   (0.6, -4.2, 2.0),    (1.4, 0, 1.0)),
    (S[9] + 12,  (2.4, -3.8, 1.7),    (1.4, 0, 0.9)),            # one ton
    (S[10] - 2,  (4.0, -9.0, 2.7),    (4.2, 0, 1.2)),            # car balances it
    (S[10] + 14, (4.8, -9.6, 3.0),    (4.4, 0, 1.2)),
    (S[11] - 2,  (6.4, -10.2, 3.3),   (6.0, 0, 1.4)),
    (S[11] + 8,  (12.0, -9.0, 5.5),   (BX, BY, 1.4)),            # ten pallets rain down
    (S[12] - 2,  (16.5, -7.5, 4.2),   (BX, BY, 1.2)),
    (S[12] + 12, (8.5, -5.0, 3.2),    (BX + 1.0, BY, 1.3)),      # ten tons
    (S[13] - 2,  (11.0, -7.0, 3.4),   (BX + 3.0, BY, 1.6)),
    (S[13] + 12, (17.0, -6.2, 3.2),   (EX - 1.5, EY, 2.0)),      # elephant
    (S[14] - 2,  (19.2, -6.4, 3.0),   (EX - 1.5, EY, 2.0)),
    (S[14] + 3,  (9.0, 388.0, 2.5),   (TBX, TBY, 60)),           # base of the $1B stack, looking up
    (S[14] + 20, (34.0, 330.0, 240),  (TBX, TBY, 480)),
    (S[15] - 2,  (44.0, 300.0, 400),  (TBX, TBY, 640)),
    (S[15] + 12, (40.0, 300.0, 600),  (TBX, TBY, 500)),          # punching through the clouds
    (S[16] - 2,  (48.0, 292.0, 650),  (TBX, TBY, 560)),
    (S[16] + 14, (420.0, -120.0, 950), (70, 470, 760)),          # vs the tallest building
    (S[17] - 2,  (440.0, -150.0, 960), (70, 470, 760)),
    (S[17] + 12, (10.6, -6.4, 2.0),   (8.8, -1.2, 1.1)),         # back to you
    (FRAMES - 1, (9.8, -4.6, 1.7),    (8.6, -1.1, 1.1)),
]
for f, cl, tl in cam_keys:
    cam.location = cl; cam.keyframe_insert("location", frame=f)
    target.location = tl; target.keyframe_insert("location", frame=f)

bpy.ops.wm.save_as_mainfile(filepath=f"{HERE}/scene.blend")
print("SCENE OK", FRAMES, S)
