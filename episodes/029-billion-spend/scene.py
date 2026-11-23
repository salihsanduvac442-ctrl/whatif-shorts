# Day 29 — What if you spent $1,000 a day until a billion ran out?  Build: python3 episodes/029-billion-spend/scene.py
# Reference style: base (helpers, lawn/soil, house, garden) copied from episodes/003-lift-million-ref / 006-mantis-punch
import bpy, math, random, os, json
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
random.seed(29)
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


# =====================================================================================
# Day 29 — What if you spent $1,000 a day until a billion ran out?
# Facts used (checked 2026-11-23):
#   $1B / $1,000 a day = 1,000,000 days = ~2,738 years.  $1M lasts 1,000 days = ~2.7 years.
#   $1,000 = ten $100 bills; ~$30,000 a month (price of a typical new car is in that range).
#   80 years x 365.25 x $1,000 = ~$29.2M = ~2.9% of $1B.
#   Starting today (late 2026) -> broke around the year 4764.  To be broke now -> start ~712 BC
#   (Rome: traditionally founded 753 BC, a small hilltop village at the time).
#   $1B at 4% a year = $40M/yr = ~$110,000 a day > $1,000 a day -> never runs out.
#   $1B in $100 bills = 10 million bills, ~10 t, ~11 m3 -> a ~2.2 m cube.
# =====================================================================================
ease_in = lambda f0, f1, f: max(0.0, min(1.0, (f - f0) / max(1, f1 - f0)))
YX, YY = 0.0, 0.5
hair_m = mat("YouHair", (0.25, 0.14, 0.06), 0.8)
you, yd = person_hair("You", (YX, YY, 0), mat("YouShirt", (0.95, 0.3, 0.35), 0.7), mat("YouPants", (0.18, 0.22, 0.38), 0.8), hair_m)
armL, armR = yd["arms"]
def arms(fs):
    for f, up in fs:
        a = math.radians(150) * up
        keyrot(armL, [(f, (0, a, 0))]); keyrot(armR, [(f, (0, -a, 0))])
arms([(0, 0), (5, 0.8), (S[1] - 2, 0.8), (S[1] + 2, 0), (S[2], 0), (S[2] + 6, 0.45), (E(2) - 2, 0.45), (E(2), 0),
      (S[3], 0), (S[3] + 14, 0), (S[3] + 18, 1), (E(3) - 1, 1), (E(3), 0),
      (S[10], 0), (W(10, 0.7), 0), (W(10, 0.7) + 4, 0.35), (E(10) - 1, 0.35), (E(10), 0),
      (S[15], 0), (S[15] + 6, 1), (E(15) - 1, 1), (E(15), 0), (S[16], 0), (S[16] + 5, 0.55)])
ycol_hold = keyrot(yd["head"], [(0, (0, 0, 0))])

# ---------------- the billion: a ~2.2 m cube made of 1,000 $1M bricks ----------------
CX, CY = 2.45, 1.45
NB, BS, GAP, EXP = 10, 0.215, 0.224, 0.4
cubeg = group("BillionCube", (CX, CY, 0))
life_m = stripe_mat("LifeCash", (0.3, 0.68, 0.25), (0.18, 0.48, 0.15), axis="Z", freq=40.0, thresh=0.3)
_lb = life_m.node_tree.nodes["Principled BSDF"]
_lmx = [n for n in life_m.node_tree.nodes if n.type == 'MIX'][0]
for f, c1, c2, em in [(0, (0.3, 0.68, 0.25), (0.18, 0.48, 0.15), 0.0), (S[6] + 2, (0.3, 0.68, 0.25), (0.18, 0.48, 0.15), 0.0),
                      (S[6] + 7, (1.0, 0.25, 0.2), (0.8, 0.1, 0.08), 0.6), (S[8] + 2, (1.0, 0.25, 0.2), (0.8, 0.1, 0.08), 0.6),
                      (S[8] + 6, (0.3, 0.68, 0.25), (0.18, 0.48, 0.15), 0.0)]:
    _lmx.inputs[6].default_value = (*c1, 1); _lmx.inputs[6].keyframe_insert("default_value", frame=f)
    _lmx.inputs[7].default_value = (*c2, 1); _lmx.inputs[7].keyframe_insert("default_value", frame=f)
    _lb.inputs["Emission Color"].default_value = (1.0, 0.2, 0.1, 1); _lb.inputs["Emission Strength"].default_value = em
    _lb.inputs["Emission Strength"].keyframe_insert("default_value", frame=f)
BMESH = []
for m_ in (cash_m, life_m):
    t_ = box("BrickT", (0, 0, -50), (BS, BS, BS), m_)
    BMESH.append(t_.data); bpy.data.objects.remove(t_)
