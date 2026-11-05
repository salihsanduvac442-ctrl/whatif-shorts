# Day 11 — What if a storm cloud sucked you up?  Build: python3 episodes/011-storm-cloud/scene.py
# Reference style: base (helpers, lawn/soil, house, garden) copied from episodes/003-lift-million-ref/scene.py
import bpy, math, random, os, json
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
random.seed(11)
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
# ground split around a front cut-away swimming pool (pool cross-section is visible in the soil cut face)
PL, PR, PB, PD = -2.5, 2.5, 2.7, -2.7        # pool hole: x from PL to PR, y from FRONT_Y to PB, floor at PD
box("GroundL", ((-200 + PL) / 2, 26.2, -6.0), (200 + PL, 55.6, 12.0), grass_m)
box("GroundR", ((200 + PR) / 2, 26.2, -6.0), (200 - PR, 55.6, 12.0), grass_m)
box("GroundB", (0, (PB + 54.0) / 2, -6.0), (PR - PL, 54.0 - PB, 12.0), grass_m)
box("GroundBot", (0, (FRONT_Y + PB) / 2, (-12.0 + PD) / 2), (PR - PL, PB - FRONT_Y, 12.0 + PD), grass_m)
tile_m = stripe_mat("Tiles", (0.62, 0.86, 0.95), (0.42, 0.7, 0.86), axis="X", freq=14.0, thresh=0.8, rough=0.3)
tile_f = stripe_mat("TilesF", (0.62, 0.86, 0.95), (0.42, 0.7, 0.86), axis="Y", freq=14.0, thresh=0.8, rough=0.3)
box("PoolFloor", (0, (FRONT_Y + PB) / 2 - 0.05, PD + 0.05), (PR - PL, PB - FRONT_Y - 0.1, 0.1), tile_f)
box("PoolBack", (0, PB - 0.05, PD / 2), (PR - PL, 0.1, -PD), tile_m)
for sx in (-1, 1):
    box("PoolSide", (sx * (PR - 0.05), (FRONT_Y + PB) / 2 - 0.05, PD / 2), (0.1, PB - FRONT_Y - 0.1, -PD), tile_f)
rimc = mat("PoolRimM", (0.92, 0.9, 0.84), 0.7)
box("RimB", (0, PB + 0.2, 0.04), (PR - PL + 0.8, 0.4, 0.1), rimc, bevel=0.03)
for sx in (-1, 1):
    box("RimS", (sx * (PR + 0.2), (FRONT_Y + PB) / 2 + 0.2, 0.04), (0.4, PB - FRONT_Y + 0.4, 0.1), rimc, bevel=0.03)
WTOP = -0.15
water_m = mat("Water", (0.3, 0.72, 0.95), 0.05, emit=(0.15, 0.5, 0.8), emit_strength=0.15)
water_m.node_tree.nodes["Principled BSDF"].inputs["Alpha"].default_value = 0.32
water = box("Water", (0, (FRONT_Y + PB) / 2 - 0.06, (WTOP + PD + 0.1) / 2), (PR - PL - 0.2, PB - FRONT_Y - 0.12, WTOP - PD - 0.1), water_m)
water.visible_shadow = False
under_m = mat("Underside", (0.3, 0.2, 0.12), 0.9)
bpy.ops.mesh.primitive_plane_add(size=1200, location=(0, 0, -12.05))
bpy.context.object.data.materials.append(under_m)
far = grass_m
bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 0, -0.003))
fp = bpy.context.object; fp.scale = (400000, 400000, 1); fp.location = (0, 200050, -0.008)
fp.data.materials.append(far)
stone_m = mat("Stone", (0.7, 0.66, 0.6), 0.8)
for i in range(30):
    x = random.uniform(-30, 30)
    if abs(x) < 3.2:
        continue
    sphere("Peb", (x, FRONT_Y - 0.02, random.uniform(-5.6, -0.6)), random.uniform(0.12, 0.3),
           stone_m, scale=(1.3, 0.5, 0.8), sub=1, smooth=False)
for i in range(12):
    sphere("Peb", (random.uniform(-2.4, 2.4), FRONT_Y - 0.02, random.uniform(-5.6, -3.2)), random.uniform(0.12, 0.25),
           stone_m, scale=(1.3, 0.5, 0.8), sub=1, smooth=False)

for sx in (-1, 1):   # lawn beside the diorama (no void at the sides)
    bpy.ops.mesh.primitive_plane_add(size=1, location=(sx * 100016, 26.2, -0.003))
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
for (x, y) in [(-14, 1.5), (-8, 22), (8.8, 24), (26, 30), (12, 36)]:
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
def overhead(cl, tl):
    dx, dy = cl[0] - tl[0], cl[1] - tl[1]
    hd = math.hypot(dx, dy)
    if cl[2] > 60 or hd > 40 or cl[0] < -5e5:
        return cl
    if cl[2] < 0 and cl[1] < FRONT_Y - 1.0:     # front view through the pool cut face: keep it level
        return cl
    z = max(cl[2], tl[2] + 0.62 * hd)
    return (cl[0], cl[1], z)
LIFT = math.atan(0.36 * math.tan(math.atan(18 / 26)))   # subject ~68% down the frame
def aim(cl, subj):
    d = Vector(subj) - Vector(cl)
    ax = d.cross(Vector((0, 0, 1))).normalized()
    return tuple(Vector(cl) + Quaternion(ax, LIFT) @ d)
TANV = 18 / 26
def SP(view, D, v, u=0.0):
    """world point at distance D in front of the camera of view=(cam, subject) that lands at screen
    height v (0 = top, 1 = bottom) and horizontal offset u (-0.5..0.5 of the width)"""
    cl = Vector(overhead(*view)); t = Vector(aim(overhead(*view), view[1]))
    fwd = (t - cl).normalized()
    right = fwd.cross(Vector((0, 0, 1))).normalized(); up = right.cross(fwd)
    d = fwd + up * ((0.5 - v) * 2 * TANV) + right * (u * 2 * TANV * 9 / 16)
    return tuple(cl + d.normalized() * D)
def CL(view):
    return overhead(*view)
def keyscale(o, keys):
    for f, s in keys:
        o.scale = (s,) * 3 if not isinstance(s, tuple) else s
        o.keyframe_insert("scale", frame=f)
def keyrot(o, keys):
    for f, r in keys:
        o.rotation_euler = r; o.keyframe_insert("rotation_euler", frame=f)

