# Day 21 — What if a billion dollars was pure gold?  Build: python3 episodes/021-billion-gold/scene.py
# Reference style: base (helpers, lawn/soil, house, garden) copied from episodes/003-lift-million-ref / 006-mantis-punch
import bpy, math, random, os, json
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
random.seed(21)
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
# Day 21 — What if a billion dollars was pure gold?
# Facts used (checked 2026-11-15): spot gold ~$3,884/oz (Fortune, Nov 13 2026) -> "about $3,900 an ounce".
#   1 troy oz = 31.1 g -> ~$125/g -> $1e9 = ~8.0 t of gold.
#   $1B in $100 bills = 10 million x ~1 g = 10 t (~11 m3)  -> the gold is LIGHTER than the cash.
#   Gold density 19.3 g/cm3 (19.3x water) -> 8.0 t = 0.415 m3 = cube ~0.75 m per side.
#   London Good Delivery bar ~400 oz = 12.4 kg (~$1.55M) -> ~640 bars.
#   Adult African elephant ~4-7 t -> 8 t is heavier.  8 t on 0.56 m2 ~ 140 kPa -> pavers can crack.
#   Fort Knox ~147 million oz (~4,580 t) -> ~570x.  All gold ever mined ~216,000 t -> 11,200 m3 = 22.4 m cube.
# =====================================================================================
gold_m = mat("Gold", (1.0, 0.7, 0.16), 0.28, emit=(1.0, 0.68, 0.12), emit_strength=0.35, metal=1.0)
gold_dark = mat("GoldD", (0.85, 0.55, 0.1), 0.35, emit=(0.8, 0.5, 0.08), emit_strength=0.25, metal=1.0)
water_m = mat("WaterB", (0.3, 0.65, 1.0), 0.08, emit=(0.2, 0.55, 1.0), emit_strength=0.5)
bill_m = mat("Bill", (0.3, 0.68, 0.25), 0.8)
band_m = mat("Band", (0.95, 0.75, 0.3), 0.6)
cash_m = stripe_mat("Cash", (0.3, 0.68, 0.25), (0.18, 0.48, 0.15), axis="Z", freq=40.0, thresh=0.3)
tag_m = mat("Tag", (1.0, 0.82, 0.15), 0.5)
red_m = mat("RedM", (0.9, 0.12, 0.1), 0.5)
white_m = mat("WhiteM", (0.97, 0.97, 0.95), 0.5)
dark_m = mat("DarkM", (0.08, 0.08, 0.1), 0.5)
iron_m = mat("Iron", (0.22, 0.23, 0.26), 0.5, metal=0.6)
wood_m = mat("Wood", (0.6, 0.42, 0.24), 0.8)
ele_m = mat("Ele", (0.55, 0.57, 0.62), 0.8)
ele_in = mat("EleIn", (0.9, 0.6, 0.65), 0.7)
dust_m = mat("Dust", (0.85, 0.8, 0.7), 0.95)
crack_m = mat("Crack", (0.05, 0.04, 0.03), 0.9)
sweat_m = mat("Sweat", (0.5, 0.8, 1.0), 0.1, emit=(0.4, 0.7, 1.0), emit_strength=0.6)

def show(o, wins, s=1.0):
    """visible (popped) only inside the given (f_in, f_out) windows"""
    keys = [(0, 0.001)]
    for a, b in wins:
        keys += [(a - 1, 0.001), (a + 3, 1.15 * s), (a + 5, s), (b - 1, s), (b, 0.001)]
    keyscale(o, keys)

def gold_cube(name, loc, size, wins, bevel=0.015):
    g = group(name, loc)
    c = box(name + "C", (loc[0], loc[1], loc[2] + size / 2), (size, size, size), gold_m, bevel=bevel * size / 0.75)
    attach([c], g); show(g, wins); return g

def gbar(name, loc, k=1.0, m_=None):
    return box(name, loc, (0.3 * k, 0.14 * k, 0.1 * k), m_ or gold_m, bevel=0.02 * k)

