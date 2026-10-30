# Day 5 — What if an air bubble got into your vein?  Build: python3 episodes/005-air-bubble/scene.py
# Reference style: base (helpers, lawn/soil, house, garden) copied from episodes/003-lift-million-ref/scene.py
import bpy, math, random, os, json
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
random.seed(5)
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
# Day 5 — What if an air bubble got into your vein?
# Facts used: small venous air bubbles (e.g. the few that slip in from IV lines) are usually harmless — they travel
#   to the right heart, are pumped into the lungs, get trapped in the pulmonary capillary network and dissolve.
#   A large, rapid volume of air is dangerous: it can froth in the right ventricle and block outflow ("air lock").
#   Prevention: nurses remove air from lines, infusion pumps have air-in-line alarms. Treatment: 100% oxygen,
#   positioning, hyperbaric (pressure) chambers. Divers: decompression sickness ("the bends") = gas bubbles.
#   No volumes / doses are given anywhere (YouTube-safe, not a how-to).
# v2 (Salih, 2026-10-30): told on the body of a man sitting in a garden chair — cut-away chest + arm vein.
# =====================================================================================

def recenter(o, bottom=False):
    from mathutils import Matrix
    bpy.context.view_layer.update()
    vs = [o.matrix_world @ v.co for v in o.data.vertices]
    c = Vector((sum(v.x for v in vs) / len(vs), sum(v.y for v in vs) / len(vs),
                min(v.z for v in vs) if bottom else sum(v.z for v in vs) / len(vs)))
    o.data.transform(o.matrix_world)
    o.data.transform(Matrix.Translation(-c))
    o.matrix_world = Matrix.Translation(c)
    return o

def keyscale(o, keys):
    for f, s in keys:
        o.scale = (s,) * 3 if not isinstance(s, tuple) else s
        o.keyframe_insert("scale", frame=f)

def half_pipe(name, x0, x1, y, z, r, material, a0=-150, a1=55, seg=28, thick=0.07):
    """Cut-away vessel along X: keeps the back + bottom wall, open towards the camera (front/top)."""
    nx = 2
    verts, faces = [], []
    for i in range(nx):
        x = x0 + (x1 - x0) * i / (nx - 1)
        for k in range(seg + 1):
            a = math.radians(a0 + (a1 - a0) * k / seg)
            verts.append((x, y + r * math.cos(a), z + r * math.sin(a)))
    for k in range(seg):
        faces.append((k, k + 1, seg + 1 + k + 1, seg + 1 + k))
    me = bpy.data.meshes.new(name); me.from_pydata(verts, [], faces); me.update()
    o = bpy.data.objects.new(name, me); sc.collection.objects.link(o)
    me.materials.append(material)
    for p in me.polygons:
        p.use_smooth = True
    m = o.modifiers.new("s", 'SOLIDIFY'); m.thickness = thick; m.offset = 1.0
    return o

def person(name, loc, body_c, skin=(0.95, 0.75, 0.6), hair=(0.25, 0.14, 0.06), arm_up=False, extra=None):
    g = group(name, loc, 0)
    x, y, z = loc
    bm = mat(name + "B", body_c, 0.7)
    lm = mat(name + "L", (0.18, 0.22, 0.38), 0.8)
    sk = mat(name + "S", skin, 0.6)
    dk = mat(name + "E", (0.05, 0.04, 0.05), 0.4)
    parts = [
        cyl("LegL", (x - 0.13, y, 0.38), 0.1, 0.76, lm), cyl("LegR", (x + 0.13, y, 0.38), 0.1, 0.76, lm),
        cyl("Body", (x, y, 1.08), 0.28, 0.75, bm, r2=0.22),
        sphere("Head", (x, y, 1.68), 0.24, sk, sub=2),
        sphere("Hair", (x, y + 0.05, 1.82), 0.22, mat(name + "Hr", hair, 0.8), scale=(1.05, 1.05, 0.6), sub=2),
        sphere("EyeL", (x - 0.08, y - 0.21, 1.72), 0.035, dk, sub=1), sphere("EyeR", (x + 0.08, y - 0.21, 1.72), 0.035, dk, sub=1),
        tube("Smile", [(x - 0.07, y - 0.215, 1.6), (x, y - 0.235, 1.575), (x + 0.07, y - 0.215, 1.6)], [0.012] * 3, dk),
        tube("ArmL", [(x - 0.3, y, 1.35), (x - 0.4, y - 0.02, 1.08), (x - 0.4, y - 0.05, 0.85)], [0.07, 0.065, 0.06], bm),
        sphere("HandL", (x - 0.4, y - 0.05, 0.82), 0.06, sk, sub=1),
    ]
    if arm_up:
        parts += [tube("ArmR", [(x + 0.3, y, 1.35), (x + 0.5, y - 0.1, 1.65), (x + 0.6, y - 0.15, 1.98)], [0.07, 0.065, 0.06], bm),
                  sphere("HandR", (x + 0.62, y - 0.16, 2.02), 0.07, sk, sub=1)]
    else:
        parts += [tube("ArmR", [(x + 0.3, y, 1.35), (x + 0.4, y - 0.02, 1.08), (x + 0.4, y - 0.05, 0.85)], [0.07, 0.065, 0.06], bm),
                  sphere("HandR", (x + 0.4, y - 0.05, 0.82), 0.06, sk, sub=1)]
    if extra:
        parts += extra(x, y)
    attach(parts, g)
    return g

