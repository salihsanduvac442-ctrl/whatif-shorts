# Day 25 — What if you stacked a trillion dollars?  Build: python3 episodes/025-trillion-stack/scene.py
# Reference style: base (helpers, lawn/soil, house, garden) copied from episodes/003-lift-million-ref / 006-mantis-punch
import bpy, math, random, os, json
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
random.seed(25)
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
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
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
    x, y, z, s = x * 4, y * 6, z * 3.2, s * 3.5
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
box("Ground", (0, 25.9, -6.0), (400, 55.0, 12.0), grass_m)
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
    bpy.ops.mesh.primitive_plane_add(size=1, location=(sx * 100016, 25.9, -0.03))
    o = bpy.context.object; o.scale = (199968, 55.0, 1); o.data.materials.append(far)

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


# =====================================================================================
# Day 25 — What if you stacked a trillion dollars?
# Facts used (checked 2026-11-19):
#   $1 trillion = 1,000,000 x $1,000,000.  US bill: 15.6 x 6.6 cm, ~0.11 mm thick, ~1 g.
#   In $100 bills: $1M = 10,000 bills = ~1.09 m;  $1B = ~1.09 km;  $1T = 10 billion bills = ~1,090 km.
#   Airliners cruise ~10-12 km; edge of space (Karman line) 100 km; ISS orbits ~400-420 km -> 1,090 km ~2.6x.
#   Weight 10^10 g = 10,000 t (volume ~11,300 m3 = a ~22 m cube).  Eiffel Tower total mass ~10,100 t.
#   One bill per second: 10^10 s = ~317 years.  In $1 bills: 100x taller = ~109,000 km.
# =====================================================================================
from mathutils import Quaternion
bill_m = mat("Bill", (0.3, 0.68, 0.25), 0.8)
bill_lt = mat("BillLt", (0.62, 0.85, 0.55), 0.8)
band_m = mat("Band", (0.95, 0.75, 0.3), 0.6)
cash_m = stripe_mat("Cash", (0.3, 0.68, 0.25), (0.18, 0.48, 0.15), axis="Z", freq=40.0, thresh=0.3)
bigcash_m = stripe_mat("BigCash", (0.32, 0.7, 0.27), (0.2, 0.5, 0.17), axis="Z", freq=2.2, thresh=0.3)
red_m = mat("RedM", (0.9, 0.12, 0.1), 0.5)
white_m = mat("WhiteM", (0.97, 0.97, 0.95), 0.5)
dark_m = mat("DarkM", (0.08, 0.08, 0.1), 0.5)
wood_m = mat("Wood", (0.6, 0.42, 0.24), 0.8)
dust_m = mat("Dust", (0.85, 0.8, 0.7), 0.95)
crack_m = mat("Crack", (0.05, 0.04, 0.03), 0.9)
metal_m = mat("Metal", (0.75, 0.77, 0.8), 0.35, metal=0.7)
panel_m = mat("Panel", (0.15, 0.25, 0.7), 0.3, emit=(0.1, 0.2, 0.6), emit_strength=0.4, metal=0.3)
glass_m = bpy.data.materials.new("Glass"); glass_m.use_nodes = True
_gb = glass_m.node_tree.nodes["Principled BSDF"]
_gb.inputs["Base Color"].default_value = (0.8, 0.92, 1.0, 1); _gb.inputs["Roughness"].default_value = 0.02
_gb.inputs["Transmission Weight"].default_value = 1.0
tower_m = mat("Tower", (0.5, 0.33, 0.2), 0.7)

# column material: bands fixed in WORLD height, so the stack can grow without stretching its stripes
col_m = bpy.data.materials.new("ColCash"); col_m.use_nodes = True
_N = col_m.node_tree.nodes; _L = col_m.node_tree.links
_bs = _N["Principled BSDF"]; _bs.inputs["Roughness"].default_value = 0.75
_geo = _N.new("ShaderNodeNewGeometry"); _sp = _N.new("ShaderNodeSeparateXYZ"); _L.new(_geo.outputs["Position"], _sp.inputs[0])
_mu = _N.new("ShaderNodeMath"); _mu.operation = 'MULTIPLY'; _mu.inputs[1].default_value = 30.0; _L.new(_sp.outputs["Z"], _mu.inputs[0])
_sn = _N.new("ShaderNodeMath"); _sn.operation = 'SINE'; _L.new(_mu.outputs[0], _sn.inputs[0])
_gt = _N.new("ShaderNodeMath"); _gt.operation = 'GREATER_THAN'; _gt.inputs[1].default_value = 0.3; _L.new(_sn.outputs[0], _gt.inputs[0])
_mx = _N.new("ShaderNodeMix"); _mx.data_type = 'RGBA'
_mx.inputs[6].default_value = (0.32, 0.72, 0.26, 1); _mx.inputs[7].default_value = (0.18, 0.48, 0.15, 1)
_L.new(_gt.outputs[0], _mx.inputs["Factor"]); _L.new(_mx.outputs[2], _bs.inputs["Base Color"])
_bs.inputs["Emission Color"].default_value = (0.2, 0.6, 0.18, 1); _bs.inputs["Emission Strength"].default_value = 0.35

def lin(o):
    for fc in fcurves(o):
        for k in fc.keyframe_points:
            k.interpolation = 'LINEAR'
def fcurves(o_):
    ad = o_.animation_data
    if ad is None or ad.action is None:
        return []
    try:
        return list(ad.action.fcurves)
    except AttributeError:
        from bpy_extras import anim_utils
        return list(anim_utils.action_get_channelbag_for_slot(ad.action, ad.action_slot).fcurves)

def column(name, loc, w, d, m_):
    g = group(name, loc)
    b = box(name + "B", (loc[0], loc[1], loc[2] + 0.5), (w, d, 1.0), m_)
    attach([b], g)
    return g

def face_rot(loc, cam):
    fwd = Vector(loc) - Vector(cam)
    return (math.radians(90) - math.atan2(-fwd.z, math.hypot(fwd.x, fwd.y)), 0, math.atan2(fwd.x, -fwd.y) + math.pi)

