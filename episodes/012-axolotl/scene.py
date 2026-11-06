# Day 12 — What if you could regrow body parts like an axolotl?  Build: python3 episodes/012-axolotl/scene.py
# Reference style: base (helpers, lawn/soil, house, garden) copied from episodes/003-lift-million-ref / 006-mantis-punch
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

# =====================================================================================
# Day 12 — What if you could regrow body parts like an axolotl?
# Facts used: axolotl (Ambystoma mexicanum), native to the Xochimilco lake/canal system near Mexico City;
#   adults typically ~15-30 cm, about 23 cm on average; regrows whole limbs (bone, muscle, nerves, skin) without a scar;
#   the wound is covered by new skin (wound epidermis) within about a day; a blastema (bud of progenitor cells) then
#   forms and rebuilds the limb over weeks (young animals faster); also repairs heart tissue and the spinal cord.
#   Humans: the liver can regrow from a fraction of its mass; young children can regrow a fingertip tip;
#   a lost limb does not regrow (it heals with a scar).
# =====================================================================================
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

# ---------------- garden table + aquarium ----------------
TX, TY, TZ = 0.0, 1.0, 0.75
wood = mat("Wood", (0.72, 0.48, 0.26), 0.7)
box("TableTop", (TX, TY, TZ - 0.03), (2.3, 0.85, 0.06), wood, bevel=0.01)
for x in (-1.05, 1.05):
    for y in (-0.35, 0.35):
        box("TLeg", (TX + x, TY + y, (TZ - 0.06) / 2), (0.06, 0.06, TZ - 0.06), wood)
KX = -0.4                                # tank centre x
AW, AD, AH = 0.9, 0.42, 0.42
KY = TY + 0.08
AY0 = KY - AD / 2                        # front glass plane
frame_m = mat("TankFrame", (0.12, 0.12, 0.14), 0.4)
for x in (-AW/2, AW/2):
    for y in (KY - AD/2, KY + AD/2):
        box("TFv", (KX + x, y, TZ + AH/2), (0.02, 0.02, AH), frame_m)
for z in (TZ + 0.01, TZ + AH):
    for y in (KY - AD/2, KY + AD/2):
        box("TFh", (KX, y, z), (AW + 0.02, 0.02, 0.02), frame_m)
    for x in (-AW/2, AW/2):
        box("TFd", (KX + x, KY, z), (0.02, AD, 0.02), frame_m)
wat = bpy.data.materials.new("WaterBack"); wat.use_nodes = True
N = wat.node_tree.nodes; Lk = wat.node_tree.links
N.remove(N["Principled BSDF"])
tcw = N.new("ShaderNodeTexCoord"); sw = N.new("ShaderNodeSeparateXYZ"); Lk.new(tcw.outputs["Generated"], sw.inputs[0])
rw_ = N.new("ShaderNodeValToRGB"); rw_.color_ramp.elements[0].color = (0.05, 0.35, 0.55, 1); rw_.color_ramp.elements[1].color = (0.35, 0.85, 0.9, 1)
Lk.new(sw.outputs["Z"], rw_.inputs[0])
emw = N.new("ShaderNodeEmission"); emw.inputs["Strength"].default_value = 0.85
Lk.new(rw_.outputs[0], emw.inputs[0]); Lk.new(emw.outputs[0], N["Material Output"].inputs["Surface"])
box("WaterBack", (KX, KY + AD/2 - 0.006, TZ + AH/2), (AW, 0.01, AH), wat)
for x in (-AW/2 + 0.006, AW/2 - 0.006):
    box("WaterSide", (KX + x, KY, TZ + AH/2), (0.01, AD, AH), wat)
sand_m = mat("Sand", (0.93, 0.82, 0.55), 0.9)
box("Sand", (KX, KY, TZ + 0.025), (AW, AD, 0.05), sand_m)
FL = TZ + 0.05
for i in range(10):
    sphere("TRock", (KX + random.uniform(-0.4, 0.4), KY + random.uniform(0.06, 0.18), FL + 0.005),
           random.uniform(0.018, 0.04), mat(f"TR{i}", random.choice([(0.55, 0.5, 0.48), (0.8, 0.45, 0.4), (0.45, 0.55, 0.6)]), 0.8),
           scale=(1.3, 1, 0.7), sub=1, smooth=False)
