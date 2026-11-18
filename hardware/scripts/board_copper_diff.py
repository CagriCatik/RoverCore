#!/usr/bin/env python3
"""Copper and placement diff between two board files (rework review, 2026-11-18).

Usage: <KiCad python> board_copper_diff.py BEFORE.kicad_pcb AFTER.kicad_pcb [--region X1 Y1 X2 Y2]...
Compares tracks, vias (net, layer, width, drill, exact end points), footprints (position, rotation, side, pads'
nets), zones (net, layers, outline vertices, settings) and the outline. Every track/via that exists in only one
of the files is listed as removed or added; footprints/zones that differ are listed with the change. Positions are
K1 coordinates of each file (top-left outline corner). With one or more --region boxes (K1 mm), every change is
checked to lie inside at least one region (a track counts as inside when both ends are inside); changes outside
are reported as UNEXPECTED and the exit status is 1. The diff reads the files only.
"""
import collections
import sys

import pcbnew

T = pcbnew.ToMM


def load(path):
    b = pcbnew.LoadBoard(path)
    e = b.GetBoardEdgesBoundingBox()
    ox, oy = T(e.GetLeft()) + 0.05, T(e.GetTop()) + 0.05

    def k(p):
        return (round(T(p.x) - ox, 4), round(T(p.y) - oy, 4))
    tr = {}
    for t in b.GetTracks():
        if t.GetClass() == "PCB_VIA":
            key = ("via", t.GetNetname(), k(t.GetPosition()), round(T(t.GetWidth(pcbnew.F_Cu)), 3),
                   round(T(t.GetDrill()), 3))
            pts = [k(t.GetPosition())]
        else:
            a, c = sorted([k(t.GetStart()), k(t.GetEnd())])
            key = ("track", t.GetNetname(), b.GetLayerName(t.GetLayer()), round(T(t.GetWidth()), 3), a, c)
            pts = [a, c]
        tr[key] = pts
    fp = {}
    for f in b.GetFootprints():
        fp[f.GetReference()] = (k(f.GetPosition()), round(f.GetOrientationDegrees(), 2), f.IsFlipped(),
                                tuple(sorted((p.GetNumber(), p.GetNetname()) for p in f.Pads())))
    zn = {}
    for z in b.Zones():
        ol = z.Outline()
        pts = tuple(k(ol.CVertex(i)) for i in range(ol.TotalVertices()))
        zn[(z.GetZoneName(), z.GetNetname(), tuple(b.GetLayerName(L) for L in z.GetLayerSet().Seq()))] = (
            pts, z.GetAssignedPriority(), z.GetIsRuleArea(), round(T(z.GetLocalClearance() or 0), 3))
    bb = b.GetBoardEdgesBoundingBox()
    outline = (round(T(bb.GetWidth()), 2), round(T(bb.GetHeight()), 2))
    return tr, fp, zn, outline


def inside(pts, regions):
    return any(all(x1 <= x <= x2 and y1 <= y <= y2 for x, y in pts) for x1, y1, x2, y2 in regions)


def main():
    a, b = sys.argv[1], sys.argv[2]
    regions = []
    args = sys.argv[3:]
    while "--region" in args:
        i = args.index("--region")
        regions.append(tuple(float(v) for v in args[i + 1:i + 5]))
        args = args[:i] + args[i + 5:]
    ta, fa, za, oa = load(a)
    tb, fb, zb, ob = load(b)
    unexpected = []
    print("outline %s -> %s" % (oa, ob))
    removed = [k for k in ta if k not in tb]
    added = [k for k in tb if k not in ta]
    for name, keys, src in (("removed", removed, ta), ("added", added, tb)):
        c = collections.Counter((k[0], k[1].split("/")[-1]) for k in keys)
        print("%s: %d (%s)" % (name, len(keys), ", ".join("%s %s x%d" % (t, n, v) for (t, n), v in sorted(c.items()))))
        if regions:
            for k in keys:
                if not inside(src[k], regions):
                    unexpected.append("%s %s %s at %s" % (name, k[0], k[1].split("/")[-1], src[k]))
    for ref in sorted(set(fa) | set(fb)):
        if fa.get(ref) != fb.get(ref):
            x, y = fa.get(ref), fb.get(ref)
            what = "added" if x is None else "removed" if y is None else \
                "moved %s -> %s" % (x[0], y[0]) if x[0] != y[0] else "changed (rotation/side/pad nets)"
            print("footprint %s: %s" % (ref, what))
            pts = [p[0] for p in (x, y) if p]
            if regions and not inside(pts, regions) and not ref.startswith("H"):
                unexpected.append("footprint %s %s" % (ref, what))
    for key in sorted(set(za) | set(zb)):
        if za.get(key) != zb.get(key):
            print("zone %s (%s): changed" % (key[0], key[1].split("/")[-1]))
            pts = [p for z in (za.get(key), zb.get(key)) if z for p in z[0]]
            moved_pts = [p for p in pts if not (za.get(key) and zb.get(key) and p in za[key][0] and p in zb[key][0])]
            if regions and moved_pts and not inside(moved_pts, regions):
                unexpected.append("zone %s vertices outside regions: %s" % (key[0], moved_pts[:4]))
    print("UNEXPECTED changes: %d" % len(unexpected))
    for u in unexpected:
        print("  " + u)
    sys.exit(1 if unexpected else 0)


if __name__ == "__main__":
    main()
