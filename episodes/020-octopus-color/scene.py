# Day 20 — What if you could change color like an octopus?  Build: python3 episodes/020-octopus-color/scene.py
# Reference style: base (helpers, lawn/soil, house, garden, camera helpers) copied from episodes/016-tardigrade
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
# Day 20 — What if you could change color like an octopus?
# Facts used: octopus skin holds thousands-to-millions of chromatophores — tiny elastic pigment sacs
#   (red, yellow, brown, black) ringed by radial muscles; nerves from the brain contract the muscles to
#   stretch a sac open and show its colour, so a pattern can change in a fraction of a second (~0.2-0.7 s).
#   Papillae let it raise bumps and spikes to match texture. Many octopuses darken during aggressive
#   displays (e.g. Scheel et al. 2016, gloomy octopus). Most cephalopods have a single visual pigment and are
#   thought to be colour-blind. Opsins in octopus skin let the skin itself respond to light
#   (Ramirez & Oakley 2015, California two-spot octopus).
# =====================================================================================
random.seed(20)
CY = 2.6
gspark_m = glow_mat("GSpark", (0.4, 1.0, 0.4), 4.0)
cspark_m = glow_mat("CSpark", (0.4, 0.95, 1.0), 4.0)

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
def keycol(sock, keys):
    for f, c in keys:
        sock.default_value = (*c, 1); sock.keyframe_insert("default_value", frame=f)
def keyval(sock, keys):
    for f, v in keys:
        sock.default_value = v; sock.keyframe_insert("default_value", frame=f)

def skin_mat(name, base, mottle=0.18):
    """Colour-changing skin: animated base colour x soft noise mottling."""
    m = mat(name, base, 0.5); N = m.node_tree.nodes; L = m.node_tree.links
    bs = N["Principled BSDF"]
    nz = N.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 4.0; nz.inputs["Detail"].default_value = 4.0
    rp = N.new("ShaderNodeValToRGB"); e = rp.color_ramp.elements
    e[0].position = 0.35; e[0].color = (1 - mottle * 2, 1 - mottle * 2, 1 - mottle * 2, 1); e[1].position = 0.65; e[1].color = (1, 1, 1, 1)
    L.new(nz.outputs["Fac"], rp.inputs["Fac"])
    mx = N.new("ShaderNodeMix"); mx.data_type = 'RGBA'; mx.blend_type = 'MULTIPLY'; mx.inputs["Factor"].default_value = 1.0
    mx.inputs[6].default_value = (*base, 1)
    L.new(rp.outputs["Color"], mx.inputs[7]); L.new(mx.outputs[2], bs.inputs["Base Color"])
    return m, mx.inputs[6]

WALLC = (0.86, 0.8, 0.7)
def camo_mat(name, base):
    """Person material: base colour -> lawn stripes (fA) -> wall plaster (fB)."""
    m = mat(name, base, 0.6); N = m.node_tree.nodes; L = m.node_tree.links
    bs = N["Principled BSDF"]
    geo = N.new("ShaderNodeNewGeometry"); sx = N.new("ShaderNodeSeparateXYZ"); L.new(geo.outputs["Position"], sx.inputs[0])
    ad = N.new("ShaderNodeMath"); ad.operation = 'ADD'; L.new(sx.outputs["X"], ad.inputs[0]); L.new(sx.outputs["Y"], ad.inputs[1])
    mu = N.new("ShaderNodeMath"); mu.operation = 'MULTIPLY'; mu.inputs[1].default_value = 1.35; L.new(ad.outputs[0], mu.inputs[0])
    sn = N.new("ShaderNodeMath"); sn.operation = 'SINE'; L.new(mu.outputs[0], sn.inputs[0])
    gt = N.new("ShaderNodeMath"); gt.operation = 'GREATER_THAN'; gt.inputs[1].default_value = 0.0; L.new(sn.outputs[0], gt.inputs[0])
    st = N.new("ShaderNodeMix"); st.data_type = 'RGBA'
    st.inputs[6].default_value = (0.22, 0.5, 0.12, 1); st.inputs[7].default_value = (0.42, 0.72, 0.22, 1)
    L.new(gt.outputs[0], st.inputs["Factor"])
    a = N.new("ShaderNodeMix"); a.data_type = 'RGBA'; a.inputs["Factor"].default_value = 0.0
    a.inputs[6].default_value = (*base, 1); L.new(st.outputs[2], a.inputs[7])
    b = N.new("ShaderNodeMix"); b.data_type = 'RGBA'; b.inputs["Factor"].default_value = 0.0
    L.new(a.outputs[2], b.inputs[6]); b.inputs[7].default_value = (*WALLC, 1)
    L.new(b.outputs[2], bs.inputs["Base Color"])
    return m, a.inputs[6], a.inputs["Factor"], b.inputs["Factor"]

