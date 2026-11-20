# Day 26 — What if 1 billion locusts flew over your town?  Build: python3 episodes/026-billion-locusts/scene.py
# Reference style: base (helpers, lawn/soil, house, garden, camera helpers) copied from episodes/022-billion-bees (ref style of 003-lift-million-ref)
import bpy, math, random, os, json
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
random.seed(26)
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
# Day 26 — What if 1 billion locusts flew over your town?
# Facts used (FAO Locust Watch, desert locust Schistocerca gregaria):
#   an adult desert locust weighs ~2 g and eats roughly its own weight in fresh vegetation every day;
#   locusts are grasshoppers: when crowded (touching hind legs) solitary green nymphs switch to the gregarious
#   phase — behaviour changes within hours, colour turns yellow/black — and they band and swarm;
#   1e3 x 2 g = 2 kg/day; 1e6 -> ~2 t/day (a garden in a day);  1e9 x 2 g = 2,000 t (cars ~1.5 t -> > 1,000 cars);
#   swarm density 40-80 million per km2 -> 1e9 covers ~12-25 km2 ("over ten square kilometers");
#   FAO: a 1 km2 swarm eats as much food in one day as ~35,000 people -> ~12.5 km2 ~ 440,000 people
#   ("hundreds of thousands");  swarms drift with the wind up to ~150 km a day;
#   the 2019-2020 East Africa upsurge had swarms estimated at up to 150-200 billion locusts.
# Cartoon scale: locusts are drawn far bigger than life so they read on a phone.
# =====================================================================================

for o in bpy.data.objects:
    if o.name.startswith("Bush"):
        o.scale = (0.001,) * 3

# ---------------- materials ----------------
loc_y = mat("LocYellow", (1.0, 0.76, 0.08), 0.45)
loc_k = mat("LocBlack", (0.07, 0.05, 0.03), 0.5)
loc_g = mat("LocGreen", (0.32, 0.72, 0.18), 0.5)
loc_gd = mat("LocGreenDk", (0.16, 0.45, 0.1), 0.55)
lwing_m = mat("LWing", (0.85, 0.78, 0.55), 0.3, emit=(0.8, 0.72, 0.45), emit_strength=0.25)
gwing_m = mat("GWing", (0.6, 0.85, 0.45), 0.3, emit=(0.5, 0.8, 0.35), emit_strength=0.2)
haze_m = mat("Haze", (0.55, 0.42, 0.16), 0.9)
dark_haze = mat("DarkHaze", (0.22, 0.16, 0.07), 0.95)
leaf_m = mat("Lettuce", (0.45, 0.85, 0.25), 0.6)
leaf_dk = mat("LettuceDk", (0.3, 0.65, 0.15), 0.6)
cab_ms = [mat("Cab%d" % k, c, 0.6) for k, c in enumerate([(0.3, 0.7, 0.25), (0.45, 0.8, 0.3), (0.55, 0.3, 0.6)])]
wood = mat("Wood", (0.75, 0.5, 0.28), 0.7)
ink_m = mat("Ink", (0.08, 0.08, 0.1), 0.5)
dirt_m = mat("Dirt", (0.45, 0.28, 0.13), 0.95)
wheat_m = mat("Wheat", (0.95, 0.75, 0.25), 0.6)
grain_m = mat("Grain", (0.98, 0.8, 0.35), 0.7)
road_m = mat("Road", (0.25, 0.25, 0.28), 0.8)
streak_m = glow_mat("Streak", (1, 1, 1), 2.5)
frame_glow = glow_mat("FrameGlow", (1.0, 0.85, 0.2), 4.0)
_stripe = {}
def loc_stripe(r, green=False):
    k = (round(r, 3), green)
    if k not in _stripe:
        c1, c2 = ((0.32, 0.72, 0.18), (0.2, 0.5, 0.12)) if green else ((1.0, 0.76, 0.08), (0.07, 0.05, 0.03))
        _stripe[k] = stripe_mat("LocStripe%s%s" % (k[0], "g" if green else "y"), c1, c2, axis="Y",
                                freq=2 * math.pi / (0.3 * r), thresh=0.45, rough=0.45)
    return _stripe[k]

