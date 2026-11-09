# Day 15 — What if you never slept again?  Build: python3 episodes/015-never-sleep/scene.py
# Reference style: base (helpers, lawn/soil, house, garden) copied from episodes/003-lift-million-ref/scene.py (via 004)
import bpy, math, random, os, json
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
random.seed(15)
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
# Day 15 — What if you never slept again?
# Facts used:
#   ~17-19 h awake impairs performance like 0.05% blood alcohol, ~24 h like ~0.10% (Dawson & Reid, Nature 1997;
#   Williamson & Feyer 2000) -> "your brain acts drunk"; slower reactions -> the missed ball.
#   Microsleeps: brief (fraction of a second to ~10+ s) lapses, can happen with eyes open.
#   Perceptual distortions / hallucinations commonly appear after ~2-3 days without sleep.
#   Glymphatic system: cerebrospinal fluid flushes waste (e.g. beta-amyloid) mostly during sleep (Xie et al. 2013).
#   Record: 11 days (264 h), a 1964 school science project; Guinness stopped accepting sleep-deprivation records.
#   Rats totally deprived of sleep died within ~2-4 weeks (Rechtschaffen et al., 1983/1989).
#   You can't stay awake forever: sleep pressure forces microsleeps / sleep.
# =====================================================================================
gold_m = mat("Gold", (1.0, 0.78, 0.2), 0.3, metal=0.85)
mouth_m = mat("Mouth", (0.35, 0.05, 0.07), 0.5)
YX, YY = 0.7, 1.4
TWX, TWY = -0.9, 1.4

def add_face(g, P_, name):
    lids = []
    for sx in (-1, 1):
        l_ = sphere(name + "Lid", P_(sx * 0.085, -0.235, 1.80), 0.07, skin_m, scale=(1.15, 0.6, 0.75), sub=2)
        parent_to(l_, g); lids.append(l_)
    mo = sphere(name + "Mouth", P_(0, -0.235, 1.565), 0.05, mouth_m, scale=(1.0, 0.5, 1.3), sub=2)
    parent_to(mo, g)
    return lids, mo

you, YD = person("You", (0, 0, 0), 1.0, mat("Shirt", (0.95, 0.35, 0.2), 0.6), mat("Pants", (0.2, 0.3, 0.55), 0.7),
                 skin_m, mat("Hair", (0.25, 0.14, 0.07), 0.8))
Y_LIDS, Y_MOUTH = add_face(you, YD["P"], "You")
twin, TD = person("Twin", (0, 0, 0), 1.0, mat("ShirtT", (0.2, 0.75, 0.35), 0.6), mat("PantsT", (0.2, 0.3, 0.55), 0.7),
                  skin_m, mat("HairT", (0.25, 0.14, 0.07), 0.8))
T_LIDS, T_MOUTH = add_face(twin, TD["P"], "Twin")
for o in T_LIDS:
    o.location.z += 0.02          # twin: wide awake
Y_MOUTH.scale = (0.001,) * 3; T_MOUTH.scale = (0.001,) * 3

def lid_keys(lids, keys):
    for f, z in keys:
        for l_ in lids:
            l_.location.z = z; l_.keyframe_insert("location", index=2, frame=f)
OPEN, HALF, SHUT = 1.80, 1.765, 1.725

# ---------------- bed ----------------
bedwood = mat("BedWood", (0.62, 0.4, 0.22), 0.7)
sheet_m = mat("Sheet", (0.97, 0.97, 0.95), 0.6)
duvet_m = stripe_mat("Duvet", (0.25, 0.45, 0.9), (0.4, 0.6, 1.0), axis="X", freq=14.0, thresh=0.3, rough=0.7)
def make_bed(name, c):
    x, y = c
    g = group(name, (x, y, 0))
    parts = [box(name + "Frame", (x, y, 0.18), (1.25, 2.35, 0.36), bedwood, bevel=0.04),
             box(name + "Matt", (x, y, 0.45), (1.12, 2.22, 0.2), sheet_m, bevel=0.05),
             box(name + "Head", (x, y + 1.17, 0.55), (1.25, 0.12, 1.1), bedwood, bevel=0.04),
             box(name + "Pillow", (x, y + 0.78, 0.62), (0.8, 0.42, 0.16), sheet_m, bevel=0.07),
             box(name + "Duvet", (x, y - 0.45, 0.66), (1.2, 1.35, 0.24), duvet_m, bevel=0.08)]
    for dx in (-0.55, 0.55):
        parts.append(box(name + "Foot", (x + dx, y - 1.1, 0.4), (0.1, 0.1, 0.8), bedwood))
    attach(parts, g)
    return g
BD = (YX, YY + 1.0)
bed = make_bed("Bed", BD)

# ---------------- clock ----------------
face_m = mat("ClockFace", (0.98, 0.97, 0.9), 0.4)
rim_m = mat("ClockRim", (0.9, 0.2, 0.2), 0.4)
hand_m = mat("ClockHand", (0.05, 0.05, 0.08), 0.4)
CKX, CKY, CKZ = YX + 1.45, YY + 0.9, 1.6
clock = group("Clock", (CKX, CKY, CKZ))
cp = [cyl("CFace", (CKX, CKY, CKZ), 0.72, 0.1, face_m, rot=(math.radians(90), 0, 0), verts=40)]
bpy.ops.mesh.primitive_torus_add(major_radius=0.74, minor_radius=0.07, location=(CKX, CKY - 0.02, CKZ), rotation=(math.radians(90), 0, 0))
o = bpy.context.object; o.data.materials.append(rim_m); cp.append(o)
for k in range(12):
    a = k / 12 * 6.283
    cp.append(box("CTick", (CKX + 0.58 * math.sin(a), CKY - 0.06, CKZ + 0.58 * math.cos(a)), (0.05, 0.03, 0.12 if k % 3 else 0.2), hand_m))
