# Day 8 — What if you laid a billion dollars end to end?  Build: python3 episodes/008-billion-end-to-end/scene.py
# Reference style: base (helpers, lawn/soil, house, garden) copied from episodes/003-lift-million-ref/scene.py
import bpy, math, random, os, json
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
random.seed(8)
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
bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 0, -0.003))
fp = bpy.context.object; fp.scale = (400000, 400000, 1); fp.location = (0, 200050, -0.008)
fp.data.materials.append(far)
stone_m = mat("Stone", (0.7, 0.66, 0.6), 0.8)
for i in range(30):
    sphere("Peb", (random.uniform(-30, 30), FRONT_Y - 0.02, random.uniform(-5.6, -0.6)), random.uniform(0.12, 0.3),
           stone_m, scale=(1.3, 0.5, 0.8), sub=1, smooth=False)

for sx in (-1, 1):   # lawn beside the diorama (no void at the sides)
    bpy.ops.mesh.primitive_plane_add(size=1, location=(sx * 100016, 26.2, -0.003))
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
for (x, y) in [(-9, 5), (-8, 22), (8.8, 24), (-12, 30), (26, 30), (-1, 26), (12, 34)]:
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



# =====================================================================================
# Day 8 — What if you laid a billion dollars end to end?
# Numbers: US $1 bill 15.6 cm long (6.14 in), ~1 g, ~0.11 mm thick.
#   10 bills = 1.56 m; 1,000 = 156 m; 1,000,000 = 156 km (marathon 42.195 km -> ~3.7 marathons)
#   1,000,000,000 = 156,000 km. Earth's equator ~40,075 km -> ~3.9 laps. Moon ~384,400 km -> ~40%.
#   Walking at 5 km/h: 31,200 h ~ 3.6 years nonstop. One bill per second: 1e9 s ~ 31.7 years.
#   Volume of 1e9 $1 bills ~ 1e9 x 15.6 x 6.6 x 0.011 cm3 ~ 1,130 m3 -> a cube ~10.4 m on a side.
# Visual cheat (cartoon): beyond the first 1.56 m the line is drawn wider so it stays visible from far away.
# =====================================================================================
from mathutils import Quaternion, Matrix
bill_m = mat("Bill", (0.3, 0.68, 0.25), 0.8)
bill_ink = mat("BillInk", (0.12, 0.38, 0.16), 0.7)
def keyscale(o, keys):
    for f, s in keys:
        o.scale = (s,) * 3 if not isinstance(s, tuple) else s
        o.keyframe_insert("scale", frame=f)
def keyrot(o, keys):
    for f, r in keys:
        o.rotation_euler = r; o.keyframe_insert("rotation_euler", frame=f)

lab_m = mat("LabelM", (1.0, 0.85, 0.2), 0.4, emit=(1.0, 0.8, 0.2), emit_strength=0.9)
white_lab = mat("LabW", (1, 1, 1), 0.4, emit=(1, 1, 1), emit_strength=0.8)
red_lab = mat("LabR", (0.95, 0.1, 0.08), 0.4, emit=(1.0, 0.1, 0.05), emit_strength=1.2)
green_lab = mat("LabG", (0.35, 0.95, 0.35), 0.4, emit=(0.3, 0.95, 0.3), emit_strength=1.0)
spark_m = glow_mat("Spark", (1.0, 0.95, 0.7), 5.0)
eyew = mat("EyeW", (1, 1, 1), 0.3)
eyeb = mat("EyeB", (0.03, 0.03, 0.04), 0.3)
bill_seam = stripe_mat("BillSeam", (0.32, 0.7, 0.27), (0.1, 0.32, 0.12), axis="X", freq=2 * math.pi / 0.156, thresh=0.96, rough=0.8)
line_m = mat("LineM", (0.3, 0.75, 0.25), 0.7, emit=(0.25, 0.8, 0.2), emit_strength=0.35)
wedge_m = mat("WedgeM", (0.3, 0.8, 0.25), 0.7, emit=(0.3, 0.9, 0.25), emit_strength=0.9)

def label(name, body, loc, size, m_, f_in, f_out, face=None):
    t = text(name, body, loc, size, m_, extrude=size * 0.08)
    if face is not None:   # turn the text to face a camera position
        dx, dy = face[0] - loc[0], face[1] - loc[1]
        t.rotation_euler = (math.radians(90), 0, math.atan2(dx, -dy))
    pop(t, f_in, 5, f_out)
    return t
def burst(loc, f, n=10, r=0.12, size=0.012, f_out=None, material=None):
    for k in range(n):
        a = k / n * 6.283
        s_ = sphere("Burst", (loc[0] + r * math.cos(a), loc[1] - 0.05, loc[2] + r * math.sin(a)), size, material or spark_m, sub=1)
        pop(s_, f, 3, f_out if f_out else f + 10)

# one generic cartoon $1 bill (no real design: just "1" in the corners and a plain oval)
def bill(name, loc, rz=0.0):
    g = group(name, loc, rz)
    x, y, z = loc
    ps = [box(name + "B", (x, y, z), (0.156, 0.066, 0.003), bill_m),
          box(name + "F", (x, y, z + 0.0018), (0.142, 0.054, 0.0005), mat(name + "FM", (0.55, 0.85, 0.45), 0.8)),
          sphere(name + "O", (x, y, z + 0.0022), 0.022, bill_ink, scale=(1.0, 0.85, 0.05), sub=2)]
    for sx in (-1, 1):
        ps.append(text(name + "N", "1", (x + sx * 0.055, y, z + 0.0025), 0.026, bill_ink, rot=(0, 0, 0)))
    attach(ps, g)
    return g

