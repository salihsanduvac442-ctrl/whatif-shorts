# Day 19 — What if you swallowed your chewing gum?  Build: python3 episodes/019-swallow-gum/scene.py
# Reference style: base (helpers, lawn/soil, house, garden) copied from episodes/003-lift-million-ref/scene.py (via 015)
import bpy, math, random, os, json
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
random.seed(19)
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
box("Ground", (0, 26.2, -6.0), (400, 55.6, 12.0), grass_m)
under_m = mat("Underside", (0.3, 0.2, 0.12), 0.9)
bpy.ops.mesh.primitive_plane_add(size=1200, location=(0, 0, -12.05))
bpy.context.object.data.materials.append(under_m)
far = grass_m
bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 0, -0.03))
fp = bpy.context.object; fp.scale = (400000, 400000, 1); fp.location = (0, 200050, -0.03)
fp.data.materials.append(far)
stone_m = mat("Stone", (0.7, 0.66, 0.6), 0.8)
for i in range(30):
    sphere("Peb", (random.uniform(-30, 30), FRONT_Y - 0.02, random.uniform(-5.6, -0.6)), random.uniform(0.12, 0.3),
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
POX, POY = -8.0, 9.5
box("PoolRim", (POX, POY, 0.03), (6.4, 3.8, 0.1), mat("PoolRimM", (0.9, 0.88, 0.82), 0.7))
box("PoolWater", (POX, POY, 0.06), (5.8, 3.2, 0.06), mat("PoolWaterM", (0.25, 0.7, 0.85), 0.05, emit=(0.2, 0.6, 0.8), emit_strength=0.25))

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

# =====================================================================================
# Day 19 — What if you swallowed your chewing gum?
# Facts used (Mayo Clinic / NIH / Milov et al., Pediatrics 1998):
#   The "stays 7 years" story is a myth. Stomach acid (pH ~1.5-3.5) and enzymes can't break down the gum base
#   (polymers/resins/elastomers), but sweeteners, softeners and flavour are absorbed. The undigested base is pushed
#   along by peristalsis and usually leaves in the stool within a few days, like other indigestible material.
#   The gut is several metres long. Rare blockages (bezoars) were reported in children who swallowed large
#   amounts of gum habitually (sometimes with coins/seeds). An occasional swallowed piece is not a problem.
# =====================================================================================
gold_m = mat("Gold", (1.0, 0.78, 0.2), 0.3, metal=0.85)
mouth_m = mat("Mouth", (0.35, 0.05, 0.07), 0.5)
gum_m = mat("Gum", (1.0, 0.35, 0.68), 0.25, emit=(1.0, 0.3, 0.6), emit_strength=0.35)
gum_m2 = mat("Gum2", (1.0, 0.45, 0.75), 0.3, emit=(1.0, 0.35, 0.65), emit_strength=0.25)
bubble_gum = mat("BubbleGum", (1.0, 0.5, 0.78), 0.15, emit=(1.0, 0.4, 0.7), emit_strength=0.4)
acid_m = glow_mat("Acid", (0.45, 1.0, 0.2), 1.6)
acidb_m = glow_mat("AcidB", (0.6, 1.0, 0.25), 4.0)
sugar_m = mat("Sugar", (1, 1, 1), 0.3, emit=(1, 1, 1), emit_strength=1.2)
ped_m = mat("Pedestal", (0.96, 0.96, 0.98), 0.4)
cav_m = mat("Cavity", (0.5, 0.1, 0.13), 0.7)
stom_m = mat("Stomach", (0.95, 0.42, 0.48), 0.45)
stin_m = mat("StomachIn", (0.7, 0.18, 0.25), 0.6)
eso_m = mat("Eso", (0.95, 0.5, 0.55), 0.5)
si_m = mat("SmallInt", (1.0, 0.64, 0.62), 0.45)
li_m = mat("LargeInt", (0.88, 0.52, 0.38), 0.5)
redglow = glow_mat("RedGlow", (1.0, 0.08, 0.05), 3.0)
food_m = mat("Food", (0.95, 0.72, 0.35), 0.7)
crumb_m = mat("Crumb", (0.85, 0.6, 0.25), 0.7)
porc_m = mat("Porcelain", (0.97, 0.97, 1.0), 0.2)
water_m = mat("Water", (0.3, 0.7, 1.0), 0.05, emit=(0.2, 0.6, 1.0), emit_strength=0.6)
board_m = mat("Board", (0.98, 0.98, 0.96), 0.6)

def lin(o):
    for fc in fcurves(o):
        for p in fc.keyframe_points:
            p.interpolation = 'LINEAR'

def path_keys(o, pts, f0, f1):
    """Key o along a poly-line from frame f0 to f1, speed proportional to arc length."""
    pts = [Vector(p) for p in pts]
    L_ = [0.0]
    for a, b in zip(pts, pts[1:]):
        L_.append(L_[-1] + (b - a).length)
    tot = L_[-1] or 1.0
    for p, l in zip(pts, L_):
        o.location = tuple(p); o.keyframe_insert("location", frame=round(f0 + (f1 - f0) * l / tot))

def along(pts, t):
    pts = [Vector(p) for p in pts]
    L_ = [0.0]
    for a, b in zip(pts, pts[1:]):
        L_.append(L_[-1] + (b - a).length)
    d = t * L_[-1]
    for i in range(len(pts) - 1):
        if L_[i + 1] >= d:
            u = (d - L_[i]) / max(L_[i + 1] - L_[i], 1e-6)
            return pts[i].lerp(pts[i + 1], u), (pts[i + 1] - pts[i]).normalized()
    return pts[-1], (pts[-1] - pts[-2]).normalized()

# ---------------- the giant anatomy model (bust on a pedestal, organs on a cut-away front) ----------------
GX, GY = 2.0, 3.0
OY = GY - 0.75
box("Pedestal", (GX, GY, 0.6), (3.2, 1.7, 1.2), ped_m, bevel=0.05)
box("PedTrim", (GX, GY, 1.2), (3.4, 1.85, 0.1), gold_m, bevel=0.02)
box("Torso", (GX, GY, 3.3), (3.4, 1.2, 4.2), skin_m, bevel=0.35)
for sx in (-1, 1):
    sphere("Shoulder", (GX + sx * 1.6, GY, 4.95), 0.65, skin_m, scale=(1.0, 0.9, 0.8), sub=3)
box("Cavity", (GX, GY - 0.62, 3.25), (3.0, 0.04, 3.85), cav_m, bevel=0.01)
cyl("Neck", (GX, GY, 5.75), 0.5, 0.8, skin_m, verts=24)
HEADC = (GX, GY, 6.95)
sphere("GHead", HEADC, 1.05, skin_m, sub=3)
sphere("GHair", (GX, GY + 0.1, 7.35), 1.0, mat("GHairM", (0.25, 0.14, 0.07), 0.8), scale=(1.06, 1.0, 0.62), sub=3)
for sx in (-1, 1):
    sphere("GEyeW", (GX + sx * 0.36, GY - 0.88, 7.15), 0.2, eyew, scale=(1, 0.6, 1.25), sub=2)
    sphere("GEyeB", (GX + sx * 0.36, GY - 1.0, 7.12), 0.1, eyeb, sub=2)
    sphere("GEar", (GX + sx * 1.05, GY, 6.95), 0.22, skin_m, scale=(0.5, 0.8, 1.2), sub=2)
GMOUTH = sphere("GMouth", (GX, GY - 0.93, 6.45), 0.26, mouth_m, scale=(1.25, 0.45, 0.7), sub=2)
MOUTHP = (GX, GY - 1.25, 6.45)

ESO = [(GX, GY - 0.95, 6.3), (GX, OY, 5.9), (GX + 0.05, OY, 5.2), (GX + 0.25, OY, 4.75), (GX + 0.45, OY, 4.5)]
tube("Esophagus", ESO, [0.17] * len(ESO), eso_m)
STC = Vector((GX + 0.75, OY, 4.0))
stom = group("StomachG", tuple(STC))
sp_ = [sphere("Stomach", tuple(STC), 1.0, stom_m, scale=(0.98, 0.36, 0.66), sub=3),
       sphere("StomachJ", tuple(STC + Vector((0.5, 0, -0.38))), 0.45, stom_m, scale=(1.0, 0.8, 0.9), sub=3),
       cyl("StomIn", (STC.x, OY - 0.37, STC.z), 1.0, 0.04, stin_m, rot=(math.radians(90), 0, 0), verts=40),
       cyl("AcidPool", (STC.x, OY - 0.4, STC.z - 0.32), 1.0, 0.04, acid_m, rot=(math.radians(90), 0, 0), verts=40)]
sp_[2].scale = (0.84, 0.56, 1.0); sp_[3].scale = (0.66, 0.2, 1.0)
attach(sp_, stom)
GUMS = Vector((STC.x, OY - 0.52, STC.z - 0.18))       # gum resting spot inside the stomach

# small intestine: serpentine, starts at the stomach exit and ends at the lower right
SX0, SX1 = GX - 0.95, GX + 0.95
SI = [(GX + 1.3, OY - 0.08, 3.55), (GX + 1.0, OY - 0.08, 2.95)]
rows = [2.95, 2.6, 2.25, 1.9]
for k, z in enumerate(rows):
    xa, xb = (SX1, SX0) if k % 2 == 0 else (SX0, SX1)
    SI += [(xa, OY - 0.08, z), (xb, OY - 0.08, z)]
SI += [(GX + 1.32, OY - 0.06, 1.75)]
tube("SmallInt", SI, [0.17] * len(SI), si_m)
LI = [(GX + 1.32, OY, 1.75), (GX + 1.32, OY, 3.25), (GX - 1.32, OY, 3.25), (GX - 1.32, OY, 1.6), (GX - 0.3, OY, 1.5), (GX, OY, 1.42)]
tube("LargeInt", LI, [0.24] * len(LI), li_m)
def front(pts, dy=-0.32):
    return [(p[0], OY + dy, p[2]) for p in pts]

# ---------------- "You" (normal-size person) ----------------
YX, YY = -1.5, 1.0
you, YD = person("You", (0, 0, 0), 1.0, mat("Shirt", (0.2, 0.6, 0.95), 0.6), mat("Pants", (0.2, 0.3, 0.55), 0.7),
                 skin_m, mat("Hair", (0.25, 0.14, 0.07), 0.8))
HID = (0, 40, 0)
jumps(you, [(0, (YX, YY, 0)), (S[1], HID), (S[11], (-6.2, 0.7, 0)), (S[12], HID), (S[16], (YX, YY, 0))])
you.rotation_euler = (0, 0, math.radians(-12)); you.keyframe_insert("rotation_euler", frame=0)
vis(you, [(0, S[1]), (S[11], S[12]), (S[16], FRAMES)])
YM = lambda: Vector((YX, YY - 0.25, 1.565))          # mouth (rotation ignored, small)
def bubble(name, f0, fpeak, fpop, rmax):
    b_ = sphere(name, (0, 0, 0), 1.0, bubble_gum, sub=3)
    b_.data.transform(Matrix.Translation((0, -0.95, 0)))
    b_.location = tuple(YM() + Vector((0, 0.05, 0)))
    keyscale(b_, [(0, 0.001), (f0 - 1, 0.001), (f0, 0.05), (fpeak, rmax), (fpop - 1, rmax * 1.05), (fpop, 0.001)])
    burst(tuple(YM() + Vector((0, -rmax, 0))), fpop, n=12, r=rmax * 1.1, size=0.06, material=pspark_m)
    return b_
bubble("Bubble0", 3, W(0, 0.75), W(0, 0.88), 0.42)
bubble("Bubble17", S[17] + 4, W(17, 0.8), E(17) - 5, 0.62)

# =================== main gum ball: lines 1-10, 12 ===================
gum = sphere("Gum", (0, 0, 0), 0.22, gum_m, scale=(1.15, 1.0, 0.9), sub=3)
gk = []
gum.location = (GX + 0.3, GY - 3.0, 8.2); gum.keyframe_insert("location", frame=S[1])
gum.location = MOUTHP; gum.keyframe_insert("location", frame=W(1, 0.3))
path_keys(gum, [MOUTHP] + front(ESO[1:], -0.3) + [tuple(GUMS)], W(1, 0.3) + 1, E(1) - 1)
gum.location = tuple(GUMS); gum.keyframe_insert("location", frame=S[2])
gum.keyframe_insert("location", frame=S[5])
for f in range(S[5] + 2, E(5) - 1, 2):                      # line 5: acid hits, the gum shudders
    gum.location = tuple(GUMS + Vector((random.uniform(-0.04, 0.04), 0, random.uniform(-0.03, 0.03)))); gum.keyframe_insert("location", frame=f)
gum.location = tuple(GUMS); gum.keyframe_insert("location", frame=E(5) - 1)
gum.keyframe_insert("location", frame=S[8])
G8 = GUMS + Vector((0.3, 0, 0))
gum.location = tuple(G8); gum.keyframe_insert("location", frame=S[8] + 5)
gum.keyframe_insert("location", frame=S[9])
path_keys(gum, [tuple(G8)] + front(SI[:2]), S[9] + 1, E(9) - 1)
path_keys(gum, front(SI[1:-1]), S[10], E(10) - 1)
path_keys(gum, front(SI[-2:]) + front(LI, -0.38) + [(GX, OY - 0.6, 1.3), (GX, 1.2, 1.5), (GX, 0.55, 0.55)], S[12], W(12, 0.7))
gum.location = (GX, 0.55, 0.32); gum.keyframe_insert("location", frame=W(12, 0.82))
lin(gum)
keyscale(gum, [(S[6], (1.15, 1.0, 0.9)), (E(6) - 2, (1.0, 0.88, 0.8)), (S[7], (1.0, 0.88, 0.8)), (W(7, 0.25), (1.35, 0.8, 0.65)),
               (W(7, 0.5), (0.85, 0.95, 1.15)), (W(7, 0.75), (1.2, 0.85, 0.75)), (E(7), (1.0, 0.88, 0.8))])
vis_spans = [(S[1], S[11]), (S[12], S[13])]
# vis via a parent empty so the squash keys above stay intact
gpar = group("GumVis", (0, 0, 0)); gum.parent = gpar
vis(gpar, vis_spans)

# =================== line 0: chewing ===================
for f in range(0, W(0, 0.3), 4):
    pass

# =================== lines 2-3: the "7 years" calendar, smashed ===================
CAX, CAY = -0.75, 2.5
cal_m = mat("CalBack", (0.25, 0.25, 0.3), 0.6)
calg = group("CalG", (CAX, CAY, 1.6))
calp = [box("CalStand", (CAX, CAY + 0.12, 2.15), (1.55, 0.12, 2.5), cal_m, bevel=0.03),
        box("CalLeg", (CAX, CAY + 0.2, 0.5), (0.18, 0.18, 1.0), cal_m), box("CalFoot", (CAX, CAY + 0.2, 0.05), (1.0, 0.6, 0.1), cal_m)]
attach(calp, calg)
vis(calg, [(S[2], W(3, 0.55))])
pg_m = mat("Page", (0.98, 0.98, 0.96), 0.6)
ink_m = mat("Ink", (0.08, 0.08, 0.1), 0.5)
for k in range(1, 8):
    yk = CAY + 0.05 - 0.012 * (8 - k)
    g = group(f"Page{k}", (CAX, yk, 2.3))
    pp = [box("PageB", (CAX, yk, 2.3), (1.35, 0.01, 1.85), pg_m), box("PageTop", (CAX, yk - 0.006, 3.05), (1.35, 0.01, 0.32), red_lab),
          text("PageY", "YEAR", (CAX, yk - 0.014, 3.05), 0.26, white_lab, extrude=0.005),
          text("PageN", str(k), (CAX, yk - 0.012, 2.15), 1.1, ink_m, extrude=0.01)]
    attach(pp, g)
    tf = W(2, 0.12 + 0.11 * (k - 1))
    vis(g, [(S[2], W(3, 0.55) if k == 7 else tf + 9)])
    if k < 7:
        key_loc(g, [(tf, (CAX, yk, 2.3)), (tf + 9, (CAX - 2.0, yk - 1.0, 4.2))])
        keyrot(g, [(tf, (0, 0, 0)), (tf + 9, (math.radians(-60), math.radians(140), math.radians(30)))])
xg = group("XStamp", (CAX, CAY - 0.35, 2.3))
xp = [boxc("X1", (CAX, CAY - 0.35, 2.3), (0.3, 0.1, 2.3), red_lab), boxc("X2", (CAX, CAY - 0.35, 2.3), (0.3, 0.1, 2.3), red_lab)]
xp[0].rotation_euler = (0, math.radians(45), 0); xp[1].rotation_euler = (0, math.radians(-45), 0)
attach(xp, xg)
fx = W(3, 0.18)
keyscale(xg, [(0, 0.001), (fx - 1, 0.001), (fx, 2.4), (fx + 4, 0.95), (fx + 6, 1.0), (W(3, 0.55) - 1, 1.0), (W(3, 0.55), 0.001)])
burst((CAX, CAY - 0.45, 2.3), fx + 3, n=12, r=1.0, size=0.08, material=spark_m, f_out=W(3, 0.6))
# smash: shards of calendar fly apart
fs = W(3, 0.55)
for k in range(14):
    p0 = Vector((CAX + random.uniform(-0.6, 0.6), CAY - 0.1, random.uniform(1.4, 3.2)))
    sh = boxc("Shard", tuple(p0), (random.uniform(0.25, 0.5), 0.05, random.uniform(0.25, 0.5)), random.choice((pg_m, red_lab, cal_m)))
    v_ = Vector((random.uniform(-1, 1) * 2.2, -random.uniform(0.5, 2.0), random.uniform(0.5, 2.0)))
    key_loc(sh, [(fs, tuple(p0)), (fs + 8, tuple(p0 + v_)), (E(3), tuple(p0 + v_ * 1.4 + Vector((0, 0, -1.2))))])
    keyrot(sh, [(fs, (0, 0, 0)), (E(3), (random.uniform(3, 8), random.uniform(3, 8), random.uniform(1, 4)))])
    vis(sh, [(fs, S[4])], 1.0)

# =================== line 4: stomach churns ===================
for f in range(S[4], E(8), 4):
    k_ = (f - S[4]) // 4
    stom.scale = (1.0 + 0.04 * math.sin(k_ * 1.7), 1.0, 1.0 + 0.05 * math.cos(k_ * 1.7)); stom.keyframe_insert("scale", frame=f)
stom.scale = (1, 1, 1); stom.keyframe_insert("scale", frame=E(8)); stom.keyframe_insert("scale", frame=S[2])

# =================== line 5: acid bubbles attack and bounce off ===================
for k in range(14):
    p0 = Vector((STC.x + random.uniform(-0.55, 0.55), OY - 0.5, STC.z - 0.4 + random.uniform(-0.05, 0.05)))
    tgt = GUMS + (p0 - GUMS).normalized() * 0.2
    t0 = S[5] + 2 + k * 2
    bb = sphere("AcidBub", tuple(p0), random.uniform(0.05, 0.09), acidb_m, sub=1)
    out = GUMS + (p0 - GUMS).normalized() * 0.9 + Vector((0, 0, 0.3))
    key_loc(bb, [(t0, tuple(p0)), (t0 + 6, tuple(tgt)), (t0 + 14, tuple(out))])
    vis(bb, [(t0, min(t0 + 14, E(5)))])
    if k % 3 == 0:
        burst(tuple(tgt), t0 + 6, n=6, r=0.12, size=0.03, material=acidb_m, f_out=t0 + 12)

# =================== line 6: sugar + flavour leave the gum ===================
fl_ms = [sugar_m, glow_mat("FlavY", (1.0, 0.9, 0.2), 4.0), glow_mat("FlavC", (0.3, 0.9, 1.0), 4.0), pspark_m]
for k in range(18):
    a = k / 18 * 6.283
    d_ = Vector((math.cos(a), -0.15, math.sin(a)))
    o_ = box("SugarCube", tuple(GUMS), (0.09, 0.09, 0.09), fl_ms[k % 4]) if k % 2 == 0 else sphere("Flav", tuple(GUMS), 0.06, fl_ms[k % 4], sub=1)
    t0 = S[6] + (k % 6) * 2
    o_.data.transform(Matrix.Translation(-GUMS)); o_.location = tuple(GUMS)
    key_loc(o_, [(t0, tuple(GUMS)), (t0 + 20, tuple(GUMS + d_ * 1.2))])
    vis(o_, [(t0, min(t0 + 21, E(6)))])

# =================== line 8: real food melts away next to the gum ===================
FOODP = GUMS + Vector((-0.42, 0, 0.02))
food = boxc("Food", tuple(FOODP), (0.38, 0.32, 0.32), food_m, bevel=0.05)
keyscale(food, [(0, 0.001), (S[8] - 1, 0.001), (S[8], 1.0), (W(8, 0.25), 1.0), (W(8, 0.8), 0.05), (W(8, 0.8) + 1, 0.001)])
for k in range(14):
    c_ = sphere("Crumb", tuple(FOODP), 0.045, crumb_m, sub=1)
    t0 = W(8, 0.25) + k * 2
    d_ = Vector((random.uniform(-1, 0.3), -0.1, random.uniform(-0.3, 1)))
    key_loc(c_, [(t0, tuple(FOODP)), (t0 + 12, tuple(FOODP + d_ * 0.9))])
    vis(c_, [(t0, min(t0 + 12, E(8)))])

# =================== line 10: squeeze rings travel along the gut ===================
ring_m = mat("RingM", (0.85, 0.35, 0.4), 0.5)
for k in range(2):
    bpy.ops.mesh.primitive_torus_add(major_radius=0.22, minor_radius=0.07, location=(0, 0, 0))
    rg = bpy.context.object; rg.data.materials.append(ring_m); rg.rotation_mode = 'QUATERNION'
    for j in range(13):
        t = max(0.0, j / 12 - 0.08 * (k + 1))
        p, dv = along(front(SI[1:-1], -0.08), t)
        f = round(S[10] + (E(10) - 1 - S[10]) * j / 12)
        rg.location = tuple(p); rg.keyframe_insert("location", frame=f)
        rg.rotation_quaternion = dv.to_track_quat('Z', 'Y'); rg.keyframe_insert("rotation_quaternion", frame=f)
    vis(rg, [(S[10], S[11])])

# =================== line 11: the gut unrolled on the lawn next to you ===================
UX0, UY = -5.5, 0.55
bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=0.2, depth=5.0, location=(0, 0, 0), rotation=(0, math.radians(90), 0))
un = bpy.context.object; un.name = "Unrolled"; bpy.ops.object.transform_apply(rotation=True)
un.data.transform(Matrix.Translation((2.5, 0, 0))); un.location = (UX0, UY, 0.22); un.data.materials.append(si_m)
keyscale(un, [(0, (0.001,) * 3), (S[11] - 1, (0.001,) * 3), (S[11], (0.02, 1, 1)), (W(11, 0.6), (1, 1, 1)), (E(11), (1, 1, 1)), (E(11) + 1, (0.001,) * 3)])
for m_i in range(1, 6):
    t_ = text(f"Ruler{m_i}", f"{m_i} m", (UX0 + m_i, UY - 0.55, 0.03), 0.34, lab_m, rot=(0, 0, 0), extrude=0.01)
    tk_ = box("Tick", (UX0 + m_i, UY - 0.28, 0.04), (0.05, 0.25, 0.04), white_lab)
    for o_ in (t_, tk_):
        vis(o_, [(round(S[11] + (W(11, 0.6) - S[11]) * m_i / 5), S[12])])
