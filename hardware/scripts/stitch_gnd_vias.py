#!/usr/bin/env python3
"""GND return vias (routing step 5, K1): every GND pad or GND track end that KiCad still reports as unconnected
gets its own via to the solid GND planes In1/In2, placed at the nearest free spot and joined with a short stub.

Usage: <KiCad python> stitch_gnd_vias.py BOARD.kicad_pcb [--group NAME]
Free spot: via 0.45/0.25 mm, at least 0.2 mm from any copper of another net on F and B (pads, tracks, vias,
filled zones), stub 0.3 mm likewise; spots inside the board, 0.5 mm from the edge. Runs KiCad DRC to find the
open GND items, repeats until none is left or no spot is found; prints what it could not place.
"""
from pathlib import Path
import json
import math
import subprocess
import sys
import tempfile

import pcbnew

CLI = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
M, T = pcbnew.FromMM, pcbnew.ToMM
VIA, DRILL, STUB, CLR = 0.45, 0.25, 0.2, 0.2


def seg_dist(p, a, b):
    ax, ay, bx, by = a[0], a[1], b[0], b[1]
    dx, dy = bx - ax, by - ay
    L = dx * dx + dy * dy
    t = 0 if L == 0 else max(0, min(1, ((p[0] - ax) * dx + (p[1] - ay) * dy) / L))
    return math.hypot(p[0] - ax - t * dx, p[1] - ay - t * dy)


class Copper:
    def __init__(self, b, gnd):
        self.b, self.gnd = b, gnd
        self.items = []  # (layers, kind, data)
        for fp in b.GetFootprints():
            for p in fp.Pads():
                if p.GetNetCode() == gnd:
                    continue
                bb = p.GetBoundingBox()
                lays = [l for l in (pcbnew.F_Cu, pcbnew.B_Cu) if p.IsOnLayer(l)]
                self.items.append((lays, "box", (T(bb.GetLeft()), T(bb.GetTop()), T(bb.GetRight()), T(bb.GetBottom()))))
                if p.GetDrillSize().x > 0:  # holes block both outer layers
                    self.items.append(([pcbnew.F_Cu, pcbnew.B_Cu], "box", (T(bb.GetLeft()), T(bb.GetTop()),
                                                                          T(bb.GetRight()), T(bb.GetBottom()))))
        for t in b.GetTracks():
            if t.GetNetCode() == gnd:
                continue
            if t.GetClass() == "PCB_VIA":
                p = t.GetPosition()
                self.items.append(([pcbnew.F_Cu, pcbnew.B_Cu], "circ", (T(p.x), T(p.y), T(t.GetWidth(pcbnew.F_Cu)) / 2)))
            elif t.GetLayer() in (pcbnew.F_Cu, pcbnew.B_Cu):
                self.items.append(([t.GetLayer()], "seg", ((T(t.GetStart().x), T(t.GetStart().y)),
                                                           (T(t.GetEnd().x), T(t.GetEnd().y)), T(t.GetWidth()) / 2)))
        self.zones = [z for z in b.Zones() if z.GetNetCode() != gnd]
        e = b.GetBoardEdgesBoundingBox()
        self.edge = (T(e.GetLeft()) + 0.5, T(e.GetTop()) + 0.5, T(e.GetRight()) - 0.5, T(e.GetBottom()) - 0.5)
        # every drilled hole (pads and vias of any net, the own net included): a new via keeps hole spacing
        self.holes = []
        for fp in b.GetFootprints():
            for p in fp.Pads():
                if p.GetDrillSize().x > 0:
                    c = p.GetPosition()
                    self.holes.append((T(c.x), T(c.y), T(max(p.GetSize().x, p.GetSize().y)) / 2))
        for t in b.GetTracks():
            if t.GetClass() == "PCB_VIA":
                c = t.GetPosition()
                self.holes.append((T(c.x), T(c.y), T(t.GetWidth(pcbnew.F_Cu)) / 2))

    def free_via(self, x, y, r):
        if any(math.hypot(x - hx, y - hy) < r + hr + 0.25 for hx, hy, hr in self.holes):
            return False
        return self.free_point(x, y, r, [pcbnew.F_Cu, pcbnew.B_Cu])

    def free_point(self, x, y, r, layers):
        if not (self.edge[0] + r <= x <= self.edge[2] - r and self.edge[1] + r <= y <= self.edge[3] - r):
            return False
        for lays, kind, d in self.items:
            if not any(l in layers for l in lays):
                continue
            if kind == "box":
                dd = math.hypot(max(d[0] - x, 0, x - d[2]), max(d[1] - y, 0, y - d[3]))
            elif kind == "circ":
                dd = math.hypot(x - d[0], y - d[1]) - d[2]
            else:
                dd = seg_dist((x, y), d[0], d[1]) - d[2]
            if dd < r + CLR:
                return False
        pt = pcbnew.VECTOR2I(M(x), M(y))
        for z in self.zones:
            for l in layers:
                if z.IsOnLayer(l) and z.HitTestFilledArea(l, pt, M(r + CLR)):
                    return False
        return True

    def free_stub(self, a, c, layer):
        n = max(2, int(math.hypot(c[0] - a[0], c[1] - a[1]) / 0.1))
        return all(self.free_point(a[0] + (c[0] - a[0]) * i / n, a[1] + (c[1] - a[1]) * i / n, STUB / 2, [layer])
                   for i in range(1, n))