lab_m = mat("LabelM", (1.0, 0.85, 0.2), 0.4, emit=(1.0, 0.8, 0.2), emit_strength=0.9)
white_lab = mat("LabW", (1, 1, 1), 0.4, emit=(1, 1, 1), emit_strength=0.8)
red_lab = mat("LabR", (0.95, 0.1, 0.08), 0.4, emit=(1.0, 0.1, 0.05), emit_strength=1.2)
pink_lab = mat("LabP", (1.0, 0.45, 0.55), 0.4, emit=(1.0, 0.4, 0.5), emit_strength=1.1)
spark_m = glow_mat("Spark", (1.0, 0.95, 0.7), 5.0)
eyew = mat("EyeW", (1, 1, 1), 0.3)
eyeb = mat("EyeB", (0.03, 0.03, 0.04), 0.3)

def label(name, body, loc, size, m_, f_in, f_out, face=None):
    t = text(name, body, loc, size, m_, extrude=size * 0.08)
    if face is not None:
        dx, dy = face[0] - loc[0], face[1] - loc[1]
        t.rotation_euler = (math.radians(90), 0, math.atan2(dx, -dy))
    pop(t, f_in, 5, f_out)
    return t
def burst(loc, f, n=10, r=0.12, size=0.012, f_out=None, material=None):
    for k in range(n):
        a = k / n * 6.283
        s_ = sphere("Burst", (loc[0] + r * math.cos(a), loc[1] - 0.05, loc[2] + r * math.sin(a)), size, material or spark_m, sub=1)
        pop(s_, f, 3, f_out if f_out else f + 10)

# =====================================================================================
# Day 11 — What if a storm cloud sucked you up?   (rare accident, true story, cartoon diorama)
# Facts: Feb 2007, a paraglider pilot preparing for the world championships near Manilla (NSW, Australia)
#   was pulled into a thunderstorm by its updraft to ~9,946 m (higher than Everest, 8,849 m; airliners
#   cruise ~9-12 km). Hail and lightning, temperatures around -50 C, she lost consciousness from lack of
#   oxygen (roughly 30-60 min), was covered in ice, her GPS/vario logged the climb, she woke still in the
#   cloud, steered down and landed hours later (~3.5 h after launch), frostbitten but alive.
#   She is not named or shown realistically — generic cartoon pilot.
# =====================================================================================
lab_m = mat("LabelM", (1.0, 0.85, 0.2), 0.4, emit=(1.0, 0.8, 0.2), emit_strength=0.9)
white_lab = mat("LabW", (1, 1, 1), 0.4, emit=(1, 1, 1), emit_strength=0.8)
red_lab = mat("LabR", (0.95, 0.1, 0.08), 0.4, emit=(1.0, 0.1, 0.05), emit_strength=1.2)
blue_lab = mat("LabB", (0.4, 0.8, 1.0), 0.4, emit=(0.35, 0.75, 1.0), emit_strength=1.2)
grey_lab = mat("LabG", (0.75, 0.75, 0.78), 0.4, emit=(0.7, 0.7, 0.75), emit_strength=0.7)
spark_m = glow_mat("Spark", (1.0, 0.95, 0.7), 5.0)
eyew = mat("EyeW", (1, 1, 1), 0.3)
eyeb = mat("EyeB", (0.03, 0.03, 0.04), 0.3)
bub_m = mat("Bubble", (0.85, 0.95, 1.0), 0.05, emit=(0.8, 0.95, 1.0), emit_strength=0.6)

def fit(body, D, size):
    return min(size, (0.8 if D <= 3.0 else 0.85) * D / max(len(body), 4))
def parent_to(o, p):
    bpy.context.view_layer.update()
    mw = o.matrix_world.copy()
    o.parent = p
    o.matrix_parent_inverse = p.matrix_world.inverted()
def center(o):
    bpy.ops.object.select_all(action='DESELECT')
    o.select_set(True); bpy.context.view_layer.objects.active = o
    bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')

# ---------------- people ----------------
def alpha_mat(name, color, rough=0.7):
    m = mat(name, color, rough)
    return m
def person(name, base, K, shirt, pants, skin, hair, face_y=-1):
    """cartoon person standing at base (feet), facing -y. returns group, parts dict"""
    PX_, PY_, PZ_ = base
    g = group(name, base)
    def P(dx, dy, dz):
        return (PX_ + dx * K, PY_ + dy * K, PZ_ + dz * K)
    d = {"P": P, "arms": [], "legs": [], "eyes": [], "pupils": []}
    allp = []
    for sx in (-1, 1):
        lg = group(name + "LegG", P(sx * 0.13, 0, 0.78))
        attach([tube(name + "Leg", [P(sx * 0.13, 0, 0.8), P(sx * 0.14, 0, 0.08)], [0.1 * K, 0.09 * K], pants),
                box(name + "Shoe", P(sx * 0.14, -0.06, 0.05), (0.17 * K, 0.3 * K, 0.1 * K), shoe_m, bevel=0.03)], lg)
        d["legs"].append(lg)
        ag = group(name + "ArmG", P(sx * 0.3, 0, 1.33))
        attach([tube(name + "Arm", [P(sx * 0.3, 0, 1.35), P(sx * 0.38, -0.03, 1.05), P(sx * 0.38, -0.06, 0.8)], [0.07 * K] * 3, shirt),
                sphere(name + "Hand", P(sx * 0.38, -0.06, 0.76), 0.068 * K, skin, sub=2)], ag)
        d["arms"].append(ag)
        e = sphere(name + "EyeW", P(sx * 0.085, -0.21, 1.72), 0.055 * K, eyew, scale=(1, 0.6, 1.2), sub=2)
        pu = sphere(name + "EyeB", P(sx * 0.085, -0.25, 1.72), 0.028 * K, eyeb, sub=1)
        d["eyes"].append(e); d["pupils"].append(pu); allp += [e, pu]
    torso = sphere(name + "Torso", P(0, 0, 1.1), 1.0, shirt, scale=(0.3 * K, 0.22 * K, 0.4 * K), sub=3)
    head = sphere(name + "Head", P(0, 0, 1.68), 0.25 * K, skin, sub=3)
    hr = sphere(name + "Hair", P(0, 0.04, 1.81), 0.24 * K, hair, scale=(1.05, 1.0, 0.55), sub=2)
    sm = tube(name + "Smile", [P(-0.08, -0.23, 1.6), P(0, -0.26, 1.56), P(0.08, -0.23, 1.6)], [0.014 * K] * 3, eyeb)
    d.update(torso=torso, head=head, smile=sm)
    attach(allp + [torso, head, hr, sm] + d["arms"] + d["legs"], g)
    return g, d

