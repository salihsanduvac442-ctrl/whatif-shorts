# Day 4 — What if 1 billion ladybugs landed on your house?  Build: python3 episodes/004-ladybugs/scene.py
# Reference style: base (helpers, lawn/soil, house, garden) copied from episodes/003-lift-million-ref/scene.py
import bpy, math, random, os, json
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
random.seed(4)
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


# =====================================================================================
# Day 4 — What if 1 billion ladybugs landed on your house?
# Facts used (seven-spot ladybird): ~30 mg each, ~50 aphids a day, body ~7 x 6 mm (~0.33 cm2).
#   1,000,000 x 30 mg = 30 kg ; 1,000,000,000 x 30 mg = 30 t (a loaded cement mixer truck is ~30 t)
#   one layer of 1e9 x 0.33 cm2 = ~33,000 m2 = ~5 soccer pitches (7,140 m2) = ~100x a house's roof + walls (~300 m2)
#   1e9 x 50 aphids = 50 billion aphids a day. 2019: a ladybug swarm showed up on NWS San Diego weather radar.
#   Reflex bleeding: yellow, smelly fluid from the leg joints. Some species shelter in houses for winter.
# Cartoon scale: ladybugs are drawn much bigger than life so they read on a phone.
# =====================================================================================

def cell_mat(name, base, dark, spot, scale=4.0, spot_r=0.14, edge=0.05, rough=0.35, bump=0.5):
    """Packed beetles: each voronoi cell is one bug (domed), with a black spot and dark gaps between bugs."""
    m = bpy.data.materials.new(name); m.use_nodes = True
    N = m.node_tree.nodes; L = m.node_tree.links
    bs = N["Principled BSDF"]; bs.inputs["Roughness"].default_value = rough
    tc = N.new("ShaderNodeTexCoord")
    v1 = N.new("ShaderNodeTexVoronoi"); v1.inputs["Scale"].default_value = scale
    v2 = N.new("ShaderNodeTexVoronoi"); v2.feature = 'DISTANCE_TO_EDGE'; v2.inputs["Scale"].default_value = scale
    for v in (v1, v2):
        L.new(tc.outputs["Object"], v.inputs["Vector"])
    s1 = N.new("ShaderNodeMath"); s1.operation = 'LESS_THAN'; s1.inputs[1].default_value = spot_r
    L.new(v1.outputs["Distance"], s1.inputs[0])
    e1 = N.new("ShaderNodeMath"); e1.operation = 'LESS_THAN'; e1.inputs[1].default_value = edge
    L.new(v2.outputs["Distance"], e1.inputs[0])
    mx = N.new("ShaderNodeMath"); mx.operation = 'MAXIMUM'
    L.new(s1.outputs[0], mx.inputs[0]); L.new(e1.outputs[0], mx.inputs[1])
    c = N.new("ShaderNodeMix"); c.data_type = 'RGBA'
    c.inputs[6].default_value = (*base, 1); c.inputs[7].default_value = (*spot, 1)
    L.new(mx.outputs[0], c.inputs["Factor"])
    L.new(c.outputs[2], bs.inputs["Base Color"])
    inv = N.new("ShaderNodeMath"); inv.operation = 'SUBTRACT'; inv.inputs[0].default_value = 1.0
    L.new(v1.outputs["Distance"], inv.inputs[1])
    bp = N.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = bump
    L.new(v2.outputs["Distance"], bp.inputs["Height"]); L.new(bp.outputs["Normal"], bs.inputs["Normal"])
    return m


def recenter(o, bottom=False):
    """Move the object origin to its mesh centre (or bottom centre) so scale animations grow in place."""
    from mathutils import Matrix, Vector
    bpy.context.view_layer.update()
    vs = [o.matrix_world @ v.co for v in o.data.vertices]
    c = Vector((sum(v.x for v in vs) / len(vs), sum(v.y for v in vs) / len(vs),
                min(v.z for v in vs) if bottom else sum(v.z for v in vs) / len(vs)))
    o.data.transform(o.matrix_world)
    o.data.transform(Matrix.Translation(-c))
    o.matrix_world = Matrix.Translation(c)
    return o

red_m = mat("LadyRed", (0.9, 0.05, 0.03), 0.25)
black_m = mat("LadyBlack", (0.02, 0.02, 0.025), 0.3)
white_m = mat("LadyWhite", (1, 1, 1), 0.3)
bugs_m = cell_mat("Bugs", (0.88, 0.06, 0.04), (0.2, 0.02, 0.02), (0.03, 0.02, 0.02), scale=4.0)
bugs_big_m = cell_mat("BugsBig", (0.88, 0.06, 0.04), (0.2, 0.02, 0.02), (0.03, 0.02, 0.02), scale=0.35, bump=0.2)
aphid_m = cell_mat("Aphids", (0.45, 0.85, 0.25), (0.2, 0.4, 0.1), (0.15, 0.35, 0.08), scale=7.0, spot_r=0.08, edge=0.06)
yellow_m = mat("Knee", (1.0, 0.82, 0.1), 0.15, emit=(1.0, 0.75, 0.05), emit_strength=0.4)
stink_m = mat("Stink", (0.55, 0.85, 0.2), 0.5, emit=(0.5, 0.8, 0.2), emit_strength=0.6)
lab_m = mat("LabelM", (1.0, 0.85, 0.2), 0.4, emit=(1.0, 0.8, 0.2), emit_strength=0.8)

# ---------- one shared low-poly bug mesh for swarms (shell + head + spots, 3 material slots) ----------
def make_bug_mesh():
    objs = []
    objs.append(sphere("bs", (0, 0, 0), 1.0, red_m, scale=(0.95, 1.15, 0.72), sub=2))
    objs.append(sphere("bh", (0, -1.05, -0.1), 0.48, black_m, sub=1))
    for (x, y) in [(-0.45, -0.35), (0.45, -0.35), (-0.5, 0.45), (0.5, 0.45), (0, 0.15)]:
        z = 0.72 * math.sqrt(max(0.0, 1 - (x / 0.95) ** 2 - (y / 1.15) ** 2))
        objs.append(sphere("bsp", (x, y, z), 0.24, black_m, scale=(1, 1, 0.5), sub=1))
    for sx in (-1, 1):
        objs.append(sphere("be", (sx * 0.2, -1.42, 0.05), 0.12, white_m, sub=1))
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    bpy.ops.object.join()
    o = bpy.context.object; o.name = "BugProto"
    me = o.data
    sc.collection.objects.unlink(o)
    return me
BUG = make_bug_mesh()