def open_gnd(pcb):
    with tempfile.TemporaryDirectory() as d:
        rep = Path(d) / "drc.json"
        subprocess.run([CLI, "pcb", "drc", "--format", "json", "-o", str(rep), str(pcb)], capture_output=True)
        data = json.loads(rep.read_text())
    pts = []
    for u in data["unconnected_items"]:
        for it in u["items"][:2]:
            if "[GND]" in it["description"]:
                lay = pcbnew.B_Cu if "B.Cu" in it["description"] else pcbnew.F_Cu
                pts.append((it["pos"]["x"], it["pos"]["y"], lay, it["description"]))
    return pts


def main():
    pcb = Path(sys.argv[1])
    name = sys.argv[sys.argv.index("--group") + 1] if "--group" in sys.argv else "gnd_stitch_k1"
    failed, added = [], 0
    for _round in range(4):
        todo = open_gnd(pcb)
        if not todo:
            break
        b = pcbnew.LoadBoard(str(pcb))
        gnd = b.FindNet("GND")
        g = next((x for x in b.Groups() if x.GetName() == name), None)
        if g is None:
            g = pcbnew.PCB_GROUP(b)
            g.SetName(name)
            b.Add(g)
        cu = Copper(b, gnd.GetNetCode())
        done = set()
        for x, y, lay, desc in todo:
            key = (round(x, 1), round(y, 1))
            if key in done:
                continue
            done.add(key)
            spot = None
            on_hole = "PTH pad" in desc  # never drill a via into a through-hole pad
            for r in ((0.6, 0.9, 1.2, 1.6, 2.0, 2.5) if on_hole else (0.0, 0.6, 0.9, 1.2, 1.6, 2.0, 2.5)):
                for k in range(16 if r else 1):
                    a = 2 * math.pi * k / 16
                    vx, vy = x + r * math.cos(a), y + r * math.sin(a)
                    if cu.free_via(vx, vy, VIA / 2) and \
                            (r == 0 or cu.free_stub((x, y), (vx, vy), lay)):
                        spot = (vx, vy)
                        break
                if spot:
                    break
            if not spot:
                failed.append("%s at (%.1f, %.1f)" % (desc[:40], x, y))
                continue
            v = pcbnew.PCB_VIA(b)
            v.SetViaType(pcbnew.VIATYPE_THROUGH)
            v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
            v.SetPosition(pcbnew.VECTOR2I(M(spot[0]), M(spot[1])))
            v.SetWidth(M(VIA))
            v.SetDrill(M(DRILL))
            v.SetNet(gnd)
            b.Add(v)
            g.AddItem(v)
            cu.items.append(([pcbnew.F_Cu, pcbnew.B_Cu], "circ", (spot[0], spot[1], VIA / 2)))
            cu.holes.append((spot[0], spot[1], VIA / 2))
            if spot != (x, y):
                t = pcbnew.PCB_TRACK(b)
                t.SetStart(pcbnew.VECTOR2I(M(x), M(y)))
                t.SetEnd(pcbnew.VECTOR2I(M(spot[0]), M(spot[1])))
                t.SetWidth(M(STUB))
                t.SetLayer(lay)
                t.SetNet(gnd)
                b.Add(t)
                g.AddItem(t)
            added += 1
        pcbnew.ZONE_FILLER(b).Fill(b.Zones())
        b.Save(str(pcb))
        if failed:
            break
    print("GND vias added: %d; not placeable: %d" % (added, len(failed)))
    for f in failed:
        print("  " + f)


if __name__ == "__main__":
    main()
