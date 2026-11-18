#!/usr/bin/env python3
"""Mechanical rework variant B (owner decision 2026-11-18): outline 160 x 85, four M3 corner holes.

Usage: <KiCad python> mount_rework_b.py BOARD.kicad_pcb prepare
       <KiCad python> mount_rework_b.py BOARD.kicad_pcb route [--passes N]
       <KiCad python> mount_rework_b.py BOARD.kicad_pcb holes
prepare: outline rectangle 150 -> 160 mm wide (right edge, no copper added: the GND planes stay 0-150);
         J101/TP101/F101 3 mm down together with the VBAT_IN pours (F/B) and the lower edge of the VBAT_FUSED pours;
         LED row J108-J112 to x 10 ... 61 with 1 mm gaps; R520 and TP506 to free spots; the track chains from
         the moved parts' pads up to the first via / foreign pad / branch are removed (strip_stubs) and routed again.
route:   locks all copper, exports Specctra DSN (In1/In2 as power planes, outer pours as keep-outs, as
         autoroute_k1.py), runs Freerouting headless for the open connections only, imports the new copper into
         group "mount_rework_b" (import_autoroute.py), closes gaps and stitches GND vias.
cleanup: (after route) connector labels follow, D101 silk reference hidden, dangling vias removed.
holes:   sets H1-H4 to the corner positions HOLES (checked by mounting_holes.Board.check), locks them, refills.
Coordinates are K1 coordinates (top-left outline corner). Refuses to run while KiCad lock files exist.
"""
from pathlib import Path
import re
import subprocess
import sys

import pcbnew

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import mounting_holes as mh  # noqa: E402

T, M = pcbnew.ToMM, pcbnew.FromMM
W_NEW = 160.0
DY_IN = 3.0
# F101 only 2.4 mm down and 1.4 mm left: 3 mm would put its courtyard onto D101 (TVS); TP101 gets its own spot
MOVES = {"J101": (0, DY_IN), "F101": (-1.4, 2.4),
         "J108": (7.5, 0), "J109": (6.5, 0), "J110": (5.5, 0), "J111": (4.5, 0), "J112": (3.5, 0)}
PLACE = {"R520": (58.5, 74.9), "TP506": (63.0, 81.4), "TP101": (9.0, 27.5)}          # new centres (free spots, checked by DRC)
HOLES = {"H1": (4.5, 4.5), "H2": (4.5, 80.5), "H3": (155.5, 16.0), "H4": (155.5, 80.5)}
JAR = Path.home() / "Documents/KiCad/10.0/3rdparty/plugins/app_freerouting_kicad-plugin/jar/freerouting-2.4.1.jar"


def origin(b):
    e = b.GetBoardEdgesBoundingBox()
    return T(e.GetLeft()) + 0.05, T(e.GetTop()) + 0.05


def strip_stubs(b, refs):
    """Remove, before the move, the track chains that start on a pad of REFS, up to the first via, the next pad of
    another footprint or the next branch point (>= 3 track ends). Vias, branches and all other copper stay."""
    fps = {f.GetReference(): f for f in b.GetFootprints()}
    own = [p for r in refs for p in fps[r].Pads() if p.GetNetname()]
    others = [p for f in b.GetFootprints() if f.GetReference() not in refs for p in f.Pads()]
    tracks = [t for t in b.GetTracks() if t.GetClass() == "PCB_TRACK"]
    vias = [t for t in b.GetTracks() if t.GetClass() == "PCB_VIA"]

    uid = lambda t: t.m_Uuid.AsString()  # noqa: E731  (SWIG objects are not hashable)

    def ends_at(pt, layer, net, skip):
        return [t for t in tracks if uid(t) not in skip and t.GetNetCode() == net and t.GetLayer() == layer
                and (t.GetStart() == pt or t.GetEnd() == pt)]
    doomed = {}
    for p in own:
        start = [t for t in tracks if t.GetNetCode() == p.GetNetCode() and
                 (p.HitTest(t.GetStart()) or p.HitTest(t.GetEnd()))]
        for t0 in start:
            chain, t, from_pad = [], t0, True
            pt = t.GetEnd() if p.HitTest(t.GetStart()) else t.GetStart()
            while True:
                chain.append(t)
                if any(v.GetNetCode() == t.GetNetCode() and v.GetPosition() == pt for v in vias):
                    break                                 # stop at a via (kept)
                if any(q.GetNetCode() == t.GetNetCode() and q.HitTest(pt) and q.IsOnLayer(t.GetLayer())
                       for q in others):
                    break                                 # reached another part's pad
                nxt = ends_at(pt, t.GetLayer(), t.GetNetCode(), {uid(c) for c in chain})
                if len(nxt) != 1:
                    break                                 # open end or branch point
                t = nxt[0]
                pt = t.GetEnd() if t.GetStart() == pt else t.GetStart()
            doomed.update((uid(c), c) for c in chain)
    return list(doomed.values())   # removed by the caller last: b.Remove() breaks later SWIG lookups