weed_m = mat("Weed", (0.2, 0.75, 0.35), 0.6)
for x in (-0.4, -0.34, -0.28, 0.3, 0.36, 0.41):
    h_ = random.uniform(0.18, 0.3)
    tube("Weed", [(KX + x, KY + 0.15, FL), (KX + x + 0.02, KY + 0.15, FL + h_ * 0.5), (KX + x - 0.015, KY + 0.15, FL + h_)],
         [0.01, 0.008, 0.004], weed_m)
glass_m = mat("Glass", (0.75, 0.92, 1.0), 0.05)
glass_m.node_tree.nodes["Principled BSDF"].inputs["Alpha"].default_value = 0.1
box("FrontGlass", (KX, AY0, TZ + AH/2), (AW, 0.004, AH), glass_m)
for i in range(12):
    p0 = (KX + random.uniform(-0.38, 0.38), KY + random.uniform(-0.05, 0.12), FL + 0.02)
    b_ = sphere("TankBub", p0, random.uniform(0.005, 0.01), bubble_m, sub=1)
    off = random.randint(0, 60)
    for f in range(-off, FRAMES, 60):
        b_.location = p0; b_.keyframe_insert("location", frame=max(f, 0))
        b_.location = (p0[0] + 0.02, p0[1], TZ + AH - 0.02); b_.keyframe_insert("location", frame=f + 59)

# ---------------- the cartoon axolotl (~23 cm), head points +x, turned toward the camera ----------------
AXP = (KX - 0.02, KY - 0.06, FL + 0.035)
RZ = -0.45
ax = group("Axolotl", AXP, RZ)
K = 0.16
def P(x, y, z):
    return (AXP[0] + K * x, AXP[1] + K * y, AXP[2] + K * z)
body_m = mat("AxBody", (1.0, 0.66, 0.74), 0.45)
belly_m = mat("AxBelly", (1.0, 0.8, 0.84), 0.5)
gill_m = mat("AxGill", (0.92, 0.18, 0.45), 0.4, emit=(0.9, 0.15, 0.4), emit_strength=0.25)
fin_m = mat("AxFin", (1.0, 0.78, 0.84), 0.45)
ap = []
ap.append(sphere("AxTorso", P(0, 0, 0), K * 0.17, body_m, scale=(2.3, 1.0, 0.8), sub=3))
ap.append(sphere("AxHead", P(0.46, 0, 0.03), K * 0.19, body_m, scale=(1.0, 1.25, 0.78), sub=3))
ap.append(sphere("AxTailBase", P(-0.48, 0, 0.02), K * 0.11, body_m, scale=(1.6, 0.8, 0.9), sub=2))
tail = sphere("AxTail", P(-0.72, 0, 0.03), K * 0.22, fin_m, scale=(1.5, 0.14, 0.62), sub=3)
ap.append(tail)
ap.append(sphere("AxFinTop", P(-0.1, 0, 0.13), K * 0.2, fin_m, scale=(2.0, 0.1, 0.35), sub=2))
for sy in (-1, 1):
    ap.append(sphere("AxEyeW", P(0.56, sy * 0.15, 0.13), K * 0.05, eyew, sub=2))
    ap.append(sphere("AxEyeB", P(0.585, sy * 0.165, 0.14), K * 0.032, eyeb, sub=2))
    for k, (dz, ln) in enumerate([(0.1, 0.24), (0.02, 0.27), (-0.06, 0.22)]):
        base = P(0.38, sy * 0.2, dz + 0.05)
        mid = P(0.32, sy * (0.2 + ln * 0.55), dz + 0.1 + k * 0.03)
        tip = P(0.24, sy * (0.2 + ln), dz + 0.16 + k * 0.05)
        ap.append(tube("AxGillS", [base, mid, tip], [K * 0.03, K * 0.026, K * 0.018], gill_m))
        for t_ in (0.35, 0.65, 0.95):
            q_ = Vector(base).lerp(Vector(tip), t_)
            ap.append(sphere("AxGillF", tuple(q_), K * 0.045, gill_m, scale=(0.6, 1.0, 1.2), sub=1))
