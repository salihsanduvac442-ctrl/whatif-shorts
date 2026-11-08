# Day 14 — What if 1 billion mosquitoes found you?  Build: python3 episodes/014-billion-mosquitoes/scene.py
# Reference style: base (helpers, lawn/soil, house, garden) copied from episodes/003-lift-million-ref/scene.py (via 004)
import bpy, math, random, os, json
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
random.seed(14)
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


# =====================================================================================
# Day 14 — What if 1 billion mosquitoes found you?
# Facts used (AMCA / mosquito.org fun facts and textbooks):
#   an average mosquito weighs ~2.5 mg; only females bite (blood protein to make eggs; males drink nectar);
#   females sense exhaled CO2 from ~75 ft (~23 m) -> "twenty meters"; wings beat ~300-600 times/s -> "500";
#   1,000 x 2.5 mg = 2.5 g = one US penny (2.5 g); 1e6 -> 2.5 kg; 1e9 -> 2,500 kg = 2.5 t ~ a full-size pickup;
#   they fly only ~1-1.5 mph (~1.6-2.4 km/h), slower than walking (~5 km/h), so a fan's breeze beats them;
#   mosquitoes spread malaria, dengue, Zika... -> commonly called the deadliest animal on Earth (WHO).
# Cartoon scale: mosquitoes are drawn far bigger than life so they read on a phone.
# =====================================================================================
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

# ---------------- materials ----------------
mos_body = mat("MosBody", (0.16, 0.13, 0.12), 0.45)
mos_dark = mat("MosDark", (0.05, 0.045, 0.045), 0.4)
mos_abd = stripe_mat("MosAbd", (0.05, 0.045, 0.045), (0.95, 0.95, 0.92), axis="Y", freq=16.0, thresh=0.55, rough=0.4)
mos_leg = mat("MosLeg", (0.1, 0.09, 0.09), 0.5)
wing_m = bpy.data.materials.new("Wing"); wing_m.use_nodes = True
_b = wing_m.node_tree.nodes["Principled BSDF"]
_b.inputs["Base Color"].default_value = (0.75, 0.9, 1.0, 1); _b.inputs["Roughness"].default_value = 0.15
_b.inputs["Alpha"].default_value = 0.5
_b.inputs["Emission Color"].default_value = (0.6, 0.85, 1.0, 1); _b.inputs["Emission Strength"].default_value = 0.35
ghost_m = bpy.data.materials.new("WingGhost"); ghost_m.use_nodes = True
_b = ghost_m.node_tree.nodes["Principled BSDF"]
_b.inputs["Base Color"].default_value = (0.8, 0.92, 1.0, 1); _b.inputs["Alpha"].default_value = 0.18
_b.inputs["Emission Color"].default_value = (0.7, 0.9, 1.0, 1); _b.inputs["Emission Strength"].default_value = 0.4
blood_m = mat("Blood", (0.85, 0.04, 0.06), 0.15, emit=(0.8, 0.02, 0.05), emit_strength=0.3)
egg_m = mat("Egg", (0.97, 0.95, 0.88), 0.4)
co2_m = bpy.data.materials.new("CO2"); co2_m.use_nodes = True
_b = co2_m.node_tree.nodes["Principled BSDF"]
_b.inputs["Base Color"].default_value = (0.85, 0.93, 1.0, 1); _b.inputs["Alpha"].default_value = 0.6
_b.inputs["Emission Color"].default_value = (0.7, 0.85, 1.0, 1); _b.inputs["Emission Strength"].default_value = 0.8
ring_m = glow_mat("SoundRing", (1.0, 0.85, 0.3), 3.0)
copper = mat("Copper", (0.85, 0.45, 0.25), 0.3, metal=0.85)
gold_m = mat("Gold", (1.0, 0.78, 0.2), 0.3, metal=0.85)
germ_ms = [glow_mat("GermA", (0.4, 1.0, 0.3), 1.6), glow_mat("GermB", (0.8, 0.3, 1.0), 1.6), glow_mat("GermC", (1.0, 0.5, 0.15), 1.6)]
wind_m = glow_mat("Wind", (0.92, 0.97, 1.0), 2.0)

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

# ---------------- hero mosquito (faces -Y; body centre at the group origin; feet ~0.9 r below) ----------------
HEROES = []
def mosquito(name, loc, r, rz=0.0):
    x, y, z = loc
    g = group(name, loc, rz)
    def P(dx, dy, dz):
        return (x + dx * r, y + dy * r, z + dz * r)
    parts = [sphere(name + "Thx", P(0, 0, 0), 0.36 * r, mos_body, scale=(0.9, 1.1, 0.95), sub=3),
             sphere(name + "Head", P(0, -0.48, 0.06), 0.25 * r, mos_body, sub=3)]
    ab = sphere(name + "Abd", P(0, 1.0, -0.12), 0.3 * r, mos_abd, scale=(0.8, 2.4, 0.75), sub=3)
    ab.rotation_euler = (math.radians(-8), 0, 0); parts.append(ab)
    for sx in (-1, 1):
        parts.append(sphere(name + "Eye", P(sx * 0.14, -0.58, 0.14), 0.15 * r, mos_dark, sub=2))
        parts.append(sphere(name + "EyeHi", P(sx * 0.17, -0.71, 0.2), 0.045 * r, eyew, sub=1))
        parts.append(tube(name + "Ant", [P(sx * 0.06, -0.68, 0.22), P(sx * 0.2, -0.95, 0.55), P(sx * 0.3, -1.1, 0.75)],
                          [0.025 * r, 0.02 * r, 0.012 * r], mos_leg))
        for k, dy in enumerate((-0.18, 0.0, 0.18)):
            spread = (-0.9, 0.0, 1.0)[k]
            parts.append(tube(name + "Leg", [P(sx * 0.2, dy, -0.22), P(sx * 0.95, dy + spread * 0.5, 0.35),
                                             P(sx * 1.35, dy + spread * 1.1, -0.9)], [0.04 * r, 0.03 * r, 0.02 * r], mos_leg))
    parts.append(tube(name + "Prob", [P(0, -0.66, -0.02), P(0, -0.95, -0.25), P(0, -1.12, -0.55)], [0.04 * r, 0.03 * r, 0.012 * r], mos_dark))
    wings = []
    for sx in (-1, 1):
        wp = group(name + "WingP", P(sx * 0.12, 0.05, 0.3), 0)
        wg = sphere(name + "Wing", P(sx * 0.5, 0.75, 0.38), 0.5 * r, wing_m, scale=(0.42, 1.55, 0.03), sub=2)
        wg.rotation_euler = (0, 0, sx * math.radians(-28))
        gh = []
        for a_ in (-30, 30):
            gw = sphere(name + "Ghost", P(sx * 0.5, 0.75, 0.38), 0.5 * r, ghost_m, scale=(0.42, 1.55, 0.03), sub=2)
            gw.rotation_euler = (0, 0, sx * math.radians(-28)); gh.append(gw)
        attach([wg], wp)
        gps = []
        for gw, a_ in zip(gh, (-30, 30)):
            gp = group(name + "GhostP", P(sx * 0.12, 0.05, 0.3), 0)
            attach([gw], gp); gp.rotation_euler = (0, sx * math.radians(a_), 0); gp["rz"] = 0
            gps.append(gp)
        wings.append((sx, wp, gps))
    allw = [w[1] for w in wings] + [g_ for w in wings for g_ in w[2]]
    for gp in allw:
        gp.rotation_euler = (0, 0, 0) if gp not in [g_ for w in wings for g_ in w[2]] else gp.rotation_euler
    attach(parts + allw, g)
    g["wings"] = [w[1].name for w in wings]
    g["ghosts"] = [g_.name for w in wings for g_ in w[2]]
    HEROES.append(g)
    return g