def lab3(name, body, loc, cam, m_, f_in, f_out, maxs):
    D = (Vector(loc) - Vector(cam)).length
    s_ = min(maxs, 0.62 * 0.778 * D / (max(len(body), 5) * 0.62))
    t = text(name, body, loc, s_, m_, extrude=s_ * 0.08)
    t.rotation_euler = face_rot(loc, cam)
    t.visible_shadow = False
    pop(t, f_in, 5, f_out)
    return t

def person_hair(name, base, shirt, pants, hair):
    return person(name, base, 1.0, shirt, pants, skin_m, hair)

def ease(a, b, t):
    t = max(0.0, min(1.0, t)); t = t * t * (3 - 2 * t)
    return a + (b - a) * t

# ================================ SET A: the backyard ================================
YX, YY = 0.0, 0.5
hair_m = mat("YouHair", (0.25, 0.14, 0.06), 0.8)
you, yd = person_hair("You", (YX, YY, 0), mat("YouShirt", (0.95, 0.3, 0.35), 0.7), mat("YouPants", (0.18, 0.22, 0.38), 0.8), hair_m)
armL, armR = yd["arms"]
def arms_up(fs):
    for f, up in fs:
        a = math.radians(150) * up
        keyrot(armL, [(f, (0, a, 0))]); keyrot(armR, [(f, (0, -a, 0))])
arms_up([(0, 0), (6, 1), (S[1] - 2, 1), (S[1], 0), (S[3], 0), (S[3] + 5, 0.3), (E(3) - 1, 0.3), (E(3), 0),
         (S[11], 0), (S[11] + 9, 1), (E(12) - 1, 1), (E(12), 0), (S[16], 0), (S[16] + 5, 0.55)])

# the stack in the yard (grows: 1.09 m -> 1.09 km -> off the screen)
CX, CY = 0.85, 0.5
ycol = column("YardCol", (CX, CY, 0), 0.62, 0.28, col_m)
keyscale(ycol, [(0, (1, 1, 130)), (S[1] - 1, (1, 1, 130)), (S[1], (0.001,) * 3), (S[3] - 1, (0.001,) * 3), (S[3], (1, 1, 0.001)),
                (S[3] + 16, (1, 1, 1.09)), (S[4] + 1, (1, 1, 1.09)), (S[4] + 30, (3.2, 3.2, 110)), (S[5] + 2, (3.2, 3.2, 110)), (E(5) - 1, (4.5, 4.5, 520)),
                (E(5), (0.001,) * 3), (S[16] - 1, (0.001,) * 3), (S[16], (1, 1, 520))])
# a cap (top bill bundle with a band) that rides on top while it grows (line 3)
cap_ = box("ColBand", (CX, CY, 0.55), (0.64, 0.3, 0.12), band_m)
keyscale(cap_, [(0, 0.001), (S[3] - 1, 0.001), (S[3], 1.0), (E(3) - 1, 1.0), (E(3), 0.001)])
key_loc(cap_, [(S[3], (CX, CY, 0.05)), (S[3] + 16, (CX, CY, 0.55))])
# local clouds the column pokes through (line 4-5)
cloud_m2 = mat("Cloud2", (1, 1, 1), 0.9, emit=(1, 1, 1), emit_strength=0.45)
for k in range(16):
    a = random.uniform(0, 6.28); r = random.uniform(5, 26)
    x, y = CX + r * math.cos(a), CY + abs(r * math.sin(a)) * 1.2 + 2
    z = random.uniform(36, 48)
    for j in range(3):
        c_ = sphere("YCloud", (x + (j - 1) * 3.2, y, z + random.uniform(-0.8, 0.8)), random.uniform(2.6, 3.8), cloud_m2, scale=(1.4, 0.9, 0.7), sub=2)
        hide_until(c_, S[4] + 2)
# speed streaks along the column (line 5)
for k in range(14):
    z0 = random.uniform(60, 200); x0 = CX + random.choice([-1, 1]) * random.uniform(1.5, 4)
    st = tube("Streak", [(x0, CY + 1, z0), (x0, CY + 1, z0 + 14)], [0.18, 0.18], white_lab)
    key_loc(st, [(S[5] + 2, (0, 0, 40)), (E(5), (0, 0, -60))])
    pop(st, S[5] + 2 + k % 5, 3, E(5))

# line 0: bills rain around you
for k in range(36):
    p = (YX + random.uniform(-2.6, 2.6), YY + random.uniform(-0.8, 1.6), random.uniform(2.4, 6.0))
    b = box("RainBill", p, (0.42, 0.18, 0.012), bill_m)
    st = random.randint(0, 12); zend = random.uniform(0.05, 0.12)
    b.rotation_euler = (random.uniform(-1, 1), random.uniform(-1, 1), random.uniform(0, 6)); b.keyframe_insert("rotation_euler", frame=st)
    b.rotation_euler = (0, 0, random.uniform(0, 6)); b.keyframe_insert("rotation_euler", frame=st + 16)
    key_loc(b, [(st, p), (st + 16, (p[0], p[1], zend))])
    hide_until(b, st); gone_at(b, S[1] + 1, 2)

# line 1: a million $1M bricks (a wave of bricks over the lawn)
def brick(name, loc):
    g = group(name, loc)
    attach([box(name + "C", (loc[0], loc[1], loc[2] + 0.2), (0.5, 0.24, 0.4), cash_m, bevel=0.01),
            box(name + "Bd", (loc[0], loc[1], loc[2] + 0.2), (0.1, 0.26, 0.42), band_m)], g)
    return g
for ix in range(12):
    for iy in range(8):
        x, y = -3.3 + ix * 0.6, 1.4 + iy * 0.55
        bg_ = brick("Brick", (x, y, 0))
        f0 = S[1] + 2 + int((ix + iy) * 1.0)
        keyscale(bg_, [(0, 0.001), (f0 - 1, 0.001), (f0 + 3, 1.2), (f0 + 5, 1.0), (E(1) - 1, 1.0), (E(1), 0.001)])