def sparkle(loc, f0, f1, n=6, r=0.6):
    for k in range(n):
        a = random.uniform(0, 6.28); z = random.uniform(0.1, r * 1.4)
        s_ = sphere("Spk", (loc[0] + r * math.cos(a), loc[1] - abs(r * math.sin(a)) - 0.1, loc[2] + z), 0.035, spark_m, sub=1)
        st = f0 + random.randint(0, max(1, (f1 - f0) - 8))
        pop(s_, st, 3, st + 7)

# ---------------- YOU ----------------
YX, YY = 0.0, 0.5
you, yd = person("You", (YX, YY, 0), 1.0, mat("YouShirt", (0.95, 0.3, 0.35), 0.7), mat("YouPants", (0.18, 0.22, 0.38), 0.8),
                 skin_m, mat("YouHair", (0.25, 0.14, 0.06), 0.8))
armL, armR = yd["arms"]
def arms_up(fs):
    for f, up in fs:
        a = math.radians(150) * up
        keyrot(armL, [(f, (0, a, 0))]); keyrot(armR, [(f, (0, -a, 0))])
arms_up([(0, 0), (S[0] + 6, 1), (E(0) - 2, 1), (S[1], 0), (S[8], 0), (S[8] + 4, 0.35), (E(8) - 1, 0.35), (E(8), 0),
         (S[10], 0), (S[10] + 5, 1), (E(10) - 1, 1), (E(10), 0), (S[15], 0), (S[15] + 4, 0.5)])
# you sit out the seesaw / patio / far shots
keyscale(you, [(0, 1.0), (S[4] - 1, 1.0), (S[4], 0.001), (E(4) - 1, 0.001), (E(4), 1.0),
               (S[11] - 1, 1.0), (S[11], 0.001), (E(14) - 1, 0.001), (E(14), 1.0)])

# line 0: gold bars rain around you
for k in range(36):
    p = (YX + random.uniform(-2.4, 2.4), YY + random.uniform(-0.8, 1.6), random.uniform(2.2, 5.5))
    b = gbar("RainBar", p, 1.4)
    st = random.randint(0, 14); zend = random.uniform(0.07, 0.15)
    b.rotation_euler = (random.uniform(-1, 1), random.uniform(-1, 1), random.uniform(0, 6)); b.keyframe_insert("rotation_euler", frame=st)
    b.rotation_euler = (0, 0, random.uniform(0, 6)); b.keyframe_insert("rotation_euler", frame=st + 12)
    key_loc(b, [(st, p), (st + 12, (p[0], p[1], zend))])
    hide_until(b, st); gone_at(b, S[1] + 2, 3)
sparkle((YX, YY, 0.2), 4, S[1], n=10, r=1.8)

# ---------------- line 1: one ounce coin + $3,900 tag ----------------
CX_, CY_ = 1.3, 0.8
coin_g = group("CoinG", (CX_, CY_, 0.75))
attach([cyl("Coin", (CX_, CY_, 0.75), 0.55, 0.12, gold_m, rot=(math.radians(90), 0, 0), verts=40),
        cyl("CoinRim", (CX_, CY_, 0.75), 0.46, 0.14, gold_dark, rot=(math.radians(90), 0, 0), verts=40),
        text("CoinT", "1 OZ", (CX_, CY_ - 0.08, 0.75), 0.28, dark_m)], coin_g)
show(coin_g, [(S[1], E(1))])
keyrot(coin_g, [(S[1], (0, 0, -1.2)), (S[1] + 10, (0, 0, 0.15)), (E(1), (0, 0, -0.1))])
tg = group("TagG", (CX_ + 0.9, CY_ - 0.4, 1.25))
attach([box("TagCard", (CX_ + 0.9, CY_ - 0.4, 1.25), (1.1, 0.04, 0.5), tag_m, bevel=0.03),
        text("TagT", "$3,900", (CX_ + 0.9, CY_ - 0.43, 1.25), 0.28, dark_m)], tg)
