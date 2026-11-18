# Day 24 — What if you lived like the immortal jellyfish?  Build: python3 episodes/024-immortal-jellyfish/scene.py
# Reference style: base (helpers, lawn/soil, house, garden) copied from episodes/003-lift-million-ref/scene.py (via 019)
import bpy, math, random, os, json
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
random.seed(24)
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
# Day 24 — What if you lived like the immortal jellyfish?
# Facts used (Smithsonian Ocean, AMNH, Natural History Museum London, Piraino et al. 1996, Kubota 2011 reports):
#   Turritopsis dohrnii: bell up to ~4.5 mm across (smaller than a pinky nail), red stomach. When stressed, injured,
#   sick or old, the medusa sinks to the sea floor, shrinks into a cyst ("blob") and transforms back into a polyp — its
#   earliest attached life stage. The polyp colony buds new, genetically identical medusae. It can repeat this, so it is
#   called "biologically immortal"; in one Japanese lab (Shin Kubota) a jellyfish reportedly rejuvenated 10 times in
#   2 years. In the wild most are eaten (fish etc.) or die of disease before they can revert.
#   The human part is a playful "what if" — nobody knows what would happen to memories.
# =====================================================================================
def jel_material(name, a=0.55, em=0.9):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (0.8, 0.94, 1.0, 1); b.inputs["Roughness"].default_value = 0.2
    b.inputs["Alpha"].default_value = a
    b.inputs["Emission Color"].default_value = (0.55, 0.88, 1.0, 1); b.inputs["Emission Strength"].default_value = em
    return m, b
jel_m, _ = jel_material("JelShared")
main_m, MB = jel_material("JelMain")
core_red = glow_mat("CoreRed", (1.0, 0.18, 0.12), 2.5)
tent_w = mat("TentW", (0.95, 0.97, 1.0), 0.3, emit=(0.8, 0.95, 1.0), emit_strength=1.0)
blob_m = glow_mat("BlobM", (1.0, 0.5, 0.2), 2.2)
polyp_m = mat("Polyp", (1.0, 0.75, 0.8), 0.4, emit=(1.0, 0.6, 0.7), emit_strength=0.7)
cocoon_m = mat("Cocoon", (0.98, 0.92, 0.75), 0.5, emit=(1.0, 0.8, 0.4), emit_strength=0.7)
fish_m = mat("Fish", (1.0, 0.5, 0.1), 0.45)
fin_m = mat("Fin", (0.95, 0.3, 0.05), 0.5)
cake_m = mat("Cake", (1.0, 0.7, 0.8), 0.6)
icing_m = mat("Icing", (1.0, 1.0, 0.97), 0.5)
flame_m = glow_mat("Flame", (1.0, 0.7, 0.2), 6.0)
grey_hair = mat("GreyHair", (0.85, 0.85, 0.85), 0.8)
ring_m = glow_mat("RingG", (1.0, 0.8, 0.2), 3.0)
cyc_m = glow_mat("CycM", (0.35, 0.85, 1.0), 2.5)

def make_jelly(name, c, s, bell_m, eyes=True):
    c = Vector(c)
    g = group(name, tuple(c))
    P = [sphere(name + "Bell", tuple(c + Vector((0, 0, 0.12 * s))), 0.55 * s, bell_m, scale=(1, 1, 0.7), sub=3)]
    bpy.ops.mesh.primitive_torus_add(major_radius=0.5 * s, minor_radius=0.07 * s, location=tuple(c + Vector((0, 0, -0.1 * s))))
    rim = bpy.context.object; rim.data.materials.append(bell_m); P.append(rim)
    P.append(sphere(name + "Core", tuple(c + Vector((0, 0, 0.05 * s))), 0.17 * s, core_red, sub=2))
    for k in range(4):
        a = k * math.pi / 2 + math.pi / 4
        P.append(sphere(name + "Lobe", tuple(c + Vector((0.17 * s * math.cos(a), 0.17 * s * math.sin(a), 0.0))), 0.09 * s, core_red, sub=1))
    if eyes:
        for sx in (-1, 1):
            P.append(sphere(name + "EW", tuple(c + Vector((sx * 0.17 * s, -0.47 * s, 0.25 * s))), 0.1 * s, eyew, scale=(1, 0.6, 1.2), sub=2))
            P.append(sphere(name + "EB", tuple(c + Vector((sx * 0.17 * s, -0.53 * s, 0.25 * s))), 0.05 * s, eyeb, sub=1))
    for k in range(16):
        a = k / 16 * 6.283
        st = c + Vector((0.48 * s * math.cos(a), 0.48 * s * math.sin(a), -0.12 * s))
        pts = [tuple(st + Vector((0.04 * s * math.sin(n * 1.4 + k), 0.04 * s * math.cos(n * 1.1 + k), -n * 0.16 * s))) for n in range(6)]
        P.append(tube(name + "T", pts, [0.025 * s] * 6, tent_w))
    attach(P, g)
    return g