# line 2: one hero $100 bill flips edge-on -> paper thin
HBX, HBY, HBZ = 0.75, -0.25, 1.45
hb = group("HeroBill", (HBX, HBY, HBZ))
hparts = [box("HB", (HBX, HBY, HBZ), (2.0, 0.035, 0.85), bill_m),
          box("HBin", (HBX, HBY - 0.02, HBZ), (1.5, 0.01, 0.6), bill_lt),
          sphere("HBseal", (HBX - 0.35, HBY - 0.03, HBZ), 0.2, bill_m, scale=(1, 0.1, 1), sub=2),
          text("HBt", "$100", (HBX + 0.3, HBY - 0.04, HBZ), 0.32, dark_m)]
for sx in (-1, 1):
    for sz in (-1, 1):
        hparts.append(text("HBc", "100", (HBX + sx * 0.8, HBY - 0.03, HBZ + sz * 0.3), 0.13, dark_m))
attach(hparts, hb)
flip = W(2, 0.42)
keyscale(hb, [(0, 0.001), (S[2] - 1, 0.001), (S[2] + 3, 1.1), (S[2] + 5, 1.0), (E(2) - 1, 1.0), (E(2), 0.001)])
keyrot(hb, [(S[2], (0, 0, -0.5)), (S[2] + 8, (0, 0, 0.12)), (flip, (0, 0, 0.12)), (flip + 8, (0, 0, math.radians(90)))])
for sz in (-1, 1):     # arrows pointing at the thin edge
    c_ = cyl("ThinArr", (HBX, HBY - 0.25, HBZ + sz * 0.75), 0.12, 0.35, lab_m, r2=0.0, verts=12, rot=(0, math.radians(180) if sz > 0 else 0, 0))
    pop(c_, flip + 9, 4, E(2))

# line 3: waist line next to the 1.09 m stack
wline = box("WaistLine", (CX - 0.45, CY - 0.3, 1.09), (1.6, 0.02, 0.025), lab_m)
pop(wline, S[3] + 14, 4, E(3))

# ---------------- line 11: the whole trillion = a ~22 m cash cube slams down ----------------
QX, QY, QS = 19.0, 14.0, 22.4
cube = group("TCube", (QX, QY, 0))
cparts = [box("TCubeC", (QX, QY, QS / 2), (QS, QS, QS), bigcash_m)]
for dx in (-QS * 0.27, QS * 0.27):
    cparts.append(box("TCubeBd", (QX + dx, QY, QS / 2), (2.2, QS + 0.1, QS + 0.1), band_m))
cparts.append(text("TCubeT", "$1 TRILLION", (QX, QY - QS / 2 - 0.08, QS * 0.62), 2.6, white_lab))
attach(cparts, cube)
fh = S[11] + 8
keyscale(cube, [(0, 0.001), (S[11] - 1, 0.001), (S[11], 1.0), (fh, 1.0), (fh + 2, (1.08, 1.08, 0.88)), (fh + 5, 1.0),
                (E(12) - 1, 1.0), (E(12), 0.001)])
key_loc(cube, [(S[11], (QX, QY, 70.0)), (fh, (QX, QY, 0.0))])
for k in range(18):
    a = k / 18 * 6.283
    d_ = sphere("Dust", (QX + 12 * math.cos(a), QY + 12 * math.sin(a), 1.0), 2.4, dust_m, sub=1)
    key_loc(d_, [(fh, (QX + 12 * math.cos(a), QY + 12 * math.sin(a), 1.0)), (fh + 14, (QX + 20 * math.cos(a), QY + 20 * math.sin(a), 4.0))])
    pop(d_, fh, 3, fh + 15)
for k in range(12):   # cracks in the lawn running out from the cube
    a = -math.pi / 2 + random.uniform(-1.3, 1.3)
    Lc = random.uniform(5, 11)
    cx_, cy_ = QX + (12 + Lc / 2) * math.cos(a), QY + (12 + Lc / 2) * math.sin(a)
    cr_ = box("CrackL", (cx_, cy_, 0.02), (Lc, 0.35, 0.05), crack_m, rot=(0, 0, a))
    hide_until(cr_, fh + 1 + (k % 3)); gone_at(cr_, E(12), 1)

# ---------------- line 12: Eiffel-style iron tower, true size, rises behind the house ----------------
TX, TY = -95.0, 125.0
tw = group("Tower", (TX, TY, 0))
tparts = []
prof = [(0, 62), (57, 45), (116, 22), (200, 9), (276, 4.5)]
rad = [5.0, 3.8, 2.8, 1.8, 1.3]
for sx in (-1, 1):
    for sy in (-1, 1):
        tparts.append(tube("TLeg", [(TX + sx * b_, TY + sy * b_, z) for z, b_ in prof], rad, tower_m))
for z, half, th in [(57, 48, 3.2), (116, 24, 2.6), (276, 6, 8.0)]:
    tparts.append(box("TDeck", (TX, TY, z), (half * 2, half * 2, th), tower_m))
tparts.append(cyl("TSpire", (TX, TY, 303), 1.6, 50, tower_m, r2=0.4, verts=10))
for (ax, ay) in [((1, 0)), ((0, 1))]:
    for sgn in (-1, 1):   # arches + cross bracing on each face
        def P(u, z, b_):
            return (TX + (u * b_ if ax else sgn * b_), TY + (sgn * b_ if ax else u * b_), z)
        tparts.append(tube("TArch", [P(-0.8, 2, 58), P(-0.5, 30, 52), P(0, 40, 50), P(0.5, 30, 52), P(0.8, 2, 58)], [1.2] * 5, tower_m))
        for (z0, b0), (z1, b1) in zip(prof[1:-1], prof[2:]):
            tparts.append(tube("TBr", [P(-1, z0, b0), P(1, z1, b1)], [0.8, 0.8], tower_m))
            tparts.append(tube("TBr", [P(1, z0, b0), P(-1, z1, b1)], [0.8, 0.8], tower_m))
attach(tparts, tw)
keyscale(tw, [(0, 0.001), (S[12] - 1, 0.001), (S[12], (1, 1, 0.02)), (S[12] + 12, (1, 1, 1.04)), (S[12] + 15, 1.0), (E(12) - 1, 1.0), (E(12), 0.001)])

# ---------------- lines 13-14: counting one bill per second ... for 317 years ----------------
TBX, TBY = 0.0, -0.35
tparts2 = [box("TableTop", (TBX, TBY, 0.72), (1.6, 0.6, 0.06), wood_m)]
for dx in (-0.7, 0.7):
    for dy in (-0.24, 0.24):
        tparts2.append(box("TableLeg", (TBX + dx, TBY + dy, 0.36), (0.06, 0.06, 0.72), wood_m))