# ---------------- "you": a cartoon person with hip-pivot legs (walks) and hair that can go gray ----------------
skin_m = mat("Skin", (0.95, 0.74, 0.58), 0.6)
pants_m = mat("Pants", (0.2, 0.3, 0.6), 0.8)
shoe_m = mat("Shoe", (0.15, 0.15, 0.18), 0.6)
shirt_m = mat("ShirtY", (0.95, 0.3, 0.35), 0.7)
hair_m = mat("HairY", (0.28, 0.16, 0.07), 0.8)
K = 0.86
PX0, PY0 = 0.0, 0.15
you = group("You", (PX0, PY0, 0))
def P_(dx, dy, dz):
    return (PX0 + dx * K, PY0 + dy * K, dz * K)
yp = []
legs = []
for sx in (-1, 1):
    lg = group("LegG", P_(sx * 0.13, 0, 0.78))
    lps = [tube("Leg", [P_(sx * 0.13, 0, 0.8), P_(sx * 0.14, 0, 0.08)], [0.1 * K, 0.09 * K], pants_m),
           box("ShoeP", P_(sx * 0.14, -0.06, 0.05), (0.17 * K, 0.3 * K, 0.1 * K), shoe_m, bevel=0.03)]
    attach(lps, lg); legs.append(lg)
arms = []
for sx in (-1, 1):
    ag = group("ArmG", P_(sx * 0.3, 0, 1.33))
    aps = [tube("Arm", [P_(sx * 0.3, 0, 1.35), P_(sx * 0.38, -0.03, 1.05), P_(sx * 0.38, -0.06, 0.8)], [0.07 * K] * 3, shirt_m),
           sphere("Hand", P_(sx * 0.38, -0.06, 0.76), 0.068 * K, skin_m, sub=2)]
    attach(aps, ag); arms.append(ag)
    yp.append(sphere("EyeWp", P_(sx * 0.085, -0.21, 1.72), 0.055 * K, eyew, scale=(1, 0.6, 1.2), sub=2))
    yp.append(sphere("EyeBp", P_(sx * 0.085, -0.25, 1.72), 0.028 * K, eyeb, sub=1))
yp.append(sphere("Torso", P_(0, 0, 1.1), 1.0, shirt_m, scale=(0.3 * K, 0.22 * K, 0.4 * K), sub=3))
yp.append(sphere("Head", P_(0, 0, 1.68), 0.25 * K, skin_m, sub=3))
yp.append(sphere("HairP", P_(0, 0.04, 1.81), 0.24 * K, hair_m, scale=(1.05, 1.0, 0.55), sub=2))
yp.append(tube("Smile", [P_(-0.08, -0.23, 1.6), P_(0, -0.26, 1.56), P_(0.08, -0.23, 1.6)], [0.014 * K] * 3, eyeb))
beard = sphere("Beard", P_(0, -0.13, 1.5), 0.2 * K, mat("BeardM", (0.92, 0.92, 0.92), 0.9), scale=(1.0, 0.7, 0.75), sub=2)
yp.append(beard)
attach(yp + legs + arms, you)

# =============== line 0: hook — a $1,000,000,000 title, cash rains, a green line shoots off across the lawn ===============
XS, YL = 0.45, -0.38            # start of the line of bills (in front of "you", near the cut face)
title = text("Title", "$1,000,000,000", (0.6, -0.4, 2.55), 0.3, green_lab, extrude=0.03)
pop(title, 1, 6, S[1])
for i in range(30):
    p = (random.uniform(-0.8, 2.0), random.uniform(-0.9, 0.4), random.uniform(1.8, 3.2))
    b = box("FlyBill", p, (0.156, 0.066, 0.003), bill_m)
    land = (p[0] + random.uniform(-0.3, 0.3), max(p[1] - 0.2, -1.0), 0.004)
    key_loc(b, [(0, p), (random.randint(16, 30), land)])
    keyrot(b, [(0, (random.uniform(-1, 1), random.uniform(-1, 1), random.uniform(0, 3))), (30, (0, 0, random.uniform(0, 3)))])
    gone_at(b, S[1] - 1, 3)

# ---------------- line 1: one bill falls from your hand; line 2: a ruler shows 15.6 cm ----------------
b1 = bill("Bill1", (XS + 0.078, YL, 0.002), 0.0)
key_loc(b1, [(0, (XS + 0.25, YL + 0.1, 0.75)), (S[1] + 2, (XS + 0.25, YL + 0.1, 0.75)), (S[1] + 14, (XS + 0.078, YL, 0.002))])
keyrot(b1, [(S[1] + 2, (0.5, 0.3, 0.9)), (S[1] + 8, (-0.3, 0.2, -0.4)), (S[1] + 14, (0, 0, 0))])
hide_until(b1, S[1] + 2)
keyrot(arms[1], [(S[1] - 4, (0, 0, 0)), (S[1] + 2, (-1.1, 0, 0.3)), (S[1] + 10, (0, 0, 0))])
label("L1d", "$1", (XS + 0.5, YL - 0.1, 1.4), 0.36, green_lab, S[1] + 4, S[2])
ruler_m = mat("Ruler", (1.0, 0.82, 0.15), 0.5)
rg = group("Ruler", (XS + 0.078, YL - 0.07, 0.006))
rps = [box("RulerB", (XS + 0.078, YL - 0.065, 0.006), (0.17, 0.035, 0.008), ruler_m)]
for k in range(17):
    rps.append(box("Tick", (XS + k * 0.01, YL - 0.075, 0.011), (0.0015, 0.015 if k % 5 else 0.025, 0.002), eyeb))