# ---------------- the pool ----------------
PZF, PZW = -1.75, -0.15
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

# =================== lines 0-5: the jellyfish in the pool ===================
JC = Vector((1.0, 0.6, -0.7))
JF = Vector((1.0, 0.6, -1.25))
jel = make_jelly("Jelly", tuple(JC), 1.0, main_m)
for f in range(0, S[4], 12):
    k_ = f // 12
    jel.location = tuple(JC + Vector((0, 0, 0.07 * math.sin(k_ * 1.1)))); jel.keyframe_insert("location", frame=f)
jel.location = tuple(JC); jel.keyframe_insert("location", frame=S[4])
jel.location = tuple(JF); jel.keyframe_insert("location", frame=E(4) - 2)
for f in range(0, S[5], 12):
    k_ = f // 12
    sq = 0.05 * math.sin(k_ * 1.1 + 1.5)
    jel.scale = (1 + sq, 1 + sq, 1 - sq); jel.keyframe_insert("scale", frame=f)
keyscale(jel, [(S[5], 1.0), (W(5, 0.15), 1.0), (W(5, 0.7), 0.12), (W(5, 0.8), 0.001)])
# line 0 sparkles, line 2 golden glow
burst(tuple(JC + Vector((0, -0.6, 0.1))), S[0] + 8, n=14, r=0.9, size=0.04, material=spark_m, f_out=S[1])
for f, a in [(0, 0.9), (S[2] - 1, 0.9), (S[2] + 3, 4.0), (W(2, 0.6), 2.5), (E(2), 0.9)]:
    MB.inputs["Emission Strength"].default_value = a; MB.inputs["Emission Strength"].keyframe_insert("default_value", frame=f)
for f, c in [(0, (0.55, 0.88, 1.0, 1)), (S[2] - 1, (0.55, 0.88, 1.0, 1)), (S[2] + 2, (1.0, 0.8, 0.25, 1)), (E(2) - 2, (1.0, 0.8, 0.25, 1)),
             (S[3] + 1, (0.55, 0.88, 1.0, 1)), (W(3, 0.6), (0.35, 0.35, 0.38, 1))]:
    MB.inputs["Emission Color"].default_value = c; MB.inputs["Emission Color"].keyframe_insert("default_value", frame=f)
for f, c in [(0, (0.8, 0.94, 1.0, 1)), (S[3], (0.8, 0.94, 1.0, 1)), (W(3, 0.6), (0.5, 0.5, 0.52, 1))]:
    MB.inputs["Base Color"].default_value = c; MB.inputs["Base Color"].keyframe_insert("default_value", frame=f)
burst(tuple(JC + Vector((0, -0.6, 0.1))), S[2] + 2, n=16, r=1.0, size=0.06, material=spark_m, f_out=E(2))
for k in range(2):
    bpy.ops.mesh.primitive_torus_add(major_radius=0.95 + 0.25 * k, minor_radius=0.04, location=tuple(JC + Vector((0, 0, 0.05))))
    rg = bpy.context.object; rg.data.materials.append(ring_m)
    vis(rg, [(S[2] + 2 + 3 * k, S[3])])
    keyrot(rg, [(S[2], (math.radians(70), 0, 0)), (E(2), (math.radians(70), math.radians(360 * (1 + k)), 0))])
# line 3: bandage + grey (old / hurt)
bd = group("Band", tuple(JC + Vector((0.2, -0.5, 0.35))))
bdp = [boxc("BandA", tuple(JC + Vector((0.2, -0.5, 0.35))), (0.5, 0.06, 0.14), white_lab),
       boxc("BandB", tuple(JC + Vector((0.2, -0.5, 0.35))), (0.5, 0.06, 0.14), white_lab)]
bdp[0].rotation_euler = (0, math.radians(40), 0); bdp[1].rotation_euler = (0, math.radians(-40), 0)
attach(bdp, bd); parent_to(bd, jel)
vis(bd, [(W(3, 0.4), S[5])])
# line 4: down arrow
arw = group("Arrow", (2.0, 0.4, -0.5))
ap = [cyl("ArS", (2.0, 0.4, -0.45), 0.07, 0.7, lab_m, verts=12), cyl("ArH", (2.0, 0.4, -0.95), 0.2, 0.3, lab_m, rot=(math.radians(180), 0, 0), r2=0.0, verts=12)]
attach(ap, arw)
pop(arw, S[4] + 2, 4, S[5])
key_loc(arw, [(S[4] + 2, (2.0, 0.4, -0.3)), (E(4), (2.0, 0.4, -0.75))])
# line 5: the blob
BLOB = Vector((1.0, 0.6, -1.55))
blob = sphere("Blob", tuple(BLOB), 0.26, blob_m, sub=3)
keyscale(blob, [(0, 0.001), (W(5, 0.5) - 1, 0.001), (W(5, 0.7), 1.3), (W(5, 0.8), 1.0), (S[6], 1.0), (W(6, 0.5), 0.75), (S[8], 0.75), (S[8] + 1, 0.001)])
burst(tuple(BLOB + Vector((0, -0.3, 0))), W(5, 0.7), n=12, r=0.55, size=0.04, material=spark_m, f_out=S[6])