gum2 = sphere("Gum2", (UX0, UY, 0.5), 0.2, gum_m, scale=(1.15, 1.0, 0.9), sub=3)
key_loc(gum2, [(S[11], (UX0, UY - 0.05, 0.5)), (W(11, 0.6), (UX0 + 5.0, UY - 0.05, 0.5)), (E(11), (UX0 + 5.0, UY - 0.05, 0.5))])
lin(gum2)
vis(gum2, [(S[11], S[12])], (1.15, 1.0, 0.9))

# =================== line 12: it's out (cartoon toilet) ===================
TX, TY = GX, 0.55
toil = group("Toilet", (TX, TY, 0))
tp = [cyl("Bowl", (TX, TY, 0.24), 0.34, 0.48, porc_m, r2=0.44, verts=28),
      box("Tank", (TX, TY + 0.5, 0.75), (0.8, 0.28, 0.6), porc_m, bevel=0.06),
      cyl("TankStem", (TX, TY + 0.45, 0.4), 0.18, 0.5, porc_m, verts=16),
      cyl("WaterT", (TX, TY, 0.47), 0.36, 0.03, water_m, verts=28)]
bpy.ops.mesh.primitive_torus_add(major_radius=0.42, minor_radius=0.06, location=(TX, TY, 0.5))
o = bpy.context.object; o.data.materials.append(porc_m); tp.append(o)
attach(tp, toil)
vis(toil, [(S[12], S[13])])
for k in range(12):
    a = k / 12 * 6.283
    sp2 = sphere("Splash", (TX, TY, 0.5), 0.06, water_m, sub=1)
    t0 = W(12, 0.82)
    key_loc(sp2, [(t0, (TX, TY, 0.5)), (t0 + 6, (TX + 0.5 * math.cos(a), TY + 0.5 * math.sin(a), 1.2)), (t0 + 11, (TX + 0.8 * math.cos(a), TY + 0.8 * math.sin(a), 0.6))])
    vis(sp2, [(t0, min(t0 + 11, E(12)))])

