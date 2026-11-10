# Day 16 — What if you were as tough as a tardigrade?  Build: python3 episodes/016-tardigrade/scene.py
# Reference style: base (helpers, lawn/soil, house, garden, camera helpers) copied from episodes/012-croc-bite (003-lift-million-ref / 006-mantis-punch)
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
FRONT_Y = 0.5
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
box("Ground", (0, 26.95, -6.0), (400, 52.9, 12.0), grass_m)
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
# Day 16 — What if you were as tough as a tardigrade?
# Facts used: tardigrades ("water bears") are mostly ~0.3-0.5 mm long (largest ~1.2 mm), 8 stubby clawed legs,
#   live in the water film on moss/lichen. Dried out they retract into a "tun" with metabolism near zero.
#   Tsujimoto et al. 2016: tardigrades from moss frozen in Antarctica in 1983 revived after 30.5 years.
#   Tuns survived ~1 K (-272 C) briefly (Becquerel 1950) and ~150 C for minutes (Rahm, 1920s; tun state).
#   Tuns survived ~600 MPa (~6x the ~110 MPa at the bottom of the Mariana Trench) (Seki & Toyoshima 1998).
#   FOTON-M3 2007 (Jonsson et al. 2008): 10 days exposed to open space vacuum; many survived (fewer with full UV).
#   Lethal radiation for humans ~5 Gy, many tardigrades tolerate ~5,000 Gy -> "about 1,000 times".
#   Dsup protein binds DNA and reduces X-ray damage (Hashimoto et al. 2016).
#   The catch: most extreme tolerance only in the dried tun state.
# =====================================================================================
random.seed(16)
CY = 2.6
gspark_m = glow_mat("GSpark", (0.4, 1.0, 0.4), 4.0)
cspark_m = glow_mat("CSpark", (0.4, 0.95, 1.0), 4.0)
ospark_m = glow_mat("OSpark", (1.0, 0.55, 0.1), 5.0)
snow_m = mat("Snow", (1, 1, 1), 0.5, emit=(0.9, 0.95, 1.0), emit_strength=0.6)

def wpos(o):
    bpy.context.view_layer.update()
    return tuple(o.matrix_world.translation)
def join(parts, name):
    bpy.ops.object.select_all(action='DESELECT')
    for p_ in parts:
        p_.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]
    bpy.ops.object.convert(target='MESH'); bpy.ops.object.join()
    o = bpy.context.object; o.name = name
    return o
def alpha_mat(name, color, a, emit_s=0.2):
    m = mat(name, color, 0.08, emit=color, emit_strength=emit_s)
    m.node_tree.nodes["Principled BSDF"].inputs["Alpha"].default_value = a
    return m
def aim_obj(o, p, tgt):
    o.rotation_mode = 'QUATERNION'
    o.rotation_quaternion = (Vector(tgt) - Vector(p)).to_track_quat('Z', 'Y')
def beam(name, p0, p1, r, m_):
    d = Vector(p1) - Vector(p0)
    o = cyl(name, tuple((Vector(p0) + Vector(p1)) / 2), r, d.length, m_, verts=8)
    aim_obj(o, (0, 0, 0), tuple(d))
    return o
def shatter_at(c0, f, n, r, ms, spread=1.0, f_gone=None):
    for i in range(n):
        th = random.uniform(0, 6.283); ph = random.uniform(-0.3, 1.0)
        d = Vector((math.cos(th) * math.cos(ph), math.sin(th) * math.cos(ph) * 0.6 - 0.4, math.sin(ph)))
        p0 = tuple(Vector(c0) + d * r * 0.4)
        ch = box("Shard", p0, (r * random.uniform(0.3, 0.5),) * 3, random.choice(ms))
        p1 = tuple(Vector(c0) + d * r * 3 * spread + Vector((0, 0, 0.6)))
        p2 = (c0[0] + d.x * r * 5 * spread, c0[1] + d.y * r * 5 * spread, 0.08)
        key_loc(ch, [(f, p0), (f + 7, p1), (f + 16, p2)])
        ch.rotation_euler = (0, 0, 0); ch.keyframe_insert("rotation_euler", frame=f)
        ch.rotation_euler = (random.uniform(3, 8), random.uniform(3, 8), 0); ch.keyframe_insert("rotation_euler", frame=f + 16)
        keyscale(ch, [(0, 0.001), (f - 1, 0.001), (f, 1.0)] + ([(f_gone - 3, 1.0), (f_gone, 0.001)] if f_gone else []))
def snow(cx, cy, f0, f1, n, spread, zt=3.6):
    for k in range(n):
        L_ = random.randint(18, 28)
        fs = random.randint(f0, max(f0, f1 - L_))
        x, y = cx + random.uniform(-spread, spread), cy + random.uniform(-spread * 0.7, spread * 0.7)
        fl = sphere("Flake", (x, y, zt), random.uniform(0.035, 0.06), snow_m, sub=1)
        key_loc(fl, [(fs, (x, y, zt)), (fs + L_, (x + random.uniform(0.3, 0.8), y, 0.05))])
        keyscale(fl, [(0, 0.001), (fs - 1, 0.001), (fs, 1.0), (fs + L_, 1.0), (fs + L_ + 1, 0.001)])

