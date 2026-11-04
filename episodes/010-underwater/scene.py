# Day 10 — What if you stayed underwater too long?  Build: python3 episodes/010-underwater/scene.py
# Reference style: base (helpers, lawn/soil, house, garden) copied from episodes/003-lift-million-ref/scene.py
import bpy, math, random, os, json
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
random.seed(10)
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
# Day 10 — What if you stayed underwater too long?   (body series, YouTube-safe cartoon x-ray)
# Facts: most untrained people hold their breath ~30-90 s. Cold water on the face triggers the
#   mammalian diving reflex: heart rate slows, blood vessels in the limbs narrow (blood shifts to the core),
#   the spleen contracts and releases extra red blood cells. The urge to breathe is driven mainly by
#   rising CO2, not low O2; later the diaphragm makes involuntary contractions. O2 keeps falling;
#   the brain uses ~20% of the body's oxygen. Hypoxic blackout can come with little or no warning,
#   even when the person feels fine -> never swim / breath-hold alone.
#   Static apnea records (no pure-oxygen pre-breathing): ~11.5 min. Weddell seals dive for over an hour.
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
    return min(size, 0.85 * D / max(len(body), 4))
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
K = 1.0
PX, PY, PZ = -0.45, -0.35, PD + 0.08          # standing on the pool floor, head ~0.5 m under the surface
you, Y = person("You", (PX, PY, PZ), K, shirt_y, pants_y, skin_y, hair_y)
P_ = Y["P"]
TORSO = P_(0, 0, 1.12); HEAD = P_(0, 0, 1.7); MOUTH = P_(0, -0.25, 1.6)

# hook: jump from the pool edge into the water
EDGE = (PX - 3.1, PY, 0.0)
off0 = Vector(EDGE) - Vector((PX, PY, PZ))
JUMP0, JUMP1 = 5, 22
key_loc(you, [(0, tuple(Vector((PX, PY, PZ)) + off0)), (JUMP0, tuple(Vector((PX, PY, PZ)) + off0)),
              (JUMP0 + 7, tuple(Vector((PX, PY, PZ)) + off0 * 0.45 + Vector((0, 0, 1.6)))),
              (JUMP1 - 4, tuple(Vector((PX, PY, PZ)) + Vector((0, 0, 1.0)))),
              (JUMP1, (PX, PY, PZ - 0.08)), (JUMP1 + 6, (PX, PY, PZ))])
for a_, sgn in zip(Y["arms"], (1, -1)):
    keyrot(a_, [(JUMP0, (0, 0, 0)), (JUMP0 + 4, (0, sgn * 2.6, 0)), (JUMP1 + 2, (0, sgn * 2.6, 0)), (JUMP1 + 8, (0, sgn * 0.35, 0))])
splash = []
for k in range(16):
    a = k / 16 * 6.283
    s_ = sphere("Splash", (PX + 0.7 * math.cos(a), PY + 0.5 * math.sin(a) + 0.2, WTOP + 0.05), 0.11, bub_m, sub=1)
    key_loc(s_, [(JUMP1 - 3, (PX + 0.3 * math.cos(a), PY + 0.2 * math.sin(a) + 0.2, WTOP)),
                 (JUMP1 + 4, (PX + 0.9 * math.cos(a), PY + 0.6 * math.sin(a) + 0.2, WTOP + 0.9)),
                 (JUMP1 + 12, (PX + 1.3 * math.cos(a), PY + 0.8 * math.sin(a) + 0.2, WTOP))])
    pop(s_, JUMP1 - 3, 3, JUMP1 + 12)
cheeks = []
for sx in (-1, 1):
    c_ = sphere("Cheek", P_(sx * 0.15, -0.16, 1.62), 0.085, skin_y, sub=2)
    cheeks.append(c_)
# mouth bubbles while underwater
for k, f0 in enumerate(range(JUMP1 + 8, S[12], 11)):
    b_ = sphere("MBub", MOUTH, random.uniform(0.035, 0.06), bub_m, sub=2)
    hide_until(b_, f0)
    key_loc(b_, [(f0, MOUTH), (f0 + 26, (MOUTH[0] + random.uniform(-0.15, 0.15), MOUTH[1] - 0.05, WTOP - 0.03))])
    gone_at(b_, f0 + 27, 1)

V0 = ((0.6, -7.8, 3.0), (PX - 2.0, PY + 0.3, -0.3))
CAM0 = CL(V0)
label("LHook", "UNDERWATER", SP(V0, 9, 0.31), fit("UNDERWATER", 9, 0.62), blue_lab, 4, S[1], face=CAM0)
label("LHook2", "TOO LONG?", SP(V0, 9, 0.38), fit("TOO LONG?", 9, 0.62), white_lab, 9, S[1], face=CAM0)

# ---------------- line 1: stopwatch 30-90 s ----------------
SW = (PX + 1.75, PY - 0.25, -1.25)
sw_g = group("Stopwatch", SW)
face_m = mat("SWFace", (1, 1, 1), 0.4, emit=(1, 1, 1), emit_strength=0.3)
swp = [cyl("SWRim", SW, 0.5, 0.12, mat("SWRimM", (0.95, 0.35, 0.3), 0.4), rot=(math.radians(90), 0, 0), verts=40),
       cyl("SWFace", (SW[0], SW[1] - 0.04, SW[2]), 0.43, 0.08, face_m, rot=(math.radians(90), 0, 0), verts=40),
       cyl("SWBtn", (SW[0], SW[1], SW[2] + 0.58), 0.08, 0.16, mat("SWBtnM", (0.3, 0.3, 0.35), 0.4), verts=12)]
for k in range(12):
    a = k / 12 * 6.283
    swp.append(box("SWTick", (SW[0] + 0.36 * math.sin(a), SW[1] - 0.09, SW[2] + 0.36 * math.cos(a)), (0.03, 0.02, 0.07), eyeb, rot=(0, a, 0)))