# =================== line 13: "7 YEARS" (crossed out) vs "FEW DAYS" (tick) ===================
def sign(name, x, title, tm, f_in):
    g = group(name, (x, 0.5, 1.4))
    pr = [box(name + "B", (x, 0.5, 1.45), (2.0, 0.12, 0.95), board_m, bevel=0.04),
          box(name + "P", (x, 0.6, 0.5), (0.14, 0.14, 1.0), cal_m),
          text(name + "T", title, (x, 0.42, 1.45), 0.42, tm, extrude=0.02)]
    attach(pr, g)
    keyscale(g, [(0, 0.001), (f_in - 1, 0.001), (f_in + 4, 1.12), (f_in + 6, 1.0), (S[14] - 1, 1.0), (S[14], 0.001)])
    return g
sign("SignY", GX - 1.15, "7 YEARS", red_lab, S[13])
sign("SignD", GX + 1.15, "FEW DAYS", green_lab, W(13, 0.4))
x13 = group("X13", (GX - 1.15, 0.3, 1.45))
xq = [boxc("X13a", (GX - 1.15, 0.3, 1.45), (0.18, 0.08, 1.5), red_lab), boxc("X13b", (GX - 1.15, 0.3, 1.45), (0.18, 0.08, 1.5), red_lab)]
xq[0].rotation_euler = (0, math.radians(55), 0); xq[1].rotation_euler = (0, math.radians(-55), 0)
attach(xq, x13)
f13 = W(13, 0.2)
keyscale(x13, [(0, 0.001), (f13 - 1, 0.001), (f13, 2.0), (f13 + 4, 1.0), (S[14] - 1, 1.0), (S[14], 0.001)])
def check(name, c, f_in, f_out, s=1.0):
    g = group(name, c)
    a_ = boxc(name + "a", (c[0] - 0.18 * s, c[1], c[2] - 0.05 * s), (0.14 * s, 0.08, 0.42 * s), green_lab)
    b_ = boxc(name + "b", (c[0] + 0.12 * s, c[1], c[2] + 0.12 * s), (0.14 * s, 0.08, 0.85 * s), green_lab)
    a_.rotation_euler = (0, math.radians(-40), 0); b_.rotation_euler = (0, math.radians(30), 0)
    attach([a_, b_], g)
    keyscale(g, [(0, 0.001), (f_in - 1, 0.001), (f_in + 3, 1.25), (f_in + 6, 1.0), (f_out - 1, 1.0), (f_out, 0.001)])
    return g
