# Day 23 — What if you got stung by a box jellyfish?  Build: python3 episodes/023-box-jellyfish/scene.py
# Reference style: base (helpers, lawn/soil, house, garden) copied from episodes/003-lift-million-ref/scene.py (via 019)
import bpy, math, random, os, json
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
random.seed(23)
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
PZP = -1.45                                       # you stand on the pool step
box("Step", (0.0, 0.6, (PZF + PZP) / 2), (2.6, 1.6, PZP - PZF), tile_m)

# ---------------- the box jellyfish ----------------
JC = Vector((1.6, 0.6, -0.55))
jelly = group("Jelly", tuple(JC))
jp = [boxc("Bell", tuple(JC), (0.8, 0.8, 0.7), jelly_m, bevel=0.22),
      sphere("Core", tuple(JC + Vector((0, 0, -0.05))), 0.18, jcore_m, scale=(1.0, 1.0, 0.7), sub=2)]
for k in range(4):
    a = k * math.pi / 2
    sphere("CoreLobe", tuple(JC + Vector((0.16 * math.cos(a), 0.16 * math.sin(a), -0.12))), 0.08, jcore_m, sub=1)
TENTS = []
for cx in (-1, 1):
    for cy in (-1, 1):
        for j in range(3):
            st = JC + Vector((cx * 0.33 + j * 0.03 * cx, cy * 0.33, -0.32))
            pts, rad = [], []
            for n in range(7):
                t_ = n / 6
                pts.append(tuple(st + Vector((0.07 * math.sin(n * 1.3 + j) - 0.05 * t_, 0.04 * math.cos(n + j), -t_ * (0.95 - 0.08 * j)))))
                rad.append(0.035 * (1 - 0.6 * t_))
            TENTS.append(tube("Tent", pts, rad, jelly_m))
jp += TENTS
EYES = []
for (nx, ny) in [(0, -1), (-1, 0), (1, 0), (0, 1)]:
    c0 = JC + Vector((nx * 0.405, ny * 0.405, -0.16))
    for e in range(6):
        a = e / 6 * 6.283
        t_ = Vector((ny, -nx, 0)) if nx == 0 else Vector((0, 1, 0))
        p_ = c0 + t_ * 0.075 * math.cos(a) + Vector((0, 0, 0.065 * math.sin(a)))
        EYES.append(sphere("JEye", tuple(p_), 0.032, eyeb, sub=1))
jp += EYES
attach(jp, jelly)
# bobbing + wiggle
for f in range(0, FRAMES + 12, 12):
    k_ = f // 12
    jelly.location = tuple(JC + Vector((0, 0, 0.06 * math.sin(k_ * 1.1)))); jelly.keyframe_insert("location", frame=f)
    jelly.scale = (1.0 + 0.04 * math.sin(k_ * 1.1 + 1.5), 1.0 + 0.04 * math.sin(k_ * 1.1 + 1.5), 1.0 - 0.05 * math.sin(k_ * 1.1 + 1.5))
    jelly.keyframe_insert("scale", frame=f)
# eyes pop one by one (line 2)
for i_, e_ in enumerate(EYES):
    hide_until(e_, W(2, 0.02 + 0.018 * i_))
# "almost invisible": the jelly fades out at line 1, then shows itself
for f, a in [(0, 0.6), (S[1] - 1, 0.6), (S[1], 0.06), (W(1, 0.5), 0.06), (W(1, 0.75), 0.6)]:
    jb.inputs["Alpha"].default_value = a; jb.inputs["Alpha"].keyframe_insert("default_value", frame=f)
for f, a in [(0, 0.9), (S[1] - 1, 0.9), (S[1], 0.05), (W(1, 0.5), 0.05), (W(1, 0.75), 2.2), (E(1), 0.9)]:
    jb.inputs["Emission Strength"].default_value = a; jb.inputs["Emission Strength"].keyframe_insert("default_value", frame=f)
burst(tuple(JC + Vector((0, -0.6, 0.1))), W(1, 0.72), n=14, r=0.75, size=0.04, material=spark_m, f_out=E(1))

# ---------------- you ----------------
you, YD = person("You", (0, 0, 0), 1.0, mat("Shirt", (0.95, 0.45, 0.2), 0.6), mat("Pants", (0.2, 0.3, 0.55), 0.7),
                 skin_m, mat("Hair", (0.25, 0.14, 0.07), 0.8))