pileL = column("PileL", (TBX - 0.5, TBY, 0.75), 0.42, 0.18, cash_m)
pileR = column("PileR", (TBX + 0.5, TBY, 0.75), 0.42, 0.18, cash_m)
for o_ in tparts2:
    keyscale(o_, [(0, 0.001), (S[13] - 1, 0.001), (S[13], 1.0), (E(14) - 1, 1.0), (E(14), 0.001)])
keyscale(pileL, [(0, 0.001), (S[13] - 1, 0.001), (S[13], (1, 1, 0.5)), (E(14) - 1, (1, 1, 0.5)), (E(14), 0.001)])
keyscale(pileR, [(0, 0.001), (S[13] - 1, 0.001), (S[13], (1, 1, 0.02)), (S[14], (1, 1, 0.06)), (E(14) - 4, (1, 1, 0.9)), (E(14) - 1, (1, 1, 0.9)), (E(14), 0.001)])
# bills hop from the left pile to the right pile
for k in range(10):
    f0 = S[13] + 2 + k * 6
    if f0 + 6 > E(14) - 2:
        break
    b = box("Hop", (TBX - 0.5, TBY, 1.3), (0.42, 0.18, 0.012), bill_m)
    key_loc(b, [(f0, (TBX - 0.5, TBY, 1.28)), (f0 + 3, (TBX, TBY - 0.05, 1.7)), (f0 + 6, (TBX + 0.5, TBY, 1.3))])
    keyrot(b, [(f0, (0, 0, 0)), (f0 + 6, (0, math.radians(180), 0))])
    pop(b, f0, 1, f0 + 7)
# counting arm
for k in range(0, E(14) - S[13], 6):
    keyrot(armR, [(S[13] + k, (0, -0.3, 0)), (S[13] + k + 3, (0, -1.1, 0))])
keyrot(armR, [(E(14), (0, 0, 0))])
# big clock on a post
CKX, CKY, CKZ = 1.9, 1.0, 2.3
ck = group("Clock", (CKX, CKY, CKZ))
ckp = [cyl("CkFace", (CKX, CKY, CKZ), 0.55, 0.08, white_m, rot=(math.radians(90), 0, 0), verts=32),
       cyl("CkRim", (CKX, CKY + 0.03, CKZ), 0.62, 0.08, red_m, rot=(math.radians(90), 0, 0), verts=32),
       cyl("CkPost", (CKX, CKY + 0.05, CKZ / 2 - 0.3), 0.05, CKZ - 0.6, dark_m)]
for k in range(12):
    a = k / 12 * 6.283
    ckp.append(box("CkTick", (CKX + 0.46 * math.sin(a), CKY - 0.05, CKZ + 0.46 * math.cos(a)), (0.05, 0.02, 0.1), dark_m, rot=(0, a, 0)))
attach(ckp, ck)
hand = group("CkHand", (CKX, CKY - 0.07, CKZ))
attach([box("CkHandB", (CKX, CKY - 0.07, CKZ + 0.2), (0.05, 0.02, 0.42), red_m)], hand)
hand2 = group("CkHand2", (CKX, CKY - 0.06, CKZ))
attach([box("CkHandB2", (CKX, CKY - 0.06, CKZ + 0.13), (0.07, 0.02, 0.28), dark_m)], hand2)
for o_ in (ck, hand, hand2):
    keyscale(o_, [(0, 0.001), (S[13] - 1, 0.001), (S[13] + 3, 1.1), (S[13] + 5, 1.0), (E(14) - 1, 1.0), (E(14), 0.001)])
for k in range(0, S[14] - S[13], 6):     # ticks, one per "second"
    keyrot(hand, [(S[13] + k, (0, k / 6 * 0.5236, 0)), (S[13] + k + 1, (0, (k / 6 + 1) * 0.5236, 0))])
keyrot(hand, [(S[14], (0, 3.0, 0)), (E(14), (0, 3.0 + 6.283 * 9, 0))])
keyrot(hand2, [(S[13], (0, 0, 0)), (S[14], (0, 0.2, 0)), (E(14), (0, 6.283 * 3, 0))])
# 317 years: hair turns grey, a long beard grows, cobweb
hc = hair_m.node_tree.nodes["Principled BSDF"].inputs["Base Color"]
for f, c in [(0, (0.25, 0.14, 0.06, 1)), (S[14] + 4, (0.25, 0.14, 0.06, 1)), (S[14] + 16, (0.88, 0.88, 0.9, 1)), (E(14) - 1, (0.88, 0.88, 0.9, 1)), (E(14), (0.25, 0.14, 0.06, 1))]:
    hc.default_value = c; hc.keyframe_insert("default_value", frame=f)
beard = sphere("Beard", (YX, YY - 0.17, 1.38), 1.0, mat("BeardM", (0.92, 0.92, 0.94), 0.8), scale=(0.001,) * 3, sub=3)
keyscale(beard, [(0, (0.001,) * 3), (S[14] + 4, (0.001,) * 3), (S[14] + 10, (0.16, 0.1, 0.22)), (E(14) - 6, (0.17, 0.11, 0.42)), (E(14) - 1, (0.17, 0.11, 0.42)), (E(14), (0.001,) * 3)])
key_loc(beard, [(S[14] + 10, (YX, YY - 0.19, 1.45)), (E(14) - 6, (YX, YY - 0.21, 1.25))])
web = tube("Web", [(TBX - 0.8, TBY - 0.3, 0.72), (TBX - 0.8, TBY - 0.3, 0.2), (TBX - 0.3, TBY - 0.3, 0.72)], [0.01] * 3, white_m)
pop(web, S[14] + 18, 4, E(14))

# ---------------- line 16: a ladder against the endless stack ----------------
LDX = CX
ld = group("Ladder", (LDX, CY - 0.75, 0))
lps = []
for sx in (-0.25, 0.25):
    lps.append(tube("LdRail", [(LDX + sx, CY - 0.75, 0), (LDX + sx, CY - 0.16, 7.0)], [0.035, 0.035], wood_m))