ap.append(tube("AxSmile", [P(0.6, -0.17, -0.0), P(0.64, -0.08, -0.05), P(0.65, 0, -0.06), P(0.64, 0.08, -0.05), P(0.6, 0.17, 0.0)],
               [K * 0.012] * 5, eyeb))
ap.append(sphere("AxBellyS", P(0.05, 0, -0.08), K * 0.15, belly_m, scale=(2.0, 0.9, 0.5), sub=2))
def make_leg(name, hip, sy, front, material, glow=False):
    g = group(name, hip)
    hx, hy, hz = hip
    d = 1 if front else -1
    knee = (hx + K * 0.05 * d, hy + sy * K * 0.2, hz - K * 0.04)
    foot = (hx + K * 0.1 * d, hy + sy * K * 0.24, hz - K * 0.14)
    parts = [tube(name + "T", [hip, knee, foot], [K * 0.055, K * 0.05, K * 0.045], material)]
    for t in range(4):
        a = (t - 1.5) * 0.45
        parts.append(sphere(name + "Toe", (foot[0] + K * 0.08 * math.cos(a) * d, foot[1] + sy * K * 0.05 + K * 0.06 * math.sin(a) * d, foot[2] - K * 0.01),
                            K * 0.03, material, scale=(1.4, 1, 0.7), sub=1))
    attach(parts, g)
    return g
legs = {}
for sy in (-1, 1):
    for front in (True, False):
        hip = P(0.28 if front else -0.3, sy * 0.13, -0.05)
        legs[(sy, front)] = make_leg(f"AxLeg{sy}{front}", hip, sy, front, body_m)
LEG = legs[(-1, True)]                    # the front leg on the camera side
HIP_LOCAL = P(0.28, -0.13, -0.05)
gleg = make_leg("GlowLeg", HIP_LOCAL, -1, True, bud_m)
cap = sphere("SkinCap", P(0.29, -0.2, -0.06), K * 0.07, mat("CapM", (1.0, 0.55, 0.65), 0.4, emit=(1.0, 0.5, 0.6), emit_strength=0.4), sub=2)
bud = sphere("Blastema", P(0.3, -0.24, -0.08), K * 0.08, bud_m, sub=3)
heart = group("Heart", P(0.22, -0.27, 0.02))
hm = glow_mat("HeartM", (1.0, 0.1, 0.2), 4.0)
hp = [sphere("HeartL", P(0.18, -0.27, 0.05), K * 0.08, hm, sub=2), sphere("HeartR", P(0.26, -0.27, 0.05), K * 0.08, hm, sub=2),
      cyl("HeartTip", P(0.22, -0.27, -0.03), K * 0.115, K * 0.13, hm, rot=(math.radians(180), 0, 0), r2=0.001, verts=12)]
attach(hp, heart)
spine = tube("Spine", [P(-0.7, 0, 0.12), P(-0.35, 0, 0.16), P(0.0, 0, 0.17), P(0.35, 0, 0.18), P(0.52, 0, 0.16)],
             [K * 0.035] * 5, glow_mat("SpineM", (0.25, 0.65, 1.0), 4.0))
attach(ap + list(legs.values()) + [gleg, cap, bud, heart, spine], ax)
bpy.context.view_layer.update()
def wpos(o):
    bpy.context.view_layer.update()
    return tuple(o.matrix_world.translation)
