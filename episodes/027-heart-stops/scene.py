# Day 27 — What if your heart stopped for 10 minutes?  Build: python3 episodes/027-heart-stops/scene.py
# Reference style: base (helpers, lawn/soil, house, garden) copied from episodes/003-lift-million-ref/scene.py (via 019)
import bpy, math, random, os, json
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
random.seed(27)
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
# ground split around a big cut-away pool at the front face (pool x PX0..PX1, y FRONT_Y..PY1, floor PZF)
PX0, PX1, PY1, PZB = -3.2, 5.2, 3.6, -1.95
box("GroundBelow", (0, 26.2, (PZB - 12.0) / 2), (400, 55.6, 12.0 + PZB), grass_m)
box("GroundL", ((-200 + PX0) / 2, 26.2, PZB / 2), (200 + PX0, 55.6, -PZB), grass_m)
box("GroundR", ((200 + PX1) / 2, 26.2, PZB / 2), (200 - PX1, 55.6, -PZB), grass_m)
box("GroundB", ((PX0 + PX1) / 2, (PY1 + 54.0) / 2, PZB / 2), (PX1 - PX0, 54.0 - PY1, -PZB), grass_m)
under_m = mat("Underside", (0.3, 0.2, 0.12), 0.9)
bpy.ops.mesh.primitive_plane_add(size=1200, location=(0, 0, -12.05))
bpy.context.object.data.materials.append(under_m)
far = grass_m
bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 0, -0.03))
fp = bpy.context.object; fp.scale = (400000, 400000, 1); fp.location = (0, 200050, -0.03)
fp.data.materials.append(far)
stone_m = mat("Stone", (0.7, 0.66, 0.6), 0.8)
for i in range(30):
    px_, pz_ = random.uniform(-30, 30), random.uniform(-5.6, -0.6)
    if PX0 - 0.4 < px_ < PX1 + 0.4 and pz_ > PZB - 0.4:
        continue
    sphere("Peb", (px_, FRONT_Y - 0.02, pz_), random.uniform(0.12, 0.3),
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
# Day 23 — What if you got stung by a box jellyfish?
# Facts used (Australian Resuscitation Council first-aid guideline, Queensland Health, Lewis Gershwin, NOAA):
#   Chironex fleckeri: transparent, up to ~15 tentacles per corner (up to ~60), each up to ~3 m; 24 eyes in 4 clusters,
#   no brain (nerve net/ring). Tentacles carry millions of nematocysts (stinging capsules) that fire a barbed thread in
#   microseconds — one of the fastest movements in biology — and inject venom. The pain is extreme; a large sting can
#   cause cardiac arrest within minutes, but most stings are not fatal. First aid (tropical Australia): get out of the
#   water, call emergency help (CPR if needed), pour vinegar for at least 30 s to deactivate undischarged stingers;
#   don't rub, don't rinse with fresh water. A box jellyfish antivenom exists. Stinger suits / nets prevent stings.
# =====================================================================================
gold_m = mat("Gold", (1.0, 0.78, 0.2), 0.3, metal=0.85)
tile_m = stripe_mat("Tile", (0.93, 0.97, 1.0), (0.7, 0.85, 0.95), axis="Z", freq=18.0, thresh=0.85, rough=0.3)
coping_m = mat("Coping", (0.92, 0.9, 0.84), 0.6)
water_m = bpy.data.materials.new("Water"); water_m.use_nodes = True
wb = water_m.node_tree.nodes["Principled BSDF"]
wb.inputs["Base Color"].default_value = (0.25, 0.68, 0.95, 1); wb.inputs["Roughness"].default_value = 0.3
wb.inputs["Alpha"].default_value = 0.32
wb.inputs["Emission Color"].default_value = (0.2, 0.6, 0.9, 1); wb.inputs["Emission Strength"].default_value = 0.12
jelly_m = bpy.data.materials.new("Jelly"); jelly_m.use_nodes = True
jb = jelly_m.node_tree.nodes["Principled BSDF"]
jb.inputs["Base Color"].default_value = (0.75, 0.92, 1.0, 1); jb.inputs["Roughness"].default_value = 0.2
jb.inputs["Emission Color"].default_value = (0.55, 0.88, 1.0, 1); jb.inputs["Emission Strength"].default_value = 0.9
jcore_m = glow_mat("JCore", (1.0, 0.55, 0.85), 2.0)
gten_m = bpy.data.materials.new("GTent"); gten_m.use_nodes = True
gb = gten_m.node_tree.nodes["Principled BSDF"]
gb.inputs["Base Color"].default_value = (0.7, 0.9, 1.0, 1); gb.inputs["Roughness"].default_value = 0.25
gb.inputs["Alpha"].default_value = 0.75
gb.inputs["Emission Color"].default_value = (0.5, 0.85, 1.0, 1); gb.inputs["Emission Strength"].default_value = 0.5
caps_m = mat("Capsule", (0.98, 0.98, 1.0), 0.3, emit=(1, 1, 1), emit_strength=0.5)
coil_m = mat("Coil", (0.35, 0.2, 0.6), 0.4)
harp_m = mat("Harpoon", (0.95, 0.95, 0.85), 0.3, emit=(1, 1, 0.8), emit_strength=0.8)
venom_m = glow_mat("Venom", (0.75, 0.2, 1.0), 4.0)
epi_m = mat("Epi", (1.0, 0.8, 0.68), 0.6)
der_m = mat("Derm", (0.95, 0.55, 0.55), 0.6)
fat_m = mat("Fat", (1.0, 0.88, 0.45), 0.6)
heart_m = mat("HeartM", (0.9, 0.1, 0.15), 0.35, emit=(1.0, 0.1, 0.1), emit_strength=0.3)
redglow = glow_mat("RedGlow", (1.0, 0.08, 0.05), 3.0)
grnglow = glow_mat("GrnGlow", (0.2, 1.0, 0.35), 3.0)
ecgg_m = glow_mat("ECGG", (0.2, 1.0, 0.4), 4.0)
screen_m = mat("Screen", (0.03, 0.05, 0.06), 0.4)
board_m = mat("Board", (0.98, 0.98, 0.96), 0.6)
post_m = mat("Post", (0.3, 0.3, 0.35), 0.6)
vin_m = mat("Vinegar", (0.95, 0.85, 0.55), 0.1, emit=(1.0, 0.85, 0.45), emit_strength=0.3)
vdrop_m = glow_mat("VDrop", (1.0, 0.92, 0.6), 2.5)
cap_red = mat("CapRed", (0.9, 0.15, 0.1), 0.4)
vial_m = mat("Vial", (0.85, 0.95, 1.0), 0.05, emit=(0.8, 0.9, 1.0), emit_strength=0.2)
anti_m = glow_mat("Anti", (0.2, 0.55, 1.0), 2.5)
suit_m = mat("Suit", (0.1, 0.12, 0.3), 0.5)
bolt_m = glow_mat("Bolt", (1.0, 0.9, 0.1), 5.0)
phone_m = mat("Phone", (0.08, 0.08, 0.1), 0.3)
phs_m = glow_mat("PhoneS", (0.3, 0.9, 1.0), 3.0)

def lin(o):
    for fc in fcurves(o):
        for p in fc.keyframe_points:
            p.interpolation = 'LINEAR'

def path_keys(o, pts, f0, f1):
    pts = [Vector(p) for p in pts]
    L_ = [0.0]
    for a, b in zip(pts, pts[1:]):
        L_.append(L_[-1] + (b - a).length)
    tot = L_[-1] or 1.0
    for p, l in zip(pts, L_):
        o.location = tuple(p); o.keyframe_insert("location", frame=round(f0 + (f1 - f0) * l / tot))

def xstamp(name, c, f_in, f_out, s=1.0):
    g = group(name, c)
    a_ = boxc(name + "a", c, (0.2 * s, 0.08, 1.6 * s), red_lab); b_ = boxc(name + "b", c, (0.2 * s, 0.08, 1.6 * s), red_lab)
    a_.rotation_euler = (0, math.radians(45), 0); b_.rotation_euler = (0, math.radians(-45), 0)
    attach([a_, b_], g)
    keyscale(g, [(0, 0.001), (f_in - 1, 0.001), (f_in, 2.2), (f_in + 4, 0.95), (f_in + 6, 1.0), (f_out - 1, 1.0), (f_out, 0.001)])
    burst(c, f_in + 3, n=10, r=0.7 * s, size=0.06, material=spark_m, f_out=f_out)
    return g

def check(name, c, f_in, f_out, s=1.0):
    g = group(name, c)
    a_ = boxc(name + "a", (c[0] - 0.18 * s, c[1], c[2] - 0.05 * s), (0.14 * s, 0.08, 0.42 * s), green_lab)
    b_ = boxc(name + "b", (c[0] + 0.12 * s, c[1], c[2] + 0.12 * s), (0.14 * s, 0.08, 0.85 * s), green_lab)
    a_.rotation_euler = (0, math.radians(-40), 0); b_.rotation_euler = (0, math.radians(30), 0)
    attach([a_, b_], g)
    keyscale(g, [(0, 0.001), (f_in - 1, 0.001), (f_in + 3, 1.25), (f_in + 6, 1.0), (f_out - 1, 1.0), (f_out, 0.001)])
    return g

def bolt(name, c, s, f_in, f_out, flick=3):
    """Cartoon lightning zig-zag, flickering."""
    pts = [(0, 0, 0.5), (0.15, 0, 0.12), (-0.08, 0, 0.05), (0.1, 0, -0.45)]
    o = tube(name, [(c[0] + p[0] * s, c[1], c[2] + p[2] * s) for p in pts], [0.05 * s] * 4, bolt_m)
    kk = [(0, 0.001), (f_in - 1, 0.001)]
    for j, f in enumerate(range(f_in, f_out, flick)):
        kk.append((f, 1.0 if j % 2 == 0 else 0.001))
    kk.append((f_out, 0.001))
    p_ = group(name + "P", (0, 0, 0)); o.parent = p_
    for f, v in kk:
        p_.scale = (v,) * 3; p_.keyframe_insert("scale", frame=f)
    for fc in fcurves(p_):
        for p in fc.keyframe_points:
            p.interpolation = 'CONSTANT'
    return o

# ---------------- the pool (cut-away front = glass) ----------------
PZF, PZW = -1.75, -0.15                    # pool floor top, water surface
box("PoolFloor", ((PX0 + PX1) / 2, (FRONT_Y + PY1) / 2, (PZB + PZF) / 2), (PX1 - PX0, PY1 - FRONT_Y, PZF - PZB), tile_m)
box("PoolWallL", (PX0 + 0.1, (FRONT_Y + PY1) / 2, PZB / 2), (0.2, PY1 - FRONT_Y, -PZB), tile_m)
box("PoolWallR", (PX1 - 0.1, (FRONT_Y + PY1) / 2, PZB / 2), (0.2, PY1 - FRONT_Y, -PZB), tile_m)
box("PoolWallB", ((PX0 + PX1) / 2, PY1 - 0.1, PZB / 2), (PX1 - PX0, 0.2, -PZB), tile_m)
box("Water", ((PX0 + PX1) / 2, (FRONT_Y + PY1 - 0.2) / 2 - 0.005, (PZF + PZW) / 2), (PX1 - PX0 - 0.42, PY1 - 0.2 - FRONT_Y - 0.01, PZW - PZF), water_m)
for (x, y, sx_, sy_) in [(PX0 - 0.15, (FRONT_Y + PY1) / 2, 0.5, PY1 - FRONT_Y), (PX1 + 0.15, (FRONT_Y + PY1) / 2, 0.5, PY1 - FRONT_Y),
                         ((PX0 + PX1) / 2, PY1 + 0.15, PX1 - PX0 + 0.8, 0.5)]:
    box("Coping", (x, y, 0.04), (sx_, sy_, 0.1), coping_m, bevel=0.02)
for x in (PX0 + 0.1, PX1 - 0.1):
    box("GlassFrame", (x, FRONT_Y - 0.03, PZB / 2), (0.24, 0.06, -PZB), trim_m)
box("GlassFrameB", ((PX0 + PX1) / 2, FRONT_Y - 0.03, PZB + 0.1), (PX1 - PX0, 0.06, 0.2), trim_m)

# =====================================================================================
# Day 27 — What if your heart stopped for 10 minutes?
# Facts used (American Heart Association, Resuscitation Council UK, NHS, Mayo Clinic):
#   A resting heart beats ~60-100/min => roughly 100,000 beats a day. In sudden cardiac arrest the heart most often
#   goes into ventricular fibrillation (it quivers instead of pumping). Blood flow stops; the brain uses ~20% of the
#   body's oxygen. Unconsciousness follows in ~10-20 s; no pulse, no normal breathing. Brain damage can begin after
#   ~4-6 min without oxygen. Without CPR, survival falls by ~7-10% for every minute. CPR: push hard and fast,
#   100-120 compressions/min (about 2 per second), which pushes blood to the brain. An AED shock can stop the
#   fibrillation so a normal rhythm can return. People have survived after 10+ minutes of good CPR.
# =====================================================================================
heartbig_m = mat("HeartBig", (0.9, 0.1, 0.15), 0.35, emit=(1.0, 0.1, 0.1), emit_strength=0.3)
hbsdf = heartbig_m.node_tree.nodes["Principled BSDF"]
grey_m = mat("HeartGrey", (0.42, 0.34, 0.38), 0.6)
vein_m = mat("Vein", (0.2, 0.35, 0.9), 0.4)
aorta_m = mat("Aorta", (0.85, 0.12, 0.15), 0.4)
brain_m = mat("BrainM", (1.0, 0.6, 0.72), 0.5, emit=(1.0, 0.45, 0.6), emit_strength=0.25)
cellr_m = glow_mat("CellR", (1.0, 0.08, 0.06), 2.5)
o2_m = glow_mat("O2", (0.25, 0.6, 1.0), 3.0)
deadc_m = mat("DeadCell", (0.35, 0.33, 0.34), 0.7)
art_m = bpy.data.materials.new("Artery"); art_m.use_nodes = True
ab = art_m.node_tree.nodes["Principled BSDF"]
ab.inputs["Base Color"].default_value = (1.0, 0.55, 0.6, 1); ab.inputs["Roughness"].default_value = 0.2
ab.inputs["Alpha"].default_value = 0.28
ab.inputs["Emission Color"].default_value = (1.0, 0.5, 0.55, 1); ab.inputs["Emission Strength"].default_value = 0.15
aed_m = mat("AED", (1.0, 0.82, 0.1), 0.5)
pad_m = mat("Pad", (0.98, 0.98, 0.98), 0.5)
wire_m = mat("Wire", (0.1, 0.1, 0.12), 0.5)
chaos_m = glow_mat("Chaos", (1.0, 0.45, 0.1), 4.0)
lung_m = mat("Lung", (1.0, 0.62, 0.68), 0.6)
flash_m = glow_mat("Flash", (1.0, 1.0, 0.85), 8.0)

def heart_parts(name, c, s, m_, eyes=False):
    c = Vector(c)
    ps = [sphere(name + "L", tuple(c + Vector((-0.33, 0, 0.2)) * s), 0.48 * s, m_, sub=3),
          sphere(name + "R", tuple(c + Vector((0.33, 0, 0.2)) * s), 0.48 * s, m_, sub=3)]
    ps[0].location = tuple(c + Vector((-0.33, 0, 0.2)) * s); ps[1].location = tuple(c + Vector((0.33, 0, 0.2)) * s)
    v_ = cyl(name + "V", tuple(c + Vector((0, 0, -0.4 * s))), 0.72 * s, 0.85 * s, m_, rot=(math.radians(180), 0, 0), r2=0.03 * s, verts=24)
    v_.scale = (1.0, 0.62, 1.0)
    ps.append(v_)
    return ps

# =================== the patient ("you") ===================
A = Vector((-5.6, -0.5, 0.0))
you, YD = person("You", tuple(A), 1.0, mat("Shirt", (0.95, 0.45, 0.2), 0.6), mat("Pants", (0.2, 0.3, 0.55), 0.7),
                 skin_m, mat("Hair", (0.25, 0.14, 0.07), 0.8))
Q = YD["P"]
# chest heart icon (red beating / grey stopped), attached to the body so it follows the fall
ich = Vector(Q(0, -0.27, 1.22))
ired = heart_parts("IconR", (0, 0, 0), 0.17, redglow)
igry = heart_parts("IconG", (0, 0, 0), 0.17, grey_m)
icr = group("IconRed", tuple(ich)); icg = group("IconGrey", tuple(ich))
for o_ in ired:
    o_.location = tuple(Vector(o_.location) + ich)
for o_ in igry:
    o_.location = tuple(Vector(o_.location) + ich)
attach(ired, icr); attach(igry, icg)
attach([icr, icg], you)
# poses
LIE = (math.radians(-90), 0, math.radians(90))
UP = (0, 0, 0)
FALL0, FALL1 = W(6, 0.18), W(6, 0.45)
RISE0, RISE1 = W(15, 0.1), W(15, 0.35)
keyrot(you, [(0, UP), (FALL0, UP), (FALL1, LIE), (RISE0, LIE), (RISE1, UP)])
key_loc(you, [(0, tuple(A)), (FALL0, tuple(A)), (FALL1, tuple(A + Vector((0, 0, 0.22)))), (RISE0, tuple(A + Vector((0, 0, 0.22)))),
              (RISE1, tuple(A))])
CH = Vector((A.x - 1.1, A.y, 0.46))
HEADL = Vector((A.x - 1.68, A.y, 0.3))
burst(tuple(HEADL + Vector((0, -0.3, 0.3))), FALL1, n=12, r=0.45, size=0.05, material=spark_m, f_out=FALL1 + 12)
# AED zap: jolt
ZAP = W(13, 0.55)
you.location = tuple(A + Vector((0, 0, 0.22))); you.keyframe_insert("location", frame=ZAP - 1)
you.location = tuple(A + Vector((0, 0, 0.36))); you.keyframe_insert("location", frame=ZAP + 1)
you.location = tuple(A + Vector((0, 0, 0.22))); you.keyframe_insert("location", frame=ZAP + 4)
# icon: red beating until line 2 (stop) and again after the shock
RESTART = ZAP + 2
vis(icr, [(0, S[2] + 2), (RESTART, FRAMES + 1)]); vis(icg, [(S[2] + 2, RESTART)])
ib = group("IconBeat", (0, 0, 0))
kk = []
for f in range(0, FRAMES + 1, 8):
    alive = f < S[2] or f >= RESTART
    kk += [(f, 1.0), (f + 3, 1.25 if alive else 1.0)]
for o_ in (icr,):
    pass
# beat the red icon itself via a child-friendly delta: scale keys on its own group (vis keys use scale too) -> use a parent
# (kept simple: the icon pops on/off with vis; the giant heart carries the beat)

# chest squash during CPR (chest depth = torso local Y)
tor = YD["torso"]
t0s = tuple(tor.scale)
CPR0 = W(10, 0.85)
PUSHES = list(range(S[11], ZAP - 8, 12))
keyscale(tor, [(0, t0s), (S[11] - 1, t0s)])
for f in PUSHES:
    keyscale(tor, [(f, t0s), (f + 4, (t0s[0], t0s[1] * 0.72, t0s[2])), (f + 9, t0s)])

# =================== stopwatch helper ===================
def stopwatch(name, c, spans, turns):
    c = Vector(c)
    g = group(name, tuple(c))
    p = [cyl(name + "Body", tuple(c), 0.5, 0.12, white_lab, rot=(math.radians(90), 0, 0), verts=32),
         cyl(name + "Rim", tuple(c + Vector((0, 0.02, 0))), 0.56, 0.1, gold_m, rot=(math.radians(90), 0, 0), verts=32),
         cyl(name + "Knob", tuple(c + Vector((0, 0, 0.62))), 0.09, 0.14, gold_m, verts=12),
         box(name + "Post", tuple(c + Vector((0, 0.1, -c.z / 2 - 0.25))), (0.12, 0.12, c.z - 0.5), post_m)]
    attach(p, g)
    h_ = boxc(name + "Hand", tuple(c + Vector((0, -0.09, 0))), (0.05, 0.03, 0.42), red_lab)
    h_.data.transform(Matrix.Translation((0, 0, 0.18)))
    hg = group(name + "HG", tuple(c + Vector((0, -0.09, 0)))); parent_to(h_, hg)
    a, b = spans[0][0], spans[-1][1]
    keyrot(hg, [(a, (0, 0, 0)), (b, (0, math.radians(360 * turns), 0))]); lin(hg)
    vis(g, spans); vis(hg, spans)
    return g
stopwatch("SW0", (A.x + 1.3, A.y - 0.1, 1.0), [(0, S[1])], 3)
stopwatch("SW6", (A.x + 0.9, A.y - 0.3, 1.0), [(S[6], S[7])], 2)

# =================== line 7: no pulse, no breathing ===================
PI = Vector((CH.x - 0.35, A.y - 0.95, 0.55))
pig = group("PulseIcon", tuple(PI))
pp = heart_parts("PulseI", (0, 0, 0), 0.38, red_lab)
for o_ in pp:
    o_.location = tuple(Vector(o_.location) + PI)
attach(pp, pig)
pop(pig, S[7] + 2, 5, S[8])
xstamp("XPulse", tuple(PI + Vector((0, -0.25, 0))), W(7, 0.25), S[8], s=0.45)
LU = Vector((CH.x + 0.95, A.y - 0.95, 0.55))
lug = group("Lungs", tuple(LU))
lp = [sphere("LungL", tuple(LU + Vector((-0.2, 0, 0))), 0.24, lung_m, scale=(0.7, 0.6, 1.1), sub=2),
      sphere("LungR", tuple(LU + Vector((0.2, 0, 0))), 0.24, lung_m, scale=(0.7, 0.6, 1.1), sub=2),
      cyl("Trachea", tuple(LU + Vector((0, 0, 0.3))), 0.05, 0.3, lung_m, verts=10)]
attach(lp, lug)
pop(lug, W(7, 0.45), 5, S[8])
xstamp("XLung", tuple(LU + Vector((0, -0.25, 0))), W(7, 0.65), S[8], s=0.45)

# =================== line 9: survival meter ===================
M = Vector((A.x - 3.3, A.y + 0.9, 0))
mtr = group("Meter", tuple(M))
mp = [box("MFrame", (M.x, M.y, 1.0), (0.8, 0.2, 2.0), board_m, bevel=0.04), box("MFoot", (M.x, M.y + 0.1, 0.05), (0.6, 0.5, 0.1), post_m)]
attach(mp, mtr)
vis(mtr, [(S[9], S[10])])
DROP = [W(9, 0.1 + 0.11 * j) for j in range(7)]
for k in range(10):
    m_ = green_lab if k >= 6 else (lab_m if k >= 3 else red_lab)
    sg = box(f"MSeg{k}", (M.x, M.y - 0.12, 0.2 + k * 0.175), (0.6, 0.06, 0.14), green_lab)
    j = 9 - k
    vis(sg, [(S[9], DROP[j] if j < 7 else S[10])])
pcts = ["100%"] + [f"{100 - 10 * (j + 1)}%" for j in range(7)]
for j, t_ in enumerate(pcts):
    a = S[9] if j == 0 else DROP[j - 1]
    b = DROP[j] if j < 7 else S[10]
    tt = text(f"Pct{j}", t_, (M.x + 1.15, M.y - 0.2, 1.0), 0.5, red_lab if j >= 4 else lab_m, extrude=0.04)
    vis(tt, [(a, b)])
    burst((M.x, M.y - 0.2, 0.2 + (9 - j) * 0.175 + 0.175), b, n=6, r=0.3, size=0.035, material=spark_m, f_out=b + 8) if j < 7 else None

# =================== helper (lines 10-16) ===================
helper, HDd = person("Helper", (0, 0, 0), 1.0, green_lab, mat("HPants", (0.15, 0.15, 0.3), 0.6), mat("HSkin", (0.62, 0.42, 0.3), 0.6),
                     mat("HHair", (0.08, 0.05, 0.04), 0.8))
HP = Vector((CH.x, A.y + 0.45, -0.37))
START = Vector((-10.8, 2.6, 0))
key_loc(helper, [(0, tuple(START)), (S[10], tuple(START)), (W(10, 0.7), (HP.x, HP.y, 0)), (CPR0, tuple(HP))])
keyrot(helper, [(0, (0, 0, math.radians(70))), (W(10, 0.6), (0, 0, math.radians(70))), (W(10, 0.75), (0, 0, 0))])
for f in PUSHES:
    key_loc(helper, [(f, tuple(HP)), (f + 4, tuple(HP - Vector((0, 0, 0.07)))), (f + 9, tuple(HP))])
key_loc(helper, [(RISE0, tuple(HP)), (RISE1, (HP.x - 0.2, HP.y + 0.1, 0))])
vis(helper, [(S[10], FRAMES + 1)])
for k, lg in enumerate(HDd["legs"]):
    for j, f in enumerate(range(S[10], W(10, 0.7), 4)):
        lg.rotation_euler = (math.radians(30 if (j + k) % 2 else -30), 0, 0); lg.keyframe_insert("rotation_euler", frame=f)
    lg.rotation_euler = (0, 0, 0); lg.keyframe_insert("rotation_euler", frame=W(10, 0.72))
for k, ar in enumerate(HDd["arms"]):
    sx = -1 if k == 0 else 1
    reach = (math.radians(-40), math.radians(25 * sx), 0)
    keyrot(ar, [(0, (0, 0, 0)), (W(10, 0.72), (0, 0, 0)), (CPR0, reach), (W(13, 0.1), reach), (W(13, 0.25), (math.radians(-15), 0, 0)),
                (RISE0, (math.radians(-15), 0, 0)), (RISE1, (0, math.radians(-150 * sx), 0))])

# =================== line 13: the AED ===================
AE = Vector((CH.x + 1.2, A.y - 0.75, 0.2))
aeg = group("AEDg", tuple(AE))
ap = [box("AEDBox", tuple(AE), (0.7, 0.45, 0.4), aed_m, bevel=0.06),
      box("AEDScr", tuple(AE + Vector((-0.12, -0.23, 0.05))), (0.28, 0.02, 0.18), phs_m),
      box("AEDBtn", tuple(AE + Vector((0.2, -0.23, 0.05))), (0.14, 0.02, 0.14), red_lab)]
attach(ap, aeg)
pop(aeg, S[13] + 1, 5, S[14])
PADS = [Vector((CH.x - 0.18, A.y + 0.12, 0.49)), Vector((CH.x + 0.2, A.y - 0.14, 0.49))]
for k, pd in enumerate(PADS):
    pd_ = box(f"Pad{k}", tuple(pd), (0.2, 0.24, 0.03), pad_m)
    w_ = tube(f"Wire{k}", [tuple(AE + Vector((-0.2 + 0.1 * k, -0.05, 0.2))), tuple((AE + pd) / 2 + Vector((0, -0.1, 0.35))), tuple(pd + Vector((0, 0, 0.02)))],
              [0.02] * 3, wire_m)
    for o_ in (pd_, w_):
        vis(o_, [(W(13, 0.2) + 2 * k, S[14])])
fl = sphere("ZapFlash", tuple(CH + Vector((0, -0.1, 0.2))), 0.2, flash_m, sub=2)
keyscale(fl, [(0, 0.001), (ZAP - 1, 0.001), (ZAP, 1.6), (ZAP + 2, 0.7), (ZAP + 4, 0.001)])
burst(tuple(CH + Vector((0, -0.3, 0.3))), ZAP, n=14, r=0.7, size=0.06, material=bolt_m, f_out=ZAP + 12)
bolt("ZB1", (CH.x - 0.7, CH.y - 0.4, 1.0), 0.9, ZAP, E(13), 2)
bolt("ZB2", (CH.x + 0.7, CH.y - 0.4, 1.05), 0.8, ZAP + 1, E(13), 2)

# =================== line 15: 10:00 sign + check ===================
CK = Vector((A.x + 1.4, A.y + 0.6, 0))
ckg = group("ClockSign", tuple(CK))
cp_ = [box("CKB", (CK.x, CK.y, 1.15), (1.6, 0.12, 0.8), board_m, bevel=0.04), box("CKP", (CK.x, CK.y + 0.1, 0.4), (0.12, 0.12, 0.8), post_m),
       text("CKT", "10:00", (CK.x, CK.y - 0.08, 1.15), 0.48, mat("InkM", (0.08, 0.08, 0.1), 0.5), extrude=0.02)]
attach(cp_, ckg)
pop(ckg, S[15] + 2, 5)
check("Chk15", (CK.x + 1.0, CK.y - 0.2, 1.3), W(15, 0.35), FRAMES + 1, s=0.9)
qm = text("QMark", "?", (A.x - 0.7, A.y - 0.1, 2.45), 1.3, lab_m, extrude=0.08)
pop(qm, S[16] + 4, 5)

# =================== heart zone ===================
HC = Vector((9.0, 0.0, 1.4))
BC = Vector((13.0, 0.0, 1.2))
box("HPed", (HC.x, HC.y, 0.28), (1.2, 1.2, 0.56), board_m, bevel=0.05)
box("BPed", (BC.x, BC.y, 0.36), (1.4, 1.2, 0.72), board_m, bevel=0.05)
hq = group("HeartQ", tuple(HC))
hpar = heart_parts("HBig", (0, 0, 0), 1.0, heartbig_m)
for o_ in hpar:
    o_.location = tuple(Vector(o_.location) + HC)
hpar += [tube("AortaT", [tuple(HC + Vector((0.12, 0.05, 0.45))), tuple(HC + Vector((0.2, 0.05, 0.9))), tuple(HC + Vector((0.45, 0.05, 1.0)))], [0.13] * 3, aorta_m),
         tube("VenaT", [tuple(HC + Vector((-0.3, 0.1, 0.45))), tuple(HC + Vector((-0.35, 0.1, 0.85)))], [0.11] * 2, vein_m)]
# eyes: open (alive) / closed (stopped)
EO, EC = [], []
for sx in (-1, 1):
    EO += [sphere("HEyeW", tuple(HC + Vector((sx * 0.3, -0.42, 0.22))), 0.1, eyew, scale=(1, 0.6, 1.2), sub=2),
           sphere("HEyeB", tuple(HC + Vector((sx * 0.3, -0.49, 0.22))), 0.05, eyeb, sub=1)]
    EC.append(box("HEyeC", tuple(HC + Vector((sx * 0.3, -0.47, 0.2))), (0.2, 0.04, 0.04), eyeb))
smile = tube("HSmile", [tuple(HC + Vector((-0.12, -0.44, 0.02))), tuple(HC + Vector((0, -0.48, -0.04))), tuple(HC + Vector((0.12, -0.44, 0.02)))], [0.025] * 3, eyeb)
hpar += EO + EC + [smile]
attach(hpar, hq)
hb = group("HeartBeat", tuple(HC)); parent_to(hq, hb)
for o_ in EO:
    vis(o_, [(0, S[2] + 3), (W(14, 0.25), FRAMES + 1)], tuple(o_.scale))
for o_ in EC:
    vis(o_, [(S[2] + 3, W(14, 0.25))])
vis(smile, [(0, S[2] + 3), (W(14, 0.25), FRAMES + 1)])
REBEAT = W(14, 0.25)
# beat / stop / squeeze
kk = [(0, 1.0)]
f = 0
while f < S[2] + 2:
    per = 6 if S[1] <= f < S[2] else 9
    kk += [(f, 1.0), (f + 2, 1.14)]
    f += per
kk += [(S[2] + 3, 1.0), (S[12] - 1, 1.0)]
for f in range(S[12], E(12) - 6, 12):
    kk += [(f, 1.0), (f + 4, (1.1, 1.1, 0.8)), (f + 9, 1.0)]
kk += [(E(12), 1.0), (REBEAT - 1, 1.0)]
for f in range(REBEAT, FRAMES + 1, 12):
    kk += [(f, 1.0), (f + 3, 1.14), (f + 7, 1.0)]
kk.sort(key=lambda x: x[0])
dedup = {}
for f, s in kk:
    dedup[f] = s
keyscale(hb, sorted(dedup.items()))
# quiver: noise on location, restricted to the fibrillation span
key_loc(hq, [(0, tuple(HC))])
for fc in fcurves(hq):
    if fc.data_path == "location":
        m = fc.modifiers.new('NOISE'); m.strength = 0.12; m.scale = 1.2; m.phase = random.uniform(0, 100)
        m.use_restricted_range = True; m.frame_start = S[3]; m.frame_end = REBEAT
        m.blend_in = 0; m.blend_out = 0
# colour: red -> grey on stop, back to red on restart
for f, col, em in [(0, (0.9, 0.1, 0.15), 0.3), (S[2] + 2, (0.9, 0.1, 0.15), 0.3), (S[2] + 4, (0.45, 0.3, 0.36), 0.0),
                   (REBEAT - 2, (0.45, 0.3, 0.36), 0.0), (REBEAT, (0.95, 0.1, 0.15), 0.6)]:
    hbsdf.inputs["Base Color"].default_value = (*col, 1); hbsdf.inputs["Base Color"].keyframe_insert("default_value", frame=f)
    hbsdf.inputs["Emission Strength"].default_value = em; hbsdf.inputs["Emission Strength"].keyframe_insert("default_value", frame=f)
# beat rings (line 1, and after restart)
def rings(a, b, per):
    for t0 in range(a, b - 8, per):
        bpy.ops.mesh.primitive_torus_add(major_radius=0.8, minor_radius=0.04, location=tuple(HC + Vector((0, -0.2, 0.05))), rotation=(math.radians(90), 0, 0))
        rg = bpy.context.object; rg.data.materials.append(redglow)
        keyscale(rg, [(0, 0.001), (t0 - 1, 0.001), (t0, 0.8), (t0 + 8, 1.7), (t0 + 9, 0.001)])
rings(S[1], S[2], 6)
rings(REBEAT, E(14), 12)
burst(tuple(HC + Vector((0, -0.7, 0.3))), REBEAT, n=14, r=1.0, size=0.06, material=spark_m, f_out=REBEAT + 12)
check("Chk14", tuple(HC + Vector((-1.0, -0.5, 1.35))), W(14, 0.4), S[15], s=0.8)
# stop flash on line 2
burst(tuple(HC + Vector((0, -0.7, 0.3))), S[2] + 3, n=14, r=1.0, size=0.06, material=red_lab, f_out=S[3])

# ECG monitor left of the heart
MON = Vector((HC.x - 1.85, HC.y - 0.3, 1.0))
box("MonScr", tuple(MON), (1.3, 0.1, 0.9), screen_m, bevel=0.03)
box("MonPost", (MON.x, MON.y + 0.05, 0.28), (0.12, 0.12, 0.56), post_m)
my = MON.y - 0.07
def trace(name, pts, m_, spans):
    o_ = tube(name, [(MON.x + x, my, MON.z + z) for x, z in pts], [0.025] * len(pts), m_)
    vis(o_, spans)
normal = [(-0.55, 0), (-0.3, 0), (-0.22, 0.32), (-0.14, -0.25), (-0.06, 0), (0.15, 0), (0.23, 0.32), (0.31, -0.25), (0.39, 0), (0.55, 0)]
trace("ECGN", normal, ecgg_m, [(0, S[2] + 2), (REBEAT, FRAMES + 1)])
trace("ECGF", [(-0.55, 0), (0.55, 0)], redglow, [(S[2] + 2, S[3])])
chaos = [(-0.55 + 0.055 * k, random.uniform(-0.28, 0.28) * (0.6 + 0.4 * (k % 2))) for k in range(21)]
trace("ECGC", chaos, chaos_m, [(S[3], REBEAT)])

# artery heart -> brain with red cells + oxygen
AP = [HC + Vector((0.45, 0.05, 1.0)), HC + Vector((1.1, 0.05, 1.05)), Vector(((HC.x + BC.x) / 2, HC.y + 0.05, 2.3)),
      BC + Vector((-1.0, 0.05, 0.85)), BC + Vector((-0.55, 0.05, 0.3))]
tube("Artery", [tuple(p) for p in AP], [0.14] * len(AP), art_m)
CUM = [0.0]
for a_, b_ in zip(AP, AP[1:]):
    CUM.append(CUM[-1] + (b_ - a_).length)
def at(u):
    u = u % 1.0
    d = u * CUM[-1]
    for i in range(len(AP) - 1):
        if d <= CUM[i + 1]:
            t_ = (d - CUM[i]) / (CUM[i + 1] - CUM[i])
            return AP[i].lerp(AP[i + 1], t_)
    return AP[-1]
STOP = W(4, 0.3)
def flow(f):
    """distance travelled (in path fractions) at frame f."""
    sp = 0.5 / FPS
    u = min(f, STOP) * sp
    if f > S[12]:
        for p0 in range(S[12], E(12) - 6, 12):
            if f > p0:
                u += 0.14 * min(1.0, (f - p0) / 4)
    if f > REBEAT:
        u += (f - REBEAT) * sp
    return u
NC = 16
for k in range(NC):
    c_ = sphere("RBC", (0, 0, 0), 0.085, cellr_m, scale=(1, 1, 0.55), sub=2)
    o_ = sphere("O2d", (0, 0, 0), 0.05, o2_m, sub=1)
    ck, ok = [], []
    for f in range(0, FRAMES + 1):
        p_ = at(k / NC + flow(f))
        ck.append((f, tuple(p_))); ok.append((f, tuple(p_ + Vector((0, -0.09, 0.06)))))
    jumps(c_, ck); jumps(o_, ok)
    vis(o_, [(0, W(4, 0.45) + k % 4), (S[12] + 4, FRAMES + 1)])
# brain
bg_ = group("Brain", tuple(BC))
bp = [sphere("BrainL", tuple(BC + Vector((-0.3, 0, 0))), 0.55, brain_m, scale=(1.0, 0.85, 0.85), sub=2, smooth=False),
      sphere("BrainR", tuple(BC + Vector((0.3, 0, 0))), 0.55, brain_m, scale=(1.0, 0.85, 0.85), sub=2, smooth=False),
      cyl("BrainStem", tuple(BC + Vector((0.05, 0.05, -0.45))), 0.14, 0.35, brain_m, verts=12)]
attach(bp, bg_)
bbs = brain_m.node_tree.nodes["Principled BSDF"]
for f, em in [(0, 0.25), (W(12, 0.4), 0.25), (W(12, 0.4) + 6, 0.9), (E(12), 0.9), (E(12) + 6, 0.25)]:
    bbs.inputs["Emission Strength"].default_value = em; bbs.inputs["Emission Strength"].keyframe_insert("default_value", frame=f)
# line 5: oxygen bubbles, the brain takes 1 of 5 (20%)
BUB = []
for k in range(5):
    p_ = Vector((BC.x - 1.3 + k * 0.65, BC.y - 1.05, 0.38))
    b_ = sphere(f"Bub{k}", tuple(p_), 0.22, o2_m, sub=2)
    t_ = text(f"BubT{k}", "O2", tuple(p_ + Vector((0, -0.24, 0))), 0.16, white_lab, extrude=0.01)
    BUB.append((b_, t_, p_))
GO = W(5, 0.5)
for k, (b_, t_, p_) in enumerate(BUB):
    for o_ in (b_, t_):
        pop(o_, S[5] + 2 + 2 * k, 4, S[6])
b0, t0_, p0_ = BUB[2]
tgt = BC + Vector((0, -0.45, 0.1))
for o_, off in ((b0, Vector((0, 0, 0))), (t0_, Vector((0, -0.24, 0)))):
    key_loc(o_, [(GO, tuple(p0_ + off)), (GO + 8, tuple(tgt + off))])
pop(sphere("BrainPing", tuple(tgt), 0.3, o2_m, sub=2), GO + 8, 3, GO + 14)
burst(tuple(tgt), GO + 8, n=10, r=0.6, size=0.05, material=spark_m, f_out=GO + 18)
# line 8: brain cells go grey
for k in range(18):
    p_ = BC + Vector((random.uniform(-0.75, 0.75), -0.5, random.uniform(-0.3, 0.38)))
    ca = sphere("BCell", tuple(p_), 0.075, pspark_m, sub=1)
    cd = sphere("BCellD", tuple(p_), 0.075, deadc_m, sub=1)
    tk = W(8, 0.15 + 0.7 * k / 18)
    vis(ca, [(S[8], tk)]); vis(cd, [(tk, S[9])])
stopwatch("SW8", (BC.x + 1.35, BC.y - 0.5, 0.95), [(S[8], S[9])], 4)
# line 12: giant CPR hands press the heart
HH_ = HC + Vector((0, -0.1, 1.05))
hg_ = group("CPRHands", tuple(HH_))
hs = [boxc("HandTop", tuple(HH_ + Vector((0, 0, 0.18))), (0.75, 0.5, 0.22), skin_m, bevel=0.1),
      boxc("HandBot", tuple(HH_), (0.75, 0.5, 0.22), skin_m, bevel=0.1),
      tube("ArmCPR1", [tuple(HH_ + Vector((-0.2, 0.05, 0.25))), tuple(HH_ + Vector((-0.3, 0.1, 1.2)))], [0.12, 0.12], green_lab),
      tube("ArmCPR2", [tuple(HH_ + Vector((0.2, 0.05, 0.25))), tuple(HH_ + Vector((0.3, 0.1, 1.2)))], [0.12, 0.12], green_lab)]
attach(hs, hg_)
vis(hg_, [(S[12], E(12))])
for f in range(S[12], E(12) - 6, 12):
    key_loc(hg_, [(f, tuple(HH_ + Vector((0, 0, 0.1)))), (f + 4, tuple(HH_ - Vector((0, 0, 0.12)))), (f + 9, tuple(HH_ + Vector((0, 0, 0.1))))])

# =================== views (camera, subject) per line; subject in the lower third ===================
V, V2 = {}, {}
V[0] = ((A.x + 1.6, -3.6, 0.9), (A.x + 0.4, A.y, 0.9));          V2[0] = ((A.x - 0.6, -3.0, 0.9), (A.x + 0.4, A.y, 0.9))
V[1] = ((HC.x + 1.2, -3.0, 1.4), (HC.x - 0.5, HC.y, 1.3));       V2[1] = ((HC.x - 1.6, -2.8, 1.4), (HC.x - 0.5, HC.y, 1.3))
V[2] = ((HC.x - 2.4, -3.2, 1.4), (HC.x - 0.8, HC.y, 1.3));       V2[2] = ((HC.x - 0.6, -2.6, 1.4), (HC.x - 0.8, HC.y, 1.3))
V[3] = ((HC.x + 0.8, -2.6, 1.4), (HC.x - 0.7, HC.y, 1.3));       V2[3] = ((HC.x - 1.5, -2.4, 1.4), (HC.x - 0.7, HC.y, 1.3))
V[4] = ((HC.x + 1.2, -5.6, 1.6), (HC.x + 2.0, HC.y, 1.5));       V2[4] = ((HC.x + 3.0, -5.2, 1.6), (HC.x + 2.0, HC.y, 1.5))
V[5] = ((BC.x - 1.4, -3.0, 1.0), (BC.x - 0.1, BC.y, 0.9));       V2[5] = ((BC.x + 0.9, -2.8, 1.0), (BC.x - 0.1, BC.y, 0.9))
V[6] = ((A.x + 0.6, -3.8, 0.8), (A.x - 0.2, A.y, 0.7));          V2[6] = ((A.x - 1.6, -3.4, 0.6), (A.x - 0.6, A.y, 0.5))
V[7] = ((A.x - 2.4, -3.3, 0.5), (A.x - 0.8, A.y - 0.3, 0.5));    V2[7] = ((A.x + 0.4, -3.1, 0.5), (A.x - 0.8, A.y - 0.3, 0.5))
V[8] = ((BC.x + 1.4, -2.9, 1.0), (BC.x + 0.2, BC.y, 0.9));       V2[8] = ((BC.x - 0.9, -2.6, 1.0), (BC.x + 0.2, BC.y, 0.9))
V[9] = ((M.x + 2.8, -3.6, 1.0), (M.x + 1.2, A.y, 0.9));          V2[9] = ((M.x - 0.2, -3.3, 1.0), (M.x + 1.1, A.y, 0.9))
V[10] = ((A.x - 0.4, -4.6, 0.8), (A.x - 1.9, A.y + 0.5, 0.5));   V2[10] = ((A.x - 2.2, -4.0, 0.8), (A.x - 1.3, A.y + 0.4, 0.5))
V[11] = ((CH.x + 1.4, -2.8, 0.6), (CH.x, A.y, 0.6));             V2[11] = ((CH.x - 1.2, -2.6, 0.6), (CH.x, A.y, 0.6))
V[12] = ((HC.x + 3.0, -6.6, 1.6), (HC.x + 1.9, HC.y, 1.5));      V2[12] = ((HC.x + 0.8, -6.2, 1.6), (HC.x + 1.8, HC.y, 1.5))
V[13] = ((CH.x + 1.9, -3.0, 0.5), (CH.x + 0.4, A.y - 0.2, 0.5)); V2[13] = ((CH.x - 0.6, -2.7, 0.5), (CH.x + 0.3, A.y - 0.2, 0.5))
V[14] = ((HC.x - 0.1, -3.6, 1.3), (HC.x - 0.9, HC.y, 1.2));      V2[14] = ((HC.x - 2.4, -3.3, 1.3), (HC.x - 0.9, HC.y, 1.2))
V[15] = ((A.x + 1.6, -4.4, 0.9), (A.x - 0.1, A.y + 0.4, 0.9));   V2[15] = ((A.x - 1.6, -4.0, 0.9), (A.x - 0.1, A.y + 0.4, 0.9))
V[16] = ((A.x - 2.6, -4.6, 1.0), (A.x - 0.4, A.y, 0.7));         V2[16] = ((A.x - 0.5, -8.5, 2.0), (A.x - 0.4, A.y, 0.7))

for D_ in (V, V2):
    for i_ in list(D_):
        c_, t_ = D_[i_]
        D_[i_] = ((c_[0], c_[1] - 2.0, c_[2]), t_)

def LB(i, name, body, m_, size=None, f_in=None, f_out=None, Dk=0.55, end=False, v=0.26, u=0.0):
    mid = lambda a, b: tuple((Vector(a) + Vector(b)) / 2)
    view = V2[i] if end else (mid(V[i][0], V2[i][0]), mid(V[i][1], V2[i][1]))
    cl = Vector(CL(view)); D = (Vector(view[1]) - cl).length * Dk
    s_ = 0.9 * fit(body, D, size if size else 1e9)
    return label(name, body, view, D, v, s_, m_, (S[i] + 3) if f_in is None else f_in,
                 E(i) if f_out is None else f_out, u)
LB(0, "L0", "10 MINUTES?", lab_m)
LB(1, "L1", "100,000 BEATS A DAY", lab_m)
LB(2, "L2", "STOPPED!", red_lab, f_in=S[2] + 3)
LB(3, "L3", "QUIVERING", lab_m)
LB(4, "L4", "NO OXYGEN", blue_lab, f_in=STOP)
LB(5, "L5", "20% OF YOUR OXYGEN", pink_lab)
LB(6, "L6", "10 SECONDS", lab_m)
LB(7, "L7", "NO PULSE", red_lab)
LB(8, "L8", "4 MINUTES", red_lab)
LB(9, "L9", "-10% EVERY MINUTE", red_lab)
LB(10, "L10", "CPR!", green_lab)
LB(11, "L11", "2 PUSHES A SECOND", lab_m)
LB(12, "L12", "BLOOD TO BRAIN", pink_lab)
LB(13, "L13", "AED ZAP!", lab_m, f_in=ZAP - 4)
LB(14, "L14", "RHYTHM BACK!", green_lab)
LB(15, "L15", "SOME SURVIVE!", green_lab)
LB(16, "L16", "COULD YOU DO CPR?", lab_m, end=True, f_in=S[16] + 6, Dk=0.45)
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
for i in range(len(S)):
    for f, view in ((S[i], V[i]), (E(i) - 1, V2[i])):
        cl = CL(view)
        cam.location = cl; cam.keyframe_insert("location", frame=f)
        target.location = aim(cl, view[1]); target.keyframe_insert("location", frame=f)
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