attach(rps, rg)
pop(rg, S[2], 5, S[3])
label("L156cm", "15.6 cm", (XS + 0.2, YL + 0.1, 0.6), 0.13, lab_m, S[2] + 3, S[3], face=(-0.45, -1.25, 0.8))
for sx in (-1, 1):   # little arrows at both ends
    a_ = cyl("Arrow", (XS + 0.078 + sx * 0.1, YL - 0.05, 0.12), 0.025, 0.06, red_lab, rot=(0, -sx * math.pi / 2, 0), r2=0.0, verts=8)
    pop(a_, S[2] + 2, 4, S[3])

# ---------------- line 3: ten bills in a row (1.56 m) — you lie down next to them ----------------
row = []
for k in range(1, 10):
    bk = bill(f"RowBill{k}", (XS + 0.078 + k * 0.156, YL, 0.002), 0.0)
    pop(bk, S[3] + 2 + k * 2, 3)
    row.append(bk)
LIE = S[3] + 10
you.keyframe_insert("location", frame=LIE - 4); you.keyframe_insert("rotation_euler", frame=LIE - 4)
you.location = (XS - 0.03, PY0 + 0.0, 0.34); you.rotation_euler = (0, math.radians(90), 0)
you.keyframe_insert("location", frame=LIE + 4); you.keyframe_insert("rotation_euler", frame=LIE + 4)
you.keyframe_insert("location", frame=S[4] - 3); you.keyframe_insert("rotation_euler", frame=S[4] - 3)
you.location = (PX0, PY0, 0); you.rotation_euler = (0, 0, 0)
you.keyframe_insert("location", frame=S[4] + 3); you.keyframe_insert("rotation_euler", frame=S[4] + 3)
label("L156m", "1.56 m", (XS + 0.78, YL - 0.1, 1.55), 0.26, lab_m, S[3] + 6, S[4])
label("LYou", "≈ YOU!", (XS + 0.78, YL - 0.1, 1.3), 0.2, white_lab, LIE + 4, S[4])
for sx in (0, 1):   # end markers
    m_ = box("EndMark", (XS + sx * 1.56, YL, 0.18), (0.015, 0.015, 0.36), red_lab)
    pop(m_, S[3] + 6, 4, S[4])

# ---------------- line 4: 1,000 bills — the line runs 156 m across the lawn to a flag ----------------
def strip(name, x0, x1, w0, w1, h0, h1, m_):
    """a tapered bar of bills from x0 to x1 (origin at x0 so it can grow in x)"""
    me = bpy.data.meshes.new(name)
    L_ = x1 - x0
    v = [(0, -w0 / 2, 0), (0, w0 / 2, 0), (0, w0 / 2, h0), (0, -w0 / 2, h0),
         (L_, -w1 / 2, 0), (L_, w1 / 2, 0), (L_, w1 / 2, h1), (L_, -w1 / 2, h1)]
    f_ = [(0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1), (3, 2, 6, 7), (0, 3, 7, 4), (1, 5, 6, 2)]
    me.from_pydata(v, [], f_); me.update()
    o = bpy.data.objects.new(name, me); sc.collection.objects.link(o)
    o.location = (x0, YL, 0.001); o.data.materials.append(m_)
    return o
X156 = XS + 156.0
s1 = strip("Strip156", XS + 1.56, X156, 0.066, 1.4, 0.004, 0.12, wedge_m)
keyscale(s1, [(0, 0.001), (S[4] - 1, 0.001), (S[4], (0.001, 1, 1)), (S[4] + 20, (1, 1, 1))])
flag = group("Flag", (X156, YL + 0.6, 0))
fps_ = [cyl("Pole", (X156, YL + 0.6, 2.0), 0.08, 4.0, trim_m, verts=8),
        box("FlagCloth", (X156 + 0.9, YL + 0.6, 3.5), (1.8, 0.05, 1.1), red_lab)]
attach(fps_, flag)
pop(flag, S[4] + 18, 5)
CAM4 = (22.0, -48.0, 34.0)
_d4 = (Vector((85.0, YL, 0.0)) - Vector(CAM4)).normalized()
L4P = tuple(Vector(CAM4) + _d4 * 55 + Vector((0, 0, 25)))
label("L156", "156 m", L4P, 8.0, lab_m, S[4] + 14, S[5] + 1, face=CAM4)
label("L1000", "1,000 BILLS", (L4P[0], L4P[1], L4P[2] + 7.5), 4.5, white_lab, S[4] + 8, S[5] + 1, face=CAM4)