show(tg, [(W(1, 0.4), E(1))])
keyrot(tg, [(W(1, 0.4), (0, 0, -0.3)), (W(1, 0.4) + 8, (0, 0, 0.2)), (E(1), (0, 0, -0.05))])
sparkle((CX_, CY_, 0.3), S[1], E(1), n=6, r=0.7)

# ---------------- line 2: an "8 T" weight slams down ----------------
WX, WY = 1.3, 1.0
wg = group("WeightG", (WX, WY, 0))
wparts = [cyl("Wt", (WX, WY, 0.6), 0.95, 1.2, iron_m, r2=0.65, verts=4, rot=(0, 0, math.radians(45))),
          tube("WtH", [(WX - 0.35, WY, 1.2), (WX - 0.35, WY, 1.6), (WX + 0.35, WY, 1.6), (WX + 0.35, WY, 1.2)], [0.08] * 4, iron_m),
          text("WtT", "8 T", (WX, WY - 0.83, 0.55), 0.45, white_lab, rot=(math.radians(90) - 0.28, 0, 0))]
attach(wparts, wg)
fd = S[2] + 7
keyscale(wg, [(0, 0.001), (S[2] - 1, 0.001), (S[2], 1.0), (fd, 1.0), (fd + 2, (1.18, 1.18, 0.78)), (fd + 5, 1.0), (E(2) - 1, 1.0), (E(2), 0.001)])
key_loc(wg, [(S[2], (WX, WY, 7.0)), (fd, (WX, WY, 0.0))])
for k in range(10):
    a = k / 10 * 6.283
    d_ = sphere("Dust", (WX + 1.0 * math.cos(a), WY + 0.6 * math.sin(a), 0.15), 0.22, dust_m, sub=1)
    key_loc(d_, [(fd, (WX + 1.0 * math.cos(a), WY + 0.6 * math.sin(a), 0.15)), (fd + 12, (WX + 1.9 * math.cos(a), WY + 1.2 * math.sin(a), 0.4))])
    pop(d_, fd, 3, fd + 13)

# ---------------- line 3 (+15): $1B in $100 bills = 10 t cash cube ----------------
CBX, CBY = -2.4, 1.6
def cash_cube(name, x, y, z=0.0):
    g = group(name, (x, y, z))
    p_ = [box(name + "C", (x, y, z + 1.22), (2.2, 2.2, 2.2), cash_m, bevel=0.03),
          box(name + "P", (x, y, z + 0.06), (2.4, 2.4, 0.12), wood_m)]
    for dx in (-0.55, 0.55):
        p_.append(box(name + "Bd", (x + dx, y, z + 1.22), (0.22, 2.24, 2.24), band_m))
    p_.append(text(name + "T", "$1B", (x, y - 1.13, z + 1.6), 0.6, white_lab))
    attach(p_, g); return g
cg = cash_cube("CashG", CBX, CBY)
show(cg, [(S[3], E(3)), (S[15], FRAMES + 5)])
for k in range(14):
    b = box("Puff", (CBX + random.uniform(-1, 1), CBY - 1.2, random.uniform(0.3, 2.2)), (0.31, 0.13, 0.006), bill_m)
    b.rotation_euler = (random.uniform(0, 3), random.uniform(0, 3), random.uniform(0, 3))
    key_loc(b, [(S[3] + 3, tuple(b.location)), (S[3] + 16, (b.location.x + random.uniform(-1.5, 1.5), b.location.y - random.uniform(0.5, 1.5), b.location.z + random.uniform(0.5, 1.5)))])
    pop(b, S[3] + 3, 3, S[3] + 18)

