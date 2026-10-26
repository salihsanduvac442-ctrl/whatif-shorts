import bpy, math, random, sys
from mathutils import Vector

random.seed(7)
FPS = 24
FRAMES = 960
args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
RES_SCALE = int(args[0]) if args else 50   # percent of 1080x1920
SAMPLES = int(args[1]) if len(args) > 1 else 24

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.engine = 'CYCLES'
sc.cycles.device = 'CPU'
sc.cycles.samples = SAMPLES
sc.cycles.use_denoising = True
sc.cycles.max_bounces = 4
sc.cycles.diffuse_bounces = 2
sc.cycles.glossy_bounces = 1
sc.cycles.transmission_bounces = 4
sc.render.use_persistent_data = True
sc.render.resolution_x = 1080
sc.render.resolution_y = 1920
sc.render.resolution_percentage = RES_SCALE
sc.render.fps = FPS
sc.frame_start = 0
sc.frame_end = FRAMES - 1
sc.render.image_settings.file_format = 'PNG'
sc.view_settings.view_transform = 'Standard'
sc.view_settings.exposure = -0.35

# ---------------- helpers ----------------
def mat(name, color, rough=0.7, emit=None, emit_strength=0.0, alpha=None, metal=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if emit:
        b.inputs["Emission Color"].default_value = (*emit, 1)
        b.inputs["Emission Strength"].default_value = emit_strength
    if alpha is not None:
        b.inputs["Transmission Weight"].default_value = alpha
        b.inputs["IOR"].default_value = 1.33
    return m

def box(name, loc, size, material, bevel=0.0):
    bpy.ops.mesh.primitive_cube_add(location=loc)
    o = bpy.context.object
    o.name = name
    o.scale = (size[0] / 2, size[1] / 2, size[2] / 2)
    bpy.ops.object.transform_apply(scale=True)
    o.data.materials.append(material)
    if bevel:
        mod = o.modifiers.new("bev", 'BEVEL')
        mod.width = bevel
        mod.segments = 2
    return o

def cyl(name, loc, r, depth, material, rot=(0, 0, 0), verts=24):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=depth, location=loc, rotation=rot)
    o = bpy.context.object
    o.name = name
    o.data.materials.append(material)
    bpy.ops.object.shade_smooth()
    return o

def sphere(name, loc, r, material, scale=(1, 1, 1), sub=2):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=sub, radius=r, location=loc)
    o = bpy.context.object
    o.name = name
    o.scale = scale
    o.data.materials.append(material)
    bpy.ops.object.shade_smooth()
    return o

# ---------------- world ----------------
w = bpy.data.worlds.new("W")
sc.world = w
w.use_nodes = True
nt = w.node_tree
bg = nt.nodes["Background"]
tc = nt.nodes.new("ShaderNodeTexCoord")
sep = nt.nodes.new("ShaderNodeSeparateXYZ")
ramp = nt.nodes.new("ShaderNodeValToRGB")
ramp.color_ramp.elements[0].position = 0.0
ramp.color_ramp.elements[0].color = (0.82, 0.9, 1.0, 1)
ramp.color_ramp.elements[1].position = 0.45
ramp.color_ramp.elements[1].color = (0.32, 0.58, 0.95, 1)
nt.links.new(tc.outputs["Generated"], sep.inputs[0])
nt.links.new(sep.outputs["Z"], ramp.inputs[0])
nt.links.new(ramp.outputs["Color"], bg.inputs["Color"])
bg.inputs["Strength"].default_value = 0.9

bpy.ops.object.light_add(type='SUN', rotation=(math.radians(52), 0, math.radians(-28)))
sun = bpy.context.object
sun.data.energy = 3.0
sun.data.angle = math.radians(4)
sun.data.color = (1.0, 0.96, 0.9)

# ---------------- ground block with layered soil shader ----------------
GROUND_BOTTOM = -62.0
FRONT_Y = -4.0
ground_m = bpy.data.materials.new("Ground")
ground_m.use_nodes = True
gn = ground_m.node_tree
N = gn.nodes
L = gn.links
bsdf = N["Principled BSDF"]
bsdf.inputs["Roughness"].default_value = 0.95
geo = N.new("ShaderNodeNewGeometry")
sepz = N.new("ShaderNodeSeparateXYZ")
L.new(geo.outputs["Position"], sepz.inputs[0])
# wobble the layer boundaries a little
noiseB = N.new("ShaderNodeTexNoise")
noiseB.inputs["Scale"].default_value = 0.35
L.new(geo.outputs["Position"], noiseB.inputs["Vector"])
wob = N.new("ShaderNodeMath"); wob.operation = 'MULTIPLY_ADD'
L.new(noiseB.outputs["Fac"], wob.inputs[0]); wob.inputs[1].default_value = 1.2; wob.inputs[2].default_value = -0.6
zsum = N.new("ShaderNodeMath"); zsum.operation = 'ADD'
L.new(sepz.outputs["Z"], zsum.inputs[0]); L.new(wob.outputs[0], zsum.inputs[1])
mapr = N.new("ShaderNodeMapRange")
mapr.inputs["From Min"].default_value = GROUND_BOTTOM
mapr.inputs["From Max"].default_value = 0.0
L.new(zsum.outputs[0], mapr.inputs["Value"])
# plain z (no wobble) for the grass cap
mapg = N.new("ShaderNodeMapRange")
mapg.inputs["From Min"].default_value = -0.22
mapg.inputs["From Max"].default_value = -0.12
L.new(sepz.outputs["Z"], mapg.inputs["Value"])

