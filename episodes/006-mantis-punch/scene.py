# Day 6 — What if you had the punch of a mantis shrimp?  Build: python3 episodes/006-mantis-punch/scene.py
# Reference style: base (helpers, lawn/soil, house, garden) copied from episodes/003-lift-million-ref/scene.py
import bpy, math, random, os, json
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
random.seed(6)
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
FRONT_Y = -1.0
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
# Day 6 — What if you had the punch of a mantis shrimp?
# Facts used (peacock mantis shrimp, Patek et al. 2004 Nature; Patek & Caldwell 2005 J Exp Biol):
#   ~10 cm long; club tip up to ~23 m/s (~80 km/h); acceleration ~10,000 g; strike lasts only milliseconds;
#   peak impact forces up to ~1,500 N (often quoted as ~2,500x body weight); the strike makes cavitation bubbles
#   whose collapse gives a second impact, a faint flash of light and very high (thousands of degrees) local heat;
#   captive animals are known to crack aquarium glass. Fighter pilots risk blacking out around 9 g.
#   "Scaled to you": 2,500 x a ~70 kg person's weight ~ 1.7 MN ~ the weight of about 100+ cars (rough, playful).
# =====================================================================================
def keyscale(o, keys):
    for f, s in keys:
        o.scale = (s,) * 3 if not isinstance(s, tuple) else s
        o.keyframe_insert("scale", frame=f)

lab_m = mat("LabelM", (1.0, 0.85, 0.2), 0.4, emit=(1.0, 0.8, 0.2), emit_strength=0.8)
white_lab = mat("LabW", (1, 1, 1), 0.4, emit=(1, 1, 1), emit_strength=0.7)
red_lab = mat("LabR", (0.95, 0.1, 0.08), 0.4, emit=(1.0, 0.1, 0.05), emit_strength=1.2)
blue_lab = mat("LabB", (0.2, 0.5, 1.0), 0.4, emit=(0.2, 0.5, 1.0), emit_strength=1.0)
spark_m = glow_mat("Spark", (1.0, 0.95, 0.7), 5.0)
eyew = mat("EyeW", (1, 1, 1), 0.3)
eyeb = mat("EyeB", (0.03, 0.03, 0.04), 0.3)
bubble_m = mat("Bubble", (0.92, 0.97, 1.0), 0.04, emit=(0.75, 0.9, 1.0), emit_strength=0.6)

def strike(arm, f, back=8):
    """club snaps from guard (pointing up) to fully forward in 2 frames, then reloads."""
    arm.rotation_euler = (0, -1.35, 0); arm.keyframe_insert("rotation_euler", frame=f - 3)
    arm.rotation_euler = (0, 0.2, 0); arm.keyframe_insert("rotation_euler", frame=f)
    arm.keyframe_insert("rotation_euler", frame=f + 3)
    arm.rotation_euler = (0, -1.35, 0); arm.keyframe_insert("rotation_euler", frame=f + back)

def burst(loc, f, n=10, r=0.12, size=0.012, f_out=None, yoff=-0.02):
    for k in range(n):
        a = k / n * 6.283
        s_ = sphere("Burst", (loc[0] + r * math.cos(a), loc[1] + yoff, loc[2] + r * math.sin(a)), size, spark_m, sub=1)
        pop(s_, f, 3, f_out if f_out else f + 10)

# ---------------- garden table + aquarium ----------------
TX, TY, TZ = 0.0, 1.0, 0.75
wood = mat("Wood", (0.72, 0.48, 0.26), 0.7)
box("TableTop", (TX, TY, TZ - 0.03), (1.6, 0.8, 0.06), wood, bevel=0.01)
for x in (-0.72, 0.72):
    for y in (-0.32, 0.32):
        box("TLeg", (TX + x, TY + y, (TZ - 0.06) / 2), (0.06, 0.06, TZ - 0.06), wood)
AW, AD, AH = 0.62, 0.34, 0.4
AY0 = TY - AD / 2                       # front glass plane
frame_m = mat("TankFrame", (0.12, 0.12, 0.14), 0.4)
for (x, z) in [(-AW/2, None), (AW/2, None)]:
    for y in (TY - AD/2, TY + AD/2):
        box("TFv", (TX + x, y, TZ + AH/2), (0.018, 0.018, AH), frame_m)
for z in (TZ + 0.009, TZ + AH):
    for y in (TY - AD/2, TY + AD/2):
        box("TFh", (TX, y, z), (AW + 0.018, 0.018, 0.018), frame_m)
    for x in (-AW/2, AW/2):
        box("TFd", (TX + x, TY, z), (0.018, AD, 0.018), frame_m)
# water back + sides (bright aqua gradient), sand floor, rocks, weeds
wat = bpy.data.materials.new("WaterBack"); wat.use_nodes = True
N = wat.node_tree.nodes; Lk = wat.node_tree.links
N.remove(N["Principled BSDF"])
tcw = N.new("ShaderNodeTexCoord"); sw = N.new("ShaderNodeSeparateXYZ"); Lk.new(tcw.outputs["Generated"], sw.inputs[0])
rw_ = N.new("ShaderNodeValToRGB"); rw_.color_ramp.elements[0].color = (0.05, 0.35, 0.6, 1); rw_.color_ramp.elements[1].color = (0.35, 0.85, 0.95, 1)
Lk.new(sw.outputs["Z"], rw_.inputs[0])
emw = N.new("ShaderNodeEmission"); emw.inputs["Strength"].default_value = 0.9
Lk.new(rw_.outputs[0], emw.inputs[0]); Lk.new(emw.outputs[0], N["Material Output"].inputs["Surface"])
box("WaterBack", (TX, TY + AD/2 - 0.005, TZ + AH/2), (AW, 0.01, AH), wat)
for x in (-AW/2 + 0.005, AW/2 - 0.005):
    box("WaterSide", (TX + x, TY, TZ + AH/2), (0.01, AD, AH), wat)
sand_m = mat("Sand", (0.93, 0.82, 0.55), 0.9)
box("Sand", (TX, TY, TZ + 0.025), (AW, AD, 0.05), sand_m)
FL = TZ + 0.05                          # tank floor
for i in range(9):
    sphere("TRock", (TX + random.uniform(-0.27, 0.27), TY + random.uniform(0.02, 0.14), FL + 0.005),
           random.uniform(0.015, 0.035), mat(f"TR{i}", random.choice([(0.55, 0.5, 0.48), (0.8, 0.45, 0.4), (0.45, 0.55, 0.6)]), 0.8),
           scale=(1.3, 1, 0.7), sub=1, smooth=False)