check("Chk13", (GX + 1.15, 0.3, 2.35), W(13, 0.55), S[14])
burst((GX + 1.15, 0.3, 2.3), W(13, 0.55) + 2, n=10, r=0.6, size=0.05, material=spark_m, f_out=S[14])

# =================== line 14: a LOT of gum goes down ===================
for k in range(16):
    b_ = sphere("ManyGum", (0, 0, 0), 0.17, gum_m if k % 2 else gum_m2, scale=(1.15, 1.0, 0.9), sub=2)
    t0 = S[14] + round(k * 1.7)
    st_ = (GX + random.uniform(-1.2, 1.2), GY - 3.4, 8.4 + random.uniform(-0.4, 0.4))
    cl_ = GUMS + Vector((random.uniform(-0.55, 0.55), random.uniform(-0.05, 0.05), random.uniform(-0.15, 0.3)))
    path_keys(b_, [st_, MOUTHP] + front(ESO[1:], -0.3) + [tuple(cl_)], t0, t0 + 15)
    lin(b_)
    vis(b_, [(t0, S[15])], (1.15, 1.0, 0.9))

# =================== line 15: a gum lump blocks the gut ===================
LUMP = Vector((SX0 + 0.05, OY - 0.3, 2.42))
lump = sphere("Lump", tuple(LUMP), 0.36, gum_m, scale=(1.0, 0.8, 1.1), sub=2, smooth=False)
pop(lump, S[15], 5, S[16])
bpy.ops.mesh.primitive_torus_add(major_radius=0.55, minor_radius=0.06, location=tuple(LUMP + Vector((0, -0.2, 0))), rotation=(math.radians(90), 0, 0))
wr = bpy.context.object; wr.data.materials.append(redglow)
kk = [(0, 0.001), (S[15] - 1, 0.001)]
for j, f in enumerate(range(S[15], E(15), 5)):
    kk.append((f, 1.0 if j % 2 == 0 else 1.35))
