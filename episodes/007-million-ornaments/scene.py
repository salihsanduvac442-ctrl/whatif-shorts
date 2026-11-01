# Day 7 (v2, 'three problems' story) — What if you hung 1 million ornaments on one Christmas tree?  Build: python3 episodes/007-million-ornaments/scene.py
# Christmas special: snowy dusk version of the reference-style garden
# Reference style: base (helpers, lawn/soil, house, garden) copied from episodes/003-lift-million-ref/scene.py
import bpy, math, random, os, json
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
random.seed(7)
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
el[0].position = 0.0; el[0].color = (1.0, 0.74, 0.62, 1)
el[1].position = 0.42; el[1].color = (0.2, 0.28, 0.68, 1)
nt.links.new(tc.outputs["Generated"], sep.inputs[0])
nt.links.new(sep.outputs["Z"], ramp.inputs[0])
nt.links.new(ramp.outputs["Color"], bg.inputs["Color"])
bg.inputs["Strength"].default_value = 0.85

bpy.ops.object.light_add(type='SUN', rotation=(math.radians(50), 0, math.radians(-30)))
sun = bpy.context.object; sun.data.energy = 3.8; sun.data.color = (1.0, 0.9, 0.82); sun.data.angle = math.radians(5)

# fluffy clouds
cloud_m = mat("Cloud", (1, 0.9, 0.92), 0.9, emit=(1, 0.85, 0.9), emit_strength=0.35)
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
gmix.inputs[6].default_value = (0.72, 0.8, 0.95, 1); gmix.inputs[7].default_value = (0.93, 0.96, 1.0, 1)   # snow-covered lawn, mowed stripes
L.new(gt.outputs[0], gmix.inputs["Factor"])
gnz = N.new("ShaderNodeTexNoise"); gnz.inputs["Scale"].default_value = 6.0; gnz.inputs["Detail"].default_value = 6.0
L.new(geo.outputs["Position"], gnz.inputs["Vector"])
gvar = N.new("ShaderNodeMix"); gvar.data_type = 'RGBA'; gvar.blend_type = 'MULTIPLY'
gvar.inputs["Factor"].default_value = 0.12
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
box("Ground", (0, 26.5, -6.0), (400, 55.0, 12.0), grass_m)
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
    bpy.ops.mesh.primitive_plane_add(size=1, location=(sx * 100016, 26.5, -0.03))
    o = bpy.context.object; o.scale = (199968, 55.0, 1); o.data.materials.append(far)

# ---------------- house + trees ----------------
wall_m = mat("Wall", (0.86, 0.8, 0.7), 0.85)
roof_m = stripe_mat("Roof", (0.78, 0.38, 0.2), (0.6, 0.27, 0.14), axis="Z", freq=28.0, thresh=0.5, rough=0.7)
trim_m = mat("Trim", (0.97, 0.97, 0.95), 0.6)
win_m = mat("Window", (1.0, 0.78, 0.4), 0.2, emit=(1.0, 0.7, 0.3), emit_strength=2.0)   # warm lit windows
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
snow_m = mat("Snow", (0.96, 0.97, 1.0), 0.6)
fir_m = [mat("Fir1", (0.08, 0.38, 0.2), 0.85), mat("Fir2", (0.12, 0.48, 0.25), 0.85)]
def tree(x, y, h=3.4, r=1.4):
    """snowy fir: trunk + 3 cone tiers with white caps"""
    cyl("Trunk", (x, y, 0.4), 0.2, 0.8, trunk_m, verts=8)
    m_ = random.choice(fir_m)
    for i in range(3):
        rr = r * (1 - i * 0.26); z0 = 0.7 + i * h * 0.24
        cyl("Fir", (x, y, z0 + h * 0.2), rr, h * 0.4, m_, r2=0.05, verts=10)
        cyl("FirSnow", (x, y, z0 + h * 0.33), rr * 0.45, h * 0.16, snow_m, r2=0.03, verts=10)
for (x, y) in [(-17, 12), (-8, 22), (8.8, 24), (-12, 30), (26, 30), (-1, 26), (12, 34), (-24, 20), (18, 18)]:
    tree(x, y, random.uniform(3.6, 4.8), random.uniform(1.3, 1.7))
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
box("HedgeSnowB", (0, HY + 6.0, 1.22), (40, 1.0, 0.12), snow_m, bevel=0.05)
box("HedgeSnowL", (-19.5, HY - 4, 1.22), (1.0, 20, 0.12), snow_m, bevel=0.05)
POX, POY = 11.0, 8.5
box("PoolRim", (POX, POY, 0.03), (6.4, 3.8, 0.1), mat("PoolRimM", (0.9, 0.88, 0.82), 0.7))
box("PoolWater", (POX, POY, 0.06), (5.8, 3.2, 0.06), mat("PoolWaterM", (0.7, 0.88, 0.98), 0.05, emit=(0.5, 0.75, 0.9), emit_strength=0.2))   # frozen pool


# =====================================================================================
# Day 7 — What if you hung 1 million ornaments on one Christmas tree?
# Numbers (rounded, "about"): a glass ball ornament ~25 g (typical 6-8 cm glass balls ~20-30 g).
#   A home tree holds ~100 ornaments. 1,000 x 25 g = 25 kg; 10,000 = 250 kg (~3 adults of ~80 kg).
#   1,000,000 x 25 g = 25 tonnes (~4 big African elephants of ~6 t).
#   Volume: a 7.5 cm ball ~221 cm3 -> 221 m3 of balls, ~345 m3 loosely piled ~ the inside of a family house.
#   To hang them ~20 cm apart you need ~40,000 m2 of tree surface: a cone (r = h/3) with that area is ~190 m tall.
#   Tallest known living tree (Hyperion, coast redwood) ~116 m.  1,000,000 x 5 s = 5,000,000 s ~ 58 days.
# =====================================================================================
def keyscale(o, keys):
    for f, s in keys:
        o.scale = (s,) * 3 if not isinstance(s, tuple) else s
        o.keyframe_insert("scale", frame=f)

