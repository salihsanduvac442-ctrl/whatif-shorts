# Day 18 — What if 1 billion ants tried to lift your house?  Build: python3 episodes/018-billion-ants/scene.py
# Reference style: base (helpers, lawn/soil, house, garden, camera helpers) copied from episodes/014-billion-mosquitoes (ref style of 003-lift-million-ref)
import bpy, math, random, os, json
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
random.seed(18)
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
# Day 18 — What if 1 billion ants tried to lift your house?
# Facts used: a typical worker ant (e.g. garden / wood ants) weighs ~1-5 mg -> "about three milligrams";
#   ants can carry ~10-50x their own body mass (often quoted "up to 50x") -> 3 mg x 50 = 150 mg per ant;
#   square-cube law: muscle force scales with cross-section, body mass with volume -> small animals are strong
#   for their size;  you (~70 kg) x 50 = 3.5 t ~ two cars;  1,000 ants x 150 mg = 150 g ~ an apple;
#   1e6 -> 150 kg ~ a fridge;  1e9 x 3 mg = 3 t of ants;  1e9 x 150 mg = 150 t of lifting force;
#   a typical house weighs roughly 100 t (wood frame ~50-80 t, brick / with foundation more) -> "around a hundred";
#   twist: a ~40 m wall perimeter with ~2 mm per ant -> ~20,000 ants can grip the base at once.
# Cartoon scale: ants are drawn far bigger than life so they read on a phone.
# =====================================================================================

# ---------------- house as one liftable group ----------------
HOUSE_PARTS = [o for o in bpy.data.objects if o.name.split(".")[0] in ("House", "Roof", "WinFrame", "WinGlass", "Door", "Shutter")]
houseg = group("HouseG", (HX, HY, 0))
for o in HOUSE_PARTS:
    parent_to(o, houseg)

for o in bpy.data.objects:
    if o.name.startswith("Bush"):
        o.scale = (0.001,) * 3

# ---------------- materials ----------------
ant_m = mat("AntBody", (0.62, 0.12, 0.05), 0.3)
ant_dk = mat("AntDark", (0.2, 0.05, 0.03), 0.4)
sugar_m = mat("Sugar", (0.98, 0.98, 1.0), 0.5, emit=(1, 1, 1), emit_strength=0.15)
apple_m = mat("Apple", (0.85, 0.06, 0.05), 0.25)
fridge_m = mat("Fridge", (0.96, 0.97, 0.98), 0.25)
steel_m = mat("SteelG", (0.6, 0.62, 0.66), 0.3, metal=0.8)
dirt_m = mat("Dirt", (0.45, 0.27, 0.12), 0.9)
dust_m = mat("Dust", (0.85, 0.75, 0.6), 0.9, emit=(0.6, 0.5, 0.4), emit_strength=0.2)
arrow_m = glow_mat("ArrowG", (0.25, 1.0, 0.35), 2.2)
musc_m = glow_mat("Muscle", (1.0, 0.35, 0.5), 3.0)
gbar_m = mat("GBar", (0.2, 0.85, 0.3), 0.5, emit=(0.15, 0.7, 0.25), emit_strength=0.5)
rbar_m = mat("RBar", (0.95, 0.25, 0.15), 0.5, emit=(0.8, 0.2, 0.1), emit_strength=0.5)
conf_ms = [glow_mat("Cf%d" % k, c, 2.0) for k, c in enumerate([(1, 0.85, 0.2), (0.3, 0.7, 1.0), (1, 0.4, 0.7), (0.4, 1, 0.4)])]

# ---------------- hero ant (faces -Y, feet at z=0 at the group origin) ----------------
def ant(name, loc, r, rz=0.0, lift=False):
    x, y, z = loc
    g = group(name, loc, rz)
    def P(dx, dy, dz):
        return (x + dx * r, y + dy * r, z + dz * r)
    parts = [sphere(name + "Gas", P(0, 0.95, 0.68), 0.55 * r, ant_m, scale=(0.85, 1.2, 0.85), sub=3),
             sphere(name + "Pet", P(0, 0.38, 0.58), 0.16 * r, ant_m, sub=2),
             sphere(name + "Thx", P(0, 0.02, 0.62), 0.3 * r, ant_m, scale=(0.8, 1.35, 0.8), sub=3),
             sphere(name + "Head", P(0, -0.55, 0.8), 0.4 * r, ant_m, sub=3)]
    for sx in (-1, 1):
        parts += [sphere(name + "EyeW", P(sx * 0.17, -0.86, 0.92), 0.15 * r, eyew, scale=(1, 0.7, 1.15), sub=2),
                  sphere(name + "EyeB", P(sx * 0.17, -0.97, 0.94), 0.075 * r, eyeb, sub=2),
                  tube(name + "Ant", [P(sx * 0.12, -0.72, 1.12), P(sx * 0.32, -0.85, 1.55), P(sx * 0.55, -1.15, 1.5)],
                       [0.04 * r, 0.035 * r, 0.03 * r], ant_dk),
                  sphere(name + "AntTip", P(sx * 0.55, -1.15, 1.5), 0.06 * r, ant_dk, sub=1),
                  tube(name + "Mand", [P(sx * 0.14, -0.85, 0.62), P(sx * 0.08, -1.0, 0.55)], [0.05 * r, 0.03 * r], ant_dk)]
        for k, dy in enumerate((-0.2, 0.02, 0.24)):
            spread = (-1.0, 0.0, 1.0)[k]
            if lift and k == 0:
                parts.append(tube(name + "Leg", [P(sx * 0.18, dy, 0.7), P(sx * 0.55, -0.45, 1.25), P(sx * 0.42, -0.55, 1.95)],
                                  [0.065 * r, 0.05 * r, 0.04 * r], ant_dk))
                continue
            parts.append(tube(name + "Leg", [P(sx * 0.18, dy, 0.55), P(sx * 0.75, dy + spread * 0.3, 0.85),
                                             P(sx * 1.0, dy + spread * 0.65, 0.02)], [0.065 * r, 0.05 * r, 0.035 * r], ant_dk))
    sm = tube(name + "Smile", [P(-0.12, -0.9, 0.66), P(0, -0.95, 0.6), P(0.12, -0.9, 0.66)], [0.025 * r] * 3, eyeb)
    attach(parts + [sm], g)
    return g