youP = group("YouDrift", (0, 0, 0)); you.parent = youP
HID = (0, 60, -30)
POOLP = (-1.2, 0.6, PZP)
LAWNP = (-5.0, 1.0, 0.0)
DECKP = (-4.5, 0.7, 0.0)
jumps(you, [(0, POOLP), (S[1], HID), (S[3], LAWNP), (S[4], HID), (S[8], (0.7, 0.6, PZP)), (S[9], HID), (S[11], DECKP), (S[16], HID), (S[17], DECKP)])
you.rotation_euler = (0, 0, math.radians(-12)); you.keyframe_insert("rotation_euler", frame=0)
TOUCH = W(0, 0.72)
key_loc(youP, [(0, (0, 0, 0)), (TOUCH, (1.98, 0, 0)), (S[1] - 1, (1.85, 0, 0)), (S[1], (0, 0, 0))])
HANDW = Vector((POOLP[0] + 1.98 + 0.38, 0.52, PZP + 0.76))
# zap on touch
zap = sphere("Zap", tuple(HANDW), 0.22, redglow, sub=2)
keyscale(zap, [(0, 0.001), (TOUCH - 1, 0.001), (TOUCH, 1.6), (TOUCH + 3, 0.8), (TOUCH + 6, 1.4), (S[1] - 1, 0.6), (S[1], 0.001)])
burst(tuple(HANDW), TOUCH, n=12, r=0.45, size=0.05, material=bolt_m, f_out=S[1])
bolt("Bolt0a", (HANDW.x - 0.45, HANDW.y - 0.15, HANDW.z + 0.5), 0.7, TOUCH, S[1], 2)
bolt("Bolt0b", (HANDW.x + 0.5, HANDW.y - 0.15, HANDW.z + 0.45), 0.6, TOUCH + 1, S[1], 2)

# =================== line 2: no brain ===================
BR = Vector((3.05, 0.35, -0.6))
brg = group("Brain", tuple(BR))
brp = [sphere("BrainL", tuple(BR + Vector((-0.17, 0, 0))), 0.26, pink_lab, scale=(1.0, 0.8, 0.85), sub=2, smooth=False),
       sphere("BrainR", tuple(BR + Vector((0.17, 0, 0))), 0.26, pink_lab, scale=(1.0, 0.8, 0.85), sub=2, smooth=False)]
attach(brp, brg)
keyscale(brg, [(0, 0.001), (W(2, 0.5) - 1, 0.001), (W(2, 0.5) + 3, 1.2), (W(2, 0.5) + 5, 1.0), (E(2) - 1, 1.0), (E(2), 0.001)])
xstamp("XBrain", tuple(BR + Vector((0, -0.25, 0))), W(2, 0.66), E(2), s=0.45)

# =================== line 3: 3 m tentacle vs you on the lawn ===================
GAX = -6.6
gal = group("Gallows", (GAX, 1.0, 0))
gp = [box("GalPost", (GAX - 0.9, 1.0, 1.7), (0.14, 0.14, 3.4), post_m), box("GalBar", (GAX - 0.45, 1.0, 3.35), (1.0, 0.14, 0.12), post_m),
      box("GalFoot", (GAX - 0.9, 1.0, 0.05), (0.7, 0.7, 0.1), post_m)]
tpts = [(GAX + 0.08 * math.sin(n * 1.2), 1.0, 3.3 - n * 0.3) for n in range(11)]
gp.append(tube("BigTent", tpts, [0.11 - 0.005 * n for n in range(11)], jelly_m))
gp.append(sphere("BigTentTop", (GAX, 1.0, 3.3), 0.12, jelly_m, sub=2))
attach(gp, gal)
vis(gal, [(S[3], S[4])])
for m_i in range(1, 4):
    rt = text(f"Rule{m_i}", f"{m_i} m", (GAX + 0.6, 0.85, m_i * 1.0), 0.4, lab_m, extrude=0.03)
    tk = box(f"RTick{m_i}", (GAX + 0.2, 0.9, m_i * 1.0), (0.3, 0.05, 0.05), white_lab)
    for o_ in (rt, tk):
        vis(o_, [(W(3, 0.15 + 0.15 * m_i), S[4])])
yb = box("YouBar", (LAWNP[0] + 0.75, 0.85, 0.85), (0.06, 0.05, 1.7), white_lab)
yt = text("YouT", "YOU", (LAWNP[0] + 0.75, 0.82, 1.95), 0.28, white_lab, extrude=0.02)
for o_ in (yb, yt):
    vis(o_, [(W(3, 0.2), S[4])])
# extra tentacles sprout under the bell (counts toward "60")
for k in range(8):
    o_ = TENTS[k]
    keyscale(o_, [(0, 1.0)])

# =================== zoom zone: giant tentacle over a skin cut-away (lines 4-7, 13) ===================
ZX, ZY = 10.5, 1.0
ZT = 2.0
gtent = group("GiantTent", (ZX, ZY, ZT))
bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=0.42, depth=4.6, location=(ZX, ZY, ZT), rotation=(0, math.radians(90), 0))
gt_o = bpy.context.object; gt_o.data.materials.append(gten_m); bpy.ops.object.shade_smooth()
gparts = [gt_o]
CAPS = []
for r_, z_ in enumerate((ZT + 0.22, ZT, ZT - 0.22)):
    for k in range(9):
        x_ = ZX - 1.95 + k * 0.49 + (0.24 if r_ == 1 else 0)
        if x_ > ZX + 2.1:
            continue
        yv = ZY - 0.42 * math.cos(math.asin((z_ - ZT) / 0.45)) - 0.02
        c_ = sphere("Cap", (x_, yv, z_), 0.09, caps_m, scale=(1.0, 0.7, 1.35), sub=2)
        coil = sphere("Coil", (x_, yv - 0.04, z_), 0.045, coil_m, scale=(1, 0.5, 1.6), sub=1)
        CAPS.append((c_, coil, Vector((x_, yv, z_)), r_))
        gparts += [c_, coil]