def prepare(b):
    ox, oy = origin(b)
    edges = [d for d in b.GetDrawings() if d.GetLayer() == pcbnew.Edge_Cuts]
    if len(edges) != 1 or edges[0].GetShape() != pcbnew.SHAPE_T_RECTANGLE:
        raise SystemExit("ABORTED: expected one Edge.Cuts rectangle")
    r = edges[0]
    if abs(T(r.GetEnd().x) - ox - 150.0) > 0.06:
        raise SystemExit("ABORTED: outline is not 150 mm wide (already reworked?)")
    r.SetEnd(pcbnew.VECTOR2I(M(W_NEW + ox - 0.0), r.GetEnd().y))
    doomed = strip_stubs(b, list(MOVES) + list(PLACE))
    fps = {f.GetReference(): f for f in b.GetFootprints()}
    nets = set()
    for ref, (dx, dy) in MOVES.items():
        f = fps[ref]
        f.Move(pcbnew.VECTOR2I(M(dx), M(dy)))
        nets |= {p.GetNetname() for p in f.Pads() if p.GetNetname()}
    for ref, (x, y) in PLACE.items():
        f = fps[ref]
        f.SetPosition(pcbnew.VECTOR2I(M(x + ox), M(y + oy)))
        nets |= {p.GetNetname() for p in f.Pads() if p.GetNetname()}
    for z in b.Zones():
        n = z.GetZoneName()
        ol = z.Outline()
        bb = z.GetBoundingBox()
        if n in ("in_vbat_in_f", "in_vbat_in_b"):        # follows J101 (+3 mm) and reaches TP101 on the left
            for i in range(ol.TotalVertices()):
                v = ol.CVertex(i)
                x = M(7.4 + ox) if v.x <= bb.GetLeft() + M(0.01) else v.x
                ol.SetVertex(i, pcbnew.VECTOR2I(x, v.y + M(DY_IN)))
        elif n in ("in_vbat_fused_f", "in_vbat_fused_b"):  # follows the right F101 pins (-1.4 / +2.4)
            for i in range(ol.TotalVertices()):
                v = ol.CVertex(i)
                x = v.x - M(1.4) if v.x <= bb.GetLeft() + M(0.01) else v.x
                y = v.y + M(2.4) if v.y >= bb.GetBottom() - M(0.01) else v.y
                ol.SetVertex(i, pcbnew.VECTOR2I(x, y))
    # VBAT_IN stitching vias move with their pour; GND vias that now sit on a moved pad go
    moved_pads = [p for r in list(MOVES) + list(PLACE) for p in fps[r].Pads()]
    for t in b.GetTracks():
        if t.GetClass() == "PCB_VIA" and t.GetNetname().endswith("VBAT_IN"):
            t.Move(pcbnew.VECTOR2I(0, M(DY_IN)))
    for t in b.GetTracks():
        if t.GetClass() == "PCB_VIA" and t.GetNetname() == "GND":
            sh = t.GetEffectiveShape(pcbnew.F_Cu)
            if any(p.GetEffectiveShape(pcbnew.F_Cu).Collide(sh, M(0.2)) or
                   p.GetEffectiveShape(pcbnew.B_Cu).Collide(sh, M(0.2)) for p in moved_pads):
                doomed.append(t)
    for t in doomed:
        b.Remove(t)
    gone = len(doomed)
    print("outline 160 x 85; moved %s; placed %s; removed %d stub tracks (nets: %s)"
          % (", ".join(MOVES), ", ".join(PLACE), gone, ", ".join(sorted(n.split("/")[-1] for n in nets))))


