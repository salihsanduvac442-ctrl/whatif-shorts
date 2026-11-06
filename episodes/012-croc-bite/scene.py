# Day 12 — What if you had the bite of a crocodile?  Build: python3 episodes/012-croc-bite/scene.py
# Reference style: base (helpers, lawn/soil, house, garden) copied from episodes/003-lift-million-ref / 006-mantis-punch
import bpy, math, random, os, json
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
random.seed(12)
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

# =====================================================================================
# Day 12 — What if you had the bite of a crocodile?
# Facts used: saltwater crocodile (Crocodylus porosus): large males reach ~6 m; Erickson et al. 2012 (PLoS ONE) measured
#   ~16,400 N (3,700 lbf), the highest bite force measured in a living animal; ~16 kN ~ weight of ~1.7 t (a car).
#   Human maximum bite force is very roughly 1,000 N (varies a lot, molars ~500-1,300 N) -> ~16x weaker.
#   Jaw-opening muscles are weak: handlers hold jaws shut with a few wraps of tape.
#   Integumentary sense organs on the jaws are more sensitive to touch than human fingertips (Leitch & Catania 2012).
#   Each tooth position can be replaced ~50 times over a lifetime. Crocodiles swallow stones (gastroliths);
#   their purpose is debated (buoyancy/diving or digestion) -> "maybe".
# =====================================================================================
lab_m = mat("LabelM", (1.0, 0.85, 0.2), 0.4, emit=(1.0, 0.8, 0.2), emit_strength=0.8)
white_lab = mat("LabW", (1, 1, 1), 0.4, emit=(1, 1, 1), emit_strength=0.7)
red_lab = mat("LabR", (0.95, 0.1, 0.08), 0.4, emit=(1.0, 0.1, 0.05), emit_strength=1.2)
blue_lab = mat("LabB", (0.2, 0.5, 1.0), 0.4, emit=(0.2, 0.5, 1.0), emit_strength=1.0)
green_lab = mat("LabG", (0.3, 0.95, 0.3), 0.4, emit=(0.3, 0.95, 0.3), emit_strength=1.0)
spark_m = glow_mat("Spark", (1.0, 0.95, 0.7), 5.0)
gspark_m = glow_mat("GSpark", (0.4, 1.0, 0.4), 4.0)
eyew = mat("EyeW", (1, 1, 1), 0.3)
eyeb = mat("EyeB", (0.03, 0.03, 0.04), 0.3)
shoe_m = mat("Shoe", (0.15, 0.15, 0.18), 0.6)
tooth_m = mat("Tooth", (0.98, 0.97, 0.9), 0.35)

def burst(loc, f, n=10, r=0.12, size=0.012, f_out=None, material=None, yoff=-0.02):
    for k in range(n):
        a = k / n * 6.283
        s_ = sphere("Burst", (loc[0] + r * math.cos(a), loc[1] + yoff, loc[2] + r * math.sin(a)), size, material or spark_m, sub=1)
        pop(s_, f, 3, f_out if f_out else f + 10)
def wpos(o):
    bpy.context.view_layer.update()
    return tuple(o.matrix_world.translation)

# ---------------- the cartoon saltwater crocodile (~6 m), head toward +x ----------------
CY = 2.6
croc_m = mat("Croc", (0.26, 0.42, 0.15), 0.6)
crocd_m = mat("CrocD", (0.18, 0.3, 0.1), 0.65)
belly_m = mat("CrocBelly", (0.78, 0.74, 0.45), 0.6)
mouth_m = mat("Mouth", (0.95, 0.5, 0.55), 0.5)
cp = []
cp.append(sphere("CBody", (0, CY, 0.45), 1.0, croc_m, scale=(1.65, 0.75, 0.42), sub=3))
cp.append(sphere("CBelly", (0, CY, 0.25), 1.0, belly_m, scale=(1.55, 0.7, 0.22), sub=2))
cp.append(tube("CTail", [(-1.3, CY, 0.45), (-2.4, CY + 0.25, 0.32), (-3.3, CY + 0.6, 0.18), (-3.7, CY + 0.75, 0.12)], [0.48, 0.34, 0.14, 0.03], croc_m))
for k in range(9):
    t_ = k / 9
    x_ = -1.4 - t_ * 2.2; y_ = CY + 0.05 + t_ * 0.6; z_ = 0.45 - t_ * 0.27 + (0.48 - t_ * 0.4)
    cp.append(cyl("TailRidge", (x_, y_, z_), 0.08 * (1 - t_ * 0.6), 0.18 * (1 - t_ * 0.5), crocd_m, r2=0.005, verts=6))