attach(gparts, gtent)
vis(gtent, [(S[4], S[8]), (S[13], S[14])])
for i_, (c_, coil, p_, r_) in enumerate(CAPS):
    hide_until(c_, S[4] + 2 + (i_ * 7) % 26)
    hide_until(coil, S[4] + 2 + (i_ * 7) % 26)
# tentacle brushes down onto the skin on line 5
key_loc(gtent, [(S[4], (ZX, ZY, ZT)), (W(5, 0.3), (ZX, ZY, ZT)), (W(5, 0.5), (ZX, ZY, ZT - 0.45)), (S[8], (ZX, ZY, ZT - 0.45)),
                (S[13], (ZX, ZY, ZT - 0.45))])
DZ = -0.45
# skin cut-away slab
skin = group("Skin", (ZX, 1.0, 0))
sk = [box("Epi", (ZX, 1.0, 0.95), (4.6, 0.8, 0.1), epi_m), box("Derm", (ZX, 1.0, 0.65), (4.6, 0.8, 0.5), der_m),
      box("Fat", (ZX, 1.0, 0.2), (4.6, 0.8, 0.4), fat_m)]
attach(sk, skin)
vis(skin, [(S[4], S[8]), (S[13], S[14])])
# harpoons fire from the lower row (line 5), venom travels down (line 7)
FIRE = W(5, 0.55)
HARP = []
for i_, (c_, coil, p_, r_) in enumerate(CAPS):
    if r_ != 2:
        continue
    top = p_ + Vector((0, -0.08, DZ - 0.08))
    L_ = top.z - 0.55
    h = cyl("Harp", (0, 0, 0), 0.03, L_, harp_m, r2=0.004, verts=8, rot=(math.radians(180), 0, 0))
    h.data.transform(Matrix.Translation((0, 0, -L_ / 2))) if False else None
    bpy.context.view_layer.update()
    h.location = tuple(top - Vector((0, 0, L_ / 2)))
    f0 = FIRE + (i_ % 5)
    hb = group("HarpG", tuple(top)); parent_to(h, hb)
    keyscale(hb, [(0, (1, 1, 0.001)), (f0 - 1, (1, 1, 0.001)), (f0 + 2, (1, 1, 1.0)), (S[8] - 1, (1, 1, 1.0)), (S[8], (1, 1, 0.001))])
    vis(coil, [(S[4] + 2 + (i_ * 7) % 26, f0)])
    HARP.append((top, L_, f0))
    burst(tuple(top + Vector((0, 0, -L_))), f0 + 2, n=6, r=0.12, size=0.03, material=spark_m, f_out=f0 + 9)
# line 6: speed streaks + spinning stopwatch
for k in range(12):
    y_ = 0.15 - (k % 3) * 0.05
    z_ = random.uniform(0.6, 2.5)
    st_ = box("Streak", (0, 0, 0), (0.7, 0.03, 0.04), bolt_m)
    t0 = S[6] + (k * 3) % (E(6) - S[6] - 4)
    key_loc(st_, [(t0, (ZX + 3.0, y_, z_)), (t0 + 4, (ZX - 3.0, y_, z_))])
    lin(st_)
    vis(st_, [(t0, t0 + 5)])
SWC = (ZX + 1.45, 0.2, 0.75)
swg = group("Stopwatch", SWC)
swp = [cyl("SWBody", SWC, 0.5, 0.12, white_lab, rot=(math.radians(90), 0, 0), verts=32),
       cyl("SWRim", (SWC[0], SWC[1] + 0.02, SWC[2]), 0.56, 0.1, gold_m, rot=(math.radians(90), 0, 0), verts=32),
       cyl("SWKnob", (SWC[0], SWC[1], SWC[2] + 0.62), 0.09, 0.14, gold_m, verts=12)]
attach(swp, swg)
hand_ = boxc("SWHand", (SWC[0], SWC[1] - 0.09, SWC[2]), (0.05, 0.03, 0.42), red_lab)
hand_.data.transform(Matrix.Translation((0, 0, 0.18)))
hg = group("SWHandG", (SWC[0], SWC[1] - 0.09, SWC[2])); parent_to(hand_, hg)
keyrot(hg, [(S[6], (0, 0, 0)), (E(6), (0, math.radians(360 * 9), 0))]); lin(hg)
vis(swg, [(S[6], S[7])]); vis(hg, [(S[6], S[7])])
# line 7: venom pours down the harpoons and spreads in the skin
for k, (top, L_, f0) in enumerate(HARP):
    for j in range(3):
        v_ = sphere("VenomD", tuple(top), 0.05, venom_m, sub=1)
        t0 = S[7] + j * 5 + k
        tip = top + Vector((0, -0.02, -L_))
        spread = tip + Vector((random.uniform(-0.35, 0.35), 0, random.uniform(-0.35, 0.05)))
        key_loc(v_, [(t0, tuple(top)), (t0 + 6, tuple(tip)), (t0 + 14, tuple(spread))])
        vis(v_, [(t0, S[8])])