kk += [(E(15) - 1, 1.0), (E(15), 0.001)]
keyscale(wr, kk)
redrow = tube("RedRow", front(SI[2:6], -0.1), [0.19] * 4, redglow)
rk = [(0, 0.001), (S[15] - 1, 0.001)]
for j, f in enumerate(range(S[15], E(15), 5)):
    rk.append((f, 1.0 if j % 2 == 0 else 0.001))
rk += [(E(15), 0.001)]
redrow_par = group("RedRowP", (0, 0, 0)); redrow.parent = redrow_par
for f, s in rk:
    redrow_par.scale = (s,) * 3; redrow_par.keyframe_insert("scale", frame=f)
for fc in fcurves(redrow_par):
    for p in fc.keyframe_points:
        p.interpolation = 'CONSTANT'
for k in range(6):
    p_ = LUMP + Vector((0.35 + 0.22 * k, 0, 0.18 * ((k % 2) * 2 - 1) * 0.3 + 0.18))
    sb = sphere("Stuck", tuple(p_), 0.12, gum_m2, sub=2)
    pop(sb, S[15] + 3 + k * 2, 4, S[16])

# =================== line 16: one piece is fine — thumbs up ===================
check("Chk16", (YX, YY - 0.1, 2.45), S[16] + 4, S[17], s=0.8)
one = sphere("OneGum", (YX + 0.45, YY - 0.1, 1.95), 0.12, gum_m, scale=(1.15, 1.0, 0.9), sub=2)
vis(one, [(S[16] + 6, S[17])], (1.15, 1.0, 0.9))
ar = YD["arms"][1]
keyrot(ar, [(0, (0, 0, 0)), (S[16] + 2, (0, 0, 0)), (S[16] + 7, (0, math.radians(-150), 0)), (S[17] - 1, (0, math.radians(-150), 0)), (S[17], (0, 0, 0))])