# ---------------- moss cushion ----------------
moss_ms = [mat("Moss1", (0.2, 0.55, 0.12), 0.9), mat("Moss2", (0.35, 0.68, 0.18), 0.9), mat("Moss3", (0.14, 0.42, 0.1), 0.9)]
moss = []
for k in range(70):
    a = random.uniform(0, 6.283); r_ = 2.2 * math.sqrt(random.random())
    moss.append(sphere("Moss", (r_ * math.cos(a) * 1.15, CY + r_ * math.sin(a) * 0.85, 0.02), random.uniform(0.18, 0.32),
                       random.choice(moss_ms), scale=(1, 1, 0.55), sub=1, smooth=False))
sprigs = []
for k in range(26):
    a = random.uniform(0, 6.283); r_ = random.uniform(1.4, 2.4)
    x, y = r_ * math.cos(a) * 1.15, CY + r_ * math.sin(a) * 0.85
    s_ = cyl("Sprig", (x, y, 0.25), 0.04, 0.45, moss_ms[1], verts=6)
    tp = sphere("SprigTip", (x, y, 0.5), 0.08, moss_ms[0], sub=1, smooth=False)
    sprigs += [s_, tp]
drop_m = mat("Drop", (0.55, 0.85, 1.0), 0.05, emit=(0.4, 0.75, 1.0), emit_strength=1.0)
drops = [sphere("Drop", (random.uniform(-2.2, 2.2), CY + random.uniform(-1.7, 0.2), 0.22), 0.07, drop_m, scale=(1, 1, 0.8), sub=2) for k in range(14)]

# ---------------- the cartoon tardigrade (~2.6 m "zoomed"), head toward +x ----------------
tg_m = stripe_mat("TG", (0.93, 0.68, 0.57), (0.83, 0.56, 0.46), axis="X", freq=9.0, thresh=0.7, rough=0.55)
tgd_m = mat("TGD", (0.78, 0.5, 0.42), 0.6)
claw_m = mat("Claw", (0.25, 0.18, 0.15), 0.5)
tp_ = []
for x_, r_ in ((-0.95, 0.5), (-0.35, 0.58), (0.3, 0.58), (0.85, 0.52)):
    tp_.append(sphere("TGSeg", (x_, CY, 0.78), r_, tg_m, scale=(0.95, 0.95, 0.85), sub=3))
tp_.append(sphere("TGHead", (1.35, CY, 0.82), 0.44, tg_m, sub=3))
tp_.append(cyl("TGSnout", (1.78, CY, 0.74), 0.22, 0.36, tg_m, rot=(0, math.radians(90), 0), r2=0.14, verts=20))
tp_.append(cyl("TGMouth", (1.97, CY, 0.74), 0.1, 0.03, eyeb, rot=(0, math.radians(90), 0), verts=16))
for sy in (-1, 1):
    tp_.append(sphere("TGEyeW", (1.62, CY + sy * 0.2, 1.02), 0.1, eyew, sub=2))
    tp_.append(sphere("TGEyeB", (1.7, CY + sy * 0.21, 1.03), 0.055, eyeb, sub=2))
    tp_.append(sphere("TGBlush", (1.6, CY + sy * 0.36, 0.82), 0.07, mat("Blush", (1.0, 0.45, 0.5), 0.6), scale=(1, 0.5, 0.7), sub=1))
legs = []
for i, x_ in enumerate((-1.1, -0.4, 0.3, 0.95)):
    for sy in (-1, 1):
        hip = (x_, CY + sy * 0.42, 0.55)
        lg = group("TGLegG", hip)
        foot = (x_ + (-0.15 if i == 0 else 0.05), CY + sy * 0.72, 0.12)
        pts = [tube("TGLeg", [hip, ((hip[0] + foot[0]) / 2, (hip[1] + foot[1]) / 2, 0.32), foot], [0.17, 0.15, 0.13], tg_m)]
        for c in range(3):
            a = (c - 1) * 0.5
            cl_ = cyl("TGClaw", (foot[0] + 0.1 * math.cos(a), foot[1] + sy * 0.05 + 0.1 * math.sin(a) * sy, 0.05), 0.03, 0.14, claw_m,
                      rot=(0, math.radians(100), a), r2=0.004, verts=6)
            pts.append(cl_)
        attach(pts, lg)
        legs.append((lg, i, sy))