for k in range(22):
    p_ = (ZX + random.uniform(-2.1, 2.1), 0.58, random.uniform(0.45, 0.85))
    b_ = sphere("VenomCloud", p_, random.uniform(0.06, 0.12), venom_m, sub=1)
    pop(b_, W(7, 0.3) + k % 10, 4, S[8])
# line 13: vinegar rains on the tentacle; unfired stingers locked (green)
for k in range(18):
    x_ = ZX + random.uniform(-2.0, 2.0)
    d_ = sphere("VRain", (x_, 0.45, 3.4), 0.06, vdrop_m, scale=(0.8, 0.8, 1.4), sub=1)
    t0 = S[13] + (k * 2) % 18
    key_loc(d_, [(t0, (x_, 0.45, 3.6)), (t0 + 8, (x_, 0.45, ZT + DZ + 0.4))])
    lin(d_)
    vis(d_, [(t0, t0 + 8)], (0.8, 0.8, 1.4))
for i_, (c_, coil, p_, r_) in enumerate(CAPS):
    if r_ == 2:
        continue
    g_ = sphere("Lock", tuple(p_ + Vector((0, -0.03, DZ))), 0.13, grnglow, scale=(1.0, 0.6, 1.3), sub=2)
    pop(g_, W(13, 0.3) + (i_ % 9), 4, S[14])

# =================== line 8: pain in the pool ===================
pain = sphere("PainGlow", tuple(Vector((0.7 + 0.37, 0.52, PZP + 0.9))), 0.3, redglow, sub=2)
kk = [(0, 0.001), (S[8] - 1, 0.001)]
for j, f in enumerate(range(S[8], E(8), 4)):
    kk.append((f, 1.0 if j % 2 == 0 else 1.5))
kk += [(E(8) - 1, 1.0), (E(8), 0.001)]
keyscale(pain, kk)
for k, (dx, dz) in enumerate([(-0.6, 0.9), (0.9, 0.8), (1.25, 0.2)]):
    bolt(f"PainBolt{k}", (0.7 + dx, 0.35, PZP + 1.2 + dz * 0.6), 0.75, S[8] + k * 2, E(8), 3)
MX = -1.8; MY = 4.4
mtr = group("Meter", (MX, MY, 0))
mp = [box("MFrame", (MX, MY, 1.3), (0.7, 0.2, 2.6), board_m, bevel=0.04), box("MPost", (MX, MY + 0.1, 0.1), (0.4, 0.4, 0.2), post_m)]
attach(mp, mtr)
vis(mtr, [(S[8], S[9])])
for k, m_ in enumerate((green_lab, green_lab, lab_m, lab_m, red_lab, red_lab)):
    seg_ = box(f"MSeg{k}", (MX, MY - 0.12, 0.25 + k * 0.4), (0.5, 0.06, 0.34), m_)
    vis(seg_, [(W(8, 0.1 + 0.1 * k), S[9])])
mt = text("M10", "10/10", (MX, MY - 0.16, 2.95), 0.4, red_lab, extrude=0.03)
pop(mt, W(8, 0.72), 4, S[9])

# =================== lines 9-10: the heart ===================
HC = Vector((-8.6, 1.2, 1.5))
hrt = group("Heart", tuple(HC))
hp = [sphere("HL", tuple(HC + Vector((-0.33, 0, 0.2))), 0.48, heart_m, sub=3), sphere("HR", tuple(HC + Vector((0.33, 0, 0.2))), 0.48, heart_m, sub=3),
      cyl("HV", tuple(HC + Vector((0, 0, -0.4))), 0.72, 0.85, heart_m, rot=(math.radians(180), 0, 0), r2=0.03, verts=24)]
hp[2].scale = (1.0, 0.62, 1.0)
attach(hp, hrt)
vis(box("HPed", (HC.x, HC.y, 0.3), (1.0, 1.0, 0.6), board_m, bevel=0.05), [(S[9], S[11])])
vis(hrt, [(S[9], S[11])])
kk = [(S[9], 1.0)]
for j, f in enumerate(range(S[9], W(9, 0.6), 3)):
    kk.append((f, 1.0 if j % 2 == 0 else 1.18))
kk += [(W(9, 0.62), 1.0), (S[10], 1.0)]
for j, f in enumerate(range(S[10], S[11], 9)):
    kk.append((f, 1.0 if j % 2 == 0 else 1.1))
for f, s in kk:
    hrt.keyframe_insert("scale", frame=f) if False else None