weed_m = mat("Weed", (0.2, 0.75, 0.35), 0.6)
for x in (-0.25, -0.19, 0.22, 0.27):
    tube("Weed", [(TX + x, TY + 0.12, FL), (TX + x + 0.02, TY + 0.12, FL + 0.08), (TX + x - 0.01, TY + 0.12, FL + 0.17)],
         [0.008, 0.007, 0.004], weed_m)
glass_m = mat("Glass", (0.75, 0.92, 1.0), 0.05)
glass_m.node_tree.nodes["Principled BSDF"].inputs["Alpha"].default_value = 0.12
box("FrontGlass", (TX, AY0, TZ + AH/2), (AW, 0.004, AH), glass_m)
# floating bubbles in the tank
for i in range(10):
    p0 = (TX + random.uniform(-0.25, 0.25), TY + random.uniform(-0.05, 0.1), FL + 0.02)
    b_ = sphere("TankBub", p0, random.uniform(0.004, 0.008), bubble_m, sub=1)
    off = random.randint(0, 60)
    for f in range(-off, FRAMES, 60):
        b_.location = p0; b_.keyframe_insert("location", frame=max(f, 0))
        b_.location = (p0[0] + 0.02, p0[1], TZ + AH - 0.02); b_.keyframe_insert("location", frame=f + 59)

# ---------------- the cartoon mantis shrimp (built at 10x, scaled 0.1 -> ~12 cm) ----------------
SH = (TX - 0.08, TY + 0.02, FL + 0.04)
shr = group("Shrimp", SH)
K = 0.14
def P(x, y, z):
    return (SH[0] + K * x, SH[1] + K * y, SH[2] + K * z)
green = mat("ShG", (0.15, 0.72, 0.45), 0.4)
teal = mat("ShT", (0.1, 0.5, 0.75), 0.4)
orange = mat("ShO", (1.0, 0.45, 0.1), 0.4)
red = mat("ShR", (0.95, 0.15, 0.25), 0.35)
yellow = mat("ShY", (1.0, 0.85, 0.15), 0.4)
sp = []
sp.append(sphere("Cara", P(0.15, 0, 0.12), K * 0.26, green, scale=(1.5, 0.95, 0.85), sub=3))
for i in range(6):
    x = -0.18 - i * 0.15
    r = 0.2 - i * 0.012
    sp.append(sphere("Seg", P(x, 0, 0.1 - i * 0.01), K * r, green if i % 2 == 0 else teal, scale=(0.75, 1, 0.85), sub=2))
    sp.append(box("Band", P(x - 0.06, 0, 0.1 - i * 0.01), (K * 0.025, K * 2 * r * 0.95, K * 2 * r * 0.8), yellow))
for i, (dx, dz) in enumerate([(0, 0.08), (0, -0.05), (-0.03, 0.18)]):
    sp.append(sphere("Fan", P(-1.12 + dx, 0, 0.06 + dz), K * 0.14, [orange, teal, red][i], scale=(1.2, 0.35, 0.55), sub=2))
for i in range(5):
    x = -0.05 - i * 0.14
    sp.append(tube("Leg", [P(x, -0.08, -0.02), P(x + 0.02, -0.12, -0.14), P(x + 0.05, -0.12, -0.24)], [K * 0.025] * 3, orange))
# eyes on stalks (googly, look at the camera)
for sy in (-1, 1):
    sp.append(tube("Stalk", [P(0.38, sy * 0.06, 0.25), P(0.45, sy * 0.1, 0.48)], [K * 0.03, K * 0.03], orange))
    sp.append(sphere("ShEyeW", P(0.47, sy * 0.1, 0.55), K * 0.1, eyew, sub=2))
    sp.append(sphere("ShEyeB", P(0.5, sy * 0.1 - 0.08, 0.56), K * 0.045, eyeb, sub=1))
for sy in (-1, 1):
    sp.append(tube("Ant", [P(0.4, sy * 0.05, 0.2), P(0.7, sy * 0.12, 0.45), P(0.95, sy * 0.2, 0.75)], [K * 0.012] * 3, red))
    sp.append(sphere("AntPad", P(0.62, sy * 0.15, 0.32), K * 0.07, orange, scale=(1.4, 0.4, 0.8), sub=1))
# raptorial club arm (pivot under the head)
PV = P(0.3, -0.16, 0.0)
arm = group("Arm", PV)
ap = [tube("ArmUp", [PV, P(0.62, -0.17, 0.0)], [K * 0.06, K * 0.055], red),
      sphere("Club", P(0.72, -0.17, 0.0), K * 0.11, orange, scale=(1.25, 0.9, 0.9), sub=3),
      sphere("ClubTip", P(0.8, -0.17, 0.0), K * 0.06, yellow, sub=2)]
attach(ap, arm)
attach(sp + [arm], shr)
club = ap[1]
STRIKES = [8, S[2] + 6, S[3] + 6, S[6] + 10, S[8] + 4, S[9] + 6, S[11] + 4, S[11] + 24, S[17] + 8]
arm.rotation_euler = (0, -1.35, 0); arm.keyframe_insert("rotation_euler", frame=0)
for f in STRIKES:
    strike(arm, f)
# little bob
for f in range(0, FRAMES, 16):
    shr.location = SH; shr.keyframe_insert("location", frame=f)
    shr.location = (SH[0], SH[1], SH[2] + 0.005); shr.keyframe_insert("location", frame=f + 8)

def club_world(f):
    sc.frame_set(f); bpy.context.view_layer.update()
    return tuple(ap[2].matrix_world.translation)