shoe_m = mat("Shoe", (0.15, 0.15, 0.18), 0.6)
skin_y = mat("SkinY", (0.95, 0.74, 0.58), 0.6)
shirt_y = mat("ShirtY", (0.95, 0.35, 0.25), 0.7)       # red swim shirt
pants_y = mat("PantsY", (0.2, 0.3, 0.6), 0.8)
hair_y = mat("HairY", (0.28, 0.16, 0.07), 0.8)

# =====================================================================================
# Day 11 episode
# =====================================================================================
NL = len(S)
def fr_line(f):
    i = 0
    while i + 1 < NL and f >= S[i + 1]:
        i += 1
    return i
def line_end(i):
    return (S[i + 1] - 1) if i + 1 < NL else FRAMES - 1

hair_w = mat("HairW", (0.55, 0.32, 0.12), 0.8)
skin_w = mat("SkinW", (0.95, 0.74, 0.58), 0.6)
jacket = mat("Jacket", (0.15, 0.55, 0.95), 0.6)          # blue flight suit
pants_w = mat("PantsW", (0.15, 0.17, 0.25), 0.8)
helm_m = mat("Helmet", (1.0, 0.85, 0.1), 0.35, emit=(1.0, 0.8, 0.1), emit_strength=0.25)
can1 = mat("Canopy1", (1.0, 0.42, 0.05), 0.5, emit=(1.0, 0.35, 0.03), emit_strength=0.35)
can2 = mat("Canopy2", (1.0, 0.82, 0.1), 0.5, emit=(1.0, 0.75, 0.1), emit_strength=0.35)
line_m = mat("Lines", (0.95, 0.95, 0.95), 0.5)
harn_m = mat("Harness", (0.2, 0.2, 0.24), 0.6)

# ---------------- paraglider: group origin at the pilot's hips ----------------
PG = group("PG", (0, 0, 0))
KP = 0.9
pilot, PL_ = person("Pilot", (0, 0, -0.82 * KP), KP, jacket, pants_w, skin_w, hair_w)
PP = PL_["P"]
helmet = sphere("HelmetS", PP(0, 0.02, 1.76), 0.29 * KP, helm_m, scale=(1.0, 1.05, 0.8), sub=3)
pony = sphere("Pony", PP(0, 0.26, 1.55), 0.11 * KP, hair_w, scale=(0.8, 1.0, 1.8), sub=2)
seat = box("Seat", (0, 0.12, -0.05), (0.62, 0.55, 0.32), harn_m, bevel=0.06)
for o in (helmet, pony):
    parent_to(o, pilot)
canopy = group("Canopy", (0, 0, 0))
cparts = []
R_ = 3.0; CZ = 1.0
NC = 11
for k in range(NC):
    a = math.radians(-72 + 144 * k / (NC - 1))
    x, z = R_ * math.sin(a), CZ + R_ * math.cos(a)
    c = box("Cell", (x, 0.2, z), (0.82, 1.5, 0.28), can1 if k % 2 == 0 else can2, bevel=0.05, rot=(0, a, 0))
    cparts.append(c)
    if k % 2 == 0:
        cparts.append(tube("Line", [(x * 0.92, 0.2, z - 0.15), (0.0 + (0.18 if x > 0 else -0.18), 0.0, 0.85)], [0.012, 0.012], line_m))
attach(cparts, canopy)
parent_to(seat, PG); parent_to(pilot, PG); parent_to(canopy, PG)
# arms up holding the brakes
for a_, sgn in zip(PL_["arms"], (1, -1)):
    a_.rotation_euler = (0, sgn * 2.5, 0)

# ---------------- flight path (keys at line starts) ----------------
LAND = (-5.6, 0.6, 0.74)
GK = [(0, (-4.5, 6.0, 5.0)), (S[1], (-2.0, 5.0, 6.4)), (S[2], (0.0, 4.2, 7.4)), (S[3], (0.6, 4.0, 11.0)),
      (S[4], (0.0, 4.0, 46.0)), (S[5], (0.0, 4.0, 55.0)), (S[6], (0.5, 4.0, 62.0)), (S[7], (0.0, 4.0, 69.0)),
      (S[8], (-0.4, 4.0, 76.0)), (S[9], (0.0, 4.0, 83.0)), (S[10], (0.0, 4.0, 91.0)), (S[11], (0.0, 4.0, 96.5)),
      (S[12], (0.0, 4.0, 99.4)), (S[13], (0.3, 4.0, 99.5)), (S[14], (0.0, 4.0, 99.0)), (S[15], (0.0, 4.0, 60.0)),
      (S[16], (-1.5, 3.0, 24.0)), (S[16] + 32, LAND), (FRAMES, LAND)]
key_loc(PG, GK)
# sway / shake
for f in range(0, FRAMES, 6):
    i = fr_line(f)
    amp = 0.03 if i in (0, 1, 16, 17) else (0.16 if i in (2, 3, 5, 6, 14) else 0.08)
    PG.rotation_euler = (random.uniform(-amp, amp) * 0.5, random.uniform(-amp, amp), 0)
    PG.keyframe_insert("rotation_euler", frame=f)
for fc in fcurves(PG) if False else []:
    pass

def fcurves(o_):
    ad = o_.animation_data
    if ad is None or ad.action is None:
        return []
    try:
        return list(ad.action.fcurves)
    except AttributeError:
        from bpy_extras import anim_utils
        return list(anim_utils.action_get_channelbag_for_slot(ad.action, ad.action_slot).fcurves)
for fc in fcurves(PG):
    if fc.data_path == "location":
        for kp in fc.keyframe_points:
            kp.interpolation = 'LINEAR'
_gp_cache = {}
def gp(f):
    f = int(round(f))
    if f not in _gp_cache:
        sc.frame_set(f)
        _gp_cache[f] = Vector(PG.matrix_world.translation)
    return _gp_cache[f]

# ---------------- giant storm cloud (cumulonimbus) behind the garden ----------------
cl_w = mat("CloudW", (0.97, 0.97, 1.0), 0.95, emit=(0.9, 0.92, 1.0), emit_strength=0.25)
cl_g = mat("CloudG", (0.5, 0.52, 0.6), 0.95)
cl_d = mat("CloudD", (0.3, 0.32, 0.4), 0.95)
CC = (0.0, 66.0)
for zi, z in enumerate(range(14, 112, 8)):
    rr = 26 + 3 * math.sin(z * 0.07)
    m_ = cl_d if z < 60 else (cl_g if z < 100 else cl_w)
    for k in range(11):
        a = k / 11 * 6.283 + zi * 0.4
        sphere("CB", (CC[0] + rr * math.cos(a), CC[1] + rr * math.sin(a) * 0.8, z + random.uniform(-2, 2)),
               random.uniform(9, 12), m_, sub=2)