def bug(name, loc, r, rz=None):
    o = bpy.data.objects.new(name, BUG); sc.collection.objects.link(o)
    o.location = loc; o.scale = (r,) * 3
    o.rotation_euler = (random.uniform(-0.3, 0.3), random.uniform(-0.3, 0.3), random.uniform(0, 6.28) if rz is None else rz)
    return o

def keyscale(o, keys):
    for f, s in keys:
        o.scale = (s,) * 3 if not isinstance(s, tuple) else s
        o.keyframe_insert("scale", frame=f)

# ---------- hero ladybug (legs, antennae) ----------
def hero(name, loc, r, rz=0.0):
    x, y, z = loc
    g = group(name, loc, rz)
    zc = z + 0.55 * r
    p = [sphere("HShell", (x, y, zc), r, red_m, scale=(0.95, 1.15, 0.72), sub=3),
         sphere("HHead", (x, y - 1.05 * r, zc - 0.1 * r), 0.5 * r, black_m, sub=2),
         box("HSeam", (x, y + 0.05 * r, zc + 0.69 * r), (0.05 * r, 1.6 * r, 0.04 * r), black_m)]
    for (sx, sy) in [(-0.45, -0.35), (0.45, -0.35), (-0.5, 0.45), (0.5, 0.45), (-0.25, 0.85), (0.25, 0.85)]:
        sz = 0.72 * math.sqrt(max(0.0, 1 - (sx / 0.95) ** 2 - (sy / 1.15) ** 2))
        p.append(sphere("HSpot", (x + sx * r, y + sy * r, zc + sz * r), 0.2 * r, black_m, scale=(1, 1, 0.45), sub=2))
    for sx in (-1, 1):
        p.append(sphere("HEyeW", (x + sx * 0.2 * r, y - 1.45 * r, zc + 0.02 * r), 0.15 * r, white_m, sub=2))
        p.append(sphere("HEyeP", (x + sx * 0.2 * r, y - 1.57 * r, zc + 0.02 * r), 0.07 * r, black_m, sub=1))
        p.append(tube("HAnt", [(x + sx * 0.15 * r, y - 1.35 * r, zc + 0.3 * r), (x + sx * 0.35 * r, y - 1.75 * r, zc + 0.75 * r)],
                      [0.035 * r, 0.025 * r], black_m))
        p.append(sphere("HAntTip", (x + sx * 0.35 * r, y - 1.75 * r, zc + 0.75 * r), 0.07 * r, black_m, sub=1))
        for dy in (-0.5, 0.0, 0.5):
            p.append(tube("HLeg", [(x + sx * 0.6 * r, y + dy * r, zc - 0.3 * r), (x + sx * 1.15 * r, y + dy * 1.2 * r, zc - 0.15 * r),
                                   (x + sx * 1.35 * r, y + dy * 1.3 * r, z)], [0.07 * r, 0.06 * r, 0.05 * r], black_m))
    attach(p, g)
    return g

# =================== lines 1-2: one ladybug on a kitchen scale, then the aphid plant ===================
T = 0.85
wood = mat("Wood", (0.75, 0.5, 0.28), 0.7)
TX, TY = -1.5, -0.6
box("TableTop", (TX, TY, T - 0.03), (1.3, 0.75, 0.06), wood, bevel=0.01)
for dx in (-0.58, 0.58):
    for dy in (-0.3, 0.3):
        box("TableLeg", (TX + dx, TY + dy, (T - 0.06) / 2), (0.06, 0.06, T - 0.06), wood)
scale_m = mat("ScaleBody", (0.97, 0.97, 0.98), 0.4)
plat_m = mat("ScalePlat", (0.75, 0.78, 0.82), 0.25, metal=0.6)
lcd_m = mat("LCD", (0.6, 0.9, 0.62), 0.4, emit=(0.5, 0.9, 0.55), emit_strength=0.8)
lcd_ink = mat("LCDInk", (0.02, 0.06, 0.03), 0.5)
PT = T + 0.0925
SA = (TX - 0.3, TY + 0.02)
box("ScaleBase", (SA[0], SA[1], T + 0.035), (0.42, 0.42, 0.07), scale_m, bevel=0.012)
box("ScalePlat", (SA[0], SA[1], T + 0.085), (0.38, 0.38, 0.015), plat_m, bevel=0.004)
box("LCD", (SA[0], SA[1] - 0.215, T + 0.035), (0.24, 0.02, 0.07), lcd_m)
def readout(body, cx, cy, z, size, f_in, f_out=None):
    o = text("Readout", body, (cx, cy, z), size, lcd_ink)
    hide_until(o, f_in)
    if f_out is not None:
        gone_at(o, f_out, 1)
    return o
readout("0 g", SA[0], SA[1] - 0.226, T + 0.035, 0.05, 0, S[1] + 12)
readout("0.03 g", SA[0], SA[1] - 0.226, T + 0.035, 0.05, S[1] + 12)

H1 = hero("Hero1", (SA[0], SA[1], PT), 0.07)
key_loc(H1, [(0, (SA[0], SA[1], PT + 0.9)), (S[1] - 2, (SA[0], SA[1], PT + 0.6)), (S[1] + 10, (SA[0], SA[1], PT))])

# little potted plant with aphids (right side of the table)
PLX, PLY = TX + 0.33, TY + 0.05
cyl("PPot", (PLX, PLY, T + 0.08), 0.1, 0.16, mat("PPotM", (0.75, 0.38, 0.2), 0.7), r2=0.08, verts=16)
leaf_m = mat("Leaf", (0.2, 0.6, 0.18), 0.6)
stem = tube("Stem", [(PLX, PLY, T + 0.15), (PLX + 0.02, PLY, T + 0.35), (PLX - 0.01, PLY, T + 0.52)], [0.012, 0.01, 0.008], leaf_m)
leaves = []
for (dx, dz, a) in [(-0.09, 0.27, 0.5), (0.1, 0.33, -0.5), (-0.08, 0.44, 0.4), (0.09, 0.5, -0.4)]:
    leaves.append(sphere("PLeaf", (PLX + dx, PLY, T + dz), 0.075, leaf_m, scale=(1.3, 0.7, 0.18), sub=2))
    leaves[-1].rotation_euler = (0, a, 0)
