# Day 22 — What if 1 billion bees made honey just for you?  Build: python3 episodes/022-billion-bees/scene.py
# Reference style: base (helpers, lawn/soil, house, garden, camera helpers) copied from episodes/018-billion-ants (ref style of 003-lift-million-ref)
import bpy, math, random, os, json
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
random.seed(22)
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
# Day 22 — What if 1 billion bees made honey just for you?
# Facts used: a worker honeybee weighs ~0.1 g (about 90-120 mg) and makes ~1/12 teaspoon of honey in its life
#   (National Honey Board / USDA figure), visiting thousands of flowers (50-100 per foraging trip);
#   1/12 tsp ~ 0.41 ml;  1,000 bees -> ~0.41 L ~ one big jar (~0.6 kg);  1e6 -> ~410 L > a bathtub (150-300 L);
#   1e9 x 0.1 g = 100 t of bees ~ a blue whale (100-150 t);  a strong summer colony has ~50,000 bees -> 20,000 hives;
#   1e9 x 0.41 ml ~ 410,000 L ~ six backyard pools (~50-75 m3 each);  1e9/12 tsp = 83 million tsp ->
#   one teaspoon a day for ~228,000 years;  sealed honey keeps for millennia (edible honey found in ancient tombs).
# Cartoon scale: bees are drawn far bigger than life so they read on a phone.
# =====================================================================================

for o in bpy.data.objects:
    if o.name.startswith("Bush"):
        o.scale = (0.001,) * 3

# ---------------- materials ----------------
honey_m = mat("Honey", (1.0, 0.6, 0.06), 0.12, emit=(1.0, 0.5, 0.04), emit_strength=0.45)
honey_glow = glow_mat("HoneyGlow", (1.0, 0.7, 0.15), 4.0)
bee_y = mat("BeeYellow", (1.0, 0.75, 0.08), 0.45)
bee_k = mat("BeeBlack", (0.05, 0.04, 0.03), 0.5)
wing_m = mat("Wing", (0.85, 0.95, 1.0), 0.1, emit=(0.8, 0.92, 1.0), emit_strength=0.6)
fuzz_m = mat("Fuzz", (0.95, 0.62, 0.15), 0.8)
silver_m = mat("Silver", (0.8, 0.82, 0.86), 0.2, metal=0.9)
ghost_m = mat("Ghost", (0.8, 0.8, 0.82), 0.6)
petal_ms = [mat("Pet%d" % k, c, 0.5) for k, c in enumerate([(1, 0.35, 0.55), (0.95, 0.9, 0.95), (0.6, 0.4, 1.0), (1.0, 0.55, 0.15)])]
center_m = mat("FlCenter", (1.0, 0.8, 0.1), 0.5)
stem_m = mat("Stem", (0.2, 0.6, 0.18), 0.7)
hive_w = mat("HiveW", (0.97, 0.95, 0.88), 0.6)
hive_y = mat("HiveY", (1.0, 0.82, 0.3), 0.6)
hive_l = mat("HiveLid", (0.35, 0.45, 0.6), 0.5)
whale_m = mat("Whale", (0.25, 0.45, 0.78), 0.5)
whale_b = mat("WhaleBelly", (0.8, 0.88, 0.95), 0.6)
tub_m = mat("Tub", (0.98, 0.98, 1.0), 0.25)
crust_m = mat("Crust", (0.65, 0.38, 0.15), 0.8)
bread_m = mat("Bread", (0.98, 0.85, 0.6), 0.85)
plate_m = mat("Plate", (0.95, 0.95, 0.97), 0.3)
cal_m = mat("Calendar", (0.98, 0.98, 0.97), 0.6)
calred_m = mat("CalRed", (0.9, 0.15, 0.12), 0.5)
ink_m = mat("Ink", (0.08, 0.08, 0.1), 0.5)
clay_m = mat("Clay", (0.75, 0.42, 0.22), 0.8)
clay_dk = mat("ClayDk", (0.5, 0.26, 0.12), 0.8)
wood = mat("Wood", (0.75, 0.5, 0.28), 0.7)
conf_ms = [glow_mat("Cf%d" % k, c, 2.0) for k, c in enumerate([(1, 0.85, 0.2), (0.3, 0.7, 1.0), (1, 0.4, 0.7), (0.4, 1, 0.4)])]
_stripe = {}
def bee_stripe(r):
    k = round(r, 3)
    if k not in _stripe:
        _stripe[k] = stripe_mat("BeeStripe%s" % k, (1.0, 0.75, 0.08), (0.05, 0.04, 0.03), axis="Y", freq=2 * math.pi / (0.32 * r), thresh=0.35, rough=0.45)
    return _stripe[k]