# ---------------- lines 4 + 11: seesaw (cash vs gold, then elephant vs gold) ----------------
SX, SY, PH = 0.6, 5.0, 1.0
base = cyl("Pivot", (SX, SY, PH / 2), 0.7, PH, red_m, r2=0.08, verts=3, rot=(math.radians(90), 0, 0))
base.location = (SX, SY + 0.5, PH / 2)
base.rotation_euler = (math.radians(90), 0, 0)
piv = group("SeeG", (SX, SY, PH))
plank = box("Plank", (SX, SY, PH + 0.08), (6.6, 1.4, 0.16), wood_m, bevel=0.03)
s_gold = box("SeeGold", (SX + 2.7, SY, PH + 0.16 + 0.375), (0.75, 0.75, 0.75), gold_m, bevel=0.015)
s_cash = cash_cube("SeeCash", SX - 2.0, SY, PH + 0.04)
# cartoon elephant (sideways, trunk to the left)
EX, EZ = SX - 1.5, PH + 0.16
eg = group("EleG", (EX, SY, EZ))
ep = [sphere("EBody", (EX, SY, EZ + 1.25), 1.0, ele_m, scale=(1.35, 0.85, 0.85), sub=3),
      sphere("EHead", (EX - 1.35, SY - 0.05, EZ + 1.6), 0.62, ele_m, sub=3),
      tube("ETrunk", [(EX - 1.85, SY - 0.1, EZ + 1.55), (EX - 2.15, SY - 0.15, EZ + 1.05), (EX - 2.2, SY - 0.2, EZ + 0.6), (EX - 2.4, SY - 0.2, EZ + 0.5)],
           [0.2, 0.16, 0.12, 0.1], ele_m),
      sphere("EEar", (EX - 1.0, SY - 0.45, EZ + 1.7), 0.5, ele_m, scale=(0.5, 0.15, 0.9), sub=2),
      sphere("EEarIn", (EX - 1.0, SY - 0.5, EZ + 1.7), 0.38, ele_in, scale=(0.5, 0.12, 0.85), sub=2),
      sphere("EEyeW", (EX - 1.6, SY - 0.5, EZ + 1.8), 0.11, eyew, sub=2),
      sphere("EEyeB", (EX - 1.62, SY - 0.6, EZ + 1.8), 0.055, eyeb, sub=1),
      cyl("ETusk", (EX - 1.75, SY - 0.35, EZ + 1.2), 0.06, 0.4, white_m, r2=0.02, rot=(0, math.radians(-120), 0), verts=8),
      tube("ETail", [(EX + 1.3, SY, EZ + 1.4), (EX + 1.55, SY, EZ + 1.0)], [0.05, 0.03], ele_m)]
for lx in (-0.75, 0.75):
    for ly in (-0.4, 0.4):
        ep.append(cyl("ELeg", (EX + lx, SY + ly, EZ + 0.35), 0.28, 0.7, ele_m, verts=14))
attach(ep, eg)
see_lab = text("SeeT", "8 T", (SX + 2.7, SY - 0.39, PH + 0.6), 0.28, dark_m)
attach([plank, s_gold, s_cash, eg, see_lab], piv)
show(s_cash, [(S[4], E(4))]); show(eg, [(S[11], E(11))])
for o_ in (piv, base):
    show(o_, [(S[4], E(4)), (S[11], E(11))])
T4 = -0.2; T11 = 0.2
keyrot(piv, [(S[4], (0, 0, 0)), (S[4] + 6, (0, T4 * 1.25, 0)), (S[4] + 10, (0, T4 * 0.85, 0)), (S[4] + 13, (0, T4, 0)), (E(4), (0, T4, 0)),
             (S[11] - 1, (0, T4, 0)), (S[11], (0, -0.08, 0)), (S[11] + 9, (0, T11 * 1.25, 0)), (S[11] + 13, (0, T11 * 0.85, 0)), (S[11] + 16, (0, T11, 0))])
# elephant surprised: little hop
key_loc(eg, [(S[11] + 9, (EX, SY, EZ)), (S[11] + 13, (EX, SY, EZ + 0.4)), (S[11] + 17, (EX, SY, EZ))])