HIPW = wpos(LEG)
AXC = (AXP[0], AXP[1], AXP[2] + 0.01)
# idle: gentle bob + tail sway
for f in range(0, FRAMES + 20, 20):
    ax.location = AXP; ax.keyframe_insert("location", frame=f)
    ax.location = (AXP[0], AXP[1], AXP[2] + 0.006); ax.keyframe_insert("location", frame=f + 10)
    tail.rotation_euler = (0, 0, 0.18); tail.keyframe_insert("rotation_euler", frame=f)
    tail.rotation_euler = (0, 0, -0.18); tail.keyframe_insert("rotation_euler", frame=f + 10)

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
    return min(size, 0.8 * D * 2 * TANV * 9 / 16 / (max(len(body), 7) * 0.66))

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
MX, MY = 1.75, 0.55
you, Y = person("You", (MX, MY, 0.0), 1.0, mat("ShirtY", (0.2, 0.55, 0.95), 0.7), mat("PantsY", (0.2, 0.25, 0.4), 0.8),
                skin_m, mat("HairY", (0.28, 0.16, 0.07), 0.8))
KIDX = MX + 1.25
kid, KD = person("Kid", (KIDX, MY - 0.1, 0.0), 0.62, mat("ShirtK", (1.0, 0.75, 0.15), 0.7), mat("PantsK", (0.85, 0.3, 0.3), 0.8),
                 skin_m, mat("HairK", (0.12, 0.08, 0.05), 0.8))
hide_until(kid, S[12] - 2)
gone_at(kid, S[13] + 2)
ARM = Y["arms"][1]                        # screen-right arm (+x)
SHW = Y["P"](0.32, 0, 1.36)

# =====================================================================================
# per-line views: (camera, subject) — hard cut on every line + drift
# =====================================================================================
TK = (KX, KY - 0.05, FL + 0.08)
V = {}
V[0] = ((1.6, -3.3, 1.9), (KX + 0.9, TY, 0.9))
V[1] = ((AXC[0] + 0.12, AXC[1] - 0.62, AXC[2] + 0.1), AXC)
V[2] = ((AXC[0] - 0.25, AXC[1] - 0.75, AXC[2] + 0.1), AXC)
V[3] = ((HIPW[0] + 0.05, HIPW[1] - 0.42, HIPW[2]), HIPW)
V[4] = ((1.0, TY - 1.2, 1.2), (0.62, TY - 0.05, TZ + 0.08))
V[5] = ((HIPW[0] - 0.08, HIPW[1] - 0.36, HIPW[2]), HIPW)
V[6] = ((HIPW[0] + 0.08, HIPW[1] - 0.34, HIPW[2]), HIPW)
V[7] = ((HIPW[0] - 0.02, HIPW[1] - 0.36, HIPW[2]), HIPW)
V[8] = ((AXC[0] + 0.1, AXC[1] - 0.6, AXC[2]), AXC)
V[9] = ((AXC[0] - 0.1, AXC[1] - 0.58, AXC[2]), AXC)
V[10] = ((MX + 0.6, -3.6, 1.8), (MX + 0.3, MY, 0.9))
V[11] = ((MX - 0.3, MY - 2.8, 1.4), (MX, MY, 1.0))
V[12] = ((KIDX + 0.2, MY - 2.7, 1.2), (KIDX - 0.3, MY, 0.7))
V[13] = ((MX + 0.9, MY - 3.0, 1.5), (MX + 0.2, MY, 1.0))
V[14] = ((MX + 0.4, MY - 3.4, 1.6), (MX, MY, 1.0))
V[15] = ((MX + 0.8, MY - 2.4, 1.6), (MX + 0.2, MY, 1.2))
V[16] = ((MX + 0.5, MY - 3.0, 1.6), (MX + 0.15, MY, 1.0))
V[17] = ((0.6, -4.6, 2.4), (0.9, TY, 0.75))
DR = {0: (-0.6, 1.3, -0.3), 1: (-0.08, 0.1, 0), 2: (0.1, 0.12, 0), 3: (-0.06, 0.08, 0), 4: (0.25, 0.2, 0), 5: (0.05, 0.06, 0),
      6: (-0.05, 0.06, 0), 7: (0.04, 0.05, 0), 8: (-0.1, 0.1, 0), 9: (0.1, 0.1, 0), 10: (-0.5, 0.6, 0), 11: (0.3, 0.5, 0),
      12: (-0.3, 0.4, 0), 13: (-0.3, 0.5, 0), 14: (0.3, 0.6, 0), 15: (-0.3, 0.4, 0), 16: (0.3, 0.5, 0), 17: (-0.6, 0.9, -0.2)}