lab_m = mat("LabelM", (1.0, 0.85, 0.2), 0.4, emit=(1.0, 0.8, 0.2), emit_strength=0.9)
white_lab = mat("LabW", (1, 1, 1), 0.4, emit=(1, 1, 1), emit_strength=0.8)
red_lab = mat("LabR", (0.95, 0.1, 0.08), 0.4, emit=(1.0, 0.1, 0.05), emit_strength=1.2)
green_lab = mat("LabG", (0.2, 0.9, 0.3), 0.4, emit=(0.2, 0.9, 0.3), emit_strength=1.0)
spark_m = glow_mat("Spark", (1.0, 0.95, 0.7), 5.0)
eyew = mat("EyeW", (1, 1, 1), 0.3)
eyeb = mat("EyeB", (0.03, 0.03, 0.04), 0.3)
bulb_m = glow_mat("Bulb", (1.0, 0.78, 0.35), 6.0)
star_m = mat("StarM", (1.0, 0.82, 0.2), 0.3, emit=(1.0, 0.75, 0.15), emit_strength=2.5, metal=0.4)
BALL_COLS = [(0.9, 0.06, 0.08), (1.0, 0.72, 0.1), (0.1, 0.35, 0.95), (0.85, 0.87, 0.92), (0.1, 0.65, 0.3), (0.65, 0.15, 0.8)]
ball_mats = [mat(f"Ball{i}", c, 0.12, metal=0.35) for i, c in enumerate(BALL_COLS)]
ball_mesh = []
for i, m_ in enumerate(ball_mats):
    o = sphere(f"BallProto{i}", (0, -900, -900), 1.0, m_, sub=2)
    ball_mesh.append(o.data)
def ball(loc, r, ci=None):
    o = bpy.data.objects.new("Ball", ball_mesh[random.randrange(6) if ci is None else ci]); sc.collection.objects.link(o)
    o.location = loc; o.scale = (r,) * 3
    return o
def ballpop(o, f_in, dur=4):
    r = o.scale[0]
    keyscale(o, [(0, 0.001), (max(f_in - 1, 0), 0.001), (f_in + dur * 0.6, r * 1.25), (f_in + dur, r)])
def ballgone(o, f, dur=3):
    r = o.scale[0]
    o.keyframe_insert("scale", frame=f - dur); o.scale = (0.001,) * 3; o.keyframe_insert("scale", frame=f)
    o.scale = (r,) * 3
def burst(loc, f, n=10, r=0.12, size=0.012, f_out=None, material=None):
    for k in range(n):
        a = k / n * 6.283
        s_ = sphere("Burst", (loc[0] + r * math.cos(a), loc[1] - 0.05, loc[2] + r * math.sin(a)), size, material or spark_m, sub=1)
        pop(s_, f, 3, f_out if f_out else f + 10)
def shards(loc, f, ci, n=7, spread=0.35, size=0.03):
    """a glass ball hits the ground and shatters into little shards"""
    for k in range(n):
        a = k / n * 6.283 + random.uniform(-0.3, 0.3)
        c = sphere("Shard", loc, size, ball_mats[ci], sub=1, smooth=False, scale=(1.4, 0.5, 0.9))
        d = random.uniform(0.5, 1.0) * spread
        key_loc(c, [(f, loc), (f + 4, (loc[0] + d * 0.6 * math.cos(a), loc[1] + d * 0.6 * math.sin(a), loc[2] + spread * 0.5)),
                    (f + 9, (loc[0] + d * math.cos(a), max(loc[1] + d * math.sin(a), -0.95), 0.02))])
        c.rotation_euler = (0, 0, 0); c.keyframe_insert("rotation_euler", frame=f)
        c.rotation_euler = (random.uniform(2, 5), random.uniform(2, 5), 0); c.keyframe_insert("rotation_euler", frame=f + 9)
        keyscale(c, [(0, 0.001), (f - 1, (0.001,) * 3), (f, (1.4, 0.5, 0.9))])

# ---------------- the main Christmas tree (tiers can sag, the top can snap off) ----------------
TX, TY = 0.0, 0.15   # close to the soil cut face (front edge at y=-1.0)
SNAPZ = 0.45
cyl("TTrunk", (TX, TY, 0.3), 0.13, 0.6, trunk_m, verts=12)
box("TreeSkirt", (TX, TY, 0.03), (1.6, 1.6, 0.05), mat("Skirt", (0.8, 0.1, 0.12), 0.8), bevel=0.1, rot=(0, 0, 0.6))
xtree = group("XTree", (TX, TY, SNAPZ))
TIERS = [(1.0, 0.42, 0.8), (0.82, 0.85, 0.7), (0.62, 1.22, 0.62), (0.42, 1.55, 0.58)]   # (base r, base z, height)
tree_g = mat("TreeG", (0.07, 0.42, 0.18), 0.8)
tree_g2 = mat("TreeG2", (0.1, 0.5, 0.22), 0.8)
tiers = []
for i, (r, z, h) in enumerate(TIERS):
    tg = group(f"Tier{i}", (TX, TY, z))
    parts = [cyl(f"TierC{i}", (TX, TY, z + h / 2), r, h, tree_g if i % 2 == 0 else tree_g2, r2=0.05, verts=16)]
    parts.append(cyl(f"TierSnow{i}", (TX, TY, z + h * 0.78), r * 0.3, h * 0.25, snow_m, r2=0.03, verts=16))
    attach(parts, tg)
    tiers.append(tg)
topstar = sphere("TopStar", (TX, TY, 2.22), 0.13, star_m, scale=(1, 0.5, 1), sub=1, smooth=False)
attach([topstar], tiers[3])
def tier_point(i, front=0.75, out=0.03):
    r, z, h = TIERS[i]
    t = random.uniform(0.08, 0.82)
    a = random.uniform(-math.pi, 0) if random.random() < front else random.uniform(0, math.pi)
    rr = r * (1 - t) + 0.05 * t + out
    return (TX + rr * math.cos(a), TY + rr * math.sin(a), z + t * h - 0.04)
def tier_of(n):
    return random.choices(range(4), weights=[4, 3, 2, 1])[0]
# fairy lights
for k in range(44):
    i = tier_of(k)
    b_ = sphere("Light", tier_point(i, 0.7, 0.02), 0.022, bulb_m, sub=1)
    attach([b_], tiers[i])