cp.append(box("CLeg", (CKX, CKY + 0.05, (CKZ - 0.7) / 2), (0.1, 0.1, CKZ - 0.7), rim_m))
cp.append(cyl("CBase", (CKX, CKY + 0.05, 0.04), 0.35, 0.08, rim_m, verts=20))
def clock_hand(name, L_, w_):
    o = box(name, (CKX, CKY - 0.08, CKZ + L_ / 2 - 0.05), (w_, 0.03, L_), hand_m)
    o.data.transform(Matrix.Translation((-CKX, -(CKY - 0.08), -CKZ)))
    o.location = (CKX, CKY - 0.08, CKZ)
    return o
hh = clock_hand("HourHand", 0.36, 0.08); mh = clock_hand("MinHand", 0.55, 0.05)
cp += [hh, mh, sphere("CHub", (CKX, CKY - 0.1, CKZ), 0.06, rim_m, sub=1)]
attach(cp, clock)
for h_, sp_ in ((hh, 2.0), (mh, 24.0)):
    h_.rotation_euler = (0, 0, 0); h_.keyframe_insert("rotation_euler", frame=0)
    h_.rotation_euler = (0, sp_ * FRAMES / 24 * 0.6, 0); h_.keyframe_insert("rotation_euler", frame=FRAMES)
    for fc in fcurves(h_):
        for p in fc.keyframe_points:
            p.interpolation = 'LINEAR'

def zzz(name, base, f0, n=3, f_out=None, size=0.22, rise=1.4, mat_=None):
    for k in range(n):
        t0 = f0 + k * 7
        z_ = text(name, "Z", base, size * (1 + 0.3 * k), mat_ or white_lab, extrude=0.03)
        p0 = Vector(base); p1 = p0 + Vector((0.35 + 0.2 * k, 0, rise))
        key_loc(z_, [(t0, tuple(p0)), (t0 + 18, tuple(p1))])
        end = f_out if f_out else t0 + 19
        keyscale(z_, [(0, 0.001), (t0 - 1, 0.001), (t0 + 3, 1.0), (end - 1, 1.0), (end, 0.001)])

# =================== line 0: the bed blasts off into the sky ===================
HOME = (BD[0], BD[1], 0.0)
B0 = (TWX, BD[1], 0.0)
key_loc(bed, [(0, B0), (W(0, 0.35), B0), (E(0) - 1, (TWX - 1.5, BD[1] + 6.0, 9.0))])
bed.rotation_euler = (0, 0, 0); bed.keyframe_insert("rotation_euler", frame=W(0, 0.35))
bed.rotation_euler = (math.radians(70), math.radians(-40), math.radians(120)); bed.keyframe_insert("rotation_euler", frame=E(0) - 1)
bed.rotation_euler = (0, 0, 0); bed.keyframe_insert("rotation_euler", frame=S[16] - 1)
for k in range(10):
    pf = sphere("Smoke", (TWX + random.uniform(-0.6, 0.6), BD[1] + random.uniform(-0.8, 0.8), 0.2), random.uniform(0.25, 0.4), cloud_m, sub=2)
    keyscale(pf, [(0, 0.001), (W(0, 0.35), 0.001), (W(0, 0.35) + 3, 1.0), (E(0) - 2, 1.4), (E(0) - 1, 0.001)])
# bed returns at line 16 (drops in behind you), stays to the end
key_loc(bed, [(S[16] - 1, (BD[0], BD[1], 12.0)), (S[16], (BD[0], BD[1], 5.0)), (S[16] + 6, HOME)])
for fc in fcurves(bed):
    for p in fc.keyframe_points:
        if int(round(p.co[0])) in (E(0) - 1, S[16] - 1):
            p.interpolation = 'CONSTANT'
vis(bed, [(0, S[1]), (S[16], FRAMES)])

# =================== line 2: yawning + stretch (clock spins), line 5: blinking microsleeps ===================
vis(clock, [(S[2], S[3]), (S[5], S[6])])
mo_keys = [(S[2], 0.001), (S[2] + 3, 0.001), (S[2] + 8, 1.7), (S[2] + 15, 1.7), (S[2] + 18, 0.2), (S[2] + 21, 0.2),
           (S[2] + 25, 1.8), (E(2) - 2, 1.8), (E(2), 0.001)]
keyscale(Y_MOUTH, [(f, (s, s * 0.6, s * 1.2) if s > 0.01 else (0.001,) * 3) for f, s in mo_keys])
lid_keys(Y_LIDS, [(0, OPEN - 0.005), (S[1], OPEN - 0.01), (S[2], HALF), (S[2] + 8, SHUT + 0.01), (S[2] + 15, SHUT + 0.01),
                  (S[2] + 19, HALF), (S[2] + 25, SHUT + 0.01), (E(2) - 1, HALF), (S[3], HALF),
                  (S[5], HALF), (W(5, 0.15), SHUT), (W(5, 0.35), SHUT), (W(5, 0.42), OPEN), (W(5, 0.55), SHUT), (W(5, 0.85), SHUT),
                  (W(5, 0.92), OPEN), (S[6] - 1, OPEN), (S[6], OPEN + 0.01), (S[7] - 1, OPEN + 0.01), (S[7], HALF),
                  (S[15], HALF), (W(16, 0.3), HALF), (W(16, 0.5), SHUT), (FRAMES, SHUT)])