layers = [  # (top z, color)
    (GROUND_BOTTOM, (1.0, 0.45, 0.05)),   # magma
    (-53.0, (0.30, 0.08, 0.04)),          # red-hot rock
    (-42.0, (0.11, 0.10, 0.11)),          # dark basalt
    (-28.0, (0.22, 0.22, 0.24)),          # grey granite
    (-16.0, (0.46, 0.34, 0.20)),          # sandstone
    (-7.0, (0.48, 0.25, 0.12)),           # clay
    (-2.6, (0.33, 0.19, 0.09)),           # topsoil
]
cr = N.new("ShaderNodeValToRGB")
cr.color_ramp.interpolation = 'CONSTANT'
el = cr.color_ramp.elements
el[0].position = 0.0; el[0].color = (*layers[0][1], 1)
el[1].position = (layers[1][0] - GROUND_BOTTOM) / -GROUND_BOTTOM; el[1].color = (*layers[1][1], 1)
for top, col in layers[2:]:
    e = el.new((top - GROUND_BOTTOM) / -GROUND_BOTTOM)
    e.color = (*col, 1)
L.new(mapr.outputs["Result"], cr.inputs["Fac"])

# emission ramp (hot layers glow)
er = N.new("ShaderNodeValToRGB")
er.color_ramp.interpolation = 'LINEAR'
_e = er.color_ramp.elements
_e[0].position = 0.0; _e[0].color = (1, 1, 1, 1)
_e[1].position = (-38.0 - GROUND_BOTTOM) / -GROUND_BOTTOM; _e[1].color = (0, 0, 0, 1)
_e2 = _e.new((-53.0 - GROUND_BOTTOM) / -GROUND_BOTTOM + 0.005); _e2.color = (0.12, 0.12, 0.12, 1)
L.new(mapr.outputs["Result"], er.inputs["Fac"])

# cracks + grain
vor = N.new("ShaderNodeTexVoronoi")
vor.feature = 'DISTANCE_TO_EDGE'
vor.inputs["Scale"].default_value = 1.6
vmap = N.new("ShaderNodeMapping"); vmap.inputs["Scale"].default_value = (1.0, 1.0, 1.6)
L.new(geo.outputs["Position"], vmap.inputs["Vector"]); L.new(vmap.outputs[0], vor.inputs["Vector"])
crk = N.new("ShaderNodeMapRange")
crk.inputs["From Min"].default_value = 0.0; crk.inputs["From Max"].default_value = 0.06
crk.inputs["To Min"].default_value = 0.55; crk.inputs["To Max"].default_value = 1.0
L.new(vor.outputs["Distance"], crk.inputs["Value"])
grain = N.new("ShaderNodeTexNoise"); grain.inputs["Scale"].default_value = 9.0; grain.inputs["Detail"].default_value = 8
L.new(geo.outputs["Position"], grain.inputs["Vector"])
gr = N.new("ShaderNodeMapRange")
gr.inputs["To Min"].default_value = 0.78; gr.inputs["To Max"].default_value = 1.12
L.new(grain.outputs["Fac"], gr.inputs["Value"])
m1 = N.new("ShaderNodeMix"); m1.data_type = 'RGBA'; m1.blend_type = 'MULTIPLY'; m1.inputs["Factor"].default_value = 1.0
L.new(cr.outputs["Color"], m1.inputs[6]); L.new(crk.outputs["Result"], m1.inputs[7])
m2 = N.new("ShaderNodeMix"); m2.data_type = 'RGBA'; m2.blend_type = 'MULTIPLY'; m2.inputs["Factor"].default_value = 1.0
L.new(m1.outputs[2], m2.inputs[6]); L.new(gr.outputs["Result"], m2.inputs[7])
sepy = N.new("ShaderNodeSeparateXYZ"); L.new(geo.outputs["Position"], sepy.inputs[0])
dk = N.new("ShaderNodeMapRange")
dk.inputs["From Min"].default_value = FRONT_Y + 0.02; dk.inputs["From Max"].default_value = FRONT_Y + 1.1
dk.inputs["To Min"].default_value = 1.0; dk.inputs["To Max"].default_value = 0.42
L.new(sepy.outputs["Y"], dk.inputs["Value"])
m3 = N.new("ShaderNodeMix"); m3.data_type = 'RGBA'; m3.blend_type = 'MULTIPLY'; m3.inputs["Factor"].default_value = 1.0
L.new(m2.outputs[2], m3.inputs[6]); L.new(dk.outputs["Result"], m3.inputs[7])