def LB(i, name, body, v, m_, size=None, u=0.0, f_in=None, f_out=None, Dk=0.55):
    cl = Vector(CL(V[i])); D = (Vector(V[i][1]) - cl).length * Dk
    s_ = fit(body, D, size if size else 1.0)
    return label(name, body, V[i], D, v, s_, m_, (S[i] + 3) if f_in is None else f_in,
                 (S[i + 1] if i + 1 < len(S) else FRAMES + 5) if f_out is None else f_out, u)

# line 0: hook — "?" over the tank
LB(0, "L0", "AXOLOTL?", 0.25, pink_lab, f_in=8)
# line 1: ruler 23 cm
rul_m = mat("RulerM", (1.0, 0.9, 0.3), 0.5)
rul = group("Ruler", (AXP[0], AY0 - 0.04, TZ + 0.01))
rp = [box("RulerB", (AXP[0], AY0 - 0.04, TZ + 0.006), (0.25, 0.05, 0.012), rul_m)]
for i in range(24):
    rp.append(box("Tick", (AXP[0] - 0.115 + i * 0.01, AY0 - 0.06, TZ + 0.013), (0.0015, 0.008, 0.004 if i % 5 else 0.008), eyeb))
attach(rp, rul)
pop(rul, S[1], 5, S[3])
LB(1, "L1", "23 cm", 0.22, lab_m)
# line 2: smile + Mexico pin
pin = group("Pin", (AXP[0] + 0.25, AY0 - 0.02, FL + 0.18))
pinp = [sphere("PinHead", (AXP[0] + 0.25, AY0 - 0.02, FL + 0.2), 0.03, red_lab, sub=2),
        cyl("PinTip", (AXP[0] + 0.25, AY0 - 0.02, FL + 0.16), 0.022, 0.05, red_lab, rot=(math.radians(180), 0, 0), r2=0.001)]
attach(pinp, pin)
pop(pin, S[2] + 2, 5, S[3])
LB(2, "L2", "MEXICO", 0.25, green_lab)
# line 3: the leg poofs away (cartoon, no injury detail)
LOSE = S[3] + 10
keyscale(LEG, [(0, 1.0), (LOSE - 3, 1.0), (LOSE, 0.001)])
burst(HIPW, LOSE, 10, 0.03, 0.004, LOSE + 10, material=pspark_m, yoff=-0.02)
LB(3, "L3", "LEG LOST?", 0.25, red_lab)
# glowing new leg grows (line 7), the real leg returns (line 8)
keyscale(gleg, [(0, 0.001), (S[7], 0.001), (S[7] + 20, 0.6), (S[8], 1.0), (S[8] + 2, 1.0), (S[8] + 4, 0.001)])
keyscale(LEG, [(S[8] + 1, 0.001), (S[8] + 3, 1.0)])
burst(HIPW, S[8] + 3, 12, 0.035, 0.004, S[8] + 16, yoff=-0.02)
# line 5: skin seals the stump
keyscale(cap, [(0, 0.001), (S[5] + 3, 0.001), (S[5] + 8, 1.15), (S[5] + 10, 1.0), (S[7] + 6, 1.0), (S[7] + 10, 0.001)])
LB(5, "L5", "1 DAY", 0.25, lab_m)
# line 6: blastema bud
keyscale(bud, [(0, 0.001), (S[6] + 2, 0.001), (S[6] + 12, 0.9), (S[6] + 26, 1.25), (S[7] + 4, 1.25), (S[7] + 20, 0.5), (S[8], 0.001)])
LB(6, "L6", "BLASTEMA", 0.25, pink_lab)
LB(7, "L7", "REGROWING", 0.25, pink_lab)
LB(8, "L8", "NO SCAR!", 0.25, green_lab)
# line 9: heart + spinal cord glow
keyscale(heart, [(0, 0.001), (S[9] + 2, 0.001), (S[9] + 6, 1.3), (S[9] + 10, 1.0), (S[9] + 14, 1.25), (S[9] + 18, 1.0), (S[9] + 22, 1.25), (S[10] - 2, 1.0), (S[10], 0.001)])
keyscale(spine, [(0, 0.001), (S[9] + 12, 0.001), (S[9] + 18, 1.0), (S[10] - 1, 1.0), (S[10] + 1, 0.001)])
LB(9, "L9a", "HEART", 0.21, red_lab, u=-0.08)
LB(9, "L9b", "SPINAL CORD", 0.31, blue_lab, f_in=S[9] + 14)

