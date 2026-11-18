#!/usr/bin/env python3
"""Silkscreen around the mounting holes H1-H4 (mounting review, 2026-11-18).

Usage: <KiCad python> mounting_silk.py BOARD.kicad_pcb
- H1-H4: silkscreen reference hidden (it sat on or past the board edge; the reference stays on F.Fab).
- Board label "ENABLE" (for SW501) lay across H3. No free spot for it at 1.5 mm within 15 mm of SW501 (geometric
  search against silkscreen, pads and the washer areas); it now stands vertically left of SW501 at 1.2 mm height,
  0.2 mm stroke (JLCPCB minimum 1.0 / 0.15 mm).
- R301 reference lay under the H2 washer (3.2 mm from the centre): moved right of R301 (first free spot).
Positions are K1 coordinates and absolute, so the script can be run again.
Nothing else moves. Refuses to run while KiCad lock files exist.
"""
from pathlib import Path
import sys

import pcbnew

T, M = pcbnew.ToMM, pcbnew.FromMM
TEXT_AT = (96.0, 80.0)
R301_AT = (9.3, 49.35)


def main():
    pcb = Path(sys.argv[1])
    if list(pcb.parent.glob("~*.lck")) + list(pcb.parent.glob("*.lck")):
        raise SystemExit("ABORTED: KiCad lock files present")
    b = pcbnew.LoadBoard(str(pcb))
    e = b.GetBoardEdgesBoundingBox()
    ox, oy = T(e.GetLeft()) + 0.05, T(e.GetTop()) + 0.05
    for r in ("H1", "H2", "H3", "H4"):
        b.FindFootprintByReference(r).Reference().SetVisible(False)
    t = [d for d in b.GetDrawings() if d.GetClass() == "PCB_TEXT" and d.GetText() == "ENABLE"]
    if len(t) != 1:
        raise SystemExit("ABORTED: ENABLE label not unique")
    t[0].SetTextAngleDegrees(90)
    t[0].SetTextSize(pcbnew.VECTOR2I(M(1.2), M(1.2)))
    t[0].SetTextThickness(M(0.2))
    t[0].SetPosition(pcbnew.VECTOR2I(M(TEXT_AT[0] + ox), M(TEXT_AT[1] + oy)))
    ref = b.FindFootprintByReference("R301").Reference()
    ref.SetPosition(pcbnew.VECTOR2I(M(R301_AT[0] + ox), M(R301_AT[1] + oy)))
    b.Save(str(pcb))
    print("H1-H4 silk references hidden; ENABLE at (%.1f | %.1f), vertical, 1.2 mm; R301 reference at (%.2f | %.2f)"
          % (TEXT_AT + R301_AT))


if __name__ == "__main__":
    main()