aph_green = mat("Aphid", (0.55, 0.92, 0.3), 0.4)
aphids = []
for i in range(26):
    lf = random.randrange(4)
    L0 = leaves[lf].location
    p = (L0[0] + random.uniform(-0.06, 0.06), PLY - random.uniform(0.0, 0.03), L0[2] + 0.02 + random.uniform(-0.01, 0.01))
    a = sphere("Aphid", p, 0.013, aph_green, scale=(1, 1.3, 0.8), sub=1)
    aphids.append(a)
    f = S[2] + 6 + int(i * (S[3] - S[2] - 6) / 26)
    gone_at(a, f, 2)
# hero walks over to the plant and munches (line 2)
key_loc(H1, [(S[2], (SA[0], SA[1], PT)), (S[2] + 8, (PLX - 0.05, PLY - 0.12, T + 0.42)), (S[2] + 18, (PLX + 0.03, PLY - 0.12, T + 0.32)),
             (S[3] - 1, (PLX - 0.02, PLY - 0.12, T + 0.48))])
H1.rotation_euler = (0, 0, 0); H1.keyframe_insert("rotation_euler", frame=S[2])
H1.rotation_euler = (math.radians(-20), 0, math.radians(15)); H1.keyframe_insert("rotation_euler", frame=S[2] + 10)
H1.rotation_euler = (math.radians(-20), 0, math.radians(-15)); H1.keyframe_insert("rotation_euler", frame=S[2] + 20)
H1.rotation_euler = (0, 0, 0); H1.keyframe_insert("rotation_euler", frame=S[3])
# line 3: it flies up out of shot
key_loc(H1, [(S[3] + 6, (PLX - 0.3, PLY - 0.4, T + 1.4))])
gone_at(H1, S[3] + 10, 3)
cnt50 = text("Cnt50", "50", (PLX + 0.0, PLY - 0.05, T + 0.72), 0.12, lab_m, extrude=0.01)
pop(cnt50, S[2] + 4, 6, S[3] + 3)

# =================== lines 3-5: a thousand, a red cloud, a million on a big scale ===================
swarmA = []
CA = (0.3, 4.0, 3.0)
for i in range(170):
    start = (TX + random.uniform(-1.2, 1.6), TY + random.uniform(-0.4, 1.5), T + random.uniform(0.2, 1.6))
    o = bug("SwA", start, 0.05)
    f0 = S[3] + 2 + int(i * (S[4] - S[3] - 4) / 170)
    c1 = (CA[0] + random.uniform(-4.0, 4.0), CA[1] + random.uniform(-2.5, 2.5), CA[2] + random.uniform(-1.4, 1.4))
    c2 = (c1[0] + random.uniform(-1.2, 1.2), c1[1] + random.uniform(-1, 1), c1[2] + random.uniform(-0.5, 0.5))
    tgt = (1.7 + random.uniform(-0.25, 0.25), 0.2 + random.uniform(-0.25, 0.25), 0.4)
    key_loc(o, [(f0, start), (S[4] + 8, c1), (S[5] - 2, c2), (S[5] + 8, tgt)])
    keyscale(o, [(0, 0.001), (f0 - 1, 0.001), (f0 + 3, 0.065), (f0 + 5, 0.05), (S[4] + 8, 0.12), (S[5] - 2, 0.12), (S[5] + 6, 0.05), (S[5] + 9, 0.001)])
    swarmA.append(o)

# platform scale with a 30 kg pile of beetles, next to you
BSX, BSY = 1.7, 0.2
bsc = group("BigScale", (BSX, BSY, 0))
bp = [box("BSBase", (BSX, BSY, 0.06), (1.0, 1.0, 0.12), scale_m, bevel=0.03),
      box("BSPlat", (BSX, BSY, 0.13), (0.92, 0.92, 0.03), plat_m, bevel=0.01),
      box("BSPost", (BSX, BSY + 0.42, 0.55), (0.08, 0.08, 0.9), scale_m),
      box("BSHead", (BSX, BSY + 0.42, 1.05), (0.6, 0.12, 0.3), scale_m, bevel=0.03),
      box("BSLcd", (BSX, BSY + 0.35, 1.05), (0.5, 0.02, 0.2), lcd_m)]
attach(bp, bsc)
pop(bsc, S[4] + 10, 7, S[7] + 2)
readout("0 kg", BSX, BSY + 0.335, 1.05, 0.14, S[4] + 14, S[5] + 8)
readout("30 kg", BSX, BSY + 0.335, 1.05, 0.14, S[5] + 8, S[7] + 2)
pile1 = sphere("Pile30kg", (BSX, BSY - 0.05, 0.145), 0.4, bugs_m, scale=(1, 1, 0.65), sub=3)
keyscale(pile1, [(0, 0.001), (S[5] + 1, 0.001), (S[5] + 9, (1.1, 1.1, 0.75)), (S[5] + 12, (1, 1, 0.65)), (S[7] - 2, (1, 1, 0.65)), (S[7] + 2, 0.001)])

# =================== line 6: roof covered; line 7: the whole house + a billion-bug storm ===================
roof_cov = bpy.data.objects.new("RoofCover", roof.data.copy()); sc.collection.objects.link(roof_cov)
roof_cov.data.materials.clear(); roof_cov.data.materials.append(bugs_m)
roof_cov.location = (HX, HY, HH + 0.04)
mod = roof_cov.modifiers.new("s", 'SOLIDIFY'); mod.thickness = 0.3
wall_cov = recenter(box("WallCover", (HX, HY, HH / 2 + 0.03), (HW + 0.14, HD + 0.14, HH + 0.06), bugs_m), bottom=True)
def cover_keys(o, base):
    k = [(0, 0.001), (base - 1, 0.001), (base + 6, (1.04, 1.04, 1.04)), (base + 9, 1.0),
         (S[13] - 4, 1.0), (S[13], 0.001), (S[17] - 1, 0.001), (S[17] + 5, 1.0)]
    keyscale(o, k)
# roof cover grows from the eaves (scale about the eave-centre origin)
roof_cov.scale = (1, 1, 0.001)
for f, s in [(0, (1, 1, 0.001)), (S[6] + 2, (1, 1, 0.001)), (S[6] + 14, (1.02, 1.02, 1.05)), (S[6] + 18, (1.0, 1.0, 1.0)),
             (S[13] - 4, (1, 1, 1)), (S[13], (1, 1, 0.001)), (S[17] - 1, (1, 1, 0.001)), (S[17] + 6, (1, 1, 1))]:
    roof_cov.scale = s; roof_cov.keyframe_insert("scale", frame=f)