zzz("ZMicro", (YX + 0.35, YY - 0.3, 2.0), W(5, 0.15), n=2, size=0.2, rise=0.9, mat_=lab_m)
zzz("ZMicro2", (YX + 0.35, YY - 0.3, 2.0), W(5, 0.55), n=2, size=0.2, rise=0.9, mat_=lab_m)

# =================== line 3: drunk brain — wobble + dizzy stars ===================
star_m = glow_mat("Star", (1.0, 0.85, 0.2), 4.0)
for k in range(5):
    st = sphere("Dizzy", (YX, YY, 2.1), 0.06, star_m, sub=1)
    keys = []
    for f in range(S[3], E(3) + 1, 2):
        a = k / 5 * 6.283 + (f - S[3]) * 0.35
        keys.append((f, (YX + 0.4 * math.cos(a), YY + 0.3 * math.sin(a) - 0.05, 2.12 + 0.05 * math.sin(3 * a))))
    key_loc(st, keys)
    vis(st, [(S[3], S[4])], 1.0)

# =================== line 4: two balls — twin catches, you get bonked ===================
ball_m = mat("Ball", (1.0, 0.85, 0.15), 0.4)
ball2_m = mat("Ball2", (0.95, 0.25, 0.6), 0.4)
HANDT = (TWX - 0.754, TWY - 0.06, 1.69)
bA = sphere("BallA", HANDT, 0.14, ball_m, sub=2)
key_loc(bA, [(S[4], (HANDT[0] - 0.3, 7.0, 4.5)), (W(4, 0.18), (HANDT[0] - 0.2, 4.5, 3.6)), (W(4, 0.38), HANDT)])
vis(bA, [(S[4], S[5])])
bB = sphere("BallB", (YX, YY, 2.0), 0.14, ball2_m, sub=2)
HEADY = (YX, YY - 0.05, 2.0)
key_loc(bB, [(W(4, 0.3), (YX + 0.3, 7.0, 4.5)), (W(4, 0.48), (YX + 0.2, 4.0, 3.6)), (W(4, 0.66), HEADY),
             (W(4, 0.8), (YX + 1.0, YY - 1.6, 1.5)), (E(4), (YX + 1.6, YY - 2.6, 0.15))])
vis(bB, [(W(4, 0.3), S[5])])
burst(HEADY, W(4, 0.66), n=10, r=0.3, size=0.05, material=star_m)
tick_m = green_lab
tk = [boxc("Tick1", (HANDT[0] + 0.1, HANDT[1] - 0.1, 2.35), (0.08, 0.04, 0.22), green_lab),
      boxc("Tick2", (HANDT[0] + 0.28, HANDT[1] - 0.1, 2.43), (0.08, 0.04, 0.42), green_lab)]
tk[0].rotation_euler = (0, math.radians(-45), 0); tk[1].rotation_euler = (0, math.radians(30), 0)
for o in tk:
    vis(o, [(W(4, 0.4), S[5])])

# =================== line 6 + 9-11: the giant brain (microsleep, cleaning shift, trash pile) ===================
BRX, BRY, BRZ = 9.0, 3.0, 2.05
brain_m = mat("Brain", (0.98, 0.58, 0.66), 0.45)
brain2_m = mat("Brain2", (0.9, 0.45, 0.55), 0.5)
ped_m = mat("Pedestal", (0.96, 0.96, 0.98), 0.4)
brain = group("BrainG", (BRX, BRY, BRZ))
bp = [sphere("BrainCore", (BRX, BRY, BRZ), 1.0, brain_m, scale=(1.35, 1.05, 0.92), sub=3)]
RAD = (1.35, 1.05, 0.92)
def on_brain(u, k=1.0):
    return Vector((BRX + u.x * RAD[0] * k, BRY + u.y * RAD[1] * k, BRZ + u.z * RAD[2] * k))
for i in range(70):
    u = Vector((random.gauss(0, 1), random.gauss(0, 1), random.gauss(0, 1))).normalized()
    if u.z < -0.35:
        continue
    bp.append(sphere("Gyrus", tuple(on_brain(u, 0.93)), random.uniform(0.24, 0.32), random.choice((brain_m, brain2_m)), scale=(1.4, 0.7, 0.7), sub=2))
    bp[-1].rotation_euler = (random.uniform(0, 3), random.uniform(0, 3), random.uniform(0, 3))
bp.append(box("Groove", (BRX, BRY, BRZ + 0.9), (0.06, 1.9, 0.22), mat("GrooveM", (0.6, 0.25, 0.32), 0.6)))
bp.append(cyl("Stem", (BRX + 0.25, BRY + 0.2, BRZ - 0.95), 0.25, 0.6, brain2_m, verts=16))
attach(bp, brain)
ped = [cyl("Ped", (BRX, BRY, 0.55), 0.85, 1.1, ped_m, verts=32), cyl("PedTop", (BRX, BRY, 1.13), 0.95, 0.08, rim_m, verts=32)]
BRAIN_SPANS = [(S[6], S[7]), (S[9], S[12])]
vis(brain, BRAIN_SPANS)
for o in ped:
    vis(o, BRAIN_SPANS)