# =================== lines 6-7: polyp regrows and buds clones ===================
PB = Vector((1.0, 0.6, PZF))
pol = group("Polyp", tuple(PB))
pp = [tube("Stalk", [tuple(PB), tuple(PB + Vector((0.05, 0, 0.5))), tuple(PB + Vector((-0.04, 0, 0.95)))], [0.1, 0.08, 0.08], polyp_m),
      sphere("PHead", tuple(PB + Vector((-0.04, 0, 1.02))), 0.17, polyp_m, sub=2)]
for k in range(8):
    a = k / 8 * 6.283
    h0 = PB + Vector((-0.04, 0, 1.08))
    pp.append(tube("PTen", [tuple(h0), tuple(h0 + Vector((0.3 * math.cos(a), 0.3 * math.sin(a), 0.22)))], [0.035, 0.02], tent_w))
attach(pp, pol)
keyscale(pol, [(0, 0.001), (S[6] - 1, 0.001), (S[6], (1, 1, 0.05)), (W(6, 0.55), (1.1, 1.1, 1.15)), (W(6, 0.7), (1, 1, 1)), (S[8] - 1, 1.0), (S[8], 0.001)])
burst(tuple(PB + Vector((0, -0.3, 1.0))), W(6, 0.55), n=12, r=0.6, size=0.04, material=spark_m, f_out=S[7])
BR_ = []
for sx in (-1, 1):
    b0 = PB + Vector((0.0, 0, 0.35)); b1 = b0 + Vector((sx * 0.55, 0, 0.35))
    br = tube("Branch", [tuple(b0), tuple(b0 + Vector((sx * 0.3, 0, 0.1))), tuple(b1)], [0.07, 0.06, 0.05], polyp_m)
    bud = sphere("Bud", tuple(b1 + Vector((0, 0, 0.08))), 0.12, polyp_m, sub=2)
    for o_ in (br, bud):
        vis(o_, [(S[7], S[8])])
    BR_.append(b1)
for k, (st, up) in enumerate([(BR_[0], (-1.1, 0.4, -0.35)), (BR_[1], (0.1 + 2.0, 0.3, -0.45)), (PB + Vector((-0.04, 0, 1.1)), (1.0, 0.5, -0.35)),
                              (BR_[0], (-0.2, 0.2, -0.75)), (BR_[1], (2.4, 0.7, -0.9))]):
    cj = make_jelly(f"Clone{k}", tuple(st + Vector((0, 0, 0.15))), 0.42, jel_m)
    t0 = W(7, 0.12 + 0.13 * k)
    keyscale(cj, [(0, 0.001), (t0 - 1, 0.001), (t0 + 3, 1.2), (t0 + 5, 1.0), (S[8] - 1, 1.0), (S[8], 0.001)])
    key_loc(cj, [(t0, tuple(st + Vector((0, 0, 0.15)))), (E(7), up)])
    burst(tuple(st + Vector((0, -0.2, 0.15))), t0, n=8, r=0.3, size=0.03, material=spark_m, f_out=t0 + 8)

# =================== line 1: fingertip vs the tiny jellyfish (zoom zone) ===================
ZX = 10.5
fz = group("Finger", (ZX, 1.0, 0))
nail_m = mat("Nail", (1.0, 0.75, 0.78), 0.2)
fp_ = [box("FPed", (ZX, 1.0, 0.35), (4.6, 1.4, 0.7), board_m, bevel=0.05),
       tube("Fing", [(ZX - 2.4, 1.0, 1.15), (ZX - 0.5, 1.0, 1.15)], [0.42, 0.42], skin_m),
       sphere("FTip", (ZX - 0.5, 1.0, 1.15), 0.42, skin_m, sub=3),
       box("FNail", (ZX - 0.75, 0.95, 1.53), (0.62, 0.62, 0.1), pink_lab, bevel=0.04)]