lab_m = mat("LabelM", (1.0, 0.85, 0.2), 0.4, emit=(1.0, 0.8, 0.2), emit_strength=0.8)
white_lab = mat("LabW", (1, 1, 1), 0.4, emit=(1, 1, 1), emit_strength=0.7)
red_lab = mat("LabR", (0.95, 0.1, 0.08), 0.4, emit=(1.0, 0.1, 0.05), emit_strength=1.2)
green_lab = mat("LabG", (0.2, 0.9, 0.3), 0.4, emit=(0.2, 0.9, 0.3), emit_strength=1.2)
bubble_m = mat("Bubble", (0.92, 0.97, 1.0), 0.04, emit=(0.75, 0.9, 1.0), emit_strength=0.55)
shine_m = glow_mat("Shine", (1, 1, 1), 3.0)
vein_m = mat("VeinWall", (0.62, 0.16, 0.28), 0.45)
art_m = mat("ArtWall", (0.32, 0.36, 0.85), 0.45)
cell_m = mat("RBC", (0.9, 0.06, 0.08), 0.35)
cellb_m = mat("RBCb", (0.6, 0.1, 0.45), 0.35)
heart_m = mat("Heart", (0.92, 0.1, 0.16), 0.3)
eyew = mat("EyeW", (1, 1, 1), 0.3)
eyeb = mat("EyeB", (0.03, 0.03, 0.04), 0.3)

def bubble(name, loc, r):
    g = group(name, loc)
    p = [sphere(name + "B", loc, r, bubble_m, sub=3),
         sphere(name + "S", (loc[0] - 0.35 * r, loc[1] - 0.75 * r, loc[2] + 0.4 * r), 0.22 * r, shine_m, sub=1)]
    attach(p, g)
    return g

# ---------------- the man in the garden chair (big cartoon, facing the camera) ----------------
skin_m = mat("Skin", (0.95, 0.74, 0.58), 0.6)
shorts_m = mat("Shorts", (0.2, 0.42, 0.85), 0.7)
hair_m = mat("ManHair", (0.28, 0.16, 0.07), 0.8)
chair_w = mat("BigChair", (0.97, 0.97, 0.95), 0.5)
MY = 1.95
# chair
box("CSeat", (0, 2.0, 1.0), (1.9, 1.6, 0.12), chair_w, bevel=0.03)
box("CBack", (0, 2.78, 2.1), (1.9, 0.12, 2.2), chair_w, bevel=0.03)
for x in (-0.85, 0.85):
    for y in (1.3, 2.7):
        box("CLeg", (x, y, 0.47), (0.1, 0.1, 0.94), chair_w)
box("CArm", (0.98, 2.0, 1.55), (0.12, 1.4, 0.08), chair_w)
box("CArmPost", (0.98, 1.35, 1.28), (0.08, 0.08, 0.5), chair_w)
# side table under the left arm (IV arm)
box("STable", (-2.0, 1.4, 1.45), (1.6, 0.9, 0.08), mat("STableM", (0.75, 0.5, 0.28), 0.7), bevel=0.02)
for x in (-2.7, -1.3):
    for y in (1.05, 1.75):
        box("STLeg", (x, y, 0.71), (0.07, 0.07, 1.42), mat("STLegM", (0.6, 0.4, 0.22), 0.7))
# body
sphere("Torso", (0, MY, 2.05), 1.0, skin_m, scale=(0.78, 0.48, 1.0), sub=3)
sphere("Hips", (0, MY, 1.18), 1.0, shorts_m, scale=(0.8, 0.55, 0.3), sub=3)
cyl("Neck", (0, MY, 3.05), 0.2, 0.35, skin_m)
sphere("Head", (0, MY, 3.5), 0.45, skin_m, sub=3)
sphere("ManHairS", (0, MY + 0.06, 3.72), 0.42, hair_m, scale=(1.05, 1.0, 0.6), sub=2)
for sx in (-1, 1):
    sphere("MEyeW", (sx * 0.15, MY - 0.4, 3.58), 0.1, eyew, scale=(1, 0.6, 1.2), sub=2)
    sphere("MEyeB", (sx * 0.15, MY - 0.46, 3.57), 0.05, eyeb, sub=1)
    sphere("Ear", (sx * 0.45, MY, 3.5), 0.1, skin_m, scale=(0.5, 1, 1.2), sub=1)
mouth = tube("MSmile", [(-0.14, MY - 0.41, 3.36), (0, MY - 0.45, 3.31), (0.14, MY - 0.41, 3.36)], [0.022] * 3, eyeb)
sphere("Nose", (0, MY - 0.46, 3.46), 0.06, skin_m, sub=1)
for sx in (-1, 1):
    tube("Thigh", [(sx * 0.38, 2.0, 1.2), (sx * 0.42, 0.65, 1.2)], [0.27, 0.25], shorts_m)
    tube("Shin", [(sx * 0.42, 0.62, 1.2), (sx * 0.42, 0.56, 0.14)], [0.21, 0.18], skin_m)
    box("Foot", (sx * 0.42, 0.42, 0.08), (0.3, 0.5, 0.16), mat("Shoe", (0.15, 0.15, 0.18), 0.6), bevel=0.05)
# arm on the side table (IV arm, screen-left)
sphere("ShoulderL", (-0.8, MY, 2.8), 0.25, skin_m, sub=2)
tube("UpperArmL", [(-0.82, MY, 2.8), (-1.05, 1.55, 1.85)], [0.22, 0.21], skin_m)
sphere("ElbowL", (-1.07, 1.48, 1.74), 0.22, skin_m, sub=2)
tube("ForearmL", [(-1.07, 1.43, 1.72), (-2.45, 1.4, 1.72)], [0.23, 0.19], skin_m)
sphere("HandL", (-2.68, 1.4, 1.68), 0.2, skin_m, scale=(1.3, 1, 0.6), sub=2)
# other arm resting on the lap
sphere("ShoulderR", (0.8, MY, 2.8), 0.25, skin_m, sub=2)
tube("UpperArmR", [(0.82, MY, 2.8), (0.9, 1.8, 1.75)], [0.22, 0.21], skin_m)
tube("ForearmR", [(0.9, 1.78, 1.72), (0.62, 0.95, 1.5)], [0.21, 0.18], skin_m)
sphere("HandR", (0.58, 0.82, 1.48), 0.17, skin_m, sub=2)