# ---------------- crowd ant proto + geometry-nodes carpets ----------------
def make_proto():
    objs = [sphere("q1", (0, 0.95, 0.68), 0.55, ant_m, scale=(0.85, 1.2, 0.85), sub=1, smooth=False),
            sphere("q2", (0, 0.02, 0.62), 0.3, ant_m, scale=(0.8, 1.35, 0.8), sub=1, smooth=False),
            sphere("q3", (0, -0.55, 0.8), 0.4, ant_m, sub=1, smooth=False)]
    for sx in (-1, 1):
        for k, dy in enumerate((-0.2, 0.02, 0.24)):
            spread = (-1.0, 0.0, 1.0)[k]
            objs.append(seg("ql", (sx * 0.18, dy, 0.55), (sx * 0.75, dy + spread * 0.3, 0.85), 0.07, ant_dk, verts=4))
            objs.append(seg("ql", (sx * 0.75, dy + spread * 0.3, 0.85), (sx * 1.0, dy + spread * 0.65, 0.02), 0.06, ant_dk, verts=4))
        objs.append(seg("qa", (sx * 0.12, -0.72, 1.12), (sx * 0.5, -1.1, 1.5), 0.05, ant_dk, verts=4))
        objs.append(sphere("qe", (sx * 0.17, -0.88, 0.92), 0.13, eyew, sub=1, smooth=False))
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    bpy.ops.object.join()
    o = bpy.context.object; o.name = "AntProto"
    o.location = (0, 0, -300); o.hide_render = True; o.hide_viewport = True
    return o
PROTO = make_proto()

def carpet(name, me_obj, density, s, seed, rotz=None, align=False):
    """Instance crowd ants on the faces of me_obj (mesh itself not rendered)."""
    ng = bpy.data.node_groups.new(name + "GN", 'GeometryNodeTree')
    ng.interface.new_socket(name="Geometry", in_out='INPUT', socket_type='NodeSocketGeometry')
    ng.interface.new_socket(name="Geometry", in_out='OUTPUT', socket_type='NodeSocketGeometry')
    Nn = ng.nodes; Ln = ng.links
    gi = Nn.new('NodeGroupInput'); go = Nn.new('NodeGroupOutput')
    d = Nn.new('GeometryNodeDistributePointsOnFaces')
    d.inputs['Density'].default_value = density; d.inputs['Seed'].default_value = seed
    oi = Nn.new('GeometryNodeObjectInfo'); oi.inputs['Object'].default_value = PROTO
    ip = Nn.new('GeometryNodeInstanceOnPoints')
    Ln.new(gi.outputs[0], d.inputs['Mesh']); Ln.new(d.outputs['Points'], ip.inputs['Points'])
    Ln.new(oi.outputs['Geometry'], ip.inputs['Instance'])
    if align:
        Ln.new(d.outputs['Rotation'], ip.inputs['Rotation'])
    elif rotz is not None:
        cx = Nn.new('ShaderNodeCombineXYZ'); rj = Nn.new('FunctionNodeRandomValue')
        rj.inputs['Min'].default_value = rotz - 0.25; rj.inputs['Max'].default_value = rotz + 0.25; rj.inputs['Seed'].default_value = seed + 3
        Ln.new(rj.outputs[0], cx.inputs['Z']); Ln.new(cx.outputs[0], ip.inputs['Rotation'])
    else:
        cx = Nn.new('ShaderNodeCombineXYZ'); rr = Nn.new('FunctionNodeRandomValue')
        rr.inputs['Min'].default_value = 0.0; rr.inputs['Max'].default_value = 6.283; rr.inputs['Seed'].default_value = seed + 1
        Ln.new(rr.outputs[0], cx.inputs['Z']); Ln.new(cx.outputs[0], ip.inputs['Rotation'])
    rs = Nn.new('FunctionNodeRandomValue'); rs.inputs['Min'].default_value = s * 0.8; rs.inputs['Max'].default_value = s * 1.2
    rs.inputs['Seed'].default_value = seed + 2
    Ln.new(rs.outputs[0], ip.inputs['Scale'])
    Ln.new(ip.outputs[0], go.inputs[0])
    me_obj.modifiers.new("GN", 'NODES').node_group = ng
    return me_obj

def plane_obj(name, cx, cy, sx, sy, z=0.0):
    bpy.ops.mesh.primitive_plane_add(size=1, location=(cx, cy, z))
    o = bpy.context.object; o.name = name; o.scale = (sx, sy, 1)
    bpy.ops.object.transform_apply(scale=True)
    me = o.data; me.transform(Matrix.Translation((0, 0, 0)))
    return o

def ground_carpet(name, cx, cy, sx, sy, density, s, seed, rotz=None):
    o = plane_obj(name, cx, cy, sx, sy)
    return carpet(name, o, density, s, seed, rotz)