bricks = []
life = []
order = 0
for iz in range(NB - 1, -1, -1):
    for iy in range(NB):
        for ix in range(NB):
            tight = (CX + (ix - 4.5) * GAP, CY + (iy - 4.5) * GAP, BS / 2 + iz * GAP)
            expl = (CX + (ix - 4.5) * EXP, CY + (iy - 4.5) * EXP, BS / 2 + iz * EXP)
            is_life = order < 29
            b = bpy.data.objects.new("Brick", BMESH[1 if is_life else 0]); sc.collection.objects.link(b); b.location = tight
            bricks.append((b, tight, expl, is_life, ix, iy, iz))
            order += 1
attach([b[0] for b in bricks], cubeg)
for b, tight, expl, is_life, ix, iy, iz in bricks:
    d0 = S[5] + 1 + int((9 - iz) * 0.6 + (ix + iy) * 0.25)
    keys = [(d0, tight), (d0 + 7, expl)]
    if is_life:
        up = (expl[0], expl[1] - 0.2, expl[2] + 1.3)
        f6 = S[6] + 2 + (ix % 5)
        keys += [(f6, expl), (f6 + 8, up), (S[8], up)]
    else:
        keys += [(S[8], expl)]
    keys += [(S[8] + 8, tight)]
    key_loc(b, keys)
# front + side band labels on the cube
cube_lab = text("CubeT", "$1 BILLION", (CX, CY - 1.13, 1.55), 0.36, white_lab, extrude=0.03)
cube_lab2 = text("CubeT2", "10 TONS", (CX, CY - 1.13, 1.05), 0.26, lab_m, extrude=0.03)
attach([cube_lab, cube_lab2], cubeg)
for t_ in (cube_lab, cube_lab2):
    keyscale(t_, [(0, 1.0), (S[5], 1.0), (S[5] + 3, 0.001), (S[8] + 8, 0.001), (S[8] + 11, 1.0)])
# cube group: slams down on line 1, drains on line 10, refills on line 11, grows on line 15
fh = S[1] + 7
keyscale(cubeg, [(0, 0.001), (S[1] - 1, 0.001), (S[1], 1.0), (fh, 1.0), (fh + 2, (1.08, 1.08, 0.86)), (fh + 5, 1.0),
                 (W(10, 0.25), 1.0), (E(10) - 3, (1, 1, 0.02)), (S[11] + 3, (1, 1, 0.02)), (W(11, 0.8), 1.0),
                 (S[15] + 4, 1.0), (E(15) - 2, 1.3)])
key_loc(cubeg, [(S[1], (CX, CY, 14.0)), (fh, (CX, CY, 0.0))])
for k in range(16):
    a = k / 16 * 6.283
    d_ = sphere("Dust", (CX + 1.4 * math.cos(a), CY + 1.4 * math.sin(a), 0.2), 0.32, dust_m, sub=1)
    key_loc(d_, [(fh, (CX + 1.4 * math.cos(a), CY + 1.4 * math.sin(a), 0.2)), (fh + 12, (CX + 2.6 * math.cos(a), CY + 2.6 * math.sin(a), 0.6))])
    pop(d_, fh, 3, fh + 13)