# lawn: mowed stripes on top
stripe = N.new("ShaderNodeMath"); stripe.operation = 'SINE'
sx = N.new("ShaderNodeMath"); sx.operation = 'MULTIPLY'; sx.inputs[1].default_value = 1.4
L.new(sepz.outputs["X"], sx.inputs[0]); L.new(sx.outputs[0], stripe.inputs[0])
stc = N.new("ShaderNodeMath"); stc.operation = 'GREATER_THAN'; stc.inputs[1].default_value = 0.0
L.new(stripe.outputs[0], stc.inputs[0])
grass = N.new("ShaderNodeMix"); grass.data_type = 'RGBA'
grass.inputs[6].default_value = (0.20, 0.42, 0.10, 1); grass.inputs[7].default_value = (0.30, 0.55, 0.14, 1)
L.new(stc.outputs[0], grass.inputs["Factor"])
gnoise = N.new("ShaderNodeMix"); gnoise.data_type = 'RGBA'; gnoise.blend_type = 'MULTIPLY'; gnoise.inputs["Factor"].default_value = 1.0
L.new(grass.outputs[2], gnoise.inputs[6]); L.new(gr.outputs["Result"], gnoise.inputs[7])
final = N.new("ShaderNodeMix"); final.data_type = 'RGBA'
L.new(mapg.outputs["Result"], final.inputs["Factor"])
L.new(m3.outputs[2], final.inputs[6]); L.new(gnoise.outputs[2], final.inputs[7])
L.new(final.outputs[2], bsdf.inputs["Base Color"])
L.new(m2.outputs[2], bsdf.inputs["Emission Color"])
emul = N.new("ShaderNodeMath"); emul.operation = 'MULTIPLY'; emul.inputs[1].default_value = 2.2
sepE = N.new("ShaderNodeSeparateColor")
L.new(er.outputs["Color"], sepE.inputs[0]); L.new(sepE.outputs[0], emul.inputs[0])
L.new(emul.outputs[0], bsdf.inputs["Emission Strength"])

ground = box("Ground", (0, 4.0, GROUND_BOTTOM / 2), (24, 16, -GROUND_BOTTOM), ground_m)
ground.data.materials.clear(); ground.data.materials.append(ground_m)
bpy.ops.object.modifier_add(type='REMESH')  # not used; removed below
ground.modifiers.clear()

# far lawn plane so the horizon is green, not void
lawn_far = mat("LawnFar", (0.26, 0.5, 0.13), 0.9)
bpy.ops.mesh.primitive_plane_add(size=400, location=(0, 200, -0.02))
bpy.context.object.data.materials.append(lawn_far)

# ---------------- shaft (animated boolean) ----------------
SHAFT_R = 1.05
SX = -1.5
bpy.ops.mesh.primitive_cylinder_add(vertices=48, radius=SHAFT_R, depth=1.0, location=(SX, FRONT_Y, 0))
cutter = bpy.context.object
cutter.name = "Cutter"
cutter.display_type = 'WIRE'
cutter.hide_render = True
# cylinder origin at top: shift mesh so it spans z in [-1, 0] then scale z = depth
for v in cutter.data.vertices:
    v.co.z -= 0.5
cutter.location.z = 0.6  # top above ground surface
boolm = ground.modifiers.new("Shaft", 'BOOLEAN')
boolm.operation = 'DIFFERENCE'
boolm.object = cutter
boolm.solver = 'EXACT'

def dig_depth_keys():
    # (frame, bottom z)
    return [(0, 0.55), (40, 0.55), (100, -1.6), (197, -3.6), (275, -6.2), (336, -7.0),
            (461, -14.8), (560, -24.5), (680, -32), (760, -39.5), (890, -55.5), (959, -56.5)]

for f, z in dig_depth_keys():
    cutter.scale.z = max(0.6 - z, 0.05)
    cutter.keyframe_insert("scale", index=2, frame=f)

# dirt pile beside the hole (grows as we dig)
dirt_m = mat("Dirt", (0.36, 0.22, 0.11), 1.0)
pile = sphere("Pile", (2.6, FRONT_Y + 2.2, 0.0), 1.0, dirt_m, sub=3)
disp = pile.modifiers.new("d", 'DISPLACE')
tex = bpy.data.textures.new("pn", 'CLOUDS'); tex.noise_scale = 0.4
disp.texture = tex; disp.strength = 0.25
for f, s in [(40, 0.01), (100, 0.35), (197, 0.6), (336, 0.85), (461, 1.0)]:
    pile.scale = (s * 1.3, s * 1.0, s * 0.55)
    pile.keyframe_insert("scale", frame=f)