for x_ in [i * 0.3 - 1.35 for i in range(10)]:
    for yo in (-0.42, -0.15, 0.15, 0.42):
        zt = 0.45 + 0.42 * math.sqrt(max(0.0, 1 - (x_ / 1.65) ** 2 - (yo / 0.75) ** 2))
        cp.append(sphere("Scute", (x_, CY + yo, zt - 0.02), 0.09, crocd_m, scale=(1.3, 1.0, 0.7), sub=1, smooth=False))
cp.append(sphere("CHead", (1.75, CY, 0.5), 0.5, croc_m, scale=(1.1, 1.0, 0.68), sub=3))
# lower jaw (fixed)
lj = cyl("LowerJaw", (2.55, CY, 0.3), 0.38, 1.4, croc_m, rot=(0, math.radians(90), 0), r2=0.19, verts=24)
lj.scale = (0.5, 1.0, 1.0); cp.append(lj)
cp.append(box("Tongue", (2.45, CY, 0.43), (1.1, 0.5, 0.03), mouth_m))
for side in (-1, 1):
    for i in range(8):
        x_ = 2.0 + i * 0.15
        y_ = side * (0.33 - (x_ - 2.0) * 0.13)
        cp.append(cyl("LTooth", (x_, CY + y_, 0.47), 0.035, 0.12, tooth_m, r2=0.004, verts=8))
for sy in (-1, 1):   # front legs + back legs
    for xl in (1.05, -1.0):
        cp.append(tube("CLeg", [(xl, CY + sy * 0.55, 0.35), (xl + 0.15, CY + sy * 0.95, 0.22), (xl + 0.3, CY + sy * 1.05, 0.06)], [0.17, 0.14, 0.12], croc_m))
        for t in range(4):
            a = (t - 1.5) * 0.4
            cp.append(sphere("CToe", (xl + 0.3 + 0.15 * math.cos(a), CY + sy * 1.08 + 0.15 * math.sin(a), 0.04), 0.06, crocd_m, scale=(1.5, 0.8, 0.5), sub=1))
croc = group("Croc", (0, CY, 0))
# upper jaw (pivot at the hinge)
HINGE = (1.95, CY, 0.44)
uj = group("UpperJaw", HINGE)
ujp = []
u_ = cyl("UpperJawM", (2.6, CY, 0.52), 0.42, 1.36, croc_m, rot=(0, math.radians(90), 0), r2=0.2, verts=24)
u_.scale = (0.48, 1.0, 1.0); ujp.append(u_)
ujp.append(box("Palate", (2.5, CY, 0.44), (1.15, 0.6, 0.03), mouth_m))
for sy in (-1, 1):
    ujp.append(sphere("Nostril", (3.18, CY + sy * 0.07, 0.6), 0.06, crocd_m, sub=1))
    for i in range(8):
        x_ = 2.07 + i * 0.15
        y_ = sy * (0.37 - (x_ - 2.0) * 0.13)
        ujp.append(cyl("UTooth", (x_, CY + y_, 0.39), 0.035, 0.13, tooth_m, rot=(math.radians(180), 0, 0), r2=0.004, verts=8))
# sensors (line 9): tiny glowing dots on the snout
sens = []
for i in range(46):
    x_ = random.uniform(2.1, 3.15); w_ = 0.4 - (x_ - 2.0) * 0.17
    yy = random.uniform(-w_, w_) * 0.85
    zz = 0.52 + 0.19 * math.sqrt(max(0.0, 1 - (yy / max(w_, 0.05)) ** 2)) * (1.0 - (x_ - 2.0) * 0.4)
    s_ = sphere("Sensor", (x_, CY + yy, zz + 0.02), 0.022, glow_mat("SensM", (1.0, 0.9, 0.2), 4.0), sub=1)
    sens.append(s_); ujp.append(s_)
attach(ujp, uj)
# eyes
for sy in (-1, 1):
    cp.append(sphere("EyeBump", (1.95, CY + sy * 0.24, 0.8), 0.15, croc_m, sub=2))
    cp.append(sphere("CEye", (2.0, CY + sy * 0.26, 0.86), 0.1, mat("CEyeY", (1.0, 0.82, 0.15), 0.3), sub=2))
    cp.append(box("CPupil", (2.09, CY + sy * 0.27, 0.87), (0.03, 0.03, 0.13), eyeb))