# neuron lights (switch off during the microsleep)
neur_m = glow_mat("Neuron", (1.0, 0.95, 0.4), 6.0)
for i in range(34):
    u = Vector((random.gauss(0, 1), -abs(random.gauss(0, 1)) - 0.3, abs(random.gauss(0, 1)))).normalized()
    n_ = sphere("Neuron", tuple(on_brain(u, 1.16)), 0.075, neur_m, sub=1)
    vis(n_, [(S[6], W(6, 0.28)), (W(6, 0.78), S[7]), (S[9], S[12])])
zzz("ZBrain", (BRX - 0.4, BRY - 1.3, BRZ + 0.9), W(6, 0.3), n=3, size=0.32, rise=1.0, mat_=lab_m)
# fluid blobs flowing over the front of the brain (lines 9-10)
fluid_m = mat("Fluid", (0.25, 0.65, 1.0), 0.05, emit=(0.2, 0.55, 1.0), emit_strength=1.4)
def arc(s):
    phi = math.radians(165 - 150 * s)
    return (BRX + 1.55 * math.cos(phi), BRY - 0.75, BRZ + 1.1 * math.sin(phi) + 0.05)
for k in range(16):
    fb = sphere("FluidBlob", arc(0), 0.15, fluid_m, scale=(1.3, 1.0, 1.0), sub=2)
    keys = []; t0 = S[9] - 30 + k * 6
    for c in range(3):
        a_ = t0 + c * 34
        keys += [(a_, arc(0)), (a_ + 33, arc(1))]
    key_loc(fb, keys)
    for fc in fcurves(fb):
        for p in fc.keyframe_points:
            p.interpolation = 'LINEAR'
    vis(fb, [(S[9], S[11])])
# waste cubes: sit on the brain (line 9), get carried to the bin (line 10), pile up (line 11)
waste_ms = [mat("WasteG", (0.45, 0.8, 0.2), 0.5), mat("WasteP", (0.55, 0.3, 0.75), 0.5), mat("WasteB", (0.45, 0.35, 0.25), 0.6)]
BIN = (BRX + 2.35, BRY - 0.6)
binm = mat("Bin", (0.4, 0.45, 0.5), 0.5, metal=0.3)
binp = [cyl("BinBody", (BIN[0], BIN[1], 0.45), 0.42, 0.9, binm, r2=0.5, verts=20),
        cyl("BinRim", (BIN[0], BIN[1], 0.92), 0.52, 0.06, mat("BinRimM", (0.3, 0.32, 0.36), 0.5), verts=20)]
for o in binp:
    vis(o, [(S[9], S[12])])
for k in range(9):
    u = Vector((random.uniform(-0.8, 0.8), -1.0, random.uniform(0.0, 0.9))).normalized()
    p0 = on_brain(u, 1.12)
    wc = box("Waste", tuple(p0), (0.2, 0.2, 0.2), waste_ms[k % 3], bevel=0.02)
    wc.data.transform(Matrix.Translation(-p0)); wc.location = p0
    tgo = S[10] + 2 + k * 3
    key_loc(wc, [(tgo, tuple(p0)), (tgo + 10, (BRX + 1.6, BRY - 0.8, BRZ + 0.9)), (tgo + 18, (BIN[0], BIN[1], 1.6)), (tgo + 22, (BIN[0], BIN[1], 0.7))])
    keyrot(wc, [(tgo, (0, 0, 0)), (tgo + 22, (2.0, 1.5, 0.5))])
    vis(wc, [(S[9], tgo + 22)])
for k in range(46):
    if k < 28:
        u = Vector((random.uniform(-1, 1), -random.uniform(0.6, 1.0), random.uniform(-0.1, 1.0))).normalized()
        p0 = on_brain(u, 1.12)
    else:
        a = random.uniform(0, 6.283); rr = random.uniform(0.95, 1.6)
        p0 = Vector((BRX + rr * math.cos(a), BRY - abs(rr * math.sin(a)) * 0.8, 0.12 + random.uniform(0, 0.25) if rr > 1.0 else 1.25))
    wc = box("Pile", tuple(p0), (0.24, 0.24, 0.24), waste_ms[k % 3], bevel=0.02)
    wc.rotation_euler = (random.uniform(0, 1), random.uniform(0, 1), random.uniform(0, 3))
    pop(wc, S[11] + int(k * 0.6), 4)
    gone_at(wc, S[12])
brain_grey = mat("BrainGrey", (0.6, 0.55, 0.55), 0.6)

# =================== lines 7-8: day 3 — wiggling hedges, walking shadows, floating rings ===================
bush_m = mat("BushH", (0.2, 0.55, 0.2), 0.85)
for i, (x, y, r) in enumerate([(-2.0, 3.4, 0.85), (2.9, 3.6, 0.9), (0.4, 5.0, 1.0)]):
    g = group("WBush", (x, y, r * 0.8))
    pr = [sphere("WBushS", (x, y, r * 0.8), r, bush_m, scale=(1.2, 0.9, 0.9), sub=2, smooth=False)]
    for sx in (-1, 1):
        pr.append(sphere("BEyeW", (x + sx * 0.22 * r, y - 0.82 * r, r * 1.0), 0.16 * r, eyew, sub=2))
        pr.append(sphere("BEyeB", (x + sx * 0.22 * r, y - 0.95 * r, r * 1.0), 0.08 * r, eyeb, sub=1))
    attach(pr, g)
    keyrot(g, [(S[7], (0, 0, 0)), (FRAMES, (0, 0, 0))])
    for f in range(S[7], E(8) + 1, 5):
        g.rotation_euler = (0.12 * math.sin(f * 0.7 + i), 0.22 * math.sin(f * 0.9 + i * 2), 0); g.keyframe_insert("rotation_euler", frame=f)
    vis(g, [(S[7], S[9])])