# ---------------- hero bee (faces -Y, group origin = body centre) ----------------
def bee(name, loc, r, rz=0.0):
    x, y, z = loc
    g = group(name, loc, rz)
    def P(dx, dy, dz):
        return (x + dx * r, y + dy * r, z + dz * r)
    ab = sphere(name + "Abd", P(0, 0.5, -0.02), 0.5 * r, bee_stripe(r), scale=(0.9, 1.2, 0.9), sub=3)
    parts = [ab,
             sphere(name + "Thx", P(0, -0.1, 0.03), 0.36 * r, fuzz_m, sub=3),
             sphere(name + "Head", P(0, -0.55, 0.1), 0.32 * r, bee_k, sub=3),
             cyl(name + "Sting", P(0, 1.15, -0.04), 0.06 * r, 0.25 * r, bee_k, rot=(math.radians(-90), 0, 0), r2=0.0, verts=10)]
    for sx in (-1, 1):
        parts += [sphere(name + "EyeW", P(sx * 0.14, -0.8, 0.2), 0.14 * r, eyew, scale=(1, 0.7, 1.15), sub=2),
                  sphere(name + "EyeB", P(sx * 0.14, -0.9, 0.22), 0.07 * r, eyeb, sub=2),
                  tube(name + "Ant", [P(sx * 0.1, -0.7, 0.35), P(sx * 0.25, -0.85, 0.75), P(sx * 0.4, -1.05, 0.8)], [0.03 * r] * 3, bee_k),
                  sphere(name + "AntTip", P(sx * 0.4, -1.05, 0.8), 0.06 * r, bee_k, sub=1)]
        for dy in (-0.25, 0.0):
            parts.append(tube(name + "Leg", [P(sx * 0.15, -0.1 + dy, -0.2), P(sx * 0.3, -0.1 + dy, -0.45), P(sx * 0.32, -0.15 + dy, -0.62)],
                              [0.04 * r] * 3, bee_k))
        wg = group(name + "WingG", P(sx * 0.12, -0.05, 0.3))
        wing = sphere(name + "Wing", P(sx * 0.55, 0.05, 0.42), 0.45 * r, wing_m, scale=(1.0, 0.5, 0.06), sub=2)
        wing.rotation_euler = (0, sx * math.radians(-15), sx * math.radians(-12))
        attach([wing], wg)
        wg.rotation_euler = (0, 0, 0); wg.keyframe_insert("rotation_euler", frame=0)
        for fc in fcurves(wg):
            if fc.data_path == "rotation_euler" and fc.array_index == 1:
                m_ = fc.modifiers.new('NOISE'); m_.strength = 1.6; m_.scale = 0.7; m_.phase = random.uniform(0, 100)
        parts.append(wg)
    sm = tube(name + "Smile", [P(-0.1, -0.83, 0.0), P(0, -0.87, -0.05), P(0.1, -0.83, 0.0)], [0.022 * r] * 3, eyew)
    attach(parts + [sm], g)
    return g

def hover(o, keys, amp=0.08):
    """keys: list of (frame, loc); adds a little bob."""
    key_loc(o, keys)
    jitter(o, amp, 5.0)

# ---------------- crowd bee proto + geometry-node swarms ----------------
def make_bee_proto():
    objs = [sphere("q1", (0, 0.45, 0), 0.5, bee_stripe(1.0), scale=(0.9, 1.2, 0.9), sub=1, smooth=False),
            sphere("q2", (0, -0.1, 0.03), 0.36, fuzz_m, sub=1, smooth=False),
            sphere("q3", (0, -0.55, 0.1), 0.32, bee_k, sub=1, smooth=False)]
    for sx in (-1, 1):
        objs.append(sphere("qw", (sx * 0.5, 0.05, 0.45), 0.45, wing_m, scale=(1.0, 0.5, 0.08), sub=1, smooth=False))
        objs.append(sphere("qe", (sx * 0.15, -0.8, 0.2), 0.13, eyew, sub=1, smooth=False))
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    bpy.ops.object.join()
    o = bpy.context.object; o.name = "BeeProto"
    o.location = (0, 0, -300); o.hide_render = True; o.hide_viewport = True
    return o
BEE = make_bee_proto()

def make_hive_proto():
    objs = [box("h1", (0, 0, 0.17), (0.7, 0.55, 0.32), hive_w, bevel=0.02),
            box("h2", (0, 0, 0.5), (0.7, 0.55, 0.32), hive_y, bevel=0.02),
            box("h3", (0, 0, 0.83), (0.7, 0.55, 0.32), hive_w, bevel=0.02),
            box("h4", (0, 0, 1.03), (0.82, 0.66, 0.08), hive_l),
            box("h5", (0, -0.28, 0.05), (0.3, 0.03, 0.05), bee_k)]
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    o = bpy.context.object; o.name = "HiveProto"
    o.location = (0, 0, -300); o.hide_render = True; o.hide_viewport = True
    return o
HIVE = make_hive_proto()

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

def swarm(name, c, R, density, s, seed, layers=(1.0, 0.7, 0.4), squash=(1, 1, 0.75)):
    g = group(name, c)
    ch = []
    for k, f_ in enumerate(layers):
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3, radius=R * f_, location=c)
        o = bpy.context.object; o.name = name + "L%d" % k; o.scale = squash
        carpet(o.name, o, density, s, seed + 7 * k, BEE)
        ch.append(o)
    core = sphere(name + "Core", c, R * 0.5, fuzz_m, scale=squash, sub=2)
    ch.append(core)
    attach(ch, g)
    g.rotation_euler = (0, 0, 0); g.keyframe_insert("rotation_euler", frame=0)
    g.rotation_euler = (0, 0, 6.0); g.keyframe_insert("rotation_euler", frame=FRAMES)
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