attach(cp + [uj], croc)
def snap(f, opn=-0.62, hold=6):
    uj.keyframe_insert("rotation_euler", frame=f - hold - 1)
    uj.rotation_euler = (0, opn, 0); uj.keyframe_insert("rotation_euler", frame=f - 2)
    uj.rotation_euler = (0, 0, 0); uj.keyframe_insert("rotation_euler", frame=f)
    uj.rotation_euler = (0, -0.05, 0); uj.keyframe_insert("rotation_euler", frame=f + 2)
    uj.rotation_euler = (0, 0, 0); uj.keyframe_insert("rotation_euler", frame=f + 4)
uj.rotation_euler = (0, 0, 0); uj.keyframe_insert("rotation_euler", frame=0)
TIP = (3.25, CY, 0.45)
SNAP0 = 16
snap(SNAP0)
burst((TIP[0] + 0.1, TIP[1] - 0.4, TIP[2] + 0.1), SNAP0, 12, 0.35, 0.04, SNAP0 + 12)
snap(S[2] + 18)
SNAP3 = S[3] + 33
snap(SNAP3, hold=10)
burst((TIP[0] + 0.1, TIP[1] - 0.4, TIP[2] + 0.1), SNAP3, 12, 0.4, 0.045, SNAP3 + 12)
# idle breathing
for f in range(0, FRAMES + 30, 30):
    croc.scale = (1, 1, 1); croc.keyframe_insert("scale", frame=f)
    croc.scale = (1, 1, 1.015); croc.keyframe_insert("scale", frame=f + 15)

# ---------------- people (hidden until line 12) ----------------
MX, MY = 4.7, 0.55
you, Y = person("You", (MX, MY, 0.0), 1.0, mat("ShirtY", (0.95, 0.35, 0.25), 0.7), mat("PantsY", (0.2, 0.25, 0.45), 0.8),
                skin_m, mat("HairY", (0.28, 0.16, 0.07), 0.8))

# =====================================================================================
# per-line views
# =====================================================================================
V = {}
V[0] = ((4.4, -2.6, 1.3), (2.5, CY, 0.5))
V[1] = ((0.8, -8.6, 2.6), (-0.2, CY, 0.4))
V[2] = ((4.6, -3.2, 1.5), (2.3, CY, 0.55))
V[3] = ((5.8, 0.4, 1.2), (2.9, CY, 0.5))
V[4] = ((6.4, -3.6, 2.2), (4.6, 3.2, 0.9))
V[5] = ((-0.6, -4.8, 1.8), (-0.6, 0.7, 0.9))
V[6] = ((0.2, -4.6, 1.9), (-0.6, 0.7, 1.0))
V[7] = ((2.9, -1.9, 1.0), (2.5, CY, 0.5))
V[8] = ((3.6, -1.7, 1.1), (2.7, CY, 0.48))
V[9] = ((3.9, -1.0, 1.6), (2.8, CY, 0.5))
V[10] = ((2.8, -1.2, 0.75), (2.55, CY - 0.3, 0.45))
V[11] = ((0.4, -2.5, 1.2), (0.0, CY - 0.8, 0.5))
V[12] = ((5.6, -3.0, 1.5), (MX + 0.4, MY, 1.1))
V[13] = ((MX + 0.3, MY - 2.7, 1.5), (MX, MY, 1.15))
V[14] = ((MX + 0.9, MY - 2.4, 1.5), (MX + 0.3, MY, 1.2))
V[15] = ((MX - 0.5, MY - 2.4, 1.5), (MX + 0.3, MY, 1.2))
V[16] = ((MX + 0.2, MY - 2.1, 1.6), (MX, MY, 1.35))
V[17] = ((3.4, -7.4, 2.8), (3.2, 1.8, 0.6))
DR = {0: (-0.6, 0.6, 0), 1: (1.0, 1.4, 0), 2: (-0.5, 0.5, 0), 3: (-0.6, -0.6, 0), 4: (-0.6, 0.6, 0), 5: (0.4, 0.4, 0), 6: (-0.4, 0.5, 0),
      7: (0.3, 0.2, 0), 8: (-0.3, 0.2, 0), 9: (0.3, 0.2, 0), 10: (-0.2, 0.15, 0), 11: (0.5, 0.4, 0), 12: (-0.5, 0.5, 0),
      13: (0.3, 0.5, 0), 14: (-0.3, 0.4, 0), 15: (0.3, 0.4, 0), 16: (-0.2, 0.3, 0), 17: (-0.8, 1.2, -0.2)}