attach(fp_, fz)
vis(fz, [(S[1], S[2])])
mini = make_jelly("MiniJ", (ZX + 0.9, 1.0, 1.15), 0.6, jel_m)
vis(mini, [(S[1], S[2])])
key_loc(mini, [(S[1], (ZX + 0.9, 1.0, 1.15)), (E(1), (ZX + 0.9, 1.0, 1.25))])
for sx in (-1, 1):   # size brackets: nail width == jelly width
    for xx in (ZX - 0.75, ZX + 0.9):
        b_ = box("Brk", (xx + sx * 0.33, 0.62, 1.95), (0.05, 0.05, 0.35), lab_m)
        vis(b_, [(W(1, 0.35), S[2])])
for xx in (ZX - 0.75, ZX + 0.9):
    b_ = box("BrkH", (xx, 0.62, 2.12), (0.71, 0.05, 0.05), lab_m)
    vis(b_, [(W(1, 0.35), S[2])])

# =================== line 8: the life-cycle wheel (lawn left) ===================
CY = Vector((-7.0, 1.0, 1.55))
bpy.ops.mesh.primitive_torus_add(major_radius=1.25, minor_radius=0.05, location=tuple(CY), rotation=(math.radians(90), 0, 0))
whl = bpy.context.object; whl.data.materials.append(cyc_m)
vis(whl, [(S[8], S[9])])
icons = []
icons.append(make_jelly("CycA", tuple(CY + Vector((0, -0.1, 1.25))), 0.42, jel_m))
icons.append(sphere("CycB", tuple(CY + Vector((1.25, -0.1, 0))), 0.2, blob_m, sub=2))
pg = group("CycC", tuple(CY + Vector((0, -0.1, -1.25))))
attach([tube("CycCS", [tuple(CY + Vector((0, -0.1, -1.45))), tuple(CY + Vector((0, -0.1, -1.0)))], [0.06, 0.05], polyp_m),
        sphere("CycCH", tuple(CY + Vector((0, -0.1, -0.97))), 0.1, polyp_m, sub=2)], pg)
icons.append(pg)
icons.append(make_jelly("CycD", tuple(CY + Vector((-1.25, -0.1, 0))), 0.3, jel_m))
for k, ic in enumerate(icons):
    keyscale(ic, [(0, 0.001), (S[8] + 2 * k - 1, 0.001), (S[8] + 2 * k + 3, 1.2), (S[8] + 2 * k + 5, 1.0), (S[9] - 1, 1.0), (S[9], 0.001)])
orb = sphere("Orb", tuple(CY), 0.14, ring_m, sub=2)
vis(orb, [(S[8], S[9])])
n_ = E(8) - S[8]
for j in range(n_ + 1):
    a = math.pi / 2 - j / n_ * 2 * 6.283
    orb.location = tuple(CY + Vector((1.25 * math.cos(a), -0.15, 1.25 * math.sin(a)))); orb.keyframe_insert("location", frame=S[8] + j)
for k in range(4):   # arrow heads around the wheel (clockwise)
    a = math.pi / 4 + k * math.pi / 2
    ah = cyl("CycArr", tuple(CY + Vector((1.25 * math.cos(a), -0.1, 1.25 * math.sin(a)))), 0.13, 0.26, cyc_m, r2=0.0, verts=10)
    ah.rotation_euler = (0, a + math.pi, 0)
    vis(ah, [(S[8] + 6, S[9])])

# =================== line 9: the lab tank, 10 restarts ===================
lab = group("Lab", (ZX, 1.0, 0))
lp_ = [box("LTable", (ZX, 1.2, 0.4), (3.2, 1.4, 0.8), board_m, bevel=0.05),
       cyl("TankW", (ZX, 1.2, 1.45), 0.7, 1.25, water_m, verts=32),
       cyl("TankLid", (ZX, 1.2, 2.33), 0.8, 0.08, post_m, verts=32)]
attach(lp_, lab)
vis(lab, [(S[9], S[10])])
lj = make_jelly("LabJ", (ZX, 1.2, 1.6), 0.6, jel_m)
lb = sphere("LabBlob", (ZX, 1.2, 1.2), 0.2, blob_m, sub=2)
spans_j, spans_b = [], []
n_ = E(9) - S[9]
for k in range(10):
    a = S[9] + round(k * n_ / 10); b = S[9] + round((k + 1) * n_ / 10)
    m = (a + b) // 2
    spans_j.append((a, m)); spans_b.append((m, b))
vis(lj, spans_j); vis(lb, spans_b)
for k in range(10):
    a = S[9] + round(k * n_ / 10); b = S[9] + round((k + 1) * n_ / 10) if k < 9 else E(9)
    t_ = text(f"Cnt{k}", str(k + 1), (ZX, 0.46, 0.42), 0.6, red_lab if k == 9 else mat(f"CntM{k}", (0.08, 0.08, 0.1), 0.5), extrude=0.03)
    vis(t_, [(a, b)])

