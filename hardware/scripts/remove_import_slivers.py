#!/usr/bin/env python3
"""Remove sliver tracks that an autorouter import added outside the reworked regions (rework review, 2026-11-18).

Usage: <KiCad python> remove_import_slivers.py BEFORE.kicad_pcb BOARD.kicad_pcb --region X1 Y1 X2 Y2 [...]
A track of BOARD that does not exist in BEFORE, lies (with one end at least) outside every region (K1 mm) and is
shorter than 0.1 mm is removed. Freerouting writes such pieces from existing track ends to pad centres; the
connection existed before. Longer additions outside the regions are only listed. Refill afterwards in a second
process (KiCad Python crashes when zones are filled after Remove()). Refuses to run while lock files exist.
"""
from pathlib import Path
import os
import sys

import pcbnew

T = pcbnew.ToMM


def keys(b):
    e = b.GetBoardEdgesBoundingBox()
    ox, oy = T(e.GetLeft()) + 0.05, T(e.GetTop()) + 0.05
    out = {}
    for t in b.GetTracks():
        if t.GetClass() != "PCB_TRACK":
            continue
        a = (round(T(t.GetStart().x) - ox, 4), round(T(t.GetStart().y) - oy, 4))
        c = (round(T(t.GetEnd().x) - ox, 4), round(T(t.GetEnd().y) - oy, 4))
        out[(t.GetNetname(), t.GetLayer(), round(T(t.GetWidth()), 3)) + tuple(sorted([a, c]))] = (t, [a, c])
    return out


def main():
    before, pcb = sys.argv[1], Path(sys.argv[2])
    if list(pcb.parent.glob("~*.lck")) + list(pcb.parent.glob("*.lck")):
        raise SystemExit("ABORTED: KiCad lock files present")
    args, regions = sys.argv[3:], []
    while "--region" in args:
        i = args.index("--region")
        regions.append(tuple(float(v) for v in args[i + 1:i + 5]))
        args = args[:i] + args[i + 5:]
    old = set(keys(pcbnew.LoadBoard(before)))
    b = pcbnew.LoadBoard(str(pcb))
    drop, keep = [], []
    for k, (t, pts) in keys(b).items():
        if k in old or any(all(x1 <= x <= x2 and y1 <= y <= y2 for x, y in pts) for x1, y1, x2, y2 in regions):
            continue
        (drop if T(t.GetLength()) < 0.1 else keep).append((t, k))
    for t, _ in drop:
        b.Remove(t)
    b.Save(str(pcb))
    print("removed %d slivers (< 0.1 mm) outside the regions" % len(drop))
    for _, k in keep:
        print("kept (longer than 0.1 mm, check):", k[0].split("/")[-1], k[3:])
    sys.stdout.flush()
    os._exit(0)                  # SWIG teardown after Remove() may crash; the board is saved


if __name__ == "__main__":
    main()