# ---------------- hero locust (faces -Y, group origin = body centre) ----------------
def locust(name, loc, r, rz=0.0, green=False, flying=False):
    x, y, z = loc
    g = group(name, loc, rz)
    def P(dx, dy, dz):
        return (x + dx * r, y + dy * r, z + dz * r)
    body = loc_g if green else loc_y
    dk = loc_gd if green else loc_k
    wm = gwing_m if green else lwing_m
    parts = [sphere(name + "Abd", P(0, 0.55, -0.02), 0.5 * r, loc_stripe(r, green), scale=(0.42, 1.35, 0.42), sub=3),
             sphere(name + "Thx", P(0, -0.15, 0.03), 0.3 * r, body, scale=(0.85, 1.15, 0.95), sub=3),
             sphere(name + "Pron", P(0, -0.15, 0.13), 0.3 * r, dk, scale=(0.95, 1.05, 0.62), sub=3),
             sphere(name + "Head", P(0, -0.55, 0.1), 0.25 * r, body, scale=(0.85, 0.95, 1.12), sub=3)]
    for sx in (-1, 1):
        parts += [sphere(name + "EyeW", P(sx * 0.17, -0.62, 0.2), 0.12 * r, eyew, scale=(0.8, 0.9, 1.15), sub=2),
                  sphere(name + "EyeB", P(sx * 0.19, -0.71, 0.22), 0.06 * r, eyeb, sub=2),
                  tube(name + "Ant", [P(sx * 0.07, -0.72, 0.3), P(sx * 0.2, -0.95, 0.55), P(sx * 0.3, -1.15, 0.62)], [0.025 * r] * 3, dk)]
        # front + mid legs
        for dy in (-0.32, -0.08):
            parts.append(tube(name + "Leg", [P(sx * 0.15, dy, -0.12), P(sx * 0.3, dy - 0.05, -0.2), P(sx * 0.33, dy - 0.1, -0.36)],
                              [0.035 * r] * 3, dk))
        # big jumping hind legs: thick thigh up to the knee, thin shin back down
        parts.append(tube(name + "Thigh", [P(sx * 0.16, 0.0, -0.08), P(sx * 0.3, 0.35, 0.22), P(sx * 0.34, 0.62, 0.42)],
                          [0.1 * r, 0.085 * r, 0.05 * r], body))
        parts.append(tube(name + "Shin", [P(sx * 0.34, 0.62, 0.42), P(sx * 0.36, 0.72, 0.0), P(sx * 0.37, 0.8, -0.36)],
                          [0.035 * r] * 3, dk))
        if flying:
            wg = group(name + "WingG", P(sx * 0.1, -0.05, 0.22))
            wing = sphere(name + "Wing", P(sx * 0.62, 0.25, 0.3), 0.55 * r, wm, scale=(1.0, 0.42, 0.05), sub=2)
            wing.rotation_euler = (0, sx * math.radians(-12), sx * math.radians(-18))
            attach([wing], wg)
            wg.rotation_euler = (0, 0, 0); wg.keyframe_insert("rotation_euler", frame=0)
            for fc in fcurves(wg):
                if fc.data_path == "rotation_euler" and fc.array_index == 1:
                    m_ = fc.modifiers.new('NOISE'); m_.strength = 1.4; m_.scale = 0.7; m_.phase = random.uniform(0, 100)
            parts.append(wg)
        else:
            parts.append(sphere(name + "Wing", P(sx * 0.1, 0.5, 0.24), 0.5 * r, wm, scale=(0.26, 1.45, 0.06), sub=2))
    sm = tube(name + "Smile", [P(-0.09, -0.79, -0.0), P(0, -0.82, -0.05), P(0.09, -0.79, -0.0)], [0.02 * r] * 3, eyeb)
    attach(parts + [sm], g)
    return g

def hover(o, keys, amp=0.08):
    key_loc(o, keys)
    jitter(o, amp, 5.0)

def hop(o, a, b, f0, f1, h=0.6):
    """parabolic hop from a to b between frames f0..f1"""
    for k in range(5):
        t = k / 4
        p = Vector(a).lerp(Vector(b), t); p.z += h * 4 * t * (1 - t)
        o.location = p; o.keyframe_insert("location", frame=int(f0 + t * (f1 - f0)))

def join(objs, name):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    bpy.ops.object.join()
    o = bpy.context.object; o.name = name
    o.location = (0, 0, -300); o.hide_render = True; o.hide_viewport = True
    return o

# ---------------- crowd protos ----------------
LOC = join([sphere("q1", (0, 0.45, 0), 0.5, loc_stripe(1.0), scale=(0.42, 1.3, 0.42), sub=1, smooth=False),
            sphere("q2", (0, -0.15, 0.03), 0.32, loc_y, sub=1, smooth=False),
            sphere("q3", (0, -0.52, 0.1), 0.26, loc_y, sub=1, smooth=False),
            sphere("qw1", (-0.55, 0.2, 0.3), 0.5, lwing_m, scale=(1.0, 0.45, 0.06), sub=1, smooth=False),
            sphere("qw2", (0.55, 0.2, 0.3), 0.5, lwing_m, scale=(1.0, 0.45, 0.06), sub=1, smooth=False),
            sphere("qe1", (-0.15, -0.62, 0.2), 0.11, eyew, sub=1, smooth=False),
            sphere("qe2", (0.15, -0.62, 0.2), 0.11, eyew, sub=1, smooth=False),
            seg("ql1", (-0.15, 0.0, 0), (-0.32, 0.6, 0.4), 0.07, loc_k),
            seg("ql2", (0.15, 0.0, 0), (0.32, 0.6, 0.4), 0.07, loc_k)], "LocProto")
roof_p = mat("RoofP", (0.82, 0.36, 0.2), 0.7)
wall_ps = [mat("WallP%d" % k, c, 0.8) for k, c in enumerate([(0.95, 0.9, 0.8), (0.85, 0.9, 0.98), (0.98, 0.85, 0.7)])]
def house_proto(k):
    w_ = box("hw", (0, 0, 0.45), (1.2, 1.0, 0.9), wall_ps[k])
    rf = cyl("hr", (0, 0, 1.15), 0.95, 0.55, roof_p, verts=4, r2=0.0)
    rf.rotation_euler = (0, 0, math.radians(45))
    return join([w_, rf], "HouseProto%d" % k)
HOUSES = [house_proto(k) for k in range(3)]
shirt_ps = [mat("CrowdShirt%d" % k, c, 0.6) for k, c in enumerate([(0.95, 0.35, 0.2), (0.2, 0.5, 0.95), (0.3, 0.75, 0.35), (0.95, 0.8, 0.2)])]
def people_proto(k):
    return join([cyl("pb", (0, 0, 0.45), 0.2, 0.9, shirt_ps[k], verts=10),
                 sphere("ph", (0, 0, 1.05), 0.18, skin_m, sub=1, smooth=False),
                 sphere("phr", (0, 0.03, 1.13), 0.17, mat("CHair%d" % k, (0.2, 0.12, 0.06), 0.8), scale=(1, 1, 0.6), sub=1, smooth=False)],
                "PersonProto%d" % k)