for k in range(22):           # anvil top
    a = k / 22 * 6.283
    rr = random.uniform(30, 62)
    sphere("CA", (CC[0] + rr * math.cos(a), CC[1] + 10 + rr * math.sin(a) * 0.6, 118 + random.uniform(-3, 3)),
           random.uniform(10, 14), cl_w, scale=(1.4, 1.2, 0.55), sub=2)
for k in range(9):            # dark base
    sphere("CDb", (CC[0] + random.uniform(-30, 30), CC[1] - 20 + random.uniform(-6, 6), 12), random.uniform(8, 11),
           cl_d, scale=(1.5, 1.0, 0.6), sub=2)
# rain curtain under the cloud base
rain_m = mat("Rain", (0.55, 0.6, 0.7), 0.9)
for k in range(28):
    x = random.uniform(-28, 28)
    box("Rain", (x, CC[1] - 14 + random.uniform(-4, 6), 6), (0.12, 0.12, 12), rain_m)

# puffs inside the cloud along her climb (frame her at the sides / behind)
puffs = []
for k in range(16):
    z = 38 + k * 4.0
    sx = 1 if k % 2 else -1
    p = sphere("Puff", (sx * random.uniform(12.0, 15.0), random.uniform(4.0, 14.0), z), random.uniform(3.0, 4.2),
               cl_d, scale=(1.2, 1.0, 0.85), sub=2)
    puffs.append(p)
for p in puffs:
    s0 = tuple(p.scale)
    keyscale(p, [(0, 0.001), (S[4] - 2, 0.001), (S[4] + 4, s0), (S[9] - 1, s0), (S[9], 0.001), (S[13] - 1, 0.001), (S[13], s0), (S[16] - 2, s0), (S[16], 0.001)])

# ---------------- sky: blue -> dark storm -> blue again ----------------
def sky(f, c0, c1, st):
    el[0].color = (*c0, 1); el[0].keyframe_insert("color", frame=f)
    el[1].color = (*c1, 1); el[1].keyframe_insert("color", frame=f)
    bg.inputs["Strength"].default_value = st; bg.inputs["Strength"].keyframe_insert("default_value", frame=f)
BLUE = ((0.78, 0.9, 1.0), (0.22, 0.52, 0.95), 0.85)
GREYB = ((0.55, 0.6, 0.7), (0.3, 0.36, 0.5), 0.75)
DARK = ((0.26, 0.28, 0.36), (0.12, 0.13, 0.2), 0.7)
sky(0, *BLUE); sky(S[3], *BLUE); sky(S[3] + 18, *GREYB); sky(S[4], *GREYB); sky(S[4] + 6, *DARK)
sky(S[15] - 1, *DARK); sky(S[16] - 4, *GREYB); sky(S[16] + 10, *BLUE)
# lightning flashes: bright sky spikes
FLASH = [S[6] + 1, S[6] + 9, S[6] + 19, S[7] - 3, S[5] + 14, S[13] + 6]
for f in FLASH:
    sky(f - 1, *DARK); sky(f, (0.9, 0.9, 1.0), (0.6, 0.62, 0.8), 2.2); sky(f + 2, *DARK)

# ---------------- HUD labels: children of the camera (always upper part, never behind captions) ----------------
bpy.ops.object.camera_add()
cam = bpy.context.object
sc.camera = cam
cam.data.lens = 26
cam.data.sensor_fit = 'VERTICAL'
cam.data.sensor_height = 36
cam.data.clip_start = 0.02
cam.data.clip_end = 3.0e6
TV = 18 / 26
DH = 6.0
def hud(name, body, v, size, m_, f_in, f_out, u=0.0, D=DH):
    size = min(size, 0.85 * 2 * TV * D * 9 / 16 / (0.66 * max(len(body), 3)))
    t = text(name, body, (0, 0, 0), size, m_, rot=(0, 0, 0), extrude=size * 0.06)
    t.parent = cam
    t.location = (u * 2 * TV * D * 9 / 16, (0.5 - v) * 2 * TV * D, -D)
    t.visible_shadow = False
    pop(t, f_in, 5, f_out)
    sh = text(name + "Sh", body, (0, 0, 0), size, shadow_m, rot=(0, 0, 0), extrude=size * 0.06)
    sh.parent = cam
    sh.location = (t.location[0] + size * 0.05, t.location[1] - size * 0.06, -D - 0.03)
    pop(sh, f_in, 5, f_out)
    return t
shadow_m = mat("ShadowM", (0.0, 0.0, 0.0), 0.9)
green_lab = mat("LabGr", (0.3, 1.0, 0.4), 0.4, emit=(0.3, 1.0, 0.4), emit_strength=1.2)
orange_lab = mat("LabO", (1.0, 0.5, 0.1), 0.4, emit=(1.0, 0.45, 0.05), emit_strength=1.2)