# ---------------- lines 5-8: THE cube next to you ----------------
GX, GY = 1.2, 0.5
gc = gold_cube("GoldCube", (GX, GY, 0), 0.75, [(S[5], S[9] + 6), (S[13], E(13)), (S[15], FRAMES + 5)])
sparkle((GX, GY, 0.1), S[6], E(6), n=12, r=0.75)
sparkle((GX, GY, 0.1), S[15], FRAMES - 2, n=8, r=0.75)
# line 5: 19 water cubes of the same size stack up
WBX, WBY = 3.0, 1.4
wcount = 0
for lz in range(3):
    for ix in range(3):
        for iy in range(3):
            if wcount >= 19 or (lz == 2 and (ix, iy) != (1, 1)):
                continue
            o_ = box("WaterBlk", (WBX + (ix - 1) * 0.78, WBY + (iy - 1) * 0.78, 0.375 + lz * 0.78), (0.74, 0.74, 0.74), water_m, bevel=0.04)
            f0 = S[5] + 3 + wcount * 1.6
            pop(o_, int(f0), 4, E(5))
            wcount += 1
wl = text("WaterT", "x19", (WBX, WBY - 1.5, 3.0), 0.5, blue_lab, extrude=0.04)
pop(wl, W(5, 0.5), 4, E(5))
gl = text("GoldEq", "=", (GX + 0.95, GY - 0.6, 0.45), 0.6, white_lab, extrude=0.04)
pop(gl, W(5, 0.4), 4, E(5))
# line 7: dimension arrows 75 cm
def arrow(name, a, b, f0, f1, m_=lab_m):
    t_ = tube(name, [a, b], [0.025, 0.025], m_)
    va = Vector(b) - Vector(a)
    for end, dirv in ((a, -va), (b, va)):
        c_ = cyl(name + "H", end, 0.07, 0.16, m_, r2=0.0, verts=10)
        c_.rotation_mode = 'QUATERNION'; c_.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(dirv.normalized())
        pop(c_, f0, 4, f1)
    pop(t_, f0, 4, f1)
h_ = 0.375
arrow("DimX", (GX - h_, GY - h_ - 0.18, 0.02), (GX + h_, GY - h_ - 0.18, 0.02), S[7] + 2, E(7))
arrow("DimZ", (GX + h_ + 0.18, GY - h_, 0.0), (GX + h_ + 0.18, GY - h_, 0.75), S[7] + 6, E(7))
arrow("DimY", (GX + h_ + 0.18, GY - h_, 0.0), (GX + h_ + 0.18, GY + h_, 0.0), S[7] + 10, E(7))
# line 8: waist line marker
wline = box("WaistLine", (GX * 0.5, GY - 0.45, 0.76), (2.4, 0.02, 0.025), lab_m)
pop(wline, S[8] + 3, 4, E(8))

# ---------------- lines 9-10: melted into ~640 big bars ----------------
BX0, BY0 = 1.9, 1.0
bproto = gbar("BarProto", (0, 0, 0), 1.0)
bproto.modifiers.clear()
bproto.location = (0, -100, -50)
for lz in range(10):
    lg_ = group(f"BarLayer{lz}", (BX0, BY0, 0))
    objs = []
    for ix in range(8):
        for iy in range(8):
            o_ = bpy.data.objects.new(f"Bar{lz}_{ix}_{iy}", bproto.data); sc.collection.objects.link(o_)
            o_.location = (BX0 + (ix - 3.5) * 0.31, BY0 + (iy - 3.5) * 0.145, 0.05 + lz * 0.102)
            if lz % 2:
                o_.location.x += 0.07
            objs.append(o_)
    attach(objs, lg_)
    f0 = S[9] + 4 + lz * 3
    key_loc(lg_, [(f0, (BX0, BY0, 2.5)), (f0 + 4, (BX0, BY0, 0.0))])
    keyscale(lg_, [(0, 0.001), (f0 - 1, 0.001), (f0, 1.0), (E(10) - 1, 1.0), (E(10), 0.001)])