def flap(h, f0, f1, amp=35, ghosts=True):
    """Wing flap that changes on every rendered (even) frame."""
    ws = [bpy.data.objects[n] for n in h["wings"]]
    for f in range(f0 - f0 % 2, f1 + 1, 2):
        up = (f // 2) % 2 == 0
        for w in ws:
            sx = 1 if w.location.x > 0 or "R" in w.name else 1
        for k, w in enumerate(ws):
            sx = -1 if k == 0 else 1
            w.rotation_euler = (0, sx * math.radians(amp if up else -amp), 0); w.keyframe_insert("rotation_euler", frame=f)
    for w in ws:
        for fc in fcurves(w):
            for p in fc.keyframe_points:
                p.interpolation = 'CONSTANT'
    if not ghosts:
        for n in h["ghosts"]:
            bpy.data.objects[n].scale = (0.001,) * 3

# ---------------- swarm proto mesh + merged clusters ----------------
def make_proto():
    objs = [sphere("p1", (0, 0, 0), 0.36, mos_body, scale=(0.9, 1.1, 0.95), sub=1, smooth=False),
            sphere("p2", (0, -0.48, 0.06), 0.27, mos_dark, sub=1, smooth=False),
            sphere("p3", (0, 1.0, -0.12), 0.3, mos_body, scale=(0.8, 2.4, 0.75), sub=1, smooth=False)]
    for sx in (-1, 1):
        for k, dy in enumerate((-0.18, 0.0, 0.18)):
            spread = (-0.9, 0.0, 1.0)[k]
            objs.append(seg("pl", (sx * 0.2, dy, -0.2), (sx * 0.95, dy + spread * 0.5, 0.35), 0.05, mos_leg, verts=4))
            objs.append(seg("pl", (sx * 0.95, dy + spread * 0.5, 0.35), (sx * 1.35, dy + spread * 1.1, -0.9), 0.04, mos_leg, verts=4))
        w = sphere("pw", (sx * 0.55, 0.65, 0.42), 0.5, wing_m, scale=(0.5, 1.4, 0.04), sub=1, smooth=False)
        w.rotation_euler = (0, sx * 0.25, sx * math.radians(-30)); objs.append(w)
    objs.append(seg("pp", (0, -0.66, -0.02), (0, -1.15, -0.5), 0.035, mos_dark, verts=4))
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    bpy.ops.object.join()
    o = bpy.context.object
    me = o.data
    sc.collection.objects.unlink(o)
    return me
PROTO = make_proto()
PV = [v.co.copy() for v in PROTO.vertices]
PF = [tuple(p.vertices) for p in PROTO.polygons]
PM = [p.material_index for p in PROTO.polygons]

def cluster_mesh(name, n, rad, s, jit=0.3, shell=False):
    verts, faces, mi = [], [], []
    for k in range(n):
        while True:
            u = Vector((random.uniform(-1, 1), random.uniform(-1, 1), random.uniform(-1, 1)))
            if u.length <= 1:
                break
        if shell:
            u = u.normalized() * random.uniform(0.75, 1.0)
        off = Vector((u.x * rad[0], u.y * rad[1], u.z * rad[2]))
        from mathutils import Euler
        rot = Euler((random.uniform(-0.4, 0.4), random.uniform(-0.4, 0.4), random.uniform(0, 6.283))).to_matrix().to_4x4()
        M = Matrix.Translation(off) @ rot @ Matrix.Scale(s * random.uniform(1 - jit, 1 + jit), 4)
        b0 = len(verts)
        verts += [tuple(M @ v) for v in PV]
        faces += [tuple(b0 + i for i in f) for f in PF]
        mi += PM
    me = bpy.data.meshes.new(name); me.from_pydata(verts, [], faces); me.update()
    for m_ in PROTO.materials:
        me.materials.append(m_)
    me.polygons.foreach_set("material_index", mi)
    return me

def cluster(name, me, loc):
    o = bpy.data.objects.new(name, me); sc.collection.objects.link(o); o.location = loc
    return o

SW_MESH = [cluster_mesh(f"SwM{i}", 230, (3.6, 3.6, 2.0), 0.22) for i in range(4)]
MIL_MESH = [cluster_mesh(f"MilM{i}", 120, (1.2, 1.2, 0.8), 0.13) for i in range(3)]
PEN_MESH = cluster_mesh("PenM", 200, (0.26, 0.26, 0.2), 0.035, shell=True)
TON_MESH = cluster_mesh("TonM", 520, (1.15, 1.15, 1.15), 0.11, shell=True)

# ---------------- people ----------------
you, YD = person("You", (0, 0, 0), 1.0, mat("Shirt", (0.95, 0.35, 0.2), 0.6), mat("Pants", (0.2, 0.3, 0.55), 0.7),
                 skin_m, mat("Hair", (0.25, 0.14, 0.07), 0.8))
YX, YY = 0.5, 1.5

# =================== line 0: hook — a dark swarm pours over the hedge toward you ===================
HOUSE_C = (HX, HY - 4.0, 4.0)
swarm = []
for i in range(26):
    me = SW_MESH[i % 4]
    o = cluster(f"Swarm{i}", me, (0, 0, 0))
    a = i / 26 * 6.283
    # hook: high behind the garden, streaming toward you
    h0 = (random.uniform(-16, 18), random.uniform(28, 46), random.uniform(10, 20))
    h1 = (YX + random.uniform(-6, 6), random.uniform(9, 20), random.uniform(5, 10))
    # billion: from the sky down around the house
    b0 = (HX + random.uniform(-16, 16), HY + random.uniform(-6, 14), random.uniform(22, 32))
    rr = random.uniform(5, 11)
    b1 = (HX + rr * math.cos(a) * 1.3, HY - 1 + rr * math.sin(a) * 0.9, random.uniform(2.5, 9.5))
    b2 = (b1[0] + random.uniform(-2, 2), b1[1] + random.uniform(-2, 2), b1[2] + random.uniform(-1, 1))
    # twist: around you
    t1 = (YX + random.uniform(-9, 9), YY + random.uniform(5, 14), random.uniform(1.5, 7))
    # fan: in front of the fan, then blown far away
    f1 = (random.uniform(-6.0, 0.5), random.uniform(2.0, 7.0), random.uniform(0.8, 4.0))
    f2 = (f1[0] - random.uniform(32, 46), f1[1] + random.uniform(-6, 6), f1[2] + random.uniform(4, 12))
    # finale: back again from the left
    e1 = (random.uniform(-17, -11), random.uniform(1, 12), random.uniform(2, 8))
    e2 = (e1[0] + random.uniform(7, 9), e1[1], e1[2] - random.uniform(0, 1.5))
    keys = [(0, h0), (S[1] - 1, h1), (S[8], b0), (S[9] - 1, b1), (S[10], b1), (S[12] - 1, b2 if False else t1),
            (S[14], f1), (W(14, 0.3), f1), (E(14) - 1, f2), (S[17], e1), (FRAMES - 1, e2)]
    keys[5] = (S[11], t1)
    for f, p in keys:
        o.location = p; o.keyframe_insert("location", frame=f)
    for fc in fcurves(o):
        if fc.data_path == "location":
            for p in fc.keyframe_points:
                if int(p.co[0]) in (S[1] - 1, S[9] - 1, E(14) - 1, S[10] - 0, S[12] - 1):
                    p.interpolation = 'CONSTANT'
    # hard jumps at the cuts: make the segment ending at each cut constant
    for fc in fcurves(o):
        if fc.data_path == "location":
            pts = fc.keyframe_points
            for k in range(len(pts) - 1):
                if int(round(pts[k + 1].co[0])) in (S[8], S[11], S[14], S[17]):
                    pts[k].interpolation = 'CONSTANT'
    o.rotation_euler = (0, 0, 0); o.keyframe_insert("rotation_euler", frame=0)
    o.rotation_euler = (random.uniform(-0.3, 0.3), random.uniform(-0.3, 0.3), random.choice((-1, 1)) * random.uniform(4, 8))
    o.keyframe_insert("rotation_euler", frame=FRAMES)
    for fc in fcurves(o):
        if fc.data_path == "rotation_euler":
            for p in fc.keyframe_points:
                p.interpolation = 'LINEAR'
    # tumble when blown away
    jitter(o, 0.35, 5.0)
    vis(o, [(0, S[1]), (S[8], S[9]), (S[10], S[12]), (S[14], E(14)), (S[17], FRAMES)])
    swarm.append(o)

# =================== lines 1-2: one mosquito on a kitchen scale, then blood -> eggs ===================
T = 0.85
wood = mat("Wood", (0.75, 0.5, 0.28), 0.7)
TX, TY = -1.5, -0.6
tbl = [box("TableTop", (TX, TY, T - 0.03), (1.3, 0.75, 0.06), wood, bevel=0.01)]
for dx in (-0.58, 0.58):
    for dy in (-0.3, 0.3):
        tbl.append(box("TableLeg", (TX + dx, TY + dy, (T - 0.06) / 2), (0.06, 0.06, T - 0.06), wood))
scale_m = mat("ScaleBody", (0.97, 0.97, 0.98), 0.4)
plat_m = mat("ScalePlat", (0.75, 0.78, 0.82), 0.25, metal=0.6)
lcd_m = mat("LCD", (0.6, 0.9, 0.62), 0.4, emit=(0.5, 0.9, 0.55), emit_strength=0.8)
lcd_ink = mat("LCDInk", (0.02, 0.06, 0.03), 0.5)
PT = T + 0.0925
SA = (TX - 0.25, TY + 0.02)
tbl += [box("ScaleBase", (SA[0], SA[1], T + 0.035), (0.46, 0.46, 0.07), scale_m, bevel=0.012),
        box("ScalePlat", (SA[0], SA[1], T + 0.085), (0.42, 0.42, 0.015), plat_m, bevel=0.004),
        box("LCD", (SA[0], SA[1] - 0.235, T + 0.035), (0.3, 0.02, 0.07), lcd_m)]
for o in tbl:
    vis(o, [(S[1], S[3])])
r0 = text("Read0", "0.000 g", (SA[0], SA[1] - 0.247, T + 0.035), 0.05, lcd_ink); vis(r0, [(S[1], S[1] + 10)])
r1 = text("Read1", "0.0025 g", (SA[0], SA[1] - 0.247, T + 0.035), 0.05, lcd_ink); vis(r1, [(S[1] + 10, S[3])])
R1 = 0.12
H1 = mosquito("H1", (SA[0], SA[1], PT + 0.9 * R1), R1, math.radians(20))
vis(H1, [(S[1], S[3])])
key_loc(H1, [(S[1], (SA[0] + 0.3, SA[1] - 0.2, PT + 0.45)), (S[1] + 9, (SA[0], SA[1], PT + 0.9 * R1))])
flap(H1, S[1], S[1] + 9, 35)
for n in H1["wings"]:
    w = bpy.data.objects[n]; w.rotation_euler = (0, 0, 0); w.keyframe_insert("rotation_euler", frame=S[1] + 10)
# line 2: a blood drop pops above her, eggs appear beside the scale
drop = sphere("Drop", (SA[0] + 0.0, SA[1] - 0.02, PT + 0.42), 0.06, blood_m, scale=(1, 1, 1.3), sub=3)
tip = cyl("DropTip", (SA[0], SA[1] - 0.02, PT + 0.5), 0.045, 0.08, blood_m, r2=0.0, verts=16)
for o in (drop, tip):
    pop(o, S[2] + 2, 5, S[3])
arrow = box("Arrow", (SA[0] + 0.28, SA[1] - 0.05, PT + 0.33), (0.2, 0.01, 0.025), white_lab)
pop(arrow, W(2, 0.45), 4, S[3])
for k in range(7):
    e = sphere("Egg", (SA[0] + 0.48 + (k % 4) * 0.045, SA[1] - 0.08 + (k // 4) * 0.05, T + 0.02), 0.028, egg_m, scale=(0.6, 1.2, 0.6), sub=2)
    pop(e, W(2, 0.5) + k, 4, S[3])

# =================== line 3: your breath travels 20 m to a mosquito ===================
BYX, BMX, BLY = -5.5, 6.5, 2.0
H2 = mosquito("H2", (BMX, BLY, 1.9), 0.85, math.radians(-90))
vis(H2, [(S[3], S[4])])
key_loc(H2, [(S[3], (BMX, BLY, 1.9)), (W(3, 0.6), (BMX, BLY, 1.9)), (E(3) - 1, (BMX - 1.8, BLY, 1.8))])
jitter(H2, 0.06, 4.0)
flap(H2, S[3], E(3), 30)
mouth = (BYX + 0.3, BLY, 1.62)
for k in range(12):
    t0 = S[3] + int(k * (E(3) - S[3]) / 14)
    p0 = mouth; p1 = (BMX - 0.8, BLY + random.uniform(-0.3, 0.3), 1.6 + random.uniform(-0.3, 0.4))
    pf = sphere("Puff", p0, 0.28, co2_m, sub=2)
    key_loc(pf, [(t0, p0), (t0 + 22, p1)])
    keyscale(pf, [(0, 0.001), (t0 - 1, 0.001), (t0, 0.4), (t0 + 22, 1.6), (t0 + 23, 0.001)])
for k in range(13):
    d = box("Dash", (BYX + 0.6 + k * 0.9, BLY - 0.9, 0.04), (0.5, 0.12, 0.04), white_lab)
    pop(d, S[3] + 1 + k, 3, S[4])
for xx in (BYX + 0.3, BMX - 0.3):
    pop(box("Tick", (xx, BLY - 0.9, 0.25), (0.08, 0.08, 0.5), white_lab), S[3] + 1, 3, S[4])

# =================== line 4: wings beat 500 times a second (close-up) ===================
WGX, WGY, WGZ = 2.0, 2.5, 1.7
H3 = mosquito("H3", (WGX, WGY, WGZ), 0.75, math.radians(25))
vis(H3, [(S[4], S[5])])
flap(H3, S[4], E(4), 40)
jitter(H3, 0.05, 3.0)
for k in range(3):
    rg = bpy.ops.mesh.primitive_torus_add(major_radius=1.0, minor_radius=0.03, location=(WGX, WGY + 0.4, WGZ + 0.4))
    rg = bpy.context.object; rg.data.materials.append(ring_m); rg.rotation_euler = (math.radians(70), 0, 0)
    f = S[4] + 3 + k * 9
    keyscale(rg, [(0, 0.001), (f - 1, 0.001), (f, 0.3), (f + 12, 1.3), (f + 13, 0.001)])

# =================== line 5: the whine in your ear ===================
H4 = mosquito("H4", (YX + 0.55, YY - 0.05, 1.82), 0.2, math.radians(-75))
vis(H4, [(S[5], S[6])])
flap(H4, S[5], E(5), 35)
jitter(H4, 0.04, 3.0)
for k in range(4):
    bpy.ops.mesh.primitive_torus_add(major_radius=0.3, minor_radius=0.012, location=(YX + 0.55, YY - 0.05, 1.82))
    rg = bpy.context.object; rg.data.materials.append(ring_m); rg.rotation_euler = (0, math.radians(90), 0)
    f = S[5] + 1 + k * 6
    keyscale(rg, [(0, 0.001), (f - 1, 0.001), (f, 0.3), (f + 9, 1.6), (f + 10, 0.001)])

# =================== line 6: a thousand mosquitoes balance one penny ===================
BX, BY_ = -3.4, 1.6
bal = []
bal.append(cyl("BalBase", (BX, BY_, 0.05), 0.45, 0.1, gold_m, verts=24))
bal.append(cyl("BalPost", (BX, BY_, 0.75), 0.05, 1.4, gold_m, verts=12))
bal.append(box("BalBeam", (BX, BY_, 1.45), (2.2, 0.08, 0.08), gold_m))
for sx in (-1, 1):
    bal.append(seg("BalStr", (BX + sx * 1.0, BY_, 1.45), (BX + sx * 1.0, BY_, 0.75), 0.012, gold_m))
    bal.append(cyl("BalPan", (BX + sx * 1.0, BY_, 0.72), 0.42, 0.05, gold_m, verts=24))
for o in bal:
    vis(o, [(S[6], S[7])])
pball = cluster("PennyBall", PEN_MESH, (BX - 1.0, BY_, 0.98))
inner = sphere("PennyBallIn", (BX - 1.0, BY_, 0.98), 0.2, mos_dark, sub=2)
pen = cyl("Penny", (BX + 1.0, BY_, 0.8), 0.32, 0.06, copper, verts=32)
pen.rotation_euler = (math.radians(-60), 0, 0)
pen2 = cyl("PennyRim", (BX + 1.0, BY_ - 0.004, 0.8), 0.26, 0.065, mat("Copper2", (0.7, 0.35, 0.18), 0.35, metal=0.85), verts=32)
pen2.rotation_euler = (math.radians(-60), 0, 0)
for o in (pball, inner, pen, pen2):
    vis(o, [(S[6], S[7])])
pen.location = (BX + 1.0, BY_, 0.92)
pen2.location = (BX + 1.0, BY_ - 0.004, 0.92)
key_loc(pen, [(S[6], (BX + 1.0, BY_, 2.6)), (W(6, 0.4), (BX + 1.0, BY_, 0.98))])
key_loc(pen2, [(S[6], (BX + 1.0, BY_ - 0.004, 2.6)), (W(6, 0.4), (BX + 1.0, BY_ - 0.004, 0.98))])
pball.rotation_euler = (0, 0, 0); pball.keyframe_insert("rotation_euler", frame=S[6])
pball.rotation_euler = (0, 0, 3); pball.keyframe_insert("rotation_euler", frame=E(6))

# =================== line 7: a million — a buzzing cloud over the pool ===================
for i in range(9):
    c = (POX + random.uniform(-1.6, 1.6), POY + random.uniform(-1.0, 1.0), 2.0 + random.uniform(-0.4, 1.2))
    o = cluster(f"Mil{i}", MIL_MESH[i % 3], c)
    key_loc(o, [(S[7], (c[0] + 3.5, c[1] - 1, c[2] + 2)), (W(7, 0.4), c), (E(7), (c[0] - 0.5, c[1], c[2] + 0.2))])
    o.rotation_euler = (0, 0, 0); o.keyframe_insert("rotation_euler", frame=S[7])
    o.rotation_euler = (0, 0, random.choice((-2.5, 2.5))); o.keyframe_insert("rotation_euler", frame=E(7))
    jitter(o, 0.2, 4.0)
    vis(o, [(S[7], S[8])])

# =================== line 9: 2.5 t of mosquitoes vs a pickup truck on a giant seesaw ===================
PX, PY, PZ = 10.0, 3.0, 1.4
steel = mat("Steel", (0.95, 0.75, 0.2), 0.5)
pivot = cyl("Pivot", (PX, PY, 0.65), 0.95, 1.3, mat("PivotM", (0.3, 0.32, 0.38), 0.6), verts=3)
pivot.rotation_mode = 'ZXY'; pivot.rotation_euler = (math.radians(90), 0, math.radians(90))
plank = group("Plank", (PX, PY, PZ))
pl = box("PlankBoard", (PX, PY, PZ), (11.0, 2.6, 0.22), steel, bevel=0.04)
tball = cluster("TonBall", TON_MESH, (PX - 3.4, PY, PZ + 1.3))
tin = sphere("TonBallIn", (PX - 3.4, PY, PZ + 1.3), 1.0, mos_dark, sub=3)
attach([pl, tball, tin], plank)
vis(pivot, [(S[9], S[10])], tuple(pivot.scale)); vis(plank, [(S[9], S[10])])
TILT = math.radians(13)
for f, a in [(S[9], TILT), (S[9] + 8, TILT), (S[9] + 14, math.radians(-4)), (S[9] + 18, math.radians(2)), (S[9] + 22, 0)]:
    plank.rotation_euler = (0, a, 0); plank.keyframe_insert("rotation_euler", frame=f)
pk_m = mat("Pickup", (0.15, 0.45, 0.85), 0.35)
tyre_m = mat("Tyre", (0.06, 0.06, 0.06), 0.9)
glass = mat("TGlass", (0.25, 0.35, 0.45), 0.1)
TRX = PX + 3.0
z0 = PZ + 0.11
truck = group("Truck", (TRX, PY, z0))
tp = [box("TBody", (TRX, PY, z0 + 0.75), (4.4, 1.8, 0.6), pk_m, bevel=0.08),
      box("TCab", (TRX + 0.55, PY, z0 + 1.4), (1.7, 1.7, 0.8), pk_m, bevel=0.12),
      box("TWin", (TRX + 1.42, PY, z0 + 1.45), (0.04, 1.5, 0.55), glass),
      box("TWinS", (TRX + 0.55, PY - 0.86, z0 + 1.45), (1.4, 0.04, 0.5), glass),
      box("TBed", (TRX - 1.25, PY, z0 + 1.1), (1.8, 1.7, 0.12), mat("BedM", (0.2, 0.2, 0.22), 0.6))]
for dx in (-1.4, 1.4):
    for dy in (-0.9, 0.9):
        tp.append(cyl("TWheel", (TRX + dx, PY + dy, z0 + 0.45), 0.45, 0.32, tyre_m, rot=(math.radians(90), 0, 0), verts=16))
attach(tp, truck)
f0 = S[9] + 6
upz = z0 + 3.0 * math.sin(TILT)
key_loc(truck, [(S[9], (TRX, PY, 12.0)), (f0 + 2, (TRX, PY, upz)), (S[9] + 14, (TRX, PY, z0 - 3.0 * math.sin(math.radians(4)))),
                (S[9] + 18, (TRX, PY, z0 + 3.0 * math.sin(math.radians(2)))), (S[9] + 22, (TRX, PY, z0))])
for f, a in [(S[9], 0.3), (f0 + 2, -TILT), (S[9] + 14, math.radians(4)), (S[9] + 18, math.radians(-2)), (S[9] + 22, 0)]:
    truck.rotation_euler = (0, a, 0); truck.keyframe_insert("rotation_euler", frame=f)
vis(truck, [(S[9], S[10])])

# =================== line 10: the sky goes dark ===================
for f, e_, b_ in [(0, 4.2, 0.85), (S[10] + 1, 4.2, 0.85), (S[10] + 10, 0.55, 0.12), (S[12] - 1, 0.55, 0.12), (S[12], 4.2, 0.85)]:
    sun.data.energy = e_; sun.data.keyframe_insert("energy", frame=f)
    bg.inputs["Strength"].default_value = b_; bg.inputs["Strength"].keyframe_insert("default_value", frame=f)
for o in [o for o in bpy.data.objects if o.name.startswith("Cloud")]:
    o.data.materials[0] = o.data.materials[0]
cloud_m.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"].keyframe_insert("default_value", frame=S[10] + 1)
cloud_m.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"].default_value = 0.0
cloud_m.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"].keyframe_insert("default_value", frame=S[10] + 10)
cloud_m.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"].keyframe_insert("default_value", frame=S[12] - 1)
cloud_m.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"].default_value = 0.4
cloud_m.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"].keyframe_insert("default_value", frame=S[12])
# warm window lights come on in the dark
lamp_m = glow_mat("WinLamp", (1.0, 0.8, 0.4), 2.5)
for x in (-2.6, 0.9, 2.6):
    for z in (1.4, 3.5):
        o = box("WinLit", (HX + x, fy - 0.075, z), (0.85, 0.02, 1.0), lamp_m)
        vis(o, [(S[10] + 6, S[12])])

# =================== lines 12-13: race — you walk, the mosquito falls behind ===================
RY_YOU, RY_MOS, RX0 = 1.0, 2.6, -4.0
H5 = mosquito("H5", (RX0, RY_MOS, 1.3), 0.45, math.radians(-90))
vis(H5, [(S[12], S[14])])
key_loc(H5, [(S[12], (RX0, RY_MOS, 1.3)), (E(13), (RX0 + 3.4, RY_MOS, 1.3))])
for fc in fcurves(H5):
    for p in fc.keyframe_points:
        p.interpolation = 'LINEAR'
jitter(H5, 0.05, 3.0)
flap(H5, S[12], E(13), 30)
lane_m = mat("Lane", (0.95, 0.95, 0.92), 0.6)
for yy in (RY_YOU - 0.7, (RY_YOU + RY_MOS) / 2, RY_MOS + 0.7):
    o = box("LaneLine", (1.0, yy, 0.03), (12.0, 0.08, 0.04), lane_m); vis(o, [(S[12], S[14])])
o = box("StartLine", (RX0, (RY_YOU + RY_MOS) / 2, 0.035), (0.15, 3.0, 0.05), lane_m); vis(o, [(S[12], S[14])])
fl = []
fl.append(seg("FlagPole", (5.6, RY_YOU - 0.8, 0), (5.6, RY_YOU - 0.8, 2.2), 0.04, lane_m))
fl.append(stripe_mat and box("Flag", (5.95, RY_YOU - 0.8, 1.95), (0.7, 0.03, 0.45), stripe_mat("Check", (0.02, 0.02, 0.02), (1, 1, 1), axis="X", freq=18, thresh=0.0)))
for o in fl:
    vis(o, [(S[12], S[14])])

# =================== line 14: a box fan blows them away ===================
FX, FY, FZ = 3.4, 3.6, 1.7
fan_body = mat("FanBody", (0.95, 0.95, 0.97), 0.4)
fan_blue = mat("FanBlue", (0.2, 0.55, 0.95), 0.4)
fan = group("Fan", (FX, FY, FZ))
fp_ = [box("FanFoot", (FX, FY, 0.06), (1.2, 1.4, 0.12), fan_body, bevel=0.04),
       seg("FanStem", (FX, FY, 0.1), (FX, FY, FZ - 1.2), 0.08, fan_body)]
bpy.ops.mesh.primitive_torus_add(major_radius=1.25, minor_radius=0.12, location=(FX, FY, FZ))
ring = bpy.context.object; ring.rotation_euler = (0, math.radians(90), 0); ring.data.materials.append(fan_blue); fp_.append(ring)
for k in range(8):
    a = k / 8 * math.pi
    g_ = boxc("FanGrill", (FX - 0.18, FY, FZ), (0.02, 2.4, 0.03), fan_body); g_.rotation_euler = (a, 0, 0); fp_.append(g_)
fp_.append(sphere("FanHub", (FX - 0.05, FY, FZ), 0.22, fan_blue, sub=2))
bl = []
for k in range(3):
    ang = k * 2.094
    b = boxc("Blade", (FX - 0.1, FY - 0.55 * math.sin(ang), FZ + 0.55 * math.cos(ang)), (0.05, 0.45, 0.95), fan_blue)
    b.rotation_euler = (ang, 0, 0)
    bl.append(b)
bpy.ops.object.select_all(action='DESELECT')
for b in bl:
    b.select_set(True)
bpy.context.view_layer.objects.active = bl[0]
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
bpy.ops.object.join()
blades = bpy.context.object; blades.name = "Blades"
blades.data.transform(Matrix.Translation((-FX, -FY, -FZ)))
blades.location = (FX, FY, FZ)
attach(fp_, fan)
blades.rotation_euler = (0, 0, 0); blades.keyframe_insert("rotation_euler", frame=S[14])
blades.rotation_euler = (0, 0, 0); blades.keyframe_insert("rotation_euler", frame=S[14] + 3)
blades.rotation_euler = (math.radians(-170) * (FRAMES - S[14] - 3) / 2, 0, 0); blades.keyframe_insert("rotation_euler", frame=FRAMES)
for fc in fcurves(blades):
    for p in fc.keyframe_points:
        p.interpolation = 'LINEAR'
vis(fan, [(S[14], E(14)), (S[17], FRAMES)])
vis(blades, [(S[14], E(14)), (S[17], FRAMES)])
for k in range(22):
    y_ = FY + random.uniform(-1.6, 1.6) + 0.0; z_ = FZ + random.uniform(-1.1, 1.3)
    st = box("Wind", (FX - 1.0, y_, z_), (1.4, 0.03, 0.03), wind_m)
    t0 = S[14] + 3 + (k % 7) * 3
    xs = FX - 1.0
    key_loc(st, [(t0, (xs, y_, z_)), (t0 + 10, (xs - 12, y_, z_ + 0.3))])
    keyscale(st, [(0, 0.001), (t0 - 1, 0.001), (t0, 1.0), (t0 + 10, 1.0), (t0 + 11, 0.001)])
    if t0 + 22 < E(14):
        key_loc(st, [(t0 + 11, (xs, y_, z_)), (t0 + 21, (xs - 12, y_, z_ + 0.3))])
        keyscale(st, [(t0 + 11, 0.001), (t0 + 12, 1.0), (t0 + 21, 1.0), (t0 + 22, 0.001)])

# =================== lines 15-16: #1 deadliest animal, the germs it carries ===================
PDX, PDY = 0.5, 2.2
pod = [box("Podium", (PDX, PDY, 0.6), (1.6, 1.6, 1.2), gold_m, bevel=0.05),
       text("PodNum", "1", (PDX, PDY - 0.82, 0.62), 0.8, white_lab, extrude=0.04)]
for o in pod:
    vis(o, [(S[15], S[17])])
H6 = mosquito("H6", (PDX, PDY, 1.2 + 0.9 * 0.55), 0.55, math.radians(15))
vis(H6, [(S[15], S[17])])
flap(H6, S[15], E(16), 25)
crown = cyl("Crown", (PDX, PDY - 0.28, 1.2 + 0.9 * 0.55 + 0.33), 0.16, 0.16, gold_m, r2=0.2, verts=6)
vis(crown, [(S[15] + 4, S[17])])
for k in range(10):
    gm = germ_ms[k % 3]
    a0 = k / 10 * 6.283
    rad = 1.25 + 0.25 * (k % 2)
    zc = 1.95 + 0.45 * math.sin(a0 * 2)
    gr = group("Germ", (PDX + rad * math.cos(a0), PDY + rad * math.sin(a0) * 0.7, zc))
    c = gr.location
    gp_ = [sphere("GermCore", tuple(c), 0.16, gm, sub=2)]
    for j in range(10):
        d = Vector((random.gauss(0, 1), random.gauss(0, 1), random.gauss(0, 1))).normalized()
        gp_.append(sphere("GermKnob", tuple(c + d * 0.17), 0.05, gm, sub=1))
    attach(gp_, gr)
    keys = []
    for s_ in range(6):
        f = S[16] + int(s_ * (E(16) - S[16]) / 5)
        a = a0 + s_ * 0.5
        keys.append((f, (PDX + rad * math.cos(a), PDY + rad * math.sin(a) * 0.7, zc)))
    key_loc(gr, keys)
    vis(gr, [(S[16] + 2 + k, S[17])])

# =================== you: positions per line (hard cuts) ===================
jumps(you, [(0, (YX, YY, 0)), (S[1], (YX, 30, 0)), (S[3], (BYX, BLY, 0)), (S[4], (YX, 40, 0)), (S[5], (YX, YY, 0)),
            (S[6], (YX, 40, 0)), (S[10], (YX + 1.6, fy - 3.4, 0)), (S[11], (YX, YY, 0)), (S[12], (RX0, RY_YOU, 0)),
            (S[14], (YX, 40, 0)), (S[17], (1.6, 2.6, 0))])
key_loc(you, [(S[12] + 1, (RX0, RY_YOU, 0)), (E(13) - 1, (RX0 + 8.5, RY_YOU, 0))])
for fc in fcurves(you):
    if fc.data_path == "location":
        for p in fc.keyframe_points:
            f_ = int(round(p.co[0]))
            p.interpolation = 'LINEAR' if S[12] + 1 <= f_ < E(13) - 1 else 'CONSTANT'
jumps(you, [(0, (0, 0, 0)), (S[3], (0, 0, math.radians(90))), (S[4], (0, 0, 0)), (S[12], (0, 0, math.radians(90))),
            (S[14], (0, 0, 0)), (S[17], (0, 0, math.radians(-25)))], "rotation_euler")
you.keyframe_insert("rotation_euler", frame=E(13))
vis(you, [(0, S[1]), (S[3], S[4]), (S[5], S[6]), (S[10], S[14]), (S[17], FRAMES)])
# walking legs + swinging arms during the race, swat at the ear, arms up at the end
for f in range(S[12], E(13), 4):
    for k, lg in enumerate(YD["legs"]):
        a = 0.45 * (1 if ((f - S[12]) // 4 + k) % 2 else -1)
        lg.rotation_euler = (a, 0, 0); lg.keyframe_insert("rotation_euler", frame=f)
    for k, ag in enumerate(YD["arms"]):
        a = 0.5 * (-1 if ((f - S[12]) // 4 + k) % 2 else 1)
        ag.rotation_euler = (a, 0, 0); ag.keyframe_insert("rotation_euler", frame=f)
for ag in YD["arms"] + YD["legs"]:
    ag.rotation_euler = (0, 0, 0); ag.keyframe_insert("rotation_euler", frame=E(13))
    ag.keyframe_insert("rotation_euler", frame=S[12] - 1)
ar = YD["arms"][1]
keyrot(ar, [(S[5], (0, 0, 0)), (W(5, 0.45), (0, 0, 0)), (W(5, 0.7), (0, math.radians(-150), 0)), (E(5), (0, math.radians(-150), 0)), (S[6], (0, 0, 0))])
for k, ag in enumerate(YD["arms"]):
    sx = -1 if k == 0 else 1
    keyrot(ag, [(S[17] - 1, (0, 0, 0)), (S[17] + 4, (0, sx * math.radians(150), 0)), (FRAMES, (0, sx * math.radians(140), 0))])
    keyrot(ag, [(S[11] - 1, (0, 0, 0)), (S[11] + 4, (0, sx * math.radians(130), 0)), (E(11) - 1, (0, sx * math.radians(130), 0)), (E(11), (0, 0, 0))])
    keyrot(ag, [(0, (0, 0, 0)), (6, (0, sx * math.radians(120), 0)), (S[1] - 1, (0, sx * math.radians(120), 0)), (S[1], (0, 0, 0))])

# ---------------- views (camera, subject) per line; subject sits in the lower third ----------------
V, V2 = {}, {}
V[0] = ((-1.0, -8.5, 2.0), (YX, YY, 1.1));                 V2[0] = ((1.8, -6.6, 2.0), (YX, YY, 1.1))
V[1] = ((SA[0] + 0.35, SA[1] - 1.05, PT + 0.4), (SA[0], SA[1], PT + 0.08)); V2[1] = ((SA[0] - 0.2, SA[1] - 0.85, PT + 0.4), (SA[0], SA[1], PT + 0.08))
V[2] = ((SA[0] - 0.5, SA[1] - 1.2, PT + 0.4), (SA[0] + 0.2, SA[1], PT + 0.12)); V2[2] = ((SA[0] + 0.5, SA[1] - 1.1, PT + 0.4), (SA[0] + 0.25, SA[1], PT + 0.12))
V[3] = ((0.5, -17.5, 3.0), (0.5, BLY, 1.2));               V2[3] = ((1.5, -16.0, 3.0), (0.5, BLY, 1.2))
V[4] = ((WGX + 1.6, WGY - 3.6, 2.0), (WGX, WGY + 0.3, WGZ)); V2[4] = ((WGX - 1.2, WGY - 3.4, 2.0), (WGX, WGY + 0.3, WGZ))
V[5] = ((YX + 1.7, YY - 1.6, 1.9), (YX + 0.3, YY, 1.55));  V2[5] = ((YX + 1.1, YY - 2.0, 1.9), (YX + 0.3, YY, 1.55))
V[6] = ((BX + 0.8, BY_ - 4.2, 1.6), (BX, BY_, 0.9));         V2[6] = ((BX - 0.6, BY_ - 4.0, 1.6), (BX, BY_, 0.9))
V[7] = ((POX + 5.0, POY - 10.5, 3.0), (POX, POY, 2.0));    V2[7] = ((POX + 3.0, POY - 9.5, 3.0), (POX, POY, 2.0))
V[8] = ((HX - 6.0, -24.0, 8.0), (HX, HY - 4.0, 3.0));      V2[8] = ((HX + 3.0, -22.0, 8.0), (HX, HY - 4.0, 3.0))
V[9] = ((PX + 0.6, PY - 11.5, 3.0), (PX + 0.2, PY, 1.8));  V2[9] = ((PX - 0.8, PY - 11.0, 3.0), (PX + 0.2, PY, 1.8))
V[10] = ((HX + 6.0, -9.0, 4.0), (HX + 1.0, HY - 3.5, 2.0)); V2[10] = ((HX + 2.0, -8.0, 4.0), (HX + 1.0, HY - 3.5, 2.0))
V[11] = ((YX - 1.2, YY - 4.8, 2.0), (YX, YY, 1.1));        V2[11] = ((YX + 1.0, YY - 4.4, 2.0), (YX, YY, 1.1))
V[12] = ((-2.4, -6.4, 2.0), (-1.8, 1.8, 1.0));             V2[12] = ((-0.6, -6.4, 2.0), (-0.2, 1.8, 1.0))
V[13] = ((0.6, -6.6, 2.0), (1.0, 1.8, 1.0));               V2[13] = ((2.2, -6.6, 2.0), (2.0, 1.8, 1.0))
V[14] = ((0.6, -9.5, 3.0), (0.4, 3.8, 1.7));              V2[14] = ((-0.8, -9.5, 3.0), (-0.4, 3.8, 1.8))
V[15] = ((PDX + 1.6, PDY - 4.4, 2.0), (PDX, PDY, 1.6));    V2[15] = ((PDX + 0.6, PDY - 3.8, 2.0), (PDX, PDY, 1.7))
V[16] = ((PDX - 1.7, PDY - 4.3, 2.0), (PDX, PDY, 1.7));    V2[16] = ((PDX - 0.7, PDY - 3.7, 2.0), (PDX, PDY, 1.8))
V[17] = ((1.0, -8.6, 2.5), (1.6, 2.8, 1.2));               V2[17] = ((-1.5, -10.0, 3.0), (0.6, 2.8, 1.2))

def LB(i, name, body, m_, size=None, f_in=None, f_out=None, Dk=0.55, end=False, v=0.26, u=0.0):
    view = V2[i] if end else V[i]
    cl = Vector(CL(view)); D = (Vector(view[1]) - cl).length * Dk
    s_ = 0.85 * fit(body, D, size if size else 1e9)
    return label(name, body, view, D, v, s_, m_, (S[i] + 3) if f_in is None else f_in,
                 E(i) if f_out is None else f_out, u)
LB(0, "L0", "1 BILLION?!", red_lab)
LB(1, "L1", "2.5 mg", lab_m, size=0.05, v=0.3)
LB(2, "L2", "ONLY FEMALES BITE", pink_lab)
LB(3, "L3", "20 METERS", white_lab, Dk=0.4)
LB(4, "L4", "500x A SECOND", lab_m)
LB(5, "L5", "BZZZZZ!", lab_m)
LB(6, "L6", "1,000 = 1 PENNY", lab_m)
LB(7, "L7", "1,000,000 = 2.5 kg", lab_m, Dk=0.45)
LB(8, "L8", "1,000,000,000", red_lab, Dk=0.4)
LB(9, "L9", "2.5 TONS", lab_m, Dk=0.45)
LB(10, "L10", "LIGHTS OUT", white_lab, f_in=S[10] + 8, Dk=0.45)
LB(11, "L11", "THE TWIST...", lab_m)
LB(12, "L12", "YOU: 5 km/h", green_lab)
LB(13, "L13", "MOSQUITO: 2 km/h", red_lab, end=True)
LB(14, "L14", "BLOWN AWAY!", blue_lab, f_in=W(14, 0.3))
LB(15, "L15", "#1 DEADLIEST ANIMAL", red_lab)
LB(16, "L16", "MALARIA, DENGUE, ZIKA", green_lab)
LB(17, "L17", "RUN OR FAN?", lab_m, end=True, f_in=S[17] + 6, Dk=0.45)

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