hud("H0a", "STORM CLOUD", 0.25, 0.5, white_lab, 3, S[1])
hud("H0b", "SUCKED UP?", 0.33, 0.5, lab_m, 8, S[1])
hud("H1a", "TRUE STORY", 0.25, 0.5, white_lab, S[1] + 2, S[2])
hud("H1b", "2007", 0.33, 0.7, lab_m, S[1] + 6, S[2])
hud("H2a", "AUSTRALIA", 0.25, 0.5, white_lab, S[2] + 2, S[3])
hud("H2b", "UPDRAFT!", 0.33, 0.55, blue_lab, S[2] + 8, S[3])
hud("H3a", "UP LIKE AN", 0.25, 0.45, white_lab, S[3] + 1, S[4])
hud("H3b", "ELEVATOR", 0.33, 0.55, lab_m, S[3] + 4, S[4])
hud("H4", "INSIDE THE CLOUD", 0.29, 0.5, white_lab, S[4] + 2, S[5])
hud("H5", "HAIL!", 0.29, 0.8, blue_lab, S[5] + 2, S[6])
hud("H6", "LIGHTNING!", 0.29, 0.6, lab_m, S[6] + 2, S[7])
hud("H7", "-50°C", 0.29, 0.85, blue_lab, S[7] + 2, S[8], u=-0.1)
hud("H8a", "NO OXYGEN", 0.25, 0.5, white_lab, S[8] + 1, S[9])
hud("H8b", "BLACKOUT", 0.33, 0.55, red_lab, S[8] + 10, S[9])
hud("H9a", "MT EVEREST", 0.25, 0.5, white_lab, S[9] + 2, S[10])
hud("H9b", "8,849 m", 0.33, 0.6, lab_m, S[9] + 5, S[10])
hud("H10a", "9,946 m", 0.29, 0.75, lab_m, S[10] + 2, S[11])
hud("H10b", "~10 KM UP", 0.36, 0.45, white_lab, S[10] + 8, S[11])
hud("H11", "GPS TRACK", 0.8, 0.5, lab_m, S[11] + 2, S[12])
hud("H12a", "PASSENGER JET", 0.25, 0.42, white_lab, S[12] + 2, S[13])
hud("H12b", "~10 KM", 0.33, 0.6, lab_m, S[12] + 6, S[13])
hud("H13", "FROZEN!", 0.29, 0.7, blue_lab, S[13] + 2, S[14])
hud("H14", "DROP!", 0.29, 0.8, red_lab, S[14] + 2, S[15])
hud("H15a", "AWAKE!", 0.25, 0.6, green_lab, S[15] + 2, S[16])
hud("H15b", "STEERING DOWN", 0.33, 0.42, white_lab, S[15] + 6, S[16])
hud("H16", "ALIVE!", 0.29, 0.85, green_lab, S[16] + 16, S[17])
hud("H17", "WOULD YOU?", 0.29, 0.6, lab_m, S[17] + 3, FRAMES + 5)

# ---------------- updraft arrows (hook, lines 2-3) ----------------
arr_m = glow_mat("Arrow", (0.55, 0.95, 1.0), 3.0)
def arrow(name):
    g = group(name, (0, 0, 0))
    attach([cyl(name + "S", (0, 0, 0), 0.12, 1.2, arr_m, verts=10), cyl(name + "H", (0, 0, 0.85), 0.3, 0.5, arr_m, verts=10, r2=0.0)], g)
    return g
for k in range(10):
    a_ = arrow("Up%d" % k)
    dx = (k % 5 - 2) * 1.2 + random.uniform(-0.3, 0.3)
    dy = random.uniform(-1.0, 1.0)
    keys = []
    for seg in range(3):
        f0 = [8, S[2] + 2, S[3]][seg] + (k % 4) * 3
        f1 = f0 + 14
        g0, g1 = gp(f0), gp(f1)
        keys += [(f0, 0.001, g0 + Vector((dx, dy, -4.0))), (f0 + 1, 1.0, g0 + Vector((dx, dy, -4.0))),
                 (f1, 1.0, g1 + Vector((dx, dy, -0.8))), (f1 + 1, 0.001, g1 + Vector((dx, dy, -0.8)))]
    a_.scale = (0.001,) * 3; a_.keyframe_insert("scale", frame=0)
    for f, s_, p in keys:
        a_.scale = (s_,) * 3; a_.keyframe_insert("scale", frame=f)
        a_.location = p; a_.keyframe_insert("location", frame=f)

# ---------------- wind streaks while she rockets up / drops ----------------
streak_m = mat("Streak", (1, 1, 1), 0.5, emit=(1, 1, 1), emit_strength=1.0)
for k in range(16):
    st = box("Streak", (0, 0, 0), (0.05, 0.05, 3.0), streak_m)
    dx = random.choice((-1, 1)) * random.uniform(2.6, 5.0); dy = random.uniform(-2, 3)
    keys = [(0, 0.001, Vector((0, 0, 0)))]
    for (fa, fb, dirz) in [(S[3], S[4], -1), (S[14], S[15], 1), (S[15], S[16], 1)]:
        f = fa + k % 5
        while f + 8 < fb:
            g0 = gp(f); g1 = gp(f + 8)
            off = random.uniform(-2, 3)
            keys += [(f, 0.001, g0 + Vector((dx, dy, 6 * -dirz + off))), (f + 1, 1.0, g0 + Vector((dx, dy, 6 * -dirz + off))),
                     (f + 7, 1.0, g1 + Vector((dx, dy, 6 * dirz + off))), (f + 8, 0.001, g1 + Vector((dx, dy, 6 * dirz + off)))]
            f += 10
    for f, s_, p in keys:
        st.scale = (s_,) * 3; st.keyframe_insert("scale", frame=f)
        st.location = p; st.keyframe_insert("location", frame=f)

# ---------------- hail (line 5) ----------------
hail_m = mat("Hail", (0.9, 0.97, 1.0), 0.15, emit=(0.8, 0.9, 1.0), emit_strength=0.8)
for k in range(34):
    h_ = sphere("Hail", (0, 0, 0), random.uniform(0.25, 0.4), hail_m, sub=1, smooth=False)
    f0 = S[5] + (k * 31) % max(S[7] - S[5] - 12, 1)
    dx = random.uniform(-4.5, 4.5); dy = random.uniform(-1.5, 3.0)
    hits = abs(dx) < 2.6 and k % 2 == 0
    g0 = gp(f0)
    if hits:
        g1 = gp(f0 + 6); g2 = gp(f0 + 14)
        top = CZ + R_ * math.cos(math.asin(min(abs(dx) / R_, 0.99)))
        keys = [(f0, g0 + Vector((dx, 0.2, 9.0))), (f0 + 6, g1 + Vector((dx, 0.2, top + 0.3))),
                (f0 + 14, g2 + Vector((dx * 2.2 + math.copysign(2.0, dx), -1.5, top - 2.5)))]
    else:
        g1 = gp(f0 + 12)
        keys = [(f0, g0 + Vector((dx, dy, 9.0))), (f0 + 12, g1 + Vector((dx, dy, -6.0)))]
    key_loc(h_, keys)
    keyscale(h_, [(0, 0.001), (f0 - 1, 0.001), (f0, 1.0), (keys[-1][0] - 1, 1.0), (keys[-1][0], 0.001)])
    if hits:
        for c_ in range(5):
            pass
# hail hits: tiny white bursts on the canopy
for k, f in enumerate(range(S[5] + 6, S[6] + 6, 5)):
    g = gp(f)
    burst(tuple(g + Vector(((k % 3 - 1) * 1.6, 0.0, 4.3 - abs(k % 3 - 1) * 0.5))), f, n=8, r=0.35, size=0.07, f_out=f + 5, material=hail_m)

