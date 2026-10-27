# Day 2 — What if a UFO landed in your backyard?
# Build: python3 episodes/002-ufo-backyard/scene.py   (writes scene.blend next to this file)
# Helpers (mat/box/cyl/sphere/tube) adapted from episodes/001-dig-forever/scene.py
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
sc.cycles.transmission_bounces = 2
sc.cycles.transparent_max_bounces = 6
sc.render.use_persistent_data = True
sc.render.resolution_x = 1080
sc.render.resolution_y = 1920
sc.render.resolution_percentage = 40
sc.render.fps = FPS
sc.frame_start = 0
sc.frame_end = FRAMES - 1
sc.render.image_settings.file_format = 'PNG'
sc.view_settings.view_transform = 'Standard'
sc.view_settings.exposure = 0.0

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

def glow_mat(name, color, strength, alpha=1.0):
    """Pure emission; alpha < 1 mixes with transparency (beams, light cones)."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree; N = nt.nodes; L = nt.links
    N.remove(N["Principled BSDF"])
    out = N["Material Output"]
    em = N.new("ShaderNodeEmission"); em.inputs["Color"].default_value = (*color, 1)
    em.inputs["Strength"].default_value = strength
    if alpha < 1.0:
        tr = N.new("ShaderNodeBsdfTransparent")
        mx = N.new("ShaderNodeMixShader"); mx.inputs["Fac"].default_value = alpha
        L.new(tr.outputs[0], mx.inputs[1]); L.new(em.outputs[0], mx.inputs[2])
        L.new(mx.outputs[0], out.inputs["Surface"])
    else:
        L.new(em.outputs[0], out.inputs["Surface"])
    return m

def emit_key(m, frame, strength):
    n = m.node_tree.nodes
    inp = n["Emission"].inputs["Strength"] if "Emission" in n else n["Principled BSDF"].inputs["Emission Strength"]
    inp.default_value = strength
    inp.keyframe_insert("default_value", frame=frame)

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

def face(x, y, tx=0.0, ty=1.0):
    """z-rotation that turns a person (built facing -y) toward (tx, ty)."""
    return math.atan2(tx - x, -(ty - y))

def group(name, loc, rot_z=0.0):
    e = bpy.data.objects.new(name, None); sc.collection.objects.link(e)
    e.location = loc; e["rz"] = rot_z   # rotation applied after children are attached
    return e

def attach(objs, parent):
    parent.rotation_euler = (0, 0, 0)   # children are modelled unrotated
    bpy.context.view_layer.update()
    for o in objs:
        o.parent = parent
        o.matrix_parent_inverse = parent.matrix_world.inverted()
    parent.rotation_euler = (0, 0, parent.get("rz", 0.0))

def pop(o, f_in, dur=6, f_out=None):
    """Scale-pop an object (or group empty) in at f_in (overshoot), optionally out at f_out."""
    o.scale = (0.001,) * 3; o.keyframe_insert("scale", frame=max(f_in - 1, 0))
    o.scale = (1.15,) * 3; o.keyframe_insert("scale", frame=f_in + dur * 0.65)
    o.scale = (1.0,) * 3; o.keyframe_insert("scale", frame=f_in + dur)
    if f_out is not None:
        o.keyframe_insert("scale", frame=f_out - 4)
        o.scale = (0.001,) * 3; o.keyframe_insert("scale", frame=f_out)

# ---------------- world: bright cartoon night ----------------
w = bpy.data.worlds.new("W"); sc.world = w
w.use_nodes = True
nt = w.node_tree
bg = nt.nodes["Background"]
tc = nt.nodes.new("ShaderNodeTexCoord")
sep = nt.nodes.new("ShaderNodeSeparateXYZ")
ramp = nt.nodes.new("ShaderNodeValToRGB")
el = ramp.color_ramp.elements
el[0].position = 0.0; el[0].color = (0.55, 0.32, 0.75, 1)       # purple horizon glow
el[1].position = 0.35; el[1].color = (0.05, 0.08, 0.30, 1)      # deep blue
e2 = el.new(0.12); e2.color = (0.22, 0.22, 0.62, 1)
nt.links.new(tc.outputs["Generated"], sep.inputs[0])
nt.links.new(sep.outputs["Z"], ramp.inputs[0])
nt.links.new(ramp.outputs["Color"], bg.inputs["Color"])
bg.inputs["Strength"].default_value = 1.0

bpy.ops.object.light_add(type='SUN', rotation=(math.radians(48), 0, math.radians(-35)))
moonlight = bpy.context.object
moonlight.data.energy = 1.6
moonlight.data.color = (0.62, 0.72, 1.0)
moonlight.data.angle = math.radians(6)
# soft fill so the diorama stays readable (bright cartoon look)
bpy.ops.object.light_add(type='AREA', location=(0, -16, 14))
fill = bpy.context.object
fill.data.energy = 2600; fill.data.size = 14; fill.data.color = (0.75, 0.8, 1.0)
fill.rotation_euler = (math.radians(50), 0, 0)

# moon + stars
moon_m = glow_mat("Moon", (1.0, 0.97, 0.85), 3.0)
sphere("Moon", (-38, 120, 70), 5.0, moon_m, sub=3)
star_m = glow_mat("Star", (1.0, 1.0, 0.95), 6.0)
for i in range(240):
    a = random.uniform(-1.4, 1.4); el_ = random.uniform(0.12, 1.45)
    r = 170
    p = (r * math.sin(a) * math.cos(el_), r * math.cos(a) * math.cos(el_) + 10, r * math.sin(el_))
    if p[1] < -20:
        continue
    sphere("Star", p, random.uniform(0.5, 1.0), star_m, sub=0, smooth=False)

# ---------------- ground diorama ----------------
FRONT_Y = -4.0
grass_m = bpy.data.materials.new("Grass"); grass_m.use_nodes = True
gn = grass_m.node_tree; N = gn.nodes; L = gn.links
bs = N["Principled BSDF"]; bs.inputs["Roughness"].default_value = 0.95
geo = N.new("ShaderNodeNewGeometry")
sxyz = N.new("ShaderNodeSeparateXYZ"); L.new(geo.outputs["Position"], sxyz.inputs[0])
# mowed stripes
mul = N.new("ShaderNodeMath"); mul.operation = 'MULTIPLY'; mul.inputs[1].default_value = 1.3
L.new(sxyz.outputs["X"], mul.inputs[0])
sn = N.new("ShaderNodeMath"); sn.operation = 'SINE'; L.new(mul.outputs[0], sn.inputs[0])
gt = N.new("ShaderNodeMath"); gt.operation = 'GREATER_THAN'; gt.inputs[1].default_value = 0.0
L.new(sn.outputs[0], gt.inputs[0])
gmix = N.new("ShaderNodeMix"); gmix.data_type = 'RGBA'
gmix.inputs[6].default_value = (0.16, 0.48, 0.14, 1); gmix.inputs[7].default_value = (0.24, 0.60, 0.18, 1)
L.new(gt.outputs[0], gmix.inputs["Factor"])
# soil layers on the cut face (by z)
cr = N.new("ShaderNodeValToRGB"); cr.color_ramp.interpolation = 'CONSTANT'
ce = cr.color_ramp.elements
ce[0].position = 0.0; ce[0].color = (0.42, 0.24, 0.12, 1)
ce[1].position = 0.55; ce[1].color = (0.55, 0.33, 0.16, 1)
c3 = ce.new(0.85); c3.color = (0.35, 0.2, 0.1, 1)
mr = N.new("ShaderNodeMapRange"); mr.inputs["From Min"].default_value = -4.0; mr.inputs["From Max"].default_value = 0.0
L.new(sxyz.outputs["Z"], mr.inputs["Value"]); L.new(mr.outputs["Result"], cr.inputs["Fac"])
cap = N.new("ShaderNodeMapRange"); cap.inputs["From Min"].default_value = -0.22; cap.inputs["From Max"].default_value = -0.1
L.new(sxyz.outputs["Z"], cap.inputs["Value"])
fin = N.new("ShaderNodeMix"); fin.data_type = 'RGBA'
L.new(cap.outputs["Result"], fin.inputs["Factor"])
L.new(cr.outputs["Color"], fin.inputs[6]); L.new(gmix.outputs[2], fin.inputs[7])
L.new(fin.outputs[2], bs.inputs["Base Color"])
box("Ground", (0, 5.0, -2.0), (26, 18, 4.0), grass_m)
under_m = mat("Underside", (0.07, 0.07, 0.16), 0.9)
bpy.ops.mesh.primitive_plane_add(size=600, location=(0, 0, -4.05))
bpy.context.object.data.materials.append(under_m)
far = mat("LawnFar", (0.12, 0.34, 0.12), 0.95)
bpy.ops.mesh.primitive_plane_add(size=600, location=(0, 300, -0.03))
bpy.context.object.data.materials.append(far)
# pebbles + roots on the cut face (in front of it)
stone_m = mat("Stone", (0.62, 0.58, 0.52), 0.8)
for i in range(26):
    sphere("Peb", (random.uniform(-12, 12), FRONT_Y - 0.02, random.uniform(-3.6, -0.6)), random.uniform(0.1, 0.25),
           stone_m, scale=(1.3, 0.5, 0.8), sub=1, smooth=False)

# ---------------- house + fence + trees ----------------
wall_m = mat("Wall", (0.95, 0.86, 0.68), 0.85)
roof_m = mat("Roof", (0.85, 0.30, 0.22), 0.75)
trim_m = mat("Trim", (0.97, 0.97, 0.95), 0.6)
win_m = mat("Window", (1.0, 0.8, 0.4), 0.3, emit=(1.0, 0.72, 0.3), emit_strength=6.0)
HX, HY, HW, HD, HH = 0.0, 9.6, 8.0, 4.0, 4.6
box("House", (HX, HY, HH / 2), (HW, HD, HH), wall_m)
bpy.ops.mesh.primitive_cube_add()
roof = bpy.context.object; roof.name = "Roof"
rw, rd, rh = HW + 0.8, HD + 1.0, 2.2
verts = [(-rw/2, -rd/2, 0), (rw/2, -rd/2, 0), (rw/2, rd/2, 0), (-rw/2, rd/2, 0), (-rw/2, 0, rh), (rw/2, 0, rh)]
faces = [(0, 1, 5, 4), (3, 4, 5, 2), (0, 4, 3), (1, 2, 5), (0, 3, 2, 1)]
me = bpy.data.meshes.new("RoofMesh"); me.from_pydata(verts, [], faces); me.update()
roof.data = me; roof.location = (HX, HY, HH); roof.data.materials.append(roof_m)
roof.modifiers.new("s", 'SOLIDIFY').thickness = 0.18
box("Chimney", (2.4, HY + 0.6, HH + 1.8), (0.6, 0.6, 1.8), wall_m)
fy = HY - HD / 2
for x in (-2.6, -0.9, 0.9, 2.6):
    for z in (1.4, 3.5):
        box("WinFrame", (x, fy - 0.03, z), (1.05, 0.08, 1.2), trim_m)
        box("WinGlass", (x, fy - 0.07, z), (0.85, 0.04, 1.0), win_m)
# neighbour houses with lit windows
for (x, y, s) in [(-15, 14, 1.0), (15, 15, 1.0), (-28, 34, 1.2), (26, 38, 1.2), (0, 60, 1.3)]:
    box("NH", (x, y, 2.2 * s), (6.5 * s, 5 * s, 4.4 * s), wall_m)
    bpy.ops.mesh.primitive_cone_add(vertices=4, radius1=5.2 * s, depth=2.4 * s, location=(x, y, 5.6 * s), rotation=(0, 0, math.radians(45)))
    bpy.context.object.data.materials.append(roof_m)
    for dx in (-1.4, 1.4):
        box("NHW", (x + dx * s, y - 2.5 * s - 0.04, 2.4 * s), (0.9 * s, 0.06, 1.0 * s), win_m)
# white picket fence across the back of the yard (behind the landing zone)
fence_m = mat("Fence", (0.98, 0.98, 0.96), 0.6)
FY = 6.8
for i in range(-26, 27):
    x = i * 0.45
    if abs(x) > 11.8:
        continue
    box("Picket", (x, FY, 0.65), (0.22, 0.08, 1.3), fence_m)
for z in (0.4, 1.0):
    box("Rail", (0, FY + 0.06, z), (23.6, 0.06, 0.12), fence_m)
trunk_m = mat("Trunk", (0.42, 0.26, 0.14), 0.9)
fol = [mat("Fol1", (0.12, 0.45, 0.16), 0.85), mat("Fol2", (0.2, 0.55, 0.2), 0.85)]
def tree(x, y, h=3.4, r=1.4):
    cyl("Trunk", (x, y, h / 2), 0.18, h, trunk_m, verts=8)
    bpy.ops.mesh.primitive_cone_add(vertices=7, radius1=r, depth=h * 0.9, location=(x, y, h + 0.6))
    bpy.context.object.data.materials.append(random.choice(fol))
    bpy.ops.mesh.primitive_cone_add(vertices=7, radius1=r * 0.75, depth=h * 0.7, location=(x, y, h + 1.6))
    bpy.context.object.data.materials.append(random.choice(fol))
for (x, y) in [(-9.5, 8.5), (9.8, 8.0), (-11, 12.5), (11.5, 12), (-7, 20), (8, 24), (-18, 26), (19, 28)]:
    tree(x, y, random.uniform(3.0, 4.2), random.uniform(1.3, 1.8))
bush_m = fol[1]
for x in (-6.0, 6.0):
    sphere("Bush", (x, 6.0, 0.5), 0.8, bush_m, scale=(1.3, 0.9, 0.8), sub=1, smooth=False)

# ---------------- dog + dog house ----------------
dh_m = mat("DogHouse", (0.20, 0.45, 0.85), 0.7)
box("DogHouse", (-6.0, -1.4, 0.7), (1.6, 1.6, 1.4), dh_m)
bpy.ops.mesh.primitive_cone_add(vertices=4, radius1=1.35, depth=0.9, location=(-6.0, -1.4, 1.85), rotation=(0, 0, math.radians(45)))
bpy.context.object.data.materials.append(roof_m)
box("DogDoor", (-5.6, -2.21, 0.5), (0.6, 0.04, 0.75), mat("Dark", (0.05, 0.04, 0.05), 0.9))
fur = mat("Fur", (0.88, 0.62, 0.32), 0.8)
fur_d = mat("FurDark", (0.45, 0.28, 0.14), 0.8)
nose_m = mat("Nose", (0.05, 0.05, 0.05), 0.3)
dog = group("Dog", (-4.4, -2.4, 0), math.radians(20))
dparts = [
    sphere("DogBody", (-4.4, -2.1, 0.55), 0.5, fur, scale=(0.7, 1.15, 0.65), sub=2),
    cyl("Leg", (-4.65, -1.75, 0.2), 0.09, 0.4, fur), cyl("Leg", (-4.15, -1.75, 0.2), 0.09, 0.4, fur),
    cyl("Leg", (-4.65, -2.5, 0.2), 0.09, 0.4, fur), cyl("Leg", (-4.15, -2.5, 0.2), 0.09, 0.4, fur),
    tube("Tail", [(-4.4, -1.55, 0.7), (-4.4, -1.3, 1.0), (-4.4, -1.25, 1.2)], [0.07, 0.06, 0.03], fur_d),
]
head = group("DogHead", (-4.4, -2.75, 0.95))
hparts = [
    sphere("DogHead", (-4.4, -2.8, 1.05), 0.36, fur, sub=2),
    sphere("Snout", (-4.4, -3.12, 0.98), 0.18, fur, scale=(0.9, 1.2, 0.8), sub=2),
    sphere("Nose", (-4.4, -3.33, 1.02), 0.06, nose_m, sub=1),
    sphere("EyeL", (-4.55, -3.06, 1.17), 0.05, nose_m, sub=1), sphere("EyeR", (-4.25, -3.06, 1.17), 0.05, nose_m, sub=1),
    sphere("EarL", (-4.72, -2.75, 1.3), 0.14, fur_d, scale=(0.5, 0.8, 1.4), sub=1),
    sphere("EarR", (-4.08, -2.75, 1.3), 0.14, fur_d, scale=(0.5, 0.8, 1.4), sub=1),
]
attach(hparts, head)
attach(dparts + [head], dog)
# bark: head snaps up/down (tilts toward the sky)
for k, f in enumerate(range(S[1], S[2] + 10, 6)):
    head.rotation_euler = (math.radians(-28 if k % 2 == 0 else -10), 0, 0)
    head.keyframe_insert("rotation_euler", frame=f)
head.rotation_euler = (math.radians(-30), 0, 0); head.keyframe_insert("rotation_euler", frame=S[3])

# ---------------- "you" with a phone ----------------
def person(name, loc, rot_z, body_c, skin=(0.95, 0.75, 0.6), phone=True, hair=(0.2, 0.12, 0.06), helmet=None, visor=None):
    g = group(name, loc, rot_z)
    x, y, z = loc
    bm = mat(name + "B", body_c, 0.7)
    parts = [
        cyl("LegL", (x - 0.13, y, 0.38), 0.1, 0.76, mat(name + "L", (0.15, 0.18, 0.3), 0.8)),
        cyl("LegR", (x + 0.13, y, 0.38), 0.1, 0.76, mat(name + "L2", (0.15, 0.18, 0.3), 0.8)),
        cyl("Body", (x, y, 1.08), 0.28, 0.75, bm, r2=0.22),
        sphere("Head", (x, y, 1.68), 0.24, mat(name + "S", skin, 0.6), sub=2),
    ]
    if helmet:
        parts.append(sphere("Hood", (x, y + 0.03, 1.72), 0.29, mat(name + "H", helmet, 0.5), scale=(1, 1, 1.05), sub=2))
        parts.append(box("Visor", (x, y - 0.24, 1.7), (0.34, 0.06, 0.2), mat(name + "V", visor, 0.1, metal=0.5)))
    else:
        parts.append(sphere("Hair", (x, y + 0.05, 1.82), 0.22, mat(name + "Hr", hair, 0.8), scale=(1.05, 1.05, 0.6), sub=2))
    parts.append(tube("ArmL", [(x - 0.3, y, 1.35), (x - 0.34, y - 0.25, 1.05), (x - 0.12, y - 0.42, 1.25)], [0.07, 0.065, 0.06], bm))
    parts.append(tube("ArmR", [(x + 0.3, y, 1.35), (x + 0.34, y - 0.25, 1.05), (x + 0.12, y - 0.42, 1.25)], [0.07, 0.065, 0.06], bm))
    scr = None
    if phone:
        parts.append(box("Phone", (x, y - 0.48, 1.38), (0.2, 0.03, 0.36), mat("PhoneCase", (0.1, 0.1, 0.12), 0.4), rot=(math.radians(-15), 0, 0)))
        scr = glow_mat(name + "Scr", (0.6, 0.85, 1.0), 4.0)
        parts.append(box("Screen", (x, y - 0.455, 1.38), (0.17, 0.02, 0.31), scr, rot=(math.radians(-15), 0, 0)))
    attach(parts, g)
    return g, scr, parts

YX, YY = 4.4, -2.5
you, you_scr, you_parts = person("You", (YX, YY, 0), face(YX, YY), (0.95, 0.3, 0.35))
# signal bars on the phone (they vanish when the signal dies), facing the camera side of the phone
bar_m = glow_mat("Bars", (0.2, 1.0, 0.3), 5.0)
bars = []
for k in range(4):
    b = box(f"Bar{k}", (YX - 0.06 + 0.04 * k, YY - 0.435, 1.28 + 0.025 * k), (0.025, 0.02, 0.05 + 0.05 * k), bar_m)
    bars.append(b)
attach(bars, you)
for k, b in enumerate(bars):
    b.scale = (1, 1, 1); b.keyframe_insert("scale", frame=S[5] + 10 + 3 * (3 - k))
    b.scale = (1, 1, 0.001); b.keyframe_insert("scale", frame=S[5] + 13 + 3 * (3 - k))
emit_key(you_scr, S[5] + 18, 4.0); emit_key(you_scr, S[5] + 21, 0.4); emit_key(you_scr, S[5] + 24, 3.5)
emit_key(you_scr, S[5] + 27, 0.3); emit_key(you_scr, S[5] + 30, 4.0)
red_m = glow_mat("NoSig", (1.0, 0.1, 0.1), 6.0)
nosig = box("NoSignalX", (YX, YY - 0.43, 1.45), (0.12, 0.02, 0.03), red_m, rot=(0, math.radians(45), 0))
nosig2 = box("NoSignalX2", (YX, YY - 0.43, 1.45), (0.12, 0.02, 0.03), red_m, rot=(0, math.radians(-45), 0))
attach([nosig, nosig2], you)
for o in (nosig, nosig2):
    o.scale = (0.001,) * 3; o.keyframe_insert("scale", frame=S[5] + 22)
    o.scale = (1,) * 3; o.keyframe_insert("scale", frame=S[5] + 26)

# ---------------- crop circle (appears under the UFO) ----------------
UX, UY = 0.0, 1.0
flat_m = mat("Flattened", (0.62, 0.78, 0.30), 0.9)
ring_m = mat("Ring", (0.10, 0.36, 0.10), 0.9)
circ = cyl("CropCircle", (UX, UY, 0.012), 4.9, 0.02, flat_m, verts=64)
rings = [cyl(f"CropRing{k}", (UX, UY, 0.025), r, 0.02, ring_m, verts=64) for k, r in enumerate((4.3, 3.2))]
inner = [cyl(f"CropIn{k}", (UX, UY, 0.035), r, 0.02, flat_m, verts=64) for k, r in enumerate((4.0, 2.9))]
dots = []
for k in range(8):
    a = k * math.pi / 4
    dots.append(cyl("CropDot", (UX + 5.5 * math.cos(a), UY + 5.5 * math.sin(a) * 0.8, 0.02), 0.32, 0.02, flat_m, verts=24))
for i, o in enumerate([circ] + rings + inner):
    o.scale = (0.001, 0.001, 1); o.keyframe_insert("scale", frame=S[4] + 2 + 3 * i)
    o.scale = (1, 1, 1); o.keyframe_insert("scale", frame=S[4] + 16 + 3 * i)
for i, o in enumerate(dots):
    pop(o, S[4] + 18 + 2 * i, 5)

# ---------------- the UFO ----------------
hull_m = mat("Hull", (0.78, 0.82, 0.88), 0.25, metal=0.8)
hull2_m = mat("Hull2", (0.45, 0.50, 0.60), 0.35, metal=0.7)
dome_m = mat("Dome", (0.35, 0.95, 0.85), 0.1, emit=(0.2, 1.0, 0.8), emit_strength=2.5)
lamp_cols = [(1.0, 0.25, 0.7), (0.3, 1.0, 0.9), (1.0, 0.85, 0.2)]
lamp_ms = [glow_mat(f"Lamp{k}", c, 10.0) for k, c in enumerate(lamp_cols)]
ufo = group("UFO", (UX, UY, 0))
spin = group("UFOSpin", (UX, UY, 0))
up = []
UR = 4.3
disc = sphere("Disc", (UX, UY, 0), UR, hull_m, scale=(1, 1, 0.16), sub=4)
rim = cyl("Rim", (UX, UY, 0), UR * 1.02, 0.18, hull2_m, verts=48)
under = sphere("Under", (UX, UY, -0.3), UR * 0.4, hull2_m, scale=(1, 1, 0.28), sub=3)
dome = sphere("Dome", (UX, UY, 0.45), UR * 0.38, dome_m, scale=(1, 1, 0.75), sub=3)
up += [disc, rim, under, dome]
lamps = []
for k in range(18):
    a = 2 * math.pi * k / 18
    l = sphere("Lamp", (UX + UR * 0.99 * math.cos(a), UY + UR * 0.99 * math.sin(a), 0.0), 0.2, lamp_ms[k % 3], sub=1)
    lamps.append(l)
attach(lamps + [disc, rim], spin)
# legs (static relative to ufo)
leg_m = hull2_m
legs = []
for k in range(3):
    a = math.radians(90 + 120 * k + 60)
    lx, ly = UX + 2.6 * math.cos(a), UY + 2.6 * math.sin(a)
    legs.append(tube("UfoLeg", [(UX + 1.8 * math.cos(a), UY + 1.8 * math.sin(a), -0.2), (lx, ly, -1.05)], [0.12, 0.08], leg_m))
    legs.append(cyl("Foot", (lx, ly, -1.12), 0.32, 0.1, leg_m, verts=16))
# hatch + ramp on the camera side (front, -y)
hatch_light = glow_mat("HatchLight", (0.75, 1.0, 0.95), 0.0)
hatch = box("Hatch", (UX, UY - 2.0, -0.62), (1.4, 1.0, 0.04), hatch_light)
ramp_piv = group("RampPivot", (UX, UY - 2.5, -0.63))
ramp_m = mat("Ramp", (0.62, 0.66, 0.74), 0.3, metal=0.6)
rmp = box("Ramp", (UX, UY - 2.5 + 1.2, -0.66), (1.3, 2.4, 0.06), ramp_m)   # closed: flat door under the hull
rl = glow_mat("RampLights", (0.3, 1.0, 0.9), 6.0)
rstrips = [box("RampStrip", (UX + s * 0.58, UY - 2.5 + 1.2, -0.62), (0.06, 2.3, 0.03), rl) for s in (-1, 1)]
attach([rmp] + rstrips, ramp_piv)
attach([spin, under, dome, hatch, ramp_piv] + legs, ufo)

# glow light under the ship + inner hatch light
bpy.ops.object.light_add(type='POINT', location=(UX, UY, -0.8))
ufo_glow = bpy.context.object; ufo_glow.data.color = (0.3, 1.0, 0.85); ufo_glow.data.shadow_soft_size = 1.5
bpy.ops.object.light_add(type='POINT', location=(UX, UY - 2.0, -0.95))
hatch_lamp = bpy.context.object; hatch_lamp.data.color = (0.8, 1.0, 0.95); hatch_lamp.data.shadow_soft_size = 0.4
attach([ufo_glow, hatch_lamp], ufo)
# tractor beam (transparent emissive cone, only during the descent)
beam_m = glow_mat("Beam", (0.4, 1.0, 0.85), 2.2, alpha=0.25)
beam = cyl("Beam", (UX, UY, -6.0), 3.6, 11.4, beam_m, verts=40, r2=1.6)
attach([beam], ufo)

LAND_Z = 1.2
# path: high in the sky behind the house -> over the fence -> hover just above the lawn
ufo_keys = [(0, (UX, UY + 16, 15)), (S[1], (UX, UY + 15, 13.5)), (S[2], (UX, UY + 11, 11)),
            (S[2] + 22, (UX, UY + 2.5, 5.0)), (S[3] + 6, (UX, UY, LAND_Z + 0.5)), (S[4], (UX, UY, LAND_Z))]
for f, p in ufo_keys:
    ufo.location = p; ufo.keyframe_insert("location", frame=f)
ufo.rotation_euler = (math.radians(10), 0, 0); ufo.keyframe_insert("rotation_euler", frame=S[2])
ufo.rotation_euler = (math.radians(-6), 0, 0); ufo.keyframe_insert("rotation_euler", frame=S[2] + 20)
ufo.rotation_euler = (0, 0, 0); ufo.keyframe_insert("rotation_euler", frame=S[3] + 10)
# gentle hover bob once landed
# spin the outer ring all the time
spin.rotation_euler = (0, 0, 0); spin.keyframe_insert("rotation_euler", frame=0)
spin.rotation_euler = (0, 0, math.radians(360 * FRAMES / 96)); spin.keyframe_insert("rotation_euler", frame=FRAMES)
for fc in spin.animation_data.action.fcurves if hasattr(spin.animation_data.action, "fcurves") else []:
    for kp in fc.keyframe_points:
        kp.interpolation = 'LINEAR'
# beam on during descent only
beam.scale = (1, 1, 1); beam.keyframe_insert("scale", frame=S[2] - 2)
beam.keyframe_insert("scale", frame=S[3] + 12)
beam.scale = (0.001, 0.001, 1); beam.keyframe_insert("scale", frame=S[3] + 20)
beam.scale = (0.001, 0.001, 1); beam.keyframe_insert("scale", frame=0)
beam.scale = (0.001, 0.001, 1); beam.keyframe_insert("scale", frame=S[2] - 6)
# glow + lamp pulses
ufo_glow.data.shadow_soft_size = 3.0
for f, e in [(0, 900), (S[3], 1800), (S[4], 2600), (S[5], 3200)]:
    ufo_glow.data.energy = e; ufo_glow.data.keyframe_insert("energy", frame=f)
# lights flicker (line 5): house windows, ufo lamps
for k, f in enumerate(range(S[5], S[6], 3)):
    v = [6.0, 0.2, 5.0, 0.0, 6.0, 0.4, 0.0, 6.0][k % 8]
    emit_key(win_m, f, v)
emit_key(win_m, S[6] + 2, 6.0)
for k, m in enumerate(lamp_ms):
    for f in range(0, FRAMES, 12):
        emit_key(m, f + 4 * k, 14.0 if (f // 12) % 2 == 0 else 4.0)
# ramp lowers (line 6), hatch lights up
ramp_piv.rotation_euler = (0, 0, 0); ramp_piv.keyframe_insert("rotation_euler", frame=S[6] + 2)
ramp_piv.rotation_euler = (math.radians(-125), 0, 0); ramp_piv.keyframe_insert("rotation_euler", frame=S[6] + 12)
ramp_piv.rotation_euler = (math.radians(-166), 0, 0); ramp_piv.keyframe_insert("rotation_euler", frame=S[6] + 30)
emit_key(hatch_light, S[6] + 4, 0.0); emit_key(hatch_light, S[6] + 16, 9.0)
for f, e in [(0, 0), (S[6] + 4, 0), (S[6] + 16, 500), (S[7] + 8, 900)]:
    hatch_lamp.data.energy = e; hatch_lamp.data.keyframe_insert("energy", frame=f)

# ---------------- neighbours filming (line 8) ----------------
shirt_cols = [(0.25, 0.55, 0.95), (0.98, 0.7, 0.2), (0.6, 0.35, 0.9), (0.3, 0.8, 0.5), (0.95, 0.45, 0.25), (0.2, 0.75, 0.85)]
neigh_spots = [(-8.2, 1.5), (-8.8, -2.4), (-7.4, 4.6), (8.0, 4.5), (9.0, 1.0), (7.6, -1.3)]
for k, (x, y) in enumerate(neigh_spots):
    rz = face(x, y)
    g, scr, _ = person(f"N{k}", (x, y, 0), rz, shirt_cols[k], hair=[(0.1, 0.07, 0.05), (0.85, 0.6, 0.3), (0.4, 0.2, 0.1)][k % 3])
    pop(g, S[8] + 2 + 3 * k, 6)
    # phone flashes
    for f in range(S[8] + 10 + 2 * k, S[9] + 30, 9):
        emit_key(scr, f, 14.0); emit_key(scr, f + 2, 4.0)

# ---------------- army: trucks, barricades, flashing lights (line 9) ----------------
army_m = mat("Army", (0.35, 0.45, 0.22), 0.8)
army_d = mat("ArmyDark", (0.24, 0.30, 0.16), 0.8)
tyre_m = mat("Tyre", (0.06, 0.06, 0.06), 0.9)
def truck(name, x, y, rz):
    g = group(name, (x, y, 0), rz)
    parts = [box("Cargo", (x, y + 0.7, 1.35), (2.0, 3.0, 1.9), army_d, bevel=0.06),
             box("Cab", (x, y - 1.35, 1.05), (2.0, 1.3, 1.5), army_m, bevel=0.06),
             box("WS", (x, y - 2.01, 1.35), (1.6, 0.04, 0.55), mat("TruckGlass", (0.2, 0.35, 0.5), 0.1)),
             box("Bed", (x, y, 0.45), (2.1, 4.6, 0.3), army_d)]
    for dx in (-1.0, 1.0):
        for dy in (-1.4, 0.2, 1.4):
            parts.append(cyl("Wheel", (x + dx, y + dy, 0.42), 0.42, 0.32, tyre_m, rot=(0, math.radians(90), 0), verts=16))
    attach(parts, g)
    return g
tk1 = truck("Truck1", -10.6, 4.2, math.radians(-8))
tk2 = truck("Truck2", 10.6, 4.2, math.radians(8))
# trucks drive in
for tk, sx in ((tk1, -1), (tk2, 1)):
    tk.location = (sx * 10.6, 10.0, 0); tk.keyframe_insert("location", frame=S[9])
    tk.location = (sx * 10.6, 4.2, 0); tk.keyframe_insert("location", frame=S[9] + 12)
    tk.scale = (0.001,) * 3; tk.keyframe_insert("scale", frame=S[9] - 1)
    tk.scale = (1,) * 3; tk.keyframe_insert("scale", frame=S[9] + 1)
stripe_r = mat("BarRed", (0.95, 0.15, 0.12), 0.6)
stripe_w = mat("BarWhite", (0.97, 0.97, 0.97), 0.6)
tape_m = mat("Tape", (1.0, 0.85, 0.05), 0.5)
siren_r = glow_mat("SirenR", (1.0, 0.1, 0.1), 0.0)
siren_b = glow_mat("SirenB", (0.1, 0.35, 1.0), 0.0)
for i, x in enumerate((-6.6, -3.0, 3.0, 6.6)):
    g = group(f"Barricade{i}", (x, -3.55, 0))
    parts = [box("BLegL", (x - 0.7, -3.55, 0.4), (0.1, 0.4, 0.8), stripe_w), box("BLegR", (x + 0.7, -3.55, 0.4), (0.1, 0.4, 0.8), stripe_w)]
    for k in range(5):
        parts.append(box("BStripe", (x - 0.64 + 0.32 * k, -3.6, 0.75), (0.32, 0.08, 0.26), stripe_r if k % 2 == 0 else stripe_w))
    parts.append(sphere("Siren", (x, -3.6, 1.05), 0.14, siren_r if i % 2 == 0 else siren_b, sub=1))
    attach(parts, g)
    pop(g, S[9] + 4 + 3 * i, 6)
tape = box("Tape", (0, -3.62, 0.55), (15.0, 0.03, 0.12), tape_m)
tape.scale = (0.001, 1, 1); tape.keyframe_insert("scale", frame=S[9] + 10)
tape.scale = (1, 1, 1); tape.keyframe_insert("scale", frame=S[9] + 22)
for f in range(S[9], FRAMES, 6):
    on = (f // 6) % 2 == 0
    emit_key(siren_r, f, 12.0 if on else 1.0); emit_key(siren_b, f, 1.0 if on else 12.0)
for f in range(0, S[9]):
    pass
emit_key(siren_r, S[9] - 1, 0.0); emit_key(siren_b, S[9] - 1, 0.0)
# red / blue light washes
bpy.ops.object.light_add(type='POINT', location=(-6, -5, 2.5)); lr = bpy.context.object; lr.data.color = (1, 0.1, 0.1)
bpy.ops.object.light_add(type='POINT', location=(6, -5, 2.5)); lb = bpy.context.object; lb.data.color = (0.15, 0.35, 1)
for f in range(0, FRAMES, 6):
    on = (f // 6) % 2 == 0
    act = f >= S[9]
    lr.data.energy = (900 if on else 80) if act else 0; lr.data.keyframe_insert("energy", frame=f)
    lb.data.energy = (80 if on else 900) if act else 0; lb.data.keyframe_insert("energy", frame=f)
soldier_spots = [(-5.0, -3.0, 0.3), (-1.6, -3.2, 0.0), (1.6, -3.2, 0.0), (5.6, -3.0, -0.3)]
soldiers = []
for k, (x, y, rz) in enumerate(soldier_spots):
    g, _, _ = person(f"Sol{k}", (x, y, 0), rz, (0.33, 0.43, 0.2), phone=False, helmet=(0.28, 0.36, 0.17), visor=(0.95, 0.75, 0.6))
    pop(g, S[9] + 6 + 3 * k, 6, S[10] + 2)
    soldiers.append(g)

# ---------------- scientists in hazmat suits (line 10) ----------------
haz = (1.0, 0.82, 0.1)
scan_m = glow_mat("Scan", (0.3, 1.0, 0.3), 8.0)
sci_spots = [(-1.9, -2.6, math.radians(-20)), (1.9, -2.6, math.radians(20))]
for k, (x, y, rz) in enumerate(sci_spots):
    g, _, parts = person(f"Sci{k}", (x, y, 0), rz, haz, phone=False, helmet=haz, visor=(0.2, 0.5, 0.7))
    wand = cyl("Wand", (x, y - 0.65, 0.55), 0.04, 1.1, mat("WandM", (0.2, 0.2, 0.22), 0.4), rot=(math.radians(-50), 0, 0), verts=8)
    det = box("Detector", (x, y - 0.42, 1.05), (0.3, 0.16, 0.22), mat("DetM", (0.15, 0.15, 0.17), 0.5))
    tip = sphere("ScanTip", (x, y - 1.05, 0.12), 0.11, scan_m, sub=1)
    attach([wand, det, tip], g)
    pop(g, S[10] + 2 + 4 * k, 6)
    # sweep the wand left/right
    for j, f in enumerate(range(S[10] + 8, S[11] + 20, 8)):
        g.rotation_euler = (0, 0, rz + math.radians(18 if j % 2 else -18)); g.keyframe_insert("rotation_euler", frame=f)
for f in range(S[10], S[11] + 24, 4):
    emit_key(scan_m, f, 14.0 if (f // 4) % 2 == 0 else 3.0)
# radiation sign on a little stand
sign_m = mat("SignY", (1.0, 0.85, 0.1), 0.5)
blk = mat("SignK", (0.05, 0.05, 0.05), 0.5)
SGX, SGY = -3.0, -1.8
sg = group("Sign", (SGX, SGY, 0))
sp = [cyl("SignPost", (SGX, SGY, 0.45), 0.04, 0.9, blk, verts=8),
      cyl("SignPlate", (SGX, SGY - 0.06, 1.05), 0.38, 0.04, sign_m, rot=(math.radians(90), 0, 0), verts=3),
      sphere("SignDot", (SGX, SGY - 0.1, 1.0), 0.07, blk, sub=1)]
attach(sp, sg)
pop(sg, S[10] + 12, 6)

# ---------------- the nearest star + light path (lines 11-12) ----------------
STAR = Vector((10, 95, 112))
bigstar_m = glow_mat("BigStar", (1.0, 0.85, 0.45), 18.0)
bigstar = sphere("BigStar", STAR, 3.2, bigstar_m, sub=2)
halo_m = glow_mat("Halo", (1.0, 0.75, 0.35), 3.0, alpha=0.18)
halo = sphere("Halo", STAR, 7.5, halo_m, sub=2)
pop(bigstar, S[11] + 6, 8); pop(halo, S[11] + 10, 8)
for f in range(S[11] + 20, S[13], 10):
    halo.scale = (1.0,) * 3 if (f // 10) % 2 else (1.25,) * 3; halo.keyframe_insert("scale", frame=f)
dot_m = glow_mat("PathDot", (1.0, 0.7, 0.15), 14.0)
END = Vector((UX, UY, LAND_Z + 1.5))
NDOT = 26
for i in range(NDOT):
    t = i / (NDOT - 1)
    p = STAR.lerp(END, t)
    p.z += math.sin(t * math.pi) * 6
    d = sphere("Dot", p, 1.3 * (1 - 0.7 * t) + 0.18, dot_m, sub=1)
    pop(d, S[12] + int(t * 30), 4, S[14] + 2)

# ---------------- news helicopters + vans (line 14) ----------------
heli_cols = [(0.95, 0.3, 0.3), (0.2, 0.6, 1.0)]
beam2_m = glow_mat("SpotCone", (1.0, 1.0, 0.85), 1.2, alpha=0.12)
def heli(name, col):
    g = group(name, (0, 0, 0))
    bm = mat(name + "Body", col, 0.4)
    parts = [sphere("HBody", (0, 0, 0), 0.9, bm, scale=(0.8, 1.3, 0.75), sub=2),
             sphere("HGlass", (0, -0.75, 0.15), 0.55, mat(name + "G", (0.2, 0.4, 0.6), 0.1), scale=(0.9, 0.7, 0.7), sub=2),
             tube("Tail", [(0, 0.9, 0.1), (0, 2.6, 0.45)], [0.22, 0.09], bm),
             box("Fin", (0, 2.6, 0.7), (0.08, 0.4, 0.6), bm),
             box("SkidL", (-0.55, 0, -0.85), (0.08, 1.8, 0.08), tyre_m), box("SkidR", (0.55, 0, -0.85), (0.08, 1.8, 0.08), tyre_m),
             cyl("Mast", (0, 0, 0.8), 0.06, 0.4, tyre_m, verts=8)]
    rotor = group(name + "Rotor", (0, 0, 1.0))
    blades = [box("Blade", (0, 0, 1.0), (4.4, 0.18, 0.04), tyre_m), box("Blade", (0, 0, 1.0), (0.18, 4.4, 0.04), tyre_m)]
    attach(blades, rotor)
    cone = cyl("SpotCone", (0, -0.4, -5.6), 2.2, 9.6, beam2_m, verts=24, r2=0.25)
    attach(parts + [rotor, cone], g)
    rotor.rotation_euler = (0, 0, 0); rotor.keyframe_insert("rotation_euler", frame=0)
    rotor.rotation_euler = (0, 0, math.radians(360 * 60)); rotor.keyframe_insert("rotation_euler", frame=FRAMES)
    return g, rotor
for k, col in enumerate(heli_cols):
    h, rot = heli(f"Heli{k}", col)
    sx = -1 if k == 0 else 1
    h.location = (sx * 30, 10, 16); h.keyframe_insert("location", frame=S[14] - 4)
    h.location = (sx * 7.5, 2.5 + 2 * k, 10.5); h.keyframe_insert("location", frame=S[14] + 16)
    h.location = (sx * 6.0, 0.5 + 2 * k, 10.0); h.keyframe_insert("location", frame=FRAMES)
    h.rotation_euler = (math.radians(12), math.radians(-14 * sx), math.radians(-60 * sx)); h.keyframe_insert("rotation_euler", frame=S[14])
    h.rotation_euler = (math.radians(8), math.radians(-14 * sx), math.radians(-35 * sx)); h.keyframe_insert("rotation_euler", frame=FRAMES)
    h.scale = (0.001,) * 3; h.keyframe_insert("scale", frame=S[14] - 5)
    h.scale = (1,) * 3; h.keyframe_insert("scale", frame=S[14] - 4)
    bpy.ops.object.light_add(type='SPOT', location=(sx * 7.0, 2.0, 9.6))
    spot = bpy.context.object; spot.data.spot_size = math.radians(30); spot.data.color = (1, 1, 0.9)
    spot.rotation_euler = (0, math.radians(30 * sx), 0)
    for f, e in [(0, 0), (S[14] + 6, 0), (S[14] + 16, 9000)]:
        spot.data.energy = e; spot.data.keyframe_insert("energy", frame=f)
van_m = mat("Van", (0.97, 0.97, 0.97), 0.5)
dish_m = mat("Dish", (0.85, 0.85, 0.88), 0.4, metal=0.4)
for k, (x, y, rz) in enumerate([(-10.6, -2.0, math.radians(90)), (10.6, -1.8, math.radians(-90))]):
    g = group(f"NewsVan{k}", (x, y, 0), 0)
    parts = [box("VanBody", (x, y, 1.0), (1.8, 3.2, 1.6), van_m, bevel=0.1),
             box("VanStripe", (x, y, 1.0), (1.84, 3.24, 0.3), mat(f"VS{k}", heli_cols[k], 0.5)),
             cyl("Mast", (x, y, 2.4), 0.06, 1.4, dish_m, verts=8),
             sphere("Dish", (x, y, 3.2), 0.6, dish_m, scale=(1, 0.3, 1), sub=2)]
    for dy in (-1.1, 1.1):
        for dx in (-0.9, 0.9):
            parts.append(cyl("VW", (x + dx, y + dy, 0.3), 0.3, 0.2, tyre_m, rot=(0, math.radians(90), 0), verts=12))
    attach(parts, g)
    pop(g, S[14] + 4 + 4 * k, 6)

# ---------------- camera ----------------
bpy.ops.object.camera_add()
cam = bpy.context.object
sc.camera = cam
cam.data.lens = 26
cam.data.sensor_fit = 'VERTICAL'
cam.data.sensor_height = 36
cam.data.clip_end = 1000
target = bpy.data.objects.new("Target", None); sc.collection.objects.link(target)
tr = cam.constraints.new('TRACK_TO'); tr.target = target
tr.track_axis = 'TRACK_NEGATIVE_Z'; tr.up_axis = 'UP_Y'

def U(z=0.0): return (UX, UY, LAND_Z + z)
cam_keys = [  # frame, camera, target  (a new move on every line, sub-beats in between)
    (0,           (5.0, -19, 4.5),   (0, 8, 8.0)),
    (S[1] - 6,    (2.0, -17, 3.5),   (0, 6, 7.0)),
    (S[1] + 8,    (-6.8, -7.6, 1.6),  (-4.5, -2.4, 1.0)),      # dog close-up
    (S[2] - 4,    (-5.6, -8.2, 1.2),  (-4.2, -2.0, 1.6)),
    (S[2] + 6,    (1.5, -15.5, 1.4),  (0, 5, 6.0)),            # UFO sinks over the fence
    (S[3] - 2,    (-1.0, -15.0, 2.0), (0, 2, 3.0)),
    (S[3] + 10,   (-10, -15, 7.5),    (0, 4, 2.4)),            # size vs house
    (S[4] - 2,    (8, -15, 6.5),      (0, 4, 2.4)),
    (S[4] + 8,    (0.5, -5.5, 15.5),  (0, 0.4, 0)),            # top-down crop circle
    (S[5] - 4,    (-2.0, -7.0, 14.0), (0, 0.4, 0)),
    (S[5] + 8,    (4.85, -2.05, 1.95), (4.03, -2.2, 1.33)),       # phone close-up (over the shoulder)
    (S[5] + 26,   (5.0, -2.35, 2.15),  (4.03, -2.2, 1.33)),
    (S[6] - 2,    (3.0, -9.0, 4.0),   (0, 4.0, 3.0)),          # flicker: house + ufo
    (S[6] + 10,   (0.0, -10.5, 1.0),  (0, -1.0, 1.0)),         # ramp lowers
    (S[7] - 2,    (0.6, -9.0, 0.9),   (0, -1.0, 1.0)),
    (S[7] + 18,   (0.0, -5.6, 0.75),  (0, -1.2, 1.1)),         # push into the empty doorway
    (S[8] + 6,    (-14, -11, 3.5),    (-6, 2.0, 1.2)),         # neighbours filming
    (S[9] - 4,    (12, -11, 3.5),     (6, 2.0, 1.2)),
    (S[9] + 14,   (0, -18.5, 5.0),    (0, 1.0, 1.5)),          # army seals the block
    (S[10] - 4,   (-4, -17, 6.0),     (0, 1.0, 1.5)),
    (S[10] + 8,   (-3.6, -7.4, 1.4),  (-1.9, -3.4, 0.6)),      # scientists scanning
    (S[11] - 6,   (3.6, -7.4, 1.4),   (1.9, -3.4, 0.6)),
    (S[11] + 14,  (1.0, -12, 1.5),    (9, 95, 62)),          # tilt up to the nearest star
    (S[12] - 4,   (2.0, -11, 2.0),    (9, 95, 62)),
    (S[12] + 18,  (0.0, -14, 3.0),    (5, 40, 50)),            # follow the light down
    (S[13] - 2,   (0.0, -15, 3.0),    (0, 1.0, 2.5)),
    (S[13] + 14,  (9.0, -6.0, 4.5),   U(0.3)),                 # orbit the ship
    (S[14] - 2,   (7.5, 5.5, 6.0),    U(0.3)),
    (S[14] + 18,  (12, -26, 15),      (0, 1, 2.0)),            # pull way out: helicopters + vans
    (S[15] - 4,   (-8, -27, 17),      (0, 1, 2.0)),
    (S[15] + 18,  (0.0, -9.5, 1.6),   (0, -1.0, 1.0)),         # ending: walk-up-the-ramp POV
    (FRAMES - 1,  (0.0, -6.8, 1.0),   (0, -0.8, 1.1)),
]
for f, cl, tl in cam_keys:
    cam.location = cl; cam.keyframe_insert("location", frame=f)
    target.location = tl; target.keyframe_insert("location", frame=f)

os.makedirs(HERE, exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=f"{HERE}/scene.blend")
print("SCENE OK", FRAMES, S)
