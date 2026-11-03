# Day 9 — What if a blue whale met a billion krill?  Build: python3 episodes/009-whale-krill/scene.py
# Reference style: base (helpers, lawn/soil, house, garden) copied from episodes/003-lift-million-ref/scene.py
import bpy, math, random, os, json
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
random.seed(9)
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
bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 0, -0.003))
fp = bpy.context.object; fp.scale = (400000, 400000, 1); fp.location = (0, 200050, -0.008)
fp.data.materials.append(far)
stone_m = mat("Stone", (0.7, 0.66, 0.6), 0.8)
for i in range(30):
    sphere("Peb", (random.uniform(-30, 30), FRONT_Y - 0.02, random.uniform(-5.6, -0.6)), random.uniform(0.12, 0.3),
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
POX, POY = -8.0, 9.5
box("PoolRim", (POX, POY, 0.03), (6.4, 3.8, 0.1), mat("PoolRimM", (0.9, 0.88, 0.82), 0.7))
box("PoolWater", (POX, POY, 0.06), (5.8, 3.2, 0.06), mat("PoolWaterM", (0.25, 0.7, 0.85), 0.05, emit=(0.2, 0.6, 0.8), emit_strength=0.25))

# =====================================================================================
# Day 9 — What if a blue whale met a billion krill?
# Numbers: Antarctic krill ~6 cm, roughly 1 g (adults ~0.5-2 g).
#   1,000 krill ~ 1 kg; 1,000,000 ~ 1 tonne (a small car); 1,000,000,000 ~ 1,000 tonnes (~1,000 m3 -> a ~10 m cube).
#   Blue whale ~25 m, ~150 t -> 1,000 t ~ 7 blue whales. Backyard pool ~50 m3 -> ~20 pools.
#   One lunge engulfs water roughly equal to the whale's own body mass (Goldbogen et al.).
#   Up to ~16 t of krill per day while feeding (Savoca et al. 2021) ~ 16 million krill -> 1e9 in ~62 days (~2 months).
#   Krill swarms can stretch for kilometres and hold far more than 1,000 t.
# =====================================================================================
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

# ---------------- krill prototype mesh (length 1 along +x, head at +x) ----------------
krill_m = mat("Krill", (0.98, 0.42, 0.34), 0.45, emit=(0.9, 0.25, 0.2), emit_strength=0.12)
krill_d = mat("KrillD", (0.85, 0.25, 0.22), 0.5)
photo_m = glow_mat("Photo", (0.3, 0.8, 1.0), 4.0)
kparts = [sphere("Kc", (0.22, 0, 0.0), 1.0, krill_m, scale=(0.3, 0.12, 0.13), sub=2)]
for k, (x, r, z) in enumerate([(-0.04, 0.11, -0.01), (-0.17, 0.095, -0.03), (-0.29, 0.08, -0.06), (-0.39, 0.065, -0.1)]):
    kparts.append(sphere("Ks", (x, 0, z), r, krill_m if k % 2 == 0 else krill_d, scale=(0.9, 1.0, 1.0), sub=2))
kparts.append(sphere("Kt", (-0.48, 0, -0.14), 1.0, krill_m, scale=(0.08, 0.11, 0.025), sub=2))
for sy in (-1, 1):
    kparts.append(sphere("Ke", (0.5, sy * 0.065, 0.05), 0.05, eyeb, sub=2))
    kparts.append(sphere("Kh", (0.53, sy * 0.08, 0.07), 0.015, eyew, sub=1))
for sy in (-1, 1):
    bpy.ops.mesh.primitive_cylinder_add(vertices=6, radius=0.008, depth=0.42, location=(0.7, sy * 0.08, 0.13),
                                        rotation=(sy * -0.25, math.radians(60), 0))
    o = bpy.context.object; o.data.materials.append(krill_d); kparts.append(o)
    for j in range(5):
        bpy.ops.mesh.primitive_cylinder_add(vertices=5, radius=0.01, depth=0.14, location=(0.25 - j * 0.09, sy * 0.06, -0.15),
                                            rotation=(sy * 0.4, 0, 0))
        o = bpy.context.object; o.data.materials.append(krill_m); kparts.append(o)
for j in range(4):
    kparts.append(sphere("Kp", (0.15 - j * 0.12, 0, -0.12 - j * 0.01), 0.022, photo_m, sub=1))
bpy.ops.object.select_all(action='DESELECT')
for o in kparts:
    o.select_set(True)
bpy.context.view_layer.objects.active = kparts[0]
bpy.ops.object.join()
KPROTO = bpy.context.object; KPROTO.name = "KrillProto"
bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
KPROTO.location = (0, 0, -500)          # parked below the world
KMESH = KPROTO.data
def krill(name, loc, size, rz=0.0, ry=0.0, parent=None):
    o = bpy.data.objects.new(name, KMESH); sc.collection.objects.link(o)
    o.location = loc; o.scale = (size,) * 3; o.rotation_euler = (0, ry, rz)
    if parent is not None:
        o.parent = parent
    return o

# krill-pile texture (pink with dark eye dots) for the mound / cube / crates / pools
def krill_tex(name, scale=4.0, dot=0.08):
    m = bpy.data.materials.new(name); m.use_nodes = True
    N = m.node_tree.nodes; L = m.node_tree.links
    bs = N["Principled BSDF"]; bs.inputs["Roughness"].default_value = 0.5
    tc = N.new("ShaderNodeTexCoord")
    nz = N.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = scale * 1.5; nz.inputs["Detail"].default_value = 4
    L.new(tc.outputs["Object"], nz.inputs["Vector"])
    cr = N.new("ShaderNodeValToRGB"); e = cr.color_ramp.elements
    e[0].position = 0.35; e[0].color = (0.82, 0.24, 0.2, 1); e[1].position = 0.65; e[1].color = (1.0, 0.55, 0.45, 1)
    L.new(nz.outputs["Fac"], cr.inputs["Fac"])
    vo = N.new("ShaderNodeTexVoronoi"); vo.inputs["Scale"].default_value = scale
    L.new(tc.outputs["Object"], vo.inputs["Vector"])
    lt = N.new("ShaderNodeMath"); lt.operation = 'LESS_THAN'; lt.inputs[1].default_value = dot
    L.new(vo.outputs["Distance"], lt.inputs[0])
    mx = N.new("ShaderNodeMix"); mx.data_type = 'RGBA'
    L.new(lt.outputs[0], mx.inputs["Factor"]); L.new(cr.outputs["Color"], mx.inputs[6])
    mx.inputs[7].default_value = (0.05, 0.03, 0.03, 1)
    L.new(mx.outputs[2], bs.inputs["Base Color"])
    bs.inputs["Emission Color"].default_value = (0.9, 0.3, 0.25, 1); bs.inputs["Emission Strength"].default_value = 0.12
    bmp = N.new("ShaderNodeBump"); bmp.inputs["Strength"].default_value = 0.5
    L.new(vo.outputs["Distance"], bmp.inputs["Height"]); L.new(bmp.outputs["Normal"], bs.inputs["Normal"])
    return m
ktex_s = krill_tex("KTexS", 40.0, 0.09)    # small heap (1 kg)
ktex_m = krill_tex("KTexM", 9.0, 0.09)     # 1 tonne mound, crates, pools
ktex_l = krill_tex("KTexL", 3.0, 0.08)     # 10 m cube

# ---------------- "you": cartoon person (from day 8) + snorkel mask for the ending ----------------
skin_m = mat("Skin", (0.95, 0.74, 0.58), 0.6)
pants_m = mat("Pants", (0.2, 0.3, 0.6), 0.8)
shoe_m = mat("Shoe", (0.15, 0.15, 0.18), 0.6)
shirt_m = mat("ShirtY", (0.2, 0.7, 0.75), 0.7)
hair_m = mat("HairY", (0.28, 0.16, 0.07), 0.8)
K = 0.86
PX0, PY0 = -1.3, -0.6
you = group("You", (PX0, PY0, 0))
def P_(dx, dy, dz):
    return (PX0 + dx * K, PY0 + dy * K, dz * K)
yp, legs, arms = [], [], []
for sx in (-1, 1):
    lg = group("LegG", P_(sx * 0.13, 0, 0.78))
    attach([tube("Leg", [P_(sx * 0.13, 0, 0.8), P_(sx * 0.14, 0, 0.08)], [0.1 * K, 0.09 * K], pants_m),
            box("ShoeP", P_(sx * 0.14, -0.06, 0.05), (0.17 * K, 0.3 * K, 0.1 * K), shoe_m, bevel=0.03)], lg)
    legs.append(lg)
for sx in (-1, 1):
    ag = group("ArmG", P_(sx * 0.3, 0, 1.33))
    attach([tube("Arm", [P_(sx * 0.3, 0, 1.35), P_(sx * 0.38, -0.03, 1.05), P_(sx * 0.38, -0.06, 0.8)], [0.07 * K] * 3, shirt_m),
            sphere("Hand", P_(sx * 0.38, -0.06, 0.76), 0.068 * K, skin_m, sub=2)], ag)
    arms.append(ag)
    yp.append(sphere("EyeWp", P_(sx * 0.085, -0.21, 1.72), 0.055 * K, eyew, scale=(1, 0.6, 1.2), sub=2))
    yp.append(sphere("EyeBp", P_(sx * 0.085, -0.25, 1.72), 0.028 * K, eyeb, sub=1))
yp.append(sphere("Torso", P_(0, 0, 1.1), 1.0, shirt_m, scale=(0.3 * K, 0.22 * K, 0.4 * K), sub=3))
yp.append(sphere("Head", P_(0, 0, 1.68), 0.25 * K, skin_m, sub=3))
yp.append(sphere("HairP", P_(0, 0.04, 1.81), 0.24 * K, hair_m, scale=(1.05, 1.0, 0.55), sub=2))
yp.append(tube("Smile", [P_(-0.08, -0.23, 1.6), P_(0, -0.26, 1.56), P_(0.08, -0.23, 1.6)], [0.014 * K] * 3, eyeb))
mask_g = group("Mask", P_(0, -0.2, 1.72))
glass_m = mat("Glass", (0.55, 0.85, 1.0), 0.1, emit=(0.4, 0.8, 1.0), emit_strength=0.4)
mps_ = [box("MaskFrame", P_(0, -0.22, 1.72), (0.36 * K, 0.06 * K, 0.2 * K), mat("MaskF", (1.0, 0.85, 0.1), 0.5), bevel=0.02),
        box("MaskGlass", P_(0, -0.255, 1.72), (0.3 * K, 0.02 * K, 0.15 * K), glass_m),
        tube("Snorkel", [P_(0.24, -0.1, 1.6), P_(0.27, -0.05, 1.75), P_(0.27, -0.02, 2.05)], [0.03 * K] * 3, mat("SnorkM", (1.0, 0.4, 0.1), 0.5))]
attach(mps_, mask_g)
attach(yp + legs + arms + [mask_g], you)

# ---------------- props: garden table, kitchen scale, small car ----------------
TX, TY, TZ = -3.0, -0.3, 0.72
table_m = mat("Table", (0.96, 0.96, 0.94), 0.5)
tbl = group("Table", (TX, TY, 0))
tps = [cyl("TableTop", (TX, TY, TZ - 0.02), 0.45, 0.04, table_m, verts=32), cyl("TableLeg", (TX, TY, TZ / 2), 0.04, TZ, table_m, verts=10),
       cyl("TableFoot", (TX, TY, 0.02), 0.25, 0.04, table_m, verts=24)]
attach(tps, tbl)
SCH = 0.035
scale_g = group("Scale", (TX, TY, TZ))
dispg = mat("Disp", (0.05, 0.08, 0.06), 0.3)
dgreen = mat("DispG", (0.3, 1.0, 0.4), 0.3, emit=(0.3, 1.0, 0.4), emit_strength=2.5)
sps = [box("ScaleB", (TX, TY, TZ + SCH / 2), (0.2, 0.2, SCH), mat("ScaleM", (0.95, 0.4, 0.45), 0.4), bevel=0.008),
       box("ScaleTop", (TX, TY, TZ + SCH + 0.002), (0.17, 0.17, 0.004), mat("ScaleT", (0.85, 0.87, 0.9), 0.2, metal=0.6)),
       box("ScaleDisp", (TX, TY - 0.101, TZ + SCH * 0.5), (0.1, 0.004, 0.024), dispg)]
attach(sps, scale_g)
d1g = text("Disp1g", "1 g", (TX, TY - 0.105, TZ + SCH * 0.5 - 0.008), 0.018, dgreen)
d1kg = text("Disp1kg", "1 kg", (TX, TY - 0.105, TZ + SCH * 0.5 - 0.008), 0.018, dgreen)

CARX, CARY = 3.4, 0.1
car_m = mat("Car", (0.98, 0.75, 0.12), 0.35)
tire_m = mat("Tire", (0.08, 0.08, 0.09), 0.8)
car = group("Car", (CARX, CARY, 0))
cps = [box("CarBody", (CARX, CARY, 0.6), (3.4, 1.6, 0.65), car_m, bevel=0.12),
       box("CarCab", (CARX - 0.2, CARY, 1.2), (1.9, 1.4, 0.6), car_m, bevel=0.12),
       box("CarWin", (CARX - 0.2, CARY - 0.71, 1.2), (1.6, 0.02, 0.42), win_m),
       box("CarWinF", (CARX + 0.76, CARY, 1.2), (0.02, 1.2, 0.42), win_m)]
for dx in (-1.1, 1.1):
    for dy in (-0.78, 0.78):
        cps.append(cyl("Wheel", (CARX + dx, CARY + dy, 0.33), 0.33, 0.24, tire_m, rot=(math.radians(90), 0, 0), verts=20))
for sy in (-0.5, 0.5):
    cps.append(sphere("Lamp", (CARX + 1.7, CARY + sy, 0.68), 0.12, white_lab, sub=2))
attach(cps, car)

# ---------------- the whale ----------------
whale_m = mat("Whale", (0.24, 0.4, 0.62), 0.45)
whale_spot = mat("WhaleSpot", (0.42, 0.58, 0.78), 0.5)
groove_m = stripe_mat("Grooves", (0.82, 0.88, 0.95), (0.5, 0.62, 0.78), axis="Y", freq=9.0, thresh=0.55, rough=0.5)
mouth_m = mat("Mouth", (0.75, 0.22, 0.3), 0.5)
baleen_m = stripe_mat("Baleen", (0.12, 0.1, 0.1), (0.35, 0.3, 0.25), axis="X", freq=18.0, thresh=0.2, rough=0.8)
WS = 0.85
def whale(name, loc, rz=0.0, s=WS):
    g = group(name, (0, 0, 0))
    ps = [sphere(name + "Body", (0, 0, 0.4), 1.0, whale_m, scale=(11.0, 2.3, 2.2), sub=4)]
    ps.append(cyl(name + "Tail", (-12.0, 0, 0.5), 1.6, 8.0, whale_m, rot=(0, math.radians(-90), 0), r2=0.45, verts=24))
    for sy in (-1, 1):
        ps.append(sphere(name + "Fluke", (-16.4, sy * 1.9, 0.5), 1.0, whale_m, scale=(1.3, 2.2, 0.18), sub=3))
        ps[-1].rotation_euler = (0, 0, sy * 0.4)
        ps.append(sphere(name + "Flip", (3.5, sy * 2.4, -1.0), 1.0, whale_m, scale=(2.2, 0.55, 0.16), sub=3))
        ps[-1].rotation_euler = (sy * 0.5, 0.2, sy * -0.5)
        ps.append(sphere(name + "EyeW", (7.4, sy * 1.55, 0.55), 0.5, eyew, sub=3))
        ps.append(sphere(name + "EyeB", (7.62, sy * 1.92, 0.6), 0.27, eyeb, sub=2))
        ps.append(sphere(name + "EyeH", (7.7, sy * 2.12, 0.72), 0.08, white_lab, sub=1))
    ps.append(cyl(name + "Dorsal", (-7.5, 0, 2.4), 0.6, 1.2, whale_m, rot=(0, -0.6, 0), r2=0.05, verts=12))
    for k in range(10):
        ps.append(sphere(name + "Spot", (random.uniform(-7, 6), random.uniform(-0.9, 0.9), 2.45), random.uniform(0.25, 0.5),
                         whale_spot, scale=(1.4, 1.0, 0.25), sub=2))
    ps.append(box(name + "Baleen", (6.0, 0, -1.45), (6.6, 2.4, 0.5), baleen_m))
    jaw = group(name + "Jaw", (-1.5, 0, -0.4))
    pouch = sphere(name + "Pouch", (4.0, 0, -1.1), 1.0, groove_m, scale=(7.2, 2.05, 1.25), sub=4)
    tongue = sphere(name + "Tongue", (5.0, 0, -0.1), 1.0, mouth_m, scale=(5.2, 1.6, 0.3), sub=3)
    attach([pouch, tongue], jaw)
    attach(ps + [jaw], g)
    g.location = loc; g.rotation_euler = (0, 0, rz); g.scale = (s,) * 3
    return g, jaw, pouch
def mouth_world(gloc, rz=0.0):
    return (gloc[0] + 9.6 * WS * math.cos(rz), gloc[1] + 9.6 * WS * math.sin(rz), gloc[2] - 0.8 * WS)

WH0 = (-4.0, 7.0, 5.5)
hero, hjaw, hpouch = whale("Hero", WH0)
CLOUD = Vector((14.0, 7.0, 4.5))

# =============== line 0: hook — a whale with its mouth open next to a pink cloud of krill ===============
cloud = group("Cloud", tuple(CLOUD))
cloud_k = []
for i in range(300):
    v = Vector((random.gauss(0, 1), random.gauss(0, 1), random.gauss(0, 0.7)))
    v = v.normalized() * (random.random() ** 0.6) * 3.0
    ko = krill(f"CK{i}", tuple(v), random.uniform(0.5, 0.7), rz=random.uniform(2.2, 4.0), ry=random.uniform(-0.3, 0.3), parent=cloud)
    cloud_k.append((ko, v))
water_m = mat("WaterBlob", (0.45, 0.8, 1.0), 0.05, emit=(0.3, 0.7, 1.0), emit_strength=0.25)
water_m.node_tree.nodes["Principled BSDF"].inputs["Alpha"].default_value = 0.28
blob = sphere("Blob", tuple(CLOUD), 3.7, water_m, sub=4)
blob.visible_shadow = False
keyscale(cloud, [(0, 1.0), (S[1] - 1, 1.0), (S[1], 0.001), (S[9] + 4, 0.001), (S[9] + 10, 1.0)])
keyscale(blob, [(0, 0.001), (S[9] + 6, 0.001), (S[9] + 12, 1.0)])
key_loc(cloud, [(0, (10.5, 7.0, 5.4)), (S[1] - 2, (9.8, 7.0, 5.2)), (S[1] - 1, tuple(CLOUD))])
keyrot(cloud, [(0, (0, 0, 0)), (S[1], (0, 0, 0.5)), (S[10], (0, 0, 0.9))])
V0 = ((9.0, -8.0, 7.0), (6.5, 7.0, 4.8))
CAM0 = CL(V0)
label("LHook", "1,000,000,000", SP(V0, 16, 0.25), 0.95, pink_lab, 2, S[1], face=CAM0)
label("LHook2", "KRILL?", SP(V0, 16, 0.33), 0.95, white_lab, 6, S[1], face=CAM0)
# whale: mouth open in the hook, hidden from line 1 to line 9, then swims in
keyscale(hero, [(0, WS), (S[1] - 1, WS), (S[1], 0.001), (S[9] - 1, 0.001), (S[9], WS)])
keyrot(hjaw, [(0, (0, 0.0, 0)), (8, (0, 0.55, 0)), (S[1] - 2, (0, 0.5, 0)), (S[1], (0, 0, 0))])
key_loc(hero, [(0, (WH0[0] - 3, WH0[1], WH0[2])), (S[1] - 1, WH0), (S[9], (-40.0, 7.0, 6.5)), (S[10] - 2, WH0)])

# ---------------- lines 1-3: one krill on the garden table (6 cm), 1 g on a scale, 1,000 krill = 1 kg ----------------
hk = krill("HeroKrill", (TX, TY, TZ + 0.012), 0.06, rz=-0.35)
key_loc(hk, [(S[1], (TX + 0.05, TY + 0.1, TZ + 0.12)), (S[1] + 12, (TX, TY, TZ + 0.012)),
             (S[2], (TX, TY, TZ + 0.012)), (S[2] + 4, (TX, TY, TZ + 0.05)), (S[2] + 7, (TX, TY, TZ + SCH + 0.014)),
             (S[3] + 8, (TX, TY, TZ + SCH + 0.014)), (S[3] + 14, (TX, TY - 0.02, TZ + SCH + 0.075))])
keyrot(hk, [(S[1], (0, -0.5, 0.4)), (S[1] + 6, (0, 0, -0.35)), (S[2] + 4, (0, -0.3, -0.35)), (S[2] + 7, (0, 0, -0.35))])
hide_until(hk, S[1])
gone_at(hk, S[4], 1)
ruler_m = mat("Ruler", (1.0, 0.82, 0.15), 0.5)
rg = group("Ruler", (TX, TY - 0.05, TZ))
rps = [box("RulerB", (TX, TY - 0.05, TZ + 0.002), (0.075, 0.018, 0.004), ruler_m)]
for k in range(7):
    rps.append(box("Tick", (TX - 0.03 + k * 0.01, TY - 0.055, TZ + 0.005), (0.001, 0.008, 0.001), eyeb))
attach(rps, rg)
pop(rg, S[1] + 6, 4, S[2])
FC1 = (TX + 0.15, TY - 0.4, 1.0)
V1 = ((TX + 0.14, TY - 0.26, 0.9), (TX, TY, TZ + 0.03))
V2 = ((TX + 0.22, TY - 0.42, 1.0), (TX, TY, TZ + 0.04))
V3 = ((TX - 0.2, TY - 0.5, 1.05), (TX, TY, TZ + 0.06))
label("L6cm", "6 cm", SP(V1, 0.3, 0.3), 0.04, lab_m, S[1] + 8, S[2], face=CL(V1))
burst((TX, TY - 0.02, TZ + 0.03), S[1] + 6, 10, 0.05, 0.004, S[1] + 14)
pop(scale_g, S[2], 5, S[4])
pop(d1g, S[2] + 6, 3, S[3] + 6)
label("L1g", "1 GRAM", SP(V2, 0.4, 0.28), 0.05, lab_m, S[2] + 6, S[3], face=CL(V2))
heap = group("Heap", (TX, TY, TZ + SCH))
hps = [sphere("HeapCore", (TX, TY, TZ + SCH), 1.0, ktex_s, scale=(0.075, 0.075, 0.05), sub=3)]
for i in range(70):
    a = random.uniform(0, 6.283); r = random.uniform(0, 1) ** 0.6
    x, y = TX + 0.075 * r * math.cos(a), TY + 0.075 * r * math.sin(a)
    z = TZ + SCH + 0.05 * math.sqrt(max(0, 1 - r * r)) + 0.004
    hps.append(krill(f"HK{i}", (x, y, z), 0.05, rz=random.uniform(0, 6.283), ry=random.uniform(-0.4, 0.4)))
attach(hps, heap)
pop(heap, S[3] + 2, 8, S[4])
pop(d1kg, S[3] + 8, 3, S[4])
label("L1000", "1,000 KRILL", SP(V3, 0.45, 0.25), 0.045, white_lab, S[3] + 2, S[4], face=CL(V3))
label("L1kg", "≈ 1 kg", SP(V3, 0.45, 0.34), 0.055, lab_m, S[3] + 8, S[4], face=CL(V3))
gone_at(tbl, S[4] + 1, 1)

# ---------------- line 4: a million krill = a 1-tonne mound, as heavy as a small car ----------------
MX, MY = 0.75, -0.55
mound = group("Mound", (MX, MY, 0))
mnd = [sphere("MoundCore", (MX, MY, 0), 1.0, ktex_m, scale=(0.78, 0.78, 0.85), sub=4)]
for i in range(160):
    v = Vector((random.gauss(0, 1), random.gauss(0, 1), abs(random.gauss(0, 1)))).normalized()
    p = (MX + v.x * 0.8, MY + v.y * 0.8, v.z * 0.87)
    mnd.append(krill(f"MK{i}", p, 0.16, rz=random.uniform(0, 6.283), ry=random.uniform(-0.6, 0.6)))
attach(mnd, mound)
key_loc(mound, [(S[4] + 1, (MX, MY, 6.0)), (S[4] + 8, (MX, MY, 0))])
hide_until(mound, S[4] + 1)
burst((MX, MY - 0.4, 0.3), S[4] + 8, 14, 1.2, 0.06, S[4] + 18, krill_m)
CAM4 = (1.9, -8.2, 3.3)
label("L1M", "1,000,000 KRILL", (MX, MY, 2.55), 0.3, white_lab, S[4] + 4, S[5], face=CAM4)
label("L1T", "≈ 1 TON", (MX, MY, 2.1), 0.36, lab_m, S[4] + 9, S[5], face=CAM4)
label("LCar", "CAR ≈ 1 TON", (CARX, CARY, 2.2), 0.3, pink_lab, S[4] + 14, S[5], face=CAM4)
keyrot(car, [(S[4] + 8, (0, 0, 0)), (S[4] + 10, (0.06, 0, 0)), (S[4] + 13, (0, 0, 0))])   # the thud rocks the car

# ---------------- lines 5-6: a BILLION krill = a ~10 m pink cube slams into the garden ----------------
CUBE_R = 18.5          # right face x (the cube is eaten from the left later, so it shrinks toward this face)
CY_, CS = 8.0, 10.0
cube = group("KCube", (CUBE_R, CY_, 0))
cbs = [box("KCubeB", (CUBE_R - CS / 2, CY_, CS / 2), (CS, CS, CS), ktex_l, bevel=0.2)]
for i in range(110):
    if i < 70:
        p = (CUBE_R - CS + 0.3 + random.uniform(0, CS - 0.6), CY_ - CS / 2 - 0.12, random.uniform(0.3, CS - 0.3))
        rz_ = random.uniform(-0.5, 0.5) + math.pi * random.randint(0, 1); ry_ = math.radians(90) * random.choice((-1, 1)) * 0.0
        ko = krill(f"FK{i}", p, 0.75, rz=rz_, ry=random.uniform(-0.6, 0.6))
        ko.rotation_euler = (math.radians(90), random.uniform(-0.6, 0.6), random.uniform(-0.3, 0.3) + (math.pi if i % 2 else 0))
    else:
        p = (CUBE_R - CS + 0.3 + random.uniform(0, CS - 0.6), CY_ - CS / 2 + random.uniform(0.3, CS - 0.3), CS + 0.1)
        ko = krill(f"FK{i}", p, 0.75, rz=random.uniform(0, 6.283))
    cbs.append(ko)
attach(cbs, cube)
CUBE_C = (CUBE_R - CS / 2, CY_, CS / 2)
key_loc(cube, [(S[5] + 1, (CUBE_R, CY_, 70.0)), (S[5] + 8, (CUBE_R, CY_, -0.4)), (S[5] + 11, (CUBE_R, CY_, 0.0))])
hide_until(cube, S[5] + 1)
burst((CUBE_C[0], CY_ - CS / 2 - 0.5, 0.8), S[5] + 8, 18, 6.0, 0.35, S[5] + 18, krill_m)
V5 = ((5.0, -25.0, 14.0), (9.0, 5.0, 2.5))
CAM5 = CL(V5)
label("L1B", "1,000,000,000", SP(V5, 24, 0.25), 1.3, pink_lab, S[5] + 4, S[7], face=CAM5)
label("L1BK", "KRILL", SP(V5, 24, 0.33), 1.15, white_lab, S[5] + 6, S[6], face=CAM5)
label("L1000T", "≈ 1,000 TONS", SP(V5, 24, 0.33), 1.15, lab_m, S[6] + 2, S[7], face=CAM5)

# ---------------- line 7: as heavy as ~7 blue whales (they float in a row behind the house) ----------------
V7 = ((-8.0, -24.0, 33.0), (-8.0, 37.0, 4.0))
CAM7 = CL(V7)
seven = []
for i in range(7):
    wx = -24.0 + i * 5.3
    wg, wj, wp_ = whale(f"W7_{i}", (wx, 37.0, 4.0), rz=math.radians(-90))
    f_in = S[7] + 2 + i * 2
    keyscale(wg, [(0, 0.001), (f_in - 1, 0.001), (f_in + 3, WS * 1.12), (f_in + 6, WS), (S[8] + 6, WS), (S[8] + 10, 0.001)])
    key_loc(wg, [(f_in - 1, (wx, 37.0, 14.0)), (f_in + 6, (wx, 37.0, 4.0)), (S[8] + 10, (wx, 37.0, 4.6))])
    label(f"L7n{i}", str(i + 1), (wx, 26.0, 9.0), 2.6, lab_m if i < 6 else red_lab, f_in + 2, S[8] + 4, face=CAM7)
    seven.append(wg)
label("L7W", "≈ 7 BLUE WHALES", SP(V7, 30, 0.25), 1.45, white_lab, S[7] + 8, S[8] + 4, face=CAM7)

# ---------------- line 8: they'd fill 20 backyard pools ----------------
pink_pool = krill_tex("PoolPink", 9.0, 0.09)
pw = bpy.data.materials["PoolWaterM"].node_tree.nodes["Principled BSDF"].inputs["Base Color"]
for f, c in [(0, (0.25, 0.7, 0.85, 1)), (S[8] + 2, (0.25, 0.7, 0.85, 1)), (S[8] + 6, (1.0, 0.45, 0.4, 1))]:
    pw.default_value = c; pw.keyframe_insert("default_value", frame=f)
k = 0
rim_m = bpy.data.materials["PoolRimM"]
for r in range(4):
    for c in range(5):
        if r == 0 and c == 0:
            continue
        px, py = -24.0 + c * 7.4, 26.0 + r * 4.8
        pg = group(f"Pool{k}", (px, py, 0))
        attach([box("PRim", (px, py, 0.05), (6.4, 3.8, 0.1), rim_m), box("PWat", (px, py, 0.1), (5.8, 3.2, 0.06), pink_pool)], pg)
        pop(pg, S[8] + 6 + k, 3)
        k += 1
V8 = ((-10.0, -22.0, 40.0), (-9.0, 34.0, 0.0))
CAM8 = CL(V8)
label("L20", "× 20 POOLS", SP(V8, 30, 0.28), 1.9, pink_lab, S[8] + 4, S[9], face=CAM8)
keyscale(cube, [(S[8] + 2, 1.0), (S[8] + 14, (1.0, 1.0, 0.001)), (S[8] + 15, 0.001), (S[14], 0.001)])

# ---------------- lines 9-11: a hungry blue whale gulps the krill cloud ----------------
V9 = ((20.0, -22.0, 10.0), (2.0, 7.0, 4.0))
CAM9 = CL(V9)
label("LBW", "BLUE WHALE ≈ 25 m", SP(V9, 26, 0.28), 1.05, white_lab, S[9] + 14, S[10], face=CAM9)
LUNGE = S[11] - 2
WH1 = (2.0, 7.0, 5.5)
key_loc(hero, [(S[10], WH0), (LUNGE, WH1)])
keyrot(hjaw, [(S[10], (0, 0, 0)), (S[10] + 12, (0, 0.75, 0)), (S[11] + 4, (0, 0.7, 0)), (S[11] + 14, (0, 0.1, 0)),
              (S[11] + 4, (0, 0.12, 0)), (S[12], (0, 0.0, 0))])
P0 = tuple(hpouch.scale)
keyscale(hpouch, [(S[10] + 12, P0), (S[11] + 8, (P0[0] * 1.05, P0[1] * 1.35, P0[2] * 2.3)), (S[12] - 2, (P0[0] * 1.05, P0[1] * 1.35, P0[2] * 2.3)),
                  (S[12] + 6, P0)])
MOUTH1 = Vector(mouth_world(WH1))
for j, (ko, v) in enumerate(cloud_k):
    f0 = S[10] + 6 + int(j / len(cloud_k) * 20)
    ko.keyframe_insert("location", frame=f0); ko.keyframe_insert("scale", frame=f0)
    ko.location = tuple(MOUTH1 - CLOUD + Vector((random.uniform(-1, 1), random.uniform(-1, 1), random.uniform(-0.5, 0.5))))
    ko.keyframe_insert("location", frame=f0 + 14)
    ko.scale = (0.001,) * 3; ko.keyframe_insert("scale", frame=f0 + 14)
key_loc(blob, [(S[10] + 10, tuple(CLOUD)), (S[11] + 6, tuple(MOUTH1))])
keyscale(blob, [(S[10] + 10, 1.0), (S[11] + 6, 0.001)])
V10 = ((22.0, -15.0, 8.0), (8.0, 7.0, 4.0))
label("LGulp", "GULP!", SP(V10, 20, 0.28), 1.6, red_lab, S[10] + 8, S[11], face=CL(V10))
# line 11: a water ball the same size as the whale's body appears next to it
V11 = ((18.0, -20.0, 9.0), (2.0, 7.0, 6.0))
CAM11 = CL(V11)
eq = sphere("EqBlob", (2.5, 7.0, 13.6), 3.3, mat("EqWater", (0.4, 0.75, 1.0), 0.05, emit=(0.3, 0.6, 1.0), emit_strength=0.35), sub=4)
pop(eq, S[11] + 2, 6, S[12] + 2)
label("LEqG", "WATER GULP", (2.5, 7.0, 17.6), 1.2, white_lab, S[11] + 4, S[12] + 2, face=CAM11)
label("LEq", "≈ WHALE'S WEIGHT", SP(V11, 30, 0.27), 1.3, lab_m, S[11] + 8, S[12] + 2, face=CAM11)

# ---------------- lines 12-13: 16 tonnes a day (16 one-tonne crates) = 16 million krill ----------------
V12 = ((9.6, -11.0, 6.0), (6.7, 1.0, 0.5))
CAM12 = CL(V12)
crate_lab = []
crates = []
for i in range(16):
    cx_, cy_ = 4.9 + (i % 4) * 1.2, -0.9 + (i // 4) * 1.15
    cg = group(f"Crate{i}", (cx_, cy_, 0.5))
    attach([box("CrateB", (cx_, cy_, 0.5), (1.0, 1.0, 1.0), ktex_m, bevel=0.05),
            text("CrateT", "1 T", (cx_, cy_ - 0.52, 0.5), 0.36, white_lab, extrude=0.02)], cg)
    pop(cg, S[12] + 2 + i, 3)
    f0 = S[13] + 1 + int(i * 1.5)
    key_loc(cg, [(f0, (cx_, cy_, 0.5)), (f0 + 12, tuple(MOUTH1))])
    keyscale(cg, [(f0, 1.0), (f0 + 12, 0.001)])
    keyrot(cg, [(f0, (0, 0, 0)), (f0 + 12, (1.5, 0.8, 0.5))])
    crates.append(cg)
label("L16T", "16 TONS / DAY", SP(V12, 9, 0.24), 0.48, lab_m, S[12] + 6, S[13] + 2, face=CAM12)
V13 = ((9.0, -19.0, 9.5), (8.0, 4.0, 2.5))
CAM13 = CL(V13)
label("L16M", "16,000,000 KRILL", SP(V13, 20, 0.25), 0.95, pink_lab, S[13] + 2, S[14], face=CAM13)
label("L16D", "EVERY DAY", SP(V13, 20, 0.33), 0.85, white_lab, S[13] + 6, S[14], face=CAM13)
for j, f in enumerate(range(S[13] + 2, S[14] - 2, 7)):
    hjaw.rotation_euler = (0, 0.45 if j % 2 == 0 else 0.08, 0); hjaw.keyframe_insert("rotation_euler", frame=f)
hjaw.rotation_euler = (0, 0, 0); hjaw.keyframe_insert("rotation_euler", frame=S[14])

# ---------------- lines 14-15: your billion-krill cube is back... and is gone in ~2 months ----------------
keyscale(cube, [(S[14] + 1, (0.001, 1, 1)), (S[14] + 7, (1.0, 1.0, 1.0)), (S[15], (1.0, 1.0, 1.0))])
V14 = ((7.0, -26.0, 13.0), (7.0, 7.0, 3.0))
CAM14 = CL(V14)
label("L1B2", "1,000,000,000", SP(V14, 26, 0.28), 1.3, pink_lab, S[14] + 3, S[15], face=CAM14)
WH2 = (-3.0, 7.0, 5.5)
key_loc(hero, [(S[14], WH1), (S[14] + 6, WH2)])
steps = [1.0, 0.75, 0.5, 0.25, 0.0]
DAYS = ["DAY 1", "DAY 15", "DAY 30", "DAY 45", "DAY 62"]
dstep = max(5, (S[16] - S[15]) // 5)
for j, s_ in enumerate(steps):
    f = S[15] + j * dstep
    sv = max(s_, 0.001)
    cube.scale = (sv, 1.0, 1.0); cube.keyframe_insert("scale", frame=f)
    face_x = CUBE_R - CS * s_
    key_loc(hero, [(f, (face_x - 9.6 * WS - 0.9, 7.0, 5.5))])
    hjaw.rotation_euler = (0, 0.5, 0); hjaw.keyframe_insert("rotation_euler", frame=f - 2)
    hjaw.rotation_euler = (0, 0.05, 0); hjaw.keyframe_insert("rotation_euler", frame=f)
    label(f"LDay{j}", DAYS[j], SP(V14, 26, 0.25), 1.7, white_lab if j < 4 else lab_m, f, f + dstep if j < 4 else S[16] + 4, face=CAM14)
    burst((face_x, 3.0, 5.0), f, 10, 2.5, 0.25, f + 8, krill_m)
label("L2Mo", "≈ 2 MONTHS", SP(V14, 26, 0.33), 1.45, lab_m, S[15] + 4 * dstep, S[16] + 4, face=CAM14)

# ---------------- line 16: real krill swarms are even bigger (kilometres wide) ----------------
swarm_m = krill_tex("Swarm", 0.05, 0.12)
SW = (0.0, 620.0, 110.0)
swarm = sphere("Swarm", SW, 1.0, swarm_m, scale=(900.0, 260.0, 60.0), sub=4)
for i in range(60):
    v = Vector((random.uniform(-1, 1), random.uniform(-1, 1), random.uniform(-1, 1)))
    sphere("SwarmPuff", (SW[0] + v.x * 800, SW[1] + v.y * 200, SW[2] + v.z * 40), random.uniform(60, 140), swarm_m, scale=(1.6, 1.0, 0.6), sub=2)
swp = [o for o in bpy.data.objects if o.name.startswith(("Swarm", "SwarmPuff"))]
for o in swp:
    hide_until(o, S[16] - 2)
    gone_at(o, S[17], 1)
V16 = ((6.0, -120.0, 90.0), (2.0, 600.0, 40.0))
CAM16 = CL(V16)
label("LSw1", "REAL SWARMS:", SP(V16, 160, 0.25), 8.0, white_lab, S[16] + 8, S[17] + 1, face=CAM16)
label("LSw2", "KILOMETERS WIDE!", SP(V16, 160, 0.33), 8.0, pink_lab, S[16] + 12, S[17] + 1, face=CAM16)

# ---------------- line 17: would you swim in the krill cloud?  (snorkel mask on, krill all around) ----------------
hide_until(mask_g, S[17])
PCL = Vector((PX0, PY0 - 0.1, 1.2))
for i in range(60):
    v = Vector((random.gauss(0, 1), random.gauss(0, 0.5), random.gauss(0, 0.8))).normalized() * random.uniform(0.55, 1.5)
    if v.y < -0.4:
        v.y = -0.4
    p = PCL + v
    ko = krill(f"SK{i}", tuple(p), random.uniform(0.18, 0.26), rz=random.uniform(0, 6.283), ry=random.uniform(-0.4, 0.4))
    hide_until(ko, S[17] + random.randint(0, 6))
    key_loc(ko, [(S[17], tuple(p)), (FRAMES, tuple(p + Vector((random.uniform(-0.3, 0.3), 0, random.uniform(-0.2, 0.3)))))])
keyrot(arms[0], [(S[17] + 2, (0, 0, 0)), (S[17] + 8, (0, -2.4, 0)), (FRAMES, (0, -2.6, 0))])   # wave
V17 = ((-0.4, -4.3, 2.1), (PX0, PY0, 0.95))
q = text("Q", "?", SP(V17, 4.2, 0.16), 0.8, lab_m, extrude=0.05)
keyscale(hero, [(S[17] - 1, WS), (S[17], 0.001)])
pop(q, S[17] + 4, 6)
keyrot(q, [(S[17] + 4, (math.radians(90), 0, 0)), (FRAMES, (math.radians(90), 0, math.radians(360)))])

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
KT = (TX, TY, TZ + 0.03)
cam_keys = [
    (0,          V0[0],                      V0[1]),                          # hook: whale + krill cloud
    (S[1] - 1,   (7.0, -9.0, 7.0),           V0[1]),
    (S[1],       V1[0],                      V1[1]),                          # one krill (6 cm)
    (S[2] - 1,   (TX - 0.06, TY - 0.27, 0.9), V1[1]),
    (S[2],       V2[0],                      V2[1]),                          # 1 gram
    (S[3] - 1,   (TX + 0.05, TY - 0.46, 1.0), V2[1]),
    (S[3],       V3[0],                      V3[1]),                          # 1,000 = 1 kg
    (S[4] - 1,   (TX + 0.1, TY - 0.62, 1.1),  V3[1]),
    (S[4],       (0.6, -7.6, 3.0),           (1.9, -0.2, 0.5)),               # 1 tonne vs car
    (S[5] - 1,   CAM4,                       (1.9, -0.2, 0.5)),
    (S[5],       (2.0, -21.0, 11.0),         V5[1]),                          # the billion cube
    (S[6],       V5[0],                      V5[1]),
    (S[7] - 1,   (8.0, -27.0, 15.0),         V5[1]),
    (S[7],       (-7.0, -21.0, 31.0),        V7[1]),                          # 7 whales
    (S[8] - 1,   V7[0],                      V7[1]),
    (S[8],       (-9.5, -21.0, 37.0),        V8[1]),                          # 20 pools
    (S[9] - 1,   V8[0],                      V8[1]),
    (S[9],       V9[0],                      V9[1]),                          # hungry whale arrives
    (S[10] - 1,  (17.0, -20.0, 9.0),         (3.0, 7.0, 4.0)),
    (S[10],      V10[0],                     V10[1]),                         # gulp
    (S[11] - 1,  (24.0, -13.0, 8.0),         (9.0, 7.0, 4.0)),
    (S[11],      V11[0],                     V11[1]),                         # gulp = body
    (S[12] - 1,  (16.0, -22.0, 9.0),         V11[1]),
    (S[12],      V12[0],                     V12[1]),                         # 16 tonnes
    (S[13] - 1,  (7.8, -11.5, 6.0),          V12[1]),
    (S[13],      V13[0],                     V13[1]),                         # 16 million krill
    (S[14] - 1,  (7.0, -20.0, 10.0),         (7.0, 5.0, 2.5)),
    (S[14],      V14[0],                     V14[1]),                         # billion cube back
    (S[15],      (8.0, -27.0, 13.0),         (8.0, 7.0, 3.0)),
    (S[16] - 1,  (11.0, -26.0, 13.0),        (10.0, 7.0, 3.0)),               # ~2 months
    (S[16],      (8.0, -95.0, 70.0),         (2.0, 500.0, 40.0)),             # swarms km wide
    (S[17] - 1,  V16[0],                     V16[1]),
    (S[17],      V17[0],                     V17[1]),                         # question
    (FRAMES - 1, (-2.1, -4.7, 2.4),          (PX0, PY0, 0.95)),
]
cam_keys = [(f, overhead(cl, tl), tl) for f, cl, tl in cam_keys]
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
CUTS = tuple(S[k] for k in (1, 2, 3, 4, 5, 7, 8, 9, 10, 11, 12, 13, 14, 16, 17))
for o_ in (cam, target):
    for fc in fcurves(o_):
        pts = fc.keyframe_points
        for i in range(len(pts) - 1):
            if int(round(pts[i + 1].co[0])) in CUTS:
                pts[i].interpolation = 'CONSTANT'
for o_ in (hero,):
    for fc in fcurves(o_):
        if fc.data_path == "location":
            for kp in fc.keyframe_points:
                if S[15] <= kp.co[0] < S[16]:
                    kp.interpolation = 'LINEAR'
for o in bpy.data.objects:
    if o.type == 'FONT':
        o.visible_shadow = False
sc.frame_set(0)
bpy.ops.wm.save_as_mainfile(filepath=f"{HERE}/scene.blend")
print("SCENE OK", FRAMES, S)