# ---------------- lightning bolts (line 6, plus a couple later) ----------------
bolt_m = glow_mat("Bolt", (1.0, 0.8, 0.15), 3.5)
def bolt(name, top, length=13.0):
    pts = [Vector(top)]
    for k in range(7):
        pts.append(pts[-1] + Vector((random.uniform(-1.4, 1.4), random.uniform(-0.3, 0.3), -length / 7)))
    return tube(name, [tuple(p) for p in pts], [0.28] * len(pts), bolt_m)
BOLTS = [(S[6] + 1, (-5.0, 5.0, 9.0)), (S[6] + 9, (5.0, 5.0, 8.5)), (S[6] + 19, (-6.5, 6.0, 10.0)),
         (S[7] - 3, (4.5, 4.0, 9.0)), (S[5] + 14, (5.5, 6.0, 9.0)), (S[13] + 6, (-5.5, 5.0, 9.0))]
for k, (f, off) in enumerate(BOLTS):
    g = gp(f)
    b_ = bolt("Bolt%d" % k, tuple(g + Vector(off)))
    keyscale(b_, [(0, 0.0), (f - 1, 0.0), (f, 1.0), (f + 3, 1.0), (f + 4, 0.0)])
    # scaling a curve object about its origin (world 0) would move it: use hide via scale on a parent group
    b_.animation_data_clear(); b_.scale = (1, 1, 1)
    grp = group("BoltG%d" % k, tuple(g + Vector(off)))
    attach([b_], grp)
    keyscale(grp, [(0, 0.001), (f - 1, 0.001), (f, 1.0), (f + 3, 1.0), (f + 4, 0.001)])

# ---------------- thermometer (HUD, line 7) ----------------
th = group("Thermo", (0, 0, 0))
glass = mat("Glass", (0.95, 0.97, 1.0), 0.2, emit=(1, 1, 1), emit_strength=0.4)
tparts = [cyl("TTube", (0, 0, 0.35), 0.11, 1.5, glass, verts=16), sphere("TBulb", (0, 0, -0.5), 0.22, red_lab, sub=2)]
col_g = group("TCol", (0, 0, -0.4))
colb = cyl("TColB", (0, 0, 0.3), 0.06, 1.3, red_lab, verts=12)
attach([colb], col_g)
attach(tparts, th)
th.parent = cam; th.location = (1.25, 1.6, -DH); th.rotation_euler = (0, 0, 0)
col_g.parent = th; col_g.location = (0, 0, -0.4)
keyscale(col_g, [(S[7], 1.0), (S[7] + 20, (1, 1, 0.08))])
pop(th, S[7] + 1, 5, S[8], s=0.7)
# frost crystals drifting past
frost_m = mat("Frost", (0.8, 0.95, 1.0), 0.1, emit=(0.7, 0.9, 1.0), emit_strength=2.0)
for k in range(18):
    f0 = S[7] + k
    g = gp(f0)
    p0 = g + Vector((random.uniform(-4, 4), random.uniform(-2.5, 0.5), random.uniform(-2, 5)))
    c_ = sphere("FrostC", tuple(p0), 0.1, frost_m, scale=(0.5, 0.5, 1.8), sub=1, smooth=False)
    c_.rotation_euler = (random.uniform(0, 3), random.uniform(0, 3), 0)
    key_loc(c_, [(f0, p0), (S[8] + 6, gp(S[8] + 6) + (p0 - g) + Vector((random.uniform(-1, 1), 0, -1)))])
    keyscale(c_, [(0, 0.001), (f0 - 1, 0.001), (f0 + 2, (0.5, 0.5, 1.8)), (S[8] + 5, (0.5, 0.5, 1.8)), (S[8] + 6, 0.001)])

# ---------------- blackout: eyes close, head tilts (S8 .. S15) ----------------
for e in PL_["eyes"] + PL_["pupils"]:
    s0 = tuple(e.scale)
    keyscale(e, [(S[8] + 8, s0), (S[8] + 12, (s0[0], s0[1], s0[2] * 0.12)), (S[15] + 2, (s0[0], s0[1], s0[2] * 0.12)), (S[15] + 6, s0)])
keyrot(pilot, [(S[8] + 8, (0, 0, 0)), (S[8] + 14, (math.radians(-14), math.radians(16), 0)), (S[15] + 1, (math.radians(-14), math.radians(16), 0)),
               (S[15] + 6, (0, 0, 0))])
for a_, sgn in zip(PL_["arms"], (1, -1)):
    keyrot(a_, [(S[8] + 8, (0, sgn * 2.5, 0)), (S[8] + 14, (0, sgn * 0.5, 0)), (S[15] + 2, (0, sgn * 0.5, 0)), (S[15] + 7, (0, sgn * 2.5, 0)),
                (S[15] + 14, (0, sgn * 2.1, 0)), (S[15] + 20, (0, sgn * 2.6, 0))])
# O2 bubbles fading
o2_m = mat("O2", (0.4, 0.8, 1.0), 0.3, emit=(0.4, 0.8, 1.0), emit_strength=1.4)
for k in range(5):
    f0 = S[8] + k * 3
    g = gp(f0)
    o_ = text("O2_%d" % k, "O2", tuple(g + Vector(((k - 2) * 0.9, -1.2, 2.2))), 0.4, o2_m)
    key_loc(o_, [(f0, g + Vector(((k - 2) * 0.9, -1.2, 2.2))), (S[9], gp(S[9]) + Vector(((k - 2) * 1.3, -1.2, 3.4)))])
    keyscale(o_, [(0, 0.001), (f0 - 1, 0.001), (f0 + 3, 1.0), (S[8] + 16, 1.0), (S[9], 0.001)])

# ---------------- Mount Everest comparison (line 9) ----------------
rock_m = mat("Rock", (0.45, 0.4, 0.38), 0.9)
snow_m = mat("Snow", (0.97, 0.98, 1.0), 0.6, emit=(0.9, 0.95, 1.0), emit_strength=0.15)
EV = group("Everest", (20.0, 24.0, 0.0))
evp = [cyl("EvRock", (20.0, 24.0, 44.25), 30.0, 88.5, rock_m, verts=7, r2=0.0),
       cyl("EvSnow", (20.0, 24.0, 74.0), 10.25, 29.5, snow_m, verts=7, r2=0.0)]