attach(swp, sw_g)
hand = group("SWHand", (SW[0], SW[1] - 0.1, SW[2]))
attach([box("SWHandB", (SW[0], SW[1] - 0.1, SW[2] + 0.15), (0.03, 0.02, 0.32), red_lab)], hand)
pop(sw_g, S[1], 5, S[2]); pop(hand, S[1], 5, S[2])
keyrot(hand, [(S[1], (0, 0, 0)), (S[2], (0, 6.283 * 1.5, 0))])
for fc in []: pass
V1 = ((PX + 2.4, PY - 3.6, -0.6), (PX + 0.9, PY, -0.9))
CAM1 = CL(V1)
label("L3090", "30 - 90 SEC", SP(V1, 3.4, 0.32), fit("30 - 90 SEC", 3.4, 0.3), lab_m, S[1] + 3, S[2], face=CAM1)

# ---------------- line 2: x-ray on: skin & clothes go see-through, glowing organs ----------------
for m_ in (skin_y, shirt_y, pants_y, hair_y):
    al = m_.node_tree.nodes["Principled BSDF"].inputs["Alpha"]
    for f, v in [(0, 1.0), (S[2] + 1, 1.0), (S[2] + 6, 0.28), (S[12] - 1, 0.28), (S[12] + 3, 1.0)]:
        al.default_value = v; al.keyframe_insert("default_value", frame=f)
brain_m = mat("Brain", (1.0, 0.55, 0.7), 0.4, emit=(1.0, 0.45, 0.65), emit_strength=0.8)
lung_m = mat("Lung", (1.0, 0.6, 0.65), 0.4, emit=(1.0, 0.5, 0.55), emit_strength=0.7)
heart_m = mat("Heart", (0.95, 0.1, 0.12), 0.35, emit=(1.0, 0.08, 0.1), emit_strength=1.4)
spleen_m = mat("Spleen", (0.55, 0.15, 0.6), 0.4, emit=(0.6, 0.15, 0.7), emit_strength=1.0)
brain = sphere("Brain", P_(0, 0.0, 1.73), 0.17, brain_m, scale=(1.0, 1.1, 0.8), sub=3)
lungs = [sphere("Lung", P_(sx * 0.12, 0.0, 1.2), 0.13, lung_m, scale=(0.75, 0.7, 1.35), sub=3) for sx in (-1, 1)]
heart = sphere("Heart", P_(0.04, -0.1, 1.1), 0.075, heart_m, scale=(1.0, 0.9, 1.15), sub=3)
spleen = sphere("Spleen", P_(0.2, -0.02, 0.93), 0.07, spleen_m, scale=(0.6, 0.6, 1.3), sub=3)
organs = [brain, heart, spleen] + lungs
for o in organs:
    o.visible_shadow = False
    pop(o, S[2] + 4, 6, S[12] + 2, s=1.0)
    # keep original non-uniform scale: re-key with tuples
bpy.context.view_layer.update()
def pop_t(o, base_s, f_in, f_out):
    keyscale(o, [(0, 0.001), (f_in - 1, 0.001), (f_in + 4, tuple(v * 1.15 for v in base_s)), (f_in + 6, base_s),
                 (f_out - 3, base_s), (f_out, 0.001)])
BRS, LUS, HES, SPS = (1.0, 1.1, 0.8), (0.75, 0.7, 1.35), (1.0, 0.9, 1.15), (0.6, 0.6, 1.3)
for o in organs:
    if o.animation_data:
        o.animation_data_clear()
pop_t(brain, BRS, S[2] + 4, S[12] + 2)
for l_ in lungs:
    pop_t(l_, LUS, S[2] + 5, S[12] + 2)
pop_t(spleen, SPS, S[2] + 7, S[12] + 2)
V2 = ((PX + 0.9, PY - 3.2, -1.0), (PX, PY, -0.40))
CAM2 = CL(V2)
label("LXray", "X-RAY", SP(V2, 2.2, 0.31), fit("X-RAY", 2.2, 0.26), blue_lab, S[2] + 3, S[3], face=CAM2)
xglow = glow_mat("XGlow", (0.5, 0.9, 1.0), 3.0)
for k in range(3):
    bpy.ops.mesh.primitive_torus_add(major_radius=0.6, minor_radius=0.018, location=TORSO, rotation=(math.radians(90), 0, 0))
    r_ = bpy.context.object; r_.data.materials.append(xglow)
    keyscale(r_, [(0, 0.001), (S[2] + k * 3, 0.001), (S[2] + k * 3 + 1, 0.2), (S[2] + k * 3 + 10, 1.6), (S[2] + k * 3 + 11, 0.001)])