wall_cov.scale = (1, 1, 0.001)
for f, s in [(0, (1, 1, 0.001)), (S[7] + 2, (1, 1, 0.001)), (S[7] + 12, (1.0, 1.0, 1.0)),
             (S[13] - 4, (1, 1, 1)), (S[13], (1, 1, 0.001)), (S[17] - 1, (1, 1, 0.001)), (S[17] + 6, (1, 1, 1))]:
    wall_cov.scale = s; wall_cov.keyframe_insert("scale", frame=f)
# wall cover origin is at its centre: move it so it grows up from the ground
# shell of bugs on the lawn around the house (line 7 on)
lawn_cov = sphere("LawnCover", (HX, HY - 1.0, -0.6), 1.0, bugs_m, scale=(9.0, 6.5, 0.75), sub=3)
keyscale(lawn_cov, [(0, 0.001), (S[7] + 6, (0.001, 0.001, 0.001)), (S[7] + 18, (9.0, 6.5, 0.75)),
                    (S[13] - 4, (9.0, 6.5, 0.75)), (S[13], (0.001, 0.001, 0.001)), (S[17] - 1, (0.001,) * 3), (S[17] + 8, (9.0, 6.5, 0.75))])

def in_house(p):
    return abs(p[0] - HX) < HW / 2 + 0.6 and abs(p[1] - HY) < HD / 2 + 1.0 and p[2] < HH + 2.6
def cloud_pt(c, r):
    while True:
        p = (c[0] + random.uniform(-r[0], r[0]), c[1] + random.uniform(-r[1], r[1]), c[2] + random.uniform(-r[2], r[2]))
        if not in_house(p) and p[2] > 0.5:
            return p
CB = (HX, HY - 1.0, 5.0)
HEAP = (-12.0, 2.5)
swarmB = []
for i in range(380):
    o = bug("SwB", (0, 0, 0), 0.16)
    entry = (CB[0] + random.uniform(-40, 40), CB[1] - 60, random.uniform(15, 30))
    f0 = S[7] - 6 + random.randint(0, 10)
    pts = [(f0, entry), (S[7] + 10 + random.randint(0, 6), cloud_pt(CB, (8, 5, 4))), (S[8] + 6, cloud_pt(CB, (8, 5, 4))),
           (S[10], cloud_pt(CB, (8, 5, 4))),
           (S[11] + 8, (HEAP[0] + random.uniform(-3.5, 3.5), HEAP[1] + random.uniform(-3, 3), random.uniform(1.0, 4.5))),
           (S[12] + 2, (HEAP[0] + random.uniform(-2.5, 2.5), HEAP[1] + random.uniform(-2, 2), random.uniform(0.6, 3.0))),
           (S[13] + 4, cloud_pt(CB, (9, 6, 5))), (S[15], cloud_pt(CB, (9, 6, 5))), (S[17], cloud_pt(CB, (9, 6, 5))),
           (FRAMES, cloud_pt(CB, (9, 6, 5)))]
    key_loc(o, pts)
    keyscale(o, [(0, 0.001), (f0 - 1, 0.001), (f0, 0.16), (S[16] - 4, 0.16), (S[16] - 2, 0.001), (S[17] - 2, 0.001), (S[17], 0.16)])
    o.rotation_euler = (0.3, 0, 0); o.keyframe_insert("rotation_euler", frame=f0)
    o.rotation_euler = (-0.3, 0.4, random.uniform(-9, 9)); o.keyframe_insert("rotation_euler", frame=FRAMES)
    swarmB.append(o)

# =================== line 8: 30 t of beetles vs a loaded cement truck on a giant seesaw ===================
PX, PY, PZ = 10.0, 3.0, 1.4
steel = mat("Steel", (0.95, 0.75, 0.2), 0.5)
pivot = cyl("Pivot", (PX, PY, 0.65), 0.95, 1.3, mat("PivotM", (0.3, 0.32, 0.38), 0.6), verts=3)
pivot.rotation_mode = 'ZXY'; pivot.rotation_euler = (math.radians(90), 0, math.radians(90))
plank = group("Plank", (PX, PY, PZ))
pl = box("PlankBoard", (PX, PY, PZ), (11.0, 2.6, 0.22), steel, bevel=0.04)
pile30t = sphere("Pile30t", (PX - 3.6, PY, PZ + 0.11), 1.0, bugs_m, scale=(1.7, 1.2, 1.25), sub=3)
attach([pl, pile30t], plank)
pop(pivot, S[8] - 4, 6, S[10]); pop(plank, S[8] - 4, 6, S[10])
TILT = math.radians(13)
for f, a in [(S[8] - 4, TILT), (S[8] + 8, TILT), (S[8] + 14, math.radians(-4)), (S[8] + 18, math.radians(2)), (S[8] + 22, 0)]:
    plank.rotation_euler = (0, a, 0); plank.keyframe_insert("rotation_euler", frame=f)
# cement mixer truck
truck_c = mat("TruckCab", (0.95, 0.55, 0.1), 0.4)
drum_m = stripe_mat("Drum", (0.92, 0.92, 0.95), (0.2, 0.45, 0.9), axis="Z", freq=5.0, thresh=0.3, rough=0.4)
tyre_m = mat("Tyre", (0.06, 0.06, 0.06), 0.9)
glass = mat("TGlass", (0.25, 0.35, 0.45), 0.1)
TRX = PX + 3.0
truck = group("Truck", (TRX, PY, PZ + 0.11))
z0 = PZ + 0.11
tp = [box("TChassis", (TRX, PY, z0 + 0.55), (4.6, 1.6, 0.3), mat("Chassis", (0.2, 0.2, 0.22), 0.6)),
      box("TCab", (TRX + 1.65, PY, z0 + 1.25), (1.3, 1.65, 1.3), truck_c, bevel=0.1),
      box("TWin", (TRX + 2.31, PY, z0 + 1.45), (0.04, 1.4, 0.6), glass),
      cyl("TDrum", (TRX - 0.5, PY, z0 + 1.5), 0.85, 2.6, drum_m, rot=(0, math.radians(75), 0), verts=20, r2=0.55)]
for dx in (-1.7, -0.6, 1.6):
    for dy in (-0.85, 0.85):
        tp.append(cyl("TWheel", (TRX + dx, PY + dy, z0 + 0.42), 0.42, 0.32, tyre_m, rot=(math.radians(90), 0, 0), verts=16))
attach(tp, truck)
f0 = S[8] + 6
upz = PZ + 0.11 + 3.0 * math.sin(TILT)
key_loc(truck, [(f0 - 6, (TRX, PY, 12.0)), (f0 + 2, (TRX, PY, upz)), (S[8] + 14, (TRX, PY, PZ + 0.11 - 3.0 * math.sin(math.radians(4)))),
                (S[8] + 18, (TRX, PY, PZ + 0.11 + 3.0 * math.sin(math.radians(2)))), (S[8] + 22, (TRX, PY, PZ + 0.11))])