def run(args):
    r = subprocess.run(args, capture_output=True, text=True)
    out = "\n".join(l for l in (r.stdout + r.stderr).splitlines() if not re.search(r"stdpbase|swig|Debug: Adding", l))
    if r.returncode:
        raise SystemExit("FAILED: %s\n%s" % (" ".join(map(str, args)), out[-1500:]))
    return out


def route(pcb, passes):
    b = pcbnew.LoadBoard(str(pcb))
    work = pcb.parent / (pcb.stem + "_rework_b")
    work.mkdir(exist_ok=True)
    for t in b.GetTracks():
        t.SetLocked(True)
    ko = []
    for z in b.Zones():
        if z.GetZoneName() in ("gnd_in1", "gnd_in2") or z.GetIsRuleArea():
            continue
        for lay, name in ((pcbnew.F_Cu, "F.Cu"), (pcbnew.B_Cu, "B.Cu")):
            if not z.IsOnLayer(lay):
                continue
            ol = z.Outline().Outline(0)
            pts = ["%d %d" % (round(T(ol.CPoint(i).x) * 1000), -round(T(ol.CPoint(i).y) * 1000))
                   for i in range(ol.PointCount())]
            pts.append(pts[0])
            ko.append('    (keepout "" (polygon %s 0  %s))' % (name, " ".join(pts)))
    dsn = work / "board.dsn"
    if not pcbnew.ExportSpecctraDSN(b, str(dsn)):
        raise SystemExit("FAILED: DSN export")
    t = dsn.read_text()
    for lay in ("In1.Cu", "In2.Cu"):
        t = t.replace("(layer %s\n      (type signal)" % lay, "(layer %s\n      (type power)" % lay)
    i = t.index("    (boundary")
    dsn.write_text(t[:i] + "\n".join(ko) + "\n" + t[i:])
    ses = work / "board.ses"
    if ses.exists():
        ses.unlink()
    log = run(["java", "-Djava.awt.headless=true", "-jar", str(JAR), "-de", str(dsn), "-do", str(ses), "-mp",
               str(passes), "-mt", "8", "--gui.enabled=false"])
    (work / "freerouting.log").write_text(log)
    print("\n".join(l[l.find("INFO") + 5:][:200] for l in log.splitlines()
                    if "finished with state" in l or "Optimization stage completed" in l))
    py = sys.executable
    print(run([py, str(HERE / "import_autoroute.py"), str(pcb), str(ses), "--group", "mount_rework_b"]))
    print(run([py, str(HERE / "close_gaps.py"), str(pcb)]))
    print(run([py, str(HERE / "stitch_gnd_vias.py"), str(pcb)]))


def free_label(b, text, cx, cy, ox, oy, radius=5.0):
    """Move a silkscreen text to the free spot nearest (cx, cy) (K1): no overlap (+0.16 mm) with silkscreen, pads,
    holes or the washer areas r 3.9 mm of H1-H4."""
    import math
    obs = []
    for d in b.GetDrawings():
        if d.GetLayer() == pcbnew.F_SilkS and d.m_Uuid.AsString() != text.m_Uuid.AsString():
            obs.append(d.GetEffectiveShape(pcbnew.F_SilkS))
    holes_at = []
    for f in b.GetFootprints():
        if f.GetReference() in HOLES:
            holes_at.append((T(f.GetPosition().x) - ox, T(f.GetPosition().y) - oy))
        for p in f.Pads():
            if p.IsOnLayer(pcbnew.F_Cu) or p.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH:
                obs.append(p.GetEffectiveShape(pcbnew.F_Cu))
        for t in list(f.GetFields()) + list(f.GraphicalItems()):
            if t.GetLayer() == pcbnew.F_SilkS and (not hasattr(t, "IsVisible") or t.IsVisible()):
                obs.append(t.GetEffectiveShape(pcbnew.F_SilkS))
    cand = sorted(((i * 0.25, j * 0.25) for i in range(-int(radius * 4), int(radius * 4) + 1)
                   for j in range(-int(radius * 4), int(radius * 4) + 1)), key=lambda q: math.hypot(*q))
    for dx, dy in cand:
        text.SetPosition(pcbnew.VECTOR2I(M(cx + dx + ox), M(cy + dy + oy)))
        bb = text.GetBoundingBox()
        x1, y1, x2, y2 = T(bb.GetLeft()) - ox, T(bb.GetTop()) - oy, T(bb.GetRight()) - ox, T(bb.GetBottom()) - oy
        if x1 < 0.5 or y1 < 0.5 or x2 > W_NEW - 0.5 or y2 > 84.5:
            continue
        if any(math.hypot(max(x1 - hx, 0, hx - x2), max(y1 - hy, 0, hy - y2)) < 3.9 for hx, hy in holes_at):
            continue
        sh = text.GetEffectiveShape(pcbnew.F_SilkS)
        if not any(sh.Collide(o, M(0.16)) for o in obs):
            return True
    raise SystemExit("ABORTED: no free spot for silkscreen text %s" % text.GetText())