# ---------------- props ----------------
def car(name, loc, color, rz=0.0):
    x, y, z = loc
    g = group(name, loc, rz)
    cm = mat(name + "Paint", color, 0.3)
    glass_ = mat(name + "Glass", (0.25, 0.4, 0.55), 0.1)
    ps = [box(name + "Body", (x, y, z + 0.55), (3.6, 1.7, 0.6), cm, bevel=0.12),
          box(name + "Cab", (x - 0.15, y, z + 1.1), (1.9, 1.5, 0.6), cm, bevel=0.15),
          box(name + "WinF", (x - 0.15, y - 0.76, z + 1.12), (1.6, 0.03, 0.42), glass_),
          box(name + "WinS", (x + 0.82, y, z + 1.12), (0.03, 1.3, 0.42), glass_),
          box(name + "WinS2", (x - 1.12, y, z + 1.12), (0.03, 1.3, 0.42), glass_)]
    for dx in (-1.15, 1.15):
        for dy in (-0.8, 0.8):
            ps.append(cyl(name + "Whl", (x + dx, y + dy, z + 0.35), 0.35, 0.28, mat("Tyre", (0.05, 0.05, 0.05), 0.9),
                          rot=(math.radians(90), 0, 0), verts=16))
    attach(ps, g)
    return g

you, YD = person("You", (0, 40, 0), 1.0, mat("Shirt", (0.95, 0.35, 0.2), 0.6), mat("Pants", (0.2, 0.3, 0.55), 0.7),
                 skin_m, mat("Hair", (0.25, 0.14, 0.07), 0.8))

# =================== line 0: hook — an ant army streams across the lawn to the house ===================
hook = []
for k, (y0, w_) in enumerate([(0.9, 2.6), (5.0, 3.0)]):
    o = ground_carpet(f"Hook{k}", -6.0, y0, 22.0, w_, 9.0, 0.14, 10 + k)
    key_loc(o, [(0, (-2.0 + 2 * k, 0, 0)), (E(0), (3.0 + 2 * k, 0, 0))])
    vis(o, [(0, S[1])])
    hook.append(o)
H0 = ant("H0", (0.4, 1.6, 0), 0.75, math.radians(-15), lift=True)
vis(H0, [(0, S[1])])
jitter(H0, 0.0)
key_loc(H0, [(0, (0.0, 1.6, 0)), (E(0), (1.0, 1.6, 0))])
# house trembles a little
for f in range(0, S[1], 2):
    houseg.rotation_euler = (0, random.uniform(-0.012, 0.012), 0); houseg.keyframe_insert("rotation_euler", frame=f)
houseg.rotation_euler = (0, 0, 0); houseg.keyframe_insert("rotation_euler", frame=S[1])

# =================== line 1: one ant on a kitchen scale ===================
T = 0.85
wood = mat("Wood", (0.75, 0.5, 0.28), 0.7)
TX, TY = -1.5, 0.6
tbl = [box("TableTop", (TX, TY, T - 0.03), (1.3, 0.75, 0.06), wood, bevel=0.01)]
for dx in (-0.58, 0.58):
    for dy in (-0.3, 0.3):
        tbl.append(box("TableLeg", (TX + dx, TY + dy, (T - 0.06) / 2), (0.06, 0.06, T - 0.06), wood))
scale_m = mat("ScaleBody", (0.97, 0.97, 0.98), 0.4)
plat_m = mat("ScalePlat", (0.75, 0.78, 0.82), 0.25, metal=0.6)
lcd_m = mat("LCD", (0.6, 0.9, 0.62), 0.4, emit=(0.5, 0.9, 0.55), emit_strength=0.8)
lcd_ink = mat("LCDInk", (0.02, 0.06, 0.03), 0.5)
PT = T + 0.0925
SA = (TX, TY + 0.02)
tbl += [box("ScaleBase", (SA[0], SA[1], T + 0.035), (0.46, 0.46, 0.07), scale_m, bevel=0.012),
        box("ScalePlat", (SA[0], SA[1], T + 0.085), (0.42, 0.42, 0.015), plat_m, bevel=0.004),
        box("LCD", (SA[0], SA[1] - 0.235, T + 0.035), (0.3, 0.02, 0.07), lcd_m)]
for o in tbl:
    vis(o, [(S[1], S[2])])
r0 = text("Read0", "0.000 g", (SA[0], SA[1] - 0.247, T + 0.035), 0.05, lcd_ink); vis(r0, [(S[1], S[1] + 12)])
r1 = text("Read1", "0.003 g", (SA[0], SA[1] - 0.247, T + 0.035), 0.05, lcd_ink); vis(r1, [(S[1] + 12, S[2])])
H1 = ant("H1", (SA[0], SA[1], PT), 0.12, math.radians(20))
vis(H1, [(S[1], S[2])])
key_loc(H1, [(S[1], (SA[0] + 0.35, SA[1] - 0.1, PT + 0.3)), (S[1] + 10, (SA[0], SA[1], PT))])

# =================== line 2: one ant lifts a sugar cube 50x its weight ===================
A2 = (2.2, 0.6)
R2 = 0.45
H2 = ant("H2", (A2[0], A2[1], 0), R2, math.radians(10), lift=True)
vis(H2, [(S[2], S[3])])
cube = boxc("SugarCube", (A2[0], A2[1] - 0.2, 0.45), (0.75, 0.75, 0.75), sugar_m, bevel=0.05)
vis(cube, [(S[2], S[3])])
CZ = 1.95 * R2 + 0.38
key_loc(cube, [(S[2], (A2[0] - 0.9, A2[1] - 0.6, 0.38)), (S[2] + 5, (A2[0] - 0.9, A2[1] - 0.6, 0.38)),
               (S[2] + 13, (A2[0], A2[1] - 0.2, CZ + 0.25)), (S[2] + 16, (A2[0], A2[1] - 0.2, CZ))])