# ---------------- lines 5-6: a million bills — 156 km to the horizon, past marathon gates ----------------
# (drawn wider and wider with distance so it reads from a plane-high camera; cartoon exaggeration)
X156K = XS + 156000.0
s2 = strip("Strip156k", X156, X156K, 1.4, 2600.0, 0.12, 300.0, wedge_m)
keyscale(s2, [(0, 1e-6), (S[5] - 1, 1e-6), (S[5], (0.0001, 1, 1)), (S[5] + 22, (1, 1, 1))])
# ground beyond the diorama, in front of it (so the high shot has no void)
bpy.ops.mesh.primitive_plane_add(size=1, location=(100200, -100001.6, -0.003))
o = bpy.context.object; o.scale = (200000, 200000, 1); o.data.materials.append(grass_m)
bpy.ops.mesh.primitive_plane_add(size=1, location=(-1400, -100080, -0.003))
o = bpy.context.object; o.scale = (3200, 200000, 1); o.data.materials.append(grass_m)
gate_m = mat("Gate", (0.95, 0.3, 0.25), 0.6, emit=(0.95, 0.3, 0.2), emit_strength=0.5)
CAM5 = (-900.0, -1700.0, 1100.0)
for k in range(1, 5):
    gx = XS + 42195.0 * k
    s_ = 0.13 * gx
    gg = group(f"Gate{k}", (gx, YL, 0))
    gps = [box("GateL", (gx, YL - s_ * 0.6, s_ * 0.5), (s_ * 0.08, s_ * 0.08, s_), gate_m),
           box("GateR", (gx, YL + s_ * 0.6, s_ * 0.5), (s_ * 0.08, s_ * 0.08, s_), gate_m),
           box("GateTop", (gx, YL, s_), (s_ * 0.1, s_ * 1.3, s_ * 0.18), white_lab)]
    attach(gps, gg)
    pop(gg, S[6] + 2 + k * 4, 5, S[7] + 2)
    label(f"LGate{k}", str(k), (gx, YL, s_ * 1.45), s_ * 0.4, lab_m if k < 4 else red_lab, S[6] + 4 + k * 4, S[7] + 2, face=CAM5)
_d5 = (Vector((60000.0, YL, 0.0)) - Vector(CAM5)).normalized()
L5P = tuple(Vector(CAM5) + _d5 * 1500 + Vector((0, 0, 820)))
label("L156k", "156 km", L5P, 140.0, lab_m, S[5] + 6, S[6] + 1, face=CAM5)
label("L1M", "1,000,000 BILLS", (L5P[0], L5P[1], L5P[2] + 170), 70.0, white_lab, S[5] + 3, S[6] + 1, face=CAM5)
label("L4Mar", "≈ 4 MARATHONS", (L5P[0], L5P[1], L5P[2] + 60), 95.0, lab_m, S[6] + 4, S[7] + 2, face=CAM5)

# ---------------- line 7: a BILLION $1 bills = a ~10 m cube of cash slams into the garden ----------------
cube_m = stripe_mat("CashCube", (0.3, 0.68, 0.25), (0.18, 0.48, 0.15), axis="Z", freq=55.0, thresh=0.3)
CX, CY, CS = 9.6, 5.6, 10.4
cube = box("CashCube", (CX, CY, CS / 2), (CS, CS, CS), cube_m, bevel=0.15)
for sx in (-1, 1):   # paper bands around it
    bd = box("Band", (CX, CY, CS / 2 + sx * 2.6), (CS + 0.06, CS + 0.06, 0.8), mat("BandM", (0.95, 0.85, 0.6), 0.6))
    bd.parent = cube; bd.matrix_parent_inverse = cube.matrix_world.inverted()
key_loc(cube, [(0, (CX, CY, 80)), (S[7] + 2, (CX, CY, 80)), (S[7] + 9, (CX, CY, CS / 2 - 0.4)), (S[7] + 12, (CX, CY, CS / 2))])
hide_until(cube, S[7] + 2); gone_at(cube, S[8] + 2, 2)
burst((CX, CY - CS / 2 - 0.3, 0.6), S[7] + 9, 16, 5.5, 0.25, S[7] + 18, bill_m)
CAM7 = (5.0, -15.0, 13.0)
label("L1B", "1,000,000,000 × $1", (CX - 1.5, CY - 3.0, 15.0), 1.3, green_lab, S[7] + 4, S[8] + 1, face=CAM7)
label("L10m", "≈ 10 m CUBE", (CX - 1.5, CY - 3.0, 13.4), 1.0, white_lab, S[7] + 12, S[8] + 1, face=CAM7)

# =============== lines 8-12: space — 156,000 km wraps Earth ~3.9 times, reaches ~40% to the Moon ===============
SP = Vector((-1.0e6, 0.0, 0.0))
space_m = glow_mat("Space", (0.012, 0.018, 0.06), 1.0)
dome = sphere("SpaceDome", tuple(SP), 420.0, space_m, sub=3)
dome.visible_shadow = False
star_g = glow_mat("Star", (1, 1, 0.95), 8.0)
for i in range(260):
    v = Vector((random.gauss(0, 1), random.gauss(0, 1), random.gauss(0, 1))).normalized()
    if v.y < -0.3:
        v.y = -v.y
    st = sphere("Star", tuple(SP + v * 400), random.uniform(0.6, 1.5), star_g, sub=1)
    st.visible_shadow = False
ER = 3.0
earth = group("Earth", tuple(SP), 0.0)
ocean_m = mat("Ocean", (0.1, 0.35, 0.85), 0.35, emit=(0.05, 0.2, 0.6), emit_strength=0.25)
land_m = mat("Land", (0.25, 0.65, 0.25), 0.8, emit=(0.15, 0.4, 0.1), emit_strength=0.15)
ice_m = mat("Ice", (0.95, 0.97, 1.0), 0.6)
eps = [sphere("EarthBall", tuple(SP), ER, ocean_m, sub=4)]
for (lat, lon, s_) in [(20, 30, 1.3), (45, 60, 1.1), (-10, 80, 0.9), (10, -60, 1.0), (40, -100, 1.2), (-25, 140, 0.8),
                       (55, 110, 1.0), (-15, -55, 0.9), (5, 20, 0.9), (30, 170, 0.7), (-30, 25, 0.7), (60, -40, 0.6)]:
    la, lo = math.radians(lat), math.radians(lon)
    d = Vector((math.cos(la) * math.cos(lo), math.cos(la) * math.sin(lo), math.sin(la)))
    c = sphere("Land", tuple(SP + d * (ER - 0.05)), s_, land_m, scale=(1, 1, 0.25), sub=2)
    c.rotation_mode = 'QUATERNION'; c.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(d)
    eps.append(c)