hb2 = group("HeartBeat", tuple(HC)); parent_to(hrt, hb2)
for f, s in kk:
    hb2.scale = (s,) * 3; hb2.keyframe_insert("scale", frame=f)
# warning ring
bpy.ops.mesh.primitive_torus_add(major_radius=1.05, minor_radius=0.06, location=tuple(HC + Vector((0, -0.2, 0))), rotation=(math.radians(90), 0, 0))
wr = bpy.context.object; wr.data.materials.append(redglow)
kk = [(0, 0.001), (S[9] - 1, 0.001)]
for j, f in enumerate(range(S[9], E(9), 4)):
    kk.append((f, 1.0 if j % 2 == 0 else 1.2))
kk += [(E(9), 0.001)]
keyscale(wr, kk)
bpy.ops.mesh.primitive_torus_add(major_radius=1.05, minor_radius=0.06, location=tuple(HC + Vector((0, -0.2, 0))), rotation=(math.radians(90), 0, 0))
gr = bpy.context.object; gr.data.materials.append(grnglow)
vis(gr, [(S[10], S[11])])
for k in range(10):
    a = k / 10 * 6.283
    v_ = sphere("VenomH", tuple(HC), 0.08, venom_m, sub=1)
    key_loc(v_, [(S[9] + k, tuple(HC + Vector((1.6 * math.cos(a), -0.3, 1.6 * math.sin(a))))), (S[9] + k + 10, tuple(HC + Vector((0.55 * math.cos(a), -0.4, 0.55 * math.sin(a)))))])
    vis(v_, [(S[9] + k, E(9))])
# ECG screen beside the heart
ECX = HC.x + 1.75
for o_ in (box("ECGScr", (ECX, HC.y, 1.15), (1.3, 0.1, 0.9), screen_m, bevel=0.03), box("ECGPost", (ECX, HC.y + 0.05, 0.35), (0.12, 0.12, 0.7), post_m)):
    vis(o_, [(S[9], S[11])])
ecg = [(ECX - 0.55, HC.y - 0.07, 1.1), (ECX - 0.3, HC.y - 0.07, 1.1), (ECX - 0.22, HC.y - 0.07, 1.45), (ECX - 0.14, HC.y - 0.07, 0.85),
       (ECX - 0.06, HC.y - 0.07, 1.1), (ECX + 0.15, HC.y - 0.07, 1.1), (ECX + 0.23, HC.y - 0.07, 1.45), (ECX + 0.31, HC.y - 0.07, 0.85),
       (ECX + 0.39, HC.y - 0.07, 1.1), (ECX + 0.55, HC.y - 0.07, 1.1)]
eg = tube("ECGLine", ecg, [0.025] * len(ecg), ecgg_m)
vis(eg, [(S[9], W(9, 0.6)), (S[10], S[11])])
ef = tube("ECGFlat", [(ECX - 0.55, HC.y - 0.07, 1.1), (ECX + 0.55, HC.y - 0.07, 1.1)], [0.025] * 2, redglow)
vis(ef, [(W(9, 0.6), S[10])])
check("Chk10", (HC.x, HC.y - 0.5, HC.z + 1.45), W(10, 0.25), S[11], s=0.9)

# =================== line 11: out of the water, call for help ===================
ph = group("Phone", (DECKP[0] + 0.5, DECKP[1] - 0.25, 1.85))
pp_ = [box("PhB", (DECKP[0] + 0.5, DECKP[1] - 0.25, 1.85), (0.32, 0.06, 0.58), phone_m, bevel=0.03),
       box("PhS", (DECKP[0] + 0.5, DECKP[1] - 0.29, 1.87), (0.26, 0.02, 0.46), phs_m)]
attach(pp_, ph)
pop(ph, W(11, 0.3), 5, S[12])
for k in range(3):
    bpy.ops.mesh.primitive_torus_add(major_radius=0.12 + 0.1 * k, minor_radius=0.025, location=(DECKP[0] + 0.85, DECKP[1] - 0.3, 2.1), rotation=(math.radians(90), 0, 0))
    rg = bpy.context.object; rg.data.materials.append(phs_m)
    kk = [(0, 0.001), (W(11, 0.4) + k * 3 - 1, 0.001)]
    for j, f in enumerate(range(W(11, 0.4) + k * 3, S[12], 8)):
        if f + 6 < S[12]:
            kk += [(f, 0.6), (f + 6, 1.3)]
    kk.append((S[12], 0.001))
    keyscale(rg, kk)
ar = YD["arms"][1]
keyrot(ar, [(0, (0, 0, 0)), (S[11] - 1, (0, 0, 0)), (W(11, 0.25), (math.radians(-20), math.radians(-150), 0)), (S[12] - 1, (math.radians(-20), math.radians(-150), 0)),
            (S[12], (0, math.radians(-60), 0)), (S[13] - 1, (0, math.radians(-60), 0)), (S[13], (0, 0, 0))])