# shovel stuck in the pile
wood = mat("Wood", (0.45, 0.28, 0.12), 0.6)
steel = mat("Steel", (0.6, 0.6, 0.62), 0.35, metal=0.9)
sh = cyl("ShovelHandle", (3.1, FRONT_Y + 2.0, 1.0), 0.05, 2.0, wood, rot=(0, math.radians(-18), 0))
blade = box("ShovelBlade", (2.82, FRONT_Y + 2.0, 0.12), (0.45, 0.06, 0.55), steel)
blade.rotation_euler = (0, math.radians(-18), 0)
for o in (sh, blade):
    o.scale = (0.001, 0.001, 0.001); o.keyframe_insert("scale", frame=60)
    o.scale = (1, 1, 1); o.keyframe_insert("scale", frame=72)

# ---------------- embedded details on the cut face ----------------
root_m = mat("Root", (0.30, 0.18, 0.08), 0.8)
def tube(name, pts, radii, material):
    cu = bpy.data.curves.new(name, 'CURVE'); cu.dimensions = '3D'
    cu.bevel_depth = 1.0; cu.bevel_resolution = 3; cu.use_fill_caps = True
    sp = cu.splines.new('POLY'); sp.points.add(len(pts) - 1)
    for p, (co, r) in enumerate(zip(pts, radii)):
        sp.points[p].co = (*co, 1); sp.points[p].radius = r
    ob = bpy.data.objects.new(name, cu); sc.collection.objects.link(ob)
    cu.materials.append(material)
    return ob
def root_system(x0, depth, spread, seed):
    rnd = random.Random(seed)
    for k in range(7):
        pts = [(x0, FRONT_Y - 0.01, -0.05)]
        x, z = x0, -0.05
        dirx = rnd.uniform(-1, 1) * spread
        n = rnd.randint(5, 8)
        for j in range(n):
            x += dirx / n + rnd.uniform(-0.25, 0.25)
            z -= depth / n * rnd.uniform(0.6, 1.3)
            pts.append((x, FRONT_Y - 0.01, z))
        r0 = rnd.uniform(0.09, 0.16)
        rad = [r0 * (1 - j / len(pts)) + 0.012 for j in range(len(pts))]
        tube(f"Root{seed}_{k}", pts, rad, root_m)
        # side rootlets
        for j in range(2, len(pts) - 1, 2):
            a = pts[j]; b = (a[0] + rnd.uniform(-0.8, 0.8), a[1], a[2] - rnd.uniform(0.3, 0.7))
            tube(f"Rootlet{seed}_{k}_{j}", [a, b], [rad[j] * 0.6, 0.01], root_m)
# front-lawn tree whose roots show in the cut
cyl("FrontTrunk", (-3.5, FRONT_Y + 1.3, 1.9), 0.22, 3.8, mat("Trunk2", (0.3, 0.2, 0.12), 0.9), verts=12)
for k in range(5):
    sphere("FrontFol", (-3.5 + random.uniform(-0.8, 0.8), FRONT_Y + 1.3 + random.uniform(-0.6, 0.6), 4.0 + random.uniform(-0.3, 0.8)),
           random.uniform(1.0, 1.4), mat(f"FF{k}", (0.17 + 0.03 * k, 0.38 + 0.02 * k, 0.11), 0.85), sub=2)
root_system(-3.5, 2.8, 1.6, 11)
root_system(3.4, 2.2, 1.4, 23)
root_system(1.2, 1.4, 1.0, 37)
# worms
worm_m = mat("Worm", (0.85, 0.45, 0.45), 0.4)
for i in range(6):
    x = random.choice([random.uniform(-4.0, -3.0), random.uniform(0.0, 3.6)]); z = random.uniform(-0.6, -2.3)
    pts = [(x + 0.12 * j, FRONT_Y - 0.0, z + 0.12 * math.sin(j * 1.3)) for j in range(6)]
    tube(f"Worm{i}", pts, [0.045] * 6, worm_m)
# old pipe crossing the soil
pipe_m = mat("Pipe", (0.42, 0.44, 0.46), 0.4, metal=0.6)
pipe = cyl("Pipe", (-6.6, FRONT_Y + 0.6, -1.35), 0.22, 8.0, pipe_m, rot=(0, math.radians(90), 0))
ring = cyl("PipeEnd", (-2.6, FRONT_Y + 0.6, -1.35), 0.27, 0.12, pipe_m, rot=(0, math.radians(90), 0))
# stones / pebbles in layers
stone_m = mat("Stone", (0.5, 0.48, 0.45), 0.8)
dark_stone = mat("DarkStone", (0.3, 0.28, 0.27), 0.8)
for i in range(70):
    z = random.uniform(-50, -0.8)
    x = random.uniform(-10, 10)
    if abs(x - SX) < SHAFT_R + 0.4 or (-0.4 < x < 4.6 and -12.6 < z < -8.0) or (0.5<x<4.5 and -22<z<-19) or (0.8<x<4<0 and z<-30) or (-4.6<x<-2.4 and -4.4<z<-2.8):
        continue
    r = random.uniform(0.08, 0.32) * (1.6 if z < -16 else 1.0)
    sphere(f"Stone{i}", (x, FRONT_Y + 0.05, z), r, dark_stone if z < -16 else stone_m,
           scale=(1.3, 0.5, 0.8), sub=1)