for k in range(1, 22):
    t_ = k / 22
    lps.append(box("LdRung", (LDX, CY - 0.75 + 0.59 * t_, 7.0 * t_), (0.5, 0.04, 0.04), wood_m))
attach(lps, ld)
keyscale(ld, [(0, 0.001), (S[16] - 1, 0.001), (S[16] + 3, 1.08), (S[16] + 5, 1.0)])
for k, (dx, dz) in enumerate([(-0.9, 2.5), (0.45, 2.9)]):
    q = text(f"Q{k}", "?", (YX + dx, YY - 0.4, dz), 0.55, lab_m, extrude=0.06)
    pop(q, S[16] + 8 + 4 * k, 5)
    keyrot(q, [(S[16] + 8, (math.radians(90), 0, -0.2)), (FRAMES - 1, (math.radians(90), 0, 0.2))])
# you look up
keyrot(yd["head"], [(0, (0, 0, 0))])

# ================================ SET B: riding the stack up into space (lines 6-8) ================================
SB = Vector((5000.0, 500.0, 0.0))
skyB = bpy.data.materials.new("SkyB"); skyB.use_nodes = True
_n = skyB.node_tree.nodes; skyB.node_tree.nodes.remove(_n["Principled BSDF"])
_em = _n.new("ShaderNodeEmission"); skyB.node_tree.links.new(_em.outputs[0], _n["Material Output"].inputs["Surface"])
_em.inputs["Strength"].default_value = 1.0
f6, f7, f8 = S[6], S[7], S[8]
for f, c in [(0, (0.35, 0.62, 1.0)), (f6 + 14, (0.35, 0.62, 1.0)), (f7 + 6, (0.1, 0.16, 0.42)), (f7 + 22, (0.012, 0.018, 0.06))]:
    _em.inputs["Color"].default_value = (*c, 1); _em.inputs["Color"].keyframe_insert("default_value", frame=f)
domeB = sphere("DomeB", tuple(SB), 420.0, skyB, sub=3); domeB.visible_shadow = False
star_g = glow_mat("Star", (1, 1, 0.95), 8.0)
for i in range(220):
    v = Vector((random.gauss(0, 1), random.gauss(0, 1) + 0.6, abs(random.gauss(0, 1)) + 0.2)).normalized()
    st = sphere("StarB", tuple(SB + v * 400), random.uniform(0.8, 1.7), star_g, sub=1)
    st.visible_shadow = False
    hide_until(st, f7 + 8)
# little town at the bottom + a cloud deck
roof2 = mat("Roof2", (0.78, 0.38, 0.2), 0.7)
for k in range(14):
    a = random.uniform(0.2, 2.9); r = random.uniform(6, 30)
    hx, hy = SB.x + r * math.cos(a), SB.y + r * math.sin(a)
    box("TownH", (hx, hy, 1.0), (3, 2.4, 2.0), wall_m)
    cyl("TownR", (hx, hy, 2.6), 2.1, 1.2, roof2, r2=0.0, verts=4, rot=(0, 0, math.radians(45)))
for k in range(26):
    a = random.uniform(-0.2, 3.34); r = random.uniform(5, 40)
    x, y = SB.x + r * math.cos(a), SB.y + r * math.sin(a) + 2
    if y < SB.y - 2 and abs(x - SB.x - 3.5) < 9:
        continue
    for j in range(3):
        sphere("BCloud", (x + (j - 1) * 2.6, y, random.uniform(14, 18)), random.uniform(2.2, 3.4), cloud_m2, scale=(1.4, 0.9, 0.6), sub=2)
# the stack + the rider
ZK = [(f6, 6.0), (W(6, 0.5), 26.0), (f7, 40.0), (W(7, 0.55), 70.0), (f8, 95.0), (W(8, 0.6), 120.0), (E(8), 132.0)]
def zt(f):
    for (a, za), (b, zb) in zip(ZK, ZK[1:]):
        if a <= f <= b:
            return za + (zb - za) * (f - a) / (b - a)
    return ZK[0][1] if f < ZK[0][0] else ZK[-1][1]
bcol = column("SpaceCol", tuple(SB), 0.62, 0.28, col_m)
rider, rd = person_hair("Rider", (SB.x, SB.y, 0), mat("RShirt", (0.95, 0.3, 0.35), 0.7), mat("RPants", (0.18, 0.22, 0.38), 0.8), mat("RHair", (0.25, 0.14, 0.06), 0.8))
helmet = sphere("Helmet", (SB.x, SB.y, 1.66), 0.42, glass_m, sub=3)
attach([helmet], rider)
keyscale(helmet, [(0, 0.001), (f7 - 1, 0.001), (f7 + 3, 1.1), (f7 + 5, 1.0)])
fr_ = list(range(f6, E(8) + 1, 3))
for f in fr_:
    bcol.scale = (1, 1, zt(f)); bcol.keyframe_insert("scale", frame=f)
    rider.location = (SB.x, SB.y, zt(f)); rider.keyframe_insert("location", frame=f)
lin(bcol); lin(rider)
rA, rB = rd["arms"]
for k in range(f6, E(8), 8):    # waving
    keyrot(rB, [(k, (0, -2.4, 0)), (k + 4, (0, -2.0, 0))])
keyrot(rA, [(f6, (0, 0.5, 0))])
# airliner crossing behind (line 6)
AZ = 26.0
pl = group("Plane", (SB.x - 30, SB.y + 5, AZ))
plw = mat("PlaneW", (0.95, 0.95, 0.97), 0.4)
plb = mat("PlaneB", (0.15, 0.35, 0.85), 0.4)
pp = [cyl("Fus", (SB.x - 30, SB.y + 5, AZ), 0.85, 9.0, plw, rot=(0, math.radians(90), 0), verts=20),
      sphere("Nose", (SB.x - 25.5, SB.y + 5, AZ), 0.85, plw, scale=(1.4, 1, 1), sub=3),
      cyl("Tail", (SB.x - 35.2, SB.y + 5, AZ + 0.2), 0.85, 1.6, plw, r2=0.3, rot=(0, math.radians(-90), 0), verts=20),
      box("Wing", (SB.x - 30.3, SB.y + 5, AZ - 0.3), (2.2, 11.0, 0.18), plw),
      box("Fin", (SB.x - 35.3, SB.y + 5, AZ + 1.3), (1.6, 0.15, 2.0), plb),
      box("Stab", (SB.x - 35.4, SB.y + 5, AZ + 0.2), (1.1, 4.0, 0.12), plw),
      box("Stripe", (SB.x - 30, SB.y + 4.12, AZ - 0.1), (8.4, 0.05, 0.3), plb)]