PEOPLE = [people_proto(k) for k in range(4)]
WHEAT = join([cyl("ws", (0, 0, 0.35), 0.02, 0.7, mat("WStem", (0.85, 0.7, 0.3), 0.7), verts=5),
              sphere("wh", (0, 0, 0.78), 0.06, wheat_m, scale=(1, 1, 2.4), sub=1, smooth=False)], "WheatProto")

def carpet(name, me_obj, density, s, seed, proto, poisson=0.0, upright=False):
    ng = bpy.data.node_groups.new(name + "GN", 'GeometryNodeTree')
    ng.interface.new_socket(name="Geometry", in_out='INPUT', socket_type='NodeSocketGeometry')
    ng.interface.new_socket(name="Geometry", in_out='OUTPUT', socket_type='NodeSocketGeometry')
    Nn = ng.nodes; Ln = ng.links
    gi = Nn.new('NodeGroupInput'); go = Nn.new('NodeGroupOutput')
    d = Nn.new('GeometryNodeDistributePointsOnFaces')
    if poisson:
        d.distribute_method = 'POISSON'
        d.inputs['Distance Min'].default_value = poisson
        d.inputs['Density Max'].default_value = density
    else:
        d.inputs['Density'].default_value = density
    d.inputs['Seed'].default_value = seed
    oi = Nn.new('GeometryNodeObjectInfo'); oi.inputs['Object'].default_value = proto
    ip = Nn.new('GeometryNodeInstanceOnPoints')
    Ln.new(gi.outputs[0], d.inputs['Mesh']); Ln.new(d.outputs['Points'], ip.inputs['Points'])
    Ln.new(oi.outputs['Geometry'], ip.inputs['Instance'])
    cx = Nn.new('ShaderNodeCombineXYZ'); rr = Nn.new('FunctionNodeRandomValue')
    rr.inputs['Min'].default_value = 0.0 if not upright else -0.3; rr.inputs['Max'].default_value = 6.283 if not upright else 0.3
    rr.inputs['Seed'].default_value = seed + 1
    Ln.new(rr.outputs[0], cx.inputs['Z']); Ln.new(cx.outputs[0], ip.inputs['Rotation'])
    rs = Nn.new('FunctionNodeRandomValue'); rs.inputs['Min'].default_value = s * 0.85; rs.inputs['Max'].default_value = s * 1.15
    rs.inputs['Seed'].default_value = seed + 2
    Ln.new(rs.outputs[0], ip.inputs['Scale'])
    Ln.new(ip.outputs[0], go.inputs[0])
    me_obj.modifiers.new("GN", 'NODES').node_group = ng
    return me_obj

def swarm(name, c, R, density, s, seed, layers=(1.0, 0.7, 0.4), squash=(1, 1, 0.75), core=None, spin=4.0):
    g = group(name, c)
    ch = []
    for k, f_ in enumerate(layers):
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3, radius=R * f_, location=c)
        o = bpy.context.object; o.name = name + "L%d" % k; o.scale = squash
        carpet(o.name, o, density, s, seed + 7 * k, LOC)
        ch.append(o)
    ch.append(sphere(name + "Core", c, R * 0.5, core or haze_m, scale=squash, sub=2))
    attach(ch, g)
    g.rotation_euler = (0, 0, 0); g.keyframe_insert("rotation_euler", frame=0)
    g.rotation_euler = (0, 0, spin); g.keyframe_insert("rotation_euler", frame=FRAMES)
    for fc in fcurves(g):
        if fc.data_path == "rotation_euler":
            for p in fc.keyframe_points:
                p.interpolation = 'LINEAR'
    return g

def plane_obj(name, cx, cy, sx, sy, z=0.0):
    bpy.ops.mesh.primitive_plane_add(size=1, location=(cx, cy, z))
    o = bpy.context.object; o.name = name; o.scale = (sx, sy, 1)
    bpy.ops.object.transform_apply(scale=True)
    return o

you, YD = person("You", (0, 40, 0), 1.0, mat("Shirt", (0.95, 0.35, 0.2), 0.6), mat("Pants", (0.2, 0.3, 0.55), 0.7),
                 skin_m, mat("Hair", (0.25, 0.14, 0.07), 0.8))

# =================== line 0: hook — a locust cloud rolls over the house toward you ===================
sw0 = swarm("Sw0", (0, 12, 6), 4.0, 3.0, 0.32, 1)
key_loc(sw0, [(0, (-6, 14, 7.5)), (E(0), (1, 10, 6))])
vis(sw0, [(0, S[1])])
sw0b = swarm("Sw0b", (6, 16, 8), 3.2, 3.0, 0.32, 3)
key_loc(sw0b, [(0, (2, 18, 9)), (E(0), (7, 15, 8))])
vis(sw0b, [(0, S[1])])
H0 = locust("H0", (0.6, 1.0, 1.7), 0.75, math.radians(-20), flying=True)
hover(H0, [(0, (-1.2, 1.8, 2.1)), (E(0), (0.8, 0.8, 1.6))], 0.1)
vis(H0, [(0, S[1])])

# =================== line 1: one locust on a kitchen scale (2 g) ===================
T = 0.85
TX, TY = -1.5, 0.6
tbl = [box("TableTop", (TX, TY, T - 0.03), (1.3, 0.75, 0.06), wood, bevel=0.01)]
for dx in (-0.58, 0.58):
    for dy in (-0.3, 0.3):
        tbl.append(box("TableLeg", (TX + dx, TY + dy, (T - 0.06) / 2), (0.06, 0.06, T - 0.06), wood))