# cut-away chest: dark cavity + organs in front
cav = cyl("Cavity", (0, 1.44, 2.25), 1.0, 0.03, mat("CavM", (0.42, 0.07, 0.12), 0.6), rot=(math.radians(90), 0, 0), verts=40)
cav.scale = (0.58, 0.74, 1)
tube("CavRim", [(0.58 * math.cos(a / 40 * 6.283), 1.425, 2.25 + 0.74 * math.sin(a / 40 * 6.283)) for a in range(41)], [0.03] * 41,
     mat("CavRimM", (0.85, 0.5, 0.45), 0.6))
lung_m = mat("Lung", (0.98, 0.6, 0.66), 0.55)
LUNGS = [(-0.3, 1.36, 2.42), (0.3, 1.36, 2.42)]
for p in LUNGS:
    sphere("Lobe", p, 1.0, lung_m, scale=(0.24, 0.1, 0.4), sub=3)
trach_m = mat("Trach", (0.95, 0.86, 0.86), 0.5)
tube("Trachea", [(0, 1.36, 2.95), (0, 1.36, 2.72)], [0.05, 0.05], trach_m)
tube("BronL", [(0, 1.36, 2.72), (-0.22, 1.35, 2.62)], [0.04, 0.035], trach_m)
tube("BronR", [(0, 1.36, 2.72), (0.22, 1.35, 2.62)], [0.04, 0.035], trach_m)
HCX, HCY, HCZ = 0.04, 1.27, 2.08
heart = group("Heart", (HCX, HCY, HCZ))
hp = [sphere("HLobeL", (HCX - 0.085, HCY, HCZ + 0.06), 0.13, heart_m, scale=(1, 0.7, 1), sub=3),
      sphere("HLobeR", (HCX + 0.085, HCY, HCZ + 0.06), 0.13, heart_m, scale=(1, 0.7, 1), sub=3),
      cyl("HTip", (HCX, HCY, HCZ - 0.1), 0.01, 0.26, heart_m, r2=0.205, verts=32)]
hp[2].scale = (1, 0.6, 1)
for sx in (-1, 1):
    hp.append(sphere("HEyeW", (HCX + sx * 0.06, HCY - 0.09, HCZ + 0.06), 0.035, eyew, scale=(0.8, 0.5, 1), sub=2))
    hp.append(sphere("HEyeB", (HCX + sx * 0.055, HCY - 0.105, HCZ + 0.055), 0.016, eyeb, sub=1))
hp.append(tube("HSmile", [(HCX - 0.045, HCY - 0.09, HCZ - 0.02), (HCX, HCY - 0.1, HCZ - 0.04), (HCX + 0.045, HCY - 0.09, HCZ - 0.02)],
               [0.007] * 3, eyeb))
attach(hp, heart)
STOP0, STOP1 = S[11], S[14] + 10
for f in range(0, FRAMES, 12):
    if STOP0 <= f < STOP1:
        continue
    keyscale(heart, [(f, 1.0), (f + 4, 1.1), (f + 8, 1.0)])
keyscale(heart, [(STOP0, (1.05, 1.05, 0.93)), (STOP1 - 1, (1.05, 1.05, 0.93))])
tube("PulmArt", [(HCX + 0.08, HCY + 0.02, HCZ + 0.15), (0.2, 1.28, 2.32), (0.27, 1.27, 2.4)], [0.025] * 3, art_m)

# capillary net on the right lung
NX, NY, NZ = 0.3, 1.255, 2.42
net = group("Net", (NX, NY, NZ))
cap_r = mat("CapR", (0.95, 0.15, 0.2), 0.4, emit=(0.9, 0.1, 0.15), emit_strength=0.4)
cap_b = mat("CapB", (0.35, 0.4, 1.0), 0.4, emit=(0.3, 0.35, 0.9), emit_strength=0.4)
np_ = []
for i in range(6):
    x = NX - 0.125 + i * 0.05
    np_.append(tube("NetV", [(x, NY, NZ - 0.22), (x, NY, NZ + 0.22)], [0.007] * 2, cap_r if i % 2 else cap_b))
for j in range(9):
    z = NZ - 0.2 + j * 0.05
    np_.append(tube("NetH", [(NX - 0.14, NY, z), (NX + 0.14, NY, z)], [0.007] * 2, cap_b if j % 2 else cap_r))
attach(np_, net)
hide_until(net, S[6] - 2)
keyscale(net, [(S[6] - 2, 0.001), (S[6] + 4, 1.15), (S[6] + 8, 1.0)])
for i in range(60):
    lp = random.choice(LUNGS)
    th = random.uniform(-1.1, 1.1); ph = random.uniform(-1.0, 1.0)
    p = (lp[0] + 0.24 * math.sin(th) * math.cos(ph), lp[1] - 0.1 * math.cos(th) * math.cos(ph) - 0.005, lp[2] + 0.4 * math.sin(ph))
    d = sphere("CapDot", p, 0.016, cap_r if i % 2 else cap_b, sub=1)
    pop(d, S[7] + int(i * 0.4), 4, S[9] - 2)

# ---------------- forearm vein (cut-away, raised on the skin) + blue vein up the arm ----------------
VY, VZ, VR = 1.33, 1.99, 0.11
VX0, VX1 = -2.4, -1.2
half_pipe("ArmVein", VX0, VX1, VY, VZ, VR, vein_m, thick=0.018)
bpy.ops.mesh.primitive_torus_add(major_radius=0.026, minor_radius=0.014, major_segments=14, minor_segments=6)
RBC = bpy.context.object.data; sc.collection.objects.unlink(bpy.context.object)
RBC.materials.append(cell_m)
L = VX1 - VX0
for i in range(22):
    o = bpy.data.objects.new("Cell", RBC); sc.collection.objects.link(o)
    ph = random.uniform(0, L)
    cy = VY + random.uniform(-0.45, 0.45) * VR
    cz = VZ - VR + 0.035 + random.uniform(0, 0.4) * VR
    rx, ry = random.uniform(0, 3), random.uniform(0, 3)
    for f in range(0, FRAMES + 2, 2):
        x = VX0 + (ph + 0.012 * f) % L
        vis = VX0 + 0.05 < x < VX1 - 0.05
        o.location = (x, cy + 0.01 * math.sin(f * 0.2 + i), cz)
        o.rotation_euler = (rx + f * 0.05, ry, 0)
        o.scale = (1.0 if vis else 0.001,) * 3
        o.keyframe_insert("location", frame=f); o.keyframe_insert("scale", frame=f); o.keyframe_insert("rotation_euler", frame=f)