# =================== lines 10-15: YOU ===================
LAWNP = (-5.0, 1.0, 0.0)
DECKP = (-4.5, 0.7, 0.0)
HID = (0, 60, -30)
shirt_m = mat("Shirt", (0.95, 0.45, 0.2), 0.6); pants_m = mat("Pants", (0.2, 0.3, 0.55), 0.7)
you, YD = person("You", (0, 0, 0), 1.0, shirt_m, pants_m, skin_m, mat("Hair", (0.25, 0.14, 0.07), 0.8))
jumps(you, [(0, HID), (S[10], LAWNP), (S[11], HID), (S[14], (-6.6, 1.0, 0.0)), (S[15], HID)])
you.rotation_euler = (0, 0, math.radians(-8)); you.keyframe_insert("rotation_euler", frame=0)
for k in range(2):
    bpy.ops.mesh.primitive_torus_add(major_radius=0.7, minor_radius=0.04, location=(LAWNP[0], LAWNP[1], 0.4 + 0.8 * k))
    au = bpy.context.object; au.data.materials.append(ring_m)
    vis(au, [(S[10] + 3 + 3 * k, S[11])])
    key_loc(au, [(S[10], (LAWNP[0], LAWNP[1], 0.2 + 0.8 * k)), (E(10), (LAWNP[0], LAWNP[1], 0.7 + 0.8 * k))])
burst((LAWNP[0], LAWNP[1] - 0.5, 1.2), S[10] + 3, n=14, r=1.0, size=0.05, material=spark_m, f_out=S[11])
# line 11: old you + cake 80
old, OD = person("Old", (0, 0, 0), 1.0, mat("OShirt", (0.55, 0.5, 0.7), 0.7), mat("OPants", (0.35, 0.33, 0.3), 0.7), skin_m, grey_hair)
cane = tube("Cane", [(0.44, -0.1, 0.8), (0.46, -0.12, 0.0)], [0.035, 0.035], mat("CaneM", (0.4, 0.22, 0.1), 0.6))
parent_to(cane, old)
jumps(old, [(0, HID), (S[11], LAWNP), (S[12], HID)])
old.rotation_euler = (math.radians(12), 0, math.radians(-8)); old.keyframe_insert("rotation_euler", frame=0)
CK = Vector((-3.7, 0.8, 0))
ck = group("Cake", tuple(CK))
ckp = [cyl("CakeB", tuple(CK + Vector((0, 0, 0.3))), 0.5, 0.6, cake_m, verts=32),
       cyl("CakeI", tuple(CK + Vector((0, 0, 0.62))), 0.52, 0.08, icing_m, verts=32),
       text("Cake80", "80", tuple(CK + Vector((0, -0.53, 0.3))), 0.42, red_lab, extrude=0.03)]
for sx in (-1, 1):
    ckp.append(cyl("Candle", tuple(CK + Vector((sx * 0.15, 0, 0.82))), 0.04, 0.32, white_lab, verts=8))
    ckp.append(sphere("Flame", tuple(CK + Vector((sx * 0.15, 0, 1.03))), 0.06, flame_m, scale=(1, 1, 1.6), sub=1))
attach(ckp, ck)
pop(ck, S[11] + 2, 5, S[12])
# zzz (tired)
for k in range(3):
    z_ = text(f"Zz{k}", "Z", (LAWNP[0] + 0.4 + 0.25 * k, LAWNP[1] - 0.2, 2.1 + 0.3 * k), 0.25 + 0.08 * k, white_lab, extrude=0.02)
    pop(z_, W(11, 0.55) + 3 * k, 4, S[12])
# line 12: cocoon
coc = group("Cocoon", (LAWNP[0], LAWNP[1], 0.0))
cp_ = [sphere("CocS", (LAWNP[0], LAWNP[1], 0.95), 0.62, cocoon_m, scale=(1.0, 1.0, 1.55), sub=3),
       sphere("CocCore", (LAWNP[0], LAWNP[1] - 0.25, 0.95), 0.3, blob_m, scale=(1, 0.6, 1.4), sub=2)]
for k in range(5):
    bpy.ops.mesh.primitive_torus_add(major_radius=0.6 - abs(k - 2) * 0.1, minor_radius=0.03, location=(LAWNP[0], LAWNP[1], 0.35 + k * 0.3))
    t_ = bpy.context.object; t_.data.materials.append(ring_m); t_.scale = (1, 1, 1); cp_.append(t_)
attach(cp_, coc)
kk = [(0, 0.001), (S[12] - 1, 0.001), (S[12] + 3, 1.15), (S[12] + 5, 1.0)]
for j, f in enumerate(range(S[12] + 8, W(13, 0.3) - 2, 5)):
    kk.append((f, 1.0 if j % 2 else 1.08))