# lifeguard runs in
guard, GD = person("Guard", (0, 0, 0), 1.0, red_lab, mat("GPants", (0.95, 0.85, 0.2), 0.6), skin_m, mat("GHair", (0.1, 0.07, 0.05), 0.8))
key_loc(guard, [(0, (-9.5, 2.2, 0)), (W(11, 0.2), (-9.5, 2.2, 0)), (E(11), (-6.1, 1.1, 0)), (E(12), (-5.8, 1.0, 0))])
guard.rotation_euler = (0, 0, math.radians(-60)); guard.keyframe_insert("rotation_euler", frame=0)
vis(guard, [(S[11], S[13])])
for k, lg in enumerate(GD["legs"]):
    for j, f in enumerate(range(S[11], E(11), 4)):
        lg.rotation_euler = (math.radians(30 if (j + k) % 2 else -30), 0, 0); lg.keyframe_insert("rotation_euler", frame=f)
    lg.rotation_euler = (0, 0, 0); lg.keyframe_insert("rotation_euler", frame=E(11))

# =================== line 12: vinegar pour ===================
HANDD = Vector((DECKP[0] + 0.74, DECKP[1] - 0.2, 1.03))       # forearm held out (arm rotated -60)
M_ = HANDD + Vector((0.2, 0, 0.55))
btl = group("Bottle", tuple(M_))
bp = [cyl("BNeck", tuple(M_ + Vector((0, 0, 0.14))), 0.08, 0.28, vin_m, verts=16),
      cyl("BBody", tuple(M_ + Vector((0, 0, 0.62))), 0.24, 0.7, vin_m, verts=24),
      cyl("BLabel", tuple(M_ + Vector((0, 0, 0.62))), 0.245, 0.3, white_lab, verts=24),
      cyl("BShoulder", tuple(M_ + Vector((0, 0, 0.32))), 0.24, 0.14, vin_m, r2=0.08, verts=24)]
bp[3].rotation_euler = (math.radians(180), 0, 0)
attach(bp, btl)
btl.rotation_euler = (0, math.radians(170), 0); btl.keyframe_insert("rotation_euler", frame=S[12])
btl.rotation_euler = (0, math.radians(55), 0); btl.keyframe_insert("rotation_euler", frame=S[12] + 7)
btl.keyframe_insert("rotation_euler", frame=E(12))
vis(btl, [(S[12], S[13])])
for k in range(20):
    d_ = sphere("Pour", tuple(M_), 0.05, vdrop_m, sub=1)
    t0 = S[12] + 7 + (k * 2) % (E(12) - S[12] - 14)
    key_loc(d_, [(t0, tuple(M_)), (t0 + 6, tuple(HANDD + Vector((random.uniform(-0.12, 0.12), 0, 0.05))))])
    lin(d_)
    vis(d_, [(t0, t0 + 7)])
for k in range(8):
    a = k / 8 * 6.283
    s2 = sphere("Splash", tuple(HANDD), 0.04, vdrop_m, sub=1)
    t0 = S[12] + 14 + k
    key_loc(s2, [(t0, tuple(HANDD)), (t0 + 6, tuple(HANDD + Vector((0.35 * math.cos(a), -0.1, 0.25 + 0.2 * math.sin(a)))))])
    vis(s2, [(t0, min(t0 + 7, E(12)))])
sting = sphere("StingMark", tuple(HANDD + Vector((0, -0.05, 0))), 0.12, redglow, scale=(1.4, 1, 0.8), sub=2)
keyscale(sting, [(0, 0.001), (S[11] - 1, 0.001), (S[11], (1.4, 1, 0.8)), (W(12, 0.5), (1.4, 1, 0.8)), (E(12) - 1, (0.5, 0.4, 0.3)), (E(12), 0.001)])

# =================== line 14: don't rub, no fresh water ===================
def sign(name, x, title, tm, f_in, f_out, y=4.6, size=0.36):
    g = group(name, (x, y, 1.4))
    pr = [box(name + "B", (x, y, 1.45), (2.2, 0.12, 0.95), board_m, bevel=0.04),
          box(name + "P", (x, y + 0.1, 0.5), (0.14, 0.14, 1.0), post_m),
          text(name + "T", title, (x, y - 0.08, 1.45), size, tm, extrude=0.02)]
    attach(pr, g)
    keyscale(g, [(0, 0.001), (f_in - 1, 0.001), (f_in + 4, 1.12), (f_in + 6, 1.0), (f_out - 1, 1.0), (f_out, 0.001)])
    return g
sign("SignRub", 0.0, "RUBBING", mat("InkM", (0.08, 0.08, 0.1), 0.5), S[14], S[15])
sign("SignFresh", 2.4, "FRESH WATER", blue_lab, W(14, 0.45), S[15], size=0.32)
xstamp("XRub", (0.0, 4.4, 1.45), W(14, 0.22), S[15], s=0.75)
xstamp("XFresh", (2.4, 4.4, 1.45), W(14, 0.7), S[15], s=0.75)
# fresh water tap prop
cyl("Tap", (2.4, 4.9, 0.4), 0.06, 0.8, post_m, verts=10)