# line 4: big cut-away leg model on the table: bone, muscle, nerves
LMX, LMY, LMZ = 0.62, TY - 0.05, TZ + 0.12
lm = group("LegModel", (LMX, LMY, LMZ))
bone = cyl("Bone", (LMX, LMY, LMZ), 0.035, 0.5, mat("BoneM", (0.97, 0.95, 0.88), 0.5), rot=(0, math.radians(90), 0))
knobs = [sphere("BoneKnob", (LMX + sx * 0.26, LMY, LMZ), 0.055, mat("BoneK", (0.97, 0.95, 0.88), 0.5), sub=2) for sx in (-1, 1)]
muscle = cyl("Muscle", (LMX - 0.04, LMY, LMZ), 0.085, 0.34, mat("MuscleM", (0.88, 0.22, 0.25), 0.55), rot=(0, math.radians(90), 0), verts=32)
nerves = [tube("Nerve", [(LMX - 0.21, LMY - 0.08 * math.cos(a), LMZ + 0.08 * math.sin(a)), (LMX + 0.13, LMY - 0.088 * math.cos(a), LMZ + 0.088 * math.sin(a))],
               [0.012, 0.012], glow_mat("NerveM", (1.0, 0.85, 0.1), 3.0)) for a in (-0.6, 0.0, 0.6, 1.2)]
pop(bone, S[4] + 2, 5, S[5]); [pop(k_, S[4] + 2, 5, S[5]) for k_ in knobs]
pop(muscle, S[4] + 10, 5, S[5])
for n_ in nerves:
    pop(n_, S[4] + 18, 5, S[5])
LB(4, "L4a", "BONE", 0.2, white_lab, u=-0.1, f_in=S[4] + 3, Dk=0.5)
LB(4, "L4b", "MUSCLE", 0.28, red_lab, u=0.1, f_in=S[4] + 11, Dk=0.5)
LB(4, "L4c", "NERVES", 0.36, lab_m, u=0.0, f_in=S[4] + 19, Dk=0.5)

