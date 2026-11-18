#!/usr/bin/env python3
"""Project footprint MountingHole_3.2mm_M3_NPTH_Keepout (mounting review, 2026-11-18).

Usage: <KiCad python> make_mounting_hole.py
Starts from KiCad's MountingHole_3.2mm_M3 (NPTH 3.2 mm, ISO 273 fine clearance for M3) and adds what the board needs
around a screw (dimensions: own assumptions, see mounting_holes.py):
- copper keep-out rule areas inside the footprint: r 3.8 mm on F.Cu/B.Cu (washer ISO 7089 Ø 7.0 mm, hex standoff
  5.5 mm AF = Ø 6.35 mm across corners, + 0.3 mm), r 2.0 mm on In1/In2 (hole + 0.4 mm). No tracks, vias or pours;
- courtyard r 3.8 mm on both sides (washer / standoff seat), so DRC flags parts placed into it;
- Cmts.User outlines: screw head Ø 5.7 mm and washer Ø 7.0 mm (top), standoff Ø 6.35 mm (bottom, B.Fab).
Written to hardware/libraries/footprints/ProjectFootprints.pretty.
"""
import math
from pathlib import Path

import pcbnew

ROOT = Path(__file__).resolve().parents[2]
SRC = "/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints/MountingHole.pretty"
LIB = str(ROOT / "hardware/libraries/footprints/ProjectFootprints.pretty")
NAME = "MountingHole_3.2mm_M3_NPTH_Keepout"
M = pcbnew.FromMM
R_OUT, R_IN, R_CY = 3.8, 2.0, 3.8


def circle(fp, r, layer, width):
    s = pcbnew.PCB_SHAPE(fp, pcbnew.SHAPE_T_CIRCLE)
    s.SetCenter(pcbnew.VECTOR2I(0, 0))
    s.SetEnd(pcbnew.VECTOR2I(M(r), 0))
    s.SetLayer(layer)
    s.SetWidth(M(width))
    fp.Add(s)


def keepout(fp, r, layers, name):
    z = pcbnew.ZONE(fp)
    z.SetIsRuleArea(True)
    z.SetDoNotAllowTracks(True)
    z.SetDoNotAllowVias(True)
    z.SetDoNotAllowZoneFills(True)
    z.SetDoNotAllowPads(False)
    z.SetDoNotAllowFootprints(False)
    ls = pcbnew.LSET()
    for L in layers:
        ls.AddLayer(L)
    z.SetLayerSet(ls)
    z.SetZoneName(name)
    ol = pcbnew.SHAPE_POLY_SET()
    ol.NewOutline()
    for k in range(48):
        a = 2 * math.pi * k / 48
        ol.Append(M(r * math.cos(a)), M(r * math.sin(a)))
    z.SetOutline(ol)
    fp.Add(z)


def main():
    fp = pcbnew.FootprintLoad(SRC, "MountingHole_3.2mm_M3")
    fp.SetFPID(pcbnew.LIB_ID("ProjectFootprints", NAME))
    fp.SetLibDescription("Mounting hole M3, NPTH 3.2 mm, copper keep-out r 3.8 mm outer / 2.0 mm inner, courtyard "
                         "r 3.8 mm both sides (washer ISO 7089, standoff 5.5 AF); RoverCore make_mounting_hole.py")
    fp.SetKeywords("mountinghole M3 NPTH keepout")
    for g in list(fp.GraphicalItems()):
        if g.GetLayer() in (pcbnew.F_CrtYd, pcbnew.Cmts_User):
            fp.Remove(g)
    circle(fp, R_CY, pcbnew.F_CrtYd, 0.05)
    circle(fp, R_CY, pcbnew.B_CrtYd, 0.05)
    circle(fp, 2.85, pcbnew.Cmts_User, 0.1)       # screw head Ø 5.7
    circle(fp, 3.5, pcbnew.Cmts_User, 0.1)        # washer Ø 7.0
    circle(fp, 3.175, pcbnew.B_Fab, 0.1)          # standoff Ø 6.35 across corners
    keepout(fp, R_OUT, (pcbnew.F_Cu, pcbnew.B_Cu), "m3_keepout_outer")
    keepout(fp, R_IN, (pcbnew.In1_Cu, pcbnew.In2_Cu), "m3_keepout_inner")
    pcbnew.PCB_IO_KICAD_SEXPR().FootprintSave(LIB, fp)
    print("written %s/%s.kicad_mod" % (LIB, NAME))


if __name__ == "__main__":
    main()