def LB(i, name, body, v, m_, size=None, u=0.0, f_in=None, f_out=None, Dk=0.55):
    cl = Vector(CL(V[i])); D = (Vector(V[i][1]) - cl).length * Dk
    s_ = fit(body, D, size if size else 1.0)
    return label(name, body, V[i], D, v, s_, m_, (S[i] + 3) if f_in is None else f_in,
                 (S[i + 1] if i + 1 < len(S) else FRAMES + 5) if f_out is None else f_out, u)
LT = 0.3   # label height on screen (clear of the badge and the 42-52% caption band)

LB(0, "L0", "SNAP!", LT, lab_m, f_in=SNAP0)
# line 1: 6 m tape measure in front of the croc
tape_y = CY - 1.35
tm = box("Measure", (-0.25, tape_y, 0.03), (6.9, 0.14, 0.04), mat("MeasM", (1.0, 0.85, 0.15), 0.5))
for i in range(13):
    tk = box("MTick", (-3.7 + i * 0.575, tape_y - 0.02, 0.06), (0.03, 0.1, 0.02), eyeb)
    hide_until(tk, S[1] + 2); gone_at(tk, S[2] + 2)
pop(tm, S[1] + 2, 6, S[2] + 2)
LB(1, "L1", "6 METERS", LT, lab_m)
LB(2, "L2", "STRONGEST BITE", LT, red_lab)
LB(3, "L3", "16,000 N", LT, lab_m)
# line 4: a car on a weighing plate
def car_mesh(name, body_c):
    parts = [box(name + "B", (0, 0, 0.32), (1.7, 0.8, 0.4), mat(name + "M", body_c, 0.35), bevel=0.06),
             box(name + "C", (-0.1, 0, 0.66), (0.9, 0.72, 0.32), mat(name + "W", (0.55, 0.8, 0.95), 0.1), bevel=0.05)]
    for x in (-0.55, 0.55):
        for y in (-0.4, 0.4):
            parts.append(cyl(name + "Wh", (x, y, 0.18), 0.18, 0.14, mat(name + "T", (0.08, 0.08, 0.09), 0.7), rot=(math.radians(90), 0, 0), verts=14))
    bpy.ops.object.select_all(action='DESELECT')
    for p_ in parts:
        p_.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]
    bpy.ops.object.convert(target='MESH'); bpy.ops.object.join()
    o = bpy.context.object; o.name = name
    return o
car = car_mesh("Car", (0.2, 0.5, 0.95))
car.scale = (1.4, 1.4, 1.4)
key_loc(car, [(0, (4.6, 3.3, 9.0)), (S[4] + 2, (4.6, 3.3, 6.0)), (S[4] + 10, (4.6, 3.3, 0.32))])
keyscale(car, [(0, 0.001), (S[4] + 1, 0.001), (S[4] + 2, 1.4), (S[5] - 2, 1.4), (S[5], 0.001)])
plate = box("Plate", (4.6, 3.3, 0.15), (3.0, 1.6, 0.3), mat("PlateM", (0.75, 0.76, 0.8), 0.3, metal=0.6), bevel=0.04)
pop(plate, S[4], 4, S[5])
burst((4.6, 3.3 - 1.0, 0.4), S[4] + 10, 14, 1.6, 0.08, S[4] + 22)
LB(4, "L4", "= A CAR (1.7 t)", LT, lab_m)
# lines 5-6: bite-force bars, you vs croc
BX, BY = -0.6, 0.7
bar_y = box("BarYou", (BX - 0.55, BY, 0), (0.7, 0.7, 1.0), blue_lab)
bar_c = box("BarCroc", (BX + 0.55, BY, 0), (0.7, 0.7, 1.0), red_lab)
for b_ in (bar_y, bar_c):
    b_.data.transform(Matrix.Translation((0, 0, 0.5)))
keyscale(bar_y, [(0, 0.001), (S[5] + 1, 0.001), (S[5] + 2, (1, 1, 0.01)), (S[5] + 10, (1, 1, 0.2)), (S[7] - 2, (1, 1, 0.2)), (S[7], 0.001)])
keyscale(bar_c, [(0, 0.001), (S[5] + 1, 0.001), (S[5] + 2, (1, 1, 0.01)), (S[6], (1, 1, 0.01)), (S[6] + 14, (1, 1, 3.2)), (S[7] - 2, (1, 1, 3.2)), (S[7], 0.001)])
yl = text("BarYouL", "YOU", (BX - 0.55, BY - 0.45, 0.45), 0.3, white_lab, extrude=0.02); pop(yl, S[5] + 4, 5, S[7])
cl_ = text("BarCrocL", "CROC", (BX + 0.55, BY - 0.45, 0.45), 0.3, white_lab, extrude=0.02); pop(cl_, S[6] + 4, 5, S[7])
cl_.location = (BX + 0.55, BY - 0.45, 0.45)
LB(5, "L5", "~1,000 N", LT, blue_lab)
LB(6, "L6", "16x WEAKER", LT, red_lab)
# line 7: jaw tries to open — weakly
for k in range(3):
    f0 = S[7] + 6 + k * 12
    uj.rotation_euler = (0, 0, 0); uj.keyframe_insert("rotation_euler", frame=f0)
    uj.rotation_euler = (0, -0.12, 0); uj.keyframe_insert("rotation_euler", frame=f0 + 5)
    uj.rotation_euler = (0, 0, 0); uj.keyframe_insert("rotation_euler", frame=f0 + 10)