# ---------------- humans ----------------
LB(10, "L10", "YOU", 0.25, lab_m)
# line 11: liver regrows (glowing, on the torso front)
liver = sphere("Liver", Y["P"](-0.07, -0.25, 1.12), 0.16, glow_mat("LiverM", (0.85, 0.25, 0.2), 2.5), scale=(1.5, 0.45, 0.8), sub=3)
keyscale(liver, [(0, 0.001), (S[11] + 1, 0.001), (S[11] + 5, (0.5, 0.5, 0.5)), (S[11] + 10, (0.5, 0.5, 0.5)), (S[11] + 30, (1.0, 1.0, 1.0)), (S[12] - 2, 1.0), (S[12], 0.001)])
ghostl = sphere("LiverGhost", Y["P"](-0.07, -0.26, 1.12), 0.16, mat("LivG", (1, 1, 1), 0.5, emit=(1, 1, 1), emit_strength=0.3), scale=(1.5, 0.4, 0.8), sub=3)
ghostl.data.materials[0].node_tree.nodes["Principled BSDF"].inputs["Alpha"].default_value = 0.25
keyscale(ghostl, [(0, 0.001), (S[11] + 1, 0.001), (S[11] + 4, (1.5, 0.4, 0.8)), (S[12] - 2, (1.5, 0.4, 0.8)), (S[12], 0.001)])
LB(11, "L11", "LIVER", 0.25, red_lab)
# line 12: kid's fingertip
KARM = KD["arms"][1]
keyrot(KARM, [(S[12], (0, 0, 0)), (S[12] + 6, (0, -2.6, 0))])
bpy.context.view_layer.update()
sc.frame_set(S[12] + 8); bpy.context.view_layer.update()
khand = [o for o in KARM.children if "Hand" in o.name][0]
KHW = tuple(khand.matrix_world.translation)
sc.frame_set(0)
tipg = sphere("FingerGlow", (KHW[0] + 0.02, KHW[1] - 0.05, KHW[2] + 0.06), 0.045, glow_mat("TipM", (1.0, 0.95, 0.5), 5.0), sub=2)
keyscale(tipg, [(0, 0.001), (S[12] + 8, 0.001), (S[12] + 12, 1.3), (S[12] + 16, 0.9), (S[12] + 20, 1.2), (S[13], 0.001)])
LB(12, "L12", "FINGERTIP", 0.25, lab_m)
# line 13: arm — no regrowth: arm gone (cartoon poof), ghost outline + red X
ARMGONE = S[13] + 8
keyscale(ARM, [(0, 1.0), (ARMGONE - 3, 1.0), (ARMGONE, 0.001)])
burst(Y["P"](0.38, -0.2, 1.05), ARMGONE, 12, 0.25, 0.03, ARMGONE + 10, yoff=-0.05)
ghost_m = mat("GhostArm", (0.85, 0.9, 1.0), 0.5, emit=(0.8, 0.9, 1.0), emit_strength=0.4)
ghost_m.node_tree.nodes["Principled BSDF"].inputs["Alpha"].default_value = 0.3
gha = tube("GhostArmT", [Y["P"](0.3, -0.02, 1.35), Y["P"](0.38, -0.05, 1.05), Y["P"](0.38, -0.08, 0.8)], [0.075] * 3, ghost_m)
keyscale(gha, [(0, 0.001), (ARMGONE, 0.001), (ARMGONE + 2, 1.0), (S[14] + 2, 1.0), (S[14] + 4, 0.001)])
xg = group("RedX", Y["P"](0.4, -0.3, 1.08))
xp = [box("X1", Y["P"](0.4, -0.3, 1.08), (0.07, 0.03, 0.55), red_lab, rot=(0, math.radians(45), 0)),
      box("X2", Y["P"](0.4, -0.3, 1.08), (0.07, 0.03, 0.55), red_lab, rot=(0, math.radians(-45), 0))]
attach(xp, xg)
pop(xg, ARMGONE + 4, 4, S[14] + 2)
scar = tube("Scar", [Y["P"](0.27, -0.2, 1.42), Y["P"](0.33, -0.2, 1.33), Y["P"](0.37, -0.19, 1.26)], [0.012] * 3, mat("ScarM", (0.75, 0.42, 0.4), 0.6))
keyscale(scar, [(0, 0.001), (ARMGONE + 6, 0.001), (ARMGONE + 8, 1.0), (S[15], 1.0), (S[15] + 2, 0.001)])
LB(13, "L13a", "WHOLE ARM?", 0.18, white_lab, f_out=ARMGONE + 6)
LB(13, "L13b", "JUST A SCAR", 0.18, red_lab, f_in=ARMGONE + 7)
keyrot(Y["smile"], [(0, (0, 0, 0))])
# line 14: axolotl power — pink gills sprout from the head + glow
gills_h = []
for sx in (-1, 1):
    for k, dz in enumerate((0.1, 0.0, -0.1)):
        b0 = Y["P"](sx * 0.2, 0.02, 1.72 + dz)
        tp = Y["P"](sx * (0.45 + 0.04 * (1 - abs(k - 1))), 0.06, 1.85 + dz * 1.6)
        g_ = tube("YouGill", [b0, tuple(Vector(b0).lerp(Vector(tp), 0.5) + Vector((0, 0, 0.03))), tp], [0.03, 0.026, 0.02], gill_m)
        gills_h.append(g_)
        for t_ in (0.4, 0.7, 1.0):
            q_ = Vector(b0).lerp(Vector(tp), t_)
            gills_h.append(sphere("YouGillF", tuple(q_), 0.04, gill_m, scale=(0.7, 0.7, 1.2), sub=1))