# =================== views (camera, subject) per line; subject in the lower third ===================
V, V2 = {}, {}
V[0] = ((0.0, -3.0, 1.8), (YX, YY, 1.4));                 V2[0] = ((-2.8, -2.6, 1.8), (YX, YY, 1.5))
V[1] = ((4.0, -4.0, 5.6), (GX, OY, 5.6));                 V2[1] = ((0.8, -3.6, 5.4), (GX + 0.3, OY, 4.9))
V[2] = ((-2.0, -4.6, 3.0), (0.9, 2.3, 3.0));              V2[2] = ((2.2, -4.9, 3.0), (0.9, 2.3, 3.0))
V[3] = ((1.4, -3.6, 2.4), (CAX + 0.2, CAY, 2.3));         V2[3] = ((-2.4, -3.4, 2.4), (CAX + 0.2, CAY, 2.3))
V[4] = ((4.6, -2.6, 4.0), (STC.x, OY, 3.9));              V2[4] = ((3.4, -1.6, 4.0), (STC.x, OY, 3.85))
V[5] = ((1.2, -1.9, 3.8), (GUMS.x, OY, 3.8));             V2[5] = ((3.9, -1.7, 3.8), (GUMS.x, OY, 3.8))
V[6] = ((4.2, -1.6, 3.8), (GUMS.x, OY, 3.85));            V2[6] = ((2.0, -1.2, 3.8), (GUMS.x, OY, 3.85))
V[7] = ((1.6, -1.3, 3.8), (GUMS.x, OY, 3.8));             V2[7] = ((3.6, -1.5, 3.8), (GUMS.x, OY, 3.8))
V[8] = ((2.4, -1.7, 3.8), (GUMS.x - 0.1, OY, 3.8));       V2[8] = ((3.0, -1.5, 3.8), (GUMS.x - 0.1, OY, 3.8))
V[9] = ((4.6, -2.0, 3.4), (GX + 1.1, OY, 3.25));          V2[9] = ((3.0, -2.2, 3.2), (GX + 0.9, OY, 2.9))
V[10] = ((3.6, -2.6, 2.6), (GX + 0.2, OY, 2.35));         V2[10] = ((0.4, -2.6, 2.6), (GX - 0.1, OY, 2.3))
V[11] = ((-4.6, -6.6, 1.0), (-3.4, 0.6, 0.5));            V2[11] = ((-2.0, -6.9, 1.0), (-3.2, 0.6, 0.5))
V[12] = ((4.8, -3.6, 2.0), (GX, 1.4, 1.5));               V2[12] = ((2.6, -4.2, 1.8), (GX, 1.2, 1.1))
V[13] = ((0.9, -5.6, 1.4), (GX, 0.5, 1.3));               V2[13] = ((3.0, -5.4, 1.4), (GX, 0.5, 1.3))
V[14] = ((-0.2, -5.2, 5.0), (GX + 0.3, OY, 4.9));         V2[14] = ((3.6, -5.0, 4.8), (GX + 0.4, OY, 4.4))
V[15] = ((-0.3, -2.4, 2.6), (LUMP.x + 0.3, OY, 2.45));    V2[15] = ((1.9, -2.2, 2.6), (LUMP.x + 0.3, OY, 2.45))
V[16] = ((0.4, -2.8, 1.8), (YX, YY, 1.5));                V2[16] = ((-1.4, -2.9, 1.8), (YX, YY, 1.5))
V[17] = ((-1.6, -3.4, 1.8), (YX + 0.3, YY, 1.4));         V2[17] = ((1.0, -7.4, 2.4), (0.4, 1.8, 1.8))