glowv = mat("GlowVein", (0.25, 0.4, 1.0), 0.3, emit=(0.25, 0.45, 1.0), emit_strength=1.4)
UP = [(VX1, VY, VZ - 0.02), (-1.08, 1.3, 2.0), (-1.0, 1.42, 2.3), (-0.93, 1.6, 2.62), (-0.76, 1.68, 2.9),
      (-0.45, 1.5, 2.72), (-0.2, 1.36, 2.42), (HCX - 0.06, HCY - 0.06, HCZ + 0.08)]
tube("ArmVeinUp", UP, [0.028] * len(UP), glowv)
def path_at(P, u):
    u = max(0.0, min(1.0, u)) * (len(P) - 1)
    i = min(int(u), len(P) - 2); t = u - i
    a, b = P[i], P[i + 1]
    return tuple(a[k] + (b[k] - a[k]) * t for k in range(3))
def ride(o, P, f0, f1, n=8, lift=0.0):
    for k in range(n + 1):
        p = path_at(P, k / n)
        o.location = (p[0], p[1] - lift, p[2] + lift); o.keyframe_insert("location", frame=f0 + (f1 - f0) * k / n)

# ---------------- IV stand, bag, line, pump ----------------
IVX, IVY = -2.75, 0.75
pole_m = mat("Pole", (0.75, 0.77, 0.8), 0.3, metal=0.7)
cyl("IVPole", (IVX, IVY, 1.95), 0.035, 3.9, pole_m, verts=12)
for a in range(5):
    t = a / 5 * 6.283
    tube("IVFoot", [(IVX, IVY, 0.12), (IVX + 0.45 * math.cos(t), IVY + 0.45 * math.sin(t), 0.04)], [0.03, 0.025], pole_m)
box("IVHook", (IVX, IVY - 0.08, 3.85), (0.4, 0.04, 0.04), pole_m)
bag_m = mat("Bag", (0.75, 0.9, 1.0), 0.1, emit=(0.6, 0.8, 1.0), emit_strength=0.25)
box("IVBag", (IVX, IVY - 0.14, 3.4), (0.6, 0.16, 0.75), bag_m, bevel=0.07)
box("IVLabel", (IVX, IVY - 0.23, 3.45), (0.36, 0.02, 0.28), white_lab)
cyl("Drip", (IVX, IVY - 0.14, 2.88), 0.06, 0.24, bag_m)
line_m = mat("Line", (0.85, 0.95, 1.0), 0.15, emit=(0.7, 0.85, 1.0), emit_strength=0.25)
LINE = [(IVX, IVY - 0.14, 2.76), (IVX + 0.05, IVY - 0.25, 2.35), (IVX + 0.2, 1.0, 2.1), (-2.42, 1.25, 2.04), (VX0 + 0.05, VY, VZ - 0.03)]
tube("IVLine", LINE, [0.025] * 5, line_m)
box("Tape", (-2.36, 1.33, 1.93), (0.18, 0.2, 0.03), mat("TapeM", (0.97, 0.95, 0.9), 0.7))
def line_at(u):
    return path_at(LINE, u)
PZ_ = 1.95
PUX = IVX - 0.36
box("Pump", (PUX, IVY, PZ_), (0.52, 0.3, 0.42), mat("Pump", (0.95, 0.95, 0.97), 0.4), bevel=0.04)
box("PumpScr", (PUX, IVY - 0.155, PZ_ + 0.03), (0.38, 0.02, 0.22), mat("PumpScrM", (0.1, 0.25, 0.2), 0.3, emit=(0.2, 0.7, 0.4), emit_strength=0.6))
air_txt = text("AirTxt", "AIR!", (PUX, IVY - 0.172, PZ_ + 0.03), 0.15, red_lab, extrude=0.01)
pop(air_txt, S[13] + 2, 4, S[14])
siren_m = mat("Siren", (0.9, 0.1, 0.05), 0.3, emit=(1.0, 0.1, 0.05), emit_strength=0.0)
sphere("Siren", (PUX, IVY, PZ_ + 0.3), 0.11, siren_m, scale=(1, 1, 0.8), sub=2)
em = siren_m.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"]
em.default_value = 0.0; em.keyframe_insert("default_value", frame=0)
for (a, b) in [(S[9], S[10]), (S[13], S[14])]:
    em.default_value = 0.0; em.keyframe_insert("default_value", frame=a - 1)
    for f in range(a, b, 6):
        em.default_value = 12.0; em.keyframe_insert("default_value", frame=f)
        em.default_value = 0.5; em.keyframe_insert("default_value", frame=f + 3)
    em.default_value = 0.0; em.keyframe_insert("default_value", frame=b)
ring_m = glow_mat("AlarmRing", (1.0, 0.25, 0.15), 3.0)
for k in range(3):
    rr = tube("AlarmRing", [(0.22 * math.cos(a / 24 * 6.283), 0, 0.22 * math.sin(a / 24 * 6.283)) for a in range(25)], [0.015] * 25, ring_m)
    rr.location = (PUX, IVY - 0.25, PZ_ + 0.03)
    f0 = S[13] + 4 + k * 7
    keyscale(rr, [(0, 0.001), (f0 - 1, 0.001), (f0, 1.0), (f0 + 12, 2.2), (f0 + 13, 0.001)])