LB(7, "L7", "WEAK OPENERS", LT, white_lab)
# line 8: tape wraps around the snout
tape_m = mat("TapeM", (0.75, 0.75, 0.78), 0.35)
for k, x_ in enumerate((2.5, 2.8, 3.05)):
    w_ = 0.42 - (x_ - 2.0) * 0.17
    ring = tube("TapeRing", [(x_, CY + w_ * 1.08 * math.cos(a / 20 * 6.283), 0.44 + 0.24 * math.sin(a / 20 * 6.283)) for a in range(21)], [0.045] * 21, tape_m)
    keyscale(ring, [(0, 0.001), (S[8] + 3 + k * 5, 0.001)])
    ring.scale = (1, 1, 1); ring.keyframe_insert("scale", frame=S[8] + 6 + k * 5)
    gone_at(ring, S[9] + 1, 2)
    bpy.context.view_layer.update()
for k in range(3):   # struggles, stays shut
    f0 = S[8] + 20 + k * 6
    uj.rotation_euler = (0, 0, 0); uj.keyframe_insert("rotation_euler", frame=f0)
    uj.rotation_euler = (0, -0.025, 0); uj.keyframe_insert("rotation_euler", frame=f0 + 3)
uj.rotation_euler = (0, 0, 0); uj.keyframe_insert("rotation_euler", frame=S[8] + 40)
LB(8, "L8", "TAPE HOLDS IT!", LT, lab_m)
# line 9: touch sensors glow + ripples in a puddle
for s_ in sens:
    keyscale(s_, [(0, 0.001), (S[9] + random.randint(1, 10), 0.001)])
    s_.scale = (1, 1, 1); s_.keyframe_insert("scale", frame=S[9] + 12)
    gone_at(s_, S[10] + 1, 2)
pud = cyl("Puddle", (3.55, CY - 0.1, 0.012), 0.7, 0.02, mat("PudM", (0.3, 0.7, 0.9), 0.05, emit=(0.2, 0.6, 0.85), emit_strength=0.4), verts=40)
pud.scale = (1, 1, 1)
pop(pud, S[9], 4, S[10] + 2)
for k in range(3):
    rg = tube("Ripple", [(3.55 + 0.15 * math.cos(a / 24 * 6.283), CY - 0.1 + 0.15 * math.sin(a / 24 * 6.283), 0.03) for a in range(25)], [0.012] * 25, white_lab)
    rg.data.transform(Matrix.Translation((-3.55, -(CY - 0.1), 0))); rg.location = (3.55, CY - 0.1, 0)
    f0 = S[9] + 4 + k * 10
    keyscale(rg, [(0, 0.001), (f0, 0.001), (f0 + 1, 1.0), (f0 + 14, 4.0), (f0 + 16, 0.001)])
LB(9, "L9", "SUPER TOUCH", LT, lab_m)
# line 10: a tooth pops out, a new one grows (x3)
TX0 = (2.45, CY - (0.33 - 0.45 * 0.13) - 0.0, 0.47)
for k in range(3):
    f0 = S[10] + 4 + k * 14
    old = cyl("OldTooth", (TX0[0], TX0[1] - 0.02, 0.5), 0.05, 0.16, tooth_m, r2=0.004, verts=8)
    keyscale(old, [(0, 0.001), (f0 - 6, 0.001), (f0 - 3, 1.0)])
    key_loc(old, [(f0, (TX0[0], TX0[1] - 0.02, 0.5)), (f0 + 5, (TX0[0] + 0.1, TX0[1] - 0.4, 0.9)), (f0 + 10, (TX0[0] + 0.2, TX0[1] - 0.7, 0.05))])
    old.rotation_euler = (0, 0, 0); old.keyframe_insert("rotation_euler", frame=f0)
    old.rotation_euler = (3, 1, 0); old.keyframe_insert("rotation_euler", frame=f0 + 10)
    gone_at(old, f0 + 13, 3)
    burst((TX0[0], TX0[1] - 0.05, 0.55), f0, 8, 0.12, 0.015, f0 + 8)