for f, a in [(f0 - 6, 0.3), (f0 + 2, -TILT), (S[8] + 14, math.radians(4)), (S[8] + 18, math.radians(-2)), (S[8] + 22, 0)]:
    truck.rotation_euler = (0, a, 0); truck.keyframe_insert("rotation_euler", frame=f)
hide_until(truck, f0 - 6); gone_at(truck, S[10], 3)
lab30 = text("Lab30t", "30 t", (PX - 3.6, PY - 1.3, PZ + 3.4), 1.0, lab_m, extrude=0.05)
pop(lab30, S[8] + 2, 6, S[9] + 2)
labT = text("LabTruck", "30 t", (TRX + 0.4, PY - 1.3, PZ + 3.4), 1.0, mat("LabW", (1, 1, 1), 0.4, emit=(1, 1, 1), emit_strength=0.7), extrude=0.05)
pop(labT, S[8] + 10, 6, S[9] + 2)

# =================== line 9: five soccer fields carpeted red ===================
pitch_m = stripe_mat("Pitch", (0.3, 0.66, 0.2), (0.24, 0.56, 0.16), axis="X", freq=0.6, thresh=0.0, rough=0.9)
line_m = mat("PitchLine", (1, 1, 1), 0.5)
FY0 = 150.0
for k in range(5):
    cy = FY0 + k * 78
    box("Field", (0, cy, 0.03), (105, 68, 0.06), pitch_m)
    for (dx, dy, wx, wy) in [(0, 34, 105, 0.6), (0, -34, 105, 0.6), (52.5, 0, 0.6, 68), (-52.5, 0, 0.6, 68), (0, 0, 0.6, 68)]:
        box("FLine", (dx, cy + dy, 0.07), (wx, wy, 0.04), line_m)
    cov = recenter(box("FieldCover", (0, cy, 0.12), (106, 69, 0.2), bugs_big_m))
    keyscale(cov, [(0, 0.001), (S[9] + 3 + 5 * k, 0.001), (S[9] + 8 + 5 * k, (1.05, 1.05, 1)), (S[9] + 10 + 5 * k, 1.0)])
    lab = text("FLab", str(k + 1), (-70, cy, 1.0), 26, lab_m, rot=(0, 0, 0), extrude=0.5)
    pop(lab, S[9] + 6 + 5 * k, 5)
for o in [o for o in bpy.data.objects if o.name.startswith(("Field", "FLine", "FLab"))]:
    s0 = tuple(o.scale) if o.name.startswith(("Field", "FLine")) and not o.name.startswith("FieldCover") else None
    if s0 is not None:
        keyscale(o, [(0, 0.001), (S[9] - 2, 0.001), (S[9] - 1, s0), (S[10], s0), (S[10] + 1, 0.001)])
    else:
        o.keyframe_insert("scale", frame=S[10]); o.scale = (0.001,) * 3; o.keyframe_insert("scale", frame=S[10] + 1)

for o in [o for o in bpy.data.objects if o.name.startswith("Cloud")]:
    keyscale(o, [(S[9] - 1, tuple(o.scale)), (S[9], 0.001), (S[10] - 1, 0.001), (S[10], tuple(o.scale))])

# =================== line 10: your house, a hundred times ===================
mini_c = []
for i in range(10):
    for j in range(10):
        x, y = -4.5 + i * 1.0, 2.2 + j * 0.85
        g = group("Mini", (x, y, 0))
        mp = [box("MiniBox", (x, y, 0.2), (0.62, 0.5, 0.4), bugs_m)]
        rm = bpy.data.meshes.new("MiniRoof")
        rw, rd, rh = 0.72, 0.6, 0.28
        rm.from_pydata([(-rw/2, -rd/2, 0), (rw/2, -rd/2, 0), (rw/2, rd/2, 0), (-rw/2, rd/2, 0), (-rw/2, 0, rh), (rw/2, 0, rh)], [],
                       [(0, 1, 5, 4), (3, 4, 5, 2), (0, 4, 3), (1, 2, 5), (0, 3, 2, 1)])
        ro = bpy.data.objects.new("MiniRoof", rm); sc.collection.objects.link(ro); ro.location = (x, y, 0.4)
        rm.materials.append(bugs_m)
        mp.append(ro)
        attach(mp, g)
        f = S[10] + 2 + int((9 - j) * 2.2 + i * 0.5)
        keyscale(g, [(0, 0.001), (f - 1, 0.001), (f + 3, 1.2), (f + 5, 1.0), (S[11] - 1, 1.0), (S[11] + 3, 0.001)])
        mini_c.append(g)

# =================== lines 11-12: a hill of aphids gets eaten ===================
heap = sphere("AphidHeap", (HEAP[0], HEAP[1], -0.4), 1.0, aphid_m, scale=(3.0, 2.6, 2.4), sub=3)
keyscale(heap, [(0, 0.001), (S[11] - 3, 0.001), (S[11] + 4, (3.2, 2.8, 2.6)), (S[11] + 7, (3.0, 2.6, 2.4)),
                (S[12] - 2, (1.6, 1.4, 1.2)), (S[12] + 8, (0.001,) * 3)])
spark_m = mat("Spark", (1, 0.95, 0.4), 0.3, emit=(1, 0.9, 0.3), emit_strength=3.0)
for i in range(18):
    a = i / 18 * 6.283
    sp_ = sphere("Spark", (HEAP[0] + 2.4 * math.cos(a), HEAP[1] + 1.6 * math.sin(a), 0.6 + random.uniform(0, 2.4)), 0.16, spark_m, sub=1)
    pop(sp_, S[12] + 6 + (i % 4), 5, S[13] + 2)
