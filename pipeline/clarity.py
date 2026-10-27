"""House look rules applied to every scene right before rendering (render.py calls apply()).
1. Bold outlines on every shape (Freestyle) so the low-poly forms read clearly on a phone.
2. Nothing see-through: transparent / glass / transmission materials are made fully opaque.
   Objects that used a see-through material (light beams, halos, light cones) become a solid
   glowing wire lattice instead, so the beam still reads as a beam without any transparency."""
import bpy, bmesh

def _closed(me):
    bm = bmesh.new(); bm.from_mesh(me)
    ok = len(bm.faces) > 0 and all(len(e.link_faces) == 2 for e in bm.edges)
    bm.free(); return ok

def _was_transparent(m):
    if not m or not m.use_nodes:
        return False
    hit = False
    for n in m.node_tree.nodes:
        if n.type == 'BSDF_TRANSPARENT':
            hit = True
        if n.type == 'BSDF_PRINCIPLED':
            for key in ("Transmission Weight", "Alpha"):
                v = n.inputs[key].default_value
                if (key == "Alpha" and v < 1.0) or (key != "Alpha" and v > 0.0):
                    hit = True
    return hit

def _make_opaque(m):
    nt = m.node_tree
    for n in list(nt.nodes):
        if n.type == 'MIX_SHADER':
            # keep the non-transparent side only
            a = n.inputs[1].links[0].from_node if n.inputs[1].links else None
            b = n.inputs[2].links[0].from_node if n.inputs[2].links else None
            keep = b if a is not None and a.type == 'BSDF_TRANSPARENT' else a
            if keep is not None:
                for l in list(n.outputs[0].links):
                    nt.links.new(keep.outputs[0], l.to_socket)
        if n.type == 'BSDF_PRINCIPLED':
            n.inputs["Transmission Weight"].default_value = 0.0
            n.inputs["Alpha"].default_value = 1.0
    for n in list(nt.nodes):
        if n.type in ('BSDF_TRANSPARENT', 'MIX_SHADER') and not n.outputs[0].links:
            nt.nodes.remove(n)

def apply(sc, line_w=0.06):
    see_through = {m.name for m in bpy.data.materials if _was_transparent(m)}
    no_line = bpy.data.collections.get("NoOutline") or bpy.data.collections.new("NoOutline")
    if no_line.name not in sc.collection.children:
        sc.collection.children.link(no_line)
    for o in bpy.data.objects:
        if o.type != 'MESH':
            continue
        used = {s.material.name for s in o.material_slots if s.material}
        if used & see_through and not any(md.type == 'WIREFRAME' for md in o.modifiers):
            w = o.modifiers.new("SolidBeam", 'WIREFRAME')
            w.thickness = 0.07; w.use_replace = True; w.use_even_offset = True
            o.visible_shadow = False
            if o.name not in no_line.objects:
                no_line.objects.link(o)               # glowing bars get no dark outline
    for name in see_through:
        _make_opaque(bpy.data.materials[name])

    sc.cycles.transparent_max_bounces = 128        # outline shells are see-through from inside; enough bounces or they turn black
    # bold outlines: "inverted hull" shell (solid dark rim around every shape)
    ol = bpy.data.materials.get("OutlineInk")
    if ol is None:
        ol = bpy.data.materials.new("OutlineInk"); ol.use_nodes = True
        nt = ol.node_tree; N = nt.nodes; L = nt.links
        N.remove(N["Principled BSDF"])
        geo = N.new("ShaderNodeNewGeometry")
        em = N.new("ShaderNodeEmission"); em.inputs["Color"].default_value = (0.05, 0.04, 0.08, 1)
        em.inputs["Strength"].default_value = 1.0
        hole = N.new("ShaderNodeBsdfTransparent")     # only lets the object itself show through its own shell
        lp = N.new("ShaderNodeLightPath")
        # ink only on camera rays hitting the outer side of the flipped shell; shadows / bounces ignore the shell
        inv = N.new("ShaderNodeMath"); inv.operation = 'SUBTRACT'; inv.inputs[0].default_value = 1.0
        L.new(geo.outputs["Backfacing"], inv.inputs[1])
        mul = N.new("ShaderNodeMath"); mul.operation = 'MULTIPLY'
        L.new(inv.outputs[0], mul.inputs[0]); L.new(lp.outputs["Is Camera Ray"], mul.inputs[1])
        mx = N.new("ShaderNodeMixShader")
        L.new(mul.outputs[0], mx.inputs["Fac"])
        L.new(hole.outputs[0], mx.inputs[1]); L.new(em.outputs[0], mx.inputs[2])
        L.new(mx.outputs[0], N["Material Output"].inputs["Surface"])
    for o in bpy.data.objects:
        if o.type != 'MESH' or o.name in no_line.objects or o.name.startswith(("Star", "Moon", "Sky")):
            continue
        if max(o.dimensions) < 0.12 or max(o.dimensions) > 18 or not _closed(o.data) or any(m.name == "Outline" for m in o.modifiers):
            continue
        if ol.name not in [m.name for m in o.data.materials if m]:
            if len(o.data.materials) == 0:
                o.data.materials.append(o.active_material)      # keep slot 0 = the object's own look
            o.data.materials.append(ol)
        sd = o.modifiers.new("Outline", 'SOLIDIFY')
        sd.thickness = line_w / max(max(o.scale), 1e-3); sd.offset = 1.0
        sd.use_flip_normals = True; sd.use_rim = False
        sd.material_offset = [m.name if m else '' for m in o.data.materials].index(ol.name)
    return sorted(see_through)