def jar(name, loc, h=1.0, r=0.45):
    x, y, z = loc
    g = group(name, loc)
    ps = [cyl(name + "Honey", (x, y, z + h * 0.45), r, h * 0.9, honey_m, verts=28),
          cyl(name + "Rim", (x, y, z + h * 0.92), r * 0.92, h * 0.08, mat(name + "RimM", (0.9, 0.95, 1.0), 0.1), verts=28),
          cyl(name + "Lid", (x, y, z + h * 1.0), r * 1.0, h * 0.12, mat(name + "LidM", (0.95, 0.75, 0.15), 0.4, metal=0.5), verts=28),
          cyl(name + "Label", (x, y, z + h * 0.45), r * 1.01, h * 0.35, mat(name + "LabM", (0.98, 0.95, 0.85), 0.6), verts=28)]
    attach(ps, g)
    return g

def flower(name, loc, k, h=0.7, rr=0.18):
    x, y, z = loc
    g = group(name, (x, y, z))
    ps = [cyl(name + "Stem", (x, y, z + h / 2), 0.025, h, stem_m, verts=6),
          sphere(name + "Leaf", (x + 0.08, y, z + h * 0.4), 0.09, stem_m, scale=(1.6, 0.5, 0.4), sub=1),
          sphere(name + "Ctr", (x, y - 0.02, z + h), rr * 0.45, center_m, scale=(1, 0.6, 1), sub=2)]
    for j in range(6):
        a = j / 6 * 6.283
        ps.append(sphere(name + "Pet", (x + rr * math.cos(a), y + 0.01, z + h + rr * math.sin(a)), rr * 0.55, petal_ms[k % 4],
                         scale=(1, 0.35, 1), sub=1))
    attach(ps, g)
    return g

def spoon(name, loc, L=1.0, rot=(0, 0, 0)):
    x, y, z = loc
    g = group(name, loc)
    ps = [sphere(name + "Bowl", (x, y, z), 0.3 * L, silver_m, scale=(0.75, 1.1, 0.25), sub=3),
          box(name + "Handle", (x, y + 0.85 * L, z + 0.05 * L), (0.09 * L, 1.2 * L, 0.04 * L), silver_m, bevel=0.01)]
    attach(ps, g)
    g.rotation_euler = rot
    return g

you, YD = person("You", (0, 40, 0), 1.0, mat("Shirt", (0.95, 0.35, 0.2), 0.6), mat("Pants", (0.2, 0.3, 0.55), 0.7),
                 skin_m, mat("Hair", (0.25, 0.14, 0.07), 0.8))

# =================== line 0: hook — a bee swarm streams across the garden toward you ===================
sw0 = swarm("Sw0", (-3.0, 4.5, 2.6), 1.8, 9.0, 0.2, 1)
key_loc(sw0, [(0, (-4.5, 5.0, 2.8)), (E(0), (-0.8, 3.6, 2.2))])
vis(sw0, [(0, S[1])])
H0 = bee("H0", (0.4, 1.0, 1.6), 0.45, math.radians(-25))
hover(H0, [(0, (-0.6, 1.6, 1.9)), (E(0), (0.6, 0.9, 1.5))], 0.1)
vis(H0, [(0, S[1])])
J0 = jar("J0", (2.4, 1.6, 0), 1.0, 0.45); vis(J0, [(0, S[1])])

# =================== line 1: one bee on a kitchen scale (0.1 g) ===================
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
    vis(o, [(S[1], S[2])])
r0 = text("Read0", "0.000 g", (SA[0], SA[1] - 0.247, T + 0.035), 0.05, ink_m); vis(r0, [(S[1], S[1] + 14)])
r1 = text("Read1", "0.100 g", (SA[0], SA[1] - 0.247, T + 0.035), 0.05, ink_m); vis(r1, [(S[1] + 14, S[2])])
BR = 0.13
H1 = bee("H1", (SA[0], SA[1], PT + 0.62 * BR), BR, math.radians(15))
vis(H1, [(S[1], S[2])])
key_loc(H1, [(S[1], (SA[0] + 0.4, SA[1] - 0.1, PT + 0.4)), (S[1] + 12, (SA[0], SA[1], PT + 0.62 * BR))])

# =================== line 2: the bee visits a whole row of flowers ===================
FL = []
for k in range(15):
    x_ = -3.9 + k * 0.56
    y_ = 0.9 + (0.35 if k % 2 else 0.0)
    f_ = flower("Fl%d" % k, (x_, y_, 0), k, h=0.65 + 0.12 * (k % 3), rr=0.2)
    vis(f_, [(S[2], S[3])])
    FL.append((f_, x_, y_, 0.65 + 0.12 * (k % 3)))
H2 = bee("H2", (0, 0, 0), 0.32, math.radians(-90))
vis(H2, [(S[2], S[3])])
kk = []
n2 = len(FL)
for k, (f_, x_, y_, h_) in enumerate(FL):
    fr_ = int(S[2] + 2 + k * (E(2) - S[2] - 4) / n2)
    kk.append((fr_, (x_, y_ - 0.12, h_ + 0.32)))
    burst((x_, y_ - 0.1, h_ + 0.1), fr_ + 1, n=6, r=0.25, size=0.035, material=spark_m, f_out=fr_ + 8)
    keyrot(f_, [(fr_, (0, 0, 0)), (fr_ + 2, (math.radians(-12), 0, 0)), (fr_ + 6, (0, 0, 0))])