# ---------------- "you" (arms down) ----------------
def person(name, loc, body_c, skin=(0.95, 0.75, 0.6), hair=(0.25, 0.14, 0.06)):
    g = group(name, loc, 0)
    x, y, z = loc
    bm = mat(name + "B", body_c, 0.7)
    lm = mat(name + "L", (0.18, 0.22, 0.38), 0.8)
    sk = mat(name + "S", skin, 0.6)
    dark = mat(name + "E", (0.05, 0.04, 0.05), 0.4)
    parts = [
        cyl("LegL", (x - 0.13, y, 0.38), 0.1, 0.76, lm), cyl("LegR", (x + 0.13, y, 0.38), 0.1, 0.76, lm),
        cyl("Body", (x, y, 1.08), 0.28, 0.75, bm, r2=0.22),
        sphere("Head", (x, y, 1.68), 0.24, sk, sub=2),
        sphere("Hair", (x, y + 0.05, 1.82), 0.22, mat(name + "Hr", hair, 0.8), scale=(1.05, 1.05, 0.6), sub=2),
        sphere("EyeL", (x - 0.08, y - 0.21, 1.72), 0.035, dark, sub=1), sphere("EyeR", (x + 0.08, y - 0.21, 1.72), 0.035, dark, sub=1),
        tube("Smile", [(x - 0.07, y - 0.215, 1.6), (x, y - 0.235, 1.575), (x + 0.07, y - 0.215, 1.6)], [0.012] * 3, dark),
        tube("ArmL", [(x - 0.3, y, 1.35), (x - 0.4, y - 0.02, 1.08), (x - 0.4, y - 0.05, 0.85)], [0.07, 0.065, 0.06], bm),
        tube("ArmR", [(x + 0.3, y, 1.35), (x + 0.4, y - 0.02, 1.08), (x + 0.4, y - 0.05, 0.85)], [0.07, 0.065, 0.06], bm),
        sphere("HandL", (x - 0.4, y - 0.05, 0.82), 0.06, sk, sub=1), sphere("HandR", (x + 0.4, y - 0.05, 0.82), 0.06, sk, sub=1),
    ]
    attach(parts, g)
    return g

you = person("You", (0, 0, 0), (0.95, 0.3, 0.35))
YX, YY = HEAP[0] + 3.4, HEAP[1] - 2.0
you_keys = [(0, (0.3, 0.4, 0)), (S[11] - 1, (0.3, 0.4, 0)), (S[11], (YX, YY, 0)),
            (S[12] + 2, (YX, YY, 0)), (S[12] + 6, (YX, YY, 0.6)), (S[12] + 10, (YX, YY, 0)), (S[12] + 14, (YX, YY, 0.5)),
            (S[12] + 18, (YX, YY, 0)), (S[13] - 1, (YX, YY, 0)), (S[13], (0.3, 0.4, 0)),
            (S[17] - 1, (0.3, 0.4, 0)), (S[17], (0.0, 4.5, 0))]
for f, p in you_keys:
    you.location = p; you.keyframe_insert("location", frame=f)
you.rotation_euler = (0, 0, 0); you.keyframe_insert("rotation_euler", frame=S[11] - 1)
you.rotation_euler = (0, 0, math.radians(-35)); you.keyframe_insert("rotation_euler", frame=S[11])
you.keyframe_insert("rotation_euler", frame=S[13] - 1)
you.rotation_euler = (0, 0, 0); you.keyframe_insert("rotation_euler", frame=S[13])
you.keyframe_insert("rotation_euler", frame=S[17] - 1)
you.rotation_euler = (0, 0, math.radians(180)); you.keyframe_insert("rotation_euler", frame=S[17])

# =================== line 13: a real swarm in the sky ===================
SKY = (-10.0, 150.0, 70.0)
for i in range(260):
    p = (SKY[0] + random.gauss(0, 30), SKY[1] + random.gauss(0, 14), SKY[2] + random.gauss(0, 9))
    o = bug("SkyBug", p, 2.0)
    q = (p[0] + random.uniform(-6, 6) + 15, p[1] + random.uniform(-4, 4), p[2] + random.uniform(-3, 3))
    key_loc(o, [(S[13] - 2, p), (S[14] + 4, q)])
    keyscale(o, [(0, 0.001), (S[13] - 2, 0.001), (S[13] + 2, 2.0), (S[14] + 4, 2.0), (S[14] + 8, 0.001)])

# =================== line 14: weather radar screen ===================
RX, RY, RZ = -2.6, 3.4, 2.3
radar = group("Radar", (RX, RY, RZ))
scr_m = mat("RadarScr", (0.02, 0.12, 0.06), 0.3, emit=(0.02, 0.2, 0.08), emit_strength=0.6)
ring_m = glow_mat("RadarRing", (0.3, 1.0, 0.45), 2.0)
rp = [box("RFrame", (RX, RY + 0.08, RZ), (3.7, 0.14, 3.7), mat("RFrameM", (0.2, 0.22, 0.26), 0.5), bevel=0.08),
      cyl("RScreen", (RX, RY, RZ), 1.65, 0.06, scr_m, rot=(math.radians(90), 0, 0), verts=48),
      box("RLeg", (RX, RY + 0.12, RZ / 2 - 0.5), (0.25, 0.12, RZ - 0.6), mat("RLegM", (0.3, 0.3, 0.33), 0.5))]
for rr in (0.55, 1.1, 1.6):
    pts = [(RX + rr * math.cos(a / 40 * 6.283), RY - 0.04, RZ + rr * math.sin(a / 40 * 6.283)) for a in range(41)]
    rp.append(tube("RRing", pts, [0.018] * 41, ring_m))
rp.append(box("RCrossH", (RX, RY - 0.04, RZ), (3.2, 0.01, 0.025), ring_m))
rp.append(box("RCrossV", (RX, RY - 0.04, RZ), (0.025, 0.01, 3.2), ring_m))
coast_m = mat("Coast", (0.55, 0.45, 0.25), 0.6, emit=(0.4, 0.3, 0.15), emit_strength=0.5)
rp.append(tube("RCoast", [(RX + 0.9, RY - 0.05, RZ + 1.3), (RX + 0.6, RY - 0.05, RZ + 0.5), (RX + 0.75, RY - 0.05, RZ - 0.3),
                          (RX + 0.5, RY - 0.05, RZ - 1.2)], [0.03] * 4, coast_m))
rp.append(text("RTitle", "RADAR 2019", (RX, RY - 0.05, RZ + 2.15), 0.42, lab_m, extrude=0.03))
attach(rp, radar)
pop(radar, S[14] - 2, 7)
sweep = group("Sweep", (RX, RY - 0.06, RZ))
sw = box("SweepBar", (RX + 0.8, RY - 0.06, RZ), (1.6, 0.01, 0.05), glow_mat("SweepM", (0.5, 1.0, 0.6), 4.0))
attach([sw], sweep)
sweep.rotation_euler = (0, 0, 0); sweep.keyframe_insert("rotation_euler", frame=S[14] - 2)
sweep.rotation_euler = (0, -6.283 * 1.6, 0); sweep.keyframe_insert("rotation_euler", frame=S[15] + 2)
pop(sweep, S[14] - 2, 7)
blob_m = mat("Blob", (1.0, 0.25, 0.15), 0.4, emit=(1.0, 0.2, 0.1), emit_strength=1.6)
for i in range(16):
    b = sphere("RBlob", (RX - 0.2 + random.gauss(0, 0.32), RY - 0.07, RZ + 0.1 + random.gauss(0, 0.32)), random.uniform(0.15, 0.3),
               blob_m, scale=(1, 0.15, 1), sub=2)
    pop(b, S[14] + 6 + i, 6, S[15] + 3)