# a fossil (spiral shell) in sandstone
fossil_m = mat("Fossil", (0.82, 0.76, 0.62), 0.6)
bpy.ops.curve.primitive_bezier_circle_add(radius=0.5, location=(-3.55, FRONT_Y + 0.03, -13.2), rotation=(math.radians(90), 0, 0))
spiral = bpy.context.object
spiral.data.bevel_depth = 0.07
spiral.data.materials.append(fossil_m)
sphere("FossilShell", (-3.55, FRONT_Y + 0.04, -13.2), 0.5, fossil_m, scale=(1, 0.25, 1))



# ---------------- dinosaur skeleton in the sandstone ----------------
bonem = mat("DinoBone", (0.90, 0.85, 0.72), 0.55)
socket = mat("Socket", (0.15, 0.1, 0.06), 0.9)
DY = FRONT_Y - 0.03
OX, OZ = 0.9, -0.6   # global offset
DS = 0.55
def P(x, z): return (2.15 + (x - 5.4) * DS, DY, -10.3 + (z + 9.9) * DS)
spine = [(9.2, -10.9), (8.4, -10.5), (7.6, -10.1), (6.8, -9.75), (6.0, -9.55), (5.2, -9.5), (4.4, -9.45),
         (3.7, -9.3), (3.2, -9.0), (2.9, -8.6)]
tube("DinoSpine", [P(*p) for p in spine], [(0.03 + 0.07 * (j / len(spine))) * DS for j in range(len(spine))], bonem)
for j in range(len(spine) - 1):
    for t in (0.0, 0.5):
        x = spine[j][0] + (spine[j + 1][0] - spine[j][0]) * t
        z = spine[j][1] + (spine[j + 1][1] - spine[j][1]) * t
        sphere("Vert", P(x, z + 0.1), (0.06 + 0.06 * j / len(spine)) * DS, bonem, scale=(0.7, 0.5, 1.3), sub=1)
# ribs
for j, x in enumerate([3.9, 4.25, 4.6, 4.95, 5.3, 5.65]):
    z = -9.45
    L = 1.05 - abs(j - 2.5) * 0.12
    tube(f"Rib{j}", [P(x, z), P(x - 0.15, z - L * 0.5), P(x + 0.05, z - L)], [0.05 * DS, 0.045 * DS, 0.02], bonem)
# skull + jaw + teeth
sphere("Skull", P(2.35, -8.45), 0.62 * DS, bonem, scale=(1.25, 0.25, 0.62), sub=3)
sphere("Eye", (P(2.55,-8.3)[0], DY - 0.06, P(2.55,-8.3)[2]), 0.08, socket, sub=2)
sphere("Nostril", (P(1.75,-8.35)[0], DY - 0.06, P(1.75,-8.35)[2]), 0.04, socket, sub=1)
sphere("Jaw", P(2.25, -8.95), 0.55 * DS, bonem, scale=(1.3, 0.22, 0.25), sub=2)
for k in range(7):
    bpy.ops.mesh.primitive_cone_add(vertices=6, radius1=0.03, depth=0.1,
        location=(P(1.65 + 0.14 * k, -8.78)[0], DY - 0.03, P(1.65,-8.78)[2]), rotation=(math.pi, 0, 0))
    bpy.context.object.data.materials.append(bonem)
# legs
for dx, ph in ((0.0, 0.0), (0.45, 0.25)):
    hip = (6.0 + dx, -9.65)
    tube("Leg", [P(*hip), P(5.55 + dx, -10.7), P(6.05 + dx, -11.55), P(5.6 + dx, -11.75)], [0.12 * DS, 0.08 * DS, 0.06 * DS, 0.03], bonem)
    sphere("Knee", P(5.55 + dx, -10.7), 0.1 * DS, bonem, sub=1)
sphere("Pelvis", P(6.1, -9.8), 0.35 * DS, bonem, scale=(1.1, 0.25, 0.7), sub=2)
for dx in (0.0, 0.2):
    tube("Arm", [P(3.75 + dx, -9.55), P(3.6 + dx, -9.95), P(3.8 + dx, -10.1)], [0.05 * DS, 0.035 * DS, 0.015], bonem)