key_loc(H2, kk)
jitter(H2, 0.04, 3.0)

# =================== line 3: one twelfth of a teaspoon ===================
SP3 = (0.0, 0.8, 0.12)
sp3 = spoon("Spoon3", SP3, 1.4, rot=(0, 0, math.radians(25)))
vis(sp3, [(S[3], S[5])])
drop3 = sphere("Drop3", (SP3[0], SP3[1] - 0.05, 0.16), 0.07, honey_m, scale=(1, 1, 0.8), sub=3)
vis(drop3, [(S[3] + 8, S[5])])
key_loc(drop3, [(S[3] + 8, (SP3[0], SP3[1] - 0.05, 1.3)), (S[3] + 15, (SP3[0], SP3[1] - 0.05, 0.16))])
H3 = bee("H3", (0.3, 0.6, 1.3), 0.35, math.radians(-10))
vis(H3, [(S[3], S[4])])
hover(H3, [(S[3], (-0.6, 0.6, 1.5)), (S[3] + 8, (0.0, 0.7, 1.45)), (E(3), (0.5, 0.5, 1.35))], 0.05)
# 12 drops in a row: one golden, eleven grey
for k in range(12):
    gx = -1.65 + k * 0.3
    m_ = honey_m if k == 0 else ghost_m
    d_ = sphere("Row12", (gx, 0.0, 0.11), 0.1, m_, scale=(1, 1, 1.1), sub=2)
    vis(d_, [(S[3] + 14 + k, S[4])])
ring3 = box("Ring12", (-1.65, -0.0, 0.01), (0.3, 0.3, 0.02), honey_glow)
vis(ring3, [(S[3] + 16, S[4])])

# =================== line 4: its whole life's work, one tiny drop ===================
H4 = bee("H4", (SP3[0] + 0.45, SP3[1] - 0.15, 0.4), 0.3, math.radians(30))
vis(H4, [(S[4], S[5])])
hover(H4, [(S[4], (SP3[0] + 0.6, SP3[1] - 0.25, 0.55)), (E(4), (SP3[0] + 0.35, SP3[1] - 0.2, 0.42))], 0.03)
for k in range(3):
    bpy.ops.mesh.primitive_torus_add(major_radius=0.25, minor_radius=0.012, location=(SP3[0], SP3[1] - 0.05, 0.2))
    rg = bpy.context.object; rg.data.materials.append(honey_glow)
    f = S[4] + 2 + k * 9
    keyscale(rg, [(0, 0.001), (f - 1, 0.001), (f, 0.3), (f + 12, 1.6), (f + 13, 0.001)])
burst((SP3[0], SP3[1] - 0.1, 0.3), S[4] + 3, n=10, r=0.3, size=0.025, f_out=E(4))

# =================== line 5: 1,000 bees -> one big jar ===================
J5 = jar("J5", (-0.4, 1.0, 0), 1.3, 0.55)
keyscale(J5, [(0, 0.001), (S[5] - 1, 0.001), (S[5] + 4, (1, 1, 0.001)), (W(5, 0.7), (1, 1, 1.0)), (E(5) - 1, 1.0), (E(5), 0.001)])
sw5 = swarm("Sw5", (-0.4, 1.0, 2.0), 0.9, 14.0, 0.11, 5, layers=(1.0, 0.7))
vis(sw5, [(S[5], S[6])])
key_loc(sw5, [(S[5], (-1.8, 1.3, 1.8)), (E(5), (0.3, 1.0, 1.9))])

# =================== line 6: 1,000,000 bees -> an overflowing bathtub ===================
TB = (1.2, 1.6)
tub = [box("TubOut", (TB[0], TB[1], 0.6), (2.6, 1.3, 0.7), tub_m, bevel=0.15),
       box("TubHoney", (TB[0], TB[1], 0.97), (2.35, 1.05, 0.06), honey_m)]
for dx in (-1.05, 1.05):
    for dy in (-0.45, 0.45):
        tub.append(sphere("TubFoot", (TB[0] + dx, TB[1] + dy, 0.14), 0.13, mat("Gold", (0.95, 0.75, 0.2), 0.3, metal=0.8), sub=2))
tubg = group("TubG", (TB[0], TB[1], 0)); attach(tub, tubg)
vis(tubg, [(S[6], S[7])])
for k in range(8):
    x_ = TB[0] - 1.1 + k * 0.31
    dr = sphere("Spill", (x_, TB[1] - 0.68, 0.9), 0.1, honey_m, scale=(1, 0.6, 1.8), sub=2)
    f0 = S[6] + 6 + (k % 4) * 3
    key_loc(dr, [(f0, (x_, TB[1] - 0.68, 0.95)), (f0 + 12, (x_, TB[1] - 0.72, 0.2))])
    vis(dr, [(f0, S[7])])
pud = cyl("Puddle", (TB[0], TB[1] - 1.0, 0.02), 1.0, 0.03, honey_m, verts=32)
keyscale(pud, [(0, 0.001), (S[6] + 8, 0.001), (S[6] + 9, (0.2, 0.15, 1)), (E(6) - 1, (1.8, 0.6, 1)), (E(6), 0.001)])
sw6 = swarm("Sw6", (TB[0], TB[1] + 0.5, 2.6), 1.7, 10.0, 0.15, 6)
vis(sw6, [(S[6], S[7])])