for g_ in gills_h:
    hide_until(g_, S[14] + 6)
burst(Y["P"](0, -0.3, 1.2), S[14] + 4, 14, 0.7, 0.04, S[14] + 18, material=pspark_m, yoff=-0.1)
bpy.ops.object.light_add(type='POINT', location=Y["P"](0, -0.8, 1.4))
pl = bpy.context.object; pl.data.color = (1.0, 0.45, 0.75); pl.data.shadow_soft_size = 0.3
pl.data.energy = 0; pl.data.keyframe_insert("energy", frame=S[14] + 2)
pl.data.energy = 120; pl.data.keyframe_insert("energy", frame=S[14] + 6)
pl.data.energy = 40; pl.data.keyframe_insert("energy", frame=S[15] + 4)
pl.data.energy = 120; pl.data.keyframe_insert("energy", frame=S[16] + 4)
pl.data.energy = 0; pl.data.keyframe_insert("energy", frame=S[17] + 4)
LB(14, "L14", "AXOLOTL POWER!", 0.25, pink_lab)
# line 15: glowing bud at the shoulder
sbud = sphere("ShoulderBud", Y["P"](0.38, -0.02, 1.3), 0.11, bud_m, sub=3)
keyscale(sbud, [(0, 0.001), (S[15] + 2, 0.001), (S[15] + 10, 1.0), (S[15] + 22, 1.35), (S[16] + 2, 1.35), (S[16] + 14, 0.001)])
LB(15, "L15", "BUD", 0.25, pink_lab)
# line 16: new arm grows out and waves
glow_arm = tube("GlowArm", [Y["P"](0.3, -0.02, 1.35), Y["P"](0.38, -0.05, 1.05), Y["P"](0.38, -0.08, 0.8)], [0.078] * 3, bud_m)
ga_g = group("GlowArmG", Y["P"](0.3, 0, 1.33)); attach([glow_arm], ga_g)
keyscale(ga_g, [(0, 0.001), (S[16], 0.001), (S[16] + 14, 1.0), (S[16] + 17, 1.0), (S[16] + 19, 0.001)])
keyscale(ARM, [(S[16] + 16, 0.001), (S[16] + 18, 1.0)])
burst(Y["P"](0.4, -0.2, 1.05), S[16] + 17, 14, 0.35, 0.035, S[16] + 30, yoff=-0.05)
keyrot(ARM, [(S[16] + 18, (0, 0, 0)), (S[16] + 23, (0, -2.5, 0)), (S[16] + 27, (0, -2.0, 0)), (S[16] + 31, (0, -2.5, 0)), (S[17] + 2, (0, -2.0, 0)),
             (S[17] + 7, (0, -2.5, 0)), (S[17] + 12, (0, -2.0, 0)), (S[17] + 17, (0, -2.5, 0)), (S[17] + 22, (0, -2.0, 0))])
keyrot(Y["arms"][0], [(S[17], (0, 0, 0)), (S[17] + 5, (0, 2.5, 0)), (S[17] + 10, (0, 2.0, 0)), (S[17] + 15, (0, 2.5, 0)), (S[17] + 20, (0, 2.0, 0))])
LB(16, "L16", "NEW ARM!", 0.25, green_lab)
# line 17: question
q = text("Q", "?", SP(V[17], 3.0, 0.3, 0.0), 0.55, lab_m, extrude=0.05)
pop(q, S[17] + 4, 6)
keyrot(q, [(S[17] + 4, (math.radians(90), 0, 0)), (FRAMES, (math.radians(90), 0, math.radians(360)))])
# axolotl hook: whole body wiggles through the garden wide shot already; gentle head turns at the end
keyrot(ax, [(0, (0, 0, RZ)), (S[17], (0, 0, RZ)), (S[17] + 10, (0, 0, RZ - 0.3))])

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