def cleanup(b):
    """After routing: connector labels follow their connectors, D101 reference only on F.Fab (it sat under the
    moved F101), dangling vias and zero-length tracks left from the removed stubs are deleted."""
    ox, oy = origin(b)
    fps = {f.GetReference(): f for f in b.GetFootprints()}
    texts = {d.GetText(): d for d in b.GetDrawings() if d.GetClass() == "PCB_TEXT" and d.GetLayer() == pcbnew.F_SilkS}
    texts["AKKU 3S"].Move(pcbnew.VECTOR2I(0, M(DY_IN)))
    for lab, ref in (("LED1", "J108"), ("LED2", "J109"), ("LED3", "J110"), ("LED4", "J111"), ("UART", "J112")):
        p = fps[ref].GetPosition()
        free_label(b, texts[lab], T(p.x) - ox + (0 if ref != "J112" else 1.5), 76.3, ox, oy)
    {f.GetReference(): f for f in b.GetFootprints()}["D101"].Reference().SetVisible(False)
    # only what KiCad's own DRC reports as dangling (via_dangling / zero-length track_dangling) is removed
    pcb_tmp = Path(b.GetFileName())
    rep = pcb_tmp.with_suffix(".dangling.json")
    subprocess.run(["/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli", "pcb", "drc", "--severity-all",
                    "--format", "json", "-o", str(rep), str(pcb_tmp)], capture_output=True)
    import json
    ids = set()
    for v in json.load(open(rep))["violations"]:
        if v["type"] == "via_dangling" or (v["type"] == "track_dangling" and
                                           any("length 0.0" in i["description"] for i in v["items"])):
            ids |= {i["uuid"] for i in v["items"]}
    rep.unlink()
    gone = [t for t in b.GetTracks() if t.m_Uuid.AsString() in ids]
    for t in gone:
        b.Remove(t)
    print("labels moved; D101 silk reference hidden; removed %d DRC-dangling vias / zero-length tracks" % len(gone))


def holes(b):
    bd = mh.Board(b)
    for ref, (x, y) in HOLES.items():
        why = bd.check(x, y)
        if why:
            raise SystemExit("ABORTED: %s at (%.1f | %.1f) not free: %s" % (ref, x, y, why))
    ox, oy = origin(b)
    for ref, (x, y) in HOLES.items():
        f = b.FindFootprintByReference(ref)
        f.SetLocked(False)
        f.SetPosition(pcbnew.VECTOR2I(M(x + ox), M(y + oy)))
        f.SetLocked(True)
        print("%s at (%.1f | %.1f)" % (ref, x, y))


def main():
    pcb = Path(sys.argv[1]).resolve()
    if list(pcb.parent.glob("~*.lck")) + list(pcb.parent.glob("*.lck")):
        raise SystemExit("ABORTED: KiCad lock files present")
    step = sys.argv[2]
    if step == "route":
        route(pcb, sys.argv[sys.argv.index("--passes") + 1] if "--passes" in sys.argv else "40")
        return
    b = pcbnew.LoadBoard(str(pcb))
    if step == "prepare":
        prepare(b)
    elif step == "holes":
        holes(b)
    elif step == "cleanup":
        cleanup(b)
        b.Save(str(pcb))              # filling in the same process crashes after Remove(): refill in a second run
        subprocess.run([sys.executable, __file__, str(pcb), "fill"], check=True)
        sys.stdout.flush()
        import os
        os._exit(0)                   # the SWIG teardown after Remove() segfaults; the board is saved and refilled
    elif step == "fill":
        pass
    else:
        raise SystemExit("unknown step")
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    b.Save(str(pcb))


if __name__ == "__main__":
    main()