# =================== line 7: one billion bees fill the sky over the garden ===================
SKY = []
for k, (c, R) in enumerate([((-6, 6, 4.5), 3.2), ((2, 4, 3.6), 3.0), ((9, 8, 5.0), 3.4), ((-12, 12, 6), 3.6),
                            ((5, 13, 7.0), 3.8), ((-2, 10, 6.5), 3.0), ((14, 2, 4), 2.6), ((-14, 2, 3.5), 2.8)]):
    o = swarm("Sky%d" % k, c, R, 2.6, 0.32, 70 + k, layers=(1.0, 0.75))
    SKY.append(o)
    vis(o, [(S[7] + 2 * k, S[8])])

# =================== line 8: 100 tons of bees balance a blue whale on a seesaw ===================
PX, PY, PZ = 0.0, 3.0, 1.4
pivot = cyl("Pivot", (PX, PY, 0.65), 0.95, 1.3, mat("PivotM", (0.3, 0.32, 0.38), 0.6), verts=3)
pivot.rotation_mode = 'ZXY'; pivot.rotation_euler = (math.radians(90), 0, math.radians(90))
plank = group("Plank", (PX, PY, PZ))
pl = box("PlankBoard", (PX, PY, PZ), (10.0, 2.4, 0.22), mat("SeeSaw", (0.95, 0.75, 0.2), 0.5), bevel=0.04)
bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3, radius=1.5, location=(PX - 3.2, PY, PZ + 1.55))
bball = bpy.context.object; bball.name = "BeeBall"; bball.data.materials.append(fuzz_m)
carpet("BeeBallC", bball, 40.0, 0.13, 8, BEE)
bcore = sphere("BeeCore", (PX - 3.2, PY, PZ + 1.55), 1.42, bee_stripe(3.0), sub=3)
# whale (head toward -X)
WX = PX + 2.9
wparts = [sphere("WBody", (WX, PY, PZ + 1.0), 1.0, whale_m, scale=(2.2, 0.95, 0.85), sub=3),
          sphere("WBelly", (WX - 0.2, PY - 0.08, PZ + 0.72), 1.0, whale_b, scale=(1.9, 0.82, 0.5), sub=3),
          sphere("WTail", (WX + 2.3, PY, PZ + 1.2), 0.45, whale_m, scale=(1.4, 0.6, 0.5), sub=2),
          sphere("WFlukeL", (WX + 2.95, PY - 0.55, PZ + 1.35), 0.45, whale_m, scale=(0.7, 1.3, 0.12), sub=2),
          sphere("WFlukeR", (WX + 2.95, PY + 0.55, PZ + 1.35), 0.45, whale_m, scale=(0.7, 1.3, 0.12), sub=2),
          sphere("WFin", (WX - 0.6, PY - 0.95, PZ + 0.6), 0.4, whale_m, scale=(1.0, 0.2, 0.35), sub=2),
          sphere("WEyeW", (WX - 1.5, PY - 0.75, PZ + 1.05), 0.14, eyew, sub=2),
          sphere("WEyeB", (WX - 1.55, PY - 0.86, PZ + 1.05), 0.07, eyeb, sub=2),
          tube("WSmile", [(WX - 2.05, PY - 0.55, PZ + 0.75), (WX - 1.7, PY - 0.78, PZ + 0.68), (WX - 1.3, PY - 0.85, PZ + 0.72)], [0.03] * 3, eyeb)]
attach([pl, bball, bcore] + wparts, plank)
vis(pivot, [(S[8], S[9])], tuple(pivot.scale)); vis(plank, [(S[8], S[9])])
for f, a in [(S[8], math.radians(-14)), (S[8] + 6, math.radians(-14)), (S[8] + 14, math.radians(5)), (S[8] + 20, math.radians(-2)), (S[8] + 26, 0)]:
    plank.rotation_euler = (0, a, 0); plank.keyframe_insert("rotation_euler", frame=f)
burst((PX, PY - 1.3, PZ + 1.0), S[8] + 26, n=12, r=1.4, size=0.06, f_out=E(8))

# =================== line 9: twenty thousand hives fill the yard ===================
HIVES = []
for k, (cx, cy, sx_, sy_) in enumerate([(0, 0.6, 30, 3.6), (0, 4.4, 30, 3.6), (-5, 8.6, 20, 4.0), (8.5, 8.6, 9, 4.0), (0, 22, 60, 8)]):
    o = plane_obj("Hives%d" % k, cx, cy, sx_, sy_)
    carpet(o.name, o, 2.0, 1.0, 90 + k, HIVE, poisson=1.05, upright=True)
    HIVES.append(o)
    vis(o, [(S[9] + 3 * k, S[10])])

# =================== line 10: about 400,000 liters — a honey flood ===================
flood = box("Flood", (0, 5.5, 0.0), (60, 14.2, 1.0), honey_m)
flood.data.transform(Matrix.Translation((0, 0, 0.5)))
keyscale(flood, [(0, 0.001), (S[10] - 1, 0.001), (S[10], (1, 1, 0.02)), (E(10) - 2, (1, 1, 0.9)), (E(10), 0.001)])
fall = cyl("HoneyFall", (0, 5.0, 8), 0.7, 16, honey_m, verts=20)
vis(fall, [(S[10], S[11])])
for k in range(10):
    p0 = (random.uniform(-3, 3), random.uniform(3, 7), 12)
    bl = sphere("Blob", p0, random.uniform(0.25, 0.45), honey_m, sub=2)
    f0 = S[10] + k * 3
    key_loc(bl, [(f0, p0), (f0 + 10, (p0[0], p0[1], 0.5))])
    vis(bl, [(f0, f0 + 11)])
