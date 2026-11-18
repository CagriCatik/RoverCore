#!/usr/bin/env python3
"""M3 mounting holes for K1: free-position search and placement (mounting review, 2026-11-18).

Usage: <KiCad python> mounting_holes.py BOARD.kicad_pcb search
       <KiCad python> mounting_holes.py BOARD.kicad_pcb place
No chassis or enclosure dimensions exist in the repository, so the positions are a PROVISIONAL proposal.

Assumptions (estimates, own choices; datasheet values where named):
- M3 screw, clearance hole 3.2 mm (ISO 273 fine), NPTH. Head ISO 7380 / ISO 4762 Ø 5.5-5.7 mm, washer ISO 7089
  Ø 7.0 mm, hex standoff M3 5.5 mm AF (Ø 6.35 mm across corners) on the bottom.
- Copper keep-out (rule area, no tracks/vias/pads/zones): r 3.8 mm on F.Cu and B.Cu (washer / standoff 3.5 mm + 0.3),
  r 2.0 mm on In1/In2 (hole 1.6 mm + 0.4). Only GND pours may be cut by it; any other copper rejects the spot.
- Component clearance from the hole centre to the nearest courtyard (both sides): >= 4.5 mm, >= 5.5 mm for tall
  parts (tool access), and >= 5.5 mm to the plug-in module / USB envelopes (render_placement_review.ENVELOPES).
- Hole centre >= 4.0 mm from the board edge (washer fully supported).
- Power paths: a spot is rejected when copper of a regulator or high-current net (PWR) lies within 5.0 mm on any
  layer, so no keep-out ever comes near a regulator or high-current conductor. Signal copper only has to stay
  outside the keep-out (it is never rerouted).
search: scans the board on a 0.5 mm grid and prints, for each corner, the feasible spot closest to it.
place:  checks POS again, sets footprints H1-H4 (ProjectFootprints:MountingHole_3.2mm_M3_NPTH_Keepout, brought in
        from the schematic by build_board.py; the keep-out rule areas are part of the footprint) to POS, locks
        them, removes the old Cmts.User marker circles (r 1.6 mm) and refills the zones.
"""
import math
from pathlib import Path
import sys

import pcbnew

sys.path.insert(0, str(Path(__file__).resolve().parent))
import render_placement_review as rp  # noqa: E402

T, M = pcbnew.ToMM, pcbnew.FromMM
R_OUT, R_IN, R_PWR = 3.8, 2.0, 5.0
CY_LOW, CY_TALL, ENV_MIN, EDGE = 4.5, 5.5, 5.5, 4.0
TALL = ("J", "U501", "C101", "C406", "C407", "L301", "L401", "F101", "SW", "BZ")
CU = [pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.B_Cu]
PWR = {"VBAT_IN", "VBAT_FUSED", "VBAT_PROT", "SW_5V", "SW_SERVO", "ISNS_PWR", "VSERVO_REG", "+V_SERVO",
       "BOOT_5V", "SENSE_P", "SENSE_N", "SENSE_P_K", "+5V"}   # regulator and high-current nets
# SUPERSEDED (variant B, 2026-11-18): first provisional positions, kept for the record; see mount_rework_b.py.
# Search result 2026-11-18 (K1 coordinates). Top-right is impossible: the DevKit with its antenna reaches the edge.
# H4 lies under the estimated USB plug/cable envelope: no collision with the screw head (plug 10.4-17.4 mm high),
# but the screw has to go in before the USB cable is plugged (ENV_EXEMPT).
POS = {"H1": (21.0, 4.0), "H2": (4.0, 43.0), "H3": (91.0, 81.0), "H4": (146.0, 81.0)}
ENV_EXEMPT = {"H4": "Micro-USB USB"}


def is_pwr(net):
    return net.split("/")[-1] in PWR