for sz in (-1, 1):
    eps.append(sphere("Pole", tuple(SP + Vector((0, 0, sz * (ER - 0.4)))), 1.0, ice_m, scale=(1.2, 1.2, 0.5), sub=2))
attach(eps, earth)
# the ribbon of cash around the Earth (curve, grows with bevel_factor_end)
cu = bpy.data.curves.new("Wrap", 'CURVE'); cu.dimensions = '3D'
cu.bevel_depth = 0.11; cu.bevel_resolution = 2; cu.use_fill_caps = True
sp_ = cu.splines.new('POLY'); N_ = 500; TURNS = 3.9
sp_.points.add(N_ - 1)
for i in range(N_):
    t = i / (N_ - 1) * TURNS
    th = 2 * math.pi * t - 2.4
    la = math.radians(-24 + 13 * t)
    R_ = ER + 0.1
    sp_.points[i].co = (R_ * math.cos(la) * math.cos(th), R_ * math.cos(la) * math.sin(th), R_ * math.sin(la), 1)
cu.materials.append(green_lab)
cu.bevel_factor_mapping_end = 'SPLINE'
wrap = bpy.data.objects.new("Wrap", cu); sc.collection.objects.link(wrap); wrap.location = tuple(SP)
attach([wrap], earth)
for f, v in [(0, 0.0), (S[8] + 4, 0.0), (S[9] + 2, 0.02), (S[10] - 1, 1 / TURNS), (S[10] + 2, 1 / TURNS), (S[11] - 2, 1.0)]:
    cu.bevel_factor_end = v; cu.keyframe_insert("bevel_factor_end", frame=f)
keyscale(wrap, [(S[11] - 1, 1.0), (S[11] + 2, 0.001)])
keyrot(earth, [(S[8], (0, 0, 0.0)), (S[11], (0, 0, 0.9)), (S[13], (0, 0, 1.4))])
# moon (distance squeezed for the shot; the 40% is measured along the real proportion)
MOON = SP + Vector((5.0, 9.0, 27.0)); MR = 1.25
moon_m = mat("Moon", (0.78, 0.78, 0.8), 0.9, emit=(0.6, 0.6, 0.62), emit_strength=0.2)
moon = sphere("Moon", tuple(MOON), MR, moon_m, sub=4)
mps = []
for k in range(7):
    v = Vector((random.uniform(-1, 1), random.uniform(-1, -0.2), random.uniform(-1, 1))).normalized()
    mps.append(sphere("Crater", tuple(MOON + v * (MR - 0.05)), random.uniform(0.1, 0.22), mat("CraterM", (0.55, 0.55, 0.58), 0.9), scale=(1, 1, 0.4), sub=2))
    mps[-1].rotation_mode = 'QUATERNION'; mps[-1].rotation_quaternion = Vector((0, 0, 1)).rotation_difference(v)
attach(mps, moon)
hide_until(moon, S[11] - 2)
dvec = (MOON - SP).normalized()
p0 = SP + dvec * (ER + 0.05); p1 = MOON - dvec * (MR + 0.05)
cu2 = bpy.data.curves.new("ToMoon", 'CURVE'); cu2.dimensions = '3D'
cu2.bevel_depth = 0.12; cu2.bevel_resolution = 2; cu2.use_fill_caps = True
sp2 = cu2.splines.new('POLY'); sp2.points.add(1)
sp2.points[0].co = (*(p0 - SP), 1); sp2.points[1].co = (*(p1 - SP), 1)
cu2.materials.append(green_lab)
tomoon = bpy.data.objects.new("ToMoon", cu2); sc.collection.objects.link(tomoon); tomoon.location = tuple(SP)
for f, v in [(0, 0.0), (S[11] + 2, 0.0), (S[12] + 4, 0.4)]:
    cu2.bevel_factor_end = v; cu2.keyframe_insert("bevel_factor_end", frame=f)
hide_until(tomoon, S[11])
for k in range(1, 15):   # the 60% still missing: a dotted line
    q = p0 + (p1 - p0) * (0.4 + 0.6 * k / 15)
    dt = sphere("Dot", tuple(q), 0.09, white_lab, sub=1)
    pop(dt, S[12] + 6 + k, 3, S[13])
CAM_E = SP + Vector((1.5, -12.5, 4.0))
CAM_M = SP + Vector((13.0, -36.0, 13.0))
label("L156kk", "156,000 km", tuple(SP + Vector((0, -1.0, 6.0))), 1.05, lab_m, S[8] + 2, S[9] + 1, face=tuple(CAM_E))
label("L1x", "1 LAP", tuple(SP + Vector((0, -1.0, 5.6))), 1.3, white_lab, S[10] - 6, S[10] + 2, face=tuple(CAM_E))
label("L39x", "3.9 LAPS!", tuple(SP + Vector((0, -1.0, 5.6))), 1.3, lab_m, S[10] + 3, S[11] - 1, face=tuple(CAM_E))
label("LMoon", "MOON", tuple(MOON + Vector((0, 0, 3.2))), 2.4, white_lab, S[11] + 2, S[13], face=tuple(CAM_M))
mid = p0 + (p1 - p0) * 0.4
label("L40", "40%", tuple(mid + Vector((-4.0, -1.0, 0.6))), 3.0, lab_m, S[12] + 6, S[13], face=tuple(CAM_M))