H10 = bee("H10", (2.2, 0.4, 2.2), 0.5, math.radians(-20))
vis(H10, [(S[10], S[11])])
hover(H10, [(S[10], (3.0, 0.2, 2.0)), (E(10), (1.8, 0.4, 2.4))], 0.08)

# =================== line 11: six backyard pools of honey ===================
POOLS = []
num_m = mat("NumM", (1, 1, 1), 0.4, emit=(1, 1, 1), emit_strength=0.9)
for k, (x_, y_) in enumerate([(-4.4, 1.3), (0.0, 1.3), (4.4, 1.3), (-4.4, 4.8), (0.0, 4.8), (4.4, 4.8)]):
    rim = box("PRim%d" % k, (x_, y_, 0.05), (3.7, 2.5, 0.12), mat("PoolRim%d" % k, (0.9, 0.88, 0.82), 0.7))
    hon = box("PHon%d" % k, (x_, y_, 0.1), (3.2, 2.0, 0.06), honey_m)
    pg = group("Pool%d" % k, (x_, y_, 0)); attach([rim, hon], pg)
    f0 = S[11] + 3 + k * 4
    vis(pg, [(f0, S[12]), (S[16], FRAMES)])
    nt_ = text("PNum%d" % k, str(k + 1), (x_, y_ - 0.2, 0.2), 1.2, num_m, rot=(math.radians(72), 0, 0), extrude=0.06)
    vis(nt_, [(f0 + 2, S[12])], tuple(nt_.scale))
    burst((x_, y_ - 1.3, 0.4), f0, n=10, r=1.2, size=0.05, f_out=f0 + 10)
    POOLS.append(pg)
gold_pool = box("PoolHoney", (POX, POY, 0.1), (5.8, 3.2, 0.06), honey_m)
vis(gold_pool, [(S[10], FRAMES)])

# =================== line 12: a spoonful on your toast every day ===================
TT = (0.0, 0.9)
tz = 0.85
t12 = [box("Tbl12", (TT[0], TT[1], tz - 0.04), (2.2, 1.2, 0.08), wood, bevel=0.02)]
for dx in (-0.95, 0.95):
    for dy in (-0.45, 0.45):
        t12.append(box("TblLeg12", (TT[0] + dx, TT[1] + dy, (tz - 0.08) / 2), (0.08, 0.08, tz - 0.08), wood))
t12 += [cyl("Plate12", (TT[0], TT[1], tz + 0.02), 0.55, 0.04, plate_m, verts=32),
        box("ToastCrust", (TT[0], TT[1], tz + 0.09), (0.7, 0.62, 0.1), crust_m, bevel=0.04),
        box("ToastTop", (TT[0], TT[1], tz + 0.141), (0.6, 0.52, 0.01), bread_m)]
for o in t12:
    vis(o, [(S[12], S[13])])
sp12 = spoon("Spoon12", (TT[0] + 0.15, TT[1] - 0.05, tz + 0.75), 0.9, rot=(math.radians(-25), 0, math.radians(30)))
vis(sp12, [(S[12], S[13])])
key_loc(sp12, [(S[12], (TT[0] + 0.6, TT[1] - 0.1, tz + 1.0)), (S[12] + 8, (TT[0] + 0.15, TT[1] - 0.05, tz + 0.75))])
drip = cyl("Drip12", (TT[0] + 0.1, TT[1] - 0.05, tz + 0.45), 0.03, 0.6, honey_m, verts=10)
keyscale(drip, [(0, 0.001), (S[12] + 9, 0.001), (S[12] + 10, (1, 1, 1)), (E(12) - 1, (1, 1, 1)), (E(12), 0.001)])
pud12 = cyl("Pud12", (TT[0] + 0.05, TT[1] - 0.02, tz + 0.15), 0.25, 0.012, honey_m, verts=24)
keyscale(pud12, [(0, 0.001), (S[12] + 10, 0.001), (S[12] + 11, (0.2, 0.2, 1)), (E(12) - 1, (1.0, 0.9, 1)), (E(12), 0.001)])
# =================== line 13: 200,000+ years — calendar pages fly ===================
CX, CY = 0.0, 1.0
cal = [box("CalBody", (CX, CY, 1.0), (1.8, 0.4, 1.6), cal_m, bevel=0.04),
       box("CalTop", (CX, CY - 0.01, 1.9), (1.82, 0.42, 0.35), calred_m, bevel=0.04),
       box("CalStand", (CX, CY + 0.25, 0.1), (1.4, 0.8, 0.2), wood)]
for o in cal:
    vis(o, [(S[13], S[14])])
years = ["YEAR 1", "YEAR 1,000", "YEAR 50,000", "YEAR 100,000", "YEAR 200,000"]
for k, yb in enumerate(years):
    t_ = text("Yr%d" % k, yb, (CX, CY - 0.22, 1.0), 0.3 if k < 3 else 0.25, ink_m)
    a = W(13, k / 5); b = W(13, (k + 1) / 5) if k < 4 else S[14]
    vis(t_, [(a, b)])