# ---------------- the hero bubble ----------------
B = bubble("Bubble", (0, 0, 0), 0.05)
ride(B, LINE, 0, S[1] - 6, 8)
key_loc(B, [(S[1], (VX0 + 0.25, VY, VZ - 0.04)), (S[2], (VX0 + 0.35, VY, VZ - 0.04)), (S[4], (VX0 + 0.45, VY, VZ - 0.04)),
            (S[4] + 14, (VX1 - 0.02, VY, VZ - 0.03))])
ride(B, UP, S[4] + 16, S[5] - 1, 10, lift=0.03)
key_loc(B, [(S[5] + 6, (HCX + 0.09, HCY - 0.06, HCZ + 0.15)), (S[6] - 4, (0.26, 1.24, 2.38)), (S[6] + 6, (NX, NY - 0.04, NZ + 0.02)),
            (S[8], (NX + 0.005, NY - 0.04, NZ + 0.025))])
keyscale(B, [(0, 1.0), (S[6] + 8, 1.0), (S[7] + 2, (1.15, 1.0, 0.85)), (S[7] + 6, 1.0), (S[7] + 10, (1.1, 1.0, 0.9)), (S[8], 1.0),
             (S[9] - 6, 0.001)])
spark_m = glow_mat("Spark", (0.8, 0.95, 1.0), 4.0)
for i in range(14):
    p0 = (NX + random.uniform(-0.05, 0.05), NY - 0.06, NZ + random.uniform(-0.03, 0.05))
    p1 = (random.uniform(-0.15, 0.15), MY - 0.55, 3.35 + random.uniform(0, 0.5))
    sp_ = sphere("Spark", p0, 0.015, spark_m, sub=1)
    f0 = S[8] + 2 + i
    key_loc(sp_, [(f0, p0), (f0 + 10, (0.0, 1.3, 2.9)), (f0 + 18, p1)])
    pop(sp_, f0, 3, min(f0 + 20, S[9] + 2))
ahh = text("Ahh", "phew", (0.0, MY - 0.7, 4.15), 0.2, white_lab, extrude=0.01)
pop(ahh, S[8] + 18, 4, S[9] + 2)

# ---------------- line 1-2: movie clapperboard + MYTH stamp + green check ----------------
CBX, CBY, CBZ = 1.9, 0.45, 1.45
clap = group("Clap", (CBX, CBY, CBZ))
cb = [box("ClapBoard", (CBX, CBY, CBZ), (1.2, 0.08, 0.8), mat("ClapM", (0.08, 0.08, 0.1), 0.5), bevel=0.02),
      box("ClapPost", (CBX, CBY + 0.08, CBZ / 2 - 0.2), (0.09, 0.06, CBZ - 0.4), mat("ClapP", (0.4, 0.4, 0.42), 0.5)),
      text("ClapTxt", "MOVIES", (CBX, CBY - 0.05, CBZ - 0.08), 0.27, white_lab, extrude=0.01)]
bar = stripe_mat("ClapBar", (0.97, 0.97, 0.97), (0.08, 0.08, 0.1), axis="X", freq=12.0, thresh=0.0)
cb.append(box("ClapTop", (CBX, CBY, CBZ + 0.48), (1.2, 0.09, 0.14), bar))
attach(cb, clap)
pop(clap, S[1] - 2, 6)
myth = text("Myth", "MYTH", (CBX, CBY - 0.18, CBZ + 0.03), 0.44, red_lab, extrude=0.04)
myth.rotation_euler = (math.radians(90), math.radians(-14), 0)
pop(myth, S[2] + 1, 5, S[3] + 2)
myth2 = text("Myth2", "MYTH?", (CBX, CBY - 0.18, CBZ + 0.03), 0.38, red_lab, extrude=0.04)
myth2.rotation_euler = (math.radians(90), math.radians(-10), 0)
pop(myth2, S[17] + 6, 5)
chk = group("Check", (VX0 + 0.45, VY - 0.15, 2.3))
ck = [box("Chk1", (VX0 + 0.4, VY - 0.15, 2.26), (0.04, 0.04, 0.13), green_lab, rot=(0, math.radians(-40), 0)),
      box("Chk2", (VX0 + 0.5, VY - 0.15, 2.31), (0.04, 0.04, 0.25), green_lab, rot=(0, math.radians(35), 0))]
attach(ck, chk)
pop(chk, S[2] + 6, 5, S[3] + 2)

# ---------------- line 3: a few tiny bubbles sneak down the IV line ----------------
for k in range(4):
    tb = bubble("Tiny", (0, 0, 0), 0.025)
    f0 = S[3] + 2 + k * 6
    ride(tb, LINE, f0, f0 + 14, 6)
    key_loc(tb, [(f0 + 20, (VX0 + 0.15 + 0.08 * k, VY - 0.02, VZ - 0.06)), (S[5], (VX0 + 0.7 + 0.08 * k, VY - 0.02, VZ - 0.06))])
    keyscale(tb, [(0, 0.001), (f0 - 1, 0.001), (f0, 1.0), (S[5] - 4, 1.0), (S[5], 0.001)])

# ---------------- line 9: a big rush of air ----------------
for k in range(14):
    r = random.uniform(0.04, 0.07)
    bb = bubble("Rush", (0, 0, 0), r)
    f0 = S[9] - 2 + k * 2
    ride(bb, LINE, f0, f0 + 8, 4)
    key_loc(bb, [(f0 + 14, (VX0 + 0.3 + random.uniform(0, 0.2), VY + random.uniform(-0.04, 0.04), VZ - VR + r + 0.02)),
                 (S[10] - 6 + k, (VX1 - 0.05, VY, VZ - 0.03))])
    ride(bb, UP, S[10] - 4 + k, S[10] + 8 + k, 6, lift=0.03)
    keyscale(bb, [(0, 0.001), (f0 - 1, 0.001), (f0 + 2, 1.0), (S[10] + 8 + k, 1.0), (S[10] + 10 + k, 0.001)])

