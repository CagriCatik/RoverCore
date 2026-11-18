#!/usr/bin/env python3
"""Cathode copper for D501 (+5V_DEVKIT) on K1 (routing review, 2026-11-18).

Usage: <KiCad python> d501_cathode_pour.py BOARD.kicad_pcb
Power document 3.11 asks for >= 1 cm2 of cathode copper at D501 (T_j 106 degC at 0.55 A instead of 155 degC with the
standard pad, estimate). After autorouting the net had only its 0.4 mm track. This adds two pours of
+5V_DEVKIT in the space the routed signals leave: F between D501 and the DevKit pin column, B in the free strip
between the vertical traces at x 119.6 and 124.1 (K1 coordinates), joined by vias next to the cathode pad.
Prints the filled area. Coordinates are K1 coordinates and follow a moved board (k1_fixups.board_offset).
"""
from pathlib import Path
import sys

import pcbnew

sys.path.insert(0, str(Path(__file__).resolve().parent))
import k1_fixups as kf  # noqa: E402
import stitch_gnd_vias as sg  # noqa: E402

M, T = pcbnew.FromMM, pcbnew.ToMM
NET = "/Controller/+5V_DEVKIT"
POURS = {"d501_cathode_f": (pcbnew.F_Cu, [(121.3, 50.9), (124.45, 50.9), (124.45, 58.4), (121.3, 58.4)]),
         "d501_cathode_b": (pcbnew.B_Cu, [(119.95, 46.6), (124.0, 46.6), (124.0, 60.4), (119.95, 60.4)])}
VIAS = [(122.9, 52.3), (123.2, 53.9), (122.9, 55.0), (121.7, 55.8)]


def main():
    pcb = Path(sys.argv[1])
    if list(pcb.parent.glob("~*.lck")) + list(pcb.parent.glob("*.lck")):
        raise SystemExit("ABORTED: KiCad lock files present")
    b = pcbnew.LoadBoard(str(pcb))
    if any(z.GetZoneName() in POURS for z in b.Zones()):
        raise SystemExit("ABORTED: pours exist already")
    ox, oy = kf.board_offset(b)
    ni = b.FindNet(NET)
    cu = sg.Copper(b, ni.GetNetCode())
    bad = [v for v in VIAS if not cu.free_via(v[0] + ox, v[1] + oy, 0.3)]
    if bad:
        raise SystemExit("ABORTED: via spots not free: %s" % bad)
    for name, (lay, pts) in POURS.items():
        z = pcbnew.ZONE(b)
        z.SetLayer(lay)
        z.SetNet(ni)
        z.SetZoneName(name)
        z.SetAssignedPriority(3)
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
        z.SetLocalClearance(M(0.2))
        z.SetMinThickness(M(0.25))
        z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
        ol = z.Outline()
        ol.NewOutline()
        for x, y in pts:
            ol.Append(M(x + ox), M(y + oy))
        b.Add(z)
    g = next((x for x in b.Groups() if x.GetName() == "k1_fixups"), None)
    for x, y in VIAS:
        v = pcbnew.PCB_VIA(b)
        v.SetViaType(pcbnew.VIATYPE_THROUGH)
        v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
        v.SetPosition(pcbnew.VECTOR2I(M(x + ox), M(y + oy)))
        v.SetWidth(M(0.6))
        v.SetDrill(M(0.3))
        v.SetNet(ni)
        b.Add(v)
        if g:
            g.AddItem(v)
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    tot = 0
    for z in b.Zones():
        if z.GetZoneName() in POURS:
            a = sum(z.GetFilledPolysList(l).Area() for l in z.GetLayerSet().CuStack()) / 1e12
            tot += a
            print("%s: %.1f mm2 filled" % (z.GetZoneName(), a))
    print("cathode pours together: %.1f mm2 (target >= 100 mm2, power document 3.11)" % tot)
    b.Save(str(pcb))


if __name__ == "__main__":
    main()