# ---------------- tide-pool corner: sand, coral, rock ----------------
sand_m, _ = skin_mat("Sand", (0.93, 0.8, 0.55), 0.12)
sandD = cyl("SandPatch", (0, CY + 0.3, 0.02), 3.3, 0.06, sand_m, verts=48)
sandD.scale = (1.0, 0.72, 1.0)
coral_m = mat("Coral", (0.98, 0.42, 0.58), 0.6)
coral2_m = mat("Coral2", (1.0, 0.6, 0.35), 0.6)
CRX, CRY = -2.55, CY + 0.75
for k in range(9):
    a = k / 9 * 6.283; h = random.uniform(0.7, 1.4)
    tl = (random.uniform(-0.35, 0.35), random.uniform(-0.3, 0.3))
    p0 = (CRX + 0.25 * math.cos(a), CRY + 0.2 * math.sin(a), 0.05)
    p1 = (p0[0] + tl[0], p0[1] + tl[1], h)
    m_ = coral_m if k % 3 else coral2_m
    tube("CoralB", [p0, ((p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2, h * 0.5), p1], [0.12, 0.1, 0.08], m_)
    sphere("CoralTip", p1, 0.13, m_, sub=1)
ROX, ROY = 2.6, CY + 0.7
rock_m = mat("Rock", (0.55, 0.55, 0.58), 0.85)
sphere("Rock", (ROX, ROY, 0.35), 0.85, rock_m, scale=(1.25, 0.95, 0.8), sub=1, smooth=False)
sphere("Rock2", (ROX + 0.9, ROY - 0.6, 0.15), 0.35, rock_m, scale=(1.2, 1, 0.7), sub=1, smooth=False)
sphere("Rock3", (ROX - 0.9, ROY + 0.3, 0.15), 0.3, rock_m, scale=(1.2, 1, 0.7), sub=1, smooth=False)
shell_m = mat("Shell", (1.0, 0.9, 0.8), 0.5)
for (x, y) in [(-1.2, CY - 1.0), (1.4, CY - 1.1), (-2.0, CY - 0.4)]:
    sphere("Shell", (x, y, 0.06), 0.13, shell_m, scale=(1.2, 1, 0.5), sub=1, smooth=False)
star_m = mat("Starfish", (1.0, 0.75, 0.15), 0.6)
for k in range(5):
    a = k / 5 * 6.283
    cyl("StarArm", (1.9 + 0.13 * math.cos(a), CY - 0.5 + 0.13 * math.sin(a), 0.07), 0.08, 0.3, star_m, rot=(0, math.radians(90), a), r2=0.02, verts=6)

# ---------------- the cartoon octopus (hub at (0, CY, 0)) ----------------
ORANGE = (0.95, 0.36, 0.14)
oct_m, OCOL = skin_mat("OctSkin", ORANGE, 0.16)
sucker_m = mat("Sucker", (1.0, 0.86, 0.75), 0.5)
op = []
op.append(sphere("Mantle", (0, CY + 0.38, 1.5), 0.8, oct_m, scale=(0.85, 0.95, 1.12), sub=3))
op.append(sphere("Head", (0, CY - 0.05, 0.85), 0.62, oct_m, scale=(1.0, 0.9, 0.85), sub=3))
for sx in (-1, 1):
    op.append(sphere("OEyeW", (sx * 0.3, CY - 0.52, 1.02), 0.19, eyew, sub=2))
    op.append(sphere("OEyeB", (sx * 0.3, CY - 0.69, 1.02), 0.09, eyeb, scale=(1.4, 0.6, 0.75), sub=2))
    op.append(sphere("OBlush", (sx * 0.47, CY - 0.5, 0.75), 0.08, mat("OBlushM", (1.0, 0.5, 0.55), 0.6), scale=(1, 0.5, 0.7), sub=1))
op.append(tube("OSmile", [(-0.12, CY - 0.6, 0.66), (0, CY - 0.64, 0.62), (0.12, CY - 0.6, 0.66)], [0.02] * 3, eyeb))
tents = []
for k in range(8):
    a = k / 8 * 6.283 + 6.283 / 16
    tg = group("TentG", (0, CY, 0.35))
    rs = [0.35, 0.8, 1.25, 1.7, 2.0, 2.1]
    zs = [0.42, 0.22, 0.14, 0.12, 0.2, 0.42]
    pts = []
    for j, (r_, z_) in enumerate(zip(rs, zs)):
        aa = a + (0.35 if j >= 4 else 0.0) * (j - 3) / 2
        pts.append((r_ * math.cos(aa), CY + r_ * math.sin(aa) * 0.85, z_))
    parts = [tube("Tent", pts, [0.22, 0.17, 0.13, 0.09, 0.06, 0.035], oct_m)]
    for j in (1, 2, 3):
        p = pts[j]
        parts.append(sphere("Suck", (p[0], p[1], p[2] + [0.17, 0.13, 0.09][j - 1] * 0.75), [0.06, 0.05, 0.04][j - 1], sucker_m, scale=(1, 1, 0.5), sub=1))
    attach(parts, tg)
    tents.append(tg)
    ph = k * 0.8
    for f in range(0, FRAMES + 12, 8):
        tg.rotation_euler = (0, 0, 0.12 * math.sin(ph + f / 8 * 1.6)); tg.keyframe_insert("rotation_euler", frame=f)
# papillae (bumps & spikes) on the mantle, hidden until line 6
pap = []
MC = Vector((0, CY + 0.38, 1.5)); MR = Vector((0.68, 0.76, 0.9))
for k in range(18):
    th = random.uniform(-2.6, -0.5); ph = random.uniform(0.15, 1.2)
    n = Vector((math.cos(th) * math.cos(ph), math.sin(th) * math.cos(ph), math.sin(ph))).normalized()
    p = MC + Vector((n.x * MR.x, n.y * MR.y, n.z * MR.z))
    c_ = cyl("Papilla", tuple(p + n * 0.1), 0.11, 0.3, oct_m, r2=0.0, verts=8)
    aim_obj(c_, (0, 0, 0), tuple(n))
    pap.append(c_)
brows = []
for sx in (-1, 1):
    b_ = box("Brow", (sx * 0.3, CY - 0.68, 1.27), (0.34, 0.06, 0.07), eyeb, rot=(0, sx * 0.45, 0))
    brows.append(b_)
OCT = group("OCT", (0, CY, 0))
attach(op + tents + pap + brows, OCT)

# =====================================================================================
# per-line views
# =====================================================================================
MX, MY = 4.6, 1.3
WX = MX + 2.4
V = {}
V[0] = ((3.0, -5.6, 2.2), (0.0, CY, 0.9))
V[1] = ((-2.4, -5.2, 1.9), (0.0, CY, 0.9))
V[2] = ((0.9, -3.4, 1.9), (0.0, CY - 1.6, 1.0))
V[3] = ((-0.8, -3.4, 2.0), (0.0, CY - 1.6, 1.0))
V[4] = ((0.5, -3.2, 1.7), (0.0, CY - 1.6, 1.0))
V[5] = ((2.8, -5.0, 2.2), (0.0, CY, 1.0))
V[6] = ((-1.6, -4.4, 2.4), (0.0, CY, 1.2))
V[7] = ((0.0, -6.6, 2.4), (0.0, CY, 0.6))
V[8] = ((1.8, -4.4, 1.8), (0.0, CY, 1.0))
V[9] = ((0.0, -5.8, 2.2), (0.0, CY - 0.7, 0.9))
V[10] = ((-2.6, -5.2, 2.0), (0.0, CY, 1.0))
V[11] = ((MX + 1.2, MY - 4.2, 1.8), (MX, MY, 1.2))
V[12] = ((MX - 1.2, MY - 4.0, 1.7), (MX, MY, 1.35))
V[13] = ((MX + 0.4, MY - 4.6, 2.2), (MX, MY, 1.1))
V[14] = ((WX - 0.8, MY - 4.6, 2.0), (WX - 0.3, MY, 1.2))
V[15] = ((WX - 1.6, MY - 5.6, 2.4), (WX - 1.2, MY, 0.9))
V[16] = ((2.6, -8.4, 3.0), (2.7, CY - 0.6, 0.8))
DR = {0: (-0.8, 0.6, 0), 1: (0.9, 0.6, 0), 2: (-0.6, 0.4, 0), 3: (0.6, 0.4, 0), 4: (0.5, 0.4, 0), 5: (-0.8, 0.6, 0),
      6: (0.7, 0.5, 0), 7: (0.8, 0.6, 0), 8: (-0.7, 0.6, 0), 9: (0.6, 0.5, 0), 10: (0.8, 0.5, 0), 11: (-0.6, 0.5, 0),
      12: (0.6, 0.5, 0), 13: (-0.5, 0.5, 0), 14: (0.6, 0.6, 0), 15: (-0.6, 0.5, 0), 16: (-0.9, 1.0, -0.2)}
def LB(i, name, body, v, m_, size=None, u=0.0, f_in=None, f_out=None, Dk=0.55):
    cl = Vector(CL(V[i])); D = (Vector(V[i][1]) - cl).length * Dk
    s_ = fit(body, D, size if size else 1.0)
    return label(name, body, V[i], D, v, s_, m_, (S[i] + 3) if f_in is None else f_in,
                 (S[i + 1] if i + 1 < len(S) else FRAMES + 5) if f_out is None else f_out, u)
LT = 0.3
orange_lab = mat("LabO", (1.0, 0.5, 0.15), 0.4, emit=(1.0, 0.45, 0.1), emit_strength=1.0)
grey_lab = mat("LabGr", (0.75, 0.75, 0.75), 0.4, emit=(0.7, 0.7, 0.7), emit_strength=0.6)

# ---------------- octopus colour track ----------------
BLUE = (0.2, 0.45, 0.95); GREEN = (0.25, 0.75, 0.3); PURPLE = (0.6, 0.3, 0.9); YELLOW = (1.0, 0.82, 0.15)
SAND = (0.93, 0.8, 0.55); CORAL = (0.98, 0.42, 0.58); ROCK = (0.55, 0.55, 0.58); DARK = (0.25, 0.05, 0.06)
ck = [(0, ORANGE), (14, ORANGE), (18, BLUE), (26, BLUE), (30, GREEN), (36, GREEN), (40, ORANGE)]
cyc = [BLUE, GREEN, PURPLE, YELLOW, CORAL, BLUE, GREEN, ORANGE]
ck += [(S[5], ORANGE)] + [(S[5] + 4 + 3 * j, c) for j, c in enumerate(cyc)] + [(S[6] - 1, ORANGE)]
F7 = [S[7], S[7] + 14, S[7] + 28]
ck += [(F7[0] + 2, ORANGE), (F7[0] + 7, SAND), (F7[1] - 1, SAND), (F7[1] + 5, CORAL), (F7[2] - 1, CORAL), (F7[2] + 5, ROCK),
       (S[8] - 1, ROCK), (S[8] + 6, DARK), (S[9] - 2, DARK), (S[9] + 4, ORANGE), (S[10] + 4, ORANGE), (S[10] + 10, (1.0, 0.62, 0.3)),
       (S[11] - 2, (1.0, 0.62, 0.3)), (S[11], ORANGE)]
ck += [(S[16] + 4 + 6 * j, c) for j, c in enumerate(cyc * 3) if S[16] + 4 + 6 * j < FRAMES]
ck.sort(key=lambda x: x[0])
keycol(OCOL, ck)

# line 0
LB(0, "L0", "OCTOPUS POWER?", LT, orange_lab)
# line 1: wave, label
for k in (1, 6):
    keyrot(tents[k], [(S[1], (0, 0, 0)), (S[1] + 5, (0.0, -0.5 if k == 1 else 0.5, 0.1)), (S[1] + 12, (0, 0, -0.1)),
                      (S[1] + 18, (0.0, -0.5 if k == 1 else 0.5, 0.1)), (S[2], (0, 0, 0))])
LB(1, "L1", "MASTER OF DISGUISE", LT, lab_m)

# lines 2-4: magnifier on the skin: tiny colour sacs -> 4 pigments -> muscles stretch them open
LC = (0.0, CY - 1.6, 1.0)
lp = [cyl("LensDisk", LC, 1.05, 0.06, mat("LensSkin", (0.98, 0.78, 0.62), 0.6), rot=(math.radians(90), 0, 0), verts=40)]
bpy.ops.mesh.primitive_torus_add(major_radius=1.1, minor_radius=0.09, location=LC, rotation=(math.radians(90), 0, 0))
ring_ = bpy.context.object; ring_.data.materials.append(mat("LensRim", (0.15, 0.15, 0.2), 0.4)); lp.append(ring_)
lp.append(cyl("LensHandle", (LC[0] + 1.25, LC[1] + 0.02, LC[2] - 1.0), 0.09, 0.8, mat("LensH", (0.35, 0.2, 0.1), 0.6), rot=(0, math.radians(-40), 0), verts=10))
pig = [red_lab, lab_m, mat("PigBrown", (0.45, 0.22, 0.08), 0.5, emit=(0.4, 0.2, 0.06), emit_strength=0.5), mat("PigBlack", (0.04, 0.04, 0.05), 0.5)]
muscle_m = mat("MuscleM", (0.85, 0.35, 0.4), 0.6)
dots = []
pos_ = []
while len(pos_) < 20:
    x, z = random.uniform(-0.82, 0.82), random.uniform(-0.82, 0.82)
    if x * x + z * z < 0.72 and all((x - a) ** 2 + (z - b) ** 2 > 0.09 for a, b in pos_):
        pos_.append((x, z))
for k, (x, z) in enumerate(pos_):
    c = k % 4
    d_ = cyl("Sac", (LC[0] + x, LC[1] - 0.05, LC[2] + z), 0.14, 0.04, pig[c], rot=(math.radians(90), 0, 0), verts=16)
    sp = []
    for j in range(6):
        a = j / 6 * 6.283
        sp.append(box("Muscle", (LC[0] + x + 0.2 * math.cos(a), LC[1] - 0.06, LC[2] + z + 0.2 * math.sin(a)), (0.13, 0.02, 0.025),
                      muscle_m, rot=(0, -a, 0)))
    dots.append((d_, c, sp))
LENS = group("LENS", LC)
attach(lp + [d for d, c, s in dots] + sum([s for d, c, s in dots], []), LENS)
LENS.rotation_euler = (-0.3, 0, 0)
pop(LENS, S[2], 6, S[5])
CW = [S[3] + 2, S[3] + 11, S[3] + 20, S[3] + 29]   # word times: red, yellow, brown, black
for d_, c, sp in dots:
    keyscale(d_, [(0, 0.001), (S[2] + 4, 0.001), (S[2] + 8, 0.35), (CW[c] - 1, 0.35), (CW[c] + 3, 0.75), (CW[c] + 7, 0.55),
                  (S[4] + 4, 0.55), (S[4] + 14, (1.6, 1.0, 1.6)), (S[5] - 1, (1.6, 1.0, 1.6))])
    for m_ in sp:
        keyscale(m_, [(0, 0.001), (S[4] + 1, 0.001), (S[4] + 4, 1.0), (S[4] + 14, (1.5, 1.0, 1.0)), (S[5] - 1, (1.5, 1.0, 1.0))])
LB(2, "L2", "TINY COLOR SACS", LT, lab_m)
LB(3, "L3r", "RED", LT, red_lab, f_in=CW[0], f_out=CW[1])
LB(3, "L3y", "YELLOW", LT, lab_m, f_in=CW[1], f_out=CW[2])
LB(3, "L3b", "BROWN", LT, orange_lab, f_in=CW[2], f_out=CW[3])
LB(3, "L3k", "BLACK", LT, white_lab, f_in=CW[3])
LB(4, "L4", "MUSCLES PULL!", LT, pink_lab)

# line 5: brain -> nerve bolts to every arm, colours flash
BR = (0, CY + 0.38, 1.9)
for k in range(8):
    a = k / 8 * 6.283 + 6.283 / 16
    tip = (1.6 * math.cos(a), CY + 1.6 * math.sin(a) * 0.85, 0.3)
    for j in range(3):
        p0 = tuple(Vector(BR) + (Vector(tip) - Vector(BR)) * (j / 3) + Vector((0.12 * (-1) ** j, 0, 0)))
        p1 = tuple(Vector(BR) + (Vector(tip) - Vector(BR)) * ((j + 1) / 3) + Vector((0.12 * (-1) ** (j + 1), 0, 0)))
        b_ = beam("Nerve", p0, p1, 0.035, cspark_m)
        f0 = S[5] + 2 + j * 2
        keyscale(b_, [(0, 0.001), (f0 - 1, 0.001), (f0, 1.0), (S[6] - 3, 1.0), (S[6], 0.001)])
burst((0, CY - 0.9, 1.6), S[5] + 6, 14, 1.0, 0.05, S[5] + 20, material=cspark_m)
LB(5, "L5", "SPLIT SECOND!", LT, blue_lab)

# line 6: bumps & spikes
for k, c_ in enumerate(pap):
    keyscale(c_, [(0, 0.001), (S[6] + 1 + k % 9, 0.001), (S[6] + 4 + k % 9, 1.3), (S[6] + 7 + k % 9, 1.0), (S[7] + 2, 1.0), (S[7] + 6, 0.001)])
LB(6, "L6", "SPIKY SKIN!", LT, lab_m)

# line 7: sand -> coral -> rock
key_loc(OCT, [(0, (0, CY, 0)), (F7[1] - 4, (0, CY, 0)), (F7[1] + 2, (-1.7, CY - 0.45, 0.25)), (F7[1] + 4, (-1.7, CY - 0.45, 0)),
              (F7[2] - 4, (-1.7, CY - 0.45, 0)), (F7[2] + 2, (1.7, CY - 0.45, 0.35)), (F7[2] + 4, (1.7, CY - 0.45, 0)),
              (S[8] - 2, (1.7, CY - 0.45, 0)), (S[8] + 2, (0, CY, 0))])
LB(7, "L7a", "SAND", LT, lab_m, f_in=F7[0] + 3, f_out=F7[1])
LB(7, "L7b", "CORAL", LT, pink_lab, f_in=F7[1] + 1, f_out=F7[2])
LB(7, "L7c", "ROCK", LT, white_lab, f_in=F7[2] + 1)
# line 8: angry -> dark, brows, red light, steam
for b_ in brows:
    keyscale(b_, [(0, 0.001), (S[8] + 1, 0.001), (S[8] + 4, 1.0), (S[9] - 1, 1.0), (S[9], 0.001)])
bpy.ops.object.light_add(type='POINT', location=(0.0, CY - 1.8, 2.2))
rl = bpy.context.object; rl.data.color = (1.0, 0.2, 0.1); rl.data.shadow_soft_size = 0.5
for f, e in ((0, 0), (S[8], 0), (S[8] + 4, 260), (S[9] - 1, 260), (S[9], 0)):
    rl.data.energy = e; rl.data.keyframe_insert("energy", frame=f)
steam_m = mat("Steam", (0.95, 0.95, 0.95), 0.9, emit=(1, 1, 1), emit_strength=0.4)
for k in range(8):
    sx = -1 if k % 2 else 1
    p0 = (sx * 0.55, CY + 0.2, 2.2); p1 = (sx * (0.9 + 0.1 * k), CY + 0.2, 3.2 + 0.1 * k)
    st_ = sphere("Steam", p0, 0.16 + 0.02 * (k % 3), steam_m, sub=1)
    f0 = S[8] + 3 + 3 * (k // 2)
    key_loc(st_, [(f0, p0), (f0 + 14, p1)])
    keyscale(st_, [(0, 0.001), (f0 - 1, 0.001), (f0, 1.0), (f0 + 12, 1.5), (f0 + 14, 0.001)])
LB(8, "L8", "ANGRY = DARK", LT, red_lab)

# line 9: colour-blind — what you see vs what it (probably) sees
for side, (cx_, name) in enumerate([(-2.05, "YOU"), (2.05, "OCTOPUS")]):
    wc = (cx_, CY - 1.05, 1.45)
    wp = [cyl("WheelBG", wc, 0.78, 0.05, mat("WheelBGM", (0.98, 0.98, 0.98), 0.6), rot=(math.radians(90), 0, 0), verts=32)]
    shades = [0.15, 0.3, 0.45, 0.6, 0.75, 0.9]
    cols = [red_lab, orange_lab, lab_m, green_lab, blue_lab, pink_lab]
    for j in range(6):
        a = j / 6 * 6.283
        m_ = cols[j] if side == 0 else mat("Grey%d" % j, (shades[j],) * 3, 0.5, emit=(shades[j],) * 3, emit_strength=0.4)
        wp.append(sphere("WheelDot", (wc[0] + 0.5 * math.cos(a), wc[1] - 0.06, wc[2] + 0.5 * math.sin(a)), 0.19, m_, scale=(1, 0.4, 1), sub=2))
    wp.append(text("WheelL", name, (wc[0], wc[1] - 0.12, wc[2] - 1.02), 0.36, white_lab, extrude=0.03))
    WG = group("WheelG", wc); attach(wp, WG); WG.rotation_euler = (-0.3, 0, 0)
    pop(WG, S[9] + 2 + side * 8, 5, S[10])
for k, x in enumerate((-0.5, 0.5)):
    q_ = text("QQ", "?", (x, CY - 0.4, 2.35 + 0.2 * k), 0.55, lab_m, extrude=0.05)
    pop(q_, S[9] + 10 + 4 * k, 5, S[10])
LB(9, "L9", "COLORBLIND?!", LT, lab_m)

# line 10: sunbeam on the skin, skin sparkles
beam_m = alpha_mat("BeamM", (1.0, 0.92, 0.5), 0.35, 1.5)
sb = cyl("SunBeam", (0, CY, 3.0), 1.5, 6.0, beam_m, r2=0.35, verts=32)
keyscale(sb, [(0, 0.001), (S[10], 0.001), (S[10] + 4, 1.0), (S[11] - 2, 1.0), (S[11], 0.001)])
for k in range(16):
    a = random.uniform(0, 6.283); r_ = random.uniform(0.3, 1.5)
    gl = sphere("Glint", (r_ * math.cos(a), CY - 0.4 + r_ * math.sin(a) * 0.5, random.uniform(0.3, 2.0)), 0.06, spark_m, sub=1)
    pop(gl, S[10] + 4 + k % 10, 3, S[10] + 16 + k % 10)
LB(10, "L10", "SKIN SENSES LIGHT", LT, lab_m)

# ---------------- lines 11-16: YOU ----------------
shirt_m, SH_C, SH_A, SH_B = camo_mat("ShirtY", (0.95, 0.2, 0.15))
pants_m, PA_C, PA_A, PA_B = camo_mat("PantsY", (0.2, 0.25, 0.6))
skinY_m, SK_C, SK_A, SK_B = camo_mat("SkinY", (0.95, 0.74, 0.58))
hairY_m, HA_C, HA_A, HA_B = camo_mat("HairY", (0.28, 0.16, 0.07))
shoe_m, SO_C, SO_A, SO_B = camo_mat("ShoeY", (0.15, 0.15, 0.18))
you, Y = person("You", (MX, MY, 0.0), 1.0, shirt_m, pants_m, skinY_m, hairY_m)
shoe_m = mat("Shoe2", (0.15, 0.15, 0.18), 0.6)
seeker, SKR = person("Seeker", (WX - 2.7, MY + 0.3, 0.0), 1.0, mat("ShirtS", (0.2, 0.5, 0.95), 0.7), mat("PantsS", (0.25, 0.25, 0.3), 0.8),
                     skin_m, mat("HairS", (0.1, 0.08, 0.06), 0.8))
# garden wall with a shuttered window (for line 14)
WY = MY + 0.6
box("GWall", (WX, WY, 1.2), (3.0, 0.4, 2.4), wall_m)
box("GWallCap", (WX, WY, 2.45), (3.2, 0.55, 0.12), trim_m)
box("GWinF", (WX + 0.85, WY - 0.21, 1.4), (0.95, 0.03, 1.05), trim_m)
box("GWin", (WX + 0.85, WY - 0.23, 1.4), (0.8, 0.04, 0.9), win_m)
for sxs in (-1, 1):
    box("GShut", (WX + 0.85 + sxs * 0.6, WY - 0.23, 1.4), (0.24, 0.05, 1.05), shut_m)
cyl("GPot", (WX + 1.9, WY - 0.4, 0.28), 0.26, 0.5, pot_m, r2=0.2, verts=14)
sphere("GPotPlant", (WX + 1.9, WY - 0.4, 0.72), 0.34, fol[1], sub=1, smooth=False)

keyscale(you, [(0, 0.001), (S[11] - 1, 0.001), (S[11], 1.0)])
keyscale(seeker, [(0, 0.001), (S[15] - 1, 0.001), (S[15] + 3, 1.1), (S[15] + 6, 1.0)])
# line 11: easy to spot — bouncing red arrow + target ring
arrow = join([cyl("ArS", (0, 0, 0.35), 0.09, 0.5, red_lab, verts=10), cyl("ArH", (0, 0, 0.0), 0.24, 0.32, red_lab, r2=0.0, verts=12, rot=(math.radians(180), 0, 0))], "Arrow")
for j in range(8):
    f = S[11] + 2 + j * 5
    arrow.location = (MX, MY, 2.35 + (0.25 if j % 2 else 0.0)); arrow.keyframe_insert("location", frame=f)
keyscale(arrow, [(0, 0.001), (S[11] + 1, 0.001), (S[11] + 4, 1.0), (S[12] - 1, 1.0), (S[12] + 1, 0.001)])
tring = tube("Target", [(MX + 0.8 * math.cos(a / 24 * 6.283), MY + 0.8 * math.sin(a / 24 * 6.283), 0.05) for a in range(25)], [0.05] * 25, red_lab)
tring.data.transform(Matrix.Translation((-MX, -MY, 0))); tring.location = (MX, MY, 0.05)
keyscale(tring, [(0, 0.001), (S[11] + 2, 0.001), (S[11] + 6, 1.15), (S[11] + 9, 1.0), (S[12] - 1, 1.0), (S[12] + 1, 0.001)])
LB(11, "L11", "EASY TO SPOT!", LT, red_lab)
# line 12: octopus power — sparks, arms up, rainbow flicker
burst(Y["P"](0, -0.35, 1.0), S[12] + 3, 18, 0.85, 0.05, S[12] + 18, material=gspark_m, yoff=-0.1)
pring = tube("PowRing", [(MX + 0.9 * math.cos(a / 24 * 6.283), MY + 0.9 * math.sin(a / 24 * 6.283), 0.05) for a in range(25)], [0.04] * 25, orange_lab)
pring.data.transform(Matrix.Translation((-MX, -MY, 0))); pring.location = (MX, MY, 0.05)
keyscale(pring, [(0, 0.001), (S[12] + 2, 0.001), (S[12] + 3, 0.3), (S[12] + 18, 1.7), (S[12] + 20, 0.001)])
rain = [BLUE, GREEN, PURPLE, YELLOW, CORAL, BLUE, GREEN, PURPLE, YELLOW]
for off, (sock, base) in enumerate(((SH_C, (0.95, 0.2, 0.15)), (PA_C, (0.2, 0.25, 0.6)), (SK_C, (0.95, 0.74, 0.58)))):
    keycol(sock, [(0, base), (S[12] + 2, base)] + [(S[12] + 4 + 3 * j, rain[(j + 2 * off) % len(rain)]) for j in range(8)] + [(S[13], base)])
keyrot(Y["arms"][0], [(S[12], (0, 0, 0)), (S[12] + 5, (0, 2.6, 0)), (S[13] - 2, (0, 2.6, 0)), (S[13] + 2, (0, 0, 0))])
keyrot(Y["arms"][1], [(S[12], (0, 0, 0)), (S[12] + 5, (0, -2.6, 0)), (S[13] - 2, (0, -2.6, 0)), (S[13] + 2, (0, 0, 0))])
LB(12, "L12", "OCTOPUS POWER!", LT, orange_lab)
# line 13: lawn stripes
FA = [(0, 0.0), (S[13] + 2, 0.0), (S[13] + 10, 1.0), (S[14] + 8, 1.0), (S[14] + 14, 0.0)]
FB = [(0, 0.0), (S[14] + 8, 0.0), (S[14] + 14, 1.0), (S[16] + 2, 1.0), (S[16] + 10, 0.0)]
for a_, b_ in ((SH_A, SH_B), (PA_A, PA_B), (SK_A, SK_B), (HA_A, HA_B), (SO_A, SO_B)):
    keyval(a_, FA); keyval(b_, FB)
for k in range(2):
    q_ = text("Q13", "?", (MX - 0.9 + 1.8 * k, MY - 0.2, 2.3 + 0.2 * k), 0.5, white_lab, extrude=0.05)
    pop(q_, S[13] + 12 + 4 * k, 5, S[14])
LB(13, "L13", "STRIPED = HIDDEN", LT, green_lab, size=0.8)
# line 14: slide to the wall, become plaster
YX = WX - 0.5
key_loc(you, [(0, (MX, MY, 0)), (S[14] + 1, (MX, MY, 0)), (S[14] + 8, (YX, MY + 0.12, 0))])
keyrot(Y["arms"][0], [(S[14] + 6, (0, 0, 0)), (S[14] + 10, (0, 0.5, 0))])
keyrot(Y["arms"][1], [(S[14] + 6, (0, 0, 0)), (S[14] + 10, (0, -0.5, 0))])
LB(14, "L14", "WALL MODE", LT, white_lab)
# line 15: seeker can't find you, trophy
for j in range(6):
    f = S[15] + j * 6
    seeker.rotation_euler = (0, 0, [0.0, 0.6, -0.5, 0.7, -0.4, 0.2][j]); seeker.keyframe_insert("rotation_euler", frame=f)
keyrot(SKR["arms"][1], [(S[15] + 4, (0, 0, 0)), (S[15] + 9, (0, -2.4, 0))])
for k in range(3):
    q_ = text("QS", "?", (WX - 2.7 - 0.4 + 0.4 * k, MY + 0.2, 2.25 + 0.25 * (k % 2)), 0.45, lab_m, extrude=0.05)
    pop(q_, S[15] + 6 + 4 * k, 5, S[16])
gold_m = mat("Gold", (1.0, 0.75, 0.15), 0.25, metal=0.8)
tp = [cyl("TrBase", (WX + 1.6, MY - 0.3, 0.12), 0.25, 0.24, gold_m, verts=16), cyl("TrStem", (WX + 1.6, MY - 0.3, 0.4), 0.06, 0.35, gold_m, verts=10),
      cyl("TrCup", (WX + 1.6, MY - 0.3, 0.8), 0.32, 0.5, gold_m, r2=0.14, verts=20, rot=(math.radians(180), 0, 0))]
TR = group("Trophy", (WX + 1.6, MY - 0.3, 0)); attach(tp, TR)
pop(TR, S[15] + 14, 6, S[16] + 2)
burst((WX + 1.6, MY - 0.7, 1.0), S[15] + 16, 12, 0.6, 0.04, S[15] + 28)
LB(15, "L15", "UNDEFEATED!", LT, lab_m)
# line 16: question
keyrot(Y["arms"][0], [(S[16], (0, 0.5, 0)), (S[16] + 6, (0, 2.4, 0))])
keyrot(Y["arms"][1], [(S[16], (0, -0.5, 0)), (S[16] + 6, (0, -2.4, 0))])
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
