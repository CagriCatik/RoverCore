#!/usr/bin/env python3
"""Larger vias in the +V_SERVO via field next to RS402 (routing review K1, 2026-11-18).

Usage: <KiCad python> servo_via_field.py BOARD.kicad_pcb
current_map.py vservo (11.2 A, blocked servos, estimate): the twelve 0.8/0.4 mm vias share the current unevenly;
the two columns next to the shunt pad carry 0.8-1.8 A each, the far columns 0.4-0.9 A. Those two columns (K1 x 87.4
and 88.6) become 1.0/0.5 mm: about 15 % less current per mm of barrel circumference in the hottest via. Positions stay;
hole spacing to the next column stays >= 0.25 mm. Coordinates are K1 coordinates (k1_fixups.board_offset).
"""
from pathlib import Path
import sys

import pcbnew

sys.path.insert(0, str(Path(__file__).resolve().parent))
import k1_fixups as kf  # noqa: E402

T, M = pcbnew.ToMM, pcbnew.FromMM
VIAS = [(x, y) for x in (87.4, 88.6) for y in (22.8, 24.4, 26.0)]


def main():
    pcb = Path(sys.argv[1])
    if list(pcb.parent.glob("~*.lck")) + list(pcb.parent.glob("*.lck")):
        raise SystemExit("ABORTED: KiCad lock files present")
    b = pcbnew.LoadBoard(str(pcb))
    ox, oy = kf.board_offset(b)
    hit = []
    for t in b.GetTracks():
        if t.GetClass() != "PCB_VIA" or t.GetNetname() != "+V_SERVO":
            continue
        x, y = T(t.GetX()) - ox, T(t.GetY()) - oy
        if any(abs(x - vx) < 0.01 and abs(y - vy) < 0.01 for vx, vy in VIAS):
            t.SetWidth(M(1.0))
            t.SetDrill(M(0.5))
            hit.append((round(x, 2), round(y, 2)))
    if len(hit) != len(VIAS):
        raise SystemExit("ABORTED: found %d of %d vias: %s" % (len(hit), len(VIAS), hit))
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    b.Save(str(pcb))
    print("vias set to 1.0/0.5 mm: %s" % hit)


if __name__ == "__main__":
    main()
