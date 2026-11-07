# Day 13 — What if everyone on Earth got a million dollars?  Build: python3 episodes/013-million-everyone/scene.py
# Reference style: base (helpers, lawn/soil, house, garden) copied from episodes/003-lift-million-ref / 006-mantis-punch
import bpy, math, random, os, json
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
random.seed(13)
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
def E(i):
    return S[i + 1] if i + 1 < len(S) else FRAMES
def W(i, fr):
    return int(S[i] + fr * (E(i) - S[i]))

bill_m = mat("Bill", (0.3, 0.68, 0.25), 0.8)
bill_ink = mat("BillInk", (0.12, 0.38, 0.16), 0.7)
band100 = mat("Band100", (0.95, 0.75, 0.3), 0.6)
cash_cube_m = stripe_mat("CashCube", (0.3, 0.68, 0.25), (0.18, 0.48, 0.15), axis="Z", freq=55.0, thresh=0.3)
leather = mat("Leather", (0.42, 0.24, 0.12), 0.55)
gold = mat("Latch", (1.0, 0.8, 0.25), 0.3, metal=0.9)
red_m = mat("RedM", (0.9, 0.12, 0.1), 0.5)
white_m = mat("WhiteM", (0.97, 0.97, 0.95), 0.5)
black_ink = mat("BlackInk", (0.03, 0.03, 0.04), 0.5)
gspark_m = glow_mat("GSpark", (0.4, 1.0, 0.4), 4.0)
conf_ms = [glow_mat(f"Conf{i}", c, 1.5) for i, c in enumerate([(1, 0.2, 0.3), (1, 0.85, 0.1), (0.2, 0.6, 1), (0.3, 0.95, 0.3), (0.9, 0.3, 1)])]

def briefcase(name, cx, cy, cz, k=1.0):
    g = group(name, (cx, cy, cz))
    parts = [box(name + "C", (cx, cy, cz), (0.46 * k, 0.13 * k, 0.34 * k), leather, bevel=0.015 * k),
             box(name + "S", (cx, cy, cz + 0.12 * k), (0.47 * k, 0.135 * k, 0.012 * k), mat(name + "Sm", (0.3, 0.16, 0.08), 0.6)),
             tube(name + "H", [(cx - 0.07 * k, cy, cz + 0.17 * k), (cx - 0.06 * k, cy, cz + 0.22 * k), (cx + 0.06 * k, cy, cz + 0.22 * k), (cx + 0.07 * k, cy, cz + 0.17 * k)],
                  [0.014 * k] * 4, mat(name + "Hm", (0.2, 0.1, 0.05), 0.5))]
    for sx in (-1, 1):
        parts.append(box(name + "L", (cx + sx * 0.14 * k, cy - 0.068 * k, cz + 0.12 * k), (0.04 * k, 0.012 * k, 0.03 * k), gold))
    attach(parts, g)
    return g

def bill_obj(name, loc, k=1.0):
    return box(name, loc, (0.31 * k, 0.13 * k, 0.006 * k), bill_m)