scale_m = mat("ScaleBody", (0.97, 0.97, 0.98), 0.4)
plat_m = mat("ScalePlat", (0.75, 0.78, 0.82), 0.25, metal=0.6)
lcd_m = mat("LCD", (0.6, 0.9, 0.62), 0.4, emit=(0.5, 0.9, 0.55), emit_strength=0.8)
PT = T + 0.0925
SA = (TX, TY + 0.02)
tbl += [box("ScaleBase", (SA[0], SA[1], T + 0.035), (0.46, 0.46, 0.07), scale_m, bevel=0.012),
        box("ScalePlat", (SA[0], SA[1], T + 0.085), (0.42, 0.42, 0.015), plat_m, bevel=0.004),
        box("LCD", (SA[0], SA[1] - 0.235, T + 0.035), (0.3, 0.02, 0.07), lcd_m)]
for o in tbl:
    vis(o, [(S[1], S[3])])
r0 = text("Read0", "0.0 g", (SA[0], SA[1] - 0.247, T + 0.035), 0.055, ink_m); vis(r0, [(S[1], S[1] + 14)])
r1 = text("Read1", "2.0 g", (SA[0], SA[1] - 0.247, T + 0.035), 0.055, ink_m); vis(r1, [(S[1] + 14, S[2])])
LR = 0.14
H1 = locust("H1", (SA[0], SA[1], PT + 0.38 * LR), LR, math.radians(20))
vis(H1, [(S[1], S[2])])
hop(H1, (SA[0] + 0.45, SA[1] - 0.1, PT + 0.38 * LR), (SA[0], SA[1], PT + 0.38 * LR), S[1], S[1] + 12, 0.35)

# =================== line 2: it eats its own weight — a lettuce leaf vanishes ===================
H2 = locust("H2", (SA[0] - 0.12, SA[1], PT + 0.38 * LR), LR, math.radians(-70))
vis(H2, [(S[2], S[3])])
r2 = text("Read2", "2.0 g", (SA[0], SA[1] - 0.247, T + 0.035), 0.055, ink_m); vis(r2, [(S[2], S[3])])
LEAF = group("Leaf2", (SA[0] + 0.1, SA[1], PT + 0.03))
lv = [sphere("Leaf2a", (SA[0] + 0.1, SA[1], PT + 0.03), 0.12, leaf_m, scale=(1.2, 0.9, 0.25), sub=2),
      sphere("Leaf2b", (SA[0] + 0.12, SA[1] + 0.02, PT + 0.06), 0.09, leaf_dk, scale=(1.0, 0.8, 0.3), sub=2)]
attach(lv, LEAF)
keyscale(LEAF, [(0, 0.001), (S[2] - 1, 0.001), (S[2], 1.0), (W(2, 0.25), 1.0), (W(2, 0.95), 0.08), (E(2), 0.001)])
for k in range(4):
    burst((SA[0] + 0.05, SA[1] - 0.05, PT + 0.1), W(2, 0.25 + k * 0.15), n=6, r=0.08, size=0.012, material=leaf_m)

# =================== line 3: secretly a grasshopper (green twin = yellow locust) ===================
G3 = locust("G3", (-0.7, 0.6, 0.12), 0.3, math.radians(-25), green=True)
Y3 = locust("Y3", (0.7, 0.6, 0.12), 0.3, math.radians(25))
vis(G3, [(S[3], S[4])]); vis(Y3, [(S[3], S[4])])
hop(G3, (-1.4, 0.9, 0.12), (-0.7, 0.6, 0.12), S[3], S[3] + 8, 0.6)
hop(Y3, (1.4, 0.9, 0.12), (0.7, 0.6, 0.12), S[3] + 4, S[3] + 12, 0.6)
eq = text("Eq3", "=", (0, 0.6, 0.35), 0.7, white_lab, extrude=0.06)
vis(eq, [(S[3] + 12, S[4])], tuple(eq.scale))
tufts = []
for k in range(26):
    p = (random.uniform(-3, 3), random.uniform(-0.6, 2.4), 0)
    tf = cyl("Tuft", (p[0], p[1], 0.12), 0.07, 0.24, loc_gd, verts=5, r2=0.0)
    tufts.append(tf)
    vis(tf, [(S[3], S[6])])

# =================== line 4: crowd them together — green grasshoppers pile in ===================
CR = (0.0, 0.8)
GREEN, YEL = [], []
for k in range(14):
    a = k / 14 * 6.283
    rr_ = 0.45 + 0.35 * (k % 3)
    p1 = (CR[0] + rr_ * math.cos(a), CR[1] + rr_ * 0.6 * math.sin(a), 0.1)
    p0 = (CR[0] + 3.2 * math.cos(a), CR[1] + 1.6 * math.sin(a), 0.1)
    rz = math.atan2(p1[1] - p0[1], p1[0] - p0[0]) + math.pi / 2
    g_ = locust("Gc%d" % k, p1, 0.26, rz, green=True)
    f0 = S[4] + (k % 5) * 3
    hop(g_, p0, p1, f0, f0 + 9, 0.7)
    vis(g_, [(S[4], W(5, 0.3))])
    y_ = locust("Yc%d" % k, p1, 0.26, rz, flying=True)
    vis(y_, [(W(5, 0.3), S[6])])
    key_loc(y_, [(W(5, 0.3), p1), (W(5, 0.55), p1),
                 (E(5), (p1[0] * 1.4, p1[1] + 0.3, 1.6 + 0.4 * (k % 4)))])
    jitter(y_, 0.05, 3.0)
    GREEN.append(g_); YEL.append(y_)
    burst((p1[0], p1[1] - 0.1, 0.35), W(5, 0.3), n=6, r=0.3, size=0.03, f_out=W(5, 0.3) + 8)