# ---------------- line 10: foam in the heart; shrinks with oxygen (line 14) ----------------
foam_m = mat("Foam", (0.97, 0.99, 1.0), 0.08, emit=(0.8, 0.9, 1.0), emit_strength=0.35)
for i in range(40):
    a = random.uniform(0, 6.283); rr = math.sqrt(random.uniform(0, 1))
    p = (HCX + 0.17 * rr * math.cos(a), HCY - 0.1 - random.uniform(0, 0.02), HCZ + 0.01 + 0.13 * rr * math.sin(a))
    fo = sphere("Foam", p, random.uniform(0.02, 0.045), foam_m, sub=2)
    f0 = S[10] + int(i * 0.5)
    keyscale(fo, [(0, 0.001), (f0 - 1, 0.001), (f0 + 3, 1.2), (f0 + 5, 1.0), (S[14] + 8, 1.0), (S[14] + 30 + i % 10, 0.001)])
stop = group("Stop", (0.0, 1.0, 4.35))
st = [cyl("StopSign", (0.0, 1.0, 4.35), 0.42, 0.04, red_lab, rot=(math.radians(90), math.radians(22.5), 0), verts=8),
      text("StopTxt", "STOP", (0.0, 0.97, 4.35), 0.22, white_lab, extrude=0.01)]
attach(st, stop)
pop(stop, S[11] + 1, 5, S[12] + 2)
lock = text("Jam", "JAMMED", (0.0, 1.0, 1.55), 0.26, lab_m, extrude=0.03)
pop(lock, S[11] + 6, 5, S[12] + 2)
# the man looks worried while the heart is jammed (mouth turns down)
mouth.keyframe_insert("rotation_euler", frame=S[9])
mouth.rotation_euler = (0, math.radians(180), 0)
mouth.location = (0, 0, 2 * 3.34)
mouth.keyframe_insert("rotation_euler", frame=S[9] + 2); mouth.keyframe_insert("location", frame=S[9] + 2)
mouth.keyframe_insert("rotation_euler", frame=S[14] + 20); mouth.keyframe_insert("location", frame=S[14] + 20)
mouth.rotation_euler = (0, 0, 0); mouth.location = (0, 0, 0)
mouth.keyframe_insert("rotation_euler", frame=S[14] + 22); mouth.keyframe_insert("location", frame=S[14] + 22)
mouth.location = (0, 0, 0); mouth.keyframe_insert("location", frame=S[9])

# ---------------- line 12: nurse flicks a bubble out of the line ----------------
nurse = person("Nurse", (IVX - 0.75, IVY - 0.55, 0), (0.15, 0.7, 0.68), hair=(0.12, 0.08, 0.05), arm_up=True,
               extra=lambda x, y: [box("Cap", (x, y + 0.02, 1.93), (0.36, 0.3, 0.12), mat("CapM", (0.15, 0.7, 0.68), 0.6))])
nurse.scale = (1.15, 1.15, 1.15)
hide_until(nurse, S[12] - 3)
keyscale(nurse, [(S[12] - 3, 0.001), (S[12] + 2, 1.15), (S[13] - 2, 1.15), (S[13] + 2, 0.001)])
for f, a in [(S[12] + 4, 0.0), (S[12] + 8, -0.2), (S[12] + 10, 0.08), (S[12] + 14, -0.2), (S[12] + 16, 0.08), (S[12] + 20, 0.0)]:
    nurse.rotation_euler = (0, a, 0); nurse.keyframe_insert("rotation_euler", frame=f)
fb = bubble("FlickB", (0, 0, 0), 0.05)
key_loc(fb, [(S[12], line_at(0.3)), (S[12] + 10, line_at(0.3)), (S[12] + 20, line_at(0.0)), (S[12] + 32, (IVX, IVY - 0.4, 4.0))])
keyscale(fb, [(0, 0.001), (S[12] - 1, 0.001), (S[12], 1.0), (S[12] + 32, 1.4), (S[12] + 35, 0.001)])
flick = text("Flick", "FLICK!", (IVX + 0.6, IVY - 0.45, 2.75), 0.22, lab_m, extrude=0.02)
pop(flick, S[12] + 8, 4, S[13])
for k in range(8):
    a = k / 8 * 6.283
    s_ = sphere("PopSpark", (IVX + 0.25 * math.cos(a), IVY - 0.4, 4.0 + 0.25 * math.sin(a)), 0.03, spark_m, sub=1)
    pop(s_, S[12] + 33, 3, S[13] + 4)

# ---------------- line 14: oxygen mask + tank ----------------
OX, OY = 1.45, 1.2
o2_m = mat("O2", (0.12, 0.62, 0.3), 0.35)
cyl("O2Tank", (OX, OY, 0.75), 0.26, 1.5, o2_m)
sphere("O2Top", (OX, OY, 1.5), 0.26, o2_m, scale=(1, 1, 0.6))
cyl("O2Valve", (OX, OY, 1.72), 0.06, 0.2, pole_m)
text("O2Txt", "O2", (OX, OY - 0.27, 0.85), 0.26, white_lab, extrude=0.01)
mask = sphere("Mask", (0, MY - 0.43, 3.33), 0.16, mat("MaskM", (0.85, 0.95, 1.0), 0.15, emit=(0.6, 0.85, 1.0), emit_strength=0.3), scale=(1, 0.6, 0.9), sub=2)
HOSE = [(OX, OY, 1.82), (OX - 0.1, OY - 0.3, 2.4), (0.7, 1.2, 2.9), (0.2, MY - 0.55, 3.25), (0.0, MY - 0.5, 3.3)]
hose = tube("O2Hose", HOSE, [0.03] * 5, mat("HoseM", (0.85, 0.95, 0.9), 0.3))
for o in (mask, hose):
    hide_until(o, S[14] - 2)