def rain(n, cx, cy, spread, z0, z1, f0, f1, k=1.0, f_gone=None, mats=None, size=None):
    out = []
    for i in range(n):
        p = (cx + random.uniform(-spread, spread), cy + random.uniform(-spread * 0.6, spread * 0.6), random.uniform(z0, z1))
        if mats:
            b = box("Conf", p, size or (0.07, 0.07, 0.01), random.choice(mats))
        else:
            b = bill_obj("Rain", p, k)
        st = f0 + random.randint(0, max(1, (f1 - f0) // 3))
        zend = max(0.03, p[2] - random.uniform(0.6, 1.0) * (z1 - 0.0))
        b.rotation_euler = (random.uniform(-1, 1), random.uniform(-1, 1), random.uniform(0, 6)); b.keyframe_insert("rotation_euler", frame=st)
        b.rotation_euler = (b.rotation_euler[0] + random.uniform(-4, 4), b.rotation_euler[1] + random.uniform(-4, 4), b.rotation_euler[2] + 3)
        b.keyframe_insert("rotation_euler", frame=f1)
        key_loc(b, [(st, p), (f1, (p[0] + random.uniform(-0.4, 0.4), p[1], zend))])
        hide_until(b, st)
        gone_at(b, f_gone or f1 + 2, 3)
        out.append(b)
    return out

# ---------------- YOU ----------------
YX, YY = 0.0, 0.5
you, yd = person("You", (YX, YY, 0), 1.0, mat("YouShirt", (0.95, 0.3, 0.35), 0.7), mat("YouPants", (0.18, 0.22, 0.38), 0.8),
                 skin_m, mat("YouHair", (0.25, 0.14, 0.06), 0.8))
case_y = briefcase("YouCase", YX + 0.38, YY - 0.08, 0.55)
parent_to(case_y, yd["arms"][1])
pop(case_y, S[0] + 10, 6)
armL, armR = yd["arms"]
def arms_up(fs):
    for f, up in fs:
        a = math.radians(150) * up
        keyrot(armL, [(f, (0, a, 0))]); keyrot(armR, [(f, (0, -a, 0))])

# line 0: money rain + $1,000,000
rain(40, YX, YY, 2.4, 2.4, 5.0, 0, S[1] + 4, k=1.0, f_gone=S[1] + 6)

# ---------------- crowd (lines 1-2, 7) ----------------
crowd = []
shirts = [mat(f"CS{i}", c, 0.7) for i, c in enumerate([(0.2, 0.55, 0.95), (0.95, 0.75, 0.15), (0.35, 0.8, 0.35), (0.85, 0.35, 0.85),
                                                        (1.0, 0.5, 0.2), (0.25, 0.8, 0.8), (0.95, 0.95, 0.95)])]
skins = [mat(f"SK{i}", c, 0.6) for i, c in enumerate([(0.95, 0.74, 0.58), (0.72, 0.5, 0.34), (0.48, 0.32, 0.2), (0.98, 0.82, 0.68)])]
hairs = [mat(f"HR{i}", c, 0.8) for i, c in enumerate([(0.1, 0.07, 0.05), (0.35, 0.2, 0.08), (0.85, 0.65, 0.3), (0.5, 0.5, 0.5)])]
pants_m = mat("CPants", (0.2, 0.24, 0.4), 0.8)
def mini(name, x, y, k=1.0):
    g = group(name, (x, y, 0))
    sh = random.choice(shirts); sk = random.choice(skins)
    parts = [cyl(name + "Lg", (x, y, 0.4 * k), 0.17 * k, 0.8 * k, pants_m, verts=12),
             cyl(name + "B", (x, y, 1.1 * k), 0.3 * k, 0.72 * k, sh, r2=0.22 * k, verts=16),
             sphere(name + "H", (x, y, 1.68 * k), 0.24 * k, sk, sub=2),
             sphere(name + "Hr", (x, y + 0.04 * k, 1.8 * k), 0.23 * k, random.choice(hairs), scale=(1.05, 1.0, 0.55), sub=2)]
    for sx in (-1, 1):
        parts.append(sphere(name + "E", (x + sx * 0.08 * k, y - 0.215 * k, 1.72 * k), 0.035 * k, eyeb, sub=1))
    arms = []
    for sx in (-1, 1):
        ag = group(name + "A", (x + sx * 0.3 * k, y, 1.35 * k))
        attach([tube(name + "Ar", [(x + sx * 0.3 * k, y, 1.36 * k), (x + sx * 0.38 * k, y - 0.03 * k, 1.05 * k), (x + sx * 0.38 * k, y - 0.06 * k, 0.8 * k)],
                     [0.07 * k] * 3, sh), sphere(name + "Hd", (x + sx * 0.38 * k, y - 0.06 * k, 0.76 * k), 0.065 * k, sk, sub=1)], ag)
        arms.append(ag)
    attach(parts + arms, g)
    return g, arms
CX_ = [-3.6, -1.2, 1.2, 3.6, 6.0, 8.2]
CY_ = [2.4, 4.4, 6.4, 8.4, 10.4]
cases = []
for j, cy in enumerate(CY_):
    for i, cx in enumerate(CX_):
        x, y = cx + random.uniform(-0.35, 0.35) + (0.6 if j % 2 else 0), cy + random.uniform(-0.25, 0.25)
        g, arms = mini(f"P{i}{j}", x, y)
        f0 = S[1] + (i + j) // 2
        keyscale(g, [(0, 0.001), (f0 - 1, 0.001), (f0 + 4, 1.12), (f0 + 6, 1.0), (S[3], 1.0), (S[3] + 1, 0.001),
                     (S[7] - 1, 0.001), (S[7] + 3, 1.0), (E(7) - 3, 1.0), (E(7), 0.001)])
        # line 7: everyone partying (jump + arms up)
        ph = random.randint(0, 5)
        for k_ in range(3):
            fj = S[7] + 2 + ph + k_ * 8
            if fj + 8 < E(7):
                key_loc(g, [(fj, (x, y, 0)), (fj + 4, (x, y, 0.45)), (fj + 8, (x, y, 0))])
        for sx, ag in zip((-1, 1), arms):
            keyrot(ag, [(S[7], (0, 0, 0)), (S[7] + 3, (0, -sx * math.radians(150), 0)), (E(7), (0, -sx * math.radians(150), 0))])
        # briefcase drops into the right hand (line 1), then all cases fly up (line 2)
        hx, hy, hz = x + 0.38, y - 0.1, 0.55
        c = briefcase(f"Case{i}{j}", hx, hy, hz)
        fd = S[1] + 4 + int((i * 5 + j * 3) % 18 * 0.9)
        fu = S[2] + 1 + random.randint(0, 6)
        key_loc(c, [(fd - 6, (hx, hy, hz + 7)), (fd, (hx, hy, hz)), (fu, (hx, hy, hz)),
                    (fu + 8, (hx + (2.2 - hx) * 0.4, hy + (6.0 - hy) * 0.4, hz + 2.5)),
                    (E(2), (2.2 + (hx - 2.2) * 0.25, 6.0 + (hy - 6.0) * 0.25, 7.5 + random.uniform(-1, 1)))])
        keyrot(c, [(fu, (0, 0, 0)), (E(2), (random.uniform(-3, 3), random.uniform(-3, 3), random.uniform(-3, 3)))])
        hide_until(c, fd - 6); gone_at(c, S[3] + 1, 1)
        cases.append(c)

# ---------------- line 3-4: $8 quadrillion as a 450 m cube of $100 bills + 12 Great Pyramids ----------------
CUBE = 450.0
QX, QY = 0.0, 600.0 + CUBE / 2
big_m = stripe_mat("BigCash", (0.3, 0.68, 0.25), (0.2, 0.5, 0.17), axis="Z", freq=0.16, thresh=0.55)
qg = group("Quad", (QX, QY, 0))
qp = [box("QCube", (QX, QY, CUBE / 2), (CUBE, CUBE, CUBE), big_m)]
for dx in (-0.25, 0.25):
    qp.append(box("QBand", (QX + dx * CUBE, QY, CUBE / 2), (24, CUBE + 2, CUBE + 1), band100))
attach(qp, qg)
keyscale(qg, [(0, (1, 1, 0.001)), (S[3] - 1, (1, 1, 0.001)), (S[3] + 7, (1, 1, 1.08)), (S[3] + 10, (1, 1, 1.0)), (S[5] - 1, (1, 1, 1.0)), (S[5], 0.001)])
sand_m = stripe_mat("Sand", (0.86, 0.72, 0.46), (0.7, 0.56, 0.34), axis="Z", freq=0.9, thresh=0.6)
pyr = []
for k in range(12):
    i, j = k % 3, k // 3
    px, py = 380 + i * 255, QY - 330 + j * 250
    p = cyl(f"Pyr{k}", (px, py, 73), 230 / math.sqrt(2), 146, sand_m, r2=0.0, verts=4)
    p.rotation_euler = (0, 0, math.radians(45))
    pop(p, S[4] + 2 + int(k * 1.6), 5, S[5])
    pyr.append(p)

# ---------------- line 5: stack of bills past Pluto (space set, schematic distances) ----------------
ZS = 30000.0
space_m = glow_mat("Space", (0.012, 0.018, 0.06), 1.0)
env = sphere("SpaceDome", (1000, 0, ZS), 3600, space_m, sub=3)
env.visible_shadow = False
star_m = glow_mat("Star", (1, 1, 0.95), 6.0)
for i in range(260):
    th = random.uniform(0, 2 * math.pi); ph = random.uniform(-1.2, 1.2)
    p = (1000 + 3300 * math.cos(ph) * math.cos(th), 3300 * math.cos(ph) * math.sin(th), ZS + 3300 * math.sin(ph))
    st = sphere("Star", p, random.uniform(4, 9), star_m, sub=1, smooth=False); st.visible_shadow = False
def planet(name, x, r, col, emit=0.25):
    return sphere(name, (x, 0, ZS), r, mat(name + "M", col, 0.6, emit=col, emit_strength=emit), sub=3)
earth = planet("Earth", 0, 34, (0.15, 0.4, 0.95))
for (a, b_, s_) in [(0.6, 0.3, 14), (2.2, -0.2, 12), (4.0, 0.5, 10), (5.2, -0.6, 9)]:
    sphere("Land", (34 * math.cos(a) * math.cos(b_), 34 * math.sin(a) * math.cos(b_), ZS + 34 * math.sin(b_)), s_,
           mat("LandM", (0.25, 0.7, 0.25), 0.7, emit=(0.25, 0.7, 0.25), emit_strength=0.2), scale=(1, 1, 0.6), sub=2)
planet("Moon", 120, 9, (0.75, 0.75, 0.75))
planet("Mars", 420, 18, (0.9, 0.35, 0.15))
jup = stripe_mat("Jup", (0.9, 0.7, 0.45), (0.7, 0.45, 0.3), axis="Z", freq=0.25, thresh=0.3)
sphere("Jupiter", (800, 0, ZS), 70, jup, sub=3)
planet("Saturn", 1180, 52, (0.95, 0.82, 0.5))
ring = cyl("Ring", (1180, 0, ZS), 100, 1.5, mat("RingM", (0.85, 0.75, 0.55), 0.6, emit=(0.85, 0.75, 0.55), emit_strength=0.2), verts=48)
ring.rotation_euler = (math.radians(70), math.radians(15), 0)
planet("Uranus", 1480, 34, (0.5, 0.9, 0.95))
planet("Neptune", 1730, 33, (0.2, 0.35, 0.95))
PL = 2000
pluto = planet("Pluto", PL, 12, (0.9, 0.8, 0.7), emit=0.45)
stack_m = stripe_mat("StackM", (0.3, 0.75, 0.25), (0.95, 0.75, 0.3), axis="X", freq=0.35, thresh=0.85)
stg = group("StackG", (36, 0, ZS))
sb_ = box("Stack", (36 + 1150, 0, ZS), (2300, 9, 9), stack_m)
attach([sb_], stg)
keyscale(stg, [(0, (0.001, 1, 1)), (S[5], (0.001, 1, 1)), (W(5, 0.85), (1, 1, 1))])

# ---------------- line 6: you quit — WORK sign gets kicked, party ----------------
post_m = mat("Post", (0.55, 0.36, 0.2), 0.8)
wg = group("WorkSign", (1.5, 1.1, 0))
wp = [box("WPost", (1.5, 1.1, 0.6), (0.08, 0.08, 1.2), post_m),
      box("WBoard", (1.5, 1.07, 1.35), (1.1, 0.06, 0.45), mat("WorkB", (0.25, 0.35, 0.6), 0.6)),
      text("WTxt", "WORK", (1.5, 1.03, 1.35), 0.27, white_lab, extrude=0.01)]
attach(wp, wg)
hide_until(wg, S[6])
fk = W(6, 0.45)
key_loc(wg, [(fk, (1.5, 1.1, 0)), (fk + 10, (4.5, 6.0, 5.0))])
keyrot(wg, [(fk, (0, 0, 0)), (fk + 10, (2.5, 1.0, 3.0))])
gone_at(wg, fk + 10, 2)
for f, z in [(fk - 4, 0), (fk, 0.35), (fk + 4, 0), (fk + 9, 0.5), (fk + 14, 0)]:
    you.location = (YX, YY, z); you.keyframe_insert("location", frame=f)
arms_up([(fk - 2, 0), (fk + 2, 1), (S[7] + 6, 1), (S[7] + 10, 0)])
rain(70, YX, YY, 2.6, 2.6, 4.6, fk, E(6) + 8, mats=conf_ms, f_gone=S[7] + 6, size=(0.09, 0.09, 0.012))
rain(90, 2.2, 6.4, 6.5, 3.0, 6.0, S[7], E(7) + 4, mats=conf_ms, f_gone=E(7), size=(0.12, 0.12, 0.015))
bal_ms = [mat(f"Bal{i}", c, 0.3) for i, c in enumerate([(1, 0.2, 0.3), (1, 0.85, 0.1), (0.2, 0.6, 1), (0.9, 0.3, 1)])]
for i in range(7):
    bx_, by_ = YX + random.uniform(-2.2, 2.2), YY + random.uniform(0.6, 2.5)
    bg_ = group("Balloon", (bx_, by_, 0.4))
    attach([sphere("BalS", (bx_, by_, 1.2), 0.28, random.choice(bal_ms), scale=(1, 1, 1.2), sub=2),
            tube("BalStr", [(bx_, by_, 0.86), (bx_ + 0.05, by_, 0.4)], [0.008, 0.008], white_m)], bg_)
    f0 = fk + random.randint(0, 6)
    key_loc(bg_, [(f0, (bx_, by_, 0.0)), (E(6) + 10, (bx_, by_, 3.2))])
    hide_until(bg_, f0); gone_at(bg_, S[7] + 8, 3)

# ---------------- line 8: no farmers, no truckers, no bakers (CLOSED) ----------------
def closed_sign(name, x, y, f_in, f_out, h=2.0):
    g = group(name, (x, y, 0))
    attach([box(name + "P", (x, y, h / 2), (0.08, 0.08, h), post_m),
            box(name + "B", (x, y - 0.02, h + 0.15), (1.3, 0.06, 0.5), red_m, bevel=0.02),
            text(name + "T", "CLOSED", (x, y - 0.065, h + 0.15), 0.28, white_lab, extrude=0.01)], g)
    pop(g, f_in, 6, f_out)
    return g
tyre_m = mat("Tyre", (0.06, 0.06, 0.06), 0.9)
ST_Y = 5.0
# tractor
TRX = -4.6
trg = group("Tractor", (TRX, ST_Y, 0))
tp = [box("TrBody", (TRX + 0.3, ST_Y, 0.9), (1.8, 0.9, 0.6), mat("TrRed", (0.85, 0.15, 0.1), 0.5), bevel=0.06),
      box("TrCab", (TRX - 0.25, ST_Y, 1.55), (0.8, 0.85, 0.8), mat("TrGlass", (0.5, 0.75, 0.9), 0.2), bevel=0.04),
      box("TrRoof", (TRX - 0.25, ST_Y, 1.98), (0.95, 1.0, 0.08), mat("TrRed2", (0.85, 0.15, 0.1), 0.5)),
      cyl("TrPipe", (TRX + 0.8, ST_Y + 0.2, 1.5), 0.05, 0.8, black_ink, verts=8)]
for dy in (-0.55, 0.55):
    tp.append(cyl("TrWB", (TRX - 0.35, ST_Y + dy, 0.6), 0.6, 0.32, tyre_m, rot=(math.radians(90), 0, 0), verts=20))
    tp.append(cyl("TrWF", (TRX + 0.9, ST_Y + dy, 0.35), 0.35, 0.25, tyre_m, rot=(math.radians(90), 0, 0), verts=16))
attach(tp, trg)
# hay bales
hay_m = mat("Hay", (0.95, 0.8, 0.35), 0.9)
for dx in (-1.6, -1.1):
    tp2 = cyl("Hay", (TRX + dx, ST_Y - 1.0, 0.35), 0.35, 0.6, hay_m, rot=(math.radians(90), 0, 0), verts=16)
    pop(tp2, S[8], 5, E(8))
pop(trg, S[8], 5, E(8))
closed_sign("ClosedA", TRX + 1.4, ST_Y - 1.0, W(8, 0.0) + 3, E(8))
# truck
TKX = 1.0
tkg = group("Truck", (TKX, ST_Y, 0))
tk = [box("TkCab", (TKX - 1.25, ST_Y, 1.0), (0.9, 1.1, 1.3), mat("TkBlue", (0.2, 0.5, 0.95), 0.4), bevel=0.08),
      box("TkWin", (TKX - 1.71, ST_Y, 1.3), (0.04, 0.95, 0.45), mat("TkGlass", (0.3, 0.45, 0.6), 0.1)),
      box("TkBox", (TKX + 0.4, ST_Y, 1.25), (2.3, 1.15, 1.6), mat("TkBoxM", (0.95, 0.95, 0.92), 0.6), bevel=0.04)]
for dx in (-1.25, 0.0, 1.0):
    for dy in (-0.55, 0.55):
        tk.append(cyl("TkW", (TKX + dx, ST_Y + dy, 0.32), 0.32, 0.22, tyre_m, rot=(math.radians(90), 0, 0), verts=16))
attach(tk, tkg)
pop(tkg, S[8], 5, E(8))
closed_sign("ClosedB", TKX + 0.2, ST_Y - 1.0, W(8, 0.33) + 2, E(8))
# bakery stall
BKX = 6.2
awn_m = stripe_mat("Awning", (0.95, 0.95, 0.95), (0.9, 0.25, 0.3), axis="X", freq=9.0, thresh=0.0)
bread_m = mat("Bread", (0.85, 0.55, 0.22), 0.6)
def stall(name, x, y, sign, signm):
    g = group(name, (x, y, 0))
    p = [box(name + "Ctr", (x, y, 0.5), (2.8, 0.8, 1.0), mat(name + "CtrM", (0.75, 0.5, 0.3), 0.7), bevel=0.03),
         box(name + "Back", (x, y + 0.9, 1.1), (2.8, 0.2, 2.2), mat(name + "BackM", (0.95, 0.9, 0.8), 0.7)),
         box(name + "Awn", (x, y + 0.1, 2.45), (3.1, 1.9, 0.1), awn_m, rot=(math.radians(-14), 0, 0)),
         box(name + "Sgn", (x, y - 0.85, 2.85), (1.8, 0.08, 0.5), signm, bevel=0.03),
         text(name + "SgT", sign, (x, y - 0.9, 2.85), 0.3, white_lab, extrude=0.01)]
    for sx in (-1, 1):
        p.append(box(name + "Pst", (x + sx * 1.45, y - 0.75, 1.2), (0.08, 0.08, 2.4), white_m))
        p.append(box(name + "Pst2", (x + sx * 1.45, y + 0.9, 1.2), (0.08, 0.08, 2.4), white_m))
    attach(p, g)
    return g, p
bkg, bkp = stall("Bakery", BKX, ST_Y, "BAKERY", mat("BakSign", (0.6, 0.35, 0.15), 0.6))
for i in range(4):
    lb_ = sphere("Loaf", (BKX - 0.9 + i * 0.6, ST_Y, 1.1), 0.26, bread_m, scale=(1.0, 0.5, 0.42), sub=2)
    bkp.append(lb_)
attach(bkp, bkg)
pop(bkg, S[8], 5, E(8))
closed_sign("ClosedC", BKX + 1.7, ST_Y - 1.3, W(8, 0.66) + 2, E(8))

# ---------------- lines 9-12: the shop (same stuff), money flood, prices explode, $3,000 burger ----------------
SHX, SHY = 1.5, 5.6
shg, shp = stall("Shop", SHX, SHY, "SHOP", mat("ShopSign", (0.15, 0.45, 0.85), 0.6))
TOP = 1.0
items = []
# bread
items.append((-1.0, [sphere("SBread", (SHX - 1.0, SHY - 0.05, TOP + 0.12), 0.3, bread_m, scale=(1.0, 0.5, 0.42), sub=2)]))
# burger (big, cartoon)
bun_m = mat("Bun", (0.92, 0.6, 0.25), 0.5); patty_m = mat("Patty", (0.35, 0.18, 0.08), 0.8)
let_m = mat("Lettuce", (0.35, 0.8, 0.25), 0.7); cheese_m = mat("Cheese", (1.0, 0.8, 0.15), 0.5)
BGX = SHX - 0.3
bp = [cyl("BunB", (BGX, SHY - 0.05, TOP + 0.05), 0.22, 0.1, bun_m, verts=24),
      cyl("PattyM", (BGX, SHY - 0.05, TOP + 0.13), 0.24, 0.08, patty_m, verts=24),
      box("CheeseM", (BGX, SHY - 0.05, TOP + 0.18), (0.38, 0.38, 0.02), cheese_m, rot=(0, 0, math.radians(45))),
      cyl("LettuceM", (BGX, SHY - 0.05, TOP + 0.2), 0.25, 0.03, let_m, verts=12),
      sphere("BunT", (BGX, SHY - 0.05, TOP + 0.22), 0.23, bun_m, scale=(1, 1, 0.6), sub=3)]
for k in range(6):
    a = k * 1.05
    bp.append(sphere("Sesame", (BGX + 0.12 * math.cos(a), SHY - 0.05 + 0.12 * math.sin(a) - 0.04, TOP + 0.34), 0.018, white_m, scale=(1, 0.6, 0.5), sub=1))
items.append((-0.3, bp))
apple_m = mat("Apple", (0.9, 0.12, 0.12), 0.35)
ap = []
for dx, dy in [(-0.12, 0), (0.12, 0), (0, 0.1)]:
    ap.append(sphere("Apple", (SHX + 0.45 + dx, SHY - 0.05 + dy, TOP + 0.1), 0.11, apple_m, sub=2))
items.append((0.45, ap))
milk = [box("Milk", (SHX + 1.1, SHY - 0.05, TOP + 0.2), (0.2, 0.2, 0.4), white_m),
        box("MilkBand", (SHX + 1.1, SHY - 0.155, TOP + 0.22), (0.2, 0.01, 0.12), mat("MilkB", (0.2, 0.5, 0.95), 0.5))]
items.append((1.1, milk))
for _, ps in items:
    shp += ps
attach(shp, shg)
pop(shg, S[9], 6)
gone_at(shg, S[14], 3)
# price tags: normal -> x100 -> thousands
PR = [("$3", "$300", "$2,000"), ("$5", "$500", "$3,000"), ("$1", "$100", "$900"), ("$2", "$200", "$1,500")]
tag_cols = [black_ink, mat("TagO", (0.9, 0.4, 0.05), 0.5, emit=(0.9, 0.4, 0.05), emit_strength=0.4), red_lab]
stage_f = [S[9] + 4, S[11] + 1, W(11, 0.5)]
stage_end = [S[11] + 1, W(11, 0.5), S[14]]
for (dx, _), pr in zip(items, PR):
    tx, ty, tz = SHX + dx, SHY - 0.42, TOP + 0.75
    tg = group("TagG", (tx, ty, tz))
    attach([box("Tag", (tx, ty, tz), (0.55, 0.03, 0.3), white_m, bevel=0.02),
            box("TagStick", (tx, ty + 0.02, TOP + 0.3), (0.02, 0.02, 0.6), white_m)], tg)
    pop(tg, S[9] + 4, 5, S[14])
    for k in range(3):
        sz = 0.16 if len(pr[k]) <= 4 else 0.12
        t_ = text("TagT", pr[k], (tx, ty - 0.025, tz), sz, tag_cols[k], extrude=0.005)
        pop(t_, stage_f[k], 4, stage_end[k])
        if k >= 1:
            burst((tx, ty, tz), stage_f[k], n=10, r=0.35, size=0.03)
# line 10: crowd with cash rushes the shop + cash piles grow
for k, (x, y) in enumerate([(SHX - 3.0, 3.2), (SHX - 2.2, 2.4), (SHX + 2.4, 2.6), (SHX + 3.2, 3.6), (SHX - 3.6, 4.8), (SHX + 3.8, 5.0)]):
    g, arms = mini(f"Buyer{k}", x, y)
    bl = bill_obj("Wave", (x, y - 0.1, 2.35), 1.3)
    bl.rotation_euler = (math.radians(90), 0, 0)
    parent_to(bl, g)
    f0 = S[10] + k
    key_loc(g, [(f0, (x + (2.5 if x < SHX else -2.5) * 0 - (1.5 if x < SHX else -1.5), y - 1.2, 0)), (f0 + 10, (x, y, 0))])
    keyscale(g, [(0, 0.001), (f0 - 1, 0.001), (f0 + 3, 1.0), (S[13] - 2, 1.0), (S[13], 0.001)])
    for sx, ag in zip((-1, 1), arms):
        keyrot(ag, [(f0, (0, -sx * math.radians(140), 0)), (f0 + 5, (0, -sx * math.radians(160), 0)), (f0 + 10, (0, -sx * math.radians(140), 0))])
cash_pile_m = stripe_mat("PileM", (0.3, 0.68, 0.25), (0.95, 0.75, 0.3), axis="Z", freq=9.0, thresh=0.85)
for k, (x, y, s_) in enumerate([(SHX - 2.0, SHY - 0.3, 0.9), (SHX + 2.0, SHY - 0.4, 1.0), (SHX - 2.8, SHY + 0.8, 0.8), (SHX + 2.9, SHY + 0.6, 0.85)]):
    pl_ = cyl("CashPile", (x, y, 0.45 * s_), 0.8 * s_, 0.9 * s_, cash_pile_m, r2=0.15 * s_, verts=10)
    keyscale(pl_, [(0, 0.001), (S[10] + 2 + 2 * k, 0.001), (E(10) - 4 + k, 1.15), (E(10) + k, 1.0), (S[13] - 2, 1.0), (S[13], 0.001)])
rain(70, SHX, SHY - 0.6, 3.4, 3.0, 6.5, S[10], E(10) + 6, k=1.3, f_gone=S[11] + 8)
for k in range(5):   # explosions of price on line 11
    burst((SHX + random.uniform(-1.4, 1.4), SHY - 0.5, 1.9 + random.uniform(0, 0.6)), S[11] + 2 + 3 * k, n=12, r=0.45, size=0.035)

# ---------------- line 13: your million melts (cash stack on a table) ----------------
TBX_, TBY_ = YX - 1.25, YY + 0.1
wood = mat("Wood", (0.75, 0.5, 0.28), 0.7)
tbg = group("Table", (TBX_, TBY_, 0))
tparts = [box("TTop", (TBX_, TBY_, 0.8), (0.9, 0.6, 0.06), wood, bevel=0.01)]
for dx in (-0.38, 0.38):
    for dy in (-0.24, 0.24):
        tparts.append(box("TLeg", (TBX_ + dx, TBY_ + dy, 0.4), (0.05, 0.05, 0.8), wood))
attach(tparts, tbg)
pop(tbg, S[13], 4, S[14] + 2)
mg = group("MeltG", (TBX_, TBY_, 0.83))
mp = [box("MStack", (TBX_, TBY_, 0.83 + 0.26), (0.36, 0.18, 0.52), cash_pile_m),
      box("MBand", (TBX_, TBY_, 0.83 + 0.26), (0.08, 0.19, 0.53), band100),
      text("MTxt", "$1M", (TBX_, TBY_ - 0.1, 0.83 + 0.3), 0.13, white_lab, extrude=0.005)]
attach(mp, mg)
keyscale(mg, [(0, 0.001), (S[13] - 1, 0.001), (S[13] + 3, 1.0), (S[13] + 6, 1.0), (E(13), (1.15, 1.15, 0.06)), (S[14] + 2, 0.001)])
pud = cyl("Puddle", (TBX_, TBY_, 0.835), 0.42, 0.012, mat("PudM", (0.3, 0.7, 0.25), 0.2), verts=24)
keyscale(pud, [(0, 0.001), (S[13] + 5, (0.05, 0.05, 1)), (E(13), (1, 1, 1)), (S[14] + 1, (1, 1, 1)), (S[14] + 2, 0.001)])
for k in range(4):
    dr = sphere("Drip", (TBX_ - 0.4 + k * 0.25, TBY_ - 0.29, 0.8), 0.035, mat("DripM", (0.3, 0.7, 0.25), 0.2), scale=(1, 1, 1.6), sub=2)
    f0 = S[13] + 8 + 3 * k
    key_loc(dr, [(f0, (TBX_ - 0.4 + k * 0.25, TBY_ - 0.31, 0.8)), (f0 + 8, (TBX_ - 0.4 + k * 0.25, TBY_ - 0.31, 0.03))])
    hide_until(dr, f0); gone_at(dr, f0 + 9, 1)


# ---------------- line 14: hyperinflation chart ----------------
CHX, CHY = -4.2, 4.0
chg = group("Chart", (CHX, CHY, 0))
chp = [box("ChBoard", (CHX, CHY, 2.2), (3.4, 0.08, 3.0), white_m, bevel=0.04),
       box("ChAxY", (CHX - 1.4, CHY - 0.05, 2.2), (0.06, 0.02, 2.6), black_ink),
       box("ChAxX", (CHX, CHY - 0.05, 0.95), (2.9, 0.02, 0.06), black_ink)]
for sx in (-1, 1):
    chp.append(box("ChLeg", (CHX + sx * 1.2, CHY + 0.06, 0.4), (0.08, 0.08, 0.8), post_m))
attach(chp, chg)
pop(chg, S[14], 4, S[15] + 2)
pts = [(CHX - 1.35 + 2.7 * t, CHY - 0.07, 1.0 + 2.4 * (math.exp(5.5 * t) - 1) / (math.exp(5.5) - 1)) for t in [i / 24 for i in range(25)]]
curve = tube("ChCurve", pts, [0.06] * len(pts), red_lab)
curve.data.bevel_factor_mapping_end = 'SPLINE'
curve.data.bevel_factor_end = 0.0; curve.data.keyframe_insert("bevel_factor_end", frame=S[14] + 2)
curve.data.bevel_factor_end = 1.0; curve.data.keyframe_insert("bevel_factor_end", frame=E(14) - 2)
hide_until(curve, S[14] + 2); gone_at(curve, S[15] + 2, 2)
arrow = cyl("ChArrow", pts[-1], 0.16, 0.3, red_lab, verts=12, r2=0.0)
arrow.rotation_euler = (0, math.radians(12), 0)
pop(arrow, E(14) - 3, 4, S[15] + 2)

# ---------------- line 15: a 100-trillion-dollar note (generic design) ----------------
NX, NY, NZ = 1.6, 3.0, 0.85
ng = group("Note", (NX, NY, NZ))
note_m = mat("NoteM", (0.75, 0.82, 0.92), 0.7)
np_ = [box("NoteB", (NX, NY, NZ), (3.4, 0.03, 1.5), note_m),
       box("NoteIn", (NX, NY - 0.017, NZ), (3.1, 0.005, 1.25), mat("NoteIn", (0.88, 0.75, 0.85), 0.7)),
       text("NoteNum", "100,000,000,000,000", (NX, NY - 0.025, NZ + 0.2), 0.27, mat("NoteInk", (0.15, 0.2, 0.45), 0.5), extrude=0.004),
       text("NoteWords", "ONE HUNDRED TRILLION DOLLARS", (NX, NY - 0.025, NZ - 0.25), 0.15, mat("NoteInk2", (0.45, 0.1, 0.25), 0.5), extrude=0.004)]
attach(np_, ng)
key_loc(ng, [(S[15], (NX, NY, NZ + 5)), (S[15] + 9, (NX, NY, NZ)), (E(15), (NX, NY, NZ))])
keyrot(ng, [(S[15], (math.radians(-60), 0, 0.6)), (S[15] + 9, (math.radians(-18), 0, 0)), (S[15] + 12, (math.radians(-24), 0, 0)), (S[15] + 15, (math.radians(-20), 0, 0))])
hide_until(ng, S[15]); gone_at(ng, S[16] + 2, 2)
burst((NX, NY - 0.3, NZ), S[15] + 9, n=14, r=1.6, size=0.05)

# ---------------- line 16: money vs stuff ----------------
MPX, MPY = -2.0, 2.6
mpg = group("MoneyPile", (MPX, MPY, 0))
mpp = []
for lvl, n in enumerate([4, 3, 2, 1]):
    for i in range(n):
        x = MPX + (i - (n - 1) / 2) * 0.4
        mpp.append(box("MPB", (x, MPY, 0.1 + lvl * 0.2), (0.38, 0.2, 0.19), cash_pile_m))
        mpp.append(box("MPBand", (x, MPY, 0.1 + lvl * 0.2), (0.07, 0.21, 0.195), band100))
attach(mpp, mpg)
keyscale(mpg, [(0, 0.001), (S[16] - 1, 0.001), (S[16] + 4, 1.1), (W(16, 0.4), 1.1), (E(16) - 2, 0.35), (E(16) + 2, 0.001)])
xg = group("RedX", (MPX, MPY - 0.3, 0.55))
attach([box("X1", (MPX, MPY - 0.3, 0.55), (1.6, 0.08, 0.16), red_lab, rot=(0, math.radians(40), 0)),
        box("X2", (MPX, MPY - 0.3, 0.55), (1.6, 0.08, 0.16), red_lab, rot=(0, math.radians(-40), 0))], xg)
pop(xg, W(16, 0.25), 5, E(16) + 2)
SPX, SPY = 2.2, 2.6
spg = group("StuffPile", (SPX, SPY, 0))
spp = []
for i in range(3):
    spp.append(sphere("PLoaf", (SPX - 0.5 + i * 0.5, SPY, 0.13), 0.3, bread_m, scale=(1, 0.5, 0.42), sub=2))
for i in range(5):
    spp.append(sphere("PApple", (SPX - 0.6 + i * 0.3, SPY - 0.3, 0.1), 0.11, apple_m, sub=2))
for i in range(2):
    x = SPX - 0.3 + i * 0.6
    spp += [cyl("PBunB", (x, SPY + 0.05, 0.3), 0.2, 0.1, bun_m, verts=20), cyl("PPat", (x, SPY + 0.05, 0.38), 0.22, 0.08, patty_m, verts=20),
            sphere("PBunT", (x, SPY + 0.05, 0.45), 0.21, bun_m, scale=(1, 1, 0.6), sub=2)]
spp.append(box("PMilk", (SPX + 0.75, SPY + 0.1, 0.2), (0.2, 0.2, 0.4), white_m))
spp.append(box("PBox", (SPX - 0.8, SPY + 0.25, 0.25), (0.45, 0.4, 0.5), mat("PBoxM", (0.75, 0.55, 0.3), 0.8)))
attach(spp, spg)
keyscale(spg, [(0, 0.001), (W(16, 0.4) - 1, 0.001), (W(16, 0.4) + 5, 1.5), (W(16, 0.4) + 8, 1.35)])
for k in range(3):
    burst((SPX, SPY - 0.4, 0.6), W(16, 0.4) + 4 + 5 * k, n=12, r=0.8 + 0.3 * k, size=0.04, material=gspark_m)

# ---------------- views (camera, subject) per line; subject sits in the lower third ----------------
V = {}; V2 = {}
V[0] = ((1.2, -5.0, 1.9), (YX, YY, 0.95))
V[1] = ((2.0, -9.5, 4.0), (2.2, 5.6, 0.9));            V2[1] = ((2.8, -8.0, 4.0), (2.2, 5.6, 0.9))
V[2] = ((3.5, -10.0, 3.0), (2.2, 6.0, 3.2))
V[3] = ((14.0, -36.0, 4.0), (2.0, 16.0, 2.0));         V2[3] = ((10.0, -31.0, 5.0), (2.0, 16.0, 2.0))
V[4] = ((-650.0, -1100.0, 900.0), (380.0, 860.0, 40.0)); V2[4] = ((-480.0, -1150.0, 820.0), (380.0, 860.0, 40.0))
V[5] = ((-70.0, -150.0, ZS + 40), (60.0, 0.0, ZS));    V2[5] = ((1880.0, -150.0, ZS + 35), (PL, 0.0, ZS))
V[6] = ((1.8, -5.4, 2.0), (YX + 0.4, YY, 1.0))
V[7] = ((-3.0, -11.0, 4.0), (2.2, 5.6, 1.0));          V2[7] = ((-1.0, -10.0, 4.0), (2.2, 5.6, 1.0))
V[8] = ((TRX, -3.2, 2.0), (TRX + 0.4, ST_Y, 1.0));     V2[8] = ((BKX, -3.2, 2.0), (BKX, ST_Y, 1.0))
V[9] = ((3.4, -2.2, 2.0), (SHX, SHY, 1.0))
V[10] = ((-2.4, -5.2, 3.0), (SHX, SHY - 0.5, 1.2))
V[11] = ((2.3, 2.2, 1.8), (SHX + 0.3, SHY - 0.3, 1.4))
V[12] = ((BGX + 0.6, SHY - 2.3, 1.7), (BGX, SHY - 0.1, TOP + 0.35))
V[13] = ((-1.9, -3.4, 1.6), (YX - 0.6, YY, 0.95))
V[14] = ((-2.0, -3.6, 2.0), (CHX, CHY, 1.5))
V[15] = ((2.6, -1.9, 2.0), (NX, NY, 0.6))
V[16] = ((0.3, -4.6, 2.0), (0.4, 2.5, 0.5))
V[17] = ((2.6, -4.4, 2.0), (YX, YY, 0.95));            V2[17] = ((-2.6, -4.2, 2.0), (YX, YY, 0.95))
DR = {0: (-0.5, 0.8, 0), 2: (-1.0, 1.0, 0), 6: (-0.5, 0.6, 0), 9: (-0.7, 0.5, 0), 10: (1.0, 0.6, 0), 11: (-0.4, 0.3, 0), 12: (-0.3, 0.4, 0),
      13: (0.4, 0.5, 0), 14: (0.4, 0.4, 0), 15: (-0.4, 0.5, 0), 16: (0.5, 0.7, 0)}

def LB(i, name, body, m_, size=None, f_in=None, f_out=None, Dk=0.55, end=False, v=0.3, u=0.0):
    view = V2[i] if end else V[i]
    cl = Vector(CL(view)); D = (Vector(view[1]) - cl).length * Dk
    s_ = 0.85 * fit(body, D, size if size else 1e9)
    return label(name, body, view, D, v, s_, m_, (S[i] + 3) if f_in is None else f_in,
                 E(i) if f_out is None else f_out, u)
LB(0, "L0", "$1,000,000", lab_m)
LB(1, "L1", "8 BILLION PEOPLE", white_lab, f_out=W(1, 0.5))
LB(1, "L1b", "$1M EACH", lab_m, f_in=W(1, 0.5) + 1, end=True)
LB(2, "L2", "$8 QUADRILLION", lab_m)
LB(3, "L3", "80 MILLION TONS", lab_m, Dk=0.3)
LB(4, "L4", "> 12 PYRAMIDS", lab_m, Dk=0.3, end=True)
LB(5, "L5", "PAST PLUTO!", lab_m, f_in=W(5, 0.55), end=True, Dk=0.45)
LB(6, "L6", "PARTY!", pink_lab if 'pink_lab' in globals() else lab_m)
LB(7, "L7", "EVERYONE QUITS", white_lab, end=True)
LB(8, "L8", "NO FARMERS", red_lab, f_out=W(8, 0.33) + 1, v=0.3)
LB(8, "L8b", "NO TRUCKERS", red_lab, f_in=W(8, 0.33) + 2, f_out=W(8, 0.66) + 1, end=False, u=0.0)
LB(8, "L8c", "NO BAKERS", red_lab, f_in=W(8, 0.66) + 2, end=True)
LB(9, "L9", "SAME STUFF", white_lab)
LB(10, "L10", "WAY MORE MONEY", lab_m)
LB(11, "L11", "PRICES EXPLODE!", red_lab)
LB(13, "L13", "$1M = ~300 BURGERS", lab_m)
LB(14, "L14", "HYPERINFLATION", red_lab)
LB(15, "L15", "ZIMBABWE, 2009", white_lab)
LB(16, "L16", "STUFF = WEALTH", green_lab)
LB(17, "L17", "WHAT WOULD YOU BUY?", lab_m, end=True, f_in=S[17] + 6, Dk=0.4)

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
    if i == 5:
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