# ---------------- targets that shatter: clam (hook), snail (line 6), clam (line 11) ----------------
shell_m = stripe_mat("Shell", (0.98, 0.72, 0.35), (0.7, 0.35, 0.15), axis="Z", freq=160.0, thresh=0.3, rough=0.5)
clam_m = stripe_mat("Clam", (0.95, 0.88, 0.95), (0.75, 0.45, 0.7), axis="X", freq=180.0, thresh=0.2, rough=0.5)
snail_b = mat("SnailB", (0.85, 0.8, 0.55), 0.5)
def shatter(loc, r, material, f_hit, f_gone, n=12, scale=(1, 1, 1), spread=1.0):
    """a shell built from chunks; at f_hit the chunks blast outward and land on the sand."""
    for i in range(n):
        th = i / n * 6.283; ph = random.uniform(-0.6, 1.0)
        off = (r * 0.55 * math.cos(th) * math.cos(ph) * scale[0], r * 0.55 * math.sin(th) * math.cos(ph) * scale[1], r * 0.55 * math.sin(ph) * scale[2])
        p0 = (loc[0] + off[0], loc[1] + off[1], loc[2] + off[2])
        c = sphere("Chunk", p0, r * 0.55, material, sub=1, smooth=False)
        d = Vector(off).normalized() if Vector(off).length > 0 else Vector((1, 0, 0))
        p1 = (p0[0] + d.x * r * 2.6 * spread + r * 1.2, p0[1] + d.y * r * 1.5 * spread - r * 0.8, p0[2] + r * 2.2 * spread)
        p2 = (p0[0] + d.x * r * 4.0 * spread + r * 1.8, p0[1] + d.y * r * 2.2 * spread - r, FL + 0.006)
        key_loc(c, [(f_hit, p0), (f_hit + 5, p1), (f_hit + 12, p2)])
        c.rotation_euler = (0, 0, 0); c.keyframe_insert("rotation_euler", frame=f_hit)
        c.rotation_euler = (random.uniform(2, 5), random.uniform(2, 5), 0); c.keyframe_insert("rotation_euler", frame=f_hit + 12)
        keyscale(c, [(f_hit + 13, 1.0), (f_gone - 3, 0.6), (f_gone, 0.001)])
    burst(loc, f_hit, 10, r * 2.2, r * 0.18, f_hit + 10, yoff=-r * 1.2)
def club_hit_point(f):
    cw = club_world(f)
    return (cw[0] + 0.02, cw[1], max(cw[2], FL + 0.03))
# hook: clam right in front of the club
CL1 = club_hit_point(8)
shatter((CL1[0] + 0.012, CL1[1], FL + 0.022), 0.024, clam_m, 8, S[1] + 4, scale=(1.3, 1, 0.6))
pw = text("Pow", "POW!", (SH[0] + 0.1, AY0 - 0.02, TZ + AH + 0.11), 0.09, lab_m, extrude=0.008)
pop(pw, 9, 4, 30)
# line 6: snail shell explodes
HIT6 = S[6] + 10
SNP = club_hit_point(HIT6)
SN = (SNP[0] + 0.03, SH[1] - 0.005, FL)
shatter((SN[0], SN[1], FL + 0.035), 0.034, shell_m, HIT6, S[8] - 2, n=14, scale=(1, 1, 1.1))
snb = sphere("SnailBody", (SN[0] + 0.025, SN[1], FL + 0.01), 0.024, snail_b, scale=(1.8, 0.8, 0.5), sub=2)
for sy in (-1, 1):
    e_ = sphere("SnEye", (SN[0] + 0.06, SN[1] + sy * 0.01 - 0.006, FL + 0.035), 0.006, eyeb, sub=1)
    gone_at(e_, S[8] - 2)
gone_at(snb, S[8] - 2)
newt = text("Newt", "1,500 N", (SN[0] - 0.04, AY0 - 0.03, TZ + AH + 0.05), 0.075, lab_m, extrude=0.008)
pop(newt, HIT6, 5, S[7] + 2)
# ---------------- line 1: ruler "10 cm" ----------------
rul = group("Ruler", (SH[0] - 0.01, AY0 - 0.03, FL - 0.0))
rp = [box("RulerB", (SH[0] - 0.01, AY0 - 0.03, TZ + 0.012), (0.18, 0.04, 0.012), mat("RulerM", (1.0, 0.9, 0.3), 0.5))]
for i in range(11):
    rp.append(box("Tick", (SH[0] - 0.085 + i * 0.017, AY0 - 0.05, TZ + 0.019), (0.0015, 0.004, 0.003 if i % 5 else 0.006), eyeb))
attach(rp, rul)
pop(rul, S[1], 5, S[3])
cm10 = text("CM10", "10 cm", (SH[0] - 0.01, AY0 - 0.06, TZ + AH + 0.05), 0.08, white_lab, extrude=0.005)
pop(cm10, S[1] + 4, 5, S[2] + 2)

# ---------------- line 2: a car zooms by at 80 km/h ----------------
def car_mesh(name, body_c):
    parts = [box(name + "B", (0, 0, 0.32), (1.7, 0.8, 0.4), mat(name + "M", body_c, 0.35), bevel=0.06),
             box(name + "C", (-0.1, 0, 0.66), (0.9, 0.72, 0.32), mat(name + "W", (0.55, 0.8, 0.95), 0.1), bevel=0.05)]
    for x in (-0.55, 0.55):
        for y in (-0.4, 0.4):
            parts.append(cyl(name + "Wh", (x, y, 0.18), 0.18, 0.14, mat(name + "T", (0.08, 0.08, 0.09), 0.7), rot=(math.radians(90), 0, 0), verts=14))
    bpy.ops.object.select_all(action='DESELECT')
    for p_ in parts:
        p_.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]
    bpy.ops.object.convert(target='MESH'); bpy.ops.object.join()
    o = bpy.context.object; o.name = name
    return o
CAR_COLS = [(0.95, 0.2, 0.15), (0.2, 0.5, 0.95), (1.0, 0.8, 0.1), (0.3, 0.8, 0.35)]
cars = [car_mesh(f"Car{i}", c) for i, c in enumerate(CAR_COLS)]
zoom = cars[0]
key_loc(zoom, [(0, (-30, -0.6, 0)), (S[2] - 2, (-9, -0.6, 0)), (S[2] + 26, (9, -0.6, 0)), (S[3] + 10, (30, -0.6, 0))])
for c in cars[1:]:
    c.location = (0, -500, -50)
