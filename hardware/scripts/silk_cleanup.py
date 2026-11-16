#!/usr/bin/env python3
"""Silkscreen: readable function labels for buttons and external connectors, and reference texts placed so that
they overlap no pad, no other silkscreen and no other part (owner review 2026-11-16).

* Function labels are board texts in the group "function_labels" (the group is replaced on every run; nothing
  else on the board is touched).
* Every reference text gets 0.8 mm height / 0.12 mm stroke (board rule min_text_height 0.8 mm) and is moved to
  the closest free spot around its own courtyard: no pad (+0.2 mm), no silkscreen line or text (+0.15 mm), no other
  part body (courtyard minus 0.3 mm), inside the board (0.5 mm). Parts with the fewest free spots are placed first. A reference that finds
  no free spot is hidden on the silkscreen and listed (it stays on the fabrication layer drawing via the
  footprint's own F.Fab reference, where the library footprint has one).
Footprint positions, copper and library graphics are not changed. Run with the KiCad Python; --board, --dry-run.
"""
from pathlib import Path
import argparse
import math
import sys

import pcbnew

ROOT = Path(__file__).resolve().parents[2]
MM, T = pcbnew.FromMM, pcbnew.ToMM
GROUP = "function_labels"
BOARD = (0.0, 0.0, 150.0, 100.0)
LABELS = {  # ref: (text, height mm); tight spots first, the order matters
    "SW501": ("ENABLE", 1.5), "SW502": ("RESET", 1.5), "SW503": ("BOOT", 1.5), "D502": ("STATUS", 1.2),
    "J104": ("AUX1", 1.2), "J105": ("AUX2", 1.2), "J106": ("ESC", 1.2),
    "J102": ("SERVO V", 1.2), "J103": ("SERVO H", 1.2), "J101": ("AKKU 3S", 1.2), "J107": ("iBUS", 1.2),
    "J108": ("LED1", 1.2), "J109": ("LED2", 1.2), "J110": ("LED3", 1.2), "J111": ("LED4", 1.2), "J112": ("UART", 1.2),
    "J115": ("IMU", 1.2), "J116": ("OLED", 1.2),
}


def rect_of(bb, grow=0.0):
    return (T(bb.GetLeft()) - grow, T(bb.GetTop()) - grow, T(bb.GetRight()) + grow, T(bb.GetBottom()) + grow)