# ---------------- treasure chest (shallow) ----------------
chest_w = mat("ChestWood", (0.38, 0.2, 0.08), 0.7)
gold = mat("Gold", (1.0, 0.75, 0.2), 0.25, metal=1.0)
box("Chest", (-3.5, FRONT_Y + 0.05, -3.6), (1.0, 0.5, 0.65), chest_w, bevel=0.04)
box("ChestBand", (-3.5, FRONT_Y - 0.2, -3.6), (1.04, 0.06, 0.12), gold)
box("ChestLock", (-3.5, FRONT_Y - 0.22, -3.45), (0.16, 0.05, 0.2), gold)
for i in range(5):
    cyl("Coin", (-3.9 + i * 0.13, FRONT_Y - 0.03, -4.05 + 0.04 * (i % 2)), 0.08, 0.03, gold, rot=(math.radians(90), 0, 0), verts=16)

# ---------------- oil pocket ----------------
oil = mat("Oil", (0.02, 0.02, 0.025), 0.05)
sphere("OilPocket", (2.4, FRONT_Y + 0.05, -20.5), 1.0, oil, scale=(1.6, 0.25, 0.75), sub=3)

# ---------------- crystal geode ----------------
geo_m = mat("GeodeShell", (0.32, 0.3, 0.34), 0.7)
sphere("Geode", (2.3, FRONT_Y + 0.05, -32.0), 1.15, geo_m, scale=(1.0, 0.2, 0.9), sub=3)
crys = mat("Crystal", (0.6, 0.35, 0.95), 0.1, emit=(0.6, 0.3, 1.0), emit_strength=1.5)
for k in range(14):
    a = random.uniform(0, 2 * math.pi); r = random.uniform(0.0, 0.75)
    bpy.ops.mesh.primitive_cone_add(vertices=6, radius1=random.uniform(0.07, 0.13), depth=random.uniform(0.35, 0.7),
        location=(2.3 + r * math.cos(a), FRONT_Y - 0.08, -32.0 + r * math.sin(a) * 0.8),
        rotation=(math.radians(random.uniform(60, 120)), 0, a))
    bpy.context.object.data.materials.append(crys)

# ---------------- lava veins rising from the magma ----------------
lava = mat("Lava", (1.0, 0.4, 0.05), 0.4, emit=(1.0, 0.38, 0.04), emit_strength=3.0)
for k, x0 in enumerate([-3.8, 0.4, 2.2, 3.9]):
    pts = [(x0, FRONT_Y - 0.02, -53.2)]
    x, z = x0, -53.2
    for j in range(6):
        x += random.uniform(-0.6, 0.6); z += random.uniform(0.9, 1.8)
        pts.append((x, FRONT_Y - 0.02, z))
    tube(f"Lava{k}", pts, [0.16 * (1 - j / 7) + 0.02 for j in range(7)], lava)

# ---------------- groundwater ----------------
water_m = mat("Water", (0.25, 0.55, 0.85), 0.05, alpha=0.85)
water = box("Water", (0, FRONT_Y, 0), (2 * SHAFT_R - 0.04, 2 * SHAFT_R - 0.04, 1.0), water_m)
water.data.vertices.foreach_set("co", [c for v in water.data.vertices for c in (v.co.x, v.co.y, v.co.z - 0.5)])
water.data.update()
# clip half: water only in shaft, keep it cylindrical
wcyl = cyl("WaterCyl", (SX, FRONT_Y, -0.5), SHAFT_R - 0.03, 1.0, water_m, verts=48)
bpy.data.objects.remove(water)
water = wcyl
bpy.ops.mesh.primitive_cube_add(location=(SX, FRONT_Y - 2.0, -30)); wcut = bpy.context.object
wcut.scale = (5, 2.0, 40); wcut.hide_render = True; wcut.display_type = 'WIRE'
wb = water.modifiers.new("cut", 'BOOLEAN'); wb.operation = 'DIFFERENCE'; wb.object = wcut; wb.solver = 'EXACT'

# keyframe: rises from bottom (-7) to -3 between f275-336, drains by f400
def wkey(f, top, bottom, vis=True):
    h = max(top - bottom, 0.01)
    water.location.z = bottom + h / 2
    water.scale.z = h
    water.keyframe_insert("location", index=2, frame=f)
    water.keyframe_insert("scale", index=2, frame=f)
    water.hide_render = not vis
    water.keyframe_insert("hide_render", frame=f)
def dig_bottom(f):
    sc.frame_set(f); return 0.6 - cutter.scale.z
wkey(0, -6.2, -6.21, False); wkey(274, -6.2, -6.21, False)
for f in range(276, 400, 2):
    b = dig_bottom(f) + 0.02
    top = -6.2 + 3.0 * (f - 276) / 60 if f <= 336 else -3.2 + (b + 0.15 + 3.2) * min((f - 336) / 50, 1)
    wkey(f, top, b, f < 392)
wkey(400, -9, -9.01, False); wkey(959, -9, -9.01, False)
sc.frame_set(0)

# ---------------- magma glow light at the bottom ----------------
bpy.ops.object.light_add(type='POINT', location=(SX, FRONT_Y - 1.5, -54))
glow = bpy.context.object
glow.data.color = (1.0, 0.45, 0.12)
glow.data.shadow_soft_size = 2.0
for f, e in [(0, 0), (700, 0), (800, 300), (890, 1500), (959, 2200)]:
    glow.data.energy = e
    glow.data.keyframe_insert("energy", frame=f)

