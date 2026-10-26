import bpy, os, time
bpy.ops.wm.open_mainfile(filepath="/home/claude/whatif/scene.blend")
sc=bpy.context.scene
sc.render.resolution_percentage=40; sc.cycles.samples=8
for f in range(0,960,2):
    p=f"/home/claude/whatif/frames/f{f:04d}.png"
    if os.path.exists(p): continue
    sc.frame_set(f); sc.render.filepath=p
    bpy.ops.render.render(write_still=True)
    print("DONE",f,flush=True)