streak_m = glow_mat("Streak", (1, 1, 1), 2.5)
for k in range(4):
    st = box("Streak", (0, 0, 0), (1.4, 0.03, 0.03), streak_m)
    key_loc(st, [(S[2] - 2, (-10.6, -0.6, 0.2 + k * 0.15)), (S[2] + 26, (7.4, -0.6, 0.2 + k * 0.15))])
    keyscale(st, [(0, 0.001), (S[2] - 3, 0.001), (S[2] - 2, 1.0), (S[2] + 26, 1.0), (S[2] + 28, 0.001)])
kmh = text("KMH", "80 km/h", (TX, AY0 - 0.25, TZ + AH + 0.12), 0.12, lab_m, extrude=0.01)
pop(kmh, S[2] + 4, 5, S[3] + 1)

# ---------------- lines 3-4: G-force bars + little jet ----------------
GX, GY = -1.55, 1.2
bar_big = box("BarBig", (GX + 0.3, GY, 0), (0.45, 0.45, 1.0), red_lab)
bpy.context.view_layer.update()
bar_big.data.transform(__import__("mathutils").Matrix.Translation((0, 0, 0.5)))
keyscale(bar_big, [(0, 0.001), (S[3] - 1, 0.001), (S[3], (1, 1, 0.01)), (S[3] + 14, (1, 1, 7.0)), (S[5] + 2, (1, 1, 7.0)), (S[5] + 6, 0.001)])
bar_s = box("BarSmall", (GX - 0.4, GY, 0.04), (0.45, 0.45, 0.08), blue_lab)
pop(bar_s, S[4], 4, S[5] + 6)
g1 = text("G1", "10,000 G", (GX + 0.1, GY - 0.45, 1.6), 0.36, lab_m, extrude=0.02)
pop(g1, S[3] + 6, 5, S[5] + 4)
g2 = text("G2", "9 G", (GX - 0.45, GY - 0.45, 0.6), 0.3, white_lab, extrude=0.02)
pop(g2, S[4] + 4, 5, S[5] + 4)
jet = group("Jet", (GX - 0.4, GY, 0.95))
jm = mat("JetM", (0.7, 0.74, 0.8), 0.35)
jp = [cyl("JetBody", (GX - 0.4, GY, 0.95), 0.1, 0.8, jm, rot=(0, math.radians(90), 0)),
      cyl("JetNose", (GX + 0.06, GY, 0.95), 0.1, 0.18, jm, rot=(0, math.radians(90), 0), r2=0.01),
      box("JetWing", (GX - 0.45, GY, 0.95), (0.3, 0.9, 0.03), jm),
      box("JetTail", (GX - 0.75, GY, 1.08), (0.15, 0.03, 0.22), jm),
      sphere("JetCanopy", (GX - 0.2, GY, 1.03), 0.08, mat("Canopy", (0.3, 0.6, 0.9), 0.1), scale=(1.6, 0.8, 0.7))]
attach(jp, jet)
hide_until(jet, S[4])
for k, f in enumerate(range(S[4], S[5] + 4, 6)):
    jet.rotation_euler = (0.25 * (1 if k % 2 else -1), 0, 0); jet.keyframe_insert("rotation_euler", frame=f)
for k in range(5):   # dizzy stars
    a = k / 5 * 6.283
    s_ = sphere("Dizzy", (GX - 0.4 + 0.3 * math.cos(a), GY - 0.2, 1.3 + 0.1 * math.sin(a)), 0.04, lab_m, sub=1)
    pop(s_, S[4] + 8 + k, 3, S[5] + 4)
gone_at(jet, S[5] + 6)

# ---------------- line 5: stopwatch ----------------
WX, WY, WZ = -0.95, 0.55, 1.05
watch = group("Watch", (WX, WY, WZ))
wp = [cyl("WatchBody", (WX, WY + 0.03, WZ), 0.36, 0.08, mat("WatchM", (0.95, 0.3, 0.2), 0.4), rot=(math.radians(90), 0, 0), verts=40),
      cyl("WatchFace", (WX, WY - 0.02, WZ), 0.3, 0.02, white_lab, rot=(math.radians(90), 0, 0), verts=40),
      cyl("WatchBtn", (WX, WY + 0.03, WZ + 0.42), 0.06, 0.1, mat("WatchM2", (0.6, 0.6, 0.62), 0.3, metal=0.6))]
for k in range(12):
    a = k / 12 * 6.283
    wp.append(box("WTick", (WX + 0.25 * math.sin(a), WY - 0.04, WZ + 0.25 * math.cos(a)), (0.02, 0.01, 0.05), eyeb, rot=(0, a, 0)))
attach(wp, watch)
hand = group("WHand", (WX, WY - 0.05, WZ))
attach([box("WHandB", (WX, WY - 0.05, WZ + 0.11), (0.025, 0.01, 0.22), red_lab)], hand)
pop(watch, S[5] - 2, 5, S[6] + 4)
pop(hand, S[5] - 2, 5, S[6] + 4)
hand.rotation_euler = (0, 0, 0); hand.keyframe_insert("rotation_euler", frame=S[5] + 4)
hand.rotation_euler = (0, 0.25, 0); hand.keyframe_insert("rotation_euler", frame=S[5] + 6)
ms = text("MS", "0.003 s", (WX, WY - 0.08, WZ - 0.52), 0.17, lab_m, extrude=0.015)
pop(ms, S[5] + 6, 5, S[6] + 4)

# ---------------- line 7: x2,500 its weight — a pile of mini shrimp ----------------
mini_m = [orange, green, teal]
k = 0
for row in range(4):
    for i in range(7 - row):
        x = TX - 0.45 + (i + row * 0.5) * 0.15
        p_ = (x, TY - 0.6, 0.06 + row * 0.1)
        g = group("Mini", p_)
        mp = [sphere("MiniB", p_, 0.07, mini_m[(i + row) % 3], scale=(1.4, 0.7, 0.7), sub=2),
              sphere("MiniE", (p_[0] + 0.07, p_[1] - 0.04, p_[2] + 0.05), 0.025, eyew, sub=1),
              sphere("MiniP", (p_[0] + 0.08, p_[1] - 0.06, p_[2] + 0.05), 0.012, eyeb, sub=1)]
        attach(mp, g)
        pop(g, S[7] + k, 4, S[8] + 2)
        k += 1
