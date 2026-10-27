"""Look v2 (cinematic diorama) on top of an episode's scene.blend — same models, same camera moves.
   python3 pipeline/look_v2.py <episode_dir>      -> writes <episode_dir>/scene_v2.blend
Changes: less flat fill + cool rim light (silhouettes pop),
warm/cool contrast (warm windows vs cyan UFO), tilt-shift depth of field that follows the camera target
(makes the low-poly set read as a miniature), soft key light under any 'UFO' group if present."""
import bpy, math, sys
ep = sys.argv[1]
bpy.ops.wm.open_mainfile(filepath=f"{ep}/scene.blend")
sc = bpy.context.scene
ob = bpy.data.objects

# 1) tone mapping: richer colours, highlights roll off instead of clipping
sc.view_settings.view_transform = 'Standard'   # AgX tested: washes out the cartoon colours -> keep Standard,
sc.view_settings.exposure = 0.0                  # the grade (bloom, contrast, vignette) is done in compose_v2.py

# 2) lighting: kill the flat front fill, add a rim/back light and a soft low key
for o in ob:
    if o.type == 'LIGHT' and o.data.type == 'AREA' and o.data.energy > 1500:
        o.data.energy *= 0.65                       # front fill 2600 -> ~1700 (more shape, still bright)
    if o.type == 'LIGHT' and o.data.type == 'SUN':
        o.data.energy *= 1.25
bpy.ops.object.light_add(type='AREA', location=(0, 22, 9))
rim = bpy.context.object; rim.name = "RimV2"
rim.data.energy = 2200; rim.data.size = 18; rim.data.color = (0.55, 0.65, 1.0)
rim.rotation_euler = (math.radians(-62), 0, 0)      # faces the camera side -> edge light on everything

# 3) warm windows a bit hotter (warm/cool contrast against the night + cyan ship)
for m in bpy.data.materials:
    if m.name.startswith("Window") and m.use_nodes:
        for n in m.node_tree.nodes:
            if n.type == 'BSDF_PRINCIPLED':
                n.inputs["Emission Color"].default_value = (1.0, 0.55, 0.18, 1)

# 4) UFO: downward cyan key that lights the lawn under the ship
if "UFO" in ob:
    bpy.ops.object.light_add(type='SPOT', location=ob["UFO"].location)
    s = bpy.context.object; s.name = "UfoKeyV2"
    s.data.energy = 700; s.data.color = (0.35, 1.0, 0.95)
    s.data.spot_size = math.radians(75); s.data.spot_blend = 0.6
    s.rotation_euler = (0, 0, 0)                    # spot points -Z = straight down
    s.parent = ob["UFO"]; s.matrix_parent_inverse = ob["UFO"].matrix_world.inverted()

# 5) tilt-shift depth of field following the camera's look-at target
cam = sc.camera
cam.data.dof.use_dof = True
cam.data.dof.focus_object = ob["Target"]
cam.data.dof.aperture_fstop = 4.0
cam.data.dof.aperture_blades = 7

sc.cycles.samples = 10
bpy.ops.wm.save_as_mainfile(filepath=f"{ep}/scene_v2.blend")
print("LOOK V2 OK")
