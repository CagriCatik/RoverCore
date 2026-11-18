#!/usr/bin/env python3
"""Silkscreen text to the JLCPCB minimum (fabrication review K1, 2026-11-18).

Usage: <KiCad python> silk_jlc.py BOARD.kicad_pcb enlarge
       <KiCad python> silk_jlc.py BOARD.kicad_pcb resolve DRC.json
JLCPCB (pcb-capabilities, read 2026-11-18): silkscreen text >= 1.0 mm high, >= 0.15 mm stroke; smaller characters are
"unidentifiable". The board used 0.8 mm / 0.12 mm references and 0.8 mm module pin labels.
enlarge: every visible silkscreen text below the minimum gets 1.0 mm height and width and 0.15 mm stroke. Text anchors
         stay; no footprint moves.
resolve: reads a kicad-cli DRC JSON report of the enlarged board. A reference field that now overlaps silkscreen,
         exposed copper or the board edge is hidden on silkscreen when the footprint carries its reference on the Fab
         layer (assembly drawing); a footprint text (module pin label) in conflict moves to the Fab layer of its side.
         Only one text per conflict changes; run DRC and resolve again until no silkscreen conflict is left.
Refuses to run while KiCad lock files exist.
"""
import json
from pathlib import Path
import sys

import pcbnew

M, T = pcbnew.FromMM, pcbnew.ToMM
H, W = 1.0, 0.15
SILK = (pcbnew.F_SilkS, pcbnew.B_SilkS)
CONFLICT = ("silk_overlap", "silk_over_copper", "silk_edge_clearance")


def silk_texts(b):
    for fp in b.GetFootprints():
        for t in list(fp.GetFields()) + [x for x in fp.GraphicalItems() if x.GetClass() == "PCB_TEXT"]:
            if t.GetLayer() in SILK and t.IsVisible() and t.GetText():
                yield fp, t
    for d in b.GetDrawings():
        if d.GetClass() == "PCB_TEXT" and d.GetLayer() in SILK:
            yield None, d


def has_fab_ref(fp):
    for t in list(fp.GetFields()) + list(fp.GraphicalItems()):
        if t.GetClass() in ("PCB_FIELD", "PCB_TEXT") and t.GetLayer() in (pcbnew.F_Fab, pcbnew.B_Fab) \
                and ("REFERENCE" in t.GetText() or t.GetText() == fp.GetReference()):
            return True
    return False


def enlarge(b):
    n = 0
    for _, t in silk_texts(b):
        if T(t.GetTextHeight()) < H - 1e-6 or T(t.GetTextThickness()) < W - 1e-6:
            t.SetTextSize(pcbnew.VECTOR2I(M(max(H, T(t.GetTextWidth()))), M(max(H, T(t.GetTextHeight())))))
            t.SetTextThickness(M(W))
            n += 1
    print("enlarged %d silkscreen texts to >= %.2f mm / %.2f mm" % (n, H, W))


def resolve(b, report):
    d = json.load(open(report))
    texts = {t.m_Uuid.AsString(): (fp, t) for fp, t in silk_texts(b) if fp is not None}
    done = set()
    hidden, moved, kept = [], [], []
    for v in d["violations"]:
        if v["type"] not in CONFLICT:
            continue
        ids = [i["uuid"] for i in v["items"] if i["uuid"] in texts]
        if not ids or any(i in done for i in ids):
            continue                      # one text per conflict is enough; the other stays readable
        fp, t = texts[ids[-1]]
        done.add(ids[-1])
        if t.GetClass() == "PCB_FIELD" and t.IsReference():
            if has_fab_ref(fp):
                t.SetVisible(False)
                hidden.append(fp.GetReference())
            else:
                kept.append(fp.GetReference())
        else:
            t.SetLayer(pcbnew.F_Fab if t.GetLayer() == pcbnew.F_SilkS else pcbnew.B_Fab)
            moved.append("%s:%s" % (fp.GetReference(), t.GetText()))
    print("silkscreen reference hidden (on Fab): %d %s" % (len(hidden), sorted(hidden)))
    print("footprint text moved to Fab: %d %s" % (len(moved), moved))
    print("conflict kept (no Fab reference): %s" % kept)


def main():
    pcb = Path(sys.argv[1])
    if list(pcb.parent.glob("~*.lck")) + list(pcb.parent.glob("*.lck")):
        raise SystemExit("ABORTED: KiCad lock files present")
    b = pcbnew.LoadBoard(str(pcb))
    if sys.argv[2] == "enlarge":
        enlarge(b)
    elif sys.argv[2] == "resolve":
        resolve(b, sys.argv[3])
    else:
        raise SystemExit("unknown step %s" % sys.argv[2])
    b.Save(str(pcb))


if __name__ == "__main__":
    main()