x2500 = text("X2500", "x2,500", (TX, TY - 0.62, 0.72), 0.2, lab_m, extrude=0.02)
pop(x2500, S[7] + 6, 5, S[8] + 2)
wtl = text("WT", "ITS WEIGHT", (TX, TY - 0.62, 0.55), 0.09, white_lab, extrude=0.01)
pop(wtl, S[7] + 10, 5, S[8] + 2)

# ---------------- lines 8-10: cavitation bubbles, flash, heat ----------------
CB = club_world(S[8] + 4)
CB = (CB[0] + 0.012, CB[1] - 0.01, CB[2])
for i in range(16):
    p_ = (CB[0] + random.uniform(-0.02, 0.025), CB[1] + random.uniform(-0.015, 0.01), CB[2] + random.uniform(-0.02, 0.02))
    b_ = sphere("Cav", p_, random.uniform(0.004, 0.009), bubble_m, sub=2)
    f0 = S[8] + 4 + i // 2
    keyscale(b_, [(0, 0.001), (f0 - 1, 0.001), (f0 + 3, 1.3), (f0 + 8, 1.0), (S[9] + 4, 1.1), (S[9] + 8, 0.001)])
flash = sphere("Flash", CB, 0.035, glow_mat("FlashM", (0.85, 0.95, 1.0), 2.0), sub=2)
keyscale(flash, [(0, 0.001), (S[9] + 6, 0.001), (S[9] + 8, 0.9), (S[9] + 11, 0.5), (S[9] + 13, 0.8), (S[9] + 18, 0.001)])
bpy.ops.object.light_add(type='POINT', location=(CB[0], CB[1] - 0.05, CB[2] + 0.03))
fl = bpy.context.object; fl.data.color = (0.8, 0.9, 1.0); fl.data.shadow_soft_size = 0.02
fl.data.energy = 0; fl.data.keyframe_insert("energy", frame=S[9] + 6)
fl.data.energy = 1.5; fl.data.keyframe_insert("energy", frame=S[9] + 8)
fl.data.energy = 0; fl.data.keyframe_insert("energy", frame=S[9] + 18)
burst(CB, S[9] + 8, 12, 0.05, 0.004, S[10])
hit2 = text('Hit2', 'HIT 2!', (TX, AY0 - 0.03, TZ + AH + 0.05), 0.1, red_lab, extrude=0.008)
pop(hit2, S[9] + 8, 4, S[10] + 2)
heat = sphere("Heat", CB, 0.03, glow_mat("HeatM", (1.0, 0.45, 0.08), 9.0), sub=2)
keyscale(heat, [(0, 0.001), (S[10] - 1, 0.001), (S[10] + 3, 1.3), (S[10] + 8, 0.9), (S[10] + 13, 1.2), (S[10] + 20, 0.9), (S[11] - 1, 0.001)])
THX, THY = TX + 0.5, TY - 0.15
thermo = group("Thermo", (THX, THY, TZ))
tp = [cyl("ThGlass", (THX, THY, TZ + 0.3), 0.035, 0.5, white_lab), sphere("ThBulb", (THX, THY, TZ + 0.05), 0.06, red_lab, sub=2)]
attach(tp, thermo)
merc = box("Merc", (THX, THY - 0.03, TZ + 0.05), (0.03, 0.01, 0.5), red_lab)
bpy.context.view_layer.update()
merc.data.transform(__import__("mathutils").Matrix.Translation((0, 0, 0.25)))
pop(thermo, S[10] - 2, 4, S[11] + 2)
keyscale(merc, [(0, (1, 1, 0.001)), (S[10], (1, 1, 0.05)), (S[10] + 14, (1, 1, 1.0)), (S[11] - 2, (1, 1, 1.0)), (S[11] + 2, (1, 1, 0.001))])
hot = text("Hot", "1000s °C", (THX - 0.2, AY0 - 0.06, TZ + AH + 0.1), 0.08, red_lab, extrude=0.008)
pop(hot, S[10] + 4, 5, S[11] + 2)

# ---------------- line 11: smashes a clam, then the aquarium glass ----------------
CL2 = club_hit_point(S[11] + 4)
shatter((CL2[0] + 0.012, CL2[1], FL + 0.022), 0.026, clam_m, S[11] + 4, S[12], scale=(1.3, 1, 0.6))
# ---------------- line 12: turns to the front glass and cracks it ----------------
shr.rotation_euler = (0, 0, 0); shr.keyframe_insert("rotation_euler", frame=S[11] + 12)
shr.rotation_euler = (0, 0, math.radians(-62)); shr.keyframe_insert("rotation_euler", frame=S[11] + 18)
shr.keyframe_insert("rotation_euler", frame=S[12] + 30)
shr.rotation_euler = (0, 0, 0); shr.keyframe_insert("rotation_euler", frame=S[12] + 36)
CG = club_world(S[11] + 24)
CC = (CG[0], AY0 - 0.004, CG[2] + 0.01)
crack_m = glow_mat("Crack", (1, 1, 1), 2.5)
cr_objs = []
for k in range(9):
    a = k / 9 * 6.283 + random.uniform(-0.2, 0.2)
    pts, rr = [CC], 0.0
    for s_ in range(3):
        rr += random.uniform(0.03, 0.06)
        aa = a + random.uniform(-0.25, 0.25)
        pts.append((CC[0] + rr * math.cos(aa), CC[1], CC[2] + rr * math.sin(aa)))
    pts = [(max(TX - AW/2 + 0.01, min(TX + AW/2 - 0.01, p[0])), p[1], max(TZ + 0.01, min(TZ + AH - 0.01, p[2]))) for p in pts]
    cr_objs.append(tube("CrackL", pts, [0.0018] * len(pts), crack_m))
ring = tube("CrackRing", [(CC[0] + 0.035 * math.cos(a / 16 * 6.283), CC[1], CC[2] + 0.035 * math.sin(a / 16 * 6.283)) for a in range(17)], [0.0016] * 17, crack_m)
for o in cr_objs + [ring]:
    bpy.context.view_layer.update()
    hide_until(o, S[11] + 24)
crk = text("Crk", "CRACK!", (CC[0], AY0 - 0.03, TZ + AH + 0.04), 0.08, lab_m, extrude=0.008)
pop(crk, S[11] + 24, 4, S[12] + 2)
burst(CC, S[11] + 24, 10, 0.06, 0.005, S[12])