o2dot = glow_mat("O2Dot", (0.4, 0.8, 1.0), 3.0)
DOWN = HOSE + [(0.0, 1.3, 2.95), (HCX, HCY - 0.08, HCZ + 0.1)]
for k in range(16):
    d = sphere("O2D", HOSE[0], 0.025, o2dot, sub=1)
    f0 = S[14] + k * 2
    ride(d, DOWN, f0, f0 + 18, 6)
    keyscale(d, [(0, 0.001), (f0 - 1, 0.001), (f0, 1.0), (f0 + 18, 1.0), (f0 + 20, 0.001)])
pct = text("O2Pct", "100% O2", (0.35, 0.9, 4.12), 0.2, lab_m, extrude=0.02)
pop(pct, S[14] + 4, 5, S[15])

# ---------------- line 15: pressure chamber (back of the garden) ----------------
CX, CY, CZ, CL, CR = 3.8, 5.6, 1.05, 3.4, 0.9
ch_m = mat("Chamber", (0.92, 0.94, 0.97), 0.75)
cyl("Chamber", (CX, CY, CZ), CR, CL, ch_m, rot=(0, math.radians(90), 0), verts=32)
sphere("ChEndR", (CX + CL / 2, CY, CZ), CR, ch_m, scale=(0.45, 1, 1), sub=3)
door = sphere("ChDoor", (CX - CL / 2, CY, CZ), CR, mat("ChDoorM", (0.2, 0.45, 0.85), 0.4), scale=(0.45, 1, 1), sub=3)
for x in (CX - 0.8, CX + 0.3):
    cyl("Porthole", (x, CY - CR + 0.02, CZ + 0.1), 0.26, 0.08, mat("PortM", (0.3, 0.6, 0.9), 0.1, emit=(0.4, 0.75, 1.0), emit_strength=0.5),
        rot=(math.radians(90), 0, 0))
for x in (CX - 1.2, CX + 1.2):
    box("ChLeg", (x, CY, 0.12), (0.3, 1.2, 0.24), mat("ChLegM", (0.4, 0.42, 0.45), 0.5))
cyl("Gauge", (CX + 1.15, CY - CR + 0.15, CZ + 0.45), 0.22, 0.06, white_lab, rot=(math.radians(90), 0, 0))
needle = group("Needle", (CX + 1.15, CY - CR + 0.1, CZ + 0.45))
nd = box("NeedleB", (CX + 1.15, CY - CR + 0.1, CZ + 0.53), (0.03, 0.02, 0.17), red_lab)
attach([nd], needle)
needle.rotation_euler = (0, -1.2, 0); needle.keyframe_insert("rotation_euler", frame=S[15] + 8)
needle.rotation_euler = (0, 1.1, 0); needle.keyframe_insert("rotation_euler", frame=S[16])
pat = person("Patient", (CX - 3.0, CY - 0.6, 0), (0.55, 0.75, 0.95), hair=(0.55, 0.32, 0.1))
key_loc(pat, [(S[15] - 2, (CX - 3.0, CY - 0.8, 0)), (S[15] + 12, (CX - CL / 2 - 0.4, CY - 0.1, 0))])
keyscale(pat, [(0, 0.001), (S[15] - 4, 0.001), (S[15] - 2, 1.0), (S[15] + 13, 1.0), (S[15] + 17, 0.001)])
door.keyframe_insert("location", frame=S[15] + 6)
door.location = (CX - CL / 2 - 0.5, CY - 1.0, CZ); door.keyframe_insert("location", frame=S[15] + 9)
door.keyframe_insert("location", frame=S[15] + 14)
door.location = (CX - CL / 2, CY, CZ); door.keyframe_insert("location", frame=S[15] + 18)
plab = text("PLab", "PRESSURE", (CX, CY - CR - 0.15, CZ + 1.35), 0.4, lab_m, extrude=0.03)
pop(plab, S[15] + 18, 5, S[16] + 2)

# ---------------- line 16: diver gets "the bends" ----------------
DX, DY = -6.0, 6.7
tank_m = mat("DTank", (1.0, 0.8, 0.1), 0.35)
diver = person("Diver", (DX, DY, 0), (0.08, 0.1, 0.14), skin=(0.95, 0.75, 0.6), hair=(0.05, 0.05, 0.06),
               extra=lambda x, y: [cyl("DTank", (x, y + 0.36, 1.15), 0.16, 0.7, tank_m),
                                   box("DMask", (x, y - 0.2, 1.72), (0.36, 0.08, 0.16), mat("DMaskM", (0.3, 0.75, 1.0), 0.1, emit=(0.3, 0.7, 1.0), emit_strength=0.4)),
                                   cyl("DFinL", (x - 0.13, y - 0.18, 0.04), 0.13, 0.06, tank_m, verts=10),
                                   cyl("DFinR", (x + 0.13, y - 0.18, 0.04), 0.13, 0.06, tank_m, verts=10)])
hide_until(diver, S[16] - 3)
diver.rotation_euler = (0, 0, 0); diver.keyframe_insert("rotation_euler", frame=S[16] + 10)
diver.rotation_euler = (0.2, 0.5, 0); diver.keyframe_insert("rotation_euler", frame=S[16] + 22)
diver.keyframe_insert("rotation_euler", frame=S[17] - 2)
diver.rotation_euler = (0, 0, 0); diver.keyframe_insert("rotation_euler", frame=S[17] + 4)
for k in range(40):
    p0 = (DX + random.uniform(-0.3, 0.3), DY - 0.3 + random.uniform(-0.1, 0.2), random.uniform(0.6, 1.6))
    p1 = (p0[0] + random.uniform(-0.6, 0.6), p0[1] - 0.2, p0[2] + random.uniform(1.4, 2.6))
    db = sphere("Fizz", p0, random.uniform(0.04, 0.09), bubble_m, sub=1)
    f0 = S[16] + 2 + k
    key_loc(db, [(f0, p0), (f0 + 16, p1)])
    keyscale(db, [(0, 0.001), (f0 - 1, 0.001), (f0, 1.0), (f0 + 15, 1.0), (f0 + 17, 0.001)])