def overlap(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def seg_hits(r, x1, y1, x2, y2, w):
    n = max(2, int(math.hypot(x2 - x1, y2 - y1) / 0.2) + 1)
    rr = (r[0] - w / 2, r[1] - w / 2, r[2] + w / 2, r[3] + w / 2)
    for i in range(n + 1):
        x, y = x1 + (x2 - x1) * i / n, y1 + (y2 - y1) * i / n
        if rr[0] <= x <= rr[2] and rr[1] <= y <= rr[3]:
            return True
    return False


class Obstacles:
    def __init__(self, board, side_layer, silk_layer, skip_texts):
        self.pads, self.yards, self.segs, self.boxes = [], [], [], []
        for fp in board.GetFootprints():
            ref = fp.GetReference()
            for p in fp.Pads():
                if p.IsOnLayer(side_layer):
                    self.pads.append(rect_of(p.GetBoundingBox(), 0.2))
            if fp.GetLayer() == side_layer:
                fp.BuildCourtyardCaches()
                cy = fp.GetCourtyard(pcbnew.F_CrtYd if side_layer == pcbnew.F_Cu else pcbnew.B_CrtYd)
                if cy.OutlineCount():  # the 0.25 mm courtyard margin may carry a neighbour's text, the body not
                    self.yards.append((ref, rect_of(cy.BBox(), -0.3)))
            for g in fp.GraphicalItems():
                if g.GetLayer() != silk_layer:
                    continue
                if isinstance(g, pcbnew.PCB_SHAPE) and g.GetShape() == pcbnew.SHAPE_T_SEGMENT:
                    self.segs.append((T(g.GetStart().x), T(g.GetStart().y), T(g.GetEnd().x), T(g.GetEnd().y),
                                      T(g.GetWidth()) + 0.3))
                elif isinstance(g, pcbnew.PCB_SHAPE) and g.GetShape() == pcbnew.SHAPE_T_RECTANGLE:
                    x1, y1, x2, y2 = T(g.GetStart().x), T(g.GetStart().y), T(g.GetEnd().x), T(g.GetEnd().y)
                    w = T(g.GetWidth()) + 0.3
                    for s in ((x1, y1, x2, y1), (x2, y1, x2, y2), (x2, y2, x1, y2), (x1, y2, x1, y1)):
                        self.segs.append(s + (w,))
                else:
                    self.boxes.append(rect_of(g.GetBoundingBox(), 0.15))
            for fld in fp.GetFields():
                if fld.IsVisible() and fld.GetLayer() == silk_layer and (ref, fld.GetName()) not in skip_texts:
                    self.boxes.append(rect_of(fld.GetBoundingBox(), 0.15))
        for d in board.GetDrawings():
            if d.GetLayer() == silk_layer and not (d.GetParentGroup() and d.GetParentGroup().GetName() == GROUP):
                self.boxes.append(rect_of(d.GetBoundingBox(), 0.15))

    def free(self, r, own):
        if r[0] < BOARD[0] + 0.5 or r[1] < BOARD[1] + 0.5 or r[2] > BOARD[2] - 0.5 or r[3] > BOARD[3] - 0.5:
            return False
        if any(overlap(r, p) for p in self.pads) or any(overlap(r, b) for b in self.boxes):
            return False
        if any(ref != own and overlap(r, y) for ref, y in self.yards):
            return False
        return not any(seg_hits(r, *s) for s in self.segs)


def candidates(fp, w, h, layer):
    fp.BuildCourtyardCaches()
    cy = fp.GetCourtyard(pcbnew.F_CrtYd if layer == pcbnew.F_Cu else pcbnew.B_CrtYd)
    x1, y1, x2, y2 = rect_of(cy.BBox()) if cy.OutlineCount() else rect_of(fp.GetBoundingBox(False))
    cx, cy_ = (x1 + x2) / 2, (y1 + y2) / 2
    out = []
    for gap in (0.0, 0.15, 0.35, 0.6, 1.0, 1.6, 2.4):
        for f in (0.5, 0.3, 0.7, 0.1, 0.9):
            px = x1 + (x2 - x1) * f
            py = y1 + (y2 - y1) * f
            out += [(px, y1 - gap - h / 2), (px, y2 + gap + h / 2), (x1 - gap - w / 2, py), (x2 + gap + w / 2, py)]
    if (x2 - x1) > 3 * w and (y2 - y1) > 3 * h:  # large parts (modules, inductors): inside the own courtyard too
        out += [(cx, y1 + h), (cx, y2 - h), (cx, cy_)]
    return sorted(out, key=lambda p: math.hypot(p[0] - cx, p[1] - cy_))


def place_text(txt, obst, own, cands, angles=(0, 90)):
    for ang in angles:
        txt.SetTextAngleDegrees(ang)
        for x, y in cands:
            txt.SetTextPos(pcbnew.VECTOR2I(MM(x), MM(y)))
            r = rect_of(txt.GetBoundingBox(), 0.05)
            if obst.free(r, own):
                return r
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--board", default=str(ROOT / "RoverCore.kicad_pcb"))
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    pcb = Path(a.board)
    if list(pcb.parent.glob("~*.lck")) + list(pcb.parent.glob("*.lck")):
        raise SystemExit("ABORTED: KiCad lock files present")
    b = pcbnew.LoadBoard(str(pcb))
    old = {}  # labels of a previous run are reused (deleting board items crashes the KiCad 10 Python bindings)
    group = None
    for g in b.Groups():
        if g.GetName() == GROUP:
            group = g
            old = {it.GetText(): it for it in g.GetItems() if isinstance(it, pcbnew.PCB_TEXT)}
    fps = {f.GetReference(): f for f in b.GetFootprints()}
    hidden, placed = [], 0
    for side, silk in ((pcbnew.F_Cu, pcbnew.F_SilkS), (pcbnew.B_Cu, pcbnew.B_SilkS)):
        refs = [f for f in fps.values() if f.GetLayer() == side]
        skip = {(f.GetReference(), "Reference") for f in refs} | {(f.GetReference(), "Value") for f in refs}
        obst = Obstacles(b, side, silk, skip)
        if side == pcbnew.F_Cu:
            if group is None:
                group = pcbnew.PCB_GROUP(b)
                group.SetName(GROUP)
                b.Add(group)
            for ref, (text, hgt) in LABELS.items():  # labels first: they get the best spots
                t = old.pop(text, None)
                new = t is None
                if new:
                    t = pcbnew.PCB_TEXT(b)
                t.SetLayer(silk)
                t.SetText(text)
                t.SetTextSize(pcbnew.VECTOR2I(MM(hgt), MM(hgt)))
                t.SetTextThickness(MM(hgt * 0.17))
                r = None
                for hh in (hgt, 1.0):  # fall back to 1.0 mm where the full height does not fit
                    t.SetTextSize(pcbnew.VECTOR2I(MM(hh), MM(hh)))
                    t.SetTextThickness(MM(max(0.15, hh * 0.17)))
                    r = place_text(t, obst, ref, candidates(fps[ref], 0.9 * hh * len(text), hh, side), angles=(0, 90))
                    if r:
                        break
                if r is None:
                    raise SystemExit("ABORTED: no free spot for label %s at %s" % (text, ref))
                if new:
                    b.Add(t)
                    group.AddItem(t)
                obst.boxes.append(r)
            if old:
                raise SystemExit("ABORTED: labels in group %s that are no longer listed: %s" % (GROUP, sorted(old)))
        # references: fewest candidates first
        work = []
        for f in refs:
            fld = f.Reference()
            fld.SetTextSize(pcbnew.VECTOR2I(MM(0.8), MM(0.8)))
            fld.SetTextThickness(MM(0.12))
            fld.SetLayer(silk)
            fld.SetMirrored(side == pcbnew.B_Cu)
            c = candidates(f, 0.75 * len(f.GetReference()), 1.45, side)
            work.append((f, c))
        def nfree(item):
            f, c = item
            fld = f.Reference()
            n = 0
            for x, y in c[:24]:
                fld.SetTextAngleDegrees(0)
                fld.SetTextPos(pcbnew.VECTOR2I(MM(x), MM(y)))
                n += obst.free(rect_of(fld.GetBoundingBox(), 0.05), f.GetReference())
            return n
        work.sort(key=nfree)
        for f, c in work:
            fld = f.Reference()
            fld.SetVisible(True)
            r = place_text(fld, obst, f.GetReference(), c)
            if r is None:
                fld.SetVisible(False)
                hidden.append(f.GetReference())
            else:
                obst.boxes.append(r)
                placed += 1
            for vf in f.GetFields():
                if not vf.IsReference() and vf.GetLayer() == silk:
                    vf.SetVisible(False)
    print("labels %d, references placed %d, hidden %d" % (len(LABELS), placed, len(hidden)))
    if hidden:
        print("hidden: " + " ".join(sorted(hidden)))
    if a.dry_run:
        print("dry run, not saved")
        return
    b.Save(str(pcb))
    print("saved", pcb)


if __name__ == "__main__":
    sys.exit(main())