gone_at(radar, S[15] + 3, 3)
for o in [sweep]:
    gone_at(o, S[15] + 3, 3)

# =================== line 15: knee juice ===================
HBX, HBY = 2.6, 1.0
H2 = hero("Hero2", (HBX, HBY, 0), 0.7)
pop(H2, S[15] - 3, 6)
H2.rotation_euler = (0, 0, 0); H2.keyframe_insert("rotation_euler", frame=S[15] + 4)
for f, a in [(S[15] + 6, 0.12), (S[15] + 8, -0.12), (S[15] + 10, 0.1), (S[15] + 12, 0)]:
    H2.rotation_euler = (0, a, 0); H2.keyframe_insert("rotation_euler", frame=f)
gone_at(H2, S[16] + 2, 3)
r = 0.7
for sx in (-1, 1):
    for dy in (-0.5, 0.0, 0.5):
        kx, ky, kz = HBX + sx * 1.15 * r, HBY + dy * 1.2 * r, 0.55 * r - 0.15 * r
        d = sphere("KneeDrop", (kx, ky, kz + 0.06), 0.09, yellow_m, scale=(1, 1, 1.3), sub=2)
        f = S[15] + 8 + random.randint(0, 6)
        key_loc(d, [(f, (kx, ky, kz + 0.06)), (f + 10, (kx + sx * 0.08, ky, kz - 0.05)), (S[16], (kx + sx * 0.1, ky, 0.06))])
        pop(d, f, 5, S[16] + 2)
for k in range(3):
    pts = [(HBX + (k - 1) * 0.45 + 0.12 * math.sin(t * 1.4), HBY - 0.2, 1.0 + t * 0.32) for t in range(7)]
    st = tube("Stink", pts, [0.05, 0.06, 0.06, 0.055, 0.05, 0.04, 0.03], stink_m)
    st.location = (0, 0, 0)
    hide_until(st, S[15] + 12 + 2 * k)
    key_loc(st, [(S[15] + 12, (0, 0, -0.3)), (S[16], (0, 0, 0.4))])
    gone_at(st, S[16] + 2, 2)

# =================== line 16: autumn, they crawl inside to sleep ===================
WX, WZ = HX + 2.6, 1.4
crawl_path = [(WX - 1.6, fy - 3.0, 0.1), (WX - 0.6, fy - 1.0, 0.1), (WX, fy - 0.25, 0.15), (WX, fy - 0.14, 0.6), (WX, fy - 0.14, WZ - 0.5),
              (WX, fy - 0.1, WZ - 0.1)]
def path_at(u):
    u = max(0.0, min(1.0, u)) * (len(crawl_path) - 1)
    i = min(int(u), len(crawl_path) - 2); t = u - i
    a, b = crawl_path[i], crawl_path[i + 1]
    return tuple(a[k] + (b[k] - a[k]) * t for k in range(3))
for n in range(16):
    o = bug("Crawler", crawl_path[0], 0.13)
    o.rotation_euler = (0, 0, 0)
    keys = []
    dur = S[17] - S[16] + 6
    for s in range(0, 7):
        f = S[16] - 2 + int(dur * s / 6)
        u = (s / 6) * 1.25 - n * 0.075
        keys.append((f, path_at(u)))
    key_loc(o, keys)
    hide_at = S[16] - 2
    keyscale(o, [(0, 0.001), (hide_at - 1, 0.001), (hide_at, 0.13), (S[17] + 4, 0.13), (S[17] + 6, 0.001)])
    sw_ = S[16] - 2 + int(dur * (0.6 + 0.075 * n) / 1.25)
    o.rotation_euler = (0, 0, math.radians(180)); o.keyframe_insert("rotation_euler", frame=S[16] - 2)
    o.keyframe_insert("rotation_euler", frame=sw_ - 2)
    o.rotation_euler = (math.radians(-90), 0, math.radians(180)); o.keyframe_insert("rotation_euler", frame=sw_ + 2)
win_open = recenter(box("WinDark", (WX, fy - 0.075, WZ), (0.85, 0.02, 1.0), mat("WinDarkM", (0.03, 0.03, 0.05), 0.5)))
hide_until(win_open, S[16] - 2); gone_at(win_open, S[17] + 6, 2)
zzz = text("Zzz", "Zzz", (WX, fy - 0.3, WZ + 0.98), 0.45, mat("ZzzM", (1, 1, 1), 0.4, emit=(0.8, 0.9, 1), emit_strength=0.8), extrude=0.03)
pop(zzz, S[16] + 14, 6, S[17] + 4)
leafc = [mat("AutumnA", (0.95, 0.5, 0.1), 0.6), mat("AutumnB", (0.85, 0.25, 0.08), 0.6), mat("AutumnC", (0.95, 0.75, 0.15), 0.6)]
for i in range(30):
    p = (WX + random.uniform(-3.0, 3.0), fy - random.uniform(0.5, 3.5), random.uniform(3.0, 5.0))
    lf = sphere("AutumnLeaf", p, 0.09, random.choice(leafc), scale=(1.4, 1, 0.15), sub=1, smooth=False)
    key_loc(lf, [(S[16] - 4, p), (S[17] + 6, (p[0] + random.uniform(-0.8, 0.8), p[1], max(0.05, p[2] - random.uniform(2.6, 4.5))))])
    lf.rotation_euler = (0, 0, 0); lf.keyframe_insert("rotation_euler", frame=S[16] - 4)
    lf.rotation_euler = (random.uniform(-3, 3), random.uniform(-3, 3), random.uniform(-3, 3)); lf.keyframe_insert("rotation_euler", frame=S[17] + 6)
    hide_until(lf, S[16] - 4); gone_at(lf, S[17] + 8, 2)

# =================== line 0: hook — swarm streaming in over the garden ===================
for i in range(140):
    p0 = (random.uniform(-14, -6), random.uniform(-4, 6), random.uniform(2.5, 6))
    p1 = (random.uniform(-3, 7), random.uniform(6, 14), random.uniform(3, 7.5))
    o = bug("HookBug", p0, 0.18)
    key_loc(o, [(0, p0), (S[1] + 2, p1)])
    keyscale(o, [(0, 0.18), (S[1] - 2, 0.18), (S[1] + 2, 0.001)])