TG = group("TG", (0, CY, 0))
attach(tp_ + [l[0] for l in legs], TG)
# paddling legs all the time
for lg, i, sy in legs:
    ph = (i + (sy > 0)) % 2
    for f in range(0, FRAMES + 12, 10):
        a = 0.28 if (f // 10 + ph) % 2 else -0.28
        lg.rotation_euler = (0, a, 0); lg.keyframe_insert("rotation_euler", frame=f)

# ---------------- tun (dried ball) ----------------
tun_m = stripe_mat("Tun", (0.62, 0.42, 0.26), (0.48, 0.3, 0.18), axis="X", freq=16.0, thresh=0.4, rough=0.85)
tun = sphere("Tun", (0, CY, 0.52), 1.0, tun_m, scale=(0.95, 0.75, 0.55), sub=3)
tunf = []
for sy in (-1, 1):   # sleepy closed eyes
    tunf.append(tube("TunEye", [(0.82, CY + sy * 0.18 - 0.08, 0.72), (0.88, CY + sy * 0.18, 0.69), (0.82, CY + sy * 0.18 + 0.08, 0.72)], [0.018] * 3, eyeb))
tunG = group("TunG", (0, CY, 0)); attach([tun] + tunf, tunG)

# ---------------- people (hidden until line 11) ----------------
MX, MY = 4.6, 1.3
you, Y = person("You", (MX, MY, 0.0), 1.0, mat("ShirtY", (0.95, 0.35, 0.25), 0.7), mat("PantsY", (0.2, 0.25, 0.45), 0.8),
                skin_m, mat("HairY", (0.28, 0.16, 0.07), 0.8))

# =====================================================================================
# per-line views
# =====================================================================================
V = {}
V[0] = ((2.8, -4.6, 1.6), (0.3, CY, 0.7))
V[1] = ((-1.6, -4.8, 1.5), (0.2, CY, 0.6))
V[2] = ((3.6, -3.0, 1.2), (0.8, CY, 0.6))
V[3] = ((0.6, -4.2, 1.4), (0.0, CY, 0.5))
V[4] = ((-2.6, -4.0, 1.6), (0.0, CY, 0.7))
V[5] = ((-3.4, -4.4, 1.8), (-1.0, CY, 0.9))
V[6] = ((0.2, -4.8, 1.8), (-0.9, CY, 0.9))
V[7] = ((2.6, -5.0, 1.8), (0.0, CY, 0.7))
V[8] = ((1.6, -8.6, 2.0), (0.0, CY, 2.6))
V[9] = ((-3.6, -4.8, 1.8), (-1.0, CY, 0.8))
V[10] = ((4.2, -3.8, 1.8), (1.5, CY - 0.2, 0.9))
V[11] = ((MX + 1.0, MY - 3.8, 1.6), (MX, MY, 1.0))
V[12] = ((MX - 1.2, MY - 3.6, 1.6), (MX, MY, 1.0))
V[13] = ((MX + 0.8, MY - 3.6, 1.6), (MX, MY, 1.1))
V[14] = ((MX - 0.6, MY - 4.8, 1.8), (MX, MY, 1.2))
V[15] = ((MX + 0.6, MY - 3.4, 1.4), (MX, MY, 0.6))
V[16] = ((3.0, -7.2, 2.4), (2.4, 1.6, 0.8))
DR = {0: (-0.8, 0.6, 0), 1: (0.9, 0.6, 0), 2: (-0.6, 0.5, 0), 3: (0.6, 0.6, 0), 4: (0.6, 0.5, 0), 5: (0.6, 0.5, 0),
      6: (-0.6, 0.5, 0), 7: (-0.7, 0.6, 0), 8: (-0.8, 0.8, 0), 9: (0.6, 0.5, 0), 10: (-0.6, 0.5, 0), 11: (-0.6, 0.5, 0),
      12: (0.6, 0.5, 0), 13: (-0.5, 0.5, 0), 14: (0.6, 0.6, 0), 15: (-0.5, 0.4, 0), 16: (-0.9, 1.0, -0.2)}
def LB(i, name, body, v, m_, size=None, u=0.0, f_in=None, f_out=None, Dk=0.55):
    cl = Vector(CL(V[i])); D = (Vector(V[i][1]) - cl).length * Dk
    s_ = fit(body, D, size if size else 1.0)
    return label(name, body, V[i], D, v, s_, m_, (S[i] + 3) if f_in is None else f_in,
                 (S[i + 1] if i + 1 < len(S) else FRAMES + 5) if f_out is None else f_out, u)
LT = 0.3

# ---- tardigrade / tun visibility (lines 3-4) and squash (line 7)
SH4 = S[4] + 22
keyscale(TG, [(0, 1.0), (S[3] + 4, 1.0), (S[3] + 9, 0.001), (SH4, 0.001), (SH4 + 3, 1.12), (SH4 + 6, 1.0),
              (S[7] + 6, 1.0), (S[7] + 12, (1.12, 1.12, 0.72)), (S[8] - 4, (1.12, 1.12, 0.72)), (S[8], 1.0)])
keyscale(tunG, [(0, 0.001), (S[3] + 6, 0.001), (S[3] + 10, 1.1), (S[3] + 13, 1.0), (SH4 - 1, 1.0), (SH4, 0.001)])

LB(0, "L0", "WATER BEAR", LT, lab_m)
# line 1: ruler + 0.5 mm
rul = box("Ruler", (0.3, CY - 1.45, 0.05), (2.6, 0.22, 0.06), mat("RulM", (1.0, 0.85, 0.15), 0.5))
pop(rul, S[1] + 2, 5, S[2] + 2)
for k in range(11):
    tk = box("RTick", (-1.0 + k * 0.26, CY - 1.53, 0.09), (0.03, 0.12 if k % 5 else 0.2, 0.02), eyeb)
    hide_until(tk, S[1] + 4); gone_at(tk, S[2] + 2)
LB(1, "L1", "0.5 mm", LT, lab_m)
LB(1, "L1b", "(ZOOMED x3,000)", LT + 0.08, white_lab, size=0.22)
# line 2: sprigs + droplets pop, legs label
for o_ in sprigs + drops:
    pop(o_, S[2] + random.randint(1, 12), 5)
LB(2, "L2", "8 LEGS", LT, lab_m)
LB(3, "L3", "DRY BALL", LT, white_lab)
# line 4: ice block around the tun, then it shatters and the water bear pops back
ice_m = alpha_mat("Ice", (0.65, 0.88, 1.0), 0.45, 0.35)
ice = box("IceBlock", (0, CY, 0.85), (2.4, 2.0, 1.7), ice_m, bevel=0.08)
keyscale(ice, [(0, 0.001), (S[4], 0.001), (S[4] + 5, 1.06), (S[4] + 8, 1.0), (SH4 - 1, 1.0), (SH4, 0.001)])
shatter_at((0, CY - 0.6, 0.9), SH4, 22, 0.5, [alpha_mat("IceS", (0.75, 0.92, 1.0), 0.7, 0.5)], spread=1.2, f_gone=S[5] + 6)
burst((0.6, CY - 1.0, 1.0), SH4, 14, 0.9, 0.05, SH4 + 12)
LB(4, "L4", "30 YEARS FROZEN", LT, blue_lab, f_out=SH4)
LB(4, "L4b", "IT WOKE UP!", LT, green_lab, f_in=SH4 + 2)
# lines 5-6: thermometer (blue low -> red high), frost + snow, then flames
THX, THY = -2.2, CY - 0.9
glass_m = mat("ThGlass", (0.95, 0.97, 1.0), 0.2, emit=(1, 1, 1), emit_strength=0.25)
th = [cyl("ThTube", (THX, THY, 1.45), 0.17, 2.3, glass_m, verts=20),
      sphere("ThBulbG", (THX, THY, 0.32), 0.3, glass_m, sub=3)]
for k in range(6):
    th.append(box("ThTick", (THX - 0.2, THY - 0.02, 0.8 + k * 0.35), (0.12, 0.03, 0.03), eyeb))
thG = group("ThG", (THX, THY, 0)); attach(th, thG)
pop(thG, S[5] + 1, 5, S[7] + 2)
liqB = cyl("LiqB", (THX, THY - 0.1, 0.32), 0.11, 1.0, blue_lab, verts=12)
liqB.data.transform(Matrix.Translation((0, 0, 0.5)))
bulbB = sphere("BulbB", (THX, THY - 0.1, 0.32), 0.24, blue_lab, sub=2)
liqR = cyl("LiqR", (THX, THY - 0.1, 0.32), 0.11, 1.0, red_lab, verts=12)
liqR.data.transform(Matrix.Translation((0, 0, 0.5)))
bulbR = sphere("BulbR", (THX, THY - 0.1, 0.32), 0.24, red_lab, sub=2)
keyscale(liqB, [(0, 0.001), (S[5] + 1, 0.001), (S[5] + 2, (1, 1, 1.4)), (S[5] + 14, (1, 1, 0.15)), (S[6] - 1, (1, 1, 0.15)), (S[6], 0.001)])
keyscale(bulbB, [(0, 0.001), (S[5] + 1, 0.001), (S[5] + 3, 1.0), (S[6] - 1, 1.0), (S[6], 0.001)])
keyscale(liqR, [(0, 0.001), (S[6] - 1, 0.001), (S[6], (1, 1, 0.15)), (S[6] + 18, (1, 1, 2.25)), (S[7] - 1, (1, 1, 2.25)), (S[7] + 2, 0.001)])
keyscale(bulbR, [(0, 0.001), (S[6] - 1, 0.001), (S[6], 1.0), (S[7] - 1, 1.0), (S[7] + 2, 0.001)])
snow(0, CY, S[5], S[6] + 4, 55, 2.6)
frost = []
for k in range(12):
    x_ = random.uniform(-1.1, 1.2)
    fr = sphere("Frost", (x_, CY + random.uniform(-0.3, 0.3), 1.25 - abs(x_) * 0.15), random.uniform(0.07, 0.12), snow_m, sub=1, smooth=False)
    pop(fr, S[5] + 6 + k, 3, S[6] + 2)
bpy.ops.object.light_add(type='POINT', location=(0.5, CY - 2.0, 2.2))
bl = bpy.context.object; bl.data.color = (0.45, 0.7, 1.0); bl.data.shadow_soft_size = 0.5
for f, e in ((0, 0), (S[5], 0), (S[5] + 4, 220), (S[6] - 1, 220), (S[6], 0)):
    bl.data.energy = e; bl.data.keyframe_insert("energy", frame=f)
LB(5, "L5", "-272 °C", LT, blue_lab)
flames = []
for k in range(10):
    a = k / 10 * 6.283
    p = (1.6 * math.cos(a) * 1.15, CY + 1.3 * math.sin(a), 0.3)
    fo = cyl("Flame", p, 0.2, 0.6, glow_mat("FlameM%d" % (k % 2), (1.0, 0.55 if k % 2 else 0.8, 0.1), 6.0), r2=0.01, verts=10)
    keyscale(fo, [(0, 0.001), (S[6] + 2 + k % 4, 0.001)] + [(S[6] + 5 + j * 3 + k % 4, (1, 1, 0.7 + 0.5 * ((j + k) % 2))) for j in range(int((S[7] - S[6]) / 3) - 1)] + [(S[7] + 1, 0.001)])
bpy.ops.object.light_add(type='POINT', location=(0.5, CY - 1.6, 1.4))
ol = bpy.context.object; ol.data.color = (1.0, 0.55, 0.15); ol.data.shadow_soft_size = 0.5
for f, e in ((0, 0), (S[6], 0), (S[6] + 4, 260), (S[7] - 1, 260), (S[7], 0)):
    ol.data.energy = e; ol.data.keyframe_insert("energy", frame=f)
LB(6, "L6", "150 °C", LT, red_lab)
# line 7: pressure arrows squeeze in from all sides
arr_m = mat("ArrM", (0.95, 0.15, 0.1), 0.4, emit=(1.0, 0.1, 0.05), emit_strength=0.6)
TGC = (0.2, CY, 0.75)
for k in range(10):
    if k < 7:
        a = (k / 7) * 6.283 + 0.3
        far_ = (TGC[0] + 3.6 * math.cos(a), TGC[1] + 2.6 * math.sin(a), 0.9)
        near_ = (TGC[0] + 2.3 * math.cos(a), TGC[1] + 1.7 * math.sin(a), 0.85)
    else:
        far_ = (TGC[0] + (k - 8) * 0.9, CY, 4.2); near_ = (TGC[0] + (k - 8) * 0.9, CY, 2.0)
    ar = join([cyl("ArS", (0, 0, -0.35), 0.1, 0.7, arr_m, verts=10), cyl("ArH", (0, 0, 0.15), 0.24, 0.3, arr_m, r2=0.0, verts=12)], "Arrow")
    ar.location = far_
    aim_obj(ar, far_, TGC)
    f0 = S[7] + 1 + k % 3
    key_loc(ar, [(f0, far_), (S[7] + 12, near_)] + [(S[7] + 14 + 4 * j, near_ if j % 2 else tuple(Vector(near_) + (Vector(far_) - Vector(near_)) * 0.12)) for j in range(5)])
    keyscale(ar, [(0, 0.001), (f0 - 1, 0.001), (f0 + 2, 1.0), (S[8] - 1, 1.0), (S[8], 0.001)])
LB(7, "L7", "~6x DEEPEST SEA", LT, lab_m)
# line 8: rocket ride into space
rk_w = mat("RocketW", (0.96, 0.96, 0.96), 0.4)
rk_r = mat("RocketR", (0.9, 0.15, 0.12), 0.4)
rp = [cyl("RkBody", (0, CY - 0.0, 0.95), 0.42, 1.5, rk_w, verts=24),
      cyl("RkNose", (0, CY, 1.98), 0.42, 0.55, rk_r, r2=0.02, verts=24),
      cyl("RkWin", (0, CY - 0.4, 1.1), 0.17, 0.06, win_m, rot=(math.radians(90), 0, 0), verts=18)]
for k in range(3):
    a = k / 3 * 6.283 - 1.57
    rp.append(box("RkFin", (0.5 * math.cos(a), CY + 0.5 * math.sin(a), 0.38), (0.36 if abs(math.cos(a)) > 0.5 else 0.08, 0.36 if abs(math.sin(a)) > 0.5 else 0.08, 0.6), rk_r))
fl = cyl("RkFlame", (0, CY, -0.35), 0.36, 0.9, glow_mat("RkFl", (1.0, 0.6, 0.15), 7.0), rot=(math.radians(180), 0, 0), r2=0.02, verts=14)
rp.append(fl)
RK = group("Rocket", (0, CY, 0)); attach(rp, RK)
L8 = S[8] + 8
keyscale(RK, [(0, 0.001), (S[8], 0.001), (S[8] + 4, 1.0), (S[9] - 1, 1.0), (S[9], 0.001)])
keyscale(fl, [(0, 0.001), (L8 - 1, 0.001), (L8, 1.0)] + [(L8 + 2 + j * 2, (1, 1, 0.8 + 0.4 * (j % 2))) for j in range(18)])
key_loc(RK, [(L8, (0, CY, 0)), (S[9] - 1, (0, CY, 3.2))])
key_loc(TG, [(0, (0, CY, 0)), (S[8] + 2, (0, CY, 0)), (S[8] + 6, (0, CY, 2.5)), (L8, (0, CY, 2.25)), (S[9] - 1, (0, CY, 5.45)), (S[9], (0, CY, 0))])
for k in range(10):
    p_ = sphere("Smoke", (random.uniform(-1.4, 1.4), CY + random.uniform(-1.0, 0.6), 0.3), random.uniform(0.3, 0.5), mat("SmokeM", (0.92, 0.92, 0.9), 0.9), sub=1)
    keyscale(p_, [(0, 0.001), (L8, 0.001), (L8 + 4, 1.0), (L8 + 18, 1.4), (L8 + 24, 0.001)])
for k in range(14):
    st = sphere("Star", (random.uniform(-3, 3), CY + random.uniform(0, 2), random.uniform(6, 10)), 0.09, glow_mat("StarM", (1, 0.95, 0.7), 6.0), sub=1)
    pop(st, L8 + 6 + k, 3, S[9])
LB(8, "L8", "10 DAYS IN SPACE", LT, white_lab)
# line 9: radiation beams + bars YOU vs WATER BEAR
rad_m = glow_mat("RadM", (0.75, 1.0, 0.2), 6.0)
for k in range(8):
    a = k / 8 * 6.283 + 0.2
    p0 = (TGC[0] + 4.2 * math.cos(a), TGC[1] + 3.2 * math.sin(a) * 0.6, 3.6 + (k % 3) * 0.6)
    b_ = beam("RadBeam", p0, TGC, 0.045, rad_m)
    keyscale(b_, [(0, 0.001), (S[9] + 2 + k, 0.001), (S[9] + 4 + k, 1.0)] + [(S[9] + 8 + k + j * 4, (1.6 if j % 2 else 0.7, 1.6 if j % 2 else 0.7, 1.0)) for j in range(int((S[11] - S[9]) / 4) - 4)] + [(S[11] - 2, 1.0), (S[11], 0.001)])
burst((TGC[0], TGC[1] - 0.8, 1.3), S[9] + 10, 12, 0.7, 0.05, S[9] + 24, material=rad_m)
BX, BY = -2.4, CY - 0.6
bar_y = box("BarYou", (BX - 0.45, BY, 0), (0.6, 0.6, 1.0), blue_lab)
bar_t = box("BarTG", (BX + 0.45, BY, 0), (0.6, 0.6, 1.0), green_lab)
for b_ in (bar_y, bar_t):
    b_.data.transform(Matrix.Translation((0, 0, 0.5)))
keyscale(bar_y, [(0, 0.001), (S[9] + 1, 0.001), (S[9] + 2, (1, 1, 0.01)), (S[9] + 8, (1, 1, 0.06)), (S[10] - 2, (1, 1, 0.06)), (S[10], 0.001)])
keyscale(bar_t, [(0, 0.001), (S[9] + 1, 0.001), (S[9] + 2, (1, 1, 0.01)), (S[9] + 10, (1, 1, 0.01)), (S[9] + 26, (1, 1, 3.0)), (S[10] - 2, (1, 1, 3.0)), (S[10], 0.001)])
yl = text("BarYouL", "YOU", (BX - 0.45, BY - 0.42, 0.35), 0.28, white_lab, extrude=0.02); pop(yl, S[9] + 4, 5, S[10])
tl_ = text("BarTGL", "BEAR", (BX + 0.45, BY - 0.42, 0.35), 0.28, white_lab, extrude=0.02); pop(tl_, S[9] + 8, 5, S[10])
LB(9, "L9", "~1,000x YOU", LT, green_lab)
# line 10: DNA helix with a glowing protein shield
DX, DYY = 2.5, CY - 0.6
dna = []
cols = [blue_lab, red_lab, lab_m, green_lab]
for k in range(22):
    z_ = 0.25 + k * 0.1; a = k * 0.55
    p1 = (DX + 0.32 * math.cos(a), DYY + 0.32 * math.sin(a), z_); p2 = (DX - 0.32 * math.cos(a), DYY - 0.32 * math.sin(a), z_)
    dna += [sphere("DNA1", p1, 0.07, white_lab, sub=1), sphere("DNA2", p2, 0.07, white_lab, sub=1)]
    if k % 2 == 0:
        dna.append(beam("Rung", p1, p2, 0.025, cols[(k // 2) % 4]))
dnaG = group("DNAG", (DX, DYY, 0)); attach(dna, dnaG)
pop(dnaG, S[10] + 1, 5, S[11])
keyrot(dnaG, [(S[10], (0, 0, 0)), (S[11], (0, 0, 3.0))])
bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=0.95, location=(DX, DYY, 1.3))
shield = bpy.context.object; shield.name = "Shield"; shield.scale = (0.8, 0.8, 1.15)
shield.modifiers.new("w", 'WIREFRAME').thickness = 0.025
shield.data.materials.append(glow_mat("ShieldM", (0.3, 0.9, 1.0), 4.0))
keyscale(shield, [(0, 0.001), (S[10] + 7, 0.001), (S[10] + 11, (0.9, 0.9, 1.3)), (S[10] + 14, (0.8, 0.8, 1.15)), (S[11] - 2, (0.8, 0.8, 1.15)), (S[11], 0.001)])
for k in range(5):
    a = 0.4 + k * 0.5
    hitp = (DX + 0.78 * math.cos(a) * 0.9, DYY - 0.6 * math.sin(a), 1.2 + 0.5 * (k % 3) - 0.3)
    p0 = (hitp[0] + 2.2 * math.cos(a), hitp[1] - 1.5, hitp[2] + 2.0)
    b_ = beam("RadBeam2", p0, hitp, 0.04, rad_m)
    f0 = S[10] + 14 + k * 3
    keyscale(b_, [(0, 0.001), (f0 - 1, 0.001), (f0, 1.0), (f0 + 5, 1.0), (f0 + 6, 0.001)])
    burst(hitp, f0 + 2, 8, 0.2, 0.03, f0 + 10, material=cspark_m)
LB(10, "L10", "PROTEIN SHIELD", LT, blue_lab, size=0.8)

# ---------------- lines 11-16: YOU ----------------
keyscale(you, [(0, 0.001), (S[11] - 1, 0.001), (S[11], 1.0), (S[15] + 6, 1.0), (S[15] + 10, 0.001), (S[16] - 1, 0.001), (S[16] + 3, 1.12), (S[16] + 6, 1.0)])
# line 11: blizzard + shiver
snow(MX, MY, S[11], S[12] + 2, 80, 2.2)
for f in range(S[11] + 2, S[12], 2):
    you.rotation_euler = (0, 0, 0.08 if (f // 2) % 2 else -0.08); you.keyframe_insert("rotation_euler", frame=f)
you.rotation_euler = (0, 0, 0); you.keyframe_insert("rotation_euler", frame=S[12])
bpy.ops.object.light_add(type='POINT', location=(MX, MY - 1.6, 2.4))
bl2 = bpy.context.object; bl2.data.color = (0.45, 0.7, 1.0); bl2.data.shadow_soft_size = 0.5
for f, e in ((0, 0), (S[11], 0), (S[11] + 3, 160), (S[12] - 1, 160), (S[12], 0), (S[13], 0), (S[13] + 3, 120), (S[13] + 20, 120), (S[13] + 22, 0),
             (S[14], 0), (S[14] + 4, 110), (S[15] - 1, 110), (S[15], 0)):
    bl2.data.energy = e; bl2.data.keyframe_insert("energy", frame=f)
icl = []
for k in range(5):
    ic = cyl("Icicle", Y["P"]((k - 2) * 0.08, -0.05, 1.86), 0.025, 0.14, snow_m, rot=(math.radians(180), 0, 0), r2=0.002, verts=6)
    ic.location = Y["P"]((k - 2) * 0.08, -0.12, 1.66)
    pop(ic, S[11] + 8 + k * 2, 3, S[12] + 2)
LB(11, "L11", "BRRR!", LT, blue_lab)
# line 12: tardigrade power
burst(Y["P"](0, -0.35, 1.0), S[12] + 4, 18, 0.85, 0.05, S[12] + 18, material=gspark_m, yoff=-0.1)
bpy.ops.object.light_add(type='POINT', location=Y["P"](0, -0.9, 1.5))
pl = bpy.context.object; pl.data.color = (0.4, 1.0, 0.4); pl.data.shadow_soft_size = 0.3
for f, e in ((0, 0), (S[12] + 2, 0), (S[12] + 6, 80), (S[13] - 2, 50), (S[13] + 2, 0)):
    pl.data.energy = e; pl.data.keyframe_insert("energy", frame=f)
ring = tube("PowRing", [(MX + 0.9 * math.cos(a / 24 * 6.283), MY + 0.9 * math.sin(a / 24 * 6.283), 0.05) for a in range(25)], [0.04] * 25, glow_mat("RingM", (0.4, 1.0, 0.4), 5.0))
ring.data.transform(Matrix.Translation((-MX, -MY, 0))); ring.location = (MX, MY, 0.05)
keyscale(ring, [(0, 0.001), (S[12] + 3, 0.001), (S[12] + 4, 0.3), (S[12] + 18, 1.6), (S[12] + 20, 0.001)])
keyrot(Y["arms"][0], [(S[12], (0, 0, 0)), (S[12] + 5, (0, 2.6, 0)), (S[13] - 2, (0, 2.6, 0)), (S[13] + 2, (0, 0, 0))])
keyrot(Y["arms"][1], [(S[12], (0, 0, 0)), (S[12] + 5, (0, -2.6, 0)), (S[13] - 2, (0, -2.6, 0)), (S[13] + 2, (0, 0, 0))])
LB(12, "L12", "BEAR POWER!", LT, green_lab, size=0.75)
# line 13: frozen in ice, pops out smiling
SH13 = S[13] + 20
ice2 = box("IceBlock2", (MX, MY, 1.0), (1.0, 0.8, 2.1), ice_m, bevel=0.06)
keyscale(ice2, [(0, 0.001), (S[13], 0.001), (S[13] + 4, 1.06), (S[13] + 7, 1.0), (SH13 - 1, 1.0), (SH13, 0.001)])
shatter_at((MX, MY - 0.4, 1.1), SH13, 20, 0.35, [alpha_mat("IceS2", (0.75, 0.92, 1.0), 0.7, 0.5)], spread=1.3, f_gone=S[14] + 8)
burst((MX, MY - 0.5, 1.2), SH13, 14, 0.8, 0.05, SH13 + 12)
key_loc(you, [(0, (MX, MY, 0)), (SH13, (MX, MY, 0)), (SH13 + 5, (MX, MY, 0.6)), (SH13 + 10, (MX, MY, 0))])
keyrot(Y["arms"][0], [(SH13, (0, 0, 0)), (SH13 + 4, (0, 2.6, 0)), (S[14] + 4, (0, 2.6, 0)), (S[14] + 10, (0, 0, 0))])
keyrot(Y["arms"][1], [(SH13, (0, 0, 0)), (SH13 + 4, (0, -2.6, 0)), (S[14] + 4, (0, -2.6, 0)), (S[14] + 10, (0, 0, 0))])
LB(13, "L13", "POP! SMILING", LT, lab_m, f_in=SH13 - 2)
LB(13, "L13a", "FROZEN", LT, blue_lab, f_out=SH13 - 2)
# line 14: bottom of the ocean — water column, fish, bubbles, deep light
sea = box("Sea", (MX, MY + 0.1, 1.6), (3.0, 2.4, 3.2), alpha_mat("SeaM", (0.1, 0.35, 0.8), 0.32, 0.15))
keyscale(sea, [(0, 0.001), (S[14], 0.001), (S[14] + 5, 1.0), (S[15] - 1, 1.0), (S[15] + 1, 0.001)])
fish_ms = [mat("FishO", (1.0, 0.55, 0.1), 0.5), mat("FishY", (1.0, 0.85, 0.15), 0.5), mat("FishP", (0.95, 0.4, 0.7), 0.5)]
for k in range(3):
    fsh = join([sphere("FishB", (0, 0, 0), 0.16, fish_ms[k], scale=(1.4, 0.6, 0.9), sub=2),
                cyl("FishT", (-0.27, 0, 0), 0.13, 0.18, fish_ms[k], rot=(0, math.radians(-90), 0), r2=0.0, verts=4),
                sphere("FishE", (0.15, -0.07, 0.04), 0.035, eyeb, sub=1)], "Fish")
    rr, zz, ph = 0.95 + k * 0.2, 0.7 + k * 0.5, k * 2.1
    for j in range(9):
        f = S[14] + 2 + j * 4
        a = ph + j * 0.5
        fsh.location = (MX + rr * math.cos(a), MY + rr * math.sin(a) * 0.7, zz); fsh.keyframe_insert("location", frame=f)
        fsh.rotation_euler = (0, 0, a + 1.57); fsh.keyframe_insert("rotation_euler", frame=f)
    keyscale(fsh, [(0, 0.001), (S[14] + 2, 0.001), (S[14] + 5, 1.0), (S[15] - 1, 1.0), (S[15], 0.001)])
for k in range(16):
    x_, y_ = MX + random.uniform(-1.0, 1.0), MY + random.uniform(-0.6, 0.3)
    bb = sphere("Bub", (x_, y_, 0.2), random.uniform(0.04, 0.08), mat("BubM", (0.9, 0.97, 1.0), 0.05, emit=(0.8, 0.95, 1.0), emit_strength=0.8), sub=2)
    f0 = S[14] + 2 + random.randint(0, 20)
    key_loc(bb, [(f0, (x_, y_, 0.2)), (f0 + 16, (x_ + 0.1, y_, 3.0))])
    keyscale(bb, [(0, 0.001), (f0 - 1, 0.001), (f0, 1.0), (f0 + 16, 1.0), (f0 + 17, 0.001)])
keyrot(Y["arms"][0], [(S[14] + 10, (0, 0, 0)), (S[14] + 14, (0, 1.4, 0)), (S[15] - 2, (0, 1.4, 0)), (S[15], (0, 0, 0))])
LB(14, "L14", "11 KM DOWN: OK!", LT, lab_m)
# line 15: the catch — dry up into a "human tun"
htun = sphere("HumanTun", (MX, MY, 0.42), 0.42, mat("HTunM", (0.78, 0.55, 0.38), 0.85), scale=(1.0, 0.9, 0.85), sub=3)
hf = [htun]
for sx in (-1, 1):
    hf.append(tube("HTEye", [(MX + sx * 0.14 - 0.06, MY - 0.36, 0.55), (MX + sx * 0.14, MY - 0.38, 0.52), (MX + sx * 0.14 + 0.06, MY - 0.36, 0.55)], [0.016] * 3, eyeb))
hf.append(sphere("HTHair", (MX, MY + 0.02, 0.76), 0.25, mat("HairY2", (0.28, 0.16, 0.07), 0.8), scale=(1.2, 1.0, 0.45), sub=2))
htG = group("HTunG", (MX, MY, 0)); attach(hf, htG)
keyscale(htG, [(0, 0.001), (S[15] + 8, 0.001), (S[15] + 12, 1.1), (S[15] + 15, 1.0), (S[16] - 1, 1.0), (S[16], 0.001)])
for k in range(8):
    a = k / 8 * 6.283
    dr = sphere("DryDrop", (MX + 0.5 * math.cos(a), MY - 0.2 + 0.3 * math.sin(a), 0.8), 0.06, drop_m, sub=2)
    key_loc(dr, [(S[15] + 4, (MX + 0.5 * math.cos(a), MY - 0.2 + 0.3 * math.sin(a), 0.8)), (S[15] + 18, (MX + 1.2 * math.cos(a), MY - 0.2 + 0.7 * math.sin(a), 2.2))])
    keyscale(dr, [(0, 0.001), (S[15] + 3, 0.001), (S[15] + 4, 1.0), (S[15] + 18, 0.001)])
LB(15, "L15", "DRY UP FIRST!", LT, lab_m)
# line 16: question
keyrot(Y["arms"][0], [(S[16], (0, 0, 0)), (S[16] + 6, (0, 2.4, 0))])
keyrot(Y["arms"][1], [(S[16], (0, 0, 0)), (S[16] + 6, (0, -2.4, 0))])
q = text("Q", "?", SP(V[16], 4.0, LT, 0.0), 1.0, lab_m, extrude=0.06)
pop(q, S[16] + 4, 6)
keyrot(q, [(S[16] + 4, (math.radians(90), 0, 0)), (FRAMES, (math.radians(90), 0, math.radians(360)))])

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