LB(10, "L10", "x50 PER TOOTH", LT, white_lab)
# line 11: stones in the belly (x-ray dots on the side)
stone_g = mat("StoneG", (0.7, 0.68, 0.64), 0.6, emit=(0.8, 0.8, 0.75), emit_strength=0.35)
xr = sphere("XRay", (0.1, CY - 0.62, 0.42), 1.0, mat("XRayM", (0.2, 0.3, 0.45), 0.5, emit=(0.25, 0.45, 0.7), emit_strength=0.6), scale=(0.95, 0.2, 0.33), sub=3)
bpy.ops.object.select_all(action="DESELECT"); xr.select_set(True); bpy.context.view_layer.objects.active = xr
bpy.ops.object.transform_apply(scale=True)
pop(xr, S[11] + 1, 4, S[12])
for k in range(9):
    st = sphere("Gastrolith", (0.1 + random.uniform(-0.65, 0.65), CY - 0.84, 0.42 + random.uniform(-0.15, 0.15)), random.uniform(0.08, 0.12), stone_g, scale=(1.2, 1, 0.9), sub=1, smooth=False)
    pop(st, S[11] + 5 + k * 2, 4, S[12])
LB(11, "L11", "STONES INSIDE", LT, white_lab)

# ---------------- lines 12-17: YOU ----------------
hide_until(you, S[12])
MOUTH = Y["P"](0, -0.32, 1.58)
TBL = (MX + 1.1, MY - 0.1)
tb_m = mat("SmallTable", (0.95, 0.95, 0.93), 0.5)
for o_ in (cyl("STableTop", (TBL[0], TBL[1], 0.9), 0.38, 0.05, tb_m, verts=24), cyl("STableLeg", (TBL[0], TBL[1], 0.45), 0.05, 0.9, tb_m, verts=10)):
    hide_until(o_, S[12])
def fly_to_mouth(o, home, f_bite):
    key_loc(o, [(f_bite - 8, home), (f_bite - 1, (MOUTH[0] + 0.12, MOUTH[1] - 0.05, MOUTH[2])), (f_bite, (MOUTH[0] + 0.1, MOUTH[1] - 0.05, MOUTH[2]))])
# line 12: apple, normal bite
APH = (TBL[0], TBL[1], 1.0)
apple = group("Apple", APH)
app = [sphere("AppleB", APH, 0.09, mat("AppleM", (0.85, 0.08, 0.08), 0.35), scale=(1, 1, 0.92), sub=3),
       cyl("AppleStem", (APH[0], APH[1], APH[2] + 0.1), 0.008, 0.05, mat("StemM", (0.35, 0.2, 0.1), 0.8)),
       sphere("AppleLeaf", (APH[0] + 0.025, APH[1], APH[2] + 0.11), 0.025, mat("LeafM", (0.2, 0.7, 0.2), 0.6), scale=(1.4, 0.5, 0.3), sub=1)]
bite = sphere("AppleBite", (APH[0] - 0.07, APH[1] - 0.04, APH[2] + 0.02), 0.045, mat("AppleFlesh", (1.0, 0.95, 0.75), 0.5), scale=(0.6, 1, 1), sub=2)
app.append(bite)
attach(app, apple)
keyscale(bite, [(0, 0.001), (S[12] + 1, 0.001)])
B12 = S[12] + 30
bite.scale = (1, 1, 1); bite.keyframe_insert("scale", frame=B12)
hide_until(apple, S[12])
fly_to_mouth(apple, APH, B12)
key_loc(apple, [(B12 + 6, (MOUTH[0] + 0.1, MOUTH[1] - 0.05, MOUTH[2])), (B12 + 14, APH)])
burst((MOUTH[0] + 0.05, MOUTH[1] - 0.1, MOUTH[2]), B12, 8, 0.12, 0.015, B12 + 8, material=mat("Crumb", (1.0, 0.95, 0.75), 0.5))
gone_at(apple, S[13], 3)
LB(12, "L12", "NORMAL BITE", LT, blue_lab)
# line 13: crocodile power — green glow + croc teeth
burst(Y["P"](0, -0.35, 1.2), S[13] + 4, 16, 0.75, 0.045, S[13] + 18, material=gspark_m, yoff=-0.1)
bpy.ops.object.light_add(type='POINT', location=Y["P"](0, -0.9, 1.5))
pl = bpy.context.object; pl.data.color = (0.4, 1.0, 0.4); pl.data.shadow_soft_size = 0.3
pl.data.energy = 0; pl.data.keyframe_insert("energy", frame=S[13] + 2)
pl.data.energy = 60; pl.data.keyframe_insert("energy", frame=S[13] + 6)
pl.data.energy = 35; pl.data.keyframe_insert("energy", frame=S[14] + 2)
pl.data.energy = 0; pl.data.keyframe_insert("energy", frame=S[17])
fangs = []
for i in range(7):
    x_ = (i - 3) * 0.032
    for sz, zz, rr in ((1, 1.615, math.radians(180)), (-1, 1.55, 0)):
        fangs.append(cyl("Fang", Y["P"](x_, -0.27 + abs(x_) * 0.4, zz), 0.014, 0.05, tooth_m, rot=(rr, 0, 0), r2=0.002, verts=6))