bends = text("Bends", "THE BENDS", (DX, DY - 0.6, 2.75), 0.3, lab_m, extrude=0.03)
pop(bends, S[16] + 22, 5, S[17] + 2)

# ---------------- line 17: big question mark over his head ----------------
q = text("Q", "?", (0.0, MY - 0.2, 4.55), 0.9, lab_m, extrude=0.08)
pop(q, S[17] + 2, 6)
q.rotation_euler = (math.radians(90), 0, 0); q.keyframe_insert("rotation_euler", frame=S[17] + 2)
q.rotation_euler = (math.radians(90), 0, math.radians(360)); q.keyframe_insert("rotation_euler", frame=FRAMES)

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

cam_keys = [
    (0,          (1.0, -3.4, 4.0),    (-0.8, 1.4, 2.4)),           # hook: man in his chair, IV in his arm
    (S[1] - 6,   (-1.6, -1.3, 3.0),   (-2.3, 1.1, 2.15)),          # bubble slides down the line
    (S[1] + 4,   (1.6, -1.6, 2.3),    (1.7, 0.6, 1.55)),           # movies say...
    (S[2] - 2,   (0.9, -1.5, 2.4),    (1.4, 0.6, 1.6)),
    (S[2] + 6,   (-1.75, -0.2, 2.5),  (-1.95, 1.3, 2.05)),         # tiny bubble in his arm vein + check
    (S[3] - 2,   (-2.2, -0.2, 2.5),   (-1.95, 1.3, 2.05)),
    (S[3] + 6,   (-2.0, -0.9, 3.0),   (-2.55, 0.9, 2.5)),          # IV drip sneaks a few in
    (S[4] - 2,   (-2.7, -0.8, 2.8),   (-2.4, 1.1, 2.15)),
    (S[4] + 4,   (-2.0, 0.0, 2.45),   (-1.7, 1.33, 2.0)),          # carried along the arm...
    (S[5] - 2,   (-0.5, 0.0, 2.9),    (-0.5, 1.45, 2.5)),          # ...up to the heart
    (S[5] + 4,   (0.05, 0.3, 2.4),    (0.06, 1.28, 2.2)),          # heart pumps it to the lungs
    (S[6] - 2,   (0.25, 0.3, 2.55),   (0.18, 1.28, 2.3)),
    (S[6] + 4,   (0.55, 0.35, 2.6),   (0.25, 1.3, 2.4)),           # lungs = bubble filter
    (S[7] - 2,   (0.0, 0.35, 2.6),    (0.2, 1.3, 2.4)),
    (S[7] + 4,   (0.38, 0.62, 2.48),  (NX, NY, NZ)),               # trapped in the tiny vessels
    (S[8] - 2,   (0.22, 0.62, 2.5),   (NX, NY, NZ)),
    (S[8] + 4,   (0.3, -0.2, 3.0),    (0.15, 1.3, 2.9)),           # dissolves, breathed out
    (S[9] - 2,   (-0.2, -0.6, 3.6),   (0.0, 1.5, 3.25)),
    (S[9] + 4,   (-2.5, -0.9, 3.1),   (-2.0, 1.2, 2.15)),          # big rush of air
    (S[10] - 2,  (-1.2, -0.5, 3.0),   (-1.0, 1.4, 2.2)),
    (S[10] + 4,  (0.0, 0.42, 2.25),   (HCX, HCY, HCZ)),            # foam in the heart
    (S[11] - 2,  (0.15, 0.45, 2.3),   (HCX, HCY, HCZ)),
    (S[11] + 4,  (0.3, -1.6, 3.6),    (0.0, 1.3, 3.0)),            # air lock, STOP
    (S[12] - 2,  (-0.3, -1.8, 3.7),   (0.0, 1.3, 3.0)),
    (S[12] + 4,  (-2.4, -1.9, 2.9),   (-3.1, 0.4, 2.2)),           # nurse flicks
    (S[13] - 2,  (-3.6, -1.7, 3.0),   (-3.0, 0.4, 2.5)),
    (S[13] + 4,  (-2.6, -0.8, 2.4),   (PUX, IVY, PZ_)),            # IV pump alarm
    (S[14] - 2,  (-3.6, -0.7, 2.4),   (PUX, IVY, PZ_)),
    (S[14] + 4,  (1.3, -1.2, 3.6),    (0.4, 1.3, 2.9)),            # oxygen mask
    (S[15] - 2,  (0.0, -1.3, 3.6),    (0.3, 1.3, 2.8)),
    (S[15] + 4,  (5.2, 0.4, 3.4),     (CX - 0.6, CY, CZ)),         # pressure chamber
    (S[16] - 2,  (2.6, 0.6, 3.4),     (CX, CY, CZ)),
    (S[16] + 4,  (-5.0, 3.4, 2.0),    (DX, DY, 1.9)),              # diver, the bends
    (S[17] - 2,  (-6.9, 3.5, 2.0),    (DX, DY, 1.8)),
    (S[17] + 6,  (0.6, -3.0, 4.0),    (0.0, 1.5, 3.0)),            # final: myth?
    (FRAMES - 1, (1.4, -4.0, 4.6),    (0.2, 1.5, 3.0)),
]

def overhead(cl, tl):
    dx, dy = cl[0] - tl[0], cl[1] - tl[1]
    hd = math.hypot(dx, dy)
    if cl[2] > 60 or hd > 40:
        return cl
    z = max(cl[2], tl[2] + 0.62 * hd)
    return (cl[0], cl[1], z)
cam_keys = [(f, overhead(cl, tl), tl) for f, cl, tl in cam_keys]
for f, cl, tl in cam_keys:
    cam.location = cl; cam.keyframe_insert("location", frame=f)
    target.location = tl; target.keyframe_insert("location", frame=f)

for o in bpy.data.objects:
    if o.type == 'FONT':
        o.visible_shadow = False
bpy.ops.wm.save_as_mainfile(filepath=f"{HERE}/scene.blend")
print("SCENE OK", FRAMES, S)