kk += [(W(13, 0.3) - 1, 1.12), (W(13, 0.3), 0.001)]
keyscale(coc, kk)
POP = W(13, 0.3)
burst((LAWNP[0], LAWNP[1] - 0.4, 1.0), POP, n=18, r=1.3, size=0.07, material=spark_m, f_out=S[14])
conf = [lab_m, pink_lab, blue_lab, green_lab]
for k in range(24):
    a = k / 24 * 6.283
    c_ = box("Conf", (LAWNP[0], LAWNP[1] - 0.3, 1.0), (0.12, 0.02, 0.08), conf[k % 4])
    key_loc(c_, [(POP, (LAWNP[0], LAWNP[1] - 0.3, 1.0)), (POP + 10, (LAWNP[0] + 1.6 * math.cos(a), LAWNP[1] - 0.6, 1.3 + 1.2 * math.sin(a))),
                 (S[14] - 1, (LAWNP[0] + 1.7 * math.cos(a), LAWNP[1] - 0.6, 0.3 + 0.8 * math.sin(a)))])
    vis(c_, [(POP, S[14])])
# line 13: kid
kid, KD = person("Kid", (0, 0, 0), 0.62, mat("KShirt", (0.2, 0.75, 0.9), 0.6), mat("KPants", (0.95, 0.75, 0.2), 0.7), skin_m, mat("KHair", (0.25, 0.14, 0.07), 0.8))
jumps(kid, [(0, HID), (S[13], LAWNP), (S[14], (-3.4, 1.0, 0.0)), (S[15], HID), (S[17], DECKP)])
kid.rotation_euler = (0, 0, math.radians(-8)); kid.keyframe_insert("rotation_euler", frame=0)
keyscale(kid, [(0, 1.0), (POP - 1, 0.001), (POP + 3, 1.25), (POP + 6, 1.0)])
for k, ar in enumerate(KD["arms"]):   # arms up: yay!
    keyrot(ar, [(0, (0, 0, 0)), (POP, (0, 0, 0)), (POP + 4, (0, math.radians(150 if k == 0 else -150), 0)), (S[14] - 1, (0, math.radians(150 if k == 0 else -150), 0)), (S[14], (0, 0, 0))])
# line 14: normal human vs you — kid gets endless rings
for k in range(3):
    bpy.ops.mesh.primitive_torus_add(major_radius=0.55, minor_radius=0.04, location=(-3.4, 1.0, 0.25 + 0.4 * k))
    au = bpy.context.object; au.data.materials.append(ring_m)
    vis(au, [(W(14, 0.5) + 2 * k, S[15])])
    keyrot(au, [(S[14], (math.radians(15), 0, 0)), (E(14), (math.radians(15), 0, math.radians(720)))])
# one-life bar under the normal human (1 heart)
hrt_m = mat("HeartR", (0.95, 0.1, 0.15), 0.4, emit=(1.0, 0.1, 0.1), emit_strength=0.6)
def mini_heart(name, c, s=0.25):
    g = group(name, c)
    attach([sphere(name + "a", (c[0] - 0.33 * s, c[1], c[2] + 0.2 * s), 0.48 * s, hrt_m, sub=2),
            sphere(name + "b", (c[0] + 0.33 * s, c[1], c[2] + 0.2 * s), 0.48 * s, hrt_m, sub=2),
            cyl(name + "c", (c[0], c[1], c[2] - 0.35 * s), 0.72 * s, 0.85 * s, hrt_m, rot=(math.radians(180), 0, 0), r2=0.02 * s, verts=16)], g)
    return g
h1 = mini_heart("H1", (-6.6, 0.6, 2.25))
pop(h1, W(14, 0.1), 4, S[15])
for k in range(5):
    hk = mini_heart(f"HK{k}", (-3.4 + (k - 2) * 0.32, 0.6, 1.55 + (0.12 if k % 2 else 0.0)), 0.18)
    pop(hk, W(14, 0.55) + 2 * k, 4, S[15])

# =================== line 15: memories? ===================
BRC = Vector((-8.6, 1.2, 1.25))
brg = group("Brain", tuple(BRC))
attach([sphere("BrainL", tuple(BRC + Vector((-0.3, 0, 0))), 0.48, pink_lab, scale=(1.0, 0.85, 0.85), sub=2, smooth=False),
        sphere("BrainR", tuple(BRC + Vector((0.3, 0, 0))), 0.48, pink_lab, scale=(1.0, 0.85, 0.85), sub=2, smooth=False),
        box("BPed", (BRC.x, BRC.y, 0.3), (1.2, 1.0, 0.6), board_m, bevel=0.05)], brg)