for fg in fangs:
    hide_until(fg, S[13] + 6)
Y["smile"].keyframe_insert("scale", frame=S[13] + 5)
Y["smile"].scale = (0.001,) * 3; Y["smile"].keyframe_insert("scale", frame=S[13] + 6)
for sx in (-1, 1):   # green scaly cheeks
    for k in range(3):
        sc_ = sphere("CheekScale", Y["P"](sx * (0.15 + k * 0.03), -0.2, 1.66 - k * 0.04), 0.03, croc_m, scale=(1, 0.5, 0.8), sub=1, smooth=False)
        hide_until(sc_, S[13] + 8)
LB(13, "L13", "CROC POWER!", LT, green_lab)
# line 14: coconut crushed
COH = (TBL[0] - 0.1, TBL[1], 1.04)
coco = sphere("Coconut", COH, 0.12, mat("CocoM", (0.45, 0.28, 0.14), 0.85), scale=(1, 1, 1.1), sub=2, smooth=False)
B14 = S[14] + 22
hide_until(coco, S[13] + 10)
fly_to_mouth(coco, COH, B14)
gone_at(coco, B14 + 1, 1)
shell_ms = [mat("CocoS", (0.45, 0.28, 0.14), 0.85), mat("CocoW", (0.98, 0.97, 0.93), 0.6)]
def shatter_at(c0, f, n, r, ms, spread=1.0, f_gone=None):
    for i in range(n):
        th = random.uniform(0, 6.283); ph = random.uniform(-0.5, 1.0)
        d = Vector((math.cos(th) * math.cos(ph), math.sin(th) * math.cos(ph) * 0.6 - 0.4, math.sin(ph)))
        p0 = tuple(Vector(c0) + d * r * 0.4)
        ch = sphere("Shard", p0, r * random.uniform(0.3, 0.45), random.choice(ms), sub=1, smooth=False)
        p1 = tuple(Vector(c0) + d * r * 6 * spread + Vector((0, 0, 0.3)))
        p2 = (c0[0] + d.x * r * 9 * spread, c0[1] + d.y * r * 9 * spread, 0.05)
        key_loc(ch, [(f, p0), (f + 7, p1), (f + 16, p2)])
        ch.rotation_euler = (0, 0, 0); ch.keyframe_insert("rotation_euler", frame=f)
        ch.rotation_euler = (random.uniform(3, 8), random.uniform(3, 8), 0); ch.keyframe_insert("rotation_euler", frame=f + 16)
        keyscale(ch, [(0, 0.001), (f - 1, 0.001), (f, 1.0)] + ([(f_gone - 3, 1.0), (f_gone, 0.001)] if f_gone else []))
MP = (MOUTH[0] + 0.1, MOUTH[1] - 0.05, MOUTH[2])
shatter_at(MP, B14, 16, 0.12, shell_ms, f_gone=S[16])
burst((MP[0], MP[1] - 0.1, MP[2]), B14, 14, 0.3, 0.025, B14 + 10, material=mat("Milk", (1, 1, 1), 0.3, emit=(1, 1, 1), emit_strength=0.5))
LB(14, "L14", "CRUSHED!", LT, lab_m)
# line 15: brick snapped in half
BRH = (TBL[0] + 0.12, TBL[1], 0.97)
brick_m = mat("Brick", (0.78, 0.3, 0.18), 0.85)
brick = box("Brick", BRH, (0.24, 0.11, 0.07), brick_m, bevel=0.005)
hide_until(brick, S[13] + 10)
B15 = S[15] + 16
fly_to_mouth(brick, BRH, B15)
gone_at(brick, B15 + 1, 1)
for sx in (-1, 1):
    h_ = box("BrickHalf", MP, (0.12, 0.11, 0.07), brick_m, bevel=0.005)
    keyscale(h_, [(0, 0.001), (B15, 0.001), (B15 + 1, 1.0), (S[16] + 6, 1.0), (S[16] + 9, 0.001)])
    key_loc(h_, [(B15, (MP[0] + sx * 0.07, MP[1], MP[2])), (B15 + 7, (MP[0] + sx * 0.6, MP[1] - 0.3, MP[2] + 0.35)), (B15 + 15, (MP[0] + sx * 1.0, MP[1] - 0.5, 0.05))])
    h_.rotation_euler = (0, 0, 0); h_.keyframe_insert("rotation_euler", frame=B15)
    h_.rotation_euler = (2.5, sx * 3.0, 1.0); h_.keyframe_insert("rotation_euler", frame=B15 + 15)