evp[1].scale = (1.03, 1.03, 1.0)
attach(evp, EV)
key_loc(EV, [(0, (20.0, 24.0, -95.0)), (S[9] - 1, (20.0, 24.0, -95.0)), (S[9] + 9, (20.0, 24.0, 0.0))])
gone_at(EV, S[11], 1)
flag = box("EvFlag", (20.0, 24.0, 89.6), (0.08, 0.08, 2.2), white_lab)
parent_to(flag, EV)

# ---------------- GPS track (line 11): glowing dots along her climb ----------------
dot_m = glow_mat("GPSDot", (1.0, 0.85, 0.15), 4.0)
DOTS = 40
for k in range(DOTS):
    f = int(S[2] + (S[11] - S[2]) * k / (DOTS - 1))
    p = gp(f)
    d_ = sphere("GPS", tuple(p + Vector((0, 0, -0.6))), 1.3, dot_m, sub=1)
    fi = S[11] + int(k * 0.5)
    keyscale(d_, [(0, 0.001), (fi - 1, 0.001), (fi + 2, 1.4), (fi + 4, 1.0), (S[12] + 2, 1.0), (S[12] + 4, 0.001)])

# ---------------- passenger jet (line 12) ----------------
jw = mat("JetW", (0.96, 0.96, 0.98), 0.4)
jb = mat("JetB", (0.15, 0.4, 0.85), 0.4)
JET = group("Jet", (0, 0, 0))
JL = 14.0
jp = [cyl("JFus", (0, 0, 0), 1.0, JL, jw, rot=(0, math.radians(90), 0), verts=20),
      sphere("JNose", (-JL / 2, 0, 0), 1.0, jw, scale=(1.6, 1.0, 1.0), sub=2),
      cyl("JTailC", (JL / 2 + 1.0, 0, 0.2), 1.0, 2.0, jw, rot=(0, math.radians(90), 0), verts=20, r2=0.35),
      box("JWing", (0.6, 0, -0.3), (3.0, 15.0, 0.25), jb, bevel=0.08),
      box("JTail", (JL / 2 + 1.0, 0, 1.9), (2.0, 0.25, 3.2), jb, bevel=0.06),
      box("JStab", (JL / 2 + 1.2, 0, 0.4), (1.4, 5.0, 0.2), jb, bevel=0.05)]
for k in range(9):
    jp.append(box("JWin", (-JL / 2 + 2.0 + k * 1.2, -0.98, 0.35), (0.45, 0.06, 0.4), win_m))
for sy in (-1, 1):
    jp.append(cyl("JEng", (-0.4, sy * 3.6, -0.95), 0.6, 2.2, jw, rot=(0, math.radians(90), 0), verts=14))
attach(jp, JET)
g12 = gp(S[12])
JET.scale = (1.7,) * 3
key_loc(JET, [(0, g12 + Vector((70, 24, 12.0))), (S[12] - 1, g12 + Vector((70, 24, 12.0))), (S[13] + 4, g12 + Vector((-65, 24, 12.0)))])
for fc in fcurves(JET):
    for kp in fc.keyframe_points:
        kp.interpolation = 'LINEAR'
hide_until(JET, S[12]); gone_at(JET, S[13] + 4, 1)
# contrail
con_m = mat("Contrail", (1, 1, 1), 0.9, emit=(1, 1, 1), emit_strength=0.6)
for k in range(24):
    f = S[12] + k
    sc.frame_set(f)
    c_ = sphere("Con", tuple(JET.location + Vector((JL / 2 * 1.7 + 4.0, 0, 0.0))), 1.1, con_m, sub=1)
    keyscale(c_, [(0, 0.001), (f - 1, 0.001), (f, 1.0), (S[13] + 4, 1.4), (S[13] + 5, 0.001)])
sc.frame_set(0)

# ---------------- ice: everything turns icy (line 13 onward) ----------------
ICE = (0.72, 0.9, 1.0)
for m_, c0 in [(can1, (1.0, 0.42, 0.05)), (can2, (1.0, 0.82, 0.1)), (jacket, (0.15, 0.55, 0.95)), (helm_m, (1.0, 0.85, 0.1)),
               (pants_w, (0.15, 0.17, 0.25)), (hair_w, (0.55, 0.32, 0.12))]:
    bc = m_.node_tree.nodes["Principled BSDF"].inputs["Base Color"]
    ice_c = tuple(c0[i] * 0.35 + ICE[i] * 0.65 for i in range(3))
    for f, c in [(S[13], c0), (S[13] + 10, ice_c), (S[16] + 30, ice_c), (S[17] + 10, c0)]:
        bc.default_value = (*c, 1); bc.keyframe_insert("default_value", frame=f)
    ec = m_.node_tree.nodes["Principled BSDF"].inputs["Emission Color"]
    ecol = tuple(ec.default_value)[:3]
    for f, c in [(S[13], ecol), (S[13] + 10, (0.6, 0.85, 1.0)), (S[16] + 30, (0.6, 0.85, 1.0)), (S[17] + 10, ecol)]:
        ec.default_value = (*c, 1); ec.keyframe_insert("default_value", frame=f)
icicles = []
for k in range(NC):
    a = math.radians(-72 + 144 * k / (NC - 1))
    x, z = R_ * math.sin(a), CZ + R_ * math.cos(a)
    for j in (-1, 1):
        ic = cyl("Icicle", (x + j * 0.2, 0.2 + j * 0.3, z - 0.45), 0.09, 0.6, ice_m if 'ice_m' in dir() else frost_m, rot=(math.pi, 0, 0), verts=6, r2=0.0)
        icicles.append(ic)
for sx in (-1, 1):
    for j in range(3):
        icicles.append(cyl("IcicleP", (sx * (0.15 + j * 0.08), -0.1, 0.0 - j * 0.15), 0.07, 0.4, frost_m, rot=(math.pi, 0, 0), verts=6, r2=0.0))
for ic in icicles:
    parent_to(ic, PG)
    hide_until(ic, S[13] + 3 + random.randint(0, 8))
    gone_at(ic, S[17] + 8, 3)