class Board:
    def __init__(self, b):
        self.b = b
        e = b.GetBoardEdgesBoundingBox()
        self.ox, self.oy = T(e.GetLeft()) + 0.05, T(e.GetTop()) + 0.05
        self.w, self.h = T(e.GetWidth()) - 0.1, T(e.GetHeight()) - 0.1
        self.items = []                        # (bbox mm, kind, net, layer, shape)
        for t in b.GetTracks():
            for L in CU:
                if t.IsOnLayer(L):
                    self.items.append((t.GetBoundingBox(), "track", t.GetNetname(), L, t.GetEffectiveShape(L)))
        for fp in b.GetFootprints():
            if fp.GetReference().startswith("H"):
                continue
            for p in fp.Pads():
                for L in CU:
                    if p.IsOnLayer(L) or p.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH:
                        self.items.append((p.GetBoundingBox(), "pad", p.GetNetname(), L, p.GetEffectiveShape(L)))
        self.zones = [(z.GetNetname(), L, z.GetFilledPolysList(L)) for z in b.Zones() if not z.GetIsRuleArea()
                      for L in CU if z.IsOnLayer(L) and z.GetNetname() != "GND"]   # non-GND pours: all power
        self.cys = []
        for fp in b.GetFootprints():
            if fp.GetReference().startswith("H"):
                continue
            fp.BuildCourtyardCaches()
            for L in (pcbnew.F_CrtYd, pcbnew.B_CrtYd):
                cy = fp.GetCourtyard(L)
                if cy.OutlineCount():
                    tall = fp.GetReference().startswith(TALL)
                    self.cys.append((fp.GetReference(), cy, CY_TALL if tall else CY_LOW))
        self.env = []
        for ref, lab, _z, rect in rp.ENVELOPES:
            r = rect or [v - o for v, o in zip(rp.fab_rect(b, ref), (self.ox, self.oy, self.ox, self.oy))]
            self.env.append((lab, r))

    def check(self, x, y):
        """None if (x, y) in K1 coordinates is feasible, else the first reason."""
        if min(x, y, self.w - x, self.h - y) < EDGE:
            return "edge"
        c = pcbnew.VECTOR2I(M(x + self.ox), M(y + self.oy))
        for bb, kind, net, L, sh in self.items:
            r = R_OUT if L in (pcbnew.F_Cu, pcbnew.B_Cu) else R_IN
            pw = is_pwr(net)
            lim = max(r, R_PWR if pw else 0)
            if abs(T(bb.Centre().x) - x - self.ox) > T(bb.GetWidth()) / 2 + lim or \
               abs(T(bb.Centre().y) - y - self.oy) > T(bb.GetHeight()) / 2 + lim:
                continue
            if pw and sh.Collide(c, M(R_PWR)):
                return "power copper %s" % net.split("/")[-1]
            if sh.Collide(c, M(r)):
                return "%s %s" % (kind, net.split("/")[-1] or "-")
        for net, L, poly in self.zones:
            if poly.OutlineCount() and poly.Collide(c, M(R_PWR)):
                return "power zone %s" % net.split("/")[-1]
        for ref, cy, lim in self.cys:
            if cy.Collide(c, M(lim)):
                return "courtyard %s" % ref
        for lab, (x1, y1, x2, y2) in self.env:
            if math.hypot(max(x1 - x, 0, x - x2), max(y1 - y, 0, y - y2)) < ENV_MIN:
                return "envelope %s" % lab[:20]
        return None


def search(bd):
    corners = {"top-left": (0, 0), "top-right": (bd.w, 0), "bottom-left": (0, bd.h), "bottom-right": (bd.w, bd.h)}
    best = {k: None for k in corners}
    step = 0.5
    ys = [EDGE + i * step for i in range(int((bd.h - 2 * EDGE) / step) + 1)]
    xs = [EDGE + i * step for i in range(int((bd.w - 2 * EDGE) / step) + 1)]
    ok = []
    for y in ys:
        for x in xs:
            # only the corner quadrants are scanned (spread); the middle never wins
            if bd.check(x, y) is None:
                ok.append((x, y))
    for k, (cx, cy) in corners.items():
        cand = sorted((p for p in ok if (p[0] < bd.w / 2) == (cx == 0) and (p[1] < bd.h / 2) == (cy == 0)),
                      key=lambda p: math.hypot(p[0] - cx, p[1] - cy))
        best[k] = cand[0] if cand else None
    for k, p in best.items():
        print("%-12s %s" % (k, "(%.1f | %.1f), %.1f mm from the corner" % (p[0], p[1], math.hypot(
            p[0] - corners[k][0], p[1] - corners[k][1])) if p else "no feasible spot"))
    return best


def main():
    pcb = Path(sys.argv[1])
    b = pcbnew.LoadBoard(str(pcb))
    bd = Board(b)
    if sys.argv[2] == "search":
        search(bd)
        for x, y in rp.holes_on_board(b):
            print("current hole (%.1f | %.1f): %s" % (x, y, bd.check(x, y) or "feasible"))
        return
    if list(pcb.parent.glob("~*.lck")) + list(pcb.parent.glob("*.lck")):
        raise SystemExit("ABORTED: KiCad lock files present")
    raise SystemExit("place is superseded: the corner holes of variant B are set by mount_rework_b.py holes")
    for ref, (x, y) in POS.items():
        why = bd.check(x, y)
        if why and not (ref in ENV_EXEMPT and why.startswith("envelope " + ENV_EXEMPT[ref][:11])):
            raise SystemExit("ABORTED: %s at (%.1f | %.1f) not free: %s" % (ref, x, y, why))
    for ref, (x, y) in POS.items():
        fp = b.FindFootprintByReference(ref)
        if fp is None:
            raise SystemExit("ABORTED: %s missing - run build_board.py first" % ref)
        fp.SetPosition(pcbnew.VECTOR2I(M(x + bd.ox), M(y + bd.oy)))
        fp.SetOrientationDegrees(0)
        fp.SetLocked(True)
        print("%s placed at (%.1f | %.1f), locked" % (ref, x, y))
    old = [d for d in b.GetDrawings() if d.GetLayer() == pcbnew.Cmts_User and d.GetClass() == "PCB_SHAPE"
           and d.GetShape() == pcbnew.SHAPE_T_CIRCLE and abs(T(d.GetRadius()) - 1.6) < 0.01]
    for d in old:
        b.Remove(d)
    print("removed %d provisional Cmts.User markers" % len(old))
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    b.Save(str(pcb))


if __name__ == "__main__":
    main()