shatter_at(MP, B15, 10, 0.06, [brick_m], spread=1.2, f_gone=S[16] + 8)
burst((MP[0], MP[1] - 0.1, MP[2]), B15, 12, 0.25, 0.02, B15 + 10)
LB(15, "L15", "SNAPPED!", LT, lab_m)
# line 16: ouch — tongue
tongue = sphere("YouTongue", Y["P"](0, -0.33, 1.53), 0.05, mouth_m, scale=(1, 1.4, 0.4), sub=2)
keyscale(tongue, [(0, 0.001), (S[16] + 8, 0.001), (S[16] + 11, (1, 1.4, 0.4)), (S[17] - 2, (1, 1.4, 0.4)), (S[17], 0.001)])
for k in range(6):
    a = k / 6 * 6.283
    st_ = sphere("Star", Y["P"](0.32 * math.cos(a), -0.1, 1.95 + 0.12 * math.sin(a)), 0.045, lab_m, sub=1)
    pop(st_, S[16] + 10 + k, 3, S[17])
LB(16, "L16", "OUCH!", LT, red_lab)
# line 17: question
keyrot(Y["arms"][0], [(S[17], (0, 0, 0)), (S[17] + 6, (0, 2.4, 0))])
keyrot(Y["arms"][1], [(S[17], (0, 0, 0)), (S[17] + 6, (0, -2.4, 0))])
snap(S[17] + 20)
q = text("Q", "?", SP(V[17], 4.0, LT, 0.0), 0.6, lab_m, extrude=0.06)
pop(q, S[17] + 4, 6)
keyrot(q, [(S[17] + 4, (math.radians(90), 0, 0)), (FRAMES, (math.radians(90), 0, math.radians(360)))])

# ---------------- camera ----------------
bpy.ops.object.camera_add()
cam = bpy.context.object
sc.camera = cam
cam.data.lens = 26
cam.data.sensor_fit = 'VERTICAL'
cam.data.sensor_height = 36
cam.data.clip_start = 0.01
cam.data.clip_end = 200000
target = bpy.data.objects.new("Target", None); sc.collection.objects.link(target)
tr = cam.constraints.new('TRACK_TO'); tr.target = target
tr.track_axis = 'TRACK_NEGATIVE_Z'; tr.up_axis = 'UP_Y'
cam_keys = []
for i in range(len(S)):
    f_a = S[i]
    f_b = (S[i + 1] - 1) if i + 1 < len(S) else FRAMES - 1
    v = V[i]; d = DR[i]
    cam_keys.append((f_a, CL(v), v[1]))
    c2 = (v[0][0] + d[0], v[0][1] + d[1], v[0][2] + d[2])
    cam_keys.append((f_b, overhead(c2, v[1]), v[1]))
for f, cl, tl in cam_keys:
    cam.location = cl; cam.keyframe_insert("location", frame=f)
    target.location = aim(cl, tl); target.keyframe_insert("location", frame=f)
def fcurves(o_):
    ad = o_.animation_data
    if ad is None or ad.action is None:
        return []
    try:
        return list(ad.action.fcurves)
    except AttributeError:
        from bpy_extras import anim_utils
        return list(anim_utils.action_get_channelbag_for_slot(ad.action, ad.action_slot).fcurves)
CUTS = tuple(S[1:])
for o_ in (cam, target):
    for fc in fcurves(o_):
        pts = fc.keyframe_points
        for i in range(len(pts) - 1):
            if int(round(pts[i + 1].co[0])) in CUTS:
                pts[i].interpolation = 'CONSTANT'
for o in bpy.data.objects:
    if o.type == 'FONT':
        o.visible_shadow = False
sc.frame_set(0)
bpy.ops.wm.save_as_mainfile(filepath=f"{HERE}/scene.blend")
print("SCENE OK", FRAMES, S)