keyrot(cube, [(S[2] + 5, (0, 0, 0)), (S[2] + 13, (0, 0, math.radians(20)))])
key_loc(H2, [(S[2], (A2[0], A2[1], 0)), (S[2] + 13, (A2[0], A2[1], 0)), (S[2] + 15, (A2[0], A2[1], -0.05)), (S[2] + 18, (A2[0], A2[1], 0))])
burst((A2[0], A2[1] - 0.4, CZ + 0.3), S[2] + 16, n=10, r=0.6, size=0.05, f_out=S[2] + 28)
# comparison: 50 little cubes the size of one ant's own weight line up beside it
for k in range(10):
    o = box("MiniCube", (A2[0] + 1.0 + (k % 5) * 0.16, A2[1] - 0.4 + (k // 5) * 0.16, 0.06), (0.11, 0.11, 0.11), sugar_m)
    vis(o, [(S[2] + 18 + k, S[3])])

# =================== line 3: you lifting two cars over your head ===================
P3 = (-3.0, 1.5)
c1 = car("Car1", (P3[0], P3[1], 2.4), (0.15, 0.5, 0.95))
c2 = car("Car2", (P3[0], P3[1], 3.85), (0.98, 0.78, 0.15))
plank3 = box("Plank3", (P3[0], P3[1], 2.36), (4.0, 1.9, 0.1), mat("PlankM", (0.6, 0.4, 0.22), 0.7))
for o in (c1, c2):
    vis(o, [(S[3], S[4])])
vis(plank3, [(S[3], S[4])])
key_loc(c2, [(S[3], (P3[0], P3[1], 9.0)), (S[3] + 7, (P3[0], P3[1], 3.85))])
key_loc(plank3, [(S[3], (0, 0, 0)), (S[3] + 7, (0, 0, -0.15)), (S[3] + 11, (0, 0, 0))])
key_loc(c1, [(S[3], (P3[0], P3[1], 2.4)), (S[3] + 7, (P3[0], P3[1], 2.25)), (S[3] + 11, (P3[0], P3[1], 2.4))])
burst((P3[0], P3[1] - 1.0, 3.9), S[3] + 7, n=12, r=1.6, size=0.07, f_out=S[3] + 20)
# a normal person next to you can barely lift one bag
you2, YD2 = person("Normal", (P3[0] + 3.6, P3[1] + 0.2, 0), 1.0, mat("Shirt2", (0.3, 0.75, 0.4), 0.6),
                   mat("Pants2", (0.25, 0.25, 0.3), 0.7), skin_m, mat("Hair2", (0.1, 0.07, 0.05), 0.8))
bag = box("Bag", (P3[0] + 3.6 + 0.42, P3[1] - 0.1, 0.45), (0.35, 0.3, 0.45), mat("BagM", (0.85, 0.7, 0.45), 0.8), bevel=0.04)
vis(you2, [(S[3], S[4])]); vis(bag, [(S[3], S[4])])
key_loc(bag, [(S[3] + 4, (0, 0, 0)), (S[3] + 10, (0, 0, 0.25)), (S[3] + 16, (0, 0, 0.05)), (S[3] + 22, (0, 0, 0.25))])

# =================== line 4: the secret? being tiny — a giant ant buckles, the tiny one holds ===================
G4 = (-3.4, 2.6)
big = ant("Big4", (G4[0], G4[1], 0), 1.6, math.radians(15))
keyscale(big, [(0, 0.001), (S[4] - 1, 0.001), (S[4], 1.0), (W(4, 0.35), 1.0), (W(4, 0.55), (1.12, 1.05, 0.42)), (W(4, 0.65), (1.1, 1.05, 0.5)), (E(4) - 1, (1.1, 1.05, 0.48)), (E(4), 0.001)])
for fc in fcurves(big):
    if fc.data_path == "scale":
        for p_ in fc.keyframe_points:
            if int(round(p_.co[0])) in (S[4] - 1, E(4) - 1):
                p_.interpolation = 'CONSTANT'

gload = boxc("BigLoad", (G4[0], G4[1] - 0.3, 3.6), (2.4, 2.4, 2.4), sugar_m, bevel=0.1)
vis(gload, [(S[4], S[5])])
key_loc(gload, [(S[4], (G4[0], G4[1] - 0.3, 3.2)), (W(4, 0.35), (G4[0], G4[1] - 0.3, 3.2)), (W(4, 0.55), (G4[0] + 0.4, G4[1] - 0.3, 2.0))])
keyrot(gload, [(W(4, 0.35), (0, 0, 0)), (W(4, 0.55), (0, math.radians(14), 0))])
burst((G4[0], G4[1] - 1.8, 0.4), W(4, 0.55), n=12, r=1.8, size=0.08, material=dust_m, f_out=E(4))
sm4 = ant("Small4", (0.6, 0.8, 0), 0.4, math.radians(-10), lift=True)
vis(sm4, [(S[4], S[5])])
sc4 = boxc("SmallLoad", (0.6, 0.6, 1.95 * 0.4 + 0.3), (0.6, 0.6, 0.6), sugar_m, bevel=0.04)
vis(sc4, [(S[4], S[5])])
for o in (sm4, sc4):
    key_loc(o, [(W(4, 0.55), (o.location.x, o.location.y, o.location.z)), (W(4, 0.65), (o.location.x, o.location.y, o.location.z + 0.15)),
                (W(4, 0.75), (o.location.x, o.location.y, o.location.z))])

# =================== line 5: strong muscles for their size (glowing muscles + barbell) ===================
A5 = (1.8, 0.7)
R5 = 0.55
H5 = ant("H5", (A5[0], A5[1], 0), R5, math.radians(-12), lift=True)
vis(H5, [(S[5], S[6])])
BZ = 1.95 * R5 + 0.1
bar = [seg("BarRod", (A5[0] - 1.1, A5[1] - 0.3, BZ), (A5[0] + 1.1, A5[1] - 0.3, BZ), 0.04, steel_m)]
for sx in (-1, 1):
    for k in range(2):
        o = cyl("Plate", (A5[0] + sx * (0.85 + k * 0.14), A5[1] - 0.3, BZ), 0.42 - k * 0.08, 0.12, mat("PlateM", (0.12, 0.12, 0.14), 0.5),
                rot=(0, math.radians(90), 0), verts=24)
        bar.append(o)
barg = group("BarG", (A5[0], A5[1] - 0.3, BZ))
attach(bar, barg)
vis(barg, [(S[5], S[6])])
key_loc(barg, [(S[5], (A5[0], A5[1] - 0.3, BZ - 0.5)), (S[5] + 8, (A5[0], A5[1] - 0.3, BZ + 0.1)), (S[5] + 12, (A5[0], A5[1] - 0.3, BZ))])
for k, (dx, dy, dz) in enumerate([(-0.4, -0.45, 1.2), (0.4, -0.45, 1.2), (-0.3, 0.0, 0.85), (0.3, 0.0, 0.85), (0.0, 0.02, 0.7)]):
    m_ = sphere("Musc", (A5[0] + dx * R5, A5[1] + dy * R5 - 0.05, dz * R5), 0.13 * R5 * 1.4, musc_m, scale=(1, 0.7, 1.3), sub=2)
    keyscale(m_, [(0, 0.001), (S[5] - 1, 0.001)] + [(S[5] + 2 + j * 6 + (0 if j % 2 else 3), 1.4 if j % 2 == 0 else 0.8) for j in range(6)] + [(S[6] - 1, 1.0), (S[6], 0.001)])
for k in range(3):
    bpy.ops.mesh.primitive_torus_add(major_radius=0.6, minor_radius=0.025, location=(A5[0], A5[1] - 0.3, 0.7 * R5))
    rg = bpy.context.object; rg.data.materials.append(musc_m); rg.rotation_euler = (math.radians(80), 0, 0)
    f = S[5] + 4 + k * 10
    keyscale(rg, [(0, 0.001), (f - 1, 0.001), (f, 0.4), (f + 12, 1.3), (f + 13, 0.001)])

# =================== line 6: 1,000 ants carry an apple ===================
AP = (-1.0, 1.0)
c6 = ground_carpet("Car6", AP[0], AP[1], 1.6, 1.3, 140.0, 0.06, 6)
apple = group("Apple", (AP[0], AP[1], 0.62))
ap = [sphere("ApBody", (AP[0], AP[1], 0.62), 0.5, apple_m, scale=(1, 1, 0.92), sub=3),
      seg("ApStem", (AP[0], AP[1], 1.02), (AP[0] + 0.05, AP[1], 1.25), 0.03, trunk_m),
      sphere("ApLeaf", (AP[0] + 0.16, AP[1], 1.2), 0.13, fol[1], scale=(1.6, 0.4, 0.7), sub=2)]
attach(ap, apple)
for o in (c6, apple):
    vis(o, [(S[6], S[7])])
    key_loc(o, [(S[6], (o.location.x - 1.4, o.location.y, o.location.z)), (E(6), (o.location.x + 1.4, o.location.y, o.location.z))])
key_loc(apple, [(S[6], (AP[0] - 1.4, AP[1], 0.62)), (W(6, 0.25), (AP[0] - 0.7, AP[1], 0.72)), (W(6, 0.5), (AP[0], AP[1], 0.62)),
                (W(6, 0.75), (AP[0] + 0.7, AP[1], 0.72)), (E(6), (AP[0] + 1.4, AP[1], 0.62))])

# =================== line 7: 1,000,000 ants lift a fridge ===================
FR = (3.0, 1.8)
c7 = ground_carpet("Car7", FR[0], FR[1], 3.0, 2.2, 55.0, 0.09, 7)
fr = group("FridgeG", (FR[0], FR[1], 0.32))
fp7 = [box("Fridge", (FR[0], FR[1], 0.32 + 1.0), (0.95, 0.85, 2.0), fridge_m, bevel=0.06),
       box("FridgeLine", (FR[0], FR[1] - 0.43, 0.32 + 1.35), (0.93, 0.02, 0.03), steel_m),
       box("FridgeH1", (FR[0] + 0.36, FR[1] - 0.46, 0.32 + 1.65), (0.05, 0.05, 0.4), steel_m),
       box("FridgeH2", (FR[0] + 0.36, FR[1] - 0.46, 0.32 + 0.9), (0.05, 0.05, 0.5), steel_m)]
attach(fp7, fr)
for o in (c7, fr):
    vis(o, [(S[7], S[8])])
key_loc(c7, [(S[7], (2.0, 0, 0)), (E(7), (-1.0, 0, 0))])
key_loc(fr, [(S[7], (FR[0] + 2.0, FR[1], 0.0)), (S[7] + 6, (FR[0] + 1.8, FR[1], 0.0)), (S[7] + 12, (FR[0] + 1.4, FR[1], 0.4)),
             (E(7), (FR[0] - 1.0, FR[1], 0.32))])
keyrot(fr, [(S[7] + 6, (0, 0, 0)), (S[7] + 12, (0, math.radians(-6), 0)), (S[7] + 20, (0, math.radians(4), 0)), (E(7), (0, 0, 0))])

# =================== line 8: one billion ants cover the whole garden ===================
BILL = []
for k, (cx, cy, sx_, sy_) in enumerate([(0, 1.6, 40, 6.0), (0, 6.2, 40, 3.2), (7.5, 10.9, 22, 3.6), (-14.5, 10.5, 7, 7.0), (-6.0, 7.0, 10, 1.0)]):
    o = ground_carpet(f"Bill{k}", cx, cy, sx_, sy_, 6.0, 0.14, 20 + k)
    BILL.append(o)
for k, o in enumerate(BILL):
    vis(o, [(S[8] + 2 + 3 * k, S[10])])
# a big "1,000,000,000" ant mound in the middle
# =================== line 9: 3 tons of ants balance two cars on a giant seesaw ===================
PX, PY, PZ = 9.0, 3.0, 1.4
steel = mat("SeeSaw", (0.95, 0.75, 0.2), 0.5)
pivot = cyl("Pivot", (PX, PY, 0.65), 0.95, 1.3, mat("PivotM", (0.3, 0.32, 0.38), 0.6), verts=3)
pivot.rotation_mode = 'ZXY'; pivot.rotation_euler = (math.radians(90), 0, math.radians(90))
plank = group("Plank", (PX, PY, PZ))
pl = box("PlankBoard", (PX, PY, PZ), (11.0, 2.6, 0.22), steel, bevel=0.04)
bpy.ops.mesh.primitive_cone_add(vertices=24, radius1=1.7, radius2=0.2, depth=2.0, location=(PX - 3.3, PY, PZ + 1.1))
heap = bpy.context.object; heap.name = "Heap"
bpy.ops.object.transform_apply(location=True)
heap_c = sphere("HeapCore", (PX - 3.3, PY, PZ + 0.6), 1.45, ant_dk, scale=(1, 1, 0.8), sub=2)
cone_core = cyl("HeapCone", (PX - 3.3, PY, PZ + 1.0), 1.55, 1.9, ant_dk, r2=0.1, verts=24)
carpet("HeapAnts", heap, 30.0, 0.11, 9, align=True)
cc1 = car("SCar1", (PX + 3.2, PY, PZ + 0.11), (0.15, 0.5, 0.95))
cc2 = car("SCar2", (PX + 3.2, PY, PZ + 0.11 + 1.45), (0.98, 0.78, 0.15))
attach([pl, heap, cone_core, cc1, cc2], plank)
heap_c.scale = (0.001,) * 3
vis(pivot, [(S[9], S[10])], tuple(pivot.scale)); vis(plank, [(S[9], S[10])])
TILT = math.radians(12)
for f, a in [(S[9], -TILT), (S[9] + 6, -TILT), (S[9] + 12, math.radians(4)), (S[9] + 16, math.radians(-2)), (S[9] + 20, 0)]:
    plank.rotation_euler = (0, a, 0); plank.keyframe_insert("rotation_euler", frame=f)
hd = ant("H9", (PX - 3.3, PY - 0.1, PZ + 2.12), 0.35, math.radians(-20), lift=True)
parent_to(hd, plank)
for o in (heap, cone_core, cc1, cc2, hd):
    pass
vis(hd, [(S[9], S[10])])

# =================== lines 10-13: lift force vs house weight, lift-off, crash ===================
# thick ring of ants around the house base (lines 10-13)
RING = []
for k, (cx, cy, sx_, sy_) in enumerate([(HX, fy - 0.75, HW + 3.0, 1.5), (HX, HY + HD / 2 + 0.75, HW + 3.0, 1.5),
                                        (HX - HW / 2 - 0.75, HY, 1.5, HD), (HX + HW / 2 + 0.75, HY, 1.5, HD),
                                        (HX, HY, HW - 0.2, HD - 0.2)]):
    o = ground_carpet(f"Ring{k}", cx, cy, sx_, sy_, 14.0, 0.12, 30 + k)
    RING.append(o)
    vis(o, [(S[10], S[14])])
# green "lift" arrows rising along the front wall
def arrow(name, loc, sz, m_):
    g = group(name, loc)
    ps = [cyl(name + "S", (loc[0], loc[1], loc[2] + sz * 0.45), sz * 0.16, sz * 0.9, m_, verts=12),
          cyl(name + "H", (loc[0], loc[1], loc[2] + sz * 1.05), sz * 0.36, sz * 0.4, m_, r2=0.0, verts=16)]
    attach(ps, g)
    return g
for k in range(7):
    x_ = HX - 3.6 + k * 1.2
    a_ = arrow("UpArr", (x_, fy - 1.6, 0), 0.9, arrow_m)
    t0 = S[10] + 2 + (k % 3) * 4
    key_loc(a_, [(t0, (x_, fy - 1.6, 0.0)), (t0 + 14, (x_, fy - 1.6, 3.5))])
    vis(a_, [(t0, t0 + 14)])
    if t0 + 30 < S[12]:
        key_loc(a_, [(t0 + 15, (x_, fy - 1.6, 0.0)), (t0 + 29, (x_, fy - 1.6, 3.5))])
        vis(a_, [(t0, t0 + 14), (t0 + 15, t0 + 29)])
# comparison bars beside the house: lift 150 t (green) vs house 100 t (red)
BXB = HX + HW / 2 + 2.2
BY2 = fy - 1.2
gbar = box("GBar", (BXB, BY2, 3.0), (2.0, 2.0, 6.0), gbar_m, bevel=0.06)
rbar = box("RBar", (BXB + 2.6, BY2, 2.0), (2.0, 2.0, 4.0), rbar_m, bevel=0.06)
for o, base_z in ((gbar, 0), (rbar, 0)):
    o.data.transform(Matrix.Translation((0, 0, -o.location.z)))
gbar.data.transform(Matrix.Translation((0, 0, 0)))
gt1 = text("GT", "150 t", (BXB, BY2 - 1.3, 7.0), 1.0, green_lab, extrude=0.05)
rt1 = text("RT", "100 t", (BXB + 2.6, BY2 - 1.3, 5.0), 1.0, red_lab, extrude=0.05)
ht = text("HT", "HOUSE", (BXB + 1.8, fy - 0.17, 1.4), 0.36, white_lab, extrude=0.03)
at = text("AT", "ANTS", (BXB, fy - 0.17, 1.4), 0.36, white_lab, extrude=0.03)
ht.data.size = 0.42; ht.location = (BXB + 2.6, BY2 - 1.03, 1.8)
at.data.size = 0.42; at.location = (BXB, BY2 - 1.03, 2.0)
keyscale(gbar, [(0, 0.001), (S[10] - 1, 0.001), (S[10], (1, 1, 0.001)), (S[10] + 10, (1, 1, 1.05)), (S[10] + 13, (1, 1, 1.0)), (S[12] - 1, (1, 1, 1)), (S[12], 0.001)])
keyscale(rbar, [(0, 0.001), (S[11] - 1, 0.001), (S[11], (1, 1, 0.001)), (S[11] + 10, (1, 1, 1.05)), (S[11] + 13, (1, 1, 1.0)), (S[12] - 1, (1, 1, 1)), (S[12], 0.001)])
gbar.location.z = 0; rbar.location.z = 0
for o, a in ((gt1, S[10] + 9), (at, S[10] + 9), (rt1, S[11] + 9), (ht, S[11] + 9)):
    vis(o, [(a, S[12])], tuple(o.scale))
# lift-off (line 12) and crash (line 13)
LZ = 4.5
key_loc(houseg, [(S[12], (HX, HY, 0)), (S[12] + 4, (HX, HY, 0)), (W(12, 0.55), (HX, HY, LZ + 0.3)), (W(12, 0.7), (HX, HY, LZ)),
                 (E(12) - 1, (HX, HY, LZ + 0.2)),
                 (S[13] + 3, (HX, HY, LZ + 0.25)), (S[13] + 9, (HX, HY, 0)), (S[13] + 12, (HX, HY, 0.25)), (S[13] + 15, (HX, HY, 0))])
keyrot(houseg, [(S[12] + 4, (0, 0, 0)), (W(12, 0.6), (0, math.radians(2.5), 0)), (E(12) - 1, (0, math.radians(-1.5), 0)),
                (S[13] + 9, (0, 0, 0))])
for k in range(26):
    a = random.uniform(0, 6.283)
    p0 = (HX + random.uniform(-HW / 2, HW / 2), fy - 0.3, 0.2)
    p1 = (p0[0] + random.uniform(-3.5, 3.5), p0[1] - random.uniform(1.0, 4.0), random.uniform(1.0, 3.5))
    p2 = (p1[0] + (p1[0] - p0[0]) * 0.5, p1[1] - 1.0, 0.1)
    ch = sphere("Chunk", p0, random.uniform(0.15, 0.32), dirt_m, sub=1, smooth=False)
    f0 = S[12] + 4 + k % 5
    key_loc(ch, [(f0, p0), (f0 + 8, p1), (f0 + 18, p2)])
    vis(ch, [(f0, f0 + 19)])
for k in range(18):
    a = k / 18 * 6.283
    p0 = (HX + 4.6 * math.cos(a), HY + 2.8 * math.sin(a), 0.3)
    p1 = (HX + 7.5 * math.cos(a), HY + 4.5 * math.sin(a), random.uniform(0.6, 1.4))
    du = sphere("Dust", p0, 0.28, dirt_m, sub=1, smooth=False)
    f0 = S[13] + 8
    key_loc(du, [(f0, p0), (f0 + 12, p1)])
    keyscale(du, [(0, 0.001), (f0 - 1, 0.001), (f0, 0.6), (f0 + 12, 1.6), (f0 + 13, 0.001)])

# =================== line 14: only ~20,000 ants fit around the walls (single file) ===================
FILE = []
for k, (cx, cy, sx_, sy_, rz) in enumerate([(HX, fy - 0.25, HW, 0.3, math.pi), (HX, HY + HD / 2 + 0.25, HW, 0.3, 0.0),
                                            (HX - HW / 2 - 0.25, HY, 0.3, HD, -math.pi / 2), (HX + HW / 2 + 0.25, HY, 0.3, HD, math.pi / 2)]):
    o = ground_carpet(f"File{k}", cx, cy, sx_, sy_, 14.0, 0.12, 40 + k, rotz=rz)
    FILE.append(o)
    vis(o, [(S[14], FRAMES)])
# glowing outline of the base
for k, (cx, cy, sx_, sy_) in enumerate([(HX, fy - 0.36, HW + 0.8, 0.05), (HX - HW / 2 - 0.36, HY, 0.05, HD + 0.8), (HX + HW / 2 + 0.36, HY, 0.05, HD + 0.8)]):
    o = box("Outline", (cx, cy, 0.03), (sx_, sy_, 0.04), lab_m)
    vis(o, [(S[14] + 4, S[15])])

# =================== line 15: the rest just stand there cheering ===================
CHEER = []
for k, (cx, cy, sx_, sy_) in enumerate([(0, 1.0, 36, 3.2), (0, 4.6, 36, 3.6), (8, 9.5, 18, 4.0), (-13, 8.5, 10, 6.0)]):
    o = ground_carpet(f"Cheer{k}", cx, cy, sx_, sy_, 6.0, 0.15, 50 + k)
    key_loc(o, [(S[15], (0, 0, 0)), (FRAMES, (0, 0, 0))])
    for f in range(S[15], FRAMES, 4):
        o.location = (0, 0, 0.18 if ((f - S[15]) // 4 + k) % 2 == 0 else 0.0); o.keyframe_insert("location", frame=f)
    vis(o, [(S[15], FRAMES)])
    CHEER.append(o)
for k in range(40):
    p0 = (random.uniform(-7, 9), random.uniform(0, 10), random.uniform(5, 8))
    cf = boxc("Conf", p0, (0.22, 0.04, 0.14), conf_ms[k % 4])
    f0 = S[15] + (k % 10)
    key_loc(cf, [(f0, p0), (FRAMES, (p0[0] + random.uniform(-1, 1), p0[1], p0[2] - random.uniform(4, 6)))])
    keyrot(cf, [(f0, (0, 0, 0)), (FRAMES, (random.uniform(-6, 6), random.uniform(-6, 6), random.uniform(-6, 6)))])
    vis(cf, [(f0, FRAMES)])
H15 = ant("H15", (1.6, 0.4, 0), 0.75, math.radians(-10), lift=True)
vis(H15, [(S[15], FRAMES)])
for f in range(S[15], FRAMES, 4):
    H15.location = (1.6, 0.4, 0.25 if ((f - S[15]) // 4) % 2 == 0 else 0.0); H15.keyframe_insert("location", frame=f)

# =================== "you": line 3 lifter ===================
jumps(you, [(0, (0, 40, 0)), (S[3], (P3[0], P3[1], 0)), (S[4], (0, 40, 0))])
for k, ag in enumerate(YD["arms"]):
    sx = -1 if k == 0 else 1
    keyrot(ag, [(S[3] - 1, (0, 0, 0)), (S[3], (0, sx * math.radians(165), 0)), (S[4], (0, 0, 0))])
vis(you, [(S[3], S[4])])
for ag in YD2["arms"][1:]:
    keyrot(ag, [(S[3], (0, 0, 0))])

# ---------------- views (camera, subject) per line; subject sits in the lower third ----------------
def orb(subj, dist, az0, az1, h=1.0, d1=None):
    d1 = dist if d1 is None else d1
    a0, a1 = math.radians(az0), math.radians(az1)
    return ((subj[0] + math.sin(a0) * dist, subj[1] - math.cos(a0) * dist, subj[2] + h), subj), \
           ((subj[0] + math.sin(a1) * d1, subj[1] - math.cos(a1) * d1, subj[2] + h), subj)
V, V2 = {}, {}
HC = (HX, HY - 3.0, 1.5)
HZ = 3.2
V[0], V2[0] = orb((0.5, 7.0, 2.6), 16.0, -14, -4, 2.0, 13.5)
V[1], V2[1] = orb((SA[0], SA[1], PT + 0.08), 1.1, 12, -10, 0.3)
V[2], V2[2] = orb((A2[0], A2[1], 0.9), 4.6, -12, 4, 0.8, 4.2)
V[3], V2[3] = orb((P3[0] + 1.6, P3[1], 2.2), 13.0, 8, -6, 1.0, 12.0)
V[4], V2[4] = orb((-1.6, 2.0, 1.6), 11.0, -8, 8, 1.0, 10.0)
V[5], V2[5] = orb((A5[0], A5[1], 0.9), 4.6, 10, -10, 0.6, 4.2)
V[6], V2[6] = orb((AP[0], AP[1], 0.6), 4.8, -12, 8, 0.6)
V[7], V2[7] = orb((FR[0], FR[1], 1.1), 7.5, 12, -8, 0.8, 7.0)
V[8], V2[8] = orb((1.0, 7.0, 2.0), 30.0, -12, 4, 6.0, 26.0)
V[9], V2[9] = orb((PX, PY, 2.6), 14.5, -6, 6, 1.0, 13.5)
V[10], V2[10] = orb((HX + 1.5, HY - 2.0, HZ), 20.0, -10, 2, 1.0, 18.0)
V[11], V2[11] = orb((HX + 3.0, HY - 2.0, HZ), 18.5, 4, 14, 1.0, 17.0)
V[12], V2[12] = orb((HX, HY - 2.0, HZ + 2.0), 19.0, -14, -2, 0.0, 21.0)
V[13], V2[13] = orb((HX, HY - 2.0, HZ), 19.0, 4, -6, 0.5, 20.0)
V[14], V2[14] = orb((HX - 1.0, fy, 1.0), 13.0, -28, -14, 2.0, 12.0)
V[15], V2[15] = orb((1.5, 5.0, 1.4), 16.0, 8, -4, 2.0, 14.0)
V[16], V2[16] = orb((1.5, 9.0, 2.6), 15.0, -6, 8, 1.5, 19.0)
VM = {i: (tuple((Vector(V[i][0]) + Vector(V2[i][0])) / 2), V[i][1]) for i in V}

def LB(i, name, body, m_, size=None, f_in=None, f_out=None, Dk=0.55, end=False, v=0.26, u=0.0):
    view = V2[i] if end else VM[i]
    cl = Vector(CL(view)); D = (Vector(view[1]) - cl).length * Dk
    s_ = 0.85 * fit(body, D, size if size else 1e9)
    return label(name, body, view, D, v, s_, m_, (S[i] + 3) if f_in is None else f_in,
                 E(i) if f_out is None else f_out, u)
LB(0, "L0", "1 BILLION ANTS?!", red_lab)
LB(1, "L1", "3 mg", lab_m, v=0.3)
LB(2, "L2", "50x ITS WEIGHT", lab_m)
LB(3, "L3", "YOU x 50 = 2 CARS", lab_m)
LB(4, "L4", "SMALL = STRONG", green_lab)
LB(5, "L5", "MUSCLE POWER", pink_lab)
LB(6, "L6", "1,000 = AN APPLE", lab_m)
LB(7, "L7", "1,000,000 = A FRIDGE", lab_m)
LB(8, "L8", "1,000,000,000", red_lab, Dk=0.4)
LB(9, "L9", "3 TONS OF ANTS", lab_m, Dk=0.45)
LB(10, "L10", "LIFT: 150 TONS", green_lab, Dk=0.45)
LB(11, "L11", "HOUSE: 100 TONS", red_lab, Dk=0.45)
LB(12, "L12", "LIFT OFF!", lab_m, Dk=0.45, f_in=W(12, 0.5))
LB(13, "L13", "THE TWIST...", white_lab, Dk=0.45)
LB(14, "L14", "ONLY ~20,000 FIT", lab_m)
LB(15, "L15", "THE REST: CHEERING!", pink_lab, Dk=0.45)
LB(16, "L16", "LET THEM TRY?", lab_m, end=True, f_in=S[16] + 6, Dk=0.45)

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
