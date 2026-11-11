# Day 17 — What if a billion dollars was rice?  Build: python3 episodes/017-billion-rice/scene.py
# Reference style: base (helpers, lawn/soil, house, garden) copied from episodes/003-lift-million-ref / 006-mantis-punch
import bpy, math, random, os, json
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
random.seed(17)
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


# =====================================================================================
# Day 13 — What if everyone on Earth got a million dollars?
# Facts used: world population ~8.2-8.3 billion (UN) -> "eight billion"; 8e9 x $1M = $8e15 = 8 quadrillion.
#   US $100 bill ~1 g, 0.11 mm thick, ~1.13 cm3 -> 8e13 bills = 8e10 kg = 80 million t; volume 9e7 m3 = cube ~450 m.
#   Great Pyramid of Giza ~6 million t -> 80 Mt is more than 12 of them (12 x 6.5 = 78 Mt).
#   Stack 8e13 x 0.11 mm = 8.8e9 km; Pluto's farthest distance from the Sun ~7.4e9 km -> "past Pluto".
#   Same goods + far more money -> prices rise (inflation; extreme case = hyperinflation).
#   Zimbabwe issued a 100-trillion-dollar note in 2009. Note shown is generic, no real design.
# =====================================================================================
# =====================================================================================
# Day 17 — What if a billion dollars was rice?
# Facts used (checked 2026-11-11): Asian export rice ~US$480-495/t (Thai/Viet 5% broken, Reuters, Nov 8 2026)
#   -> "about $500 a ton"; $1e9 / ~$490 = ~2.0 million t.
#   $1B in $100 bills = 10 million bills x ~1 g = 10 t (~11 m3, a ~2.2 m cube). 2e6 t / 10 t = 200,000x.
#   One long grain ~20-25 mg -> 2e9 kg / 25 mg = 8e13 = ~80 trillion grains; 8e13 s = ~2.5 million years.
#   Big truck ~25 t -> ~80,000 trucks; x ~14 m each = ~1,100 km.
#   Bulk density ~0.78 t/m3 -> ~2.6 million m3; Olympic pool ~2,500 m3 -> ~1,000 pools.
#   One conical pile at ~30-35 deg repose: h ~95-105 m (~30 stories).
#   World rice consumption ~520-530 Mt/yr = ~1.45 Mt/day -> 2 Mt in ~1.4 days.
#   Rice is the staple food for more than half the world's people.
# =====================================================================================
def E(i):
    return S[i + 1] if i + 1 < len(S) else FRAMES
def W(i, fr):
    return int(S[i] + fr * (E(i) - S[i]))