for k in range(14):
    p0 = (CX, CY - 0.23, 1.6)
    pg_ = boxc("Page", p0, (1.6, 0.02, 0.9), cal_m)
    f0 = S[13] + k * 2
    p1 = (CX + random.choice((-1, 1)) * random.uniform(2.5, 4.5), CY + random.uniform(0, 2), random.uniform(3, 6))
    key_loc(pg_, [(f0, p0), (f0 + 12, p1)])
    keyrot(pg_, [(f0, (0, 0, 0)), (f0 + 12, (random.uniform(-3, 3), random.uniform(-3, 3), random.uniform(-3, 3)))])
    vis(pg_, [(f0, f0 + 13)])
J13 = jar("J13", (CX + 1.7, CY - 0.2, 0), 1.0, 0.42); vis(J13, [(S[13], S[14])])
you13 = None

# =================== lines 14-15: the twist — an ancient honey jar in the soil ===================
AJ = (-0.6, FRONT_Y - 0.25, -1.6)
amph = [sphere("AmBody", AJ, 0.8, clay_m, scale=(0.85, 0.85, 1.0), sub=3),
        cyl("AmNeck", (AJ[0], AJ[1], AJ[2] + 0.95), 0.32, 0.4, clay_m, verts=20),
        tube("AmBand", [(AJ[0] - 0.68, AJ[1] - 0.05, AJ[2] + 0.2), (AJ[0], AJ[1] - 0.69, AJ[2] + 0.2), (AJ[0] + 0.68, AJ[1] - 0.05, AJ[2] + 0.2)], [0.04] * 3, clay_dk),
        tube("AmBand2", [(AJ[0] - 0.62, AJ[1] - 0.05, AJ[2] - 0.3), (AJ[0], AJ[1] - 0.63, AJ[2] - 0.3), (AJ[0] + 0.62, AJ[1] - 0.05, AJ[2] - 0.3)], [0.04] * 3, clay_dk)]
for o in amph:
    vis(o, [(S[14], FRAMES - 1)], tuple(o.scale))
lid = cyl("AmLid", (AJ[0], AJ[1], AJ[2] + 1.2), 0.38, 0.14, clay_dk, verts=20)
vis(lid, [(S[14], FRAMES - 1)])
key_loc(lid, [(S[15] + 4, (AJ[0], AJ[1], AJ[2] + 1.2)), (S[15] + 12, (AJ[0] + 1.2, AJ[1] - 0.6, AJ[2] + 3.0)), (S[15] + 22, (AJ[0] + 1.8, AJ[1] - 0.9, AJ[2] + 1.9))])
keyrot(lid, [(S[15] + 4, (0, 0, 0)), (S[15] + 22, (math.radians(140), math.radians(60), 0))])
hglow = cyl("AmHoney", (AJ[0], AJ[1], AJ[2] + 1.15), 0.28, 0.06, honey_glow, verts=20)
vis(hglow, [(S[15] + 6, FRAMES - 1)])
for k in range(3):
    bpy.ops.mesh.primitive_torus_add(major_radius=0.5, minor_radius=0.025, location=(AJ[0], AJ[1], AJ[2] + 1.3))
    rg = bpy.context.object; rg.data.materials.append(honey_glow)
    f = S[15] + 8 + k * 9
    keyscale(rg, [(0, 0.001), (f - 1, 0.001), (f, 0.3), (f + 12, 1.8), (f + 13, 0.001)])
burst((AJ[0], AJ[1] - 0.3, AJ[2] + 1.6), S[15] + 7, n=12, r=0.9, size=0.05, f_out=S[16])
# question marks / dig sparkles at the twist
for k in range(8):
    p0 = (AJ[0] + random.uniform(-1.4, 1.4), FRONT_Y - 0.3, AJ[2] + random.uniform(-0.6, 1.0))
    st = sphere("Dirt", p0, 0.09, mat("DirtM", (0.45, 0.27, 0.12), 0.9), sub=1, smooth=False)
    f0 = S[14] + 1 + k
    key_loc(st, [(f0, p0), (f0 + 10, (p0[0] * 1.4, p0[1] - 1.2, p0[2] + 1.5))])
    vis(st, [(f0, f0 + 11)])
J15 = jar("J15", (AJ[0] + 2.0, 0.0, 0), 0.9, 0.38); vis(J15, [(S[15], S[16])])
H15 = bee("H15", (AJ[0] + 1.0, -0.4, 0.8), 0.35, math.radians(20))
vis(H15, [(S[15], S[16])])
hover(H15, [(S[15], (AJ[0] + 1.6, -0.2, 1.0)), (E(15), (AJ[0] + 0.9, -0.5, 0.6))], 0.05)

# =================== line 16: you, a giant spoon, pools of honey, bees ===================
sp16 = spoon("Spoon16", (1.15, 1.7, 2.3), 1.5, rot=(math.radians(-80), 0, math.radians(10)))
vis(sp16, [(S[16], FRAMES)])
sw16 = swarm("Sw16", (-2.5, 5.0, 3.6), 1.6, 9.0, 0.2, 16)
vis(sw16, [(S[16], FRAMES)])
H16 = bee("H16", (-0.9, 1.4, 2.0), 0.4, math.radians(-30))
vis(H16, [(S[16], FRAMES)])
hover(H16, [(S[16], (-1.4, 1.5, 2.2)), (FRAMES, (-0.7, 1.3, 1.9))], 0.08)