# ---------------- lines 12-17: YOU — a normal punch, then the mantis-shrimp punch ----------------
MX, MYY = 3.3, 0.9
skin_m = mat("Skin", (0.95, 0.74, 0.58), 0.6)
shirt_m = mat("Shirt", (0.95, 0.3, 0.25), 0.7)
pants_m = mat("Pants", (0.2, 0.3, 0.6), 0.8)
hair_m = mat("ManHair", (0.28, 0.16, 0.07), 0.8)
for sx in (-1, 1):
    tube("MLeg", [(MX + sx * 0.18, MYY, 1.0), (MX + sx * 0.22, MYY, 0.12)], [0.15, 0.13], pants_m)
    box("MShoe", (MX + sx * 0.22, MYY - 0.08, 0.07), (0.24, 0.42, 0.14), mat("Shoe", (0.15, 0.15, 0.18), 0.6), bevel=0.04)
sphere("MTorso", (MX, MYY, 1.45), 1.0, shirt_m, scale=(0.42, 0.3, 0.55), sub=3)
sphere("MHead", (MX, MYY, 2.25), 0.34, skin_m, sub=3)
sphere("MHair", (MX, MYY + 0.05, 2.43), 0.32, hair_m, scale=(1.05, 1.0, 0.55), sub=2)
for sx in (-1, 1):
    sphere("MEyeW", (MX + sx * 0.12, MYY - 0.3, 2.32), 0.08, eyew, scale=(1, 0.6, 1.2), sub=2)
    sphere("MEyeB", (MX + sx * 0.12 + 0.02, MYY - 0.35, 2.31), 0.04, eyeb, sub=1)
grin = tube("MGrin", [(MX - 0.12, MYY - 0.31, 2.14), (MX, MYY - 0.35, 2.08), (MX + 0.12, MYY - 0.31, 2.14)], [0.02] * 3, eyeb)
tube("MArmL", [(MX - 0.38, MYY, 1.75), (MX - 0.5, MYY - 0.05, 1.3), (MX - 0.48, MYY - 0.1, 1.0)], [0.09, 0.085, 0.08], shirt_m)
sphere("MHandL", (MX - 0.48, MYY - 0.1, 0.95), 0.09, skin_m, sub=2)
# "ouch" face during the normal punch (mouth turns down), happy again with the shrimp power
grin.keyframe_insert("rotation_euler", frame=S[12] + 12); grin.keyframe_insert("location", frame=S[12] + 12)
grin.rotation_euler = (0, math.radians(180), 0); grin.location = (2 * MX, 0, 2 * 2.11)
grin.keyframe_insert("rotation_euler", frame=S[12] + 14); grin.keyframe_insert("location", frame=S[12] + 14)
grin.keyframe_insert("rotation_euler", frame=S[13] + 2); grin.keyframe_insert("location", frame=S[13] + 2)
grin.rotation_euler = (0, 0, 0); grin.location = (0, 0, 0)
grin.keyframe_insert("rotation_euler", frame=S[13] + 4); grin.keyframe_insert("location", frame=S[13] + 4)
grin.keyframe_insert("rotation_euler", frame=0); grin.keyframe_insert("location", frame=0)
# punching arm (screen-right)
parm = group("PArm", (MX + 0.38, MYY - 0.05, 1.7))
pa = [tube("MArmR", [(MX + 0.38, MYY - 0.05, 1.7), (MX + 0.95, MYY - 0.12, 1.62)], [0.09, 0.085], shirt_m),
      sphere("MHandR", (MX + 1.0, MYY - 0.12, 1.62), 0.11, skin_m, sub=2)]
attach(pa, parm)
glove = group("Glove", (MX + 1.08, MYY - 0.12, 1.62))
gl = [sphere("GloveB", (MX + 1.08, MYY - 0.12, 1.62), 0.2, orange, scale=(1.25, 1, 1), sub=3),
      sphere("GloveT", (MX + 1.24, MYY - 0.12, 1.62), 0.12, yellow, sub=2),
      sphere("GloveR", (MX + 0.95, MYY - 0.12, 1.62), 0.15, red, scale=(0.5, 1.1, 1.1), sub=2)]
arm_m = mat("Armor", (0.85, 0.88, 0.92), 0.15, metal=1.0)
plates = [tube("Plate", [(MX + 0.98 + k * 0.1, MYY - 0.12 + 0.205 * math.cos(a / 16 * 6.283), 1.62 + 0.205 * math.sin(a / 16 * 6.283)) for a in range(17)],
               [0.03] * 17, arm_m) for k in range(3)]
for pl in plates:
    hide_until(pl, S[16] + 2)
attach(gl + plates, glove)
glove.parent = parm; glove.matrix_parent_inverse = parm.matrix_world.inverted()
hide_until(glove, S[13] + 2)
keyscale(glove, [(S[13] + 2, 0.001), (S[13] + 6, 1.2), (S[13] + 9, 1.0)])
GUARD = (0, -1.0, 0)
REST = (MX + 0.38, MYY - 0.05, 1.7)
def punch(f_hit, reach, bounce=False):
    parm.rotation_euler = GUARD; parm.keyframe_insert("rotation_euler", frame=f_hit - 5)
    parm.location = REST; parm.keyframe_insert("location", frame=f_hit - 5)
    parm.rotation_euler = (0, 0.05, 0); parm.keyframe_insert("rotation_euler", frame=f_hit)
    parm.location = (REST[0] + reach, REST[1], REST[2]); parm.keyframe_insert("location", frame=f_hit)
    if bounce:   # fist stops dead and recoils
        parm.location = (REST[0] - 0.05, REST[1], REST[2]); parm.keyframe_insert("location", frame=f_hit + 4)
        parm.rotation_euler = (0, -0.3, 0); parm.keyframe_insert("rotation_euler", frame=f_hit + 4)
    else:
        parm.keyframe_insert("location", frame=f_hit + 6); parm.keyframe_insert("rotation_euler", frame=f_hit + 6)
    parm.rotation_euler = GUARD; parm.keyframe_insert("rotation_euler", frame=f_hit + 14)
    parm.location = REST; parm.keyframe_insert("location", frame=f_hit + 14)