vis(brg, [(S[15], S[16])])
for k in range(3):
    q_ = text(f"QB{k}", "?", (BRC.x - 0.9 + 0.9 * k, BRC.y - 0.4, BRC.z + 0.85 + (0.2 if k == 1 else 0)), 0.55, lab_m, extrude=0.05)
    pop(q_, W(15, 0.15 + 0.15 * k), 4, S[16])
# memory "photos" fading out of the brain
for k in range(4):
    ph_ = box("Memo", tuple(BRC + Vector((0, -0.4, 0.2))), (0.36, 0.03, 0.28), white_lab)
    t0 = W(15, 0.3 + 0.1 * k)
    a = 0.6 + k * 0.6
    key_loc(ph_, [(t0, tuple(BRC + Vector((0, -0.4, 0.2)))), (t0 + 14, tuple(BRC + Vector((1.3 * math.cos(a) * (1 if k % 2 else -1), -0.5, 0.4 + 0.4 * math.sin(a)))))])
    vis(ph_, [(t0, S[16])])

# =================== line 16: a fish eats it ===================
PJ = Vector((1.8, 0.6, -0.75))
prey = make_jelly("Prey", tuple(PJ), 0.75, jel_m)
CH = W(16, 0.55)
vis(prey, [(S[16], CH)])
fsh = group("Fish", (5.0, 0.6, -0.7))
FC = Vector((5.0, 0.6, -0.7))
fp2 = [sphere("FBody", tuple(FC), 0.55, fish_m, scale=(1.4, 0.75, 1.0), sub=3),
       cyl("FTail", tuple(FC + Vector((0.95, 0, 0))), 0.45, 0.5, fin_m, rot=(0, math.radians(-90), 0), r2=0.02, verts=4),
       cyl("FFin", tuple(FC + Vector((0.0, 0, 0.55))), 0.3, 0.3, fin_m, r2=0.02, verts=4),
       sphere("FEyeW", tuple(FC + Vector((-0.45, -0.32, 0.18))), 0.13, eyew, sub=2),
       sphere("FEyeB", tuple(FC + Vector((-0.5, -0.4, 0.18))), 0.065, eyeb, sub=1),
       sphere("FMouth", tuple(FC + Vector((-0.75, -0.05, -0.1))), 0.18, eyeb, scale=(0.6, 1, 0.8), sub=2)]
attach(fp2, fsh)
vis(fsh, [(S[16], S[17])])
key_loc(fsh, [(S[16], (5.4, 0.6, -0.7)), (CH, (PJ.x + 0.85, 0.6, -0.72)), (CH + 3, (PJ.x + 0.75, 0.6, -0.72)), (E(16), (PJ.x + 0.4, 0.6, -0.65))])
keyscale(fsh, [(S[16], 1.0), (CH - 1, 1.0), (CH + 2, (0.9, 1.0, 1.15)), (CH + 5, 1.0)])
burst(tuple(PJ + Vector((0, -0.4, 0))), CH, n=14, r=0.7, size=0.05, material=spark_m, f_out=E(16))
for k in range(6):
    bb = sphere("FBub", tuple(PJ), 0.06, bubble_m, sub=1)
    key_loc(bb, [(CH + k, tuple(PJ + Vector((0.2 * k - 0.5, -0.2, 0)))), (CH + k + 14, tuple(PJ + Vector((0.2 * k - 0.4, -0.2, 0.6))))])
    vis(bb, [(CH + k, min(CH + k + 14, S[17]))])

# =================== line 17: question ===================
qm = text("QMark", "?", (DECKP[0] + 0.05, DECKP[1] - 0.1, 1.75), 1.1, lab_m, extrude=0.08)
pop(qm, S[17] + 4, 5)