# =================== line 15: antivenom ===================
VC = Vector((1.2, 4.6, 0))
vg = group("Vial", tuple(VC))
vp = [cyl("VialG", tuple(VC + Vector((0, 0, 0.8))), 0.42, 1.4, vial_m, verts=32),
      cyl("VialL", tuple(VC + Vector((0, 0, 0.62))), 0.36, 1.0, anti_m, verts=32),
      cyl("VialCap", tuple(VC + Vector((0, 0, 1.62))), 0.3, 0.26, blue_lab, verts=24),
      cyl("VialBand", tuple(VC + Vector((0, 0, 0.85))), 0.43, 0.4, white_lab, verts=32)]
attach(vp, vg)
pop(vg, S[15] + 2, 6, S[16])
crs = group("Cross", tuple(VC + Vector((1.5, -0.2, 1.4))))
cp = [box("CrossV", tuple(VC + Vector((1.5, -0.2, 1.4))), (0.28, 0.1, 0.9), green_lab), box("CrossH", tuple(VC + Vector((1.5, -0.2, 1.4))), (0.9, 0.1, 0.28), green_lab)]
attach(cp, crs)
pop(crs, W(15, 0.35), 5, S[16])
burst(tuple(VC + Vector((0, -0.5, 1.0))), W(15, 0.2), n=12, r=0.9, size=0.06, material=spark_m, f_out=S[16])

# =================== line 16: stinger suit blocks the sting ===================
suit, SD = person("Suit", (0, 0, 0), 1.0, suit_m, suit_m, skin_m, suit_m)
suitP = group("SuitDrift", (0, 0, 0)); suit.parent = suitP
jumps(suit, [(0, HID), (S[16], POOLP), (S[17], HID)])
suit.rotation_euler = (0, 0, math.radians(-12)); suit.keyframe_insert("rotation_euler", frame=0)
vis(suit, [(S[16], S[17])])
for o_ in bpy.data.objects:
    if o_.name.startswith("SuitHair"):
        o_.scale = (1.12, 1.02, 1.0)
for sx in (-1, 1):
    tube(f"SuitStripe{sx}", [], [], suit_m) if False else None
TOUCH2 = W(16, 0.45)
key_loc(suitP, [(0, (0, 0, 0)), (S[16], (0, 0, 0)), (TOUCH2, (1.98, 0, 0)), (E(16), (1.9, 0, 0)), (S[17], (0, 0, 0))])
shield = sphere("Shield", tuple(HANDW), 0.42, green_lab, sub=3)
keyscale(shield, [(0, 0.001), (TOUCH2 - 1, 0.001), (TOUCH2 + 2, 1.2), (TOUCH2 + 4, 1.0), (S[17] - 1, 1.0), (S[17], 0.001)])
for k in range(10):
    a = k / 10 * 6.283
    sp_ = sphere("Bounce", tuple(HANDW), 0.04, spark_m, sub=1)
    key_loc(sp_, [(TOUCH2, tuple(HANDW)), (TOUCH2 + 8, tuple(HANDW + Vector((0.8 * math.cos(a), -0.3, 0.8 * math.sin(a)))))])
    vis(sp_, [(TOUCH2, TOUCH2 + 9)])
# shield material: translucent green
sm_ = bpy.data.materials.new("ShieldM"); sm_.use_nodes = True
sb_ = sm_.node_tree.nodes["Principled BSDF"]
sb_.inputs["Base Color"].default_value = (0.3, 1.0, 0.45, 1); sb_.inputs["Alpha"].default_value = 0.35
sb_.inputs["Emission Color"].default_value = (0.3, 1.0, 0.45, 1); sb_.inputs["Emission Strength"].default_value = 1.5
shield.data.materials[0] = sm_

# =================== line 17: question ===================
qm = text("QMark", "?", (DECKP[0] + 0.1, DECKP[1] - 0.1, 2.75), 1.4, lab_m, extrude=0.08)
pop(qm, S[17] + 4, 5)