shadow_m = mat("ShadowM", (0.07, 0.05, 0.12), 0.8)
for j, (yy, x0, x1) in enumerate([(3.0, -4.5, 3.5), (2.3, 4.2, -3.6)]):
    sh, SD = person(f"Shadow{j}", (0, 0, 0), 1.05, shadow_m, shadow_m, shadow_m, shadow_m)
    key_loc(sh, [(S[7], (x0 + (x1 - x0) * 0.1, yy, 0)), (E(8), (x1, yy, 0))])
    for fc in fcurves(sh):
        for p in fc.keyframe_points:
            p.interpolation = 'LINEAR'
    sh.rotation_euler = (0, 0, math.radians(90 if x1 > x0 else -90))
    for f in range(S[7], E(8), 4):
        for k, lg in enumerate(SD["legs"]):
            lg.rotation_euler = (0.45 * (1 if ((f - S[7]) // 4 + k) % 2 else -1), 0, 0); lg.keyframe_insert("rotation_euler", frame=f)
    vis(sh, [(S[7] + 6 * j, S[9])])
ring_cols = [(1.0, 0.3, 0.8), (0.3, 0.9, 1.0), (1.0, 0.85, 0.2), (0.6, 0.4, 1.0), (0.3, 1.0, 0.5), (1.0, 0.5, 0.2)]
for k in range(10):
    c = ring_cols[k % 6]
    bpy.ops.mesh.primitive_torus_add(major_radius=random.uniform(0.2, 0.4), minor_radius=0.05,
                                     location=(random.uniform(-3, 3.5), random.uniform(1.8, 4.5), random.uniform(0.5, 1.5)))
    rg = bpy.context.object; rg.data.materials.append(glow_mat(f"Ring{k}", c, 3.0))
    p0 = tuple(rg.location)
    key_loc(rg, [(S[7], p0), (E(8), (p0[0] + random.uniform(-0.5, 0.5), p0[1], p0[2] + random.uniform(1.0, 2.0)))])
    keyrot(rg, [(S[7], (0, 0, 0)), (E(8), (random.uniform(2, 6), random.uniform(2, 6), 0))])
    vis(rg, [(S[7] + 2 + k, S[9])])

# =================== lines 12-13: the record — calendar 1..11, trophy, then the closed record book ===================
RX, RY = -6.0, 2.0
pod = box("RPodium", (RX, RY, 0.45), (1.5, 1.5, 0.9), gold_m, bevel=0.05)
vis(pod, [(S[12], S[14])])
tro = group("Trophy", (RX, RY, 0.9))
tp = [box("TroBase", (RX, RY, 1.0), (0.6, 0.6, 0.2), mat("TroBaseM", (0.2, 0.15, 0.12), 0.5)),
      cyl("TroStem", (RX, RY, 1.25), 0.07, 0.35, gold_m, verts=12),
      cyl("TroCup", (RX, RY, 1.75), 0.18, 0.7, gold_m, r2=0.48, verts=24)]
for sx in (-1, 1):
    bpy.ops.mesh.primitive_torus_add(major_radius=0.2, minor_radius=0.045, location=(RX + sx * 0.5, RY, 1.8), rotation=(math.radians(90), 0, 0))
    o = bpy.context.object; o.data.materials.append(gold_m); tp.append(o)
attach(tp, tro)
pop(tro, S[12] + 2, 6, S[13])
CAX = RX - 1.9
cal_m = mat("CalBack", (0.25, 0.25, 0.3), 0.6)
calp = [box("CalStand", (CAX, RY + 0.12, 0.9), (1.1, 0.12, 1.8), cal_m, bevel=0.03)]
for o in calp:
    vis(o, [(S[12], S[13])])
pg_m = mat("Page", (0.98, 0.98, 0.96), 0.6)
ink_m = mat("Ink", (0.08, 0.08, 0.1), 0.5)
for k in range(1, 12):
    yk = RY + 0.05 - 0.012 * (12 - k)
    g = group(f"Page{k}", (CAX, yk, 1.1))
    pp = [box("PageB", (CAX, yk, 1.1), (0.95, 0.01, 1.2), pg_m), box("PageTop", (CAX, yk - 0.006, 1.6), (0.95, 0.01, 0.2), red_lab),
          text("PageN", str(k), (CAX, yk - 0.012, 1.02), 0.75 if k < 10 else 0.62, ink_m, extrude=0.005)]
    attach(pp, g)
    vis(g, [(S[12], S[13] if k == 11 else W(12, 0.04 + 0.075 * (k - 1)) + 11)])
    if k < 11:
        tf = W(12, 0.04 + 0.075 * (k - 1))
        key_loc(g, [(tf, (CAX, yk, 1.1)), (tf + 10, (CAX - 2.2, yk - 0.8, 3.3))])
        keyrot(g, [(tf, (0, 0, 0)), (tf + 10, (math.radians(-60), math.radians(140), math.radians(30)))])
# line 13: the record book, slammed shut with a big red X
bookg = group("Book", (RX, RY, 0.9))
cover_m = mat("Cover", (0.75, 0.12, 0.12), 0.5)
bk = [box("BookCover", (RX, RY, 1.95), (1.5, 0.35, 2.0), cover_m, bevel=0.04),
      box("BookPages", (RX + 0.06, RY - 0.01, 1.95), (1.42, 0.3, 1.9), pg_m),
      text("BookT", "RECORDS", (RX, RY - 0.19, 2.45), 0.26, gold_m, extrude=0.02)]
attach(bk, bookg)
vis(bookg, [(S[13], S[14])])
xg = group("XStamp", (RX, RY - 0.3, 1.8))
xp = [boxc("X1", (RX, RY - 0.3, 1.8), (0.25, 0.08, 1.9), red_lab), boxc("X2", (RX, RY - 0.3, 1.8), (0.25, 0.08, 1.9), red_lab)]
xp[0].rotation_euler = (0, math.radians(45), 0); xp[1].rotation_euler = (0, math.radians(-45), 0)
attach(xp, xg)
keyscale(xg, [(0, 0.001), (W(13, 0.3) - 1, 0.001), (W(13, 0.3), 2.2), (W(13, 0.3) + 4, 0.95), (W(13, 0.3) + 6, 1.0), (S[14] - 1, 1.0), (S[14], 0.001)])
burst((RX, RY - 0.4, 1.8), W(13, 0.3) + 3, n=12, r=0.9, size=0.07, material=spark_m, f_out=S[14])

# =================== line 14: lab rat that never sleeps + hourglass ===================
RTX, RTY, RTZ = -3.4, 0.8, 0.9
lab_t = [box("LabTop", (RTX, RTY, RTZ - 0.04), (2.4, 1.3, 0.08), ped_m, bevel=0.02)]
for dx in (-1.1, 1.1):
    for dy in (-0.55, 0.55):
        lab_t.append(box("LabLeg", (RTX + dx, RTY + dy, (RTZ - 0.08) / 2), (0.07, 0.07, RTZ - 0.08), mat("LabLegM", (0.6, 0.62, 0.66), 0.4, metal=0.5)))
for o in lab_t:
    vis(o, [(S[14], S[15])])
rat_m = mat("Rat", (0.82, 0.82, 0.86), 0.7)
pinkm = mat("RatPink", (1.0, 0.65, 0.7), 0.5)
RX0 = RTX - 0.3
rat = group("Rat", (RX0, RTY, RTZ))
rp = [sphere("RatBody", (RX0 + 0.15, RTY, RTZ + 0.3), 0.3, rat_m, scale=(1.5, 0.95, 0.95), sub=3),
      sphere("RatHead", (RX0 - 0.42, RTY - 0.12, RTZ + 0.42), 0.22, rat_m, scale=(1.25, 1.0, 0.95), sub=3),
      sphere("RatNose", (RX0 - 0.66, RTY - 0.22, RTZ + 0.42), 0.05, pinkm, sub=2)]
for sy in (-1, 1):
    e_ = sphere("RatEar", (RX0 - 0.32, RTY - 0.12 + sy * 0.17, RTZ + 0.64), 0.12, pinkm, scale=(0.5, 1, 1), sub=2)
    e_.rotation_euler = (0, 0, math.radians(30)); rp.append(e_)
for sx in (-1, 1):
    rp.append(sphere("RatEyeW", (RX0 - 0.48 + sx * 0.08, RTY - 0.31, RTZ + 0.5), 0.07, eyew, sub=2))
    rp.append(sphere("RatEyeB", (RX0 - 0.48 + sx * 0.08, RTY - 0.37, RTZ + 0.5), 0.035, eyeb, sub=1))
rp.append(tube("RatTail", [(RX0 + 0.55, RTY, RTZ + 0.2), (RX0 + 0.9, RTY - 0.1, RTZ + 0.05), (RX0 + 1.2, RTY - 0.35, RTZ + 0.08), (RX0 + 1.3, RTY - 0.6, RTZ + 0.25)],
               [0.04, 0.03, 0.02, 0.012], pinkm))
for dx in (-0.25, 0.4):
    for dy in (-0.15, 0.15):
        rp.append(sphere("RatFoot", (RX0 + dx, RTY + dy, RTZ + 0.03), 0.05, pinkm, scale=(1.4, 1, 0.6), sub=1))
attach(rp, rat)
vis(rat, [(S[14], S[15])])
for f in range(S[14], E(14), 6):
    rat.location = (RX0, RTY, RTZ + (0.05 if (f // 6) % 2 else 0)); rat.keyframe_insert("location", frame=f)
HGX = RTX + 0.75
glass_m = bpy.data.materials.new("HGlass"); glass_m.use_nodes = True
_b = glass_m.node_tree.nodes["Principled BSDF"]
_b.inputs["Base Color"].default_value = (0.8, 0.95, 1.0, 1); _b.inputs["Alpha"].default_value = 0.3; _b.inputs["Roughness"].default_value = 0.05
hgp = [cyl("HGTop", (HGX, RTY, RTZ + 1.0), 0.32, 0.06, bedwood, verts=20), cyl("HGBot", (HGX, RTY, RTZ + 0.03), 0.32, 0.06, bedwood, verts=20),
       cyl("HGUp", (HGX, RTY, RTZ + 0.75), 0.03, 0.44, glass_m, r2=0.27, verts=20), cyl("HGLo", (HGX, RTY, RTZ + 0.28), 0.27, 0.44, glass_m, r2=0.03, verts=20)]
for dx in (-0.27, 0.27):
    hgp.append(cyl("HGPost", (HGX + dx, RTY - 0.1, RTZ + 0.52), 0.03, 0.98, bedwood, verts=8))
for o in hgp:
    vis(o, [(S[14], S[15])], tuple(o.scale))
sand_m = mat("Sand", (1.0, 0.78, 0.3), 0.6)
st_ = cyl("SandTop", (HGX, RTY, RTZ + 0.55), 0.02, 0.36, sand_m, r2=0.22, verts=20)
st_.data.transform(Matrix.Translation((0, 0, 0.18)))
sb_ = cyl("SandBot", (HGX, RTY, RTZ + 0.07), 0.23, 0.36, sand_m, r2=0.0, verts=20)
sb_.data.transform(Matrix.Translation((0, 0, 0.18)))
keyscale(st_, [(0, 0.001), (S[14] - 1, 0.001), (S[14], (1, 1, 1)), (E(14) - 1, (0.5, 0.5, 0.25)), (E(14), 0.001)])
keyscale(sb_, [(0, 0.001), (S[14] - 1, 0.001), (S[14], (0.5, 0.5, 0.2)), (E(14) - 1, (1, 1, 0.75)), (E(14), 0.001)])

# =================== you / twin: positions, poses ===================
HID = (0, 40, 0)
jumps(you, [(0, (YX, YY, 0)), (S[6], (BRX - 2.3, BRY - 0.6, 0)), (S[7], (YX, YY, 0)), (S[9], HID), (S[15], (YX, YY, 0))])
# line 16: fall back into the bed; line 17: asleep
key_loc(you, [(W(16, 0.3), (YX, YY, 0)), (W(16, 0.55), (YX, YY - 0.05, 0.65)), (FRAMES, (YX, YY - 0.05, 0.65))])
for fc in fcurves(you):
    if fc.data_path == "location":
        for p in fc.keyframe_points:
            p.interpolation = 'CONSTANT' if int(round(p.co[0])) < W(16, 0.3) else 'BEZIER'
yr = [(0, (0, 0, 0)), (S[6], (0, 0, math.radians(15))), (S[7], (0, 0, 0))]
for f in range(S[3], E(3) + 1, 5):
    yr.append((f, (0, 0.2 * (1 if ((f - S[3]) // 5) % 2 else -1), 0.1 * math.sin(f))))
yr += [(S[4], (0, 0, 0)), (W(16, 0.3), (0, 0, 0)), (W(16, 0.55), (math.radians(-90), 0, 0)), (FRAMES, (math.radians(-90), 0, 0))]
yr.sort(key=lambda k: k[0])
keyrot(you, yr)
vis(you, [(0, S[9]), (S[15], FRAMES)])
jumps(twin, [(0, (TWX, TWY, 0)), (S[17], (TWX - 0.2, YY + 0.2, 0))])
twin.rotation_euler = (0, 0, math.radians(-15)); twin.keyframe_insert("rotation_euler", frame=0)
vis(twin, [(S[1], S[5]), (S[17], FRAMES)])
# twin smiles wide-awake; you: arms stretch in the yawn, raise too late for the ball
for k, ag in enumerate(YD["arms"]):
    sx = -1 if k == 0 else 1
    keyrot(ag, [(S[2] + 2, (0, 0, 0)), (S[2] + 9, (0, sx * math.radians(150), 0)), (E(2) - 4, (0, sx * math.radians(150), 0)), (S[3], (0, 0, 0)),
                (W(4, 0.72), (0, 0, 0)), (W(4, 0.85), (0, -sx * math.radians(110), 0)), (S[5] - 1, (0, -sx * math.radians(110), 0)), (S[5], (0, 0, 0))])
ta = TD["arms"][0]
keyrot(ta, [(S[4], (0, 0, 0)), (W(4, 0.15), (0, 0, 0)), (W(4, 0.32), (0, math.radians(120), 0)), (S[5] - 1, (0, math.radians(120), 0)), (S[5], (0, 0, 0))])
for f in range(S[17], FRAMES, 6):        # twin waves at the end
    ta.rotation_euler = (0, math.radians(130 if (f // 6) % 2 else 100), 0); ta.keyframe_insert("rotation_euler", frame=f)
zzz("ZSleep", (YX + 0.2, YY + 1.6, 1.0), W(16, 0.6), n=3, size=0.28, rise=1.5)
zzz("ZSleep2", (YX + 0.2, YY + 1.6, 1.0), S[17], n=3, size=0.28, rise=1.5)
zzz("ZSleep3", (YX + 0.2, YY + 1.6, 1.0), S[17] + 24, n=3, size=0.28, rise=1.5)

# =================== sky mood per day: normal / dusk (day 2) / purple haze (day 3) ===================
def mood(f, energy, col, bgs):
    sun.data.energy = energy; sun.data.keyframe_insert("energy", frame=f)
    sun.data.color = col; sun.data.keyframe_insert("color", frame=f)
    bg.inputs["Strength"].default_value = bgs; bg.inputs["Strength"].keyframe_insert("default_value", frame=f)
NORM = (4.2, (1.0, 0.96, 0.88), 0.85)
DUSK = (3.4, (1.0, 0.6, 0.38), 0.5)
HAZE = (3.6, (1.0, 0.5, 0.95), 0.45)
for f, m_ in [(0, NORM), (S[5] - 1, NORM), (S[5], DUSK), (S[7] - 1, DUSK), (S[7], HAZE), (S[9] - 1, HAZE), (S[9], NORM)]:
    mood(f, *m_)
for path_o in (sun.data, w.node_tree):
    ad = path_o.animation_data
    if ad and ad.action:
        for fc in fcurves(path_o):
            for p in fc.keyframe_points:
                p.interpolation = 'CONSTANT'

# ---------------- views (camera, subject) per line; subject sits in the lower third ----------------
V, V2 = {}, {}
V[0] = ((1.6, -6.2, 2.0), (-0.2, 1.8, 1.0));        V2[0] = ((-1.2, -5.6, 2.0), (-0.2, 1.8, 1.2))
V[1] = ((-1.5, -6.0, 2.0), (-0.1, YY, 1.0));        V2[1] = ((1.2, -5.6, 2.0), (-0.1, YY, 1.0))
V[2] = ((2.8, -3.9, 1.8), (1.35, YY, 1.2));         V2[2] = ((0.4, -3.5, 1.8), (1.35, YY, 1.3))
V[3] = ((1.9, -3.9, 1.8), (YX, YY, 1.3));           V2[3] = ((-0.6, -3.7, 1.8), (YX, YY, 1.3))
V[4] = ((0.2, -6.6, 2.2), (-0.1, YY, 1.2));         V2[4] = ((-1.1, -5.9, 2.2), (-0.1, YY, 1.2))
V[5] = ((-0.6, -4.0, 1.8), (YX + 0.6, YY, 1.3));    V2[5] = ((1.7, -3.6, 1.8), (YX + 0.6, YY, 1.3))
V[6] = ((6.8, -5.0, 2.5), (8.3, 3.0, 1.5));         V2[6] = ((9.9, -4.6, 2.5), (8.3, 3.0, 1.5))
V[7] = ((-2.0, -7.2, 2.5), (0.3, 2.6, 1.1));        V2[7] = ((0.6, -6.6, 2.5), (0.3, 2.6, 1.1))
V[8] = ((2.6, -6.9, 2.5), (0.3, 2.8, 1.1));         V2[8] = ((-1.5, -6.5, 2.5), (0.3, 2.8, 1.1))
V[9] = ((10.6, -4.2, 2.5), (9.3, 3.0, 1.6));        V2[9] = ((8.1, -4.0, 2.5), (9.3, 3.0, 1.6))
V[10] = ((8.2, -4.6, 2.5), (9.8, 3.0, 1.4));        V2[10] = ((10.6, -4.2, 2.5), (9.8, 3.0, 1.4))
V[11] = ((9.0, -5.4, 3.0), (9.2, 3.0, 1.4));        V2[11] = ((9.7, -4.0, 2.6), (9.2, 3.0, 1.4))
V[12] = ((-5.6, -4.8, 2.2), (-6.9, 2.0, 1.2));      V2[12] = ((-8.1, -4.4, 2.2), (-6.9, 2.0, 1.2))
V[13] = ((-7.0, -4.2, 2.2), (-6.0, 2.0, 1.4));      V2[13] = ((-5.0, -3.8, 2.2), (-6.0, 2.0, 1.5))
V[14] = ((-2.6, -2.3, 1.8), (-3.3, 0.8, 1.1));      V2[14] = ((-4.2, -2.1, 1.8), (-3.3, 0.8, 1.1))
V[15] = ((-1.0, -4.6, 1.8), (YX, YY, 1.1));         V2[15] = ((2.4, -4.1, 1.8), (YX, YY, 1.1))
V[16] = ((2.3, -4.2, 2.6), (YX, YY + 0.6, 0.8));    V2[16] = ((0.0, -3.8, 2.8), (YX, YY + 0.8, 0.6))
V[17] = ((-1.0, -5.3, 2.8), (0.0, YY + 0.6, 0.8));  V2[17] = ((1.4, -6.3, 3.2), (0.0, YY + 0.6, 0.8))

def LB(i, name, body, m_, size=None, f_in=None, f_out=None, Dk=0.55, end=False, v=0.26, u=0.0):
    mid = lambda a, b: tuple((Vector(a) + Vector(b)) / 2)
    view = V2[i] if end else (mid(V[i][0], V2[i][0]), mid(V[i][1], V2[i][1]))
    cl = Vector(CL(view)); D = (Vector(view[1]) - cl).length * Dk
    s_ = 0.9 * fit(body, D, size if size else 1e9)
    return label(name, body, view, D, v, s_, m_, (S[i] + 3) if f_in is None else f_in,
                 E(i) if f_out is None else f_out, u)
LB(0, "L0", "NEVER SLEEP?", red_lab)
LB(1, "L1a", "RESTED", green_lab, u=-0.24, v=0.2, size=0.34)
LB(1, "L1b", "NO SLEEP", red_lab, u=0.24, v=0.31, size=0.34, f_in=S[1] + 8)
LB(2, "L2", "HOUR 20: YAWN!", lab_m)
LB(3, "L3", "DRUNK BRAIN", red_lab)
LB(4, "L4", "TOO SLOW!", red_lab, f_in=W(4, 0.62))
LB(5, "L5", "DAY 2", white_lab)
LB(6, "L6", "MICROSLEEP", lab_m)
LB(7, "L7", "DAY 3", pink_lab)
LB(8, "L8", "NOT REAL!", pink_lab)
LB(9, "L9", "CLEANING SHIFT", blue_lab)
LB(10, "L10", "WASTE OUT", green_lab)
LB(11, "L11", "TRASH PILES UP", red_lab)
LB(12, "L12", "11 DAYS (1964)", lab_m)
LB(13, "L13", "TOO RISKY", red_lab)
LB(14, "L14", "NO SLEEP = DEADLY", red_lab)
LB(15, "L15", "THE TWIST...", lab_m)
LB(16, "L16", "FORCED SLEEP", blue_lab, f_in=W(16, 0.45))
LB(17, "L17", "HOW LONG?", lab_m, end=True, f_in=S[17] + 6, Dk=0.45)

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