# ornament sets: A = the normal ~100 (shown as 40), B = 1,000, C = 10,000
def make_set(n, r=0.06):
    out = []
    for k in range(n):
        i = tier_of(k)
        o = ball(tier_point(i), r * random.uniform(0.85, 1.15))
        attach([o], tiers[i])
        out.append(o)
    return out
SA, SB, SC = make_set(40), make_set(130, 0.055), make_set(230, 0.05)
attach(tiers, xtree)
S1 = S[1]
S3 = T1000 = S[8]          # 1,000 then 10,000 ornaments within line 8
S4 = T10K = S[8] + 9
SNAPF = S[9] - 12          # on the word 'Snap!'
for k, o in enumerate(SA):                      # hook: they rain on fast; stay as the "normal" tree
    ballpop(o, 2 + k // 3, 3)
for k, o in enumerate(SB):
    r = o.scale[0]
    keyscale(o, [(0, 0.001), (3 + k // 6, 0.001), (5 + k // 6, r), (S1 - 3, r), (S1, 0.001),
                 (S3 + k // 14, 0.001), (S3 + 3 + k // 14, r)])
for k, o in enumerate(SC):
    ballpop(o, S4 + k // 18, 3)
# sagging: tiers squash + spread as the weight grows, back to normal for line 1
for i, tg in enumerate(tiers):
    keyscale(tg, [(0, 1.0), (24, (1.05, 1.05, 0.9)), (S1 - 2, (1.05, 1.05, 0.9)), (S1, 1.0), (S3, 1.0),
                  (S3 + 8, (1.1, 1.1, 0.82)), (S4 + 1, (1.1, 1.1, 0.82)), (S4 + 14, (1.2, 1.2, 0.66)),
                  (SNAPF - 2, (1.22, 1.22, 0.6))])
# wobble under the load
for f in range(S4 + 4, SNAPF, 4):
    xtree.rotation_euler = (0, 0.04 * (1 if (f // 6) % 2 else -1), 0); xtree.keyframe_insert("rotation_euler", frame=f)
# line 6: SNAP — the whole top falls over to the left
xtree.rotation_euler = (0, 0, 0); xtree.keyframe_insert("rotation_euler", frame=SNAPF)
xtree.rotation_euler = (0, -1.5, 0.15); xtree.keyframe_insert("rotation_euler", frame=SNAPF + 9)
xtree.rotation_euler = (0, -1.38, 0.15); xtree.keyframe_insert("rotation_euler", frame=SNAPF + 12)
xtree.rotation_euler = (0, -1.45, 0.15); xtree.keyframe_insert("rotation_euler", frame=SNAPF + 15)
# reset (off-camera, during the giant-tree shots): upright again, only set A
RESET = S[11] + 10
xtree.keyframe_insert("rotation_euler", frame=RESET - 1)
xtree.rotation_euler = (0, 0, 0); xtree.keyframe_insert("rotation_euler", frame=RESET)
for tg in tiers:
    tg.keyframe_insert("scale", frame=RESET - 1); tg.scale = (1, 1, 1); tg.keyframe_insert("scale", frame=RESET)
for o in SB + SC:
    ballgone(o, RESET, 1)
burst((TX, TY - 0.2, SNAPZ + 0.1), SNAPF, 12, 0.35, 0.035, SNAPF + 12)
for k in range(10):   # broken wood splinters
    c = box("Splinter", (TX, TY - 0.1, SNAPZ), (0.03, 0.03, 0.14), trunk_m)
    a = random.uniform(0, 6.283)
    key_loc(c, [(SNAPF, (TX, TY - 0.1, SNAPZ)), (SNAPF + 6, (TX + 0.5 * math.cos(a), TY - 0.3, SNAPZ + 0.4)), (SNAPF + 12, (TX + 0.8 * math.cos(a), TY - 0.3 + 0.3 * math.sin(a), 0.03))])
    c.rotation_euler = (0, 0, 0); c.keyframe_insert("rotation_euler", frame=SNAPF)
    c.rotation_euler = (3, 4, 1); c.keyframe_insert("rotation_euler", frame=SNAPF + 12)
    hide_until(c, SNAPF)
    gone_at(c, S[10])
# balls that fly off and smash in the snow
for k in range(26):
    ci = random.randrange(6)
    p0 = (TX + random.uniform(-0.6, 0.4), TY - random.uniform(0.2, 0.6), random.uniform(0.6, 1.8))
    o = ball(p0, 0.055, ci)
    p2 = (TX - random.uniform(0.6, 2.4), max(TY - random.uniform(-0.3, 1.0), -0.75), 0.05)
    pm = ((p0[0] + p2[0]) / 2, (p0[1] + p2[1]) / 2, p0[2] + random.uniform(0.3, 0.9))
    land = SNAPF + 9 + random.randint(0, 6)
    key_loc(o, [(SNAPF + 2, p0), ((SNAPF + 2 + land) // 2, pm), (land, p2)])
    keyscale(o, [(0, 0.001), (SNAPF + 1, 0.001), (SNAPF + 2, 0.055), (land, 0.055), (land + 1, 0.001)])
    shards(p2, land, ci, 6, 0.3, 0.025)
snap = text("Snap", "SNAP!", (TX - 0.4, TY - 0.6, 3.6), 0.55, red_lab, extrude=0.04)
pop(snap, SNAPF, 4, S[9] + 6)

# ---------------- labels over the tree (upper frame) ----------------
LZ = 3.75
def label(name, body, loc, size, m_, f_in, f_out):
    t = text(name, body, loc, size, m_, extrude=size * 0.08)
    pop(t, f_in, 5, f_out)
    return t
label("Q1M", "1,000,000?", (TX, TY - 0.5, LZ), 0.42, lab_m, 3, S1)
label("P1", "PROBLEM 1", (TX, TY - 0.5, LZ + 0.25), 0.4, lab_m, S1 + 2, S[2] + 1)
label("P1b", "THE TREE", (TX, TY - 0.5, LZ - 0.32), 0.34, white_lab, S1 + 8, S[2] + 1)
label("P2", "PROBLEM 2", (TX, TY - 0.5, LZ + 0.25), 0.4, lab_m, S[6] + 14, S[7] + 1)
label("P2b", "WEIGHT", (TX, TY - 0.5, LZ - 0.32), 0.34, white_lab, S[6] + 20, S[7] + 1)
label("P3", "PROBLEM 3", (TX, TY - 0.5, LZ + 0.25), 0.4, lab_m, S[12] + 2, S[13] + 1)
label("P3b", "TIME", (TX, TY - 0.5, LZ - 0.32), 0.34, white_lab, S[12] + 8, S[13] + 1)
label("L100", "~100", (TX, TY - 0.5, LZ), 0.6, white_lab, S[2] + 3, S[3] + 1)
label("L1000", "1,000", (TX, TY - 0.5, LZ), 0.6, lab_m, S3 + 1, S4)
label("L10K", "10,000", (TX, TY - 0.5, LZ + 0.1), 0.55, lab_m, S4 + 1, SNAPF)
label("L250", "= 250 KG", (TX, TY - 0.5, LZ - 0.5), 0.36, white_lab, S4 + 6, SNAPF)

# ---------------- line 2: one glass ball on a kitchen scale ----------------
KX, KY = TX - 1.35, TY - 0.55
scale_m = mat("ScaleM", (0.95, 0.95, 0.97), 0.4)
kparts = [box("KScale", (KX, KY, 0.08), (0.62, 0.5, 0.16), scale_m, bevel=0.03),
          cyl("KPlate", (KX, KY, 0.18), 0.24, 0.03, mat("KPlateM", (0.75, 0.78, 0.82), 0.2, metal=0.8), verts=24),
          box("KDisp", (KX, KY - 0.255, 0.08), (0.34, 0.01, 0.09), mat("KDispM", (0.1, 0.25, 0.15), 0.3, emit=(0.2, 1.0, 0.4), emit_strength=0.6))]
kg = group("KitchenScale", (KX, KY, 0.0)); attach(kparts, kg)
bigb = ball((KX, KY, 0.42), 0.22, 0)
cap_m = mat("Cap", (0.9, 0.75, 0.3), 0.3, metal=0.9)
capo = cyl("BallCap", (KX, KY, 0.66), 0.06, 0.07, cap_m, verts=12)
for o in (kg, capo):
    pop(o, S[7] - 2, 5, S[8] + 1)
ballpop(bigb, S[7] - 2, 5); ballgone(bigb, S[8] + 1)
label("L25g", "25 g", (KX, KY - 0.1, 1.25), 0.4, lab_m, S[7] + 6, S[8] + 1)
burst((KX, KY - 0.2, 0.42), S[7] + 4, 10, 0.32, 0.02, S[7] + 14)

# ---------------- people (cartoon, built like day 6) ----------------
skin_m = mat("Skin", (0.95, 0.74, 0.58), 0.6)
pants_m = mat("Pants", (0.2, 0.3, 0.6), 0.8)
hair_m = mat("Hair", (0.28, 0.16, 0.07), 0.8)
shoe_m = mat("Shoe", (0.15, 0.15, 0.18), 0.6)
def person(x, y, shirt, k=1.0, hat=False):
    g = group("Person", (x, y, 0))
    sm = mat("Shirt", shirt, 0.7)
    P_ = lambda dx, dy, dz: (x + dx * k, y + dy * k, dz * k)
    ps = []
    for sx in (-1, 1):
        ps.append(tube("Leg", [P_(sx * 0.12, 0, 0.7), P_(sx * 0.14, 0, 0.08)], [0.1 * k, 0.09 * k], pants_m))
        ps.append(box("ShoeP", P_(sx * 0.14, -0.05, 0.05), (0.17 * k, 0.3 * k, 0.1 * k), shoe_m, bevel=0.03))
        ps.append(tube("Arm", [P_(sx * 0.27, 0, 1.22), P_(sx * 0.36, -0.03, 0.9), P_(sx * 0.34, -0.06, 0.7)], [0.065 * k] * 3, sm))
        ps.append(sphere("Hand", P_(sx * 0.34, -0.06, 0.66), 0.065 * k, skin_m, sub=2))
        ps.append(sphere("EyeWp", P_(sx * 0.085, -0.21, 1.6), 0.055 * k, eyew, scale=(1, 0.6, 1.2), sub=2))
        ps.append(sphere("EyeBp", P_(sx * 0.085, -0.25, 1.6), 0.028 * k, eyeb, sub=1))
    ps.append(sphere("Torso", P_(0, 0, 1.02), 1.0 * k, sm, scale=(0.3 * k, 0.22 * k, 0.4 * k), sub=3))
    ps.append(sphere("Head", P_(0, 0, 1.56), 0.24 * k, skin_m, sub=3))
    if hat:
        ps.append(cyl("Hat", P_(0, 0.02, 1.86), 0.2 * k, 0.4 * k, mat("HatR", (0.9, 0.1, 0.12), 0.7), r2=0.02, rot=(0.3, 0, 0)))
        ps.append(sphere("HatBob", P_(0, 0.14, 2.05), 0.06 * k, snow_m, sub=1))
        ps.append(cyl("HatRim", P_(0, 0.0, 1.72), 0.23 * k, 0.07 * k, snow_m))
    else:
        ps.append(sphere("HairP", P_(0, 0.04, 1.69), 0.23 * k, hair_m, scale=(1.05, 1.0, 0.55), sub=2))
    ps.append(tube("Smile", [P_(-0.08, -0.22, 1.48), P_(0, -0.25, 1.44), P_(0.08, -0.22, 1.48)], [0.014 * k] * 3, eyeb))
    attach(ps, g)
    return g
adults = []
for j, (x, c) in []:  # (v2: adults beat dropped)
    pass
for p_ in adults:   # they jump back when it snaps
    p_.keyframe_insert("location", frame=SNAPF)
    p_.location = (p_.location[0] + 0.3, p_.location[1], 0.35); p_.keyframe_insert("location", frame=SNAPF + 4)
    p_.location = (p_.location[0], p_.location[1], 0.0); p_.keyframe_insert("location", frame=SNAPF + 8)

# ---------------- lines 7-9: a 25-tonne pile of ornaments beside the house ----------------
PX, PY = -7.6, 15.2
pile = group("Pile", (PX, PY, 0))
pp = [sphere("PileCore", (PX, PY, 0), 4.3, ball_mats[0], scale=(1, 1, 1.15), sub=3)]
for k in range(380):
    a = random.uniform(0, 6.283); el_ = math.acos(random.uniform(0.02, 1.0))
    R_ = 4.45
    loc = (PX + R_ * math.sin(el_) * math.cos(a), PY + R_ * math.sin(el_) * math.sin(a), R_ * 1.15 * math.cos(el_))
    pp.append(ball(loc, random.uniform(0.32, 0.42)))
attach(pp, pile)
keyscale(pile, [(0, 0.001), (S[9] - 1, 0.001), (S[9] + 4, 0.25), (S[9] + 14, 0.5), (S[10], 0.55), (S[10] + 14, 0.72),
                (S[11], 0.75), (S[11] + 14, 1.0), (S[12], 1.0), (S[12] + 1, 0.001)])
label("L25T", "25 TONNES", (PX + 2.0, PY - 9.0, 11.5), 1.3, lab_m, S[9] + 4, S[11] + 2)
label("LHouse", "≈ 1 HOUSE", (PX + 4.5, PY - 6.0, 16.5), 1.4, white_lab, S[11] + 6, S[12])
# four cartoon elephants
ele_m = mat("Ele", (0.58, 0.6, 0.68), 0.75)
ear_m = mat("EleEar", (0.85, 0.6, 0.65), 0.7)
elephants = []
for j, ex in enumerate([-12.2, -8.6, -5.0, -1.4]):
    ey = 7.6
    g = group("Elephant", (ex, ey, 0))
    ps = [sphere("EBody", (ex, ey, 1.75), 1.0, ele_m, scale=(1.55, 1.05, 1.0), sub=3),
          sphere("EHead", (ex + 1.45, ey - 0.15, 2.25), 0.75, ele_m, sub=3),
          tube("ETrunk", [(ex + 2.05, ey - 0.35, 2.15), (ex + 2.35, ey - 0.45, 1.4), (ex + 2.55, ey - 0.5, 0.75), (ex + 2.8, ey - 0.55, 0.85)], [0.24, 0.2, 0.16, 0.13], ele_m)]
    for sy in (-1, 1):
        ps.append(sphere("EEar", (ex + 1.15, ey + sy * 0.75, 2.4), 0.6, ear_m, scale=(0.45, 0.2, 1.0), sub=2))
        ps.append(sphere("EEyeW", (ex + 1.9, ey - 0.45 + sy * 0.3, 2.55), 0.13, eyew, sub=2))
        ps.append(sphere("EEyeB", (ex + 1.98, ey - 0.55 + sy * 0.3, 2.55), 0.07, eyeb, sub=1))
        for lx in (-0.8, 0.8):
            ps.append(cyl("ELeg", (ex + lx, ey + sy * 0.5, 0.5), 0.3, 1.0, ele_m, verts=12))
    ps.append(tube("ETail", [(ex - 1.5, ey, 1.9), (ex - 1.9, ey, 1.2)], [0.06, 0.04], ele_m))
    attach(ps, g)
    pop(g, S[10] + 2 + j * 3, 5, S[11] + 4 + j)
    elephants.append(g)
label("L4E", "= 4 ELEPHANTS", (-6.8, 5.0, 9.6), 1.0, white_lab, S[10] + 8, S[11] + 2)

# ---------------- lines 10-13: the 190 m giant tree vs the tallest real tree (116 m) ----------------
GX, GY, GH = 0.0, 150.0, 190.0
giant = group("Giant", (GX, GY, 0))
gp = [cyl("GTrunk", (GX, GY, 6), 5.0, 12, trunk_m, verts=16)]
GT = [(38, 8, 62), (31, 52, 54), (24, 90, 46), (17, 122, 40), (10, 150, 40)]
for i, (r, z, h) in enumerate(GT):
    gp.append(cyl(f"GTier{i}", (GX, GY, z + h / 2), r, h, tree_g if i % 2 == 0 else tree_g2, r2=1.0, verts=24))
    gp.append(cyl(f"GSnow{i}", (GX, GY, z + h * 0.8), r * 0.25, h * 0.2, snow_m, r2=0.5, verts=24))
gp.append(sphere("GStar", (GX, GY, GH + 4), 8.0, star_m, scale=(1, 0.5, 1), sub=1, smooth=False))
for k in range(420):
    i = random.choices(range(5), weights=[5, 4, 3, 2, 1])[0]
    r, z, h = GT[i]
    t = random.uniform(0.05, 0.85); a = random.uniform(-math.pi, 0.2)
    rr = r * (1 - t) + 1.0 * t + 1.2
    gp.append(ball((GX + rr * math.cos(a), GY + rr * math.sin(a), z + t * h - 1.0), random.uniform(1.6, 2.4)))
for k in range(90):
    i = random.choices(range(5), weights=[5, 4, 3, 2, 1])[0]
    r, z, h = GT[i]
    t = random.uniform(0.05, 0.85); a = random.uniform(-math.pi, 0.2)
    rr = r * (1 - t) + 1.0 * t + 0.8
    gp.append(sphere("GLight", (GX + rr * math.cos(a), GY + rr * math.sin(a), z + t * h), 0.7, bulb_m, sub=1))
attach(gp, giant)
keyscale(giant, [(0, 0.001), (S[3] - 1, 0.001), (S[3], (1, 1, 0.02)), (S[3] + 18, (1, 1, 1.05)), (S[3] + 23, 1.0), (S[6] - 4, 1.0), (S[6] - 2, 0.001)])
# height bars + labels
def hbar(name, x, y, h, m_, f_in, f_out):
    b = box(name, (x, y, 0), (2.2, 2.2, 1.0), m_)
    bpy.context.view_layer.update()
    b.data.transform(__import__("mathutils").Matrix.Translation((0, 0, 0.5)))
    keyscale(b, [(0, 0.001), (f_in - 1, 0.001), (f_in, (1, 1, 1)), (f_in + 16, (1, 1, h)), (f_out - 3, (1, 1, h)), (f_out, 0.001)])
    cap_ = box(name + "Cap", (x, y, h), (9, 2.2, 1.6), m_)
    pop(cap_, f_in + 16, 4, f_out)
hbar("Bar190", GX + 48, GY - 40, GH, lab_m, S[3] + 8, S[6] - 2)
label("L190", "190 M", (GX + 50, GY - 45, GH + 16), 24, lab_m, S[3] + 16, S[4] + 2)
for sgn in (-1, 1):
    xb = box("NoX", (GX, GY - 45, 100), (12, 3, 190), red_lab, rot=(0, sgn * 0.6, 0))
    pop(xb, S[4] + 2 + (sgn + 1) * 2, 4, S[5] + 2)
label("LNoE", "NOT ON EARTH", (GX - 5, GY - 50, GH + 30), 18, red_lab, S[4] + 6, S[5] + 2)
# the record redwood (~116 m): tall narrow trunk + crown
RX, RY, RH = -62.0, 150.0, 116.0
red_g = group("Redwood", (RX, RY, 0))
rp = [cyl("RTrunk", (RX, RY, RH * 0.45), 4.0, RH * 0.9, mat("RedBark", (0.55, 0.25, 0.14), 0.9), r2=1.6, verts=14)]
for k in range(9):
    z = RH * (0.45 + k * 0.065)
    rp.append(sphere("RCrown", (RX + random.uniform(-4, 4), RY, z), 10 - k * 0.8, fir_m[k % 2], scale=(1.3, 1.1, 0.8), sub=1, smooth=False))
attach(rp, red_g)
keyscale(red_g, [(0, 0.001), (S[5] - 1, 0.001), (S[5], (1, 1, 0.02)), (S[5] + 18, (1, 1, 1.04)), (S[5] + 22, 1.0), (S[6] - 4, 1.0), (S[6] - 2, 0.001)])
hbar("Bar116", RX - 26, RY - 40, RH, white_lab, S[5] + 8, S[6] - 2)
label("L116", "116 M", (RX - 28, RY - 45, RH + 40), 22, white_lab, S[5] + 14, S[6] - 2)
label("LTall", "TALLEST REAL TREE", (RX - 10, RY - 45, RH + 66), 12, white_lab, S[5] + 18, S[6] - 2)

# ---------------- lines 14-16: hanging them one by one (5 s each) ... then a bump ----------------
LX, LY = TX + 1.05, TY - 0.15
ladder_m = mat("Ladder", (0.85, 0.65, 0.3), 0.6)
ladder = group("Ladder", (LX, LY, 0))
lp = []
for sy in (-1, 1):
    lp.append(box("LRail", (LX + 0.2, LY + sy * 0.22, 0.5), (0.05, 0.05, 1.05), ladder_m, rot=(0, -0.12, 0)))
for z in (0.25, 0.5, 0.75):
    lp.append(box("LStep", (LX + 0.2 - z * 0.12, LY, z), (0.2, 0.48, 0.04), ladder_m))
attach(lp, ladder)
helper = person(LX + 0.08, LY, (0.15, 0.55, 0.85), k=0.95, hat=True)
helper.location = (LX + 0.08, LY, 0.76)
attach([], helper)
helper.rotation_euler = (0, 0, math.radians(-65)); helper["rz"] = math.radians(-65)
for o in (ladder, helper):
    pop(o, S[12] - 2, 5, S[17] + 30) if o is ladder else pop(o, S[12] - 2, 5)
# a new ball appears on the tree on every reach (set D), counter label
SD = make_set(28, 0.06)
for o in SD:
    pass
for k, o in enumerate(SD):
    ballpop(o, S[13] + 4 + k * 4, 3)
# stopwatch
WX, WY, WZ = TX - 1.15, TY - 0.6, 0.85
watch = group("Watch", (WX, WY, WZ))
wp = [cyl("WatchBody", (WX, WY + 0.03, WZ), 0.34, 0.08, mat("WatchM", (0.95, 0.3, 0.2), 0.4), rot=(math.radians(90), 0, 0), verts=40),
      cyl("WatchFace", (WX, WY - 0.02, WZ), 0.28, 0.02, white_lab, rot=(math.radians(90), 0, 0), verts=40),
      cyl("WatchBtn", (WX, WY + 0.03, WZ + 0.4), 0.06, 0.1, mat("WatchM2", (0.6, 0.6, 0.62), 0.3, metal=0.6))]
for k in range(12):
    a = k / 12 * 6.283
    wp.append(box("WTick", (WX + 0.23 * math.sin(a), WY - 0.04, WZ + 0.23 * math.cos(a)), (0.02, 0.01, 0.05), eyeb, rot=(0, a, 0)))
attach(wp, watch)
hand = group("WHand", (WX, WY - 0.05, WZ))
attach([box("WHandB", (WX, WY - 0.05, WZ + 0.1), (0.025, 0.01, 0.2), red_lab)], hand)
pop(watch, S[13] - 2, 5, S[14] + 4); pop(hand, S[13] - 2, 5, S[14] + 4)
hand.rotation_euler = (0, 0, 0); hand.keyframe_insert("rotation_euler", frame=S[13])
hand.rotation_euler = (0, 6.283 * 3, 0); hand.keyframe_insert("rotation_euler", frame=S[14] + 4)
label("L5s", "1 EVERY 5 s", (TX, TY - 0.6, LZ), 0.36, white_lab, S[13] + 4, S[14])
# line 15: 58 days — calendar + Zzz + sky turns to night and back fast
label("L58", "58 DAYS", (TX, TY - 0.6, LZ), 0.55, lab_m, S[14] + 2, S[15])
label("LNon", "NONSTOP", (TX, TY - 0.6, LZ - 0.55), 0.3, white_lab, S[14] + 8, S[15])
CX_, CY_ = TX - 1.2, TY - 0.55
cal = group("Cal", (CX_, CY_, 0.5))
cp = [box("CalBody", (CX_, CY_, 0.55), (0.6, 0.06, 0.6), white_lab, bevel=0.02), box("CalTop", (CX_, CY_ - 0.005, 0.8), (0.6, 0.065, 0.14), red_lab),
      text("Cal58", "58", (CX_, CY_ - 0.05, 0.5), 0.34, mat("CalNum", (0.1, 0.1, 0.12), 0.5), extrude=0.01)]
attach(cp, cal)
pop(cal, S[14] + 2, 5, S[15] + 1)
def calendar(name, top, num, f_in, f_out, cross=False):
    g = group(name, (CX_, CY_, 0.5))
    ps = [box(name + "B", (CX_, CY_, 0.55), (0.62, 0.06, 0.62), white_lab, bevel=0.02), box(name + "T", (CX_, CY_ - 0.005, 0.8), (0.62, 0.065, 0.16), red_lab),
          text(name + "Top", top, (CX_, CY_ - 0.045, 0.8), 0.12, white_lab, extrude=0.005),
          text(name + "N", num, (CX_, CY_ - 0.05, 0.5), 0.34, mat(name + "NM", (0.1, 0.1, 0.12), 0.5), extrude=0.01)]
    if cross:
        for sg in (-1, 1):
            ps.append(box(name + "X", (CX_, CY_ - 0.07, 0.55), (0.07, 0.02, 0.8), red_lab, rot=(0, sg * 0.75, 0)))
    attach(ps, g)
    pop(g, f_in, 5, f_out)
    return g
calendar("Cal29", "DEC", "29", S[15], S[16] + 1)
label("LFin", "DONE: DEC 29", (TX - 0.45, TY - 0.6, LZ), 0.3, lab_m, S[15] + 4, S[16])
calendar("Cal25", "DEC", "25", S[16], S[17] + 2, cross=True)
label("LLate", "TOO LATE!", (TX, TY - 0.7, LZ), 0.4, red_lab, S[16] + 4, S[17])
for k, (dx, dz) in enumerate([(0.25, 2.35), (0.4, 2.55), (0.58, 2.78)]):
    z_ = text("Zzz", "z", (LX + dx, LY - 0.2, dz), 0.18 + k * 0.06, white_lab, extrude=0.01)
    pop(z_, S[14] + 8 + k * 4, 4, S[15])
# line 16: bump — the ladder knocks the tree, balls rain off and smash
BUMP = S[16] + 10   # he dozes off and bumps the tree
ladder.rotation_euler = (0, 0, 0); ladder.keyframe_insert("rotation_euler", frame=BUMP - 2)
ladder.rotation_euler = (0, -0.25, 0); ladder.keyframe_insert("rotation_euler", frame=BUMP + 2)
ladder.rotation_euler = (0, 0, 0); ladder.keyframe_insert("rotation_euler", frame=BUMP + 8)
helper.keyframe_insert("location", frame=BUMP - 2)
helper.location = (LX - 0.05, LY, 0.9); helper.keyframe_insert("location", frame=BUMP + 2)
helper.location = (LX + 0.35, LY - 0.1, 0.0); helper.keyframe_insert("location", frame=BUMP + 9)
xtree.keyframe_insert("rotation_euler", frame=BUMP)
for j, f in enumerate(range(BUMP + 1, BUMP + 22, 4)):
    xtree.rotation_euler = (0, (0.12 if j % 2 else -0.12) * (1 - j / 6), 0); xtree.keyframe_insert("rotation_euler", frame=f)
xtree.rotation_euler = (0, 0, 0); xtree.keyframe_insert("rotation_euler", frame=BUMP + 26)
fall = random.sample(SA + SD, 30)
for o in fall:
    o.keyframe_insert("scale", frame=BUMP)
    o.scale = (0.001,) * 3; o.keyframe_insert("scale", frame=BUMP + 1)
    sc.frame_set(BUMP); bpy.context.view_layer.update()
    p0 = tuple(o.matrix_world.translation)
    ci = ball_mesh.index(o.data)
    fb = ball(p0, 0.06, ci)
    p2 = (p0[0] + random.uniform(-0.5, 0.5), max(p0[1] - random.uniform(0.2, 0.9), -0.75), 0.05)
    land = BUMP + 6 + int(p0[2] * 4) + random.randint(0, 3)
    key_loc(fb, [(BUMP + 1, p0), (land, p2)])
    keyscale(fb, [(0, 0.001), (BUMP, 0.001), (BUMP + 1, 0.06), (land, 0.06), (land + 1, 0.001)])
    shards(p2, land, ci, 6, 0.28, 0.022)
sc.frame_set(0)
q = text("Q", "?", (TX + 0.3, TY - 0.6, LZ + 0.3), 1.4, lab_m, extrude=0.08)
pop(q, S[17] + 2, 6)
q.rotation_euler = (math.radians(90), 0, 0); q.keyframe_insert("rotation_euler", frame=S[17] + 2)
q.rotation_euler = (math.radians(90), 0, math.radians(360)); q.keyframe_insert("rotation_euler", frame=FRAMES)

# ---------------- gentle snowfall around the tree ----------------
flake_m = mat("Flake", (1, 1, 1), 0.5, emit=(1, 1, 1), emit_strength=0.6)
for i in range(110):
    p0 = (random.uniform(-3.2, 3.2), random.uniform(-2.4, 3.0), 4.5)
    fl_ = sphere("Flake", p0, random.uniform(0.012, 0.025), flake_m, sub=1)
    off = random.randint(0, 72)
    for f in range(-off, FRAMES + 72, 72):
        fl_.location = p0; fl_.keyframe_insert("location", frame=f)
        fl_.location = (p0[0] + 0.3, p0[1], 0.0); fl_.keyframe_insert("location", frame=f + 71)
sc.frame_set(0)

# ---------------- camera ----------------
bpy.ops.object.camera_add()
cam = bpy.context.object
sc.camera = cam
cam.data.lens = 26
cam.data.sensor_fit = 'VERTICAL'
cam.data.sensor_height = 36
cam.data.clip_start = 0.05
cam.data.clip_end = 200000
target = bpy.data.objects.new("Target", None); sc.collection.objects.link(target)
tr = cam.constraints.new('TRACK_TO'); tr.target = target
tr.track_axis = 'TRACK_NEGATIVE_Z'; tr.up_axis = 'UP_Y'
TC = (TX, TY, 1.15)
cam_keys = [
    (0,          (0.9, -3.6, 1.8),   TC),                              # hook: balls rain onto the tree
    (S[1] - 4,   (-0.5, -3.3, 1.7),  TC),
    (S[1] + 2,   (0.6, -3.0, 1.5),   TC),                              # problem 1: the tree
    (S[2] - 2,   (-0.6, -3.2, 1.6),  TC),
    (S[2] + 2,   (0.4, -2.8, 1.4),   TC),                              # normal ~100
    (S[3] - 2,   (-0.3, -3.0, 1.5),  TC),
    (S[3] + 2,   (3.0, -14.0, 6.0),  (0.0, 60.0, 40.0)),               # 190 m giant grows behind the house
    (S[3] + 20,  (10.0, -60.0, 20.0), (0.0, 120.0, 70.0)),
    (S[4] - 2,   (30.0, -150.0, 40.0), (5.0, 140.0, 70.0)),
    (S[4] + 2,   (20.0, -165.0, 42.0), (0.0, 140.0, 70.0)),             # not on Earth
    (S[5] - 2,   (10.0, -175.0, 45.0), (0.0, 140.0, 70.0)),
    (S[5] + 2,   (-10.0, -190.0, 45.0), (-25.0, 140.0, 65.0)),          # record redwood 116 m
    (S[6] - 4,   (-40.0, -195.0, 45.0), (-30.0, 140.0, 65.0)),
    (S[6] - 2,   (0.6, -3.4, 1.7),   TC),                              # fine, normal tree; problem 2
    (S[7] - 4,   (-0.4, -3.0, 1.5),  TC),
    (S[7] + 2,   (KX + 0.35, KY - 1.7 - (TY - 1.2), 0.9), (KX, KY, 0.35)),   # 25 g ball on the scale
    (S[8] - 2,   (KX - 0.3, KY - 1.6 - (TY - 1.2), 0.85), (KX, KY, 0.35)),
    (S[8] + 2,   (1.0, -3.4, 1.7),   TC),                              # 1,000 -> 10,000, sag
    (SNAPF - 2,  (0.2, -2.9, 1.4),   TC),
    (SNAPF + 2,  (-0.4, -3.9, 1.5),  (TX - 0.5, TY, 0.7)),              # SNAP
    (S[9] - 2,   (-1.4, -4.4, 1.9),  (TX - 1.0, TY, 0.5)),
    (S[9] + 2,   (-3.0, -9.0, 6.5),  (PX + 1.5, PY - 6.0, 1.5)),        # 25 tonne pile grows
    (S[10] - 2,  (-5.5, -9.5, 7.0),  (PX + 1.0, PY - 6.0, 1.8)),
    (S[10] + 2,  (-9.0, -9.0, 7.0),  (-6.0, 7.6, 1.6)),                 # 4 elephants
    (S[11] - 2,  (-4.5, -9.6, 7.0),  (-6.0, 7.6, 1.6)),
    (S[11] + 2,  (2.0, -12.0, 9.0),  (-3.0, PY - 3.0, 2.5)),             # pile ~ house
    (S[12] - 2,  (-1.0, -13.0, 9.5), (-3.0, PY - 3.0, 2.5)),
    (S[12] + 2,  (1.3, -3.5, 1.7),   (TX + 0.3, TY, 1.0)),                # problem 3: time (ladder)
    (S[13] - 2,  (0.4, -3.2, 1.6),   (TX + 0.3, TY, 1.0)),
    (S[13] + 2,  (-0.6, -3.3, 1.6),  (TX - 0.2, TY, 1.0)),                # every 5 s
    (S[14] - 2,  (0.3, -3.0, 1.5),   (TX - 0.2, TY, 1.0)),
    (S[14] + 2,  (0.8, -3.6, 1.8),   (TX - 0.1, TY, 1.0)),                # 58 days
    (S[15] - 2,  (-0.3, -3.2, 1.6),  (TX, TY, 1.0)),
    (S[15] + 2,  (-0.9, -3.0, 1.5),  (TX - 0.5, TY, 0.9)),                # Dec 29
    (S[16] - 2,  (-0.3, -3.1, 1.5),  (TX - 0.4, TY, 0.9)),
    (S[16] + 2,  (0.4, -3.0, 1.4),   (TX + 0.1, TY, 0.8)),                # too late + bump crash
    (S[17] - 2,  (-0.4, -3.2, 1.5),  (TX + 0.1, TY, 0.8)),
    (S[17] + 4,  (0.9, -3.8, 1.8),   TC),                                # question
    (FRAMES - 1, (0.2, -4.2, 2.0),   TC),
]

def overhead(cl, tl):
    dx, dy = cl[0] - tl[0], cl[1] - tl[1]
    hd = math.hypot(dx, dy)
    if cl[2] > 60 or hd > 40:
        return cl
    z = max(cl[2], tl[2] + 0.62 * hd)
    return (cl[0], cl[1], z)
from mathutils import Quaternion
LIFT = math.atan(0.36 * math.tan(math.atan(18 / 26)))   # subject ~68% down the frame
def aim(cl, subj):
    d = Vector(subj) - Vector(cl)
    ax = d.cross(Vector((0, 0, 1))).normalized()
    return tuple(Vector(cl) + Quaternion(ax, LIFT) @ d)
DY = TY - 1.2   # keys were laid out for TY=1.2; shift the tree shots with the tree
cam_keys = [(f, (cl[0], cl[1] + DY, cl[2]) if (abs(tl[1] - TY) < 2.5 and abs(tl[0]) < 3) else cl, tl) for f, cl, tl in cam_keys]
cam_keys = [(f, overhead(cl, tl), tl) for f, cl, tl in cam_keys]
for f, cl, tl in cam_keys:
    cam.location = cl; cam.keyframe_insert("location", frame=f)
    target.location = aim(cl, tl); target.keyframe_insert("location", frame=f)

for o in bpy.data.objects:
    if o.type == 'FONT':
        o.visible_shadow = False
bpy.ops.wm.save_as_mainfile(filepath=f"{HERE}/scene.blend")
print("SCENE OK", FRAMES, S)