for k in range(4):
    burst((CR[0] + random.uniform(-0.5, 0.5), CR[1] - 0.3, 0.4), S[4] + 12 + k * 4, n=6, r=0.25, size=0.03)
for k in range(3):
    bpy.ops.mesh.primitive_torus_add(major_radius=0.8, minor_radius=0.03, location=(CR[0], CR[1], 0.4))
    rg = bpy.context.object; rg.data.materials.append(frame_glow)
    f = W(5, 0.3) + k * 5
    keyscale(rg, [(0, 0.001), (f - 1, 0.001), (f, 0.3), (f + 12, 2.6), (f + 13, 0.001)])

# =================== line 6: 1,000 — a buzzing little cloud ===================
sw6 = swarm("Sw6", (0.3, 1.6, 1.6), 1.1, 18.0, 0.13, 6, layers=(1.0, 0.7))
vis(sw6, [(S[6], S[7])])
key_loc(sw6, [(S[6], (-1.4, 1.6, 1.4)), (E(6), (0.8, 1.4, 1.8))])

# =================== line 7: 1,000,000 — the vegetable garden is gone ===================
CAB = []
for k in range(21):
    x_ = -3.0 + (k % 7) * 1.0
    y_ = 0.6 + (k // 7) * 1.1
    c = sphere("Cab%d" % k, (x_, y_, 0.35), 0.42, cab_ms[(k // 7) % 3], scale=(1, 1, 0.8), sub=2, smooth=False)
    f_eat = W(7, 0.3 + 0.6 * (k % 7) / 6)
    keyscale(c, [(0, 0.001), (S[7] - 1, 0.001), (S[7], 1.0), (f_eat - 6, 1.0), (f_eat, 0.05), (E(7) - 1, 0.05), (E(7), 0.001)])
    st = cyl("CabStub%d" % k, (x_, y_, 0.05), 0.08, 0.1, mat("Stub", (0.4, 0.55, 0.2), 0.8), verts=6)
    vis(st, [(S[7], S[8])])
    burst((x_, y_ - 0.45, 0.4), f_eat - 4, n=6, r=0.4, size=0.05, material=leaf_m, f_out=f_eat + 6)
bed = box("Bed7", (0, 1.7, 0.02), (7.6, 3.6, 0.06), dirt_m)
vis(bed, [(S[7], S[8])])
sw7 = swarm("Sw7", (0, 1.7, 1.2), 2.0, 9.0, 0.2, 7, squash=(1.6, 1.0, 0.45))
vis(sw7, [(S[7], S[8])])
key_loc(sw7, [(S[7], (-6, 1.7, 1.4)), (W(7, 0.3), (-3.2, 1.7, 1.2)), (E(7), (3.2, 1.7, 1.1))])

# =================== line 8 & 15: billions fill the sky over the town ===================
SKY = []
for k, (c, R) in enumerate([((-8, 10, 7), 4.5), ((3, 8, 6), 4.0), ((12, 14, 8), 4.8), ((-16, 20, 9), 5.0),
                            ((6, 22, 10), 5.4), ((-3, 18, 9), 4.4), ((18, 4, 6), 3.6), ((-18, 4, 5.5), 3.8)]):
    o = swarm("Sky%d" % k, c, R, 1.6, 0.42, 70 + k, layers=(1.0, 0.75))
    SKY.append(o)
    vis(o, [(S[8] + 2 * k, S[9]), (S[15], S[16])])
FARSKY = []
for k in range(10):
    c = (random.uniform(-90, 90), random.uniform(60, 160), random.uniform(18, 35))
    o = swarm("FarSky%d" % k, c, random.uniform(12, 18), 0.15, 1.5, 120 + k, layers=(1.0,))
    vis(o, [(S[15] + k, S[16])])
    FARSKY.append(o)

# =================== line 9: 2,000 tons of locusts outweigh a pile of cars on a seesaw ===================
PX, PY, PZ = 0.0, 3.0, 1.4
pivot = cyl("Pivot", (PX, PY, 0.65), 0.95, 1.3, mat("PivotM", (0.3, 0.32, 0.38), 0.6), verts=3)
pivot.rotation_mode = 'ZXY'; pivot.rotation_euler = (math.radians(90), 0, math.radians(90))
plank = group("Plank", (PX, PY, PZ))
pl = box("PlankBoard", (PX, PY, PZ), (10.0, 2.4, 0.22), mat("SeeSaw", (0.95, 0.75, 0.2), 0.5), bevel=0.04)
bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3, radius=1.6, location=(PX - 3.2, PY, PZ + 1.65))
lball = bpy.context.object; lball.name = "LocBall"; lball.data.materials.append(haze_m)
carpet("LocBallC", lball, 30.0, 0.16, 8, LOC)
lcore = sphere("LocCore", (PX - 3.2, PY, PZ + 1.65), 1.5, loc_stripe(3.0), sub=3)
car_cols = [(0.9, 0.15, 0.12), (0.15, 0.45, 0.9), (0.95, 0.85, 0.2), (0.2, 0.7, 0.35), (0.95, 0.95, 0.95)]
car_ms = [mat("Car%d" % k, c, 0.3, metal=0.3) for k, c in enumerate(car_cols)]
tyre_m = mat("Tyre", (0.06, 0.06, 0.07), 0.8)
cglass = mat("CarGlass", (0.4, 0.6, 0.8), 0.1)
cars = []
def car(x, y, z, k, rz=0.0, s=1.0):
    ps = [box("CarBody", (x, y, z + 0.22 * s), (1.0 * s, 0.5 * s, 0.26 * s), car_ms[k % 5], bevel=0.04 * s),
          box("CarCab", (x - 0.05 * s, y, z + 0.44 * s), (0.55 * s, 0.44 * s, 0.22 * s), cglass, bevel=0.04 * s)]
    for dx in (-0.32, 0.32):
        for dy in (-0.24, 0.24):
            ps.append(cyl("Wheel", (x + dx * s, y + dy * s, z + 0.1 * s), 0.1 * s, 0.07 * s, tyre_m, rot=(math.radians(90), 0, 0), verts=12))
    g = group("Car", (x, y, z), rz); attach(ps, g)
    return g, ps
for lvl in range(3):
    for i_ in range(4 - lvl):
        for j_ in range(3):
            g_, ps = car(PX + 1.7 + i_ * 0.9 + lvl * 0.45, PY - 0.8 + j_ * 0.8, PZ + 0.11 + lvl * 0.5, i_ + j_ + lvl, 0, 0.85)
            cars += ps
attach([pl, lball, lcore] + cars, plank)
vis(pivot, [(S[9], S[10])], tuple(pivot.scale)); vis(plank, [(S[9], S[10])])
for f, a in [(S[9], math.radians(10)), (S[9] + 6, math.radians(10)), (S[9] + 16, math.radians(-14)), (S[9] + 22, math.radians(-10)),
             (S[9] + 28, math.radians(-13))]:
    plank.rotation_euler = (0, a, 0); plank.keyframe_insert("rotation_euler", frame=f)
burst((PX - 3.2, PY - 1.4, 0.6), S[9] + 16, n=12, r=1.4, size=0.06, f_out=E(9))

# =================== line 10: the cloud covers over ten square kilometers of town ===================
TOWN = []
for k, (cx, cy, sx_, sy_) in enumerate([(-24, 30, 30, 40), (24, 30, 30, 40), (0, 62, 80, 30), (-50, 40, 20, 50), (50, 40, 20, 50)]):
    o = plane_obj("Town%d" % k, cx, cy, sx_, sy_, 0.0)
    carpet(o.name, o, 1.0, 1.6, 200 + k, HOUSES[k % 3], poisson=3.0, upright=True)
    TOWN.append(o)
    vis(o, [(S[10], S[12])])
TC = (0, 30, 9)
big = swarm("Big10", TC, 14.0, 0.25, 1.2, 300, layers=(1.0, 0.8), squash=(1.5, 1.2, 0.35), spin=1.0)
vis(big, [(S[10] + 4, S[12])])
key_loc(big, [(S[10], (-30, 30, 9)), (W(10, 0.5), (0, 30, 9)), (E(11), (4, 28, 9))])
shadow = cyl("Shadow10", (0, 30, 0.08), 18, 0.05, mat("ShadowM", (0.05, 0.04, 0.03), 1.0), verts=40)
shadow.scale = (1.4, 1.1, 1)
vis(shadow, [(W(10, 0.5), S[12])], tuple(shadow.scale))
key_loc(shadow, [(W(10, 0.5), (0, 30, 0.08)), (E(11), (4, 28, 0.08))])
fr10 = []
for (a, b) in [((-20, 14), (20, 14)), ((20, 14), (20, 46)), ((20, 46), (-20, 46)), ((-20, 46), (-20, 14))]:
    fr10.append(seg("Frame10", (a[0], a[1], 0.3), (b[0], b[1], 0.3), 0.35, frame_glow, verts=8))
for o in fr10:
    vis(o, [(W(10, 0.55), S[11])], tuple(o.scale))

# =================== line 11: the sky over your town goes dark ===================
dk11 = swarm("Dark11", (0, 18, 12), 12.0, 0.6, 0.8, 330, layers=(1.0, 0.8), squash=(1.6, 1.0, 0.3), core=dark_haze, spin=1.5)
vis(dk11, [(S[11], S[12])])
key_loc(dk11, [(S[11], (-10, 18, 12)), (E(11), (4, 18, 11))])
bg_s = bg.inputs["Strength"]
for f, v in [(0, 0.85), (S[11], 0.85), (S[11] + 8, 0.12), (E(11) - 1, 0.12), (E(11), 0.85)]:
    bg_s.default_value = v; bg_s.keyframe_insert("default_value", frame=f)
for f, v in [(0, 4.2), (S[11], 4.2), (S[11] + 8, 0.25), (E(11) - 1, 0.25), (E(11), 4.2)]:
    sun.data.energy = v; sun.data.keyframe_insert("energy", frame=f)
wb = win_m.node_tree.nodes["Principled BSDF"]
wb.inputs["Emission Color"].default_value = (1.0, 0.75, 0.3, 1)
for f, v in [(0, 0.0), (S[11] + 4, 0.0), (S[11] + 10, 6.0), (E(11) - 1, 6.0), (E(11), 0.0)]:
    wb.inputs["Emission Strength"].default_value = v; wb.inputs["Emission Strength"].keyframe_insert("default_value", frame=f)
lamp_m = glow_mat("Lamp", (1.0, 0.8, 0.4), 8.0)
for x in (HX - 3.3, HX + 3.3):
    cyl("LampPost", (x, fy - 3.2, 0.9), 0.05, 1.8, loc_k, verts=8)
    lb = sphere("LampBulb", (x, fy - 3.2, 1.9), 0.18, lamp_m, sub=2)
    vis(lb, [(S[11] + 8, S[12])])

# =================== line 12: they eat two thousand tons of food a day — a wheat field vanishes ===================
WF = []
soil12 = box("Soil12", (0, 2.6, 0.02), (16.5, 5.6, 0.04), dirt_m)
vis(soil12, [(S[12], S[13])])
for k in range(8):
    x0 = -7.0 + k * 2.0
    o = plane_obj("Wheat%d" % k, x0, 2.6, 2.0, 5.4, 0.04)
    carpet(o.name, o, 30.0, 1.0, 400 + k, WHEAT, upright=True)
    vis(o, [(S[12], W(12, 0.25 + 0.09 * k))])
    burst((x0, 0.0, 0.6), W(12, 0.25 + 0.09 * k) - 2, n=8, r=0.9, size=0.05, material=wheat_m, f_out=W(12, 0.25 + 0.09 * k) + 6)
    WF.append(o)
sw12 = swarm("Sw12", (0, 2.6, 1.6), 2.6, 6.0, 0.24, 12, squash=(1.5, 1.0, 0.45))
vis(sw12, [(S[12], S[13])])
key_loc(sw12, [(S[12], (-10, 2.6, 1.6)), (W(12, 0.25), (-7, 2.6, 1.4)), (E(12), (8, 2.6, 1.3))])

# =================== line 13: food for hundreds of thousands of people ===================
CROWD = []
for k, (cx, cy, sx_, sy_) in enumerate([(-9, 4, 8, 10), (9, 4, 8, 10), (0, 10.5, 26, 4), (-5, -0.3, 6, 1.8), (5, -0.3, 6, 1.8)]):
    for j in range(2):
        o = plane_obj("Crowd%d_%d" % (k, j), cx, cy, sx_, sy_, 0.0)
        carpet(o.name, o, 6.0, 1.0, 500 + 10 * k + j, PEOPLE[(k + 2 * j) % 4], poisson=0.55, upright=True)
        vis(o, [(S[13] + k, S[14])])
        CROWD.append(o)
pile = cyl("GrainPile", (0, 3.6, 0), 3.4, 2.6, grain_m, verts=28, r2=0.0)
pile.data.transform(Matrix.Translation((0, 0, 1.3)))
pile.location = (0, 3.6, 0)
keyscale(pile, [(0, 0.001), (S[13] - 1, 0.001), (S[13], 1.0), (W(13, 0.3), 1.0), (E(13) - 1, (1, 1, 0.15)), (E(13), 0.001)])
sw13 = swarm("Sw13", (0, 3.6, 3.2), 2.4, 6.0, 0.24, 13, squash=(1.3, 1.0, 0.6))
vis(sw13, [(S[13], S[14])])
key_loc(sw13, [(S[13], (0, 3.6, 4.0)), (E(13), (0, 3.6, 2.0))])
for k in range(10):
    p0 = (random.uniform(-2, 2), random.uniform(2.5, 4.5), 2.0)
    gr = sphere("GrainFly", p0, 0.12, grain_m, sub=1)
    f0 = S[13] + 6 + k * 2
    key_loc(gr, [(f0, p0), (f0 + 10, (p0[0] * 2.5, p0[1] - 1.5, 0.2))])
    vis(gr, [(f0, f0 + 11)])

# =================== line 14: riding the wind, 150 km a day ===================
road = box("Road14", (0, 1.4, 0.02), (60, 2.4, 0.05), road_m)
vis(road, [(S[14], S[15])])
for k in range(20):
    d_ = box("RoadDash", (-28 + k * 3, 1.4, 0.05), (1.4, 0.15, 0.02), white_lab)
    vis(d_, [(S[14], S[15])])
sw14 = swarm("Sw14", (0, 3.5, 3.0), 3.0, 4.0, 0.3, 14, squash=(1.8, 1.0, 0.5))
vis(sw14, [(S[14], S[15])])
key_loc(sw14, [(S[14], (-14, 4.0, 3.2)), (E(14), (10, 4.0, 3.0))])
for k in range(16):
    y_ = random.uniform(1.0, 8.0); z_ = random.uniform(1.0, 6.0); L_ = random.uniform(2.0, 4.0)
    st = seg("Wind", (0, 0, 0), (L_, 0, 0), 0.04, streak_m, verts=6)
    f0 = S[14] + k * 2
    x0 = random.uniform(-12, -4)
    key_loc(st, [(f0, (x0, y_, z_)), (f0 + 16, (x0 + 18, y_, z_))])
    vis(st, [(f0, min(f0 + 17, S[15]))])
SGX = 1.8
post = cyl("SignPost", (SGX, 0.0, 1.0), 0.08, 2.0, wood, verts=8)
board = box("SignBoard", (SGX, -0.02, 1.9), (2.6, 0.12, 0.9), mat("SignGreen", (0.1, 0.5, 0.25), 0.5), bevel=0.04)
st14 = text("Sign14", "150 km", (SGX, -0.1, 1.9), 0.42, white_lab, extrude=0.02)
for o in (post, board):
    vis(o, [(S[14], S[15])])
vis(st14, [(S[14] + 4, S[15])], tuple(st14.scale))

# =================== line 16: you at the door — stay inside or go look? ===================
H16 = locust("H16", (HX - 2.2, fy - 1.6, 1.6), 0.4, math.radians(-30), flying=True)
vis(H16, [(S[16], FRAMES)])
hover(H16, [(S[16], (HX - 2.6, fy - 1.8, 1.8)), (FRAMES, (HX - 1.8, fy - 1.4, 1.5))], 0.08)
H16b = locust("H16b", (HX + 1.4, fy - 2.4, 1.0), 0.32, math.radians(30), flying=True)
vis(H16b, [(S[16], FRAMES)])
hover(H16b, [(S[16], (HX + 1.8, fy - 2.6, 1.2)), (FRAMES, (HX + 1.0, fy - 2.2, 0.9))], 0.06)

for k, (c, R) in enumerate([((-9, 30, 13), 4.5), ((8, 32, 14), 5.0), ((0, 40, 17), 5.5), ((-16, 40, 15), 4.0), ((16, 24, 11), 3.5)]):
    o = swarm("End%d" % k, c, R, 1.6, 0.42, 160 + k, layers=(1.0, 0.75))
    vis(o, [(S[16] + k, FRAMES)])

# =================== "you" placement ===================
jumps(you, [(0, (2.4, 3.0, 0)), (S[1], (0, 40, 0)), (S[16], (HX - 0.9, fy - 0.5, 0))])
vis(you, [(0, S[1]), (S[16], FRAMES)])
for k, ag in enumerate(YD["arms"]):
    sx = -1 if k == 0 else 1
    keyrot(ag, [(0, (0, sx * math.radians(150), 0)), (S[1], (0, 0, 0)),
                (S[16], (0, sx * math.radians(60) if k == 0 else math.radians(120), 0))])
    for fc in fcurves(ag):
        for p in fc.keyframe_points:
            p.interpolation = 'CONSTANT'

# ---------------- views (camera, subject) per line; subject sits in the lower third ----------------
def orb(subj, dist, az0, az1, h=1.0, d1=None):
    d1 = dist if d1 is None else d1
    a0, a1 = math.radians(az0), math.radians(az1)
    return ((subj[0] + math.sin(a0) * dist, subj[1] - math.cos(a0) * dist, subj[2] + h), subj), \
           ((subj[0] + math.sin(a1) * d1, subj[1] - math.cos(a1) * d1, subj[2] + h), subj)
V, V2 = {}, {}
V[0], V2[0] = orb((0.6, 4.0, 1.6), 15.0, -14, -2, 2.0, 12.0)
V[1], V2[1] = orb((SA[0], SA[1], PT + 0.06), 1.2, 12, -10, 0.3, 1.0)
V[2], V2[2] = orb((SA[0], SA[1], PT + 0.06), 1.0, -14, 8, 0.25, 0.85)
V[3], V2[3] = orb((0.0, 0.6, 0.25), 3.2, 10, -8, 0.4, 2.7)
V[4], V2[4] = orb((CR[0], CR[1], 0.3), 4.2, -12, 8, 0.5, 3.6)
V[5], V2[5] = orb((CR[0], CR[1], 0.6), 5.0, 10, -8, 0.6, 6.0)
V[6], V2[6] = orb((0.0, 1.5, 1.3), 6.5, -10, 8, 0.6, 5.8)
V[7], V2[7] = orb((0.0, 1.7, 0.4), 9.0, 10, -6, 0.8, 8.0)
V[8], V2[8] = orb((0.0, 10.0, 3.0), 30.0, -10, 6, 5.0, 36.0)
V[9], V2[9] = orb((PX, PY, 2.0), 15.0, 6, -6, 1.0, 13.5)
V[10], V2[10] = orb((0.0, 30.0, 2.0), 70.0, -8, 6, 30.0, 64.0)
V[11], V2[11] = orb((HX, HY - 2, 1.5), 22.0, 6, -6, 3.0, 19.0)
V[12], V2[12] = orb((0.0, 2.6, 0.5), 15.0, -8, 6, 3.0, 13.5)
V[13], V2[13] = orb((0.0, 4.0, 0.8), 19.0, 6, -6, 4.0, 17.0)
V[14], V2[14] = orb((0.0, 2.5, 1.0), 14.0, -10, 8, 2.0, 12.5)
V[15], V2[15] = orb((0.0, 12.0, 4.0), 48.0, 8, -6, 10.0, 58.0)
V[16], V2[16] = orb((HX - 0.6, fy - 1.0, 1.2), 15.0, -8, 6, 2.0, 18.0)
VM = {i: (tuple((Vector(V[i][0]) + Vector(V2[i][0])) / 2), V[i][1]) for i in V}

def LB(i, name, body, m_, size=None, f_in=None, f_out=None, Dk=0.55, end=False, v=0.26, u=0.0):
    view = V2[i] if end else VM[i]
    cl = Vector(CL(view)); D = (Vector(view[1]) - cl).length * Dk
    s_ = 0.85 * fit(body, D, size if size else 1e9)
    return label(name, body, view, D, v, s_, m_, (S[i] + 3) if f_in is None else f_in,
                 E(i) if f_out is None else f_out, u)
LB(0, "L0", "1 BILLION?!", red_lab)
LB(1, "L1", "2 GRAMS", lab_m, v=0.3)
LB(2, "L2", "EATS 2 g A DAY", green_lab, v=0.3)
LB(3, "L3", "SAME BUG!", green_lab)
LB(4, "L4", "TOO CROWDED...", white_lab)
LB(5, "L5", "TRANSFORM!", lab_m)
LB(6, "L6", "1,000", lab_m)
LB(7, "L7", "GARDEN: GONE!", red_lab)
LB(8, "L8", "1 BILLION", red_lab, Dk=0.4)
LB(9, "L9", "2,000 TONS", lab_m, Dk=0.45)
LB(10, "L10", "10+ SQ KM", lab_m, Dk=0.45)
LB(11, "L11", "DARK!", white_lab, Dk=0.45)
LB(12, "L12", "2,000 TONS / DAY", lab_m, Dk=0.45)
LB(13, "L13", "100,000+ PEOPLE", white_lab, Dk=0.45)
LB(14, "L14", "150 km A DAY", blue_lab, Dk=0.45)
LB(15, "L15", "100s OF BILLIONS", lab_m, Dk=0.45)
LB(16, "L16", "STAY IN OR GO LOOK?", lab_m, end=True, f_in=S[16] + 6, Dk=0.45)

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
    target.location = aim(cl, tl); target.keyframe_insert("location", frame=f)
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