# ---------------- house ----------------
wall_m = mat("Wall", (0.86, 0.80, 0.70), 0.85)
roof_m = mat("Roof", (0.66, 0.28, 0.15), 0.75)
trim_m = mat("Trim", (0.95, 0.95, 0.93), 0.6)
glass_m = mat("Glass", (0.10, 0.18, 0.30), 0.08)
shutter_m = mat("Shutter", (0.12, 0.27, 0.52), 0.6)
patio_m = mat("Patio", (0.78, 0.72, 0.62), 0.8)
HX, HY, HW, HD, HH = 0.0, 4.2, 8.0, 4.4, 5.4
house = box("House", (HX, HY, HH / 2), (HW, HD, HH), wall_m)
fy = HY - HD / 2  # front wall y
box("Plinth", (HX, HY, 0.15), (HW + 0.1, HD + 0.1, 0.3), trim_m)
box("Band", (HX, HY, HH / 2 + 0.05), (HW + 0.06, HD + 0.06, 0.12), trim_m)
# roof prism
bpy.ops.mesh.primitive_cube_add()
roof = bpy.context.object; roof.name = "Roof"
rw, rd, rh = HW + 0.8, HD + 1.0, 2.2
verts = [(-rw/2, -rd/2, 0), (rw/2, -rd/2, 0), (rw/2, rd/2, 0), (-rw/2, rd/2, 0), (-rw/2, 0, rh), (rw/2, 0, rh)]
faces = [(0, 1, 5, 4), (3, 4, 5, 2), (0, 4, 3), (1, 2, 5), (0, 3, 2, 1)]
me = bpy.data.meshes.new("RoofMesh"); me.from_pydata(verts, [], faces); me.update()
roof.data = me
roof.location = (HX, HY, HH)
roof.data.materials.append(roof_m)
sol = roof.modifiers.new("s", 'SOLIDIFY'); sol.thickness = 0.18
# roof tile lines
tile_m = mat("TileLine", (0.5, 0.2, 0.1), 0.8)
for i in range(1, 7):
    t = i / 7
    z = HH + rh * t + 0.1
    yy = -rd / 2 * (1 - t)
    for s in (-1, 1):
        b = box(f"Tile{i}{s}", (HX, HY + s * yy, z), (rw, 0.05, 0.05), tile_m)
# chimney
box("Chimney", (HX + 2.4, HY + 0.6, HH + 2.0), (0.6, 0.6, 2.0), wall_m)
box("ChimneyCap", (HX + 2.4, HY + 0.6, HH + 3.05), (0.75, 0.75, 0.12), trim_m)

def window(x, z, w=0.95, h=1.25, shutters=True):
    box("WinFrame", (x, fy - 0.03, z), (w + 0.16, 0.08, h + 0.16), trim_m)
    box("WinGlass", (x, fy - 0.07, z), (w, 0.04, h), glass_m)
    box("WinBarV", (x, fy - 0.1, z), (0.05, 0.03, h), trim_m)
    box("WinBarH", (x, fy - 0.1, z), (w, 0.03, 0.05), trim_m)
    box("Sill", (x, fy - 0.12, z - h / 2 - 0.1), (w + 0.35, 0.22, 0.08), trim_m)
    if shutters:
        for s in (-1, 1):
            box("Shutter", (x + s * (w / 2 + 0.28), fy - 0.06, z), (0.42, 0.06, h + 0.1), shutter_m)

for x in (-3.0, -1.4, 1.4, 3.0):
    window(x, 4.0)
for x in (-3.0, 3.0):
    window(x, 1.4)
# patio sliding door
box("DoorFrame", (0, fy - 0.03, 1.25), (2.3, 0.08, 2.3), trim_m)
box("DoorGlass", (0, fy - 0.07, 1.25), (2.1, 0.04, 2.1), glass_m)
box("DoorMid", (0, fy - 0.1, 1.25), (0.07, 0.03, 2.1), trim_m)
box("PatioSlab", (0, fy - 1.3, 0.04), (5.5, 2.6, 0.1), patio_m)
# patio furniture
furn_m = mat("Furn", (0.25, 0.22, 0.2), 0.5)
box("Table", (-1.8, fy - 1.2, 0.5), (0.8, 0.8, 0.06), furn_m)
cyl("TableLeg", (-1.8, fy - 1.2, 0.25), 0.04, 0.5, furn_m)
for dx in (-0.6, 0.6):
    box("Chair", (-1.8 + dx, fy - 1.2, 0.3), (0.4, 0.4, 0.05), furn_m)
    box("ChairBack", (-1.8 + dx, fy - 1.0, 0.55), (0.4, 0.05, 0.5), furn_m)