for k in range(10):     # sparkly frost burst at the moment she freezes
    g = gp(S[13] + 2)
    burst(tuple(g + Vector(((k % 5 - 2) * 1.0, -0.6, (k // 5) * 2.4 + 0.2))), S[13] + 2 + k, n=6, r=0.3, size=0.06, f_out=S[13] + 12 + k, material=frost_m)

# ---------------- landing (line 16): canopy collapses behind her, sparkles ----------------
LF = S[16] + 32
keyrot(canopy, [(LF - 2, (0, 0, 0)), (LF + 10, (math.radians(-75), 0, 0))])
keyscale(canopy, [(LF - 2, 1.0), (LF + 10, (1.0, 1.0, 0.5))])
for a_, sgn in zip(PL_["arms"], (1, -1)):
    keyrot(a_, [(LF + 2, (0, sgn * 2.6, 0)), (LF + 8, (0, sgn * 2.9, 0)), (LF + 14, (0, sgn * 2.4, 0)), (LF + 20, (0, sgn * 2.9, 0))])
gold = glow_mat("Gold", (1.0, 0.85, 0.3), 6.0)
for k in range(4):
    burst((LAND[0] + (k - 1.5) * 0.9, LAND[1] - 0.4, 2.2 + (k % 2) * 0.6), LF + 2 + k * 3, n=10, r=0.5, size=0.06, f_out=LF + 14 + k * 3, material=gold)
# question mark next to her at the end
q = text("Q", "?", (LAND[0] + 1.8, LAND[1] - 0.2, 2.2), 1.4, lab_m, extrude=0.12)
pop(q, S[17] + 4, 6)
keyrot(q, [(S[17] + 4, (math.radians(90), 0, 0)), (FRAMES, (math.radians(90), 0, math.radians(360)))])

ring_m = glow_mat("Ring", (1.0, 0.9, 0.2), 5.0)
for (fa, fb) in [(S[9], S[10]), (S[11], S[12])]:
    bpy.ops.mesh.primitive_torus_add(major_radius=4.6, minor_radius=0.22, location=(0, 0, 0), rotation=(math.radians(90), 0, 0))
    rg = bpy.context.object; rg.data.materials.append(ring_m)
    rg.parent = PG; rg.location = (0, -0.5, 1.5)
    keyscale(rg, [(0, 0.001), (fa + 4, 0.001), (fa + 8, 1.2), (fa + 11, 1.0), (fb - 1, 1.0), (fb, 0.001)])
# ---------------- camera: follows her every 2 frames ----------------
target = bpy.data.objects.new("Target", None); sc.collection.objects.link(target)
tr = cam.constraints.new('TRACK_TO'); tr.target = target
tr.track_axis = 'TRACK_NEGATIVE_Z'; tr.up_axis = 'UP_Y'
def aimL(cl, subj, k=0.5):
    lift = math.atan(k * TV)
    d = Vector(subj) - Vector(cl)
    ax = d.cross(Vector((0, 0, 1))).normalized()
    return tuple(Vector(cl) + Quaternion(ax, lift) @ d)
MID = Vector((0, 0, 1.6))
# per line: ("rel", offset_start, offset_end, use_overhead)  or ("abs", cam_start, cam_end, target_mode)
VW = [("rel", (4.0, -21.0, -4.0), (2.0, -17.0, -3.0), False),     # 0 hook: low, looking up at her + storm tower
      ("rel", (6.0, -16.0, 9.0), (3.5, -14.0, 8.0), True),        # 1 overhead over the garden
      ("rel", (-4.0, -17.0, -2.5), (-2.5, -15.0, -1.5), False),   # 2 updraft grabs the wing
      ("rel", (3.0, -19.0, -5.0), (1.0, -19.0, -2.0), False),     # 3 elevator ride up
      ("rel", (0.0, -18.0, 0.0), (-2.0, -16.0, 0.5), False),      # 4 inside, dark
      ("rel", (-2.5, -16.0, 1.5), (-0.5, -14.5, 0.5), False),     # 5 hail
      ("rel", (4.0, -21.0, -1.0), (1.5, -19.0, 0.0), False),      # 6 lightning
      ("rel", (-1.5, -14.5, 0.5), (0.0, -13.0, 0.3), False),      # 7 -50 C
      ("rel", (1.5, -13.5, 0.5), (0.0, -12.0, 0.2), False),       # 8 blackout
      ("abs", (-16.0, -50.0, 74.0), (-11.0, -44.0, 78.0), "g"),   # 9 Everest wide
      ("rel", (5.0, -21.0, -2.0), (2.5, -18.0, -1.0), False),     # 10 ~10 km
      ("abs", (30.0, -95.0, 60.0), (22.0, -88.0, 64.0), "gps"), # 11 GPS track wide
      ("rel", (-6.0, -24.0, -3.0), (-4.0, -22.0, -2.0), False),   # 12 jet
      ("rel", (1.5, -14.0, 0.6), (0.0, -12.5, 0.3), False),       # 13 ice
      ("rel", (2.5, -18.0, 5.0), (1.0, -16.0, 3.0), False),       # 14 drop
      ("rel", (-3.5, -17.0, -1.0), (-2.0, -15.5, 0.0), False),    # 15 woke, steering
      ("rel", (4.0, -17.0, 4.0), (2.5, -15.0, 3.0), True),        # 16 landing in the garden
      ("rel", (3.5, -13.0, 2.2), (1.5, -11.0, 1.6), True)]        # 17 question
assert len(VW) == NL, (len(VW), NL)
for f in range(0, FRAMES + 1):
    i = fr_line(f)
    if not (f == S[i] or f == line_end(i) or f % 2 == 0):
        continue
    u = (f - S[i]) / max(line_end(i) - S[i], 1)
    kind, a0, a1, mode = VW[i]
    off = Vector(a0).lerp(Vector(a1), u)
    g = gp(f)
    if kind == "rel":
        cl = g + MID + off
        tl = g + MID
        if mode:
            cl = Vector(overhead(tuple(cl), tuple(tl)))
        tgt = Vector(aimL(tuple(cl), tuple(tl)))
    else:
        cl = off
        if mode == "gps":
            tgt = Vector((0.0, 4.0, 78.0))
        else:
            tgt = Vector(aimL(tuple(cl), tuple(g + MID)))
    cam.location = cl; cam.keyframe_insert("location", frame=f)
    target.location = tgt; target.keyframe_insert("location", frame=f)
CUTS = tuple(S[1:])
for o_ in (cam, target):
    for fc in fcurves(o_):
        pts = fc.keyframe_points
        for i in range(len(pts) - 1):
            if int(round(pts[i + 1].co[0])) in CUTS:
                pts[i].interpolation = 'CONSTANT'
            else:
                pts[i].interpolation = 'LINEAR'
for o in bpy.data.objects:
    if o.type == 'FONT':
        o.visible_shadow = False
sc.frame_set(0)
bpy.ops.wm.save_as_mainfile(filepath=f"{HERE}/scene.blend")
print("SCENE OK", FRAMES, S)
