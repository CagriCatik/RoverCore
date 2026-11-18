#!/usr/bin/env python3
"""Solid plane connection for the high-current THT GND pins (routing review K1, 2026-11-18).

Usage: <KiCad python> power_pad_connections.py BOARD.kicad_pcb
current_map.py gnd_servo showed that the servo return current reaches the battery connector only through the inner
GND planes, and that the GND pins of J101 (9.35 A, estimate), J102 and J103 (5.1 A each) were joined to In1/In2 by
the zone default thermal relief (4 spokes x 0.5 mm per layer). These pads get a local "solid" zone connection; all
other pads keep the zone setting. Soldering note: the pins then sink more heat into two planes (preheat / larger tip).
Refuses to run while KiCad lock files exist; zones are refilled.
"""
from pathlib import Path
import sys

import pcbnew

PADS = [("J101", "1"), ("J102", "3"), ("J103", "3")]


def main():
    pcb = Path(sys.argv[1])
    if list(pcb.parent.glob("~*.lck")) + list(pcb.parent.glob("*.lck")):
        raise SystemExit("ABORTED: KiCad lock files present")
    b = pcbnew.LoadBoard(str(pcb))
    for ref, num in PADS:
        f = b.FindFootprintByReference(ref)
        p = next(p for p in f.Pads() if p.GetNumber() == num)
        if p.GetNetname() != "GND":
            raise SystemExit("ABORTED: %s.%s is %s, not GND" % (ref, num, p.GetNetname()))
        p.SetLocalZoneConnection(pcbnew.ZONE_CONNECTION_FULL)
        print("%s.%s: solid zone connection" % (ref, num))
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    b.Save(str(pcb))


if __name__ == "__main__":
    main()