parm.rotation_euler = GUARD; parm.keyframe_insert("rotation_euler", frame=0)
youl = text("YouL", "YOU", (MX, MYY - 0.4, 3.6), 0.4, lab_m, extrude=0.03)
pop(youl, S[12], 5, S[12] + 14)
# the boulder (hit twice)
BX, BY, BR = MX + 1.95, MYY + 0.05, 0.75
rock_m = mat("Boulder", (0.55, 0.53, 0.5), 0.85)
boulder = sphere("Boulder", (BX, BY, BR * 0.95), BR, rock_m, scale=(1, 1, 0.95), sub=2, smooth=False)
# line 12: NORMAL punch — fist bounces off, boulder only wobbles
HIT12 = S[12] + 12
punch(HIT12, 0.12, bounce=True)
boulder.rotation_euler = (0, 0, 0); boulder.keyframe_insert("rotation_euler", frame=HIT12)
boulder.rotation_euler = (0, 0.04, 0); boulder.keyframe_insert("rotation_euler", frame=HIT12 + 2)
boulder.rotation_euler = (0, 0, 0); boulder.keyframe_insert("rotation_euler", frame=HIT12 + 5)
norm = text("Norm", "NORMAL PUNCH", (MX + 0.9, MYY - 0.6, 4.05), 0.24, white_lab, extrude=0.02)
pop(norm, S[12] + 4, 5, S[13])
ouch = text("Ouch", "OUCH!", (MX + 1.2, MYY - 0.8, 3.75), 0.34, red_lab, extrude=0.03)
pop(ouch, HIT12 + 1, 4, S[13])
for k in range(5):   # little stars around the sore hand
    a = k / 5 * 6.283
    s_ = sphere("Star", (MX + 1.25 + 0.28 * math.cos(a), MYY - 0.3, 1.65 + 0.28 * math.sin(a)), 0.05, lab_m, sub=1)
    pop(s_, HIT12 + 2 + k, 3, S[13])
# line 13: shrimp power switched on
burst((MX + 1.15, MYY - 0.35, 1.65), S[13] + 4, 12, 0.45, 0.05, S[13] + 20)
spw = text("SPow", "SHRIMP POWER", (MX + 1.0, MYY - 0.6, 3.2), 0.17, lab_m, extrude=0.02)
pop(spw, S[13] + 4, 5, S[14])
# line 14: 100 cars pile behind him
CXp, CYp = MX - 0.6, MYY + 4.2
k = 0
for z in range(5):
    for yy in range(4):
        for xx in range(5):
            o = bpy.data.objects.new("PileCar", cars[(xx + yy + z) % 4].data); sc.collection.objects.link(o)
            o.location = (CXp + (xx - 2) * 1.85, CYp + yy * 0.95, z * 0.85)
            o.rotation_euler = (0, 0, random.uniform(-0.12, 0.12))
            o.scale = (0.001,) * 3; o.keyframe_insert("scale", frame=0)
            f0 = S[14] + 2 + k // 3
            o.keyframe_insert("scale", frame=f0)
            o.scale = (1.0,) * 3; o.keyframe_insert("scale", frame=f0 + 4)
            gone_at(o, S[15] - 2 + (k % 5), 4)
            k += 1
c100 = text("C100", "100 CARS", (CXp, CYp - 1.0, 5.6), 1.1, lab_m, extrude=0.05)
pop(c100, S[14] + 14, 5, S[15] + 2)
# line 15: SHRIMP punch — the boulder bursts and the pieces fly across the yard
HIT15 = S[15] + 6
punch(HIT15, 0.2)
gone_at(boulder, HIT15 + 1, 1)
chunk_m = [rock_m, mat("Boulder2", (0.48, 0.46, 0.44), 0.85), mat("Boulder3", (0.62, 0.6, 0.56), 0.85)]
for i in range(18):
    th = random.uniform(-1.2, 1.2); ph = random.uniform(-0.8, 1.0)
    p0 = (BX + 0.4 * math.cos(ph) * math.cos(th), BY + 0.4 * math.cos(ph) * math.sin(th), BR + 0.5 * math.sin(ph))
    c = sphere("RockChunk", p0, random.uniform(0.18, 0.32), random.choice(chunk_m), sub=1, smooth=False)
    dist = random.uniform(3, 7)
    p2 = (BX + dist, BY + random.uniform(2.0, 9.0), 0.15)
    pm = (BX + dist * 0.5, (p0[1] + p2[1]) / 2, random.uniform(2.5, 5.0))
    key_loc(c, [(HIT15, p0), (HIT15 + 9, pm), (HIT15 + 20, p2)])
    c.rotation_euler = (0, 0, 0); c.keyframe_insert("rotation_euler", frame=HIT15)
    c.rotation_euler = (random.uniform(4, 9), random.uniform(4, 9), 0); c.keyframe_insert("rotation_euler", frame=HIT15 + 20)
    keyscale(c, [(0, 0.001), (HIT15, 0.001), (HIT15 + 1, 1.0)])
burst((BX - 0.3, BY - 0.8, 1.6), HIT15, 14, 0.6, 0.06, S[16] + 4)
dust_m = mat("Dust", (0.85, 0.8, 0.7), 0.9)
for i in range(16):
    p0 = (BX + random.uniform(-0.4, 0.4), BY - 0.3, random.uniform(0.3, 1.4))
    d = sphere("Dust", p0, random.uniform(0.12, 0.22), dust_m, sub=1, smooth=False)
    key_loc(d, [(HIT15, p0), (HIT15 + 16, (p0[0] + random.uniform(0, 2.0), p0[1] - 0.3, p0[2] + random.uniform(0.3, 1.2)))])
    keyscale(d, [(0, 0.001), (HIT15 - 1, 0.001), (HIT15 + 2, 1.0), (HIT15 + 14, 0.8), (HIT15 + 18, 0.001)])