def rice_mat(name, scale=40.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    N = m.node_tree.nodes; L = m.node_tree.links
    bs = N["Principled BSDF"]; bs.inputs["Roughness"].default_value = 0.55
    tc = N.new("ShaderNodeTexCoord")
    nz = N.new("ShaderNodeTexVoronoi"); nz.inputs["Scale"].default_value = scale
    L.new(tc.outputs["Object"], nz.inputs["Vector"])
    rp = N.new("ShaderNodeValToRGB"); el = rp.color_ramp.elements
    el[0].position = 0.0; el[0].color = (0.78, 0.74, 0.64, 1)
    el[1].position = 0.6; el[1].color = (0.98, 0.97, 0.93, 1)
    L.new(nz.outputs["Distance"], rp.inputs["Fac"]); L.new(rp.outputs["Color"], bs.inputs["Base Color"])
    bp = N.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = 0.6
    L.new(nz.outputs["Distance"], bp.inputs["Height"]); L.new(bp.outputs["Normal"], bs.inputs["Normal"])
    return m
rice_m = rice_mat("Rice", 40.0)
rice_big_m = rice_mat("RiceBig", 0.35)
grain_m = mat("Grain", (0.97, 0.95, 0.88), 0.35, emit=(1, 1, 0.95), emit_strength=0.15)
bill_m = mat("Bill", (0.3, 0.68, 0.25), 0.8)
band_m = mat("Band", (0.95, 0.75, 0.3), 0.6)
cash_m = stripe_mat("Cash", (0.3, 0.68, 0.25), (0.18, 0.48, 0.15), axis="Z", freq=40.0, thresh=0.3)
sack_m = mat("Sack", (0.95, 0.93, 0.86), 0.85)
strap_m = mat("Strap", (0.15, 0.45, 0.85), 0.6)
tag_m = mat("Tag", (1.0, 0.82, 0.15), 0.5)
red_m = mat("RedM", (0.9, 0.12, 0.1), 0.5)
white_m = mat("WhiteM", (0.97, 0.97, 0.95), 0.5)
dark_m = mat("DarkM", (0.08, 0.08, 0.1), 0.5)
road_m = mat("Road", (0.22, 0.22, 0.24), 0.9)
gspark_m = glow_mat("GSpark", (1.0, 1.0, 0.85), 4.0)

def grain(name, loc, k=1.0):
    return sphere(name, loc, 0.1 * k, grain_m, scale=(1.0, 0.42, 0.42), sub=2)

def rain(n, cx, cy, spread, z0, z1, f0, f1, k=1.0, f_gone=None):
    out = []
    for i in range(n):
        p = (cx + random.uniform(-spread, spread), cy + random.uniform(-spread * 0.6, spread * 0.6), random.uniform(z0, z1))
        b = grain("Rain", p, k)
        st = f0 + random.randint(0, max(1, (f1 - f0) // 3))
        zend = max(0.05, p[2] - random.uniform(0.7, 1.0) * z1)
        b.rotation_euler = (random.uniform(-1, 1), random.uniform(-1, 1), random.uniform(0, 6)); b.keyframe_insert("rotation_euler", frame=st)
        b.rotation_euler = (b.rotation_euler[0] + random.uniform(-4, 4), b.rotation_euler[1] + random.uniform(-4, 4), b.rotation_euler[2] + 3)
        b.keyframe_insert("rotation_euler", frame=f1)
        key_loc(b, [(st, p), (f1, (p[0] + random.uniform(-0.3, 0.3), p[1], zend))])
        hide_until(b, st)
        gone_at(b, f_gone or f1 + 2, 3)
        out.append(b)
    return out

def sack(name, x, y, k=1.0, label_on=True):
    g = group(name, (x, y, 0))
    parts = [box(name + "B", (x, y, 0.5 * k), (1.0 * k, 1.0 * k, 1.0 * k), sack_m, bevel=0.12 * k)]
    for sx in (-1, 1):
        parts.append(tube(name + "St", [(x + sx * 0.3 * k, y, 0.98 * k), (x + sx * 0.3 * k, y, 1.25 * k), (x + sx * 0.1 * k, y, 1.25 * k), (x + sx * 0.1 * k, y, 0.98 * k)],
                          [0.035 * k] * 4, strap_m))
    parts.append(box(name + "Bd", (x, y - 0.505 * k, 0.5 * k), (1.0 * k, 0.02 * k, 0.12 * k), strap_m))
    if label_on:
        t = text(name + "T", "RICE", (x, y - 0.52 * k, 0.72 * k), 0.26 * k, red_m)
        parts.append(t)
    attach(parts, g)
    return g

# ---------------- YOU ----------------
YX, YY = 0.0, 0.5
you, yd = person("You", (YX, YY, 0), 1.0, mat("YouShirt", (0.95, 0.3, 0.35), 0.7), mat("YouPants", (0.18, 0.22, 0.38), 0.8),
                 skin_m, mat("YouHair", (0.25, 0.14, 0.06), 0.8))
armL, armR = yd["arms"]
def arms_up(fs):
    for f, up in fs:
        a = math.radians(150) * up
        keyrot(armL, [(f, (0, a, 0))]); keyrot(armR, [(f, (0, -a, 0))])
arms_up([(0, 0), (S[0] + 6, 1), (E(0) - 2, 1), (S[1], 0), (S[4], 0), (S[4] + 4, 1), (E(4) - 1, 1), (E(4), 0),
         (S[5], 0), (S[5] + 4, 0.6), (E(5), 0.6), (E(5) + 1, 0),
         (S[13], 0), (S[13] + 4, 0.45), (E(13) - 1, 0.45), (E(13), 0), (S[16], 0), (S[16] + 4, 0.5)])
# you sits out the far-away shots (keeps the yard clean)

# line 0: rice rain + "$1,000,000,000"
rain(45, YX, YY, 2.4, 2.4, 5.0, 0, S[1] + 4, k=1.4, f_gone=S[1] + 6)

# ---------------- line 1: a 1-ton bulk bag with a $500 price tag ----------------
SKX, SKY = 1.7, 1.2
sk1 = sack("Sack1", SKX, SKY, 1.15)
keyscale(sk1, [(0, 0.001), (S[1] - 1, 0.001), (S[1] + 4, 1.15), (S[1] + 6, 1.0), (S[3] - 1, 1.0), (S[3], 0.001),
               (S[16] - 1, 0.001), (S[16] + 4, 1.15), (S[16] + 6, 1.0)])
tg = group("TagG", (SKX - 0.7, SKY - 0.7, 1.0))
tagp = [box("TagCard", (SKX - 0.7, SKY - 0.7, 1.0), (0.9, 0.04, 0.5), tag_m, bevel=0.03),
        text("TagT", "$500", (SKX - 0.7, SKY - 0.73, 1.0), 0.3, dark_m)]
attach(tagp, tg)
keyscale(tg, [(0, 0.001), (W(1, 0.35) - 1, 0.001), (W(1, 0.35) + 4, 1.2), (W(1, 0.35) + 6, 1.0), (S[3] - 1, 1.0), (S[3], 0.001)])
keyrot(tg, [(W(1, 0.35), (0, 0, -0.3)), (W(1, 0.35) + 8, (0, 0, 0.25)), (E(1), (0, 0, -0.1))])

# ---------------- line 2: sacks multiply across the lawn ----------------
for j, sy in enumerate([3.0, 4.6, 6.2, 7.8, 9.4]):
    for i, sx_ in enumerate([-4.5, -3.0, -1.5, 0.0, 1.5, 3.0, 4.5, 6.0]):
        if sy > 8 and sx_ < -3:
            continue
        g = sack(f"Sk{i}{j}", sx_ + random.uniform(-0.1, 0.1), sy, 1.0, label_on=(j < 2))
        f0 = S[2] + int((i + j * 2) * 0.9)
        keyscale(g, [(0, 0.001), (f0 - 1, 0.001), (f0 + 3, 1.2), (f0 + 5, 1.0), (S[3] - 1, 1.0), (S[3], 0.001)])
        key_loc(g, [(f0 - 1, (g.location.x, g.location.y, 3.0)), (f0 + 4, (g.location.x, g.location.y, 0.0))])
        g.rotation_euler = (0, 0, random.uniform(-0.15, 0.15))

# ---------------- line 3: $1B in $100 bills = 10 t, a ~2.2 m cube ----------------
CBX, CBY = -2.4, 1.6
cg = group("CashG", (CBX, CBY, 0))
cparts = [box("CashCube", (CBX, CBY, 1.15), (2.2, 2.2, 2.2), cash_m, bevel=0.03),
          box("Pallet", (CBX, CBY, 0.06), (2.4, 2.4, 0.12), mat("Wood", (0.6, 0.42, 0.24), 0.8))]
for dx in (-0.55, 0.55):
    cparts.append(box("CBand", (CBX + dx, CBY, 1.15), (0.22, 2.24, 2.24), band_m))
cparts.append(text("CashT", "$1B", (CBX, CBY - 1.13, 1.5), 0.6, white_lab))
attach(cparts, cg)
keyscale(cg, [(0, 0.001), (S[3] - 1, 0.001), (S[3] + 4, 1.15), (S[3] + 6, 1.0), (S[5] - 1, 1.0), (S[5], 0.001),
              (S[16] - 1, 0.001), (S[16] + 4, 1.15), (S[16] + 6, 1.0)])
cbill = []
for k in range(14):  # bills puff out when it lands
    b = box("Puff", (CBX + random.uniform(-1, 1), CBY - 1.2, random.uniform(0.3, 2.2)), (0.31, 0.13, 0.006), bill_m)
    b.rotation_euler = (random.uniform(0, 3), random.uniform(0, 3), random.uniform(0, 3))
    key_loc(b, [(S[3] + 3, tuple(b.location)), (S[3] + 16, (b.location.x + random.uniform(-1.5, 1.5), b.location.y - random.uniform(0.5, 1.5), b.location.z + random.uniform(0.5, 1.5)))])
    pop(b, S[3] + 3, 3, S[3] + 18)

# ---------------- the rice mountain: 2 million t as one cone (~100 m tall) ----------------
MX, MY = 0.0, 500.0
MH, MR = 98.0, 165.0
mtn = cyl("Mountain", (MX, MY, 0), MR, MH, rice_big_m, r2=6.0, verts=64)
bpy.ops.object.shade_smooth()
me_ = mtn.data
for v_ in me_.vertices:      # base at z=0, origin at ground
    v_.co.z += MH / 2
cap_ = sphere("MtnCap", (MX, MY, MH - 2), 9.0, rice_big_m, scale=(1, 1, 0.5))
parent_to(cap_, mtn)
for v_ in me_.vertices:
    if v_.co.z > 1:
        v_.co.x += random.uniform(-3, 3); v_.co.y += random.uniform(-3, 3)
keyscale(mtn, [(0, 0.001), (S[4] - 1, 0.001), (S[4] + 1, (1, 1, 0.02)), (W(4, 0.7), (1, 1, 1.05)), (W(4, 0.8), (1, 1, 1.0)),
               (S[5] - 1, 1.0), (S[5], 0.001),
               (S[11] - 1, 0.001), (S[11] + 1, (0.4, 0.4, 0.05)), (E(11), (0.8, 0.8, 0.75)), (S[12] + 6, (1, 1, 1.03)), (S[12] + 9, 1.0),
               (S[14] + 2, 1.0), (W(14, 0.85), (0.08, 0.08, 0.03)), (E(14) - 1, 0.001)])
# rice stream pouring from the sky (line 4 and 11)
stream = cyl("Stream", (MX, MY, 300), 9.0, 600, rice_m, verts=20)
keyscale(stream, [(0, 0.001), (S[4] - 1, 0.001), (S[4], 1.0), (W(4, 0.75), 1.0), (W(4, 0.75) + 3, 0.001),
                  (S[11] - 1, 0.001), (S[11], 1.0), (E(11) + 3, 1.0), (E(11) + 6, 0.001)])

# 30-storey tower next to the pile (line 12)
TWX, TWY = MX + 175.0, MY - 150
tower_m = stripe_mat("TowerM", (0.55, 0.75, 0.95), (0.85, 0.88, 0.9), axis="Z", freq=2.0, thresh=0.2, rough=0.3)
tw = box("Tower", (0, 0, 0), (34, 34, 96), tower_m)
for v_ in tw.data.vertices:
    v_.co.z += 48
tw.location = (TWX, TWY, 0)
keyscale(tw, [(0, 0.001), (S[12] - 1, 0.001), (S[12] + 1, (1, 1, 0.05)), (S[12] + 8, (1, 1, 1.05)), (S[12] + 10, 1.0), (S[14] - 1, 1.0), (S[14], 0.001)])

# ---------------- line 5: giant grains tumbling ----------------
rain(40, YX, YY - 0.4, 2.2, 1.5, 4.5, S[5], E(5) - 2, k=2.2, f_gone=E(5))
for k in range(3):
    gg = grain("BigGrain", (YX + (k - 1) * 1.3, YY - 1.1, 2.6 + 0.3 * (k % 2)), 4.0)
    gg.rotation_euler = (0, 0.4 * (k - 1), 0)
    pop(gg, S[5] + 2 + 3 * k, 5, E(5))
    keyrot(gg, [(S[5], (0, 0.4 * (k - 1), 0)), (E(5), (0.8, 0.4 * (k - 1) + 1.2, 0.5))])

# ---------------- line 6: counting one grain per second (clock spins) ----------------
CKX, CKY = 1.6, 0.9
ckg = group("ClockG", (CKX, CKY, 1.6))
ckp = [cyl("ClockFace", (CKX, CKY, 1.6), 0.75, 0.12, white_m, rot=(math.radians(90), 0, 0), verts=36),
       cyl("ClockRim", (CKX, CKY + 0.02, 1.6), 0.82, 0.1, red_m, rot=(math.radians(90), 0, 0), verts=36)]
for k in range(12):
    a = k / 12 * 6.283
    ckp.append(box("Tick", (CKX + 0.62 * math.cos(a), CKY - 0.07, 1.6 + 0.62 * math.sin(a)), (0.06, 0.02, 0.06), dark_m))
attach(ckp, ckg)
hands = []
for L_, wdt, spd in ((0.55, 0.05, 30), (0.38, 0.08, 3)):
    hg = group("HandG", (CKX, CKY - 0.09, 1.6))
    attach([box("Hand", (CKX, CKY - 0.09, 1.6 + L_ / 2), (wdt, 0.02, L_), dark_m)], hg)
    keyrot(hg, [(S[6], (0, 0, 0)), (E(6), (0, spd, 0))])
    for fc in []: pass
    hands.append(hg)
for o_ in [ckg] + hands:
    keyscale(o_, [(0, 0.001), (S[6] - 1, 0.001), (S[6] + 4, 1.15), (S[6] + 6, 1.0), (E(6) - 1, 1.0), (E(6), 0.001)])
for k in range(12):   # grains hop onto a little counted pile, one by one
    f_ = S[6] + 2 + k * 3
    gx = -0.9 + (k % 4) * 0.22; gz = 0.08 + (k // 4) * 0.12
    gg = grain("Counted", (gx, YY - 0.6, gz), 1.0)
    key_loc(gg, [(f_, (YX + 0.4, YY - 0.5, 1.2)), (f_ + 3, (gx, YY - 0.6, gz))])
    hide_until(gg, f_); gone_at(gg, E(6), 1)
# you get a long white beard while counting
beard = sphere("Beard", (YX, YY - 0.2, 1.45), 0.2, white_m, scale=(1.0, 0.7, 1.4))
keyscale(beard, [(0, 0.001), (S[6], 0.001), (W(6, 0.5), (1.0, 0.7, 1.4)), (E(6) - 2, (1.4, 0.9, 3.0)), (E(6), 0.001)])
key_loc(beard, [(S[6], (YX, YY - 0.2, 1.45)), (E(6) - 2, (YX, YY - 0.25, 1.15))])

# ---------------- lines 7-8: 80,000 trucks on a road to the horizon ----------------
RX = -40.0
road = box("Road", (RX, 3000, 0.02), (9, 6010, 0.04), road_m)
for k in range(300):
    box("Dash", (RX, 2 + k * 20, 0.05), (0.25, 4, 0.02), white_m)
def truck_mesh():
    objs = [box("TCab", (0, -5.3, 1.6), (2.5, 2.2, 2.6), red_m, bevel=0.1),
            box("TWin", (0, -6.42, 2.2), (2.1, 0.05, 0.9), mat("TWinM", (0.2, 0.35, 0.55), 0.1)),
            box("TBody", (0, 1.0, 2.1), (2.6, 10.0, 3.0), rice_m, bevel=0.05),
            box("TStripe", (0, 1.0, 1.0), (2.65, 10.05, 0.25), strap_m)]
    for (wy) in (-5.2, -1.5, 0.0, 4.0, 5.3):
        objs.append(cyl("Wh", (0, wy, 0.55), 0.55, 2.7, dark_m, rot=(0, math.radians(90), 0), verts=14))
    bpy.ops.object.select_all(action='DESELECT')
    for o_ in objs:
        o_.modifiers.clear(); o_.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    t_ = bpy.context.object; t_.name = "TruckProto"
    return t_
tproto = truck_mesh()
trg = group("Trucks", (RX, 0, 0))
trucks = []
for k in range(260):
    o_ = bpy.data.objects.new(f"Truck{k}", tproto.data); sc.collection.objects.link(o_)
    o_.location = (RX - 2.0, 8 + k * 15.0, 0); o_.rotation_euler = (0, 0, math.pi)
    trucks.append(o_)
    if k < 12:   # the first trucks drive in one after another
        f0 = S[7] + k * 2
        key_loc(o_, [(f0, (RX - 2.0, -30 + k * 15.0, 0)), (f0 + 8, (RX - 2.0, 8 + k * 15.0, 0))])
tproto.location = (RX - 2.0, -100, -50)
attach(trucks, trg)
for o_ in (trg, road):
    keyscale(o_, [(0, 0.001), (S[7] - 1, 0.001), (S[7], 1.0), (E(8) - 1, 1.0), (E(8), 0.001)])

# ---------------- line 9: your backyard pool fills with rice ----------------
pool_rice = box("PoolRice", (POX, POY, -0.3), (5.8, 3.2, 0.5), rice_m)
key_loc(pool_rice, [(S[9], (POX, POY, -0.3)), (E(9) - 2, (POX, POY, 0.25))])
keyscale(pool_rice, [(0, 0.001), (S[9] - 1, 0.001), (S[9], 1.0)])
chute = cyl("Chute", (POX + 1.6, POY + 0.6, 6), 0.22, 12, rice_m, verts=16)
keyscale(chute, [(0, 0.001), (S[9] - 1, 0.001), (S[9] + 2, 1.0), (E(9) - 2, 1.0), (E(9), 0.001)])
for k in range(4):
    ring = sphere("Splash", (POX + random.uniform(-1, 1), POY + random.uniform(-0.6, 0.6), 0.3), 0.35, rice_m, scale=(1, 1, 0.5))
    pop(ring, S[9] + 3 + k * 4, 4, E(9))

# ---------------- line 10: a field of ~1,000 Olympic pools full of rice ----------------
def pool_mesh():
    a = box("PRim", (0, 0, 0.4), (27, 52, 0.8), mat("PRimM", (0.92, 0.9, 0.85), 0.7))
    b = box("PFill", (0, 0, 0.85), (25, 50, 0.2), rice_m)
    bpy.ops.object.select_all(action='DESELECT')
    a.select_set(True); b.select_set(True); bpy.context.view_layer.objects.active = a
    bpy.ops.object.join(); p_ = bpy.context.object; p_.name = "PoolProto"; return p_
pproto = pool_mesh()
PFX, PFY = 0.0, 140.0
pfg = group("PoolField", (PFX, PFY, 0))
pools = []
for i in range(40):
    for j in range(25):
        o_ = bpy.data.objects.new(f"OP{i}_{j}", pproto.data); sc.collection.objects.link(o_)
        o_.location = (PFX + (i - 19.5) * 33.0, PFY + j * 58.0, 0)
        pools.append(o_)
pproto.location = (0, -100, -50)
attach(pools, pfg)
keyscale(pfg, [(0, 0.001), (S[10] - 1, 0.001), (S[10] + 5, (1, 1, 1)), (E(10) - 1, 1.0), (E(10), 0.001)])

# ---------------- line 15: a crowd with rice bowls ----------------
shirts = [mat(f"CS{i}", c, 0.7) for i, c in enumerate([(0.2, 0.55, 0.95), (0.95, 0.75, 0.15), (0.35, 0.8, 0.35), (0.85, 0.35, 0.85),
                                                        (1.0, 0.5, 0.2), (0.25, 0.8, 0.8), (0.95, 0.95, 0.95)])]
skins = [mat(f"SK{i}", c, 0.6) for i, c in enumerate([(0.95, 0.74, 0.58), (0.72, 0.5, 0.34), (0.48, 0.32, 0.2), (0.98, 0.82, 0.68)])]
hairs = [mat(f"HR{i}", c, 0.8) for i, c in enumerate([(0.1, 0.07, 0.05), (0.35, 0.2, 0.08), (0.85, 0.65, 0.3), (0.5, 0.5, 0.5)])]
pants_m = mat("CPants", (0.2, 0.24, 0.4), 0.8)
bowl_m = mat("Bowl", (0.2, 0.5, 0.9), 0.4)
def mini(name, x, y, k=1.0):
    g = group(name, (x, y, 0))
    sh = random.choice(shirts); sk = random.choice(skins)
    parts = [cyl(name + "Lg", (x, y, 0.4 * k), 0.17 * k, 0.8 * k, pants_m, verts=12),
             cyl(name + "B", (x, y, 1.1 * k), 0.3 * k, 0.72 * k, sh, r2=0.22 * k, verts=16),
             sphere(name + "H", (x, y, 1.68 * k), 0.24 * k, sk, sub=2),
             sphere(name + "Hr", (x, y + 0.04 * k, 1.8 * k), 0.23 * k, random.choice(hairs), scale=(1.05, 1.0, 0.55), sub=2),
             tube(name + "Sm", [(x - 0.07, y - 0.225, 1.6), (x, y - 0.25, 1.57), (x + 0.07, y - 0.225, 1.6)], [0.013] * 3, eyeb)]
    for sx in (-1, 1):
        parts.append(sphere(name + "E", (x + sx * 0.08 * k, y - 0.215 * k, 1.72 * k), 0.035 * k, eyeb, sub=1))
        parts.append(tube(name + "Ar", [(x + sx * 0.3, y, 1.36), (x + sx * 0.3, y - 0.25, 1.15), (x + sx * 0.12, y - 0.4, 1.15)], [0.07] * 3, sh))
    parts.append(cyl(name + "Bw", (x, y - 0.42, 1.18), 0.22, 0.16, bowl_m, r2=0.13, rot=(math.pi, 0, 0), verts=16))
    parts.append(sphere(name + "Rc", (x, y - 0.42, 1.27), 0.2, grain_m, scale=(1, 1, 0.55), sub=2))
    attach(parts, g)
    return g
for j, cy in enumerate([1.6, 3.6, 5.6, 7.6, 9.6]):
    for i, cx in enumerate([-4.8, -2.4, 0.0, 2.4, 4.8, 7.2]):
        x, y = cx + random.uniform(-0.3, 0.3) + (1.2 if j % 2 else 0), cy + random.uniform(-0.2, 0.2)
        g = mini(f"M{i}{j}", x, y)
        f0 = S[15] + (i + j)
        keyscale(g, [(0, 0.001), (f0 - 1, 0.001), (f0 + 4, 1.12), (f0 + 6, 1.0), (E(15) - 1, 1.0), (E(15), 0.001)])
        ph = random.randint(0, 6)
        for k_ in range(2):
            fj = S[15] + 6 + ph + k_ * 10
            if fj + 8 < E(15):
                key_loc(g, [(fj, (x, y, 0)), (fj + 4, (x, y, 0.35)), (fj + 8, (x, y, 0))])
# hide YOU during line 15 (crowd stands there)
keyscale(you, [(0, 1.0), (S[15] - 1, 1.0), (S[15], 0.001), (E(15) - 1, 0.001), (E(15), 1.0)])

# line 16: question marks above cash and rice
for k, (qx, qm) in enumerate([(CBX, lab_m), (SKX, lab_m)]):
    q = text(f"Q{k}", "?", (qx, 1.0, 3.3), 1.0, qm, extrude=0.08)
    pop(q, S[16] + 6 + 4 * k, 5)
    keyrot(q, [(S[16] + 6, (math.radians(90), 0, -0.2)), (FRAMES - 1, (math.radians(90), 0, 0.2))])

for o_ in bpy.data.objects:
    if o_.name.startswith("Cloud"):
        keyscale(o_, [(S[10] - 1, 1.0), (S[10], 0.001), (E(10) - 1, 0.001), (E(10), 1.0)])
# ---------------- views (camera, subject) per line; subject sits in the lower third ----------------
V = {}; V2 = {}
V[0] = ((1.2, -5.0, 1.9), (YX, YY, 0.95))
V[1] = ((3.2, -4.6, 2.0), (SKX - 0.3, SKY, 0.9))
V[2] = ((4.0, -11.0, 4.0), (1.0, 5.6, 0.8));                 V2[2] = ((2.0, -12.5, 4.5), (0.8, 5.6, 0.8))
V[3] = ((-0.2, -5.6, 2.0), (CBX + 0.6, CBY, 1.1))
V[4] = ((3.0, -9.0, 2.5), (CBX + 2.0, CBY + 20, 2.0));        V2[4] = ((5.0, -14.0, 3.5), (CBX + 2.0, CBY + 30, 4.0))
V[5] = ((-1.0, -5.4, 2.0), (YX, YY, 1.2))
V[6] = ((0.2, -5.0, 1.8), (YX + 0.7, YY, 1.0))
V[7] = ((RX + 12.0, -14.0, 6.0), (RX - 2.0, 25.0, 1.5));     V2[7] = ((RX + 10.0, -10.0, 9.0), (RX - 2.0, 40.0, 1.5))
V[8] = ((RX + 7.0, -6.0, 7.0), (RX - 2.0, 45.0, 0.5));   V2[8] = ((RX + 6.0, -10.0, 13.0), (RX - 2.0, 90.0, 0.5))
V[9] = ((POX + 2.0, POY - 8.0, 3.0), (POX, POY, 0.3))
V[10] = ((60.0, 30.0, 110.0), (0.0, 520.0, 0.0));         V2[10] = ((-60.0, 30.0, 130.0), (0.0, 560.0, 0.0))
V[11] = ((40.0, 5.0, 25.0), (MX, MY - 200, 30.0));         V2[11] = ((20.0, 5.0, 30.0), (MX, MY - 200, 40.0))
V[12] = ((40.0, 5.0, 55.0), (MX + 110, MY - 150, 35.0));   V2[12] = ((80.0, 5.0, 60.0), (MX + 110, MY - 150, 35.0))
V[13] = ((1.6, -5.2, 1.6), (YX, YY, 1.0))
V[14] = ((40.0, 5.0, 30.0), (MX, MY - 200, 20.0));         V2[14] = ((0.0, 5.0, 26.0), (MX, MY - 200, 12.0))
V[15] = ((2.5, -10.5, 4.5), (1.2, 5.0, 0.9));                V2[15] = ((-0.5, -10.0, 4.5), (1.2, 5.0, 0.9))
V[16] = ((0.0, -7.2, 2.4), (-0.3, 1.2, 1.0));                V2[16] = ((-1.0, -6.6, 2.4), (-0.3, 1.2, 1.0))
DR = {0: (-0.5, 0.8, 0), 1: (-0.6, 0.6, 0), 3: (0.8, 0.5, 0), 5: (0.8, 0.5, 0), 6: (-0.5, 0.6, 0), 9: (-2.0, 1.0, 0), 13: (-0.6, 0.5, 0)}

def LB(i, name, body, m_, size=None, f_in=None, f_out=None, Dk=0.55, end=False, v=0.3, u=0.0):
    view = V2[i] if end else V[i]
    cl = Vector(CL(view)); D = (Vector(view[1]) - cl).length * Dk
    s_ = 0.85 * fit(body, D, size if size else 1e9)
    return label(name, body, view, D, v, s_, m_, (S[i] + 3) if f_in is None else f_in,
                 E(i) if f_out is None else f_out, u)
LB(0, "L0", "$1,000,000,000", lab_m)
LB(1, "L1", "$500 / TON", lab_m)
LB(2, "L2", "2,000,000 TONS", lab_m, end=True)
LB(3, "L3", "CASH: 10 TONS", green_lab if 'green_lab' in globals() else white_lab)
LB(4, "L4", "x200,000!", lab_m, end=True, f_in=W(4, 0.4))
LB(5, "L5", "80 TRILLION GRAINS", white_lab)
LB(6, "L6", "2.5 MILLION YEARS", lab_m, f_in=W(6, 0.4))
LB(7, "L7", "80,000 TRUCKS", lab_m, end=True)
LB(8, "L8", "1,000+ KM", lab_m, end=True, Dk=0.35)
LB(9, "L9", "1 POOL...", white_lab)
LB(10, "L10", "~1,000 POOLS!", lab_m, end=True, Dk=0.35)
LB(11, "L11", "ONE PILE", white_lab, end=True, Dk=0.4)
LB(12, "L12", "~100 M TALL", lab_m, end=True)
LB(13, "L13", "ENDLESS?", white_lab)
LB(14, "L14", "GONE IN < 2 DAYS", red_lab, end=True)
LB(15, "L15", "HALF OF HUMANITY", lab_m, end=True)
LB(16, "L16", "CASH OR RICE?", lab_m, end=True, f_in=S[16] + 6, Dk=0.45)
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