for k in range(10):
    pp.append(box("PWin", (SB.x - 33.5 + k * 0.75, SB.y + 4.12, AZ + 0.32), (0.3, 0.05, 0.28), dark_m))
for sy in (-1, 1):
    pp.append(cyl("Eng", (SB.x - 29.6, SB.y + 5 + sy * 2.6, AZ - 0.75), 0.42, 1.6, metal_m, rot=(0, math.radians(90), 0), verts=14))
attach(pp, pl)
key_loc(pl, [(f6, (SB.x - 30, SB.y + 5, AZ)), (f7 + 4, (SB.x + 30, SB.y + 5, AZ))]); lin(pl)
# edge of space ring (line 7)
bpy.ops.mesh.primitive_torus_add(major_radius=4.0, minor_radius=0.09, location=(SB.x, SB.y, 70.0))
kr = bpy.context.object; kr.data.materials.append(glow_mat("Karman", (0.4, 0.9, 1.0), 4.0))
hide_until(kr, f7 + 2)
# the space station (line 8)
IZ = 121.0
iss = group("ISS", (SB.x - 1.0, SB.y + 6, IZ))
ip = [box("Truss", (SB.x - 1.0, SB.y + 6, IZ), (11, 0.45, 0.45), metal_m)]
for dx in (-4.8, -3.0, 3.0, 4.8):
    for sz in (-1, 1):
        ip.append(box("SPanel", (SB.x - 1.0 + dx, SB.y + 6, IZ + sz * 1.6), (1.5, 0.06, 2.6), panel_m))
for dy in (-1.2, 0, 1.2):
    ip.append(cyl("Mod", (SB.x - 1.0, SB.y + 6 + dy, IZ - 0.7), 0.42, 1.3, white_m, rot=(math.radians(90), 0, 0), verts=16))
attach(ip, iss)
key_loc(iss, [(f8, (SB.x - 3.0, SB.y + 6, IZ)), (E(8), (SB.x + 1.0, SB.y + 6, IZ))]); lin(iss)
keyrot(iss, [(f8, (0, 0, -0.15)), (E(8), (0, 0, 0.1))])

def camB(f):
    z = zt(f); u = (f - f6) / (E(8) - f6)
    cl = (SB.x + 3.5 + 2.5 * math.sin(u * 6.0), SB.y - 9.0 - 1.5 * math.cos(u * 4.0), z - 0.6)
    return cl, (SB.x, SB.y, z + 0.9)
# labels riding along (upper part of the frame)
def labB(name, body, m_, f_in, f_out, dz=4.6, maxs=1.0):
    cl, _ = camB(f_in)
    loc0 = (SB.x + 0.3, SB.y + 1.0, zt(f_in) + dz)
    t = lab3(name, body, loc0, cl, m_, f_in, f_out, maxs)
    for f in range(f_in, f_out + 1, 3):
        t.location = (SB.x + 0.3, SB.y + 1.0, zt(f) + dz); t.keyframe_insert("location", frame=f)
    lin(t)
    return t
labB("LB6", "10 BILLION BILLS", lab_m, f6 + 3, f7, dz=5.6)
labB("LB6b", "JETS: 10 KM", white_lab, W(6, 0.45), f7, dz=4.5)
labB("LB7", "EDGE OF SPACE", lab_m, f7 + 3, f8, dz=5.6)
labB("LB7b", "100 KM", white_lab, W(7, 0.45), f8, dz=4.5)
labB("LB8", "SPACE STATION", lab_m, f8 + 2, E(8), dz=5.6)
labB("LB8b", "400 KM", white_lab, W(8, 0.4), E(8), dz=4.5)

# ================================ SET C: the real proportions, Earth + orbit (lines 9, 10, 15) ================================
SC = Vector((-1.0e6, 0.0, 0.0))
ER = 63.71     # 1 unit = 100 km
space_m = glow_mat("Space", (0.012, 0.018, 0.06), 1.0)
dome = sphere("SpaceDome", tuple(SC), 6000.0, space_m, sub=3); dome.visible_shadow = False
for i in range(300):
    v = Vector((random.gauss(0, 1), abs(random.gauss(0, 1)) + 0.3, random.gauss(0, 1))).normalized()
    st = sphere("StarC", tuple(SC + v * 5800), random.uniform(8, 18), star_g, sub=1); st.visible_shadow = False
for i in range(120):
    v = Vector((random.gauss(0, 1), abs(random.gauss(0, 1)) + 0.3, random.gauss(0, 1) + 0.3)).normalized()
    st = sphere("StarC2", tuple(SC + v * 600), random.uniform(0.8, 1.8), star_g, sub=1); st.visible_shadow = False
ocean_m = mat("Ocean", (0.1, 0.35, 0.85), 0.35, emit=(0.05, 0.2, 0.6), emit_strength=0.25)
land_m = mat("Land", (0.25, 0.65, 0.25), 0.8, emit=(0.15, 0.4, 0.1), emit_strength=0.15)
ice_m = mat("Ice", (0.95, 0.97, 1.0), 0.6)
sphere("EarthBall", tuple(SC), ER, ocean_m, sub=5)
K_ = ER / 3.0
for (lat, lon, s_) in [(20, 30, 1.3), (45, 60, 1.1), (-10, 80, 0.9), (10, -60, 1.0), (40, -100, 1.2), (-25, 140, 0.8),
                       (55, 110, 1.0), (-15, -55, 0.9), (5, 20, 0.9), (30, 170, 0.7), (-30, 25, 0.7), (60, -40, 0.6),
                       (62, -95, 0.7), (35, -75, 0.6), (70, 20, 0.6)]:
    la, lo = math.radians(lat), math.radians(lon)
    d = Vector((math.cos(la) * math.cos(lo), math.cos(la) * math.sin(lo), math.sin(la)))
    c = sphere("Land", tuple(SC + d * (ER - 0.05 * K_)), s_ * K_, land_m, scale=(1, 1, 0.25), sub=3)
    c.rotation_mode = 'QUATERNION'; c.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(d)