# potted plants
pot_m = mat("Pot", (0.65, 0.32, 0.18), 0.7)
leaf_m = mat("Leaf", (0.18, 0.4, 0.12), 0.8)
for x in (-1.5, 1.5, 2.4):
    cyl("Pot", (x, fy - 0.35, 0.22), 0.2, 0.4, pot_m)
    sphere("Plant", (x, fy - 0.35, 0.6), 0.3, leaf_m, sub=1)

# ---------------- trees & bushes ----------------
trunk_m = mat("Trunk", (0.3, 0.2, 0.12), 0.9)
foliage = [mat("Fol1", (0.16, 0.36, 0.10), 0.85), mat("Fol2", (0.22, 0.44, 0.13), 0.85), mat("Fol3", (0.13, 0.30, 0.09), 0.85)]
def tree(x, y, h=3.5, r=1.4):
    cyl("Trunk", (x, y, h / 2), 0.16, h, trunk_m, verts=10)
    for k in range(5):
        sphere("Fol", (x + random.uniform(-r * .5, r * .5), y + random.uniform(-r * .4, r * .4), h + random.uniform(-0.3, 0.8)),
               r * random.uniform(0.6, 0.9), random.choice(foliage), sub=2)
tree(-6.8, 6.5, 4.2, 1.7); tree(7.0, 7.5, 4.6, 1.8); tree(-9.5, 12, 4.0, 1.5); tree(10, 13, 4.4, 1.6)
tree(-14, 25, 5, 2.2); tree(15, 28, 5.5, 2.3); tree(3, 40, 6, 2.5)
for x in (-5.2, 5.3):
    sphere("Bush", (x, 2.0, 0.4), 0.7, foliage[1], scale=(1.3, 1, 0.8))
# far neighbor houses
for (x, y, s) in [(-22, 45, 1.0), (24, 50, 1.1), (-6, 70, 0.9)]:
    box("NH", (x, y, 2.5 * s), (7 * s, 5 * s, 5 * s), wall_m)
    bpy.ops.mesh.primitive_cone_add(vertices=4, radius1=5.6 * s, depth=2.4 * s, location=(x, y, 6.2 * s), rotation=(0, 0, math.radians(45)))
    bpy.context.object.data.materials.append(roof_m)
# garden hose curve on lawn
hose_m = mat("Hose", (0.15, 0.45, 0.2), 0.5)
bpy.ops.curve.primitive_bezier_curve_add(location=(0, 0, 0.04))
hose = bpy.context.object
hose.data.bevel_depth = 0.04
pts = hose.data.splines[0].bezier_points
pts[0].co = (-4.0, 1.2, 0); pts[0].handle_left = (-4.5, 1.0, 0); pts[0].handle_right = (-3.0, 1.5, 0)
pts[1].co = (-1.5, -1.6, 0); pts[1].handle_left = (-2.8, -2.2, 0); pts[1].handle_right = (-0.5, -1.1, 0)
hose.data.materials.append(hose_m)

# ---------------- camera ----------------
bpy.ops.object.camera_add()
cam = bpy.context.object
sc.camera = cam
cam.data.lens = 26
cam.data.sensor_fit = 'VERTICAL'
cam.data.sensor_height = 36
cam.data.clip_end = 1000
target = bpy.data.objects.new("Target", None)
sc.collection.objects.link(target)
tr = cam.constraints.new('TRACK_TO')
tr.target = target
tr.track_axis = 'TRACK_NEGATIVE_Z'; tr.up_axis = 'UP_Y'

cam_keys = [  # frame, cam loc, target loc
    (0,   (0.0, -18.5, 4.6),  (0, 1.0, 0.4)),
    (100, (0.0, -17.0, 3.6),  (0, 0.0, -0.2)),
    (197, (0.0, -15.5, 1.2),  (0, -2.0, -1.6)),
    (336, (0.0, -14.0, -3.6), (0, -3.0, -4.6)),
    (461, (0.0, -15.0, -11.8), (0, -3.0, -12.0)),
    (560, (0.0, -15.0, -21.5), (0, -3.0, -21.5)),
    (760, (0.0, -15.0, -36.0), (0, -3.0, -36.0)),
    (890, (0.0, -15.5, -50.5), (0, -3.0, -51.5)),
    (959, (0.0, -13.5, -51.5), (0, -3.0, -52.5)),
]
for f, cl, tl in cam_keys:
    cam.location = cl; cam.keyframe_insert("location", frame=f)
    target.location = tl; target.keyframe_insert("location", frame=f)

for o in list(bpy.data.objects):
    if o.animation_data and o.animation_data.action:
        try:
            for fc in o.animation_data.action.fcurves:
                for kp in fc.keyframe_points:
                    kp.interpolation = 'BEZIER'
                    kp.easing = 'AUTO'
        except AttributeError:
            pass

bpy.ops.wm.save_as_mainfile(filepath="/home/claude/whatif/scene.blend")
print("SCENE OK")