# =================== "you" placement ===================
jumps(you, [(0, (2.6, 3.4, 0)), (S[1], (0, 40, 0)), (S[12], (TT[0] - 0.2, TT[1] + 1.0, 0)), (S[13], (0, 40, 0)),
            (S[16], (0.6, 1.8, 0))])
vis(you, [(0, S[1]), (S[12], S[13]), (S[16], FRAMES)])
for k, ag in enumerate(YD["arms"]):
    sx = -1 if k == 0 else 1
    keyrot(ag, [(0, (0, sx * math.radians(150), 0)), (S[1], (0, 0, 0)), (S[12], (0, 0, 0)),
                (S[16], (0, sx * math.radians(70) if k == 0 else math.radians(100), 0))])
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
V[0], V2[0] = orb((0.6, 3.0, 1.6), 14.0, -14, -2, 2.0, 11.5)
V[1], V2[1] = orb((SA[0], SA[1], PT + 0.08), 1.2, 12, -10, 0.3, 1.0)
V[2], V2[2] = orb((0.0, 1.0, 0.8), 7.4, -10, 8, 0.8, 6.6)
V[3], V2[3] = orb((-0.4, 0.5, 0.4), 4.6, 10, -8, 0.6, 4.0)
V[4], V2[4] = orb((SP3[0] + 0.2, SP3[1] - 0.1, 0.35), 2.6, -12, 8, 0.4, 2.1)
V[5], V2[5] = orb((-0.4, 1.0, 1.0), 6.5, 10, -8, 0.6, 5.8)
V[6], V2[6] = orb((TB[0], TB[1], 1.0), 8.5, -10, 8, 0.8, 7.5)
V[7], V2[7] = orb((0.0, 7.0, 3.0), 26.0, -10, 6, 5.0, 31.0)
V[8], V2[8] = orb((PX, PY, 2.0), 15.0, 6, -6, 1.0, 13.5)
V[9], V2[9] = orb((0.0, 5.0, 1.0), 20.0, -10, 4, 4.0, 26.0)
V[10], V2[10] = orb((0.0, 5.0, 1.5), 21.0, 6, -6, 3.0, 19.0)
V[11], V2[11] = orb((0.0, 3.2, 0.3), 15.0, -6, 6, 4.0, 17.0)
V[12], V2[12] = orb((TT[0], TT[1], tz + 0.3), 4.8, 12, -6, 0.6, 3.8)
V[13], V2[13] = orb((CX + 0.6, CY, 1.0), 6.2, -10, 8, 0.6, 5.4)
V[14], V2[14] = orb((AJ[0] + 0.3, AJ[1], AJ[2] + 0.4), 8.0, 14, 2, 0.5, 6.5)
V[15], V2[15] = orb((AJ[0] + 0.6, AJ[1], AJ[2] + 0.8), 6.5, -6, 6, 0.5, 6.0)
V[16], V2[16] = orb((0.0, 3.0, 1.2), 13.0, -8, 6, 2.0, 16.0)
VM = {i: (tuple((Vector(V[i][0]) + Vector(V2[i][0])) / 2), V[i][1]) for i in V}

def LB(i, name, body, m_, size=None, f_in=None, f_out=None, Dk=0.55, end=False, v=0.26, u=0.0):
    view = V2[i] if end else VM[i]
    cl = Vector(CL(view)); D = (Vector(view[1]) - cl).length * Dk
    s_ = 0.85 * fit(body, D, size if size else 1e9)
    return label(name, body, view, D, v, s_, m_, (S[i] + 3) if f_in is None else f_in,
                 E(i) if f_out is None else f_out, u)
LB(0, "L0", "1 BILLION BEES?!", red_lab)
LB(1, "L1", "0.1 g", lab_m, v=0.3)
LB(2, "L2", "1000s OF FLOWERS", pink_lab)
LB(3, "L3", "1/12 TEASPOON", lab_m)
LB(4, "L4", "A WHOLE LIFE", white_lab)
LB(5, "L5", "1,000 = 1 JAR", lab_m)
LB(6, "L6", "1,000,000 = A TUB", lab_m)
LB(7, "L7", "1,000,000,000", red_lab, Dk=0.4)
LB(8, "L8", "100 TONS = 1 WHALE", blue_lab, Dk=0.45)
LB(9, "L9", "20,000 HIVES", lab_m, Dk=0.45)
LB(10, "L10", "400,000 LITERS", lab_m, Dk=0.45)
LB(11, "L11", "6 POOLS OF HONEY", lab_m, Dk=0.45)
LB(12, "L12", "1 SPOON A DAY", lab_m)
LB(13, "L13", "200,000+ YEARS", green_lab)
LB(14, "L14", "THE TWIST...", white_lab, Dk=0.45)
LB(15, "L15", "STILL GOOD!", green_lab, Dk=0.45)
LB(16, "L16", "WHAT WOULD YOU DO?", lab_m, end=True, f_in=S[16] + 6, Dk=0.45)

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