# =================== views (camera, subject) per line; subject in the lower third ===================
V, V2 = {}, {}
V[0] = ((-1.6, -4.6, 0.0), (0.5, 0.6, -0.6));            V2[0] = ((1.0, -3.8, 0.0), (0.9, 0.6, -0.6))
V[1] = ((3.2, -3.3, 0.0), (1.6, 0.6, -0.6));             V2[1] = ((1.0, -3.0, 0.0), (1.6, 0.6, -0.6))
V[2] = ((1.0, -3.5, 0.0), (2.2, 0.5, -0.6));             V2[2] = ((3.0, -3.2, 0.0), (2.3, 0.5, -0.6))
V[3] = ((-3.4, -5.6, 1.4), (-5.7, 1.0, 1.2));            V2[3] = ((-7.2, -5.4, 1.4), (-5.8, 1.0, 1.2))
V[4] = ((ZX + 2.0, -3.6, 1.5), (ZX, 0.6, 1.4));          V2[4] = ((ZX + 0.6, -3.0, 1.5), (ZX, 0.6, 1.4))
V[5] = ((ZX - 1.8, -3.3, 1.2), (ZX, 0.6, 1.0));          V2[5] = ((ZX - 0.6, -2.9, 1.2), (ZX, 0.6, 1.0))
V[6] = ((ZX + 2.4, -3.0, 1.0), (ZX + 0.6, 0.4, 0.9));    V2[6] = ((ZX + 0.8, -2.7, 1.0), (ZX + 0.6, 0.4, 0.9))
V[7] = ((ZX - 0.8, -2.7, 0.8), (ZX, 0.6, 0.8));          V2[7] = ((ZX + 0.9, -2.5, 0.8), (ZX, 0.6, 0.8))
V[8] = ((-2.6, -4.6, 0.5), (-0.4, 1.5, 0.0));            V2[8] = ((0.4, -4.4, 0.5), (-0.3, 1.5, 0.0))
V[9] = ((HC.x - 0.8, -3.8, 1.4), (HC.x + 0.8, 1.2, 1.3)); V2[9] = ((HC.x + 1.6, -3.4, 1.4), (HC.x + 0.8, 1.2, 1.3))
V[10] = ((HC.x + 2.0, -3.6, 1.4), (HC.x + 0.8, 1.2, 1.3)); V2[10] = ((HC.x + 0.1, -3.1, 1.4), (HC.x + 0.8, 1.2, 1.3))
V[11] = ((-2.8, -4.4, 1.2), (-4.9, 0.9, 0.9));           V2[11] = ((-5.0, -3.8, 1.2), (-4.9, 0.9, 0.9))
V[12] = ((-6.4, -3.6, 1.2), (DECKP[0] + 0.5, 0.6, 1.1)); V2[12] = ((-3.0, -3.4, 1.2), (DECKP[0] + 0.5, 0.6, 1.1))
V[13] = ((ZX + 1.5, -3.2, 1.3), (ZX, 0.6, 1.3));         V2[13] = ((ZX - 1.2, -3.0, 1.3), (ZX, 0.6, 1.3))
V[14] = ((0.0, -1.8, 1.3), (1.2, 4.5, 1.1));            V2[14] = ((2.4, -1.4, 1.3), (1.2, 4.5, 1.1))
V[15] = ((3.6, -1.2, 1.0), (1.9, 4.5, 1.0));             V2[15] = ((1.4, -0.8, 1.0), (1.9, 4.5, 1.0))
V[16] = ((2.4, -4.0, 0.0), (0.7, 0.6, -0.6));            V2[16] = ((0.4, -3.6, 0.0), (0.9, 0.6, -0.6))
V[17] = ((-5.6, -5.0, 1.0), (-2.6, 0.8, 0.0));           V2[17] = ((-1.4, -9.0, 2.0), (-1.6, 1.0, 0.0))

def LB(i, name, body, m_, size=None, f_in=None, f_out=None, Dk=0.55, end=False, v=0.26, u=0.0):
    mid = lambda a, b: tuple((Vector(a) + Vector(b)) / 2)
    view = V2[i] if end else (mid(V[i][0], V2[i][0]), mid(V[i][1], V2[i][1]))
    cl = Vector(CL(view)); D = (Vector(view[1]) - cl).length * Dk
    s_ = 0.9 * fit(body, D, size if size else 1e9)
    return label(name, body, view, D, v, s_, m_, (S[i] + 3) if f_in is None else f_in,
                 E(i) if f_out is None else f_out, u)
LB(0, "L0", "BOX JELLYFISH!", red_lab, f_in=TOUCH)
LB(1, "L1", "SEE-THROUGH", lab_m)
LB(2, "L2", "24 EYES", lab_m, f_in=S[2] + 2, f_out=W(2, 0.55))
LB(2, "L2b", "NO BRAIN!", pink_lab, f_in=W(2, 0.6))
LB(3, "L3", "3 METERS!", lab_m)
LB(4, "L4", "MILLIONS OF STINGERS", white_lab)
LB(5, "L5", "FIRE!", red_lab, f_in=FIRE)
LB(6, "L6", "ULTRA FAST!", lab_m)
LB(7, "L7", "VENOM!", pink_lab)
LB(8, "L8", "PAIN 10/10", red_lab)
LB(9, "L9", "HEART DANGER", red_lab)
LB(10, "L10", "MOST SURVIVE", green_lab)
LB(11, "L11", "CALL FOR HELP!", lab_m)
LB(12, "L12", "VINEGAR!", lab_m)
LB(13, "L13", "STINGERS STOPPED", green_lab)
LB(14, "L14", "DON'T!", red_lab)
LB(15, "L15", "ANTIVENOM", blue_lab)
LB(16, "L16", "STINGER SUIT", green_lab)
LB(17, "L17", "WOULD YOU SWIM?", lab_m, end=True, f_in=S[17] + 6, Dk=0.45)

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