hook_hero = hero("HookHero", (-0.2, -0.6, 1.0), 0.5)
key_loc(hook_hero, [(0, (-3.4, -4.6, 3.4)), (S[1] - 6, (-0.4, -3.2, 1.6))])
hook_hero.rotation_euler = (math.radians(-15), 0, math.radians(60)); hook_hero.keyframe_insert("rotation_euler", frame=0)
hook_hero.rotation_euler = (math.radians(-10), 0, math.radians(20)); hook_hero.keyframe_insert("rotation_euler", frame=S[1] - 6)
gone_at(hook_hero, S[1] + 1, 3)

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

A = (SA[0], SA[1], PT + 0.05)
P = (PLX, PLY, T + 0.38)
cam_keys = [
    (0,          (-3.0, -9.5, 3.0),   (0.0, 6.0, 2.6)),            # hook: swarm streams in over the garden
    (S[1] - 6,   (0.6, -5.6, 2.2),    (0.2, 0.0, 1.3)),
    (S[1] + 4,   (SA[0] + 0.3, SA[1] - 0.95, PT + 0.42), A),        # one ladybug on the scale
    (S[2] - 2,   (SA[0] - 0.2, SA[1] - 0.8, PT + 0.34), A),
    (S[2] + 6,   (PLX + 0.25, PLY - 1.0, T + 0.55), P),             # munching aphids
    (S[3] - 2,   (PLX - 0.25, PLY - 0.85, T + 0.5), P),
    (S[3] + 8,   (TX + 0.3, TY - 2.4, T + 0.9), (TX + 0.2, TY + 0.4, T + 0.7)),   # a thousand
    (S[4] - 2,   (TX + 0.9, TY - 3.2, 1.6), (TX + 0.6, TY + 1.0, 1.6)),
    (S[4] + 10,  (2.5, -8.0, 3.2),    (0.6, 3.0, 2.4)),             # red cloud over the garden
    (S[5] - 2,   (1.0, -7.4, 3.0),    (0.8, 2.4, 2.0)),
    (S[5] + 8,   (2.6, -2.6, 1.6),    (BSX, BSY, 0.55)),            # 30 kg on the scale
    (S[6] - 2,   (1.2, -2.7, 1.5),    (BSX, BSY, 0.55)),
    (S[6] + 8,   (6.5, 4.0, 7.0),     (HX, HY, 5.0)),               # roof turns red
    (S[7] - 2,   (-1.5, 4.5, 7.5),    (HX, HY, 4.8)),
    (S[7] + 12,  (3.0, -6.0, 6.5),    (HX, HY - 1.0, 3.5)),         # one billion: house buried + storm
    (S[8] - 6,   (8.0, -7.0, 6.0),    (HX + 3.0, HY - 2.0, 3.0)),
    (S[8] + 4,   (10.2, -13.0, 5.0),  (PX - 0.2, PY, 2.2)),               # seesaw vs cement truck
    (S[9] - 2,   (8.8, -13.4, 4.8),   (PX - 0.4, PY, 2.0)),
    (S[9] + 4,   (0.0, 40.0, 320.0),  (0.0, 230.0, 0.0)),           # five soccer fields from the air
    (S[10] - 3,  (0.0, 70.0, 430.0),  (0.0, 300.0, 0.0)),
    (S[10] + 4,  (0.5, -4.5, 6.5),    (0.0, 6.0, 0.2)),             # a hundred houses
    (S[11] - 2,  (-1.0, -4.0, 7.0),   (0.0, 6.2, 0.4)),
    (S[11] + 6,  (-7.0, -8.0, 4.6),   (HEAP[0], HEAP[1], 1.6)),     # the aphid hill gets eaten
    (S[12] - 2,  (-9.5, -8.4, 4.2),   (HEAP[0], HEAP[1], 1.4)),
    (S[12] + 10, (-8.0, -5.6, 3.0),   (HEAP[0] + 1.8, HEAP[1] - 0.6, 1.0)),   # goodbye pests, you cheer
    (S[13] - 2,  (-7.0, -5.2, 2.8),   (HEAP[0] + 2.0, HEAP[1] - 0.8, 1.0)),
    (S[13] + 6,  (-4.0, -6.0, 2.0),   (SKY[0], SKY[1], SKY[2])),    # real swarm in the sky
    (S[14] - 4,  (-3.0, -4.0, 2.2),   (SKY[0] + 10, SKY[1], SKY[2] + 4)),
    (S[14] + 4,  (RX + 0.6, RY - 5.6, RZ + 0.6), (RX, RY, RZ + 0.2)),       # radar screen
    (S[15] - 3,  (RX - 0.6, RY - 5.0, RZ + 0.4), (RX, RY, RZ + 0.1)),
    (S[15] + 4,  (HBX + 1.0, HBY - 3.6, 1.6), (HBX, HBY, 0.5)),     # knee juice
    (S[16] - 3,  (HBX - 0.9, HBY - 3.2, 1.4), (HBX, HBY, 0.5)),
    (S[16] + 4,  (WX - 1.6, fy - 5.6, 2.6), (WX - 0.4, fy - 0.5, 1.2)),       # crawling inside for winter
    (S[17] - 3,  (WX + 0.4, fy - 4.6, 2.4), (WX, fy - 0.3, 1.4)),
    (S[17] + 8,  (1.0, -6.0, 3.5),    (HX, HY - 4.0, 2.5)),         # final: would you let them move in?
    (FRAMES - 1, (3.5, -9.5, 6.5),    (HX, HY - 2.0, 3.0)),
]

def overhead(cl, tl):
    dx, dy = cl[0] - tl[0], cl[1] - tl[1]
    hd = math.hypot(dx, dy)
    if cl[2] > 60 or hd > 40:
        return cl
    z = max(cl[2], tl[2] + 0.62 * hd)
    return (cl[0], cl[1], z)
cam_keys = [(f, overhead(cl, tl) if f not in (0,) else cl, tl) for f, cl, tl in cam_keys]
for f, cl, tl in cam_keys:
    cam.location = cl; cam.keyframe_insert("location", frame=f)
    target.location = tl; target.keyframe_insert("location", frame=f)

bpy.ops.wm.save_as_mainfile(filepath=f"{HERE}/scene.blend")
print("SCENE OK", FRAMES, S)