# =================== views ===================
V, V2 = {}, {}
V[0] = ((-1.8, -4.6, 0.0), (0.8, 0.6, -0.7));            V2[0] = ((1.4, -3.9, 0.0), (1.0, 0.6, -0.7))
V[1] = ((ZX + 1.8, -3.6, 1.3), (ZX + 0.1, 1.0, 1.1));      V2[1] = ((ZX - 0.6, -3.1, 1.3), (ZX + 0.1, 1.0, 1.1))
V[2] = ((2.9, -3.4, 0.0), (1.0, 0.6, -0.65));            V2[2] = ((0.4, -3.0, 0.0), (1.0, 0.6, -0.65))
V[3] = ((-0.6, -3.2, 0.0), (1.0, 0.6, -0.75));           V2[3] = ((1.8, -2.9, 0.0), (1.0, 0.6, -0.8))
V[4] = ((2.6, -3.4, 0.0), (1.1, 0.6, -0.9));             V2[4] = ((0.4, -3.2, 0.0), (1.1, 0.6, -1.25))
V[5] = ((-0.4, -3.0, 0.0), (1.0, 0.6, -1.35));           V2[5] = ((1.6, -2.7, 0.0), (1.0, 0.6, -1.4))
V[6] = ((2.4, -3.2, 0.0), (1.0, 0.6, -1.2));             V2[6] = ((0.5, -3.0, 0.0), (1.0, 0.6, -1.1))
V[7] = ((-0.8, -3.8, 0.0), (1.0, 0.6, -0.9));            V2[7] = ((2.2, -4.0, 0.0), (1.0, 0.6, -0.8))
V[8] = ((-5.0, -4.6, 1.6), (-7.0, 1.0, 1.2));            V2[8] = ((-8.8, -4.4, 1.6), (-7.0, 1.0, 1.2))
V[9] = ((ZX - 1.2, -4.0, 1.3), (ZX, 1.0, 1.0));          V2[9] = ((ZX + 0.9, -3.7, 1.3), (ZX, 1.0, 1.0))
V[10] = ((-3.2, -4.0, 1.0), (-5.0, 1.0, 0.9));           V2[10] = ((-6.3, -3.6, 1.0), (-5.0, 1.0, 0.9))
V[11] = ((-6.6, -3.9, 1.0), (-4.5, 1.0, 0.8));           V2[11] = ((-3.6, -3.5, 1.0), (-4.5, 1.0, 0.8))
V[12] = ((-3.4, -3.4, 1.0), (-5.0, 1.0, 0.9));           V2[12] = ((-6.0, -3.0, 1.0), (-5.0, 1.0, 0.9))
V[13] = ((-6.4, -3.4, 0.8), (-5.0, 1.0, 0.7));           V2[13] = ((-4.0, -3.7, 0.8), (-5.0, 1.0, 0.7))
V[14] = ((-4.4, -6.6, 1.2), (-5.0, 1.0, 0.9));           V2[14] = ((-5.6, -6.4, 1.2), (-5.0, 1.0, 0.9))
V[15] = ((-7.2, -3.6, 1.3), tuple(BRC));                  V2[15] = ((-9.9, -3.3, 1.3), tuple(BRC))
V[16] = ((4.8, -4.2, 0.0), (3.0, 0.6, -0.7));            V2[16] = ((1.4, -3.8, 0.0), (2.2, 0.6, -0.7))
V[17] = ((-5.6, -5.0, 1.0), (-3.8, 0.8, 0.0));           V2[17] = ((-2.6, -7.0, 1.6), (-3.2, 1.0, 0.0))

def LB(i, name, body, m_, size=None, f_in=None, f_out=None, Dk=0.55, end=False, v=0.26, u=0.0):
    mid = lambda a, b: tuple((Vector(a) + Vector(b)) / 2)
    view = V2[i] if end else (mid(V[i][0], V2[i][0]), mid(V[i][1], V2[i][1]))
    cl = Vector(CL(view)); D = (Vector(view[1]) - cl).length * Dk
    s_ = 0.9 * fit(body, D, size if size else 1e9)
    return label(name, body, view, D, v, s_, m_, (S[i] + 3) if f_in is None else f_in,
                 E(i) if f_out is None else f_out, u)
LB(0, "L0", "IMMORTAL?", lab_m, f_in=S[0] + 8)
LB(1, "L1", "ONLY 4.5 mm!", lab_m)
LB(2, "L2", "SUPERPOWER!", lab_m)
LB(3, "L3", "OLD OR HURT", white_lab)
LB(4, "L4", "SINKS...", blue_lab)
LB(5, "L5", "TINY BLOB", lab_m, f_in=W(5, 0.5))
LB(6, "L6", "BABY AGAIN!", pink_lab, f_in=W(6, 0.3))
LB(7, "L7", "NEW JELLYFISH!", lab_m)
LB(8, "L8", "AGAIN & AGAIN", blue_lab)
LB(9, "L9", "10 RESTARTS!", lab_m)
LB(10, "L10", "YOU + POWER", lab_m)
LB(11, "L11", "AGE 80", white_lab)
LB(12, "L12", "COCOON", lab_m)
LB(13, "L13", "KID AGAIN!", green_lab, f_in=POP)
LB(14, "L14a", "1 LIFE", red_lab, size=0.3, u=-0.27, v=0.24)
LB(14, "L14b", "ENDLESS", lab_m, size=0.3, u=0.27, v=0.24, f_in=W(14, 0.5))
LB(15, "L15", "MEMORIES?", pink_lab)
LB(16, "L16", "CHOMP!", red_lab, f_in=CH)
LB(17, "L17", "RESTART YOUR LIFE?", lab_m, end=True, f_in=S[17] + 6, Dk=0.45)

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