sparkle((BX0, BY0 - 0.4, 0.2), S[9] + 30, E(9), n=8, r=1.3)
# melting glow on the cube as it disappears
glow_c = sphere("MeltGlow", (GX, GY, 0.35), 0.55, glow_mat("MeltM", (1.0, 0.55, 0.1), 3.0), sub=2)
pop(glow_c, S[9], 3, S[9] + 9)
# line 10: you lift ONE bar overhead (sweating)
hb = gbar("HeroBar", (YX, YY - 0.05, 1.92), 1.7)
keyscale(hb, [(0, 0.001), (S[10] - 1, 0.001), (S[10] + 4, 1.0), (E(10) - 1, 1.0), (E(10), 0.001)])
key_loc(hb, [(S[10], (YX, YY - 0.2, 0.9)), (S[10] + 5, (YX, YY - 0.05, 1.92))])
for k in range(3):
    sw = sphere("Sweat", (YX + 0.22 * (k - 1) + 0.1, YY - 0.25, 1.85), 0.04, sweat_m, scale=(1, 1, 1.5), sub=1)
    key_loc(sw, [(S[10] + 8 + 5 * k, (YX + 0.25 * (k - 1), YY - 0.25, 1.85)), (S[10] + 18 + 5 * k, (YX + 0.35 * (k - 1), YY - 0.3, 1.45))])
    pop(sw, S[10] + 8 + 5 * k, 2, S[10] + 19 + 5 * k)

# ---------------- line 12: cube drops onto the patio -> cracks ----------------
PTX, PTY = 1.6, fy - 1.3
pc = group("PatioCube", (PTX, PTY, 0.08))
attach([box("PatioCubeC", (PTX, PTY, 0.08 + 0.375), (0.75, 0.75, 0.75), gold_m, bevel=0.015)], pc)
fh = W(12, 0.22)
keyscale(pc, [(0, 0.001), (S[12] - 1, 0.001), (S[12], 1.0), (fh, 1.0), (fh + 2, (1.15, 1.15, 0.82)), (fh + 5, 1.0), (E(12) - 1, 1.0), (E(12), 0.001)])
key_loc(pc, [(S[12], (PTX, PTY, 6.0)), (fh, (PTX, PTY, 0.08)), (fh + 4, (PTX, PTY, 0.02))])
for k in range(11):
    a = k / 11 * 6.283 + random.uniform(-0.2, 0.2)
    Lc = random.uniform(0.7, 1.5)
    cx_, cy_ = PTX + (0.38 + Lc / 2) * math.cos(a), PTY + (0.38 + Lc / 2) * math.sin(a)
    cr_ = box("CrackL", (cx_, cy_, 0.085), (Lc, 0.05, 0.012), crack_m, rot=(0, 0, a))
    hide_until(cr_, fh + 1 + (k % 3)); gone_at(cr_, E(12), 1)
for k in range(12):
    a = random.uniform(0, 6.283)
    ch = box("Chip", (PTX, PTY, 0.1), (0.16, 0.12, 0.06), stone_p, rot=(random.uniform(0, 3), random.uniform(0, 3), 0))
    p0 = (PTX + 0.45 * math.cos(a), PTY + 0.45 * math.sin(a), 0.1)
    key_loc(ch, [(fh, p0), (fh + 6, (p0[0] + 0.7 * math.cos(a), p0[1] + 0.7 * math.sin(a), 0.9)), (fh + 13, (p0[0] + 1.3 * math.cos(a), p0[1] + 1.3 * math.sin(a), 0.1))])
    pop(ch, fh, 2, E(12))
for k in range(10):
    a = k / 10 * 6.283
    d_ = sphere("Dust2", (PTX + 0.5 * math.cos(a), PTY + 0.5 * math.sin(a), 0.2), 0.2, dust_m, sub=1)
    key_loc(d_, [(fh, (PTX + 0.5 * math.cos(a), PTY + 0.5 * math.sin(a), 0.2)), (fh + 12, (PTX + 1.4 * math.cos(a), PTY + 1.4 * math.sin(a), 0.6))])
    pop(d_, fh, 3, fh + 13)