boom = text("Boom", "BOOM!", (BX + 0.3, BY - 1.0, 3.3), 0.5, lab_m, extrude=0.04)
pop(boom, HIT15 + 1, 4, S[16] + 2)
# line 16: armor plates on the glove
armt = text("Armor", "ARMOR", (MX + 0.95, MYY - 0.6, 3.2), 0.22, blue_lab, extrude=0.03)
pop(armt, S[16] + 4, 5, S[17])
parm.keyframe_insert("rotation_euler", frame=S[17])
parm.rotation_euler = (0, -1.4, 0); parm.keyframe_insert("rotation_euler", frame=S[17] + 6)   # fist up at the end
# line 17: question mark
q = text("Q", "?", (MX + 0.2, MYY - 0.3, 3.95), 0.8, lab_m, extrude=0.08)
pop(q, S[17] + 2, 6)
q.rotation_euler = (math.radians(90), 0, 0); q.keyframe_insert("rotation_euler", frame=S[17] + 2)
q.rotation_euler = (math.radians(90), 0, math.radians(360)); q.keyframe_insert("rotation_euler", frame=FRAMES)
sc.frame_set(0)

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
SHC = (SH[0] + 0.06, SH[1], FL + 0.03)
SNC = (SN[0] - 0.03, SN[1], FL + 0.03)
CL2C = (CL2[0], CL2[1], FL + 0.03)
# (frame, camera, SUBJECT) — the subject is framed in the lower third, under the centre captions
cam_keys = [
    (0,          (0.1, -0.05, 1.08),   SHC),                                     # hook: clam smashed
    (S[1] - 6,   (0.02, 0.33, 0.98),   (SH[0] + 0.02, SH[1], FL + 0.02)),         # 10 cm
    (S[1] + 4,   (-0.12, 0.38, 0.97),  (SH[0] + 0.02, SH[1], FL + 0.02)),
    (S[2] - 4,   (0.12, 0.4, 0.99),    (SH[0] + 0.02, SH[1], FL + 0.02)),
    (S[2] + 4,   (0.5, -3.4, 1.6),     (0.0, -0.3, 0.35)),                        # car zoom 80 km/h
    (S[3] - 2,   (-0.6, -3.2, 1.8),    (-0.4, 0.0, 0.45)),
    (S[3] + 6,   (-0.2, -3.6, 2.4),    (GX, GY, 0.9)),                            # 10,000 G
    (S[4] - 2,   (-1.6, -3.8, 2.6),    (GX, GY, 1.0)),
    (S[4] + 4,   (-1.8, -1.2, 1.4),    (GX - 0.3, GY, 0.6)),                      # 9 G
    (S[5] - 2,   (-1.1, -1.0, 1.4),    (GX - 0.3, GY, 0.6)),
    (S[5] + 4,   (-0.7, -1.1, 1.3),    (WX, WY, WZ - 0.15)),                      # stopwatch
    (S[6] - 2,   (-1.2, -1.2, 1.4),    (WX, WY, WZ - 0.15)),
    (S[6] + 4,   (SN[0] - 0.02, 0.36, 0.99), SNC),                                # snail shell explodes
    (S[7] - 2,   (SN[0] - 0.1, 0.38, 1.0),   SNC),
    (S[7] + 4,   (0.4, -1.4, 1.5),     (TX, TY - 0.6, 0.2)),                      # x2,500
    (S[8] - 2,   (-0.3, -1.5, 1.4),    (TX, TY - 0.6, 0.2)),
    (S[8] + 4,   (CB[0] + 0.08, CB[1] - 0.45, CB[2] + 0.08), CB),                 # bubbles
    (S[9] - 2,   (CB[0] - 0.06, CB[1] - 0.42, CB[2] + 0.07), CB),
    (S[9] + 4,   (CB[0] + 0.02, CB[1] - 0.4, CB[2] + 0.06),  CB),                 # flash, hit 2
    (S[10] - 2,  (CB[0] + 0.08, CB[1] - 0.42, CB[2] + 0.06), CB),
    (S[10] + 4,  (0.3, 0.05, 1.15),    (0.2, TY - 0.1, TZ + 0.12)),               # heat
    (S[11] - 2,  (0.1, 0.0, 1.2),      (0.2, TY - 0.1, TZ + 0.12)),
    (S[11] + 4,  (CL2[0] + 0.02, 0.38, 0.99), CL2C),                              # clam smashed
    (S[11] + 16, (CC[0] + 0.03, 0.2, 1.02),   (CC[0], CC[1], CC[2] - 0.01)),      # glass cracks
    (S[12] - 2,  (CC[0] - 0.04, 0.15, 1.04),  (CC[0], CC[1], CC[2] - 0.01)),
    (S[12] + 4,  (4.6, -3.4, 2.4),     (MX + 0.9, MYY, 1.6)),                     # normal punch, ouch
    (S[13] - 2,  (4.9, -3.2, 2.3),     (MX + 0.9, MYY, 1.6)),
    (S[13] + 4,  (MX + 1.4, MYY - 2.6, 2.0), (MX + 0.9, MYY, 1.75)),               # shrimp power glove
    (S[14] - 2,  (MX + 0.8, MYY - 2.6, 2.0), (MX + 0.9, MYY, 1.75)),
    (S[14] + 4,  (2.8, -6.8, 4.2),     (CXp, CYp, 0.6)),                          # 100 cars
    (S[15] - 2,  (3.6, -5.4, 3.2),     (BX - 0.5, BY, 0.6)),
    (S[15] + 8,  (4.0, -5.2, 3.0),     (BX + 0.2, BY + 1.2, 0.5)),                      # boulder bursts, flies
    (S[16] - 2,  (4.8, -5.8, 3.4),     (BX + 1.0, BY + 2.5, 0.4)),
    (S[16] + 4,  (MX + 1.2, MYY - 2.3, 2.2), (MX + 0.9, MYY, 1.75)),               # armor
    (S[17] - 2,  (MX + 0.6, MYY - 2.3, 2.2), (MX + 0.9, MYY, 1.75)),
    (S[17] + 6,  (3.0, -3.4, 2.8),     (MX + 0.3, MYY, 1.6)),                     # final question
    (FRAMES - 1, (2.6, -3.2, 3.0),     (MX + 0.1, MYY, 1.6)),
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
cam_keys = [(f, overhead(cl, tl), tl) for f, cl, tl in cam_keys]
for f, cl, tl in cam_keys:
    cam.location = cl; cam.keyframe_insert("location", frame=f)
    target.location = aim(cl, tl); target.keyframe_insert("location", frame=f)

for o in bpy.data.objects:
    if o.type == 'FONT':
        o.visible_shadow = False
bpy.ops.wm.save_as_mainfile(filepath=f"{HERE}/scene.blend")
print("SCENE OK", FRAMES, S)