sphere("PoleS", tuple(SC + Vector((0, 0, -(ER - 0.4 * K_)))), K_, ice_m, scale=(1.2, 1.2, 0.5), sub=3)
# atmosphere glow shell
atm = sphere("Atmo", tuple(SC), ER + 0.6, glow_mat("AtmoM", (0.35, 0.6, 1.0), 0.0), sub=5)
_am = atm.data.materials[0].node_tree
_mix = _am.nodes.new("ShaderNodeMixShader"); _tr = _am.nodes.new("ShaderNodeBsdfTransparent")
_em2 = _am.nodes["Emission"]; _em2.inputs["Strength"].default_value = 1.2
_lw = _am.nodes.new("ShaderNodeLayerWeight"); _lw.inputs["Blend"].default_value = 0.25
_am.links.new(_lw.outputs["Facing"], _mix.inputs[0]); _am.links.new(_tr.outputs[0], _mix.inputs[1]); _am.links.new(_em2.outputs[0], _mix.inputs[2])
_am.links.new(_mix.outputs[0], _am.nodes["Material Output"].inputs["Surface"])
atm.visible_shadow = False
# stack from the north pole
ccol = column("EarthCol", tuple(SC + Vector((0, 0, ER - 0.3))), 1.0, 1.0, green_lab)
H1 = 10.9
f9, f10, f15 = S[9], S[10], S[15]
keyscale(ccol, [(0, 0.001), (f9 - 1, 0.001), (f9, (0.5, 0.5, 4.45)), (W(9, 0.55), (0.5, 0.5, H1 + 0.3))])
# ISS orbit ring (400-420 km -> radius ER + 4.15) in the camera-facing plane + the station on it
OR = ER + 4.15
bpy.ops.mesh.primitive_torus_add(major_radius=OR, minor_radius=0.07, major_segments=256, location=tuple(SC), rotation=(math.radians(90), 0, 0))
ring = bpy.context.object; ring.data.materials.append(glow_mat("RingM", (0.6, 0.95, 1.0), 3.0)); ring.visible_shadow = False
iss2 = group("ISS2", tuple(SC + Vector((0, -0.2, OR))))
ip2 = [box("Truss2", tuple(SC + Vector((0, -0.2, OR))), (1.6, 0.08, 0.08), metal_m)]
for dx in (-0.65, 0.65):
    ip2.append(box("SPanel2", tuple(SC + Vector((dx, -0.2, OR))), (0.3, 0.02, 0.9), panel_m))
attach(ip2, iss2)
def orbit_pos(ang):
    return SC + Vector((OR * math.sin(ang), -0.2, OR * math.cos(ang)))
for f in range(f9, E(10) + 1, 4):
    ang = -0.12 + 0.1 * (f - f9) / (E(10) - f9)
    iss2.location = tuple(orbit_pos(ang)); iss2.keyframe_insert("location", frame=f)
    iss2.rotation_euler = (0, ang, 0); iss2.keyframe_insert("rotation_euler", frame=f)
lin(iss2)
keyscale(iss2, [(0, 1.0), (f15, 1.0), (f15 + 8, 0.001)])
keyscale(ring, [(0, 1.0), (f15 + 10, 1.0), (f15 + 18, 0.001)])
# height markers in "ISS heights" (line 10)
TOPZ = ER + H1
for k, (h, txt) in enumerate([(4.15, "1x"), (8.3, "2x"), (H1, "2.6x")]):
    mk = box("Mark", tuple(SC + Vector((0, -0.3, ER + h))), (1.6, 0.1, 0.12), lab_m)
    pop(mk, f10 + 3 + 7 * k, 3, f15)
    t = text("MarkT", txt, tuple(SC + Vector((1.9, -0.4, ER + h))), 0.95, lab_m if k == 2 else white_lab, extrude=0.06)
    t.rotation_euler = face_rot(t.location, SC + Vector((-6, -36, 69)))
    pop(t, f10 + 3 + 7 * k, 3, f15)
# line 15: in $1 bills -> 100x taller (109,000 km)
def h15(f):
    return ease(H1, 1090.0, (f - (f15 + 6)) / (E(15) - 8 - (f15 + 6)))
for f in range(f15, E(15) + 1, 3):
    h = h15(f); w = 0.5 + 0.0085 * (h - H1)
    ccol.scale = (w, w, h + 0.3); ccol.keyframe_insert("scale", frame=f)
lin(ccol)
def camC15(f):
    h = h15(f)
    cl = SC + Vector((10 + 0.18 * h, -40 - 1.05 * h, 70 + 0.3 * h))
    return tuple(cl), tuple(SC + Vector((0, 0, ER + 0.27 * h)))

lab3("LC9", "1,100 KM", tuple(SC + Vector((0, -0.5, TOPZ + 7.0))), SC + Vector((5, -30, 68)), lab_m, W(9, 0.5), f10, 2.2)
lab3("LC9b", "ISS ORBIT", tuple(SC + Vector((-7.5, -0.5, OR + 1.6))), SC + Vector((5, -36, 68)), white_lab, f9 + 4, W(9, 0.5), 1.2)
lab3("LC10", "2.6x HIGHER", tuple(SC + Vector((0, -0.5, TOPZ + 7.0))), SC + Vector((-6, -30, 69)), lab_m, f10 + 3, f15, 2.2)
t15 = lab3("LC15", "$1 BILLS: 109,000 KM", tuple(SC + Vector((0, 0, ER + 1180))), SC + Vector((10 + 196, -40 - 1144, 70 + 327)), lab_m, W(15, 0.55), FRAMES + 5, 120)
t15b = lab3("LC15b", "100x TALLER", tuple(SC + Vector((0, 0, ER + 1300))), SC + Vector((10 + 196, -40 - 1144, 70 + 327)), white_lab, W(15, 0.3), FRAMES + 5, 90)