# ---------------- line 0: $1,000 of bills thrown in the air ----------------
def flybill(name, p0, p1, f0, f1, f_out, arc=0.8):
    b = box(name, p0, (0.42, 0.18, 0.012), bill_m)
    mid = ((p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2, max(p0[2], p1[2]) + arc)
    key_loc(b, [(f0, p0), ((f0 + f1) // 2, mid), (f1, p1)])
    keyrot(b, [(f0, (0, 0, random.uniform(0, 6))), (f1, (random.uniform(-2, 2), random.uniform(-2, 2), random.uniform(0, 6)))])
    pop(b, f0, 2, f_out)
    return b
for k in range(30):
    p = (YX + random.uniform(-2.2, 2.2), YY + random.uniform(-0.8, 1.4), random.uniform(2.6, 5.5))
    st = random.randint(0, 10)
    b = box("RainBill", p, (0.42, 0.18, 0.012), bill_m)
    b.rotation_euler = (random.uniform(-1, 1), random.uniform(-1, 1), random.uniform(0, 6)); b.keyframe_insert("rotation_euler", frame=st)
    b.rotation_euler = (0, 0, random.uniform(0, 6)); b.keyframe_insert("rotation_euler", frame=st + 18)
    key_loc(b, [(st, p), (st + 18, (p[0], p[1], random.uniform(0.05, 0.1)))])
    hide_until(b, st); gone_at(b, S[1] + 1, 2)

# ---------------- line 2: ten $100 bills fly from the cube into a fan over your head ----------------
for k in range(10):
    ang = math.radians(-60 + k * 13.3)
    p1 = (YX + 0.95 * math.sin(ang), YY - 0.35, 2.15 + 0.55 * math.cos(ang))
    b = flybill("Fan", (CX - 0.3, CY - 0.6, 2.3), p1, S[2] + 2 + k * 2, S[2] + 10 + k * 2, E(2), arc=0.9)
    b.rotation_euler = (math.radians(90), -ang, 0); b.keyframe_insert("rotation_euler", frame=S[2] + 10 + k * 2)
    b.scale = (1.4, 1.4, 1.4)
    keyscale(b, [(S[2] + 10 + k * 2, 1.4), (E(2) - 3, 1.4)])

# ---------------- line 3: a brand-new car every month ----------------
carx = -1.75
car = group("Car", (carx, -0.45, 0))
car_m = mat("CarBody", (0.15, 0.45, 0.95), 0.3, metal=0.3)
tyre_m = mat("Tyre", (0.06, 0.06, 0.07), 0.8)
cp = [box("CarBody", (carx, -0.45, 0.55), (2.3, 1.05, 0.55), car_m, bevel=0.12),
      box("CarCab", (carx - 0.1, -0.45, 1.05), (1.25, 0.95, 0.5), car_m, bevel=0.1),
      box("CarWin", (carx - 0.1, -0.95, 1.06), (1.05, 0.04, 0.36), dark_m),
      box("CarWinF", (carx + 0.53, -0.45, 1.06), (0.04, 0.85, 0.36), dark_m),
      box("CarLight", (carx + 1.16, -0.75, 0.6), (0.04, 0.2, 0.12), lab_m),
      box("CarLight", (carx + 1.16, -0.15, 0.6), (0.04, 0.2, 0.12), lab_m),
      box("Bow", (carx - 0.1, -0.45, 1.33), (0.18, 1.0, 0.06), red_lab),
      box("Bow2", (carx - 0.1, -0.45, 1.33), (1.3, 0.18, 0.06), red_lab),
      sphere("BowK", (carx - 0.1, -0.45, 1.42), 0.16, red_lab, scale=(1.4, 1, 0.8), sub=2)]
for dx in (-0.72, 0.72):
    for dy in (-0.98, 0.08):
        cp.append(cyl("Wheel", (carx + dx, -0.45 + dy + 0.45, 0.3), 0.3, 0.22, tyre_m, rot=(math.radians(90), 0, 0), verts=18))
attach(cp, car)
key_loc(car, [(S[3], (carx - 9, -0.45, 0)), (S[3] + 13, (carx, -0.45, 0))])
keyscale(car, [(0, 0.001), (S[3] - 1, 0.001), (S[3], 1.0), (E(3) - 2, 1.0), (E(3), 0.001)])
burst((carx, -1.1, 1.5), S[3] + 14, n=12, r=0.9, size=0.07)

# ---------------- line 4: a $1M stack (1.1 m) melts away in under 3 years ----------------
MX, MY = -1.1, -0.25
mcol = column("MillionCol", (MX, MY, 0), 0.62, 0.28, col_m)
keyscale(mcol, [(0, 0.001), (S[4] - 1, 0.001), (S[4], (1, 1, 0.02)), (S[4] + 6, (1, 1, 1.09)), (W(4, 0.35), (1, 1, 1.09)),
                (E(4) - 3, (1, 1, 0.02)), (E(4), 0.001)])
mtop = text("MTop", "$1M", (MX, MY - 0.16, 0.8), 0.24, white_lab, extrude=0.02)
keyscale(mtop, [(0, 0.001), (S[4] + 3, 0.001), (S[4] + 6, 1.0), (W(4, 0.35), 1.0), (W(4, 0.5), 0.001)])
for k in range(16):
    f0 = W(4, 0.35) + k
    b = flybill("Spend", (MX, MY, 1.0 - 0.06 * k), (MX + random.uniform(-2.5, 1.0), MY + random.uniform(-0.4, 2), random.uniform(3.5, 5)),
                f0, f0 + 10, f0 + 11, arc=0.5)

# ---------------- line 6: 80 years -> you turn grey (the 29 red bricks lift out) ----------------
hc = hair_m.node_tree.nodes["Principled BSDF"].inputs["Base Color"]
for f, c in [(0, (0.25, 0.14, 0.06, 1)), (S[6] + 4, (0.25, 0.14, 0.06, 1)), (S[6] + 18, (0.88, 0.88, 0.9, 1)), (E(7) - 1, (0.88, 0.88, 0.9, 1)), (E(7), (0.25, 0.14, 0.06, 1))]:
    hc.default_value = c; hc.keyframe_insert("default_value", frame=f)
beard = sphere("Beard", (YX, YY - 0.17, 1.38), 1.0, mat("BeardM", (0.92, 0.92, 0.94), 0.8), scale=(0.001,) * 3, sub=3)
keyscale(beard, [(0, (0.001,) * 3), (S[6] + 4, (0.001,) * 3), (S[6] + 12, (0.16, 0.1, 0.22)), (E(6) - 4, (0.17, 0.11, 0.36)), (E(7) - 1, (0.17, 0.11, 0.36)), (E(7), (0.001,) * 3)])
key_loc(beard, [(S[6] + 12, (YX, YY - 0.19, 1.45)), (E(6) - 4, (YX, YY - 0.21, 1.3))])
cane = tube("Cane", [(YX + 0.45, YY - 0.1, 0.0), (YX + 0.45, YY - 0.1, 0.85), (YX + 0.3, YY - 0.1, 0.95)], [0.03] * 3, wood_m)
keyscale(cane, [(0, 0.001), (S[6] + 10, 0.001), (S[6] + 13, 1.0), (E(7) - 1, 1.0), (E(7), 0.001)])

# ---------------- line 8: a flip calendar racing through days ----------------
KX, KY = -1.35, -0.1
calg = group("Calendar", (KX, KY, 0))
calp = [box("CalStand", (KX, KY + 0.1, 0.55), (0.12, 0.12, 1.1), dark_m),
        box("CalBack", (KX, KY + 0.05, 1.55), (1.35, 0.08, 1.2), white_m, bevel=0.03),
        box("CalTop", (KX, KY - 0.02, 2.06), (1.4, 0.16, 0.24), red_m, bevel=0.03),
        text("CalTt", "DAY", (KX, KY - 0.11, 2.06), 0.18, white_lab)]
attach(calp, calg)
keyscale(calg, [(0, 0.001), (S[8] - 1, 0.001), (S[8] + 3, 1.1), (S[8] + 5, 1.0), (E(9) - 1, 1.0), (E(9), 0.001)])
nums = ["1", "2", "3", "10", "100", "1,000", "10K", "100K", "500K", "999,999"]
pages = []
for k, nm in enumerate(nums):
    py_ = KY - 0.03 - 0.02 * (len(nums) - k)
    pg = group(f"Page{k}", (KX, py_, 1.95))
    pz = [box(f"PageB{k}", (KX, py_, 1.45), (1.25, 0.012, 1.0), white_m),
          text(f"PageT{k}", nm, (KX, py_ - 0.008, 1.42), 0.42 if len(nm) < 5 else 0.26, dark_m)]
    attach(pz, pg)
    pages.append(pg)
dur8 = E(8) - S[8] - 4
for k, pg in enumerate(pages):
    f0 = S[8] + 4 + int(dur8 * (k / len(pages)))
    if k == len(pages) - 1:
        continue
    keyrot(pg, [(f0, (0, 0, 0)), (f0 + 3, (math.radians(-160), 0, 0))])
    keyscale(pg, [(0, 0.001), (S[8] - 1, 0.001), (S[8] + 3, 1.0), (f0 + 3, 1.0), (f0 + 4, 0.001)])
final = text("CalFinal", "1,000,000", (KX, KY - 0.3, 1.45), 0.25, red_m)
keyscale(final, [(0, 0.001), (E(8) - 2, 0.001), (E(8), 1.0), (E(9) - 1, 1.0), (E(9), 0.001)])
pages[-1]  # last page ("999,999") stays until the end, covered by the final number
keyscale(pages[-1], [(0, 0.001), (S[8] - 1, 0.001), (S[8] + 3, 1.0), (E(8) - 3, 1.0), (E(8) - 2, 0.001)])

# ---------------- line 9: the sun whips across the sky, centuries pass (hourglass flips) ----------------
sun_m = glow_mat("SunM", (1.0, 0.85, 0.3), 6.0)
sunb = sphere("SunBall", (0, 40, 10), 2.2, sun_m, sub=3); sunb.visible_shadow = False
for f in range(S[9], E(9) + 1, 2):
    u = ((f - S[9]) / 12.0) % 1.0
    sunb.location = (-26 + 52 * u, 46, 4 + 16 * math.sin(math.pi * u)); sunb.keyframe_insert("location", frame=f)
keyscale(sunb, [(0, 0.001), (S[9] - 1, 0.001), (S[9], 1.0), (E(9) - 1, 1.0), (E(9), 0.001)])
lin(sunb)
HGX, HGY = 0.95, -0.5
hg = group("Hourglass", (HGX, HGY, 1.0))
sand_m = mat("Sand", (0.95, 0.78, 0.35), 0.8)
hgp = [box("HgTop", (HGX, HGY, 1.62), (0.75, 0.75, 0.08), wood_m), box("HgBot", (HGX, HGY, 0.38), (0.75, 0.75, 0.08), wood_m),
       cyl("HgG1", (HGX, HGY, 1.3), 0.3, 0.6, glass_m, r2=0.04, verts=20), cyl("HgG2", (HGX, HGY, 0.7), 0.04, 0.6, glass_m, r2=0.3, verts=20),
       cyl("HgS1", (HGX, HGY, 1.2), 0.18, 0.25, sand_m, r2=0.03, verts=16), cyl("HgS2", (HGX, HGY, 0.52), 0.26, 0.22, sand_m, r2=0.02, verts=16)]
for dx in (-0.3, 0.3):
    hgp.append(cyl("HgPost", (HGX + dx, HGY - 0.3, 1.0), 0.03, 1.24, wood_m, verts=8))
attach(hgp, hg)
keyscale(hg, [(0, 0.001), (S[9] - 1, 0.001), (S[9] + 3, 1.1), (S[9] + 5, 1.0), (E(9) - 1, 1.0), (E(9), 0.001)])
for k in range(5):
    f0 = S[9] + 5 + k * 6
    keyrot(hg, [(f0, (0, math.pi * k, 0)), (f0 + 3, (0, math.pi * (k + 1), 0))])

# ---------------- line 10: the year ~4764 (future towers + flying car), the cube drains ----------------
fut_m = mat("Future", (0.85, 0.9, 0.98), 0.25, metal=0.5)
ring_m = glow_mat("FutRing", (0.3, 0.95, 1.0), 4.0)
towers = []
for (tx, ty, th, tr) in [(-9, 30, 22, 2.0), (-1.5, 36, 30, 2.4), (8, 31, 18, 1.8), (15, 38, 26, 2.2)]:
    tg = group("FTower", (tx, ty, 0))
    tp = [cyl("FTb", (tx, ty, th / 2), tr, th, fut_m, r2=tr * 0.6, verts=20), sphere("FTtop", (tx, ty, th + 0.4), tr * 0.9, fut_m, scale=(1, 1, 0.5), sub=2)]
    for z in range(3, int(th), 4):
        bpy.ops.mesh.primitive_torus_add(major_radius=tr * (1 - 0.4 * z / th) + 0.12, minor_radius=0.14, location=(tx, ty, z))
        r_ = bpy.context.object; r_.data.materials.append(ring_m); tp.append(r_)
    attach(tp, tg)
    keyscale(tg, [(0, 0.001), (S[10] - 1, 0.001), (S[10], (1, 1, 0.02)), (S[10] + 12, (1, 1, 1.05)), (S[10] + 15, 1.0),
                  (E(10) - 1, 1.0), (S[11] + 10, (1, 1, 0.02)), (S[11] + 11, 0.001)])
ufo = group("FlyCar", (-14, 6, 5.5))
up_ = [sphere("UfoB", (-14, 6, 5.5), 1.0, fut_m, scale=(1.6, 1.0, 0.35), sub=3), sphere("UfoD", (-14, 6, 5.85), 0.55, glass_m, sub=3)]
for k in range(6):
    a = k / 6 * 6.283
    up_.append(sphere("UfoL", (-14 + 1.45 * math.cos(a), 6 + 0.9 * math.sin(a), 5.45), 0.12, ring_m, sub=1))
attach(up_, ufo)
key_loc(ufo, [(S[10], (-14, 6, 5.5)), (E(10), (16, 2, 6.5))]); lin(ufo)
keyscale(ufo, [(0, 0.001), (S[10] - 1, 0.001), (S[10], 1.0), (E(10), 1.0), (E(10) + 1, 0.001)])
for k in range(22):
    f0 = W(10, 0.25) + k
    flybill("Drain", (CX + random.uniform(-0.8, 0.8), CY + random.uniform(-0.8, 0.5), 2.0 * max(0.05, 1 - k / 22)),
            (CX + random.uniform(-4, 3), CY + random.uniform(-2, 3), random.uniform(3, 5.5)), f0, f0 + 9, f0 + 10, arc=0.6)
pocket = [text("Q10", "$0", (YX - 0.1, YY - 0.4, 2.45), 0.5, red_lab, extrude=0.05)]
pop(pocket[0], W(10, 0.75), 4, E(10))

# ---------------- line 11: rewind clock ----------------
CKX, CKY, CKZ = -1.35, -0.1, 1.6
ck = group("Clock", (CKX, CKY, CKZ))
ckp = [cyl("CkFace", (CKX, CKY, CKZ), 0.75, 0.08, white_m, rot=(math.radians(90), 0, 0), verts=32),
       cyl("CkRim", (CKX, CKY + 0.03, CKZ), 0.84, 0.08, blue_lab, rot=(math.radians(90), 0, 0), verts=32),
       cyl("CkPost", (CKX, CKY + 0.05, CKZ / 2 - 0.4), 0.05, CKZ - 0.8, dark_m)]
for k in range(12):
    a = k / 12 * 6.283
    ckp.append(box("CkTick", (CKX + 0.62 * math.sin(a), CKY - 0.05, CKZ + 0.62 * math.cos(a)), (0.06, 0.02, 0.13), dark_m, rot=(0, a, 0)))
attach(ckp, ck)
hand = group("CkHand", (CKX, CKY - 0.07, CKZ))
attach([box("CkHandB", (CKX, CKY - 0.07, CKZ + 0.27), (0.06, 0.02, 0.56), red_m)], hand)
for o_ in (ck, hand):
    keyscale(o_, [(0, 0.001), (S[11] - 1, 0.001), (S[11] + 3, 1.1), (S[11] + 5, 1.0), (E(11) - 1, 1.0), (E(11), 0.001)])
keyrot(hand, [(S[11], (0, 0, 0)), (E(11), (0, -6.283 * 4, 0))]); lin(hand)
for k in range(3):     # rewind arrows
    a0 = k / 3 * 6.283
    arr = cyl("RwArr", (CKX + 1.05 * math.sin(a0), CKY - 0.1, CKZ + 1.05 * math.cos(a0)), 0.13, 0.3, lab_m, r2=0.0, verts=10,
              rot=(0, a0 - math.pi / 2, 0))
    pop(arr, S[11] + 4 + 2 * k, 3, E(11))

# ---------------- line 14-15: the bank (4% interest) feeding the cube ----------------
BKX, BKY = -2.2, 3.6
bank = group("Bank", (BKX, BKY, 0))
bank_m = mat("BankM", (0.93, 0.9, 0.84), 0.7)
bp = [box("BankBody", (BKX, BKY + 0.4, 1.3), (3.2, 2.0, 2.6), bank_m),
      box("BankStep", (BKX, BKY - 0.9, 0.12), (3.8, 0.8, 0.24), bank_m),
      box("BankStep2", (BKX, BKY - 0.75, 0.32), (3.5, 0.6, 0.18), bank_m),
      box("BankFrieze", (BKX, BKY - 0.6, 2.75), (3.7, 0.9, 0.4), bank_m),
      box("BankDoor", (BKX, BKY - 0.62, 1.05), (0.8, 0.06, 1.4), mat("BankDoorM", (0.35, 0.25, 0.15), 0.6)),
      text("BankT", "BANK", (BKX, BKY - 1.07, 2.75), 0.32, dark_m)]
for dx in (-1.4, -0.75, 0.75, 1.4):
    bp.append(cyl("BankCol", (BKX + dx, BKY - 0.75, 1.5), 0.15, 2.2, bank_m, verts=14))
ped = cyl("BankPed", (BKX, BKY - 0.2, 3.25), 2.1, 1.9, roof_m, r2=0.0, verts=3, rot=(math.radians(90), 0, math.radians(0)))
ped.scale = (1.0, 0.55, 1.0); bp.append(ped)
sign = text("BankPct", "4%", (BKX, BKY - 0.9, 4.75), 0.8, green_lab, extrude=0.08)
bp.append(sign)
attach(bp, bank)
keyscale(bank, [(0, 0.001), (S[14] - 1, 0.001), (S[14], (1, 1, 0.02)), (S[14] + 8, (1, 1, 1.08)), (S[14] + 11, 1.0)])
for k in range(30):     # line 15: money streams from the bank into the cube
    f0 = S[15] + 3 + k * 2
    if f0 + 12 > FRAMES - 2:
        break
    flybill("Interest", (BKX + random.uniform(-0.4, 0.4), BKY - 0.8, 1.2), (CX + random.uniform(-0.6, 0.6), CY + random.uniform(-0.5, 0.5), 2.6),
            f0, f0 + 11, f0 + 12, arc=1.4)
for k, (dx, dz) in enumerate([(-0.9, 2.5), (0.45, 2.9)]):
    q = text(f"Q{k}", "?", (YX + dx, YY - 0.4, dz), 0.55, lab_m, extrude=0.06)
    pop(q, S[16] + 8 + 4 * k, 5)
    keyrot(q, [(S[16] + 8, (math.radians(90), 0, -0.2)), (FRAMES - 1, (math.radians(90), 0, 0.2))])

# ================================ SET B: ~700 BC, Rome is a tiny village (lines 12-13) ================================
BX = 3000.0
wild_m = grass_m.copy()
for n in wild_m.node_tree.nodes:
    if n.type == 'MIX' and n.data_type == 'RGBA' and n.blend_type == 'MIX':
        if tuple(n.inputs[6].default_value)[:3] == (0.22, 0.5, 0.12) or abs(n.inputs[6].default_value[0] - 0.22) < 1e-3:
            n.inputs[6].default_value = (0.36, 0.58, 0.18, 1); n.inputs[7].default_value = (0.44, 0.66, 0.22, 1)
box("GroundB", (BX, 25.9, -6.0), (90, 55.0, 12.0), wild_m)
for i in range(16):
    sphere("PebB", (BX + random.uniform(-40, 40), FRONT_Y - 0.02, random.uniform(-5.6, -0.6)), random.uniform(0.12, 0.3),
           stone_m, scale=(1.3, 0.5, 0.8), sub=1, smooth=False)
for (hx, hy, hr, hz) in [(-20, 46, 18, 7), (8, 52, 22, 9), (30, 44, 16, 6), (-40, 40, 14, 5)]:
    sphere("Hill", (BX + hx, hy, 0), hr, mat("HillM", (0.32, 0.55, 0.2), 0.9), scale=(1.4, 1, hz / hr), sub=3)
roman = person_hair("Roman", (BX, YY, 0), mat("Toga", (0.97, 0.95, 0.9), 0.7), mat("TogaL", (0.95, 0.93, 0.88), 0.7), mat("RHair", (0.12, 0.08, 0.05), 0.8))
rarm = roman[1]["arms"]
keyrot(rarm[0], [(S[12], (0, 0, 0)), (S[12] + 6, (0, 1.6, 0))]); keyrot(rarm[1], [(S[12], (0, 0, 0)), (S[12] + 6, (0, -0.6, 0))])
wreath = tube("Wreath", [(BX - 0.24, YY, 1.8), (BX, YY - 0.25, 1.86), (BX + 0.24, YY, 1.8)], [0.04] * 3, mat("Laurel", (0.25, 0.6, 0.2), 0.8))
BCX = BX + CX
cb = box("CubeB", (BCX, CY, 1.12), (2.24, 2.24, 2.24), cash_m, bevel=0.03)
for dx in (-0.6, 0.6):
    box("CubeBBand", (BCX + dx, CY, 1.12), (0.25, 2.27, 2.27), band_m)
tB = text("CubeBT", "$1 BILLION", (BCX, CY - 1.15, 1.55), 0.36, white_lab, extrude=0.03)
straw_m = mat("Straw", (0.78, 0.6, 0.3), 0.9)
mud_m = mat("Mud", (0.72, 0.55, 0.38), 0.9)
for (hx, hy) in [(-5.5, 7), (-1.5, 10), (3.5, 8.5), (7.5, 11), (-4, 14), (2, 15), (9, 16), (-8.5, 12)]:
    cyl("HutW", (BX + hx, hy, 0.65), 1.2, 1.3, mud_m, verts=16)
    cyl("HutR", (BX + hx, hy, 1.85), 1.55, 1.3, straw_m, r2=0.08, verts=16)
    box("HutD", (BX + hx, hy - 1.18, 0.5), (0.5, 0.08, 0.9), dark_m)
for k in range(24):    # wooden palisade
    x = BX - 11 + k * 0.95
    cyl("Post", (x, 5.0, 0.55), 0.09, 1.1, wood_m, r2=0.05, verts=6)
box("Rail", (BX - 0.1, 5.0, 0.7), (22.0, 0.06, 0.08), wood_m)
wool_m = mat("Wool", (0.97, 0.96, 0.92), 0.9)
for (sx_, sy_) in [(-6, 3.0), (-3.2, 2.6), (5.8, 3.2), (7.4, 2.4)]:
    sphere("Sheep", (BX + sx_, sy_, 0.45), 0.42, wool_m, scale=(1.3, 0.9, 0.8), sub=2)
    sphere("SheepH", (BX + sx_ + 0.55, sy_, 0.55), 0.17, dark_m, sub=2)
for (x, y) in [(-14, 12), (-12, 22), (13, 20), (16, 9), (-17, 6)]:
    tree(BX + x, y, random.uniform(3.0, 4.0), random.uniform(1.3, 1.7))
smoke_m = mat("Smoke", (0.85, 0.85, 0.85), 0.9)
for k in range(5):
    s_ = sphere("Smoke", (BX + 3.5, 8.5, 2.8 + k * 0.6), 0.3 + k * 0.08, smoke_m, sub=2)

# ---------------- views (camera, subject) per line; subject sits in the lower third ----------------
V = {}; V2 = {}
V[0] = ((1.5, -5.4, 2.0), (0.3, YY, 1.0));                   V2[0] = ((-0.9, -4.9, 2.2), (0.3, YY, 1.0))
V[1] = ((4.5, -8.0, 3.0), (1.4, 1.0, 0.9));                  V2[1] = ((-0.5, -8.8, 3.5), (1.4, 1.0, 0.9))
V[2] = ((1.8, -4.6, 2.2), (0.6, YY, 1.5));                   V2[2] = ((-0.6, -4.2, 2.2), (0.4, YY, 1.5))
V[3] = ((1.6, -6.8, 2.4), (-1.0, 0.0, 0.8));                 V2[3] = ((-3.2, -6.2, 2.4), (-0.8, 0.0, 0.8))
V[4] = ((0.9, -4.6, 1.9), (-0.7, 0.1, 0.8));                 V2[4] = ((-2.4, -4.4, 2.2), (-0.7, 0.1, 0.8))
V[5] = ((5.5, -7.0, 3.0), (2.2, 1.3, 1.4));                  V2[5] = ((0.8, -8.0, 3.5), (2.2, 1.3, 1.4))
V[6] = ((-1.6, -7.0, 2.6), (1.2, 1.0, 1.4));                 V2[6] = ((2.2, -7.6, 3.0), (1.3, 1.0, 1.4))
V[7] = ((4.6, -6.6, 3.4), (1.6, 1.1, 1.6));                  V2[7] = ((1.2, -8.4, 3.8), (1.6, 1.1, 1.6))
V[8] = ((0.6, -4.8, 2.0), (-0.9, 0.2, 1.2));                 V2[8] = ((-2.6, -4.6, 2.2), (-0.9, 0.2, 1.2))
V[9] = ((2.4, -7.2, 3.0), (0.4, 0.3, 1.1));                 V2[9] = ((-1.0, -8.2, 3.4), (0.4, 0.3, 1.1))
V[10] = ((4.0, -12.5, 4.0), (1.0, 1.4, 1.0));                V2[10] = ((-1.0, -13.5, 4.6), (1.0, 1.4, 1.0))
V[11] = ((-2.4, -6.0, 2.2), (0.0, 0.6, 1.1));                V2[11] = ((1.6, -6.6, 2.6), (0.4, 0.8, 1.1))
V[12] = ((BX + 3.6, -7.0, 2.4), (BX + 1.2, 1.0, 1.0));      V2[12] = ((BX - 0.6, -7.6, 2.8), (BX + 1.2, 1.0, 1.0))
V[13] = ((BX - 3.0, -13.0, 4.5), (BX + 0.5, 3.0, 1.0));     V2[13] = ((BX + 3.0, -14.0, 5.0), (BX + 0.5, 3.0, 1.0))
V[14] = ((2.6, -8.0, 2.8), (-0.4, 1.8, 1.2));                V2[14] = ((-2.4, -8.8, 3.2), (-0.4, 1.8, 1.2))
V[15] = ((-3.6, -9.6, 3.2), (0.3, 1.8, 1.4));                V2[15] = ((4.4, -11.0, 4.0), (0.6, 1.8, 1.4))
V[16] = ((2.8, -5.8, 2.0), (0.8, 0.8, 1.1));                 V2[16] = ((0.6, -7.4, 2.6), (0.8, 0.8, 1.2))
def LB(i, name, body, m_, size=None, f_in=None, f_out=None, Dk=0.55, end=False, v=0.3, u=0.0):
    view = V2[i] if end else V[i]
    cl = Vector(CL(view)); D = (Vector(view[1]) - cl).length * Dk
    s_ = 0.85 * fit(body, D, size if size else 1e9)
    return label(name, body, view, D, v, s_, m_, (S[i] + 3) if f_in is None else f_in,
                 E(i) if f_out is None else f_out, u)
LB(0, "L0", "$1,000 A DAY", lab_m, Dk=0.8)
LB(1, "L1", "$1,000,000,000", lab_m, end=True, f_in=fh + 1)
LB(2, "L2", "10 x $100", lab_m, end=True, f_in=S[2] + 10)
LB(3, "L3", "$30K / MONTH", lab_m, end=True, f_in=S[3] + 13)
LB(4, "L4", "$1M = 2.7 YEARS", lab_m, end=True, f_in=S[4] + 8)
LB(5, "L5", "1,000 x $1M", lab_m, end=True, f_in=S[5] + 8)
LB(6, "L6", "80 YEARS = $29M", red_lab, end=True, f_in=S[6] + 10)
LB(7, "L7", "ONLY 2.9%!", lab_m, f_in=S[7] + 2)
LB(8, "L8", "1,000,000 DAYS", lab_m, end=True, f_in=S[8] + 4)
LB(9, "L9", "2,738 YEARS", lab_m, f_in=S[9] + 3)
LB(10, "L10", "YEAR 4764", blue_lab, f_in=S[10] + 8, Dk=0.85)
LB(11, "L11", "REWIND!", lab_m, f_in=S[11] + 3)
LB(12, "L12", "~700 BC", lab_m, f_in=S[12] + 3, Dk=0.85)
LB(13, "L13", "ROME", lab_m, f_in=S[13] + 3, Dk=0.85)
LB(14, "L14", "4% A YEAR", green_lab, end=True, f_in=S[14] + 8)
LB(15, "L15", "+$110K / DAY", green_lab, f_in=S[15] + 4, Dk=0.7)
LB(16, "L16", "BUY FIRST?", lab_m, end=True, f_in=S[16] + 6, Dk=0.45)

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
for i in range(len(S)):
    cam_keys.append((S[i], CL(V[i]), V[i][1]))
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
            if int(round(pts_[i + 1].co[0])) in CUTS:
                pts_[i].interpolation = 'CONSTANT'
for o in bpy.data.objects:
    if o.type == 'FONT':
        o.visible_shadow = False
sc.frame_set(0)
bpy.ops.wm.save_as_mainfile(filepath=f"{HERE}/scene.blend")
print("SCENE OK", FRAMES, S)