# ---------------- line 13: Fort Knox holds ~570x -> a 6.2 m cube behind yours ----------------
FKX, FKY = 5.6, 5.6
fk = gold_cube("FortKnoxCube", (FKX, FKY, 0), 6.2, [(S[13] + 2, E(13))])
keyscale(fk, [(0, 0.001), (S[13] + 1, 0.001), (S[13] + 2, (1, 1, 0.03)), (S[13] + 12, (1, 1, 1.05)), (S[13] + 15, 1.0), (E(13) - 1, 1.0), (E(13), 0.001)])
sparkle((FKX, FKY - 2.6, 0.5), S[13] + 12, E(13), n=10, r=3.0)

# ---------------- line 14: all gold ever mined -> a 22.4 m cube next to the house ----------------
AGX, AGY = 20.0, 17.0
ag = gold_cube("AllGoldCube", (AGX, AGY, 0), 22.4, [(S[14], E(14))], bevel=0.004)
keyscale(ag, [(0, 0.001), (S[14] - 1, 0.001), (S[14], (1, 1, 0.02)), (S[14] + 16, (1, 1, 1.04)), (S[14] + 19, 1.0), (E(14) - 1, 1.0), (E(14), 0.001)])
mini_c = gold_cube("TinyCube", (AGX - 13.0, 3.0, 0), 0.75, [(S[14], E(14))])
mini_lab = text("TinyT", "YOURS", (AGX - 13.0, 2.4, 1.6), 0.5, white_lab, extrude=0.04)
pop(mini_lab, S[14] + 8, 4, E(14))
arr = tube("TinyArrow", [(AGX - 13.0, 2.6, 1.3), (AGX - 13.0, 2.6, 0.95)], [0.06, 0.06], lab_m)
pop(arr, S[14] + 8, 4, E(14))

# line 15: question marks above cash and gold
for k, qx in enumerate([CBX, GX]):
    q = text(f"Q{k}", "?", (qx, 1.0, 3.0 if k == 0 else 1.6), 1.0 if k == 0 else 0.7, lab_m, extrude=0.08)
    pop(q, S[15] + 6 + 4 * k, 5)
    keyrot(q, [(S[15] + 6, (math.radians(90), 0, -0.2)), (FRAMES - 1, (math.radians(90), 0, 0.2))])

# ---------------- views (camera, subject) per line; subject sits in the lower third ----------------
V = {}; V2 = {}
V[0] = ((1.2, -5.0, 1.9), (YX, YY, 0.95))
V[1] = ((3.0, -4.4, 2.0), (CX_ - 0.1, CY_, 0.8))
V[2] = ((3.6, -6.0, 2.4), (WX, WY, 0.7));                    V2[2] = ((1.6, -7.0, 2.8), (WX, WY, 0.7))
V[3] = ((-0.2, -5.6, 2.0), (CBX + 0.6, CBY, 1.1))
V[4] = ((1.6, -3.4, 2.4), (SX, SY, 1.1));                    V2[4] = ((-0.6, -3.8, 2.6), (SX, SY, 1.1))
V[5] = ((3.2, -5.4, 2.2), (2.2, 0.9, 0.8));                  V2[5] = ((1.2, -5.9, 2.5), (2.2, 0.9, 0.8))
V[6] = ((2.8, -3.6, 1.6), (GX, GY, 0.4));                    V2[6] = ((1.6, -2.4, 1.2), (GX, GY, 0.4))
V[7] = ((0.0, -3.0, 1.6), (GX, GY, 0.35));                   V2[7] = ((1.8, -3.0, 1.7), (GX, GY, 0.35))
V[8] = ((1.4, -4.6, 1.6), (0.6, YY, 0.85))
V[9] = ((3.8, -5.0, 2.4), (1.6, 1.0, 0.5));                  V2[9] = ((0.4, -5.6, 2.6), (1.6, 1.0, 0.5))
V[10] = ((-1.0, -4.6, 1.8), (0.4, YY, 1.25))
V[11] = ((-0.8, -3.6, 2.4), (SX - 0.4, SY, 1.3));            V2[11] = ((1.4, -4.0, 2.7), (SX - 0.4, SY, 1.3))
V[12] = ((2.8, fy - 8.6, 2.6), (PTX, PTY, 0.3));             V2[12] = ((1.0, fy - 8.9, 2.8), (PTX, PTY, 0.3))
V[13] = ((-3.4, -11.0, 3.5), (3.4, 3.4, 1.6));               V2[13] = ((0.6, -13.0, 4.5), (3.6, 3.6, 2.0))
V[14] = ((-4.0, -32.0, 12.0), (13.0, 15.0, 8.0));            V2[14] = ((-12.0, -42.0, 16.0), (13.0, 15.0, 9.0))
V[15] = ((0.0, -7.6, 2.4), (-0.7, 1.0, 1.0));                V2[15] = ((-1.2, -7.0, 2.4), (-0.7, 1.0, 1.0))
DR = {0: (-0.5, 0.8, 0), 1: (-0.6, 0.6, 0), 3: (0.8, 0.5, 0), 8: (-0.6, 0.6, 0), 10: (0.7, 0.6, 0)}