# ---------------- views (camera, subject) per yard line; subject sits in the lower third ----------------
V = {}; V2 = {}
V[0] = ((1.8, -5.2, 2.0), (0.35, YY, 1.0));                  V2[0] = ((-0.6, -4.8, 2.2), (0.35, YY, 1.0))
V[1] = ((2.6, -8.5, 4.2), (0.0, 3.0, 0.4));                  V2[1] = ((-1.8, -9.2, 4.8), (0.0, 3.2, 0.4))
V[2] = ((1.6, -4.0, 1.9), (0.6, -0.1, 1.15));                V2[2] = ((0.2, -3.2, 1.8), (0.6, -0.1, 1.2))
V[3] = ((2.4, -4.2, 1.7), (0.45, YY, 0.75));                 V2[3] = ((-0.6, -3.8, 1.8), (0.45, YY, 0.8))
V[4] = ((3.5, -10.0, 4.0), (0.6, YY, 1.6));                  V2[4] = ((26.0, -100.0, 34.0), (1.0, 3.0, 46.0))
V[5] = V2[4];                                                 V2[5] = ((18.0, -86.0, 150.0), (1.0, 3.0, 175.0))
V[11] = ((-8.0, -44.0, 15.0), (12.0, 10.0, 6.0));            V2[11] = ((2.0, -50.0, 20.0), (13.0, 11.0, 7.0))
V[12] = ((4.0, -64.0, 24.0), (10.0, 20.0, 14.0));            V2[12] = ((70.0, -400.0, 150.0), (-35.0, 60.0, 100.0))
V[13] = ((1.8, -3.6, 1.9), (0.3, 0.1, 1.05));                V2[13] = ((-0.6, -3.6, 2.0), (0.4, 0.1, 1.05))
V[14] = ((-1.0, -3.0, 1.8), (0.4, 0.2, 1.2));                V2[14] = ((1.6, -2.8, 1.7), (0.4, 0.2, 1.2))
V[16] = ((2.6, -5.4, 1.7), (0.5, YY, 0.95));                 V2[16] = ((1.0, -6.4, 2.2), (0.5, YY, 1.6))
def LB(i, name, body, m_, size=None, f_in=None, f_out=None, Dk=0.55, end=False, v=0.3, u=0.0):
    view = V2[i] if end else V[i]
    cl = Vector(CL(view)); D = (Vector(view[1]) - cl).length * Dk
    s_ = 0.85 * fit(body, D, size if size else 1e9)
    return label(name, body, view, D, v, s_, m_, (S[i] + 3) if f_in is None else f_in,
                 E(i) if f_out is None else f_out, u)
LB(0, "L0", "$1,000,000,000,000", lab_m)
LB(1, "L1", "A MILLION x $1M", lab_m, end=True, f_in=S[1] + 6)
LB(2, "L2", "0.1 mm", lab_m, end=True, f_in=flip + 8, Dk=0.5)
LB(3, "L3", "$1 MILLION = 1.1 m", lab_m, end=True, f_in=S[3] + 12)
LB(4, "L4", "$1 BILLION = 1.1 km", lab_m, end=True, f_in=S[4] + 24, Dk=0.3)
LB(5, "L5", "x 1,000", lab_m, f_in=S[5] + 2, Dk=0.4)
LB(11, "L11", "10,000 TONS", lab_m, end=True, f_in=fh + 2, Dk=0.45)
LB(12, "L12", "SAME WEIGHT!", lab_m, end=True, f_in=S[12] + 12, Dk=0.45)
LB(13, "L13", "1 BILL / SECOND", lab_m, f_in=S[13] + 4)
LB(14, "L14", "317 YEARS!", lab_m, end=True, f_in=S[14] + 6)
LB(16, "L16", "TOP BILL?", lab_m, end=True, f_in=S[16] + 6, Dk=0.45)

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
cam_keys = []
LINF = set()
for i in range(len(S)):
    if i in (6, 7, 8):
        for f in range(S[i], E(i), 3):
            cl, tl = camB(f); cam_keys.append((f, cl, tl)); LINF.add(f)
        cl, tl = camB(E(i) - 1); cam_keys.append((E(i) - 1, cl, tl)); LINF.add(E(i) - 1)
        continue
    if i == 9:
        cam_keys += [(S[9], tuple(SC + Vector((9, -27, 64.5))), tuple(SC + Vector((0, 0, 68.6)))),
                     (E(9) - 1, tuple(SC + Vector((4, -30, 67.5))), tuple(SC + Vector((0, 0, 69.6))))]
        continue
    if i == 10:
        cam_keys += [(S[10], tuple(SC + Vector((-7, -27, 67))), tuple(SC + Vector((0, 0, 69.2)))),
                     (E(10) - 1, tuple(SC + Vector((-4, -31, 70))), tuple(SC + Vector((0, 0, 70.0))))]
        continue
    if i == 15:
        for f in range(S[15], E(15), 3):
            cl, tl = camC15(f); cam_keys.append((f, cl, tl)); LINF.add(f)
        cl, tl = camC15(E(15) - 1); cam_keys.append((E(15) - 1, cl, tl)); LINF.add(E(15) - 1)
        continue
    v = V[i]
    cam_keys.append((S[i], CL(v), v[1]))
    cam_keys.append((E(i) - 1, CL(V2[i]), V2[i][1]))
for f, cl, tl in cam_keys:
    cam.location = cl; cam.keyframe_insert("location", frame=f)
    target.location = aim(cl, tl)
    target.keyframe_insert("location", frame=f)
CUTS = tuple(S[1:])
for o_ in (cam, target):
    for fc in fcurves(o_):
        pts_ = fc.keyframe_points
        for i in range(len(pts_) - 1):
            if int(round(pts_[i].co[0])) in LINF and int(round(pts_[i + 1].co[0])) in LINF:
                pts_[i].interpolation = 'LINEAR'
            if int(round(pts_[i + 1].co[0])) in CUTS:
                pts_[i].interpolation = 'CONSTANT'
for o in bpy.data.objects:
    if o.type == 'FONT':
        o.visible_shadow = False
sc.frame_set(0)
bpy.ops.wm.save_as_mainfile(filepath=f"{HERE}/scene.blend")
print("SCENE OK", FRAMES, S)