def LB(i, name, body, m_, size=None, f_in=None, f_out=None, Dk=0.55, end=False, v=0.26, u=0.0):
    mid = lambda a, b: tuple((Vector(a) + Vector(b)) / 2)
    view = V2[i] if end else (mid(V[i][0], V2[i][0]), mid(V[i][1], V2[i][1]))
    cl = Vector(CL(view)); D = (Vector(view[1]) - cl).length * Dk
    s_ = 0.9 * fit(body, D, size if size else 1e9)
    return label(name, body, view, D, v, s_, m_, (S[i] + 3) if f_in is None else f_in,
                 E(i) if f_out is None else f_out, u)
LB(0, "L0", "SWALLOWED GUM?", pink_lab)
LB(1, "L1", "GULP!", lab_m)
LB(2, "L2", "MYTH: 7 YEARS?", red_lab)
LB(3, "L3", "NOPE!", red_lab, f_in=W(3, 0.2))
LB(4, "L4", "STOMACH", lab_m)
LB(5, "L5", "ACID FAILS!", green_lab, f_in=W(5, 0.45))
LB(6, "L6", "SUGAR: ABSORBED", white_lab)
LB(7, "L7", "CAN'T DIGEST", red_lab)
LB(8, "L8a", "FOOD MELTS", lab_m, u=-0.2, v=0.2, size=0.2)
LB(8, "L8b", "GUM STAYS", pink_lab, u=0.2, v=0.31, size=0.2, f_in=W(8, 0.45))
LB(9, "L9", "KEEPS MOVING", lab_m)
LB(10, "L10", "SQUEEZE!", pink_lab)
LB(11, "L11", "METERS LONG!", lab_m)
LB(12, "L12", "IT'S OUT!", green_lab, f_in=W(12, 0.6))
LB(13, "L13", "DAYS, NOT YEARS", green_lab)
LB(14, "L14", "A LOT = DANGER", red_lab)
LB(15, "L15", "BLOCKED!", red_lab)
LB(16, "L16", "1 PIECE = OK", green_lab)
LB(17, "L17", "HAVE YOU?", lab_m, end=True, f_in=S[17] + 6, Dk=0.45)

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
