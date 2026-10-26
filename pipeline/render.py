"""Render every 2nd frame of a .blend:  python3 render.py <episode_dir> [percent=40] [samples=8] [frames...]
Writes <episode_dir>/frames/fNNNN.png. Skips frames that already exist (safe to resume).
With explicit frame numbers it renders only those into <episode_dir>/test/ (for previews)."""
import bpy, os, sys, time
ep = sys.argv[1]
pct = int(sys.argv[2]) if len(sys.argv) > 2 else 40
spp = int(sys.argv[3]) if len(sys.argv) > 3 else 8
only = [int(x) for x in sys.argv[4:]]
bpy.ops.wm.open_mainfile(filepath=f"{ep}/scene.blend")
sc = bpy.context.scene
sc.render.resolution_percentage = pct
sc.cycles.samples = spp
out = f"{ep}/test" if only else f"{ep}/frames"
os.makedirs(out, exist_ok=True)
frames = only or range(sc.frame_start, sc.frame_end + 1, 2)
for f in frames:
    p = f"{out}/f{f:04d}.png"
    if not only and os.path.exists(p):
        continue
    t = time.time()
    sc.frame_set(f); sc.render.filepath = p
    bpy.ops.render.render(write_still=True)
    print("DONE", f, round(time.time() - t, 1), flush=True)