# ---------------- line 3: cold water hits the face (ice crystals, blue flash) ----------------
ice_m = mat("Ice", (0.75, 0.92, 1.0), 0.1, emit=(0.6, 0.9, 1.0), emit_strength=1.5)
for k in range(14):
    a = k / 14 * 6.283
    p = Vector(HEAD) + Vector((0.42 * math.cos(a), -0.28, 0.34 * math.sin(a)))
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=0.05, location=tuple(p))
    o = bpy.context.object; o.data.materials.append(ice_m); o.scale = (0.5, 0.5, 1.6); o.rotation_euler = (0, a, 0)
    keyscale(o, [(0, 0.001), (S[3] + k // 2, 0.001), (S[3] + k // 2 + 3, (0.6, 0.6, 1.9)), (S[3] + k // 2 + 5, (0.5, 0.5, 1.6)),
                 (S[4] - 3, (0.5, 0.5, 1.6)), (S[4], 0.001)])
    key_loc(o, [(S[3] + k // 2, tuple(p + Vector((0.25 * math.cos(a), -0.1, 0.25 * math.sin(a))))), (S[3] + k // 2 + 6, tuple(p))])
V3 = ((PX + 0.5, PY - 1.9, -0.7), (PX, PY, -0.68))
CAM3 = CL(V3)
label("LCold", "COLD WATER!", SP(V3, 1.5, 0.30), fit("COLD WATER!", 1.5, 0.16), blue_lab, S[3] + 2, S[4], face=CAM3)
wc = water_m.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"]
for f, v in [(0, 0.15), (S[3], 0.15), (S[3] + 3, 0.9), (S[3] + 10, 0.15)]:
    wc.default_value = v; wc.keyframe_insert("default_value", frame=f)

# ---------------- line 4: heart slows down (fast beats -> slow beats) ----------------
beats = [S[2] + 8]
while beats[-1] < S[4]:
    beats.append(beats[-1] + 7)
while beats[-1] < S[12]:
    beats.append(beats[-1] + 15)
hk = [(0, 0.001), (S[2] + 3, 0.001)]
for b in beats:
    if b >= S[12] - 4:
        break
    hk += [(b, HES), (b + 2, tuple(v * 1.35 for v in HES)), (b + 5, HES)]
hk += [(S[12] - 1, HES), (S[12] + 2, 0.001)]
keyscale(heart, hk)
ecg_m = glow_mat("ECG", (0.3, 1.0, 0.45), 4.0)
V4 = ((PX + 0.6, PY - 2.0, -1.15), (PX, PY, -0.67))
CAM4 = CL(V4)
label("LSlow", "HEART SLOWS", SP(V4, 1.45, 0.29), fit("HEART SLOWS", 1.45, 0.13), red_lab, S[4] + 2, S[5], face=CAM4)
# ECG line: fast spikes before, slow after
def ecg(name, pts_x, spikes, ctr, w, f_in, f_out):
    pts = []
    for i in range(len(pts_x)):
        pts.append(pts_x[i])
    o = tube(name, pts, [0.008] * len(pts), ecg_m)
    pop(o, f_in, 4, f_out)
    return o
def ecg_pts(org, width, n_spikes, h):
    pts = []
    for i in range(n_spikes):
        x0 = org[0] + i * width / n_spikes
        seg = width / n_spikes
        pts += [(x0, org[1], org[2]), (x0 + seg * 0.4, org[1], org[2]), (x0 + seg * 0.5, org[1], org[2] + h),
                (x0 + seg * 0.6, org[1], org[2] - h * 0.4), (x0 + seg * 0.7, org[1], org[2])]
    pts.append((org[0] + width, org[1], org[2]))
    return pts
E0 = Vector(SP(V4, 1.4, 0.38, -0.12))
fast = tube("ECGFast", ecg_pts(tuple(E0 - Vector((0.22, 0, 0))), 0.44, 6, 0.06), [0.006] * 31, ecg_m)
slow = tube("ECGSlow", ecg_pts(tuple(E0 - Vector((0.22, 0, 0))), 0.44, 2, 0.06), [0.006] * 11, ecg_m)
for o in (fast, slow):
    center(o)
pop(fast, S[4] + 1, 3, S[4] + 14); pop(slow, S[4] + 14, 3, S[5])

# ---------------- line 5: blood rushes from the arms to the core ----------------
blood_m = mat("Blood", (0.95, 0.1, 0.12), 0.35, emit=(1.0, 0.1, 0.1), emit_strength=1.5)
for sx in (-1, 1):
    path = [P_(sx * 0.38, -0.08, 0.78), P_(sx * 0.38, -0.05, 1.05), P_(sx * 0.3, -0.03, 1.33), P_(sx * 0.1, -0.05, 1.18), P_(0.04, -0.1, 1.1)]
    for k in range(9):
        b_ = sphere("RBC", path[0], 0.035, blood_m, scale=(1, 1, 0.45), sub=2)
        f0 = S[5] + k * 3
        keyscale(b_, [(0, 0.001), (f0 - 1, 0.001), (f0, 1.0), (f0 + 16, 1.0), (f0 + 17, 0.001)])
        key_loc(b_, [(f0 + i * 4, p) for i, p in enumerate(path)])
arm_m = [shirt_y]
V5 = ((PX - 0.7, PY - 3.2, -1.0), (PX, PY, -0.45))
CAM5 = CL(V5)
label("LCore", "ARMS", SP(V5, 2.3, 0.30, -0.2), fit("ARMS", 2.3, 0.2), white_lab, S[5] + 2, S[6], face=CAM5)
label("LCore2", "TO CORE!", SP(V5, 2.3, 0.37, 0.12), fit("TO CORE!", 2.3, 0.22), red_lab, S[5] + 8, S[6], face=CAM5)

# ---------------- line 6: spleen squeezes out extra red cells ----------------
keyscale(spleen, [(S[6] + 2, SPS), (S[6] + 6, (0.4, 0.4, 0.8)), (S[6] + 10, SPS), (S[6] + 14, (0.4, 0.4, 0.8)), (S[6] + 18, SPS)])
for k in range(22):
    a = random.uniform(0, 6.283); r_ = random.uniform(0.15, 0.45)
    p0 = Vector(P_(0.2, -0.02, 0.93))
    p1 = p0 + Vector((r_ * math.cos(a), -0.12, r_ * math.sin(a) * 1.2))
    b_ = sphere("RBC2", tuple(p0), 0.03, blood_m, scale=(1, 1, 0.45), sub=2)
    f0 = S[6] + 4 + (k % 3) * 4
    keyscale(b_, [(0, 0.001), (f0 - 1, 0.001), (f0, 1.0), (S[7] - 2, 1.0), (S[7], 0.001)])
    key_loc(b_, [(f0, tuple(p0)), (f0 + 8, tuple(p1))])
    b_.rotation_euler = (random.uniform(0, 3), random.uniform(0, 3), 0)
V6 = ((PX + 0.8, PY - 2.0, -1.25), (PX + 0.1, PY, -0.72))
CAM6 = CL(V6)
label("LSpleen", "SPLEEN", SP(V6, 1.4, 0.29), fit("SPLEEN", 1.4, 0.13), mat("LabPu", (0.8, 0.4, 1.0), 0.4, emit=(0.75, 0.35, 1.0), emit_strength=1.4), S[6] + 2, S[7], face=CAM6)
label("LSpl2", "+ RED CELLS", SP(V6, 1.4, 0.36), fit("+ RED CELLS", 1.4, 0.11), red_lab, S[6] + 7, S[7], face=CAM6)

# ---------------- line 7: CO2 builds up (grey bubbles fill the chest) ----------------
co2_m = mat("CO2", (0.55, 0.55, 0.6), 0.5, emit=(0.5, 0.5, 0.55), emit_strength=0.3)
co2s = []
for k in range(36):
    p = Vector(TORSO) + Vector((random.uniform(-0.22, 0.22), random.uniform(-0.16, 0.05), random.uniform(-0.3, 0.35)))
    b_ = sphere("CO2b", tuple(p), random.uniform(0.03, 0.055), co2_m, sub=2)
    f0 = S[7] + int(k * 0.9)
    keyscale(b_, [(0, 0.001), (f0 - 1, 0.001), (f0 + 2, 1.0), (S[9] - 1, 1.0), (S[9] + 2, 0.001)])
    co2s.append(b_)
V7 = ((PX - 0.7, PY - 2.4, -1.0), (PX, PY, -0.62))
CAM7 = CL(V7)
label("LCO2", "CO2", SP(V7, 1.6, 0.29), fit("CO2", 1.6, 0.22), grey_lab, S[7] + 2, S[8], face=CAM7)
label("LCO2b", "BUILDING UP", SP(V7, 1.6, 0.37), fit("BUILDING UP", 1.6, 0.12), white_lab, S[7] + 6, S[8], face=CAM7)

# ---------------- line 8: burning urge to breathe (lungs glow orange, flames) ----------------
lc = lung_m.node_tree.nodes["Principled BSDF"].inputs["Emission Color"]
ls_ = lung_m.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"]
for f, c, s in [(0, (1.0, 0.5, 0.55, 1), 0.7), (S[8], (1.0, 0.5, 0.55, 1), 0.7), (S[8] + 5, (1.0, 0.35, 0.0, 1), 4.0),
                (S[9] - 1, (1.0, 0.3, 0.0, 1), 4.0), (S[9] + 8, (1.0, 0.5, 0.55, 1), 0.7)]:
    lc.default_value = c; lc.keyframe_insert("default_value", frame=f)
    ls_.default_value = s; ls_.keyframe_insert("default_value", frame=f)
flames = []
flame_m = glow_mat("Flame", (1.0, 0.45, 0.05), 6.0)
flame2 = glow_mat("Flame2", (1.0, 0.85, 0.2), 6.0)
for k in range(10):
    sx = -1 if k < 5 else 1
    p = P_(sx * (0.06 + (k % 5) * 0.035), -0.13, 1.08 + (k % 2) * 0.05)
    fl = cyl("Flame", p, 0.035, 0.14, flame_m if k % 2 else flame2, r2=0.0, verts=8)
    f0 = S[8] + 2 + k
    flames.append(fl)
    keyscale(fl, [(0, 0.001), (f0 - 1, 0.001)] + [(f0 + j * 3, (1, 1, 1.3 if j % 2 else 0.8)) for j in range(0, (S[9] - f0) // 3)] + [(S[9], 0.001)])
V8 = ((PX + 0.6, PY - 2.1, -1.05), (PX, PY, -0.62))
CAM8 = CL(V8)
label("LBurn", "BURN!", SP(V8, 1.4, 0.29), fit("BURN!", 1.4, 0.2), mat("LabO", (1.0, 0.5, 0.1), 0.4, emit=(1.0, 0.45, 0.05), emit_strength=1.6), S[8] + 2, S[9], face=CAM8)

# ---------------- line 9: chest twitches and jerks ----------------
jit = [(S[9], (0, 0, 0))]
for j, f in enumerate(range(S[9] + 2, S[10] - 2, 4)):
    jit.append((f, (random.choice((-1, 1)) * 0.09, random.uniform(-0.05, 0.05), random.choice((-1, 1)) * 0.07)))
    jit.append((f + 2, (0, 0, 0)))
jit.append((S[10], (0, 0, 0)))
keyrot(you, jit)
TS = tuple(Y["torso"].scale)
tk = [(S[9], TS)]
for f in range(S[9] + 2, S[10] - 2, 4):
    tk += [(f, (TS[0] * 1.08, TS[1] * 1.15, TS[2] * 0.95)), (f + 2, TS)]
keyscale(Y["torso"], tk)
V9 = ((PX + 1.3, PY - 3.6, -0.9), (PX, PY, -0.45))
CAM9 = CL(V9)
label("LTw", "TWITCH!", SP(V9, 2.8, 0.29), fit("TWITCH!", 2.8, 0.3), lab_m, S[9] + 2, S[10] - 2, face=CAM9)
label("LTw2", "JERK!", SP(V9, 2.8, 0.37, 0.15), fit("JERK!", 2.8, 0.3), red_lab, S[9] + 12, S[10], face=CAM9)

# ---------------- line 10: oxygen keeps dropping (O2 meter in the water) ----------------
MX_, MY_ = PX + 1.75, PY - 0.2
o2_frame = mat("O2Frame", (0.95, 0.95, 0.97), 0.4, emit=(1, 1, 1), emit_strength=0.2)
o2_bar_m = mat("O2Bar", (0.2, 0.9, 0.35), 0.3, emit=(0.2, 0.9, 0.3), emit_strength=1.5)
meter = group("Meter", (MX_, MY_, PD + 0.3))
mps = [box("MFrameL", (MX_ - 0.26, MY_, PD + 1.15), (0.06, 0.2, 1.75), o2_frame),
       box("MFrameR", (MX_ + 0.26, MY_, PD + 1.15), (0.06, 0.2, 1.75), o2_frame),
       box("MFrameB", (MX_, MY_, PD + 0.27), (0.58, 0.2, 0.06), o2_frame),
       box("MFrameT", (MX_, MY_, PD + 2.03), (0.58, 0.2, 0.06), o2_frame)]
attach(mps, meter)
bar = group("O2BarG", (MX_, MY_, PD + 0.3))
attach([box("O2BarB", (MX_, MY_, PD + 0.3 + 0.85), (0.44, 0.14, 1.7), o2_bar_m)], bar)
o2t = text("O2T", "O2", (MX_, MY_ - 0.2, PD + 2.3), 0.3, white_lab, extrude=0.02)
attach([o2t], meter)
for o in (meter, bar):
    keyscale(o, [(0, 0.001), (S[10] - 1, 0.001), (S[10] + 4, 1.0), (S[16] - 1, 1.0), (S[16], 0.001)])
keyscale(bar, [(S[10] + 4, 1.0), (S[11] - 2, (1, 1, 0.45)), (S[12], (1, 1, 0.3)), (S[13], (1, 1, 0.15)), (S[15], (1, 1, 0.12)),
               (S[15] + 14, (1, 1, 0.6)), (S[16] - 1, (1, 1, 0.8)), (S[16], 0.001)])
bc = o2_bar_m.node_tree.nodes["Principled BSDF"]
for f, c in [(0, (0.2, 0.9, 0.3, 1)), (S[10] + 4, (0.2, 0.9, 0.3, 1)), (S[11] - 4, (1.0, 0.75, 0.1, 1)), (S[12], (1.0, 0.1, 0.05, 1)),
             (S[15] + 4, (1.0, 0.1, 0.05, 1)), (S[15] + 14, (0.2, 0.9, 0.3, 1))]:
    bc.inputs["Base Color"].default_value = c; bc.inputs["Base Color"].keyframe_insert("default_value", frame=f)
    bc.inputs["Emission Color"].default_value = c; bc.inputs["Emission Color"].keyframe_insert("default_value", frame=f)
es = bc.inputs["Emission Strength"]
for f in range(S[14], S[15], 6):     # flashing "low" in line 14
    es.default_value = 4.0; es.keyframe_insert("default_value", frame=f)
    es.default_value = 0.6; es.keyframe_insert("default_value", frame=f + 3)
es.default_value = 1.5; es.keyframe_insert("default_value", frame=S[15] + 2)
o2dots_m = mat("O2Dot", (0.3, 0.6, 1.0), 0.3, emit=(0.3, 0.6, 1.0), emit_strength=2.0)
V10 = ((PX + 2.4, PY - 4.0, -0.9), (PX + 0.9, PY, -0.45))
CAM10 = CL(V10)
label("LO2", "OXYGEN", SP(V10, 3.0, 0.29), fit("OXYGEN", 3.0, 0.3), blue_lab, S[10] + 2, S[11], face=CAM10)
label("LO2b", "DROPPING!", SP(V10, 3.0, 0.37), fit("DROPPING!", 3.0, 0.27), red_lab, S[10] + 8, S[11], face=CAM10)
for k in range(12):   # blue O2 dots leave the body and fade
    p0 = Vector(TORSO) + Vector((random.uniform(-0.2, 0.2), -0.2, random.uniform(-0.3, 0.3)))
    d_ = sphere("O2Dot", tuple(p0), 0.045, o2dots_m, sub=2)
    f0 = S[10] + 2 + k * 2
    keyscale(d_, [(0, 0.001), (f0 - 1, 0.001), (f0, 1.0), (f0 + 10, 0.5), (f0 + 14, 0.001)])
    key_loc(d_, [(f0, tuple(p0)), (f0 + 14, tuple(p0 + Vector((random.uniform(-0.6, 0.6), -0.2, random.uniform(-0.6, 0.2)))))])

# ---------------- line 11: the brain needs it the most (O2 dots rush to the brain, brain glows) ----------------
bs_ = brain_m.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"]
for f, v in [(0, 0.8), (S[11], 0.8), (S[11] + 6, 4.0), (S[12] - 2, 4.0), (S[12] + 2, 0.3)]:
    bs_.default_value = v; bs_.keyframe_insert("default_value", frame=f)
for k in range(14):
    p0 = Vector(TORSO) + Vector((random.uniform(-0.2, 0.2), -0.15, random.uniform(-0.35, 0.0)))
    d_ = sphere("O2Dot2", tuple(p0), 0.04, o2dots_m, sub=2)
    f0 = S[11] + k * 2
    keyscale(d_, [(0, 0.001), (f0 - 1, 0.001), (f0, 1.0), (f0 + 10, 1.0), (f0 + 11, 0.001)])
    key_loc(d_, [(f0, tuple(p0)), (f0 + 10, P_(random.uniform(-0.08, 0.08), -0.05, 1.73))])
V11 = ((PX - 0.5, PY - 1.9, -0.55), (PX, PY, -0.53))
CAM11 = CL(V11)
label("LBrain", "BRAIN USES", SP(V11, 1.45, 0.27), fit("BRAIN USES", 1.45, 0.11), white_lab, S[11] + 2, S[12], face=CAM11)
label("LBrain2", "20% OF YOUR O2", SP(V11, 1.45, 0.34), fit("20% OF YOUR O2", 1.45, 0.12), lab_m, S[11] + 6, S[12], face=CAM11)

# ---------------- line 12: black out (lights dim, eyes close, body drifts) ----------------
sun_e = sun.data
for f, v in [(0, 4.2), (S[12], 4.2), (S[12] + 5, 0.6), (S[13] - 2, 0.6), (S[13] + 2, 4.2)]:
    sun_e.energy = v; sun_e.keyframe_insert("energy", frame=f)
wb = bg.inputs["Strength"]
for f, v in [(0, 0.85), (S[12], 0.85), (S[12] + 5, 0.15), (S[13] - 2, 0.15), (S[13] + 2, 0.85)]:
    wb.default_value = v; wb.keyframe_insert("default_value", frame=f)
for e in Y["eyes"]:
    keyscale(e, [(S[12] + 2, (1, 0.6, 1.2)), (S[12] + 6, (1.1, 0.6, 0.12)), (S[13] - 1, (1.1, 0.6, 0.12)), (S[13] + 1, (1, 0.6, 1.2))])
for e in Y["pupils"]:
    keyscale(e, [(S[12] + 2, 1.0), (S[12] + 5, 0.001), (S[13] - 1, 0.001), (S[13] + 1, 1.0)])
keyrot(you, [(S[12] + 2, (0, 0, 0)), (S[12] + 14, (0.25, 0.18, 0)), (S[13] - 1, (0.3, 0.2, 0)), (S[13], (0, 0, 0))])
V12 = ((PX + 1.2, PY - 3.3, -0.9), (PX, PY, -0.45))
CAM12 = CL(V12)
label("LBO", "BLACKOUT", SP(V12, 2.3, 0.30), fit("BLACKOUT", 2.3, 0.28), red_lab, S[12] + 3, S[13], face=CAM12)
for k in range(5):
    z_ = text(f"Zzz{k}", "z", tuple(Vector(HEAD) + Vector((0.3 + k * 0.08, -0.25, 0.25 + k * 0.12))), 0.08 + k * 0.03, white_lab)
    pop(z_, S[12] + 6 + k * 2, 3, S[13])

# ---------------- line 13: zero warning (warning sign with "0") ----------------
warn_m = mat("Warn", (1.0, 0.8, 0.05), 0.4, emit=(1.0, 0.75, 0.05), emit_strength=1.2)
V13 = ((PX + 1.7, PY - 3.8, -0.8), (PX + 0.4, PY, -0.45))
CAM13 = CL(V13)
WP = Vector(SP(V13, 3.0, 0.29, 0.12))
wg = group("WarnG", tuple(WP))
tri = cyl("WarnTri", tuple(WP), 0.26, 0.04, warn_m, rot=(math.radians(90), 0, 0), verts=3)
tri.rotation_euler = (math.radians(90), math.radians(-90), 0)
ex = text("WarnEx", "!", tuple(WP - Vector((0, 0.04, 0.02))), 0.26, eyeb)
attach([tri, ex], wg)
wg.rotation_euler = (0, 0, math.atan2(CAM13[0] - WP.x, -(CAM13[1] - WP.y))); wg["rz"] = wg.rotation_euler[2]
cross_m = red_lab
for sgn in (-1, 1):
    cb = box("WarnX", tuple(WP - Vector((0, 0.06, 0))), (0.05, 0.03, 0.6), cross_m, rot=(0, sgn * 0.75, 0))
    parent_to(cb, wg)
    hide_until(cb, S[13] + 9)
pop(wg, S[13] + 1, 5, S[14])
label("LNoW", "NO WARNING", SP(V13, 2.6, 0.38), fit("NO WARNING", 2.6, 0.2), red_lab, S[13] + 9, S[14], face=CAM13)

# ---------------- line 14: even when you feel totally fine (thumbs up vs O2 flashing red) ----------------
keyrot(Y["arms"][1], [(S[14], (0, -0.35, 0)), (S[14] + 5, (0, -2.3, 0)), (S[15] - 1, (0, -2.3, 0)), (S[15] + 3, (0, -0.35, 0))])
V14 = ((PX + 1.9, PY - 4.0, -0.8), (PX + 0.8, PY, -0.45))
CAM14 = CL(V14)
bub = sphere("SpeechB", SP(V14, 3.0, 0.31, -0.1), 0.3, white_lab, scale=(1.75, 0.08, 0.6), sub=3)
BUBS = (1.75, 0.08, 0.6)
keyscale(bub, [(0, 0.001), (S[14] + 1, 0.001), (S[14] + 5, BUBS), (S[15] - 3, BUBS), (S[15], 0.001)])
t_ = text("SpeechT", "I FEEL FINE!", tuple(Vector(SP(V14, 2.9, 0.31, -0.1))), 0.11, eyeb)
t_.rotation_euler = (math.radians(90), 0, math.atan2(CAM14[0] - t_.location.x, -(CAM14[1] - t_.location.y)))
bub.rotation_euler = t_.rotation_euler.copy(); bub.rotation_euler[0] = 0
pop(t_, S[14] + 3, 4, S[15])
label("LLow", "O2 LOW!", SP(V14, 3.0, 0.37, 0.22), fit("O2 LOW!", 3.0, 0.22), red_lab, S[14] + 8, S[15], face=CAM14)

# ---------------- line 15: never swim alone: buddy + ring buoy, you float up safely ----------------
skin_b = mat("SkinB", (0.75, 0.52, 0.36), 0.6)
shirt_b = mat("ShirtB", (0.98, 0.85, 0.1), 0.7)
pants_b = mat("PantsB", (0.85, 0.15, 0.15), 0.8)
hair_b = mat("HairB", (0.1, 0.08, 0.06), 0.8)
BUD = (PX - 3.3, PY + 0.3, 0.0)
buddy, B = person("Buddy", BUD, 1.0, shirt_b, pants_b, skin_b, hair_b)
hide_until(buddy, S[15])
gone_at(buddy, S[16], 1)
keyrot(B["arms"][1], [(S[15], (0, 0, 0)), (S[15] + 4, (0, -2.6, 0)), (S[15] + 8, (0, -2.2, 0)), (S[15] + 12, (0, -2.6, 0))])
bpy.ops.mesh.primitive_torus_add(major_radius=0.36, minor_radius=0.1, location=(BUD[0] + 0.6, BUD[1] - 0.2, 1.3))
ring = bpy.context.object; ring.name = "Ring"
ring.data.materials.append(stripe_mat("RingM", (1, 1, 1), (0.95, 0.15, 0.1), axis="X", freq=9.0, thresh=0.0, rough=0.5))
ring.rotation_euler = (math.radians(90), 0, 0)
hide_until(ring, S[15] + 3)
key_loc(ring, [(S[15] + 3, (BUD[0] + 0.6, BUD[1] - 0.2, 1.3)), (S[15] + 9, (PX - 1.0, PY - 0.2, 1.4)), (S[15] + 14, (PX, PY - 0.1, WTOP + 0.05))])
keyrot(ring, [(S[15] + 3, (math.radians(90), 0, 0)), (S[15] + 14, (0, 0, 3.0))])
gone_at(ring, S[16], 1)
key_loc(you, [(S[15] + 12, (PX, PY, PZ)), (S[15] + 22, (PX, PY, PZ + 1.55))])
for c_ in cheeks:
    keyscale(c_, [(0, 1.0), (S[15] + 18, 1.0), (S[15] + 21, 0.001)])
keyrot(Y["arms"][0], [(S[15] + 14, (0, 0.35, 0)), (S[15] + 22, (0, 2.4, 0))])
V15 = ((PX + 1.6, PY - 6.0, 2.0), (PX - 1.4, PY + 0.3, 0.2))
CAM15 = CL(V15)
label("LNev", "NEVER SWIM", SP(V15, 5.0, 0.29), fit("NEVER SWIM", 5.0, 0.5), white_lab, S[15] + 2, S[16], face=CAM15)
label("LNev2", "ALONE!", SP(V15, 5.0, 0.37), fit("ALONE!", 5.0, 0.55), lab_m, S[15] + 6, S[16], face=CAM15)
for k in range(3):   # second splash when you surface
    pass
burst((PX, PY - 0.2, WTOP + 0.1), S[15] + 20, 12, 0.5, 0.06, S[15] + 30, bub_m)

# ---------------- lines 16-17: breath-hold bars on the lawn: you ~1 min / freediver ~11 min / seal 60+ min ----------------
gone_at(you, S[16], 1)
UNIT = 0.42     # metres per minute of breath-hold
BY = 5.6
def bar_(name, x, minutes, m_, f_in, rise=8):
    g = group(name, (x, BY, 0))
    h = minutes * UNIT
    attach([box(name + "B", (x, BY, h / 2), (1.3 if minutes < 30 else 2.2, 1.3 if minutes < 30 else 2.2, h), m_, bevel=0.06)], g)
    keyscale(g, [(0, 0.001), (f_in - 1, 0.001), (f_in, (1, 1, 0.01)), (f_in + rise, (1, 1, 1.0))])
    return g, h
bar_you_m = mat("BarYou", (0.95, 0.35, 0.25), 0.5)
bar_fd_m = mat("BarFD", (0.1, 0.65, 0.7), 0.5)
bar_seal_m = mat("BarSeal", (0.55, 0.5, 0.62), 0.5)
b1, h1 = bar_("BarYou", -3.0, 1.2, bar_you_m, S[16])
b2, h2 = bar_("BarFD", 0.0, 11.5, bar_fd_m, S[16] + 6, 10)
b3, h3 = bar_("BarSeal", 3.2, 65.0, bar_seal_m, S[17] + 2, 16)
# small "you" (dry, normal) next to your bar, freediver with fins next to theirs
you2, Y2 = person("You2", (-4.3, BY - 0.9, 0.0), 0.9, mat("ShirtY2", (0.95, 0.35, 0.25), 0.7), pants_y, mat("SkinY2", (0.95, 0.74, 0.58), 0.6), hair_y)
wet = mat("Wetsuit", (0.08, 0.1, 0.14), 0.4)
fd, F = person("Diver", (1.3, BY - 0.9, 0.0), 0.95, wet, wet, mat("SkinD", (0.85, 0.6, 0.45), 0.6), hair_b)
fins_m = mat("Fins", (0.1, 0.55, 0.95), 0.4)
for sx in (-1, 1):
    fin = box("Fin", F["P"](sx * 0.15, -0.55, 0.03), (0.22, 0.95, 0.03), fins_m, bevel=0.02)
    parent_to(fin, fd)
mask_m = mat("DMask", (0.3, 0.85, 1.0), 0.1, emit=(0.3, 0.8, 1.0), emit_strength=0.5)
mk = box("DMaskB", F["P"](0, -0.24, 1.72), (0.34, 0.06, 0.16), mask_m, bevel=0.02)
parent_to(mk, fd)
for g_ in (you2, fd):
    hide_until(g_, S[16])
    gone_at(g_, S[18], 1)
V16 = ((3.5, -5.5, 3.0), (-1.0, BY - 0.8, 1.6))
CAM16 = CL(V16)
label("LBarY", "YOU ~1 MIN", (-3.0, BY - 0.7, h1 + 0.7), 0.7, white_lab, S[16] + 2, S[17], face=CAM16)
label("LBarF", "FREEDIVER", (0.0, BY - 0.7, h2 + 1.3), 0.55, white_lab, S[16] + 8, S[17], face=CAM16)
label("LBarF2", "~11 MIN!", (0.0, BY - 0.7, h2 + 0.55), 0.65, lab_m, S[16] + 12, S[17] + 8, face=CAM16)
# cartoon seal at the foot of the tall bar
seal_m = mat("Seal", (0.42, 0.42, 0.5), 0.45)
seal_spot = mat("SealSpot", (0.7, 0.72, 0.78), 0.5)
SX_, SY_ = 6.6, BY - 1.6
seal = group("Seal", (SX_, SY_, 0))
sps_ = [sphere("SealBody", (SX_, SY_, 0.55), 1.0, seal_m, scale=(0.55, 1.4, 0.55), sub=3),
        sphere("SealHead", (SX_, SY_ - 1.25, 0.95), 0.42, seal_m, sub=3),
        sphere("SealNose", (SX_, SY_ - 1.62, 0.88), 0.14, seal_spot, scale=(1.2, 0.8, 0.8), sub=2),
        sphere("SealTail", (SX_, SY_ + 1.45, 0.25), 1.0, seal_m, scale=(0.5, 0.35, 0.1), sub=2)]
for sx in (-1, 1):
    sps_ += [sphere("SealEyeW", (SX_ + sx * 0.17, SY_ - 1.55, 1.08), 0.1, eyew, sub=2),
             sphere("SealEyeB", (SX_ + sx * 0.18, SY_ - 1.63, 1.09), 0.06, eyeb, sub=2),
             sphere("SealFlip", (SX_ + sx * 0.55, SY_ - 0.5, 0.2), 1.0, seal_m, scale=(0.35, 0.22, 0.06), sub=2)]
    for k in range(3):
        sps_.append(tube("Whisk", [(SX_ + sx * 0.12, SY_ - 1.65, 0.86 - k * 0.04), (SX_ + sx * 0.45, SY_ - 1.75, 0.9 - k * 0.08)], [0.008, 0.004], eyeb))
for k in range(8):
    sps_.append(sphere("SealSpotS", (SX_ + random.uniform(-0.3, 0.3), SY_ + random.uniform(-0.9, 0.9), 1.05), 0.09, seal_spot, scale=(1.4, 1.0, 0.3), sub=1))
attach(sps_, seal)
hide_until(seal, S[17])
pop(seal, S[17], 6, s=2.0)
V17 = ((9.0, -22.0, 7.0), (3.0, BY, 6.0))
CAM17 = V17[0]
label("LSeal", "WEDDELL SEAL", (3.2, BY - 1.3, h3 + 3.6), 2.0, white_lab, S[17] + 10, S[18], face=CAM17)
label("LSeal2", "60+ MIN!", (3.2, BY - 1.3, h3 + 1.2), 2.8, lab_m, S[17] + 14, S[18], face=CAM17)
for g_ in (b1, b2, b3, seal):
    gone_at(g_, S[18], 1)

# ---------------- line 18: question — you on dry land, cheeks puffed, stopwatch ----------------
Q0 = (3.7, -0.9, 0.0)
you3, Y3 = person("You3", Q0, 1.0, mat("ShirtY3", (0.95, 0.35, 0.25), 0.7), pants_y, mat("SkinY3", (0.95, 0.74, 0.58), 0.6), hair_y)
for sx in (-1, 1):
    c_ = sphere("Cheek3", Y3["P"](sx * 0.15, -0.16, 1.62), 0.095, mat("SkinY3b", (0.98, 0.62, 0.55), 0.6), sub=2)
    parent_to(c_, you3)
hide_until(you3, S[18])
keyrot(Y3["arms"][0], [(S[18], (0, 0, 0)), (S[18] + 6, (0, 0.5, 0))])
V18 = ((4.9, -4.9, 1.3), (Q0[0], Q0[1], 0.95))
CAM18 = CL(V18)
sw2 = group("SW2", SP(V18, 3.2, 0.30, 0.24))
sw2p = [cyl("SW2Rim", SP(V18, 3.2, 0.30, 0.24), 0.16, 0.07, mat("SWRim2", (0.95, 0.35, 0.3), 0.4), rot=(math.radians(90), 0, 0), verts=36)]
o_ = sw2p[0]; o_.rotation_euler = (math.radians(90), 0, math.atan2(CAM18[0] - o_.location.x, -(CAM18[1] - o_.location.y)))
f2 = cyl("SW2Face", SP(V18, 3.16, 0.30, 0.24), 0.135, 0.07, face_m, rot=(math.radians(90), 0, 0), verts=36)
f2.rotation_euler = o_.rotation_euler.copy()
attach(sw2p + [f2], sw2)
pop(sw2, S[18] + 2, 5)
q = text("Q", "?", SP(V18, 3.2, 0.30, -0.22), 0.36, lab_m, extrude=0.05)
pop(q, S[18] + 6, 6)
keyrot(q, [(S[18] + 6, (math.radians(90), 0, 0)), (FRAMES, (math.radians(90), 0, math.radians(360)))])
label("LDry", "ON DRY LAND", SP(V18, 3.2, 0.38, 0.0), fit("ON DRY LAND", 3.2, 0.2), white_lab, S[18] + 10, FRAMES + 5, face=CAM18)

# organs / CO2 / flames / cheeks follow the body (twitch + blackout tilt)
sc.frame_set(S[3])
for o in organs + co2s + flames + cheeks:
    parent_to(o, you)
sc.frame_set(0)

# ---------------- camera ----------------
bpy.ops.object.camera_add()
cam = bpy.context.object
sc.camera = cam
cam.data.lens = 26
cam.data.sensor_fit = 'VERTICAL'
cam.data.sensor_height = 36
cam.data.clip_start = 0.02
cam.data.clip_end = 3.0e6
target = bpy.data.objects.new("Target", None); sc.collection.objects.link(target)
tr = cam.constraints.new('TRACK_TO'); tr.target = target
tr.track_axis = 'TRACK_NEGATIVE_Z'; tr.up_axis = 'UP_Y'
def drift(v, dx=0.0, dy=0.0, dz=0.0):
    return (v[0][0] + dx, v[0][1] + dy, v[0][2] + dz)
VIEWS = [V0, V1, V2, V3, V4, V5, V6, V7, V8, V9, V10, V11, V12, V13, V14, V15, V16, V17, V18]
DR = [(-1.2, 2.0, -1.0), (-0.4, 0.6, 0), (-0.3, 0.45, 0), (0.25, 0.3, 0), (-0.25, 0.3, 0), (0.5, 0.4, 0), (-0.3, 0.3, 0),
      (0.4, 0.35, 0), (-0.25, 0.3, 0), (-0.4, 0.5, 0), (-0.5, 0.5, 0), (0.25, 0.3, 0), (-0.3, 0.7, 0), (-0.4, 0.5, 0),
      (-0.5, 0.4, 0), (-1.4, 1.0, 0.3), (-2.0, 1.0, 0.5), (2.0, -5.0, 1.0), (-0.4, 0.4, 0)]
cam_keys = []
for i, v in enumerate(VIEWS):
    f_a = S[i]
    f_b = (S[i + 1] - 1) if i + 1 < len(S) else FRAMES - 1
    cam_keys.append((f_a, v[0], v[1]))
    cam_keys.append((f_b, drift(v, *DR[i]), v[1]))
cam_keys = [(f, cl if S[17] <= f < S[18] else overhead(cl, tl), tl) for f, cl, tl in cam_keys]
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