def LB(i, name, body, m_, size=None, f_in=None, f_out=None, Dk=0.55, end=False, v=0.3, u=0.0):
    view = V2[i] if end else V[i]
    cl = Vector(CL(view)); D = (Vector(view[1]) - cl).length * Dk
    s_ = 0.85 * fit(body, D, size if size else 1e9)
    return label(name, body, view, D, v, s_, m_, (S[i] + 3) if f_in is None else f_in,
                 E(i) if f_out is None else f_out, u)
LB(0, "L0", "$1,000,000,000", lab_m)
LB(1, "L1", "1 OZ = $3,900", lab_m, f_in=W(1, 0.3))
LB(2, "L2", "8 TONS", lab_m, end=True, f_in=S[2] + 8)
LB(3, "L3", "CASH: 10 TONS", green_lab)
LB(4, "L4", "GOLD IS LIGHTER!", lab_m, end=True, f_in=S[4] + 8)
LB(5, "L5", "19x WATER", blue_lab, end=True)
LB(6, "L6", "ALL OF IT!", lab_m, end=True)
LB(7, "L7", "75 CM", lab_m, end=True, f_in=S[7] + 6)
LB(8, "L8", "WAIST HIGH", white_lab)
LB(9, "L9", "~640 BARS", lab_m, end=True, f_in=W(9, 0.35))
LB(10, "L10", "12.4 KG EACH", white_lab)
LB(11, "L11", "8 T > ELEPHANT", lab_m, end=True, f_in=S[11] + 9)
LB(12, "L12", "CRACK!", red_lab, end=True, f_in=fh + 1, Dk=0.45)
LB(13, "L13", "FORT KNOX: 500x+", lab_m, end=True, f_in=S[13] + 10, Dk=0.4)
LB(14, "L14", "ALL GOLD EVER MINED", lab_m, end=True, f_in=S[14] + 12, Dk=0.4)
LB(15, "L15", "CASH OR GOLD?", lab_m, end=True, f_in=S[15] + 6, Dk=0.45)
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
    f_a = S[i]
    f_b = E(i) - 1
    v = V[i]
    cam_keys.append((f_a, CL(v), v[1]))
    if False:
        cam_keys.append((W(5, 0.55), CL(V2[i]), V2[i][1]))
        c2 = (V2[i][0][0] + 30, V2[i][0][1] - 10, V2[i][0][2])
        cam_keys.append((f_b, c2, V2[i][1]))
    elif i in V2:
        cam_keys.append((f_b, CL(V2[i]), V2[i][1]))
    else:
        d = DR.get(i, (0.3, 0.4, 0))
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