# =============== lines 13-14: walking the line nonstop — 3.5 years ===============
WALK0, WALK1 = S[13] - 2, S[15] - 2
WX0, WX1 = XS + 0.3, XS + 5.5
you.keyframe_insert("location", frame=WALK0 - 1); you.keyframe_insert("rotation_euler", frame=WALK0 - 1)
you.location = (WX0, YL + 0.35, 0); you.rotation_euler = (0, 0, math.radians(90))
you.keyframe_insert("location", frame=WALK0); you.keyframe_insert("rotation_euler", frame=WALK0)
you.location = (WX1, YL + 0.35, 0); you.keyframe_insert("location", frame=WALK1)
for f in range(WALK0, WALK1 + 1, 5):
    sgn = 1 if ((f - WALK0) // 5) % 2 else -1
    legs[0].rotation_euler = (0.55 * sgn, 0, 0); legs[0].keyframe_insert("rotation_euler", frame=f)
    legs[1].rotation_euler = (-0.55 * sgn, 0, 0); legs[1].keyframe_insert("rotation_euler", frame=f)
    arms[0].rotation_euler = (-0.5 * sgn, 0, 0); arms[0].keyframe_insert("rotation_euler", frame=f)
    arms[1].rotation_euler = (0.5 * sgn, 0, 0); arms[1].keyframe_insert("rotation_euler", frame=f)
for g_ in legs + arms:
    g_.rotation_euler = (0, 0, 0); g_.keyframe_insert("rotation_euler", frame=WALK1 + 2)
# walking pace label + "no sleep"
label("L5kmh", "5 km/h", (0, 0, 0), 0.28, white_lab, S[13] + 2, S[14])
label("LNoSl", "NO SLEEP!", (0, 0, 0), 0.26, red_lab, S[13] + 10, S[14])
label("L35y", "3.5 YEARS", (0, 0, 0), 0.34, lab_m, S[14] + 3, S[15])
walk_labels = [o for o in bpy.data.objects if o.name.startswith(("L5kmh", "LNoSl", "L35y"))]
# labels ride above the walker
for o in walk_labels:
    dz = {"L5": 3.25, "LN": 2.95, "L3": 3.2}[o.name[:2]]
    key_loc(o, [(WALK0, (WX0 + 0.2, YL - 0.2, dz)), (WALK1, (WX1 + 0.2, YL - 0.2, dz))])
# Zzz crossed out
for k, (dx, dz) in enumerate([(0.0, 2.0), (0.14, 2.12), (0.3, 2.26)]):
    z_ = text("Zzz", "z", (WX0 + dx - 0.5, YL - 0.2, dz - 0.15), 0.12 + k * 0.04, white_lab, extrude=0.01)
    key_loc(z_, [(WALK0, (WX0 + dx - 0.7, YL - 0.2, dz - 0.2)), (WALK1, (WX1 + dx - 0.7, YL - 0.2, dz - 0.2))])
    pop(z_, S[13] + 8 + k * 2, 3, S[14])
# year calendar flipping 2026 -> 2030 next to the walker
def calendar(name, top, num, f_in, f_out, keys):
    g = group(name, (0, 0, 0))
    ps = [box(name + "B", (0, 0, 0), (0.5, 0.05, 0.5), white_lab, bevel=0.02), box(name + "T", (0, -0.005, 0.21), (0.5, 0.055, 0.12), red_lab),
          text(name + "Top", top, (0, -0.04, 0.21), 0.08, white_lab, extrude=0.004),
          text(name + "N", num, (0, -0.04, -0.04), 0.2, mat(name + "NM", (0.1, 0.1, 0.12), 0.5), extrude=0.008)]
    attach(ps, g)
    key_loc(g, keys)
    pop(g, f_in, 3, f_out)
    return g
for j, yr in enumerate(range(2026, 2031)):
    f_in = S[14] + 1 + j * 5
    calendar(f"CalY{yr}", "YEAR", str(yr), f_in, f_in + 6 if yr < 2030 else S[15],
             [(WALK0, (WX0 - 0.7, YL - 0.25, 1.15)), (WALK1, (WX1 - 0.7, YL - 0.25, 1.15))])

# =============== lines 15-16: laying one bill per second for 31 years — your hair turns gray ===============
LX0 = -3.4           # a fresh spot on the lawn (left of the long line, in front of the pool)
LAYF = S[15] - 2
you.keyframe_insert("location", frame=LAYF - 1); you.keyframe_insert("rotation_euler", frame=LAYF - 1)
you.location = (LX0, YL + 0.5, 0); you.rotation_euler = (0, 0, 0)
you.keyframe_insert("location", frame=LAYF); you.keyframe_insert("rotation_euler", frame=LAYF)
lay = []
for k in range(10):
    bk = bill(f"LayBill{k}", (LX0 + 0.3 - k * 0.27, YL - 0.05, 0.002), 0.0)
    f_ = S[15] + 2 + k * 6
    pop(bk, f_, 3, s=1.7)
    lay.append(bk)
for f in range(S[15], S[17], 5):   # arm keeps reaching down to place a bill
    arms[0].rotation_euler = (-0.9, 0, -0.3) if (f // 5) % 2 else (0, 0, 0)
    arms[0].keyframe_insert("rotation_euler", frame=f)
# stopwatch ticking above
SWX, SWZ = LX0 + 0.38, 2.0
watch = group("Watch", (SWX, YL - 0.1, SWZ))
wp = [cyl("WatchBody", (SWX, YL - 0.07, SWZ), 0.26, 0.06, mat("WatchM", (0.95, 0.3, 0.2), 0.4), rot=(math.radians(90), 0, 0), verts=40),
      cyl("WatchFace", (SWX, YL - 0.11, SWZ), 0.21, 0.02, white_lab, rot=(math.radians(90), 0, 0), verts=40),
      cyl("WatchBtn", (SWX, YL - 0.07, SWZ + 0.31), 0.05, 0.08, mat("WatchM2", (0.6, 0.6, 0.62), 0.3, metal=0.6))]
for k in range(12):
    a = k / 12 * 6.283
    wp.append(box("WTick", (SWX + 0.17 * math.sin(a), YL - 0.125, SWZ + 0.17 * math.cos(a)), (0.016, 0.01, 0.04), eyeb, rot=(0, a, 0)))
attach(wp, watch)
hand = group("WHand", (SWX, YL - 0.13, SWZ))
attach([box("WHandB", (SWX, YL - 0.13, SWZ + 0.08), (0.02, 0.01, 0.16), red_lab)], hand)
pop(watch, S[15], 5, S[17]); pop(hand, S[15], 5, S[17])
for j, f in enumerate(range(S[15], S[17], 5)):
    hand.rotation_euler = (0, j * 6.283 / 12, 0); hand.keyframe_insert("rotation_euler", frame=f)
    hand.rotation_euler = (0, (j + 1) * 6.283 / 12, 0); hand.keyframe_insert("rotation_euler", frame=f + 1)
label("L1s", "1 BILL / SECOND", (LX0 - 0.5, YL - 0.3, 2.05), 0.13, white_lab, S[15] + 3, S[16])
label("L31", "31 YEARS", (LX0 - 0.2, YL - 0.3, 2.75), 0.2, lab_m, S[16] + 2, S[17])
for j, yr in enumerate([2026, 2036, 2046, 2057]):
    f_in = S[16] + 1 + j * 7
    calendar(f"CalL{yr}", "YEAR", str(yr), f_in, f_in + 8 if yr < 2057 else S[17] + 4,
             [(0, (LX0 - 0.75, YL - 0.25, 1.2))])
# hair goes gray, a white beard grows
hb = hair_m.node_tree.nodes["Principled BSDF"].inputs["Base Color"]
for f, c in [(0, (0.28, 0.16, 0.07, 1)), (S[16] + 4, (0.28, 0.16, 0.07, 1)), (S[16] + 22, (0.88, 0.88, 0.9, 1))]:
    hb.default_value = c; hb.keyframe_insert("default_value", frame=f)
hide_until(beard, S[16] + 8)
keyscale(beard, [(S[16] + 8, (0.2, 0.14, 0.15)), (S[16] + 22, (1.0, 0.7, 0.75))])
label("LGray", "GRAY!", (LX0 - 0.55, YL - 0.3, 1.78), 0.15, white_lab, S[16] + 18, S[17] + 2)

# ---------------- line 17: the question ----------------
q = text("Q", "?", (LX0 - 0.1, YL - 0.3, 2.9), 1.5, lab_m, extrude=0.06)
pop(q, S[17] + 2, 6)
keyrot(q, [(S[17] + 2, (math.radians(90), 0, 0)), (FRAMES, (math.radians(90), 0, math.radians(360)))])

# ---------------- camera ----------------
bpy.ops.object.camera_add()
cam = bpy.context.object
sc.camera = cam
cam.data.lens = 26
cam.data.sensor_fit = 'VERTICAL'
cam.data.sensor_height = 36
cam.data.clip_start = 0.05
cam.data.clip_end = 3.0e6
target = bpy.data.objects.new("Target", None); sc.collection.objects.link(target)
tr = cam.constraints.new('TRACK_TO'); tr.target = target
tr.track_axis = 'TRACK_NEGATIVE_Z'; tr.up_axis = 'UP_Y'
B1 = (XS + 0.08, YL, 0.0)
ROW = (XS + 0.78, YL + 0.1, 0.1)
E = tuple(SP)
def sp(v):
    return tuple(SP + Vector(v))
WM = lambda f: WX0 + (WX1 - WX0) * (f - WALK0) / (WALK1 - WALK0)
cam_keys = [
    (0,          (1.6, -3.4, 1.6),   (0.5, 0.0, 0.6)),                 # hook: you + raining cash
    (S[1] - 4,   (0.4, -3.0, 1.5),   (0.4, 0.0, 0.6)),
    (S[1] + 2,   (1.9, -2.1, 1.2),   (XS + 0.35, YL, 0.3)),            # one bill falls
    (S[2] - 2,   (1.5, -1.5, 0.7),   B1),
    (S[2] + 2,   (-0.3, -1.05, 0.5), B1),                              # 15.6 cm ruler
    (S[3] - 2,   (-0.25, -1.35, 0.6), B1),
    (S[3] + 2,   (0.3, -2.6, 1.1),   ROW),                              # ten bills = you
    (S[4] - 2,   (1.3, -2.9, 1.2),   ROW),
    (S[4] + 2,   (3.0, -6.0, 4.0),  (8.0, YL, 0.0)),                  # 156 m line across the lawn
    (S[4] + 22,  CAM4,               (85.0, YL, 0.0)),
    (S[5] - 2,   (26.0, -52.0, 37.0), (88.0, YL, 0.0)),
    (S[5] + 2,   (-200.0, -450.0, 400.0), (2000.0, YL, 0.0)),           # 156 km, plane-high
    (S[5] + 22,  CAM5,                (60000.0, YL, 0.0)),
    (S[7] - 6,   (CAM5[0] - 150, CAM5[1] - 120, CAM5[2] + 60), (75000.0, YL, 0.0)),
    (S[7] - 2,   (3.0, -19.0, 15.0), (8.0, 3.0, 2.0)),               # the billion cube slams down
    (S[7] + 10,  CAM7,                 (8.0, 3.0, 2.0)),
    (S[8] - 2,   (7.0, -14.0, 12.0),  (8.0, 3.0, 2.0)),
    (S[8] - 1,   sp((-3.0, -20.0, 6.0)), E),                               # space: 156,000 km
    (S[8] + 14,  sp((-1.0, -13.0, 4.5)), E),
    (S[10] - 2,  sp((1.5, -12.5, 4.0)), E),                                # wraps around
    (S[11] - 4,  sp((3.0, -12.0, 3.0)), E),                                # almost four times
    (S[11] + 2,  sp((6.0, -34.0, 11.0)), sp((3.0, 5.0, 4.2))),             # aim at the Moon
    (S[13] - 4,  sp((13.0, -42.0, 14.0)), sp((3.5, 5.5, 1.7))),
    (WALK0,      (WX0 + 1.6, YL - 3.2, 1.5), (WX0, YL + 0.3, 0.9)),         # walking it nonstop
    (S[14],      (WM(S[14]) + 1.7, YL - 3.0, 1.5), (WM(S[14]), YL + 0.3, 0.9)),
    (WALK1 - 2,  (WX1 + 0.8, YL - 3.1, 1.6), (WX1 - 0.4, YL + 0.3, 0.9)),
    (LAYF + 1,   (LX0 + 0.1, YL - 2.3, 1.3), (LX0 - 0.45, YL, 0.3)),   # one bill per second
    (S[16] - 2,  (LX0 - 0.5, YL - 2.2, 1.3), (LX0 - 0.6, YL, 0.3)),
    (S[16] + 2,  (LX0 + 0.3, YL - 2.0, 1.5), (LX0 - 0.2, YL + 0.4, 1.1)),   # 31 years, gray
    (S[17] - 2,  (LX0 - 0.3, YL - 1.9, 1.5), (LX0 - 0.2, YL + 0.4, 1.1)),
    (S[17] + 4,  (LX0 + 1.2, YL - 3.6, 2.0), (LX0 + 0.3, YL + 0.3, 1.0)),   # question
    (FRAMES - 1, (LX0 + 1.9, YL - 4.4, 2.4), (LX0 + 0.6, YL + 0.3, 1.0)),
]
def overhead(cl, tl):
    dx, dy = cl[0] - tl[0], cl[1] - tl[1]
    hd = math.hypot(dx, dy)
    if cl[2] > 60 or hd > 40 or cl[0] < -5e5:
        return cl
    z = max(cl[2], tl[2] + 0.62 * hd)
    return (cl[0], cl[1], z)
LIFT = math.atan(0.36 * math.tan(math.atan(18 / 26)))   # subject ~68% down the frame
def aim(cl, subj):
    d = Vector(subj) - Vector(cl)
    ax = d.cross(Vector((0, 0, 1))).normalized()
    return tuple(Vector(cl) + Quaternion(ax, LIFT) @ d)
cam_keys = [(f, overhead(cl, tl), tl) for f, cl, tl in cam_keys]
for f, cl, tl in cam_keys:
    cam.location = cl; cam.keyframe_insert("location", frame=f)
    target.location = aim(cl, tl); target.keyframe_insert("location", frame=f)
# hard cuts (no fly-through) into and out of space and between far-apart shots
def fcurves(o_):
    ad = o_.animation_data
    if ad is None or ad.action is None:
        return []
    try:
        return list(ad.action.fcurves)
    except AttributeError:
        from bpy_extras import anim_utils
        return list(anim_utils.action_get_channelbag_for_slot(ad.action, ad.action_slot).fcurves)
for o_ in (cam, target):
    for fc in fcurves(o_):
        pts = fc.keyframe_points
        for i in range(len(pts) - 1):
            if int(round(pts[i + 1].co[0])) in (S[7] - 2, S[8] - 1, WALK0, LAYF + 1):
                pts[i].interpolation = 'CONSTANT'

for o_ in [you] + walk_labels + [o for o in bpy.data.objects if o.name.startswith(("Zzz", "CalY"))]:
    for fc in fcurves(o_):
        if fc.data_path != "location":
            continue
        for kp in fc.keyframe_points:
            if WALK0 - 1 <= kp.co[0] < WALK1:
                kp.interpolation = 'LINEAR'
for o in bpy.data.objects:
    if o.type == 'FONT' or o.matrix_world.translation.x < -5e5:
        o.visible_shadow = False
sc.frame_set(0)
bpy.ops.wm.save_as_mainfile(filepath=f"{HERE}/scene.blend")
print("SCENE OK", FRAMES, S)
