#!/usr/bin/env python3
"""Compact variant K1 (owner instruction 2026-11-16; since then the working variant, applied with --main):
default run: a COPY of RoverCore.kicad_pcb with the outline reduced
to 150 x 85 mm, written to qa/generated/compact/ (generated, not versioned; RoverCore.kicad_pcb stays 150 x 100).

Only unrouted blocks move: controller periphery parts, OLED, IMU, operator buttons, O-37 block, I2C pull-ups and
the interface group. The routed groups (servo stage, input chain, logic supply) and the DevKit stay where they are,
so their copper, vias and return paths are untouched; the DevKit antenna keep-out is therefore unchanged.
Blocks move either rigidly (relative placement kept) or to explicit positions. Afterwards: outline and GND planes
to 85 mm, provisional M3 markers re-chosen, zones refilled, silkscreen re-placed, and the checks of the operator
review (finger access, M3 clearance, USB plug, parts under the plug) printed. Run with the KiCad Python.
"""
from pathlib import Path
import json
import math
import shutil
import subprocess
import sys

import pcbnew

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
OUT = ROOT / "qa/generated/compact"
PCB = OUT / "RoverCore_K1.kicad_pcb"
CLI = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
KPY = sys.executable
H_NEW = 85.0
T, M = pcbnew.ToMM, pcbnew.FromMM

# rigid blocks: refs -> new top-left corner of their joint courtyard box (x1, y1); "bottom" = align y2 instead
RIGID = [
    (["J108", "J109", "J110", "J111", "J112", "D601", "D602", "D603", "D604", "D607", "D608", "R607", "R608", "R609",
      "R610", "R615", "R616", "R617", "TP602"], (2.5, None), ("bottom", 83.0)),          # connector row at the edge
    (["BZ101", "Q601", "D605", "R611", "R612"], (0.8, 60.4), None),                       # buzzer under the logic supply
    (["U601", "C601", "C602", "R601"], (22.0, 64.0), None),                              # LED power switch
    (["U202", "C607", "C603", "R605", "R606", "R604"], (33.0, 64.0), None),              # LED4 level shifter
    (["U602", "C608", "C604", "R602"], (45.5, 64.0), None),                              # UART power
    (["J107", "D606", "R613", "R614", "U203", "C610", "TP601", "U603", "C606", "C605", "R603"], (44.0, 41.0), None),
    (["J116"], (60.5, 41.5), None),                                                       # OLED below the servo rows
    (["J115"], (92.0, 50.8), None),                                                       # IMU below the output stages
]
EXPLICIT = {
    # service buttons beside the logic supply, ENABLE + status LED between OLED and IMU
    "SW502": (40.0, 44.2, 90), "SW503": (40.0, 56.2, 90),
    "SW501": (101.0, 80.0, 0), "D502": (108.5, 79.4, 0), "R504": (108.5, 81.8, 0),
    # O-37 output lock in two rows under the OLED (outside the module outline)
    "R520": (59.0, 77.2, 0), "C512": (62.6, 77.2, 0), "D507": (67.0, 77.4, 0), "U515": (72.5, 77.4, 0),
    "R523": (76.0, 77.6, 90), "U516": (79.5, 77.4, 0), "C513": (84.0, 76.4, 0), "R521": (84.0, 78.6, 0),
    "R522": (84.0, 80.6, 180), "Q507": (72.5, 81.4, -90), "R524": (67.0, 81.6, -90), "TP506": (62.0, 81.4, 0),
    # I2C pull-ups and their test points next to ENABLE
    "R801": (114.3, 77.4, 0), "R802": (114.3, 79.2, 0), "R803": (114.3, 81.0, 0),
    "TP801": (118.4, 77.6, 0), "TP802": (118.4, 81.0, 0),
    # VBAT measurement in two rows between IMU and ENABLE (was under the USB plug, below y 85)
    "R508": (93.8, 71.6, 180), "Q505": (97.6, 71.6, 0), "R505": (101.4, 71.6, 0), "R506": (104.6, 71.6, 0),
    "C504": (107.8, 71.6, 0), "R507": (111.0, 71.6, 0), "D506": (115.0, 71.6, 0),
    "R509": (93.8, 75.0, 180), "Q506": (97.6, 75.0, 0), "TP505": (111.5, 75.2, 0),
    # 3V3 bulk next to ENABLE; latch U506 and the test points into the right column above, so the bottom-right
    # corner is free for an M3 marker
    "C501": (102.5, 75.0, 0), "C502": (106.5, 75.0, 0),
    "U506": (143.0, 66.5, 0), "C508": (146.7, 66.8, -90), "R519": (143.0, 69.6, 180), "TP501": (146.0, 70.2, 0),
    "TP502": (141.8, 73.0, 0), "TP504": (145.3, 73.0, 0),
}
HOLE_SEARCH = [  # (name, search box) for the provisional M3 markers of K1
    ("oben links", (17.0, 4.0, 30.0, 6.0)),
    ("links Mitte", (4.0, 32.0, 10.0, 46.0)),
    ("unten rechts", (144.0, 79.0, 146.0, 81.0)),
    ("unten Mitte", (86.0, 70.0, 92.0, 81.0)),
    ("oben Mitte", (52.0, 4.0, 62.0, 8.0)),
]
BUTTONS = {"SW501": "ENABLE", "SW502": "RESET", "SW503": "BOOT"}
TALL = ["L401", "C406", "C407", "C101", "J101", "J102", "J103", "J104", "J105", "J106", "J107", "BZ101", "L301"]
USB = [("Micro-USB UART", (124.7, 63.84, 135.7, 93.84)), ("Micro-USB USB", (138.1, 63.84, 149.1, 93.84))]


def yard(fp):
    fp.BuildCourtyardCaches()
    cy = fp.GetCourtyard(pcbnew.F_CrtYd if fp.GetLayer() == pcbnew.F_Cu else pcbnew.B_CrtYd)
    bb = cy.BBox() if cy.OutlineCount() else fp.GetBoundingBox(False)
    return (T(bb.GetLeft()), T(bb.GetTop()), T(bb.GetRight()), T(bb.GetBottom()))


def fab(fp):
    xs, ys = [], []
    for g in fp.GraphicalItems():
        if g.GetLayer() == pcbnew.F_Fab and isinstance(g, pcbnew.PCB_SHAPE):
            bb = g.GetBoundingBox()
            xs += [T(bb.GetLeft()), T(bb.GetRight())]
            ys += [T(bb.GetTop()), T(bb.GetBottom())]
    return (min(xs), min(ys), max(xs), max(ys))


def rdist(px, py, r):
    return math.hypot(max(r[0] - px, 0, px - r[2]), max(r[1] - py, 0, py - r[3]))


def has_copper(b, fp):
    for t in b.GetTracks():
        pts = [t.GetPosition()] if t.GetClass() == "PCB_VIA" else [t.GetStart(), t.GetEnd()]
        for p in fp.Pads():
            if t.GetNetCode() == p.GetNetCode() > 0 and any(p.HitTest(q) for q in pts):
                return True
    return False


def apply(b):
    fps = {f.GetReference(): f for f in b.GetFootprints()}
    moved = set()
    for refs, (x1, y1), align in RIGID:
        boxes = [yard(fps[r]) for r in refs]
        bx1, by1 = min(x[0] for x in boxes), min(x[1] for x in boxes)
        by2 = max(x[3] for x in boxes)
        dx = x1 - bx1
        dy = (align[1] - by2) if align else (y1 - by1)
        for r in refs:
            fps[r].Move(pcbnew.VECTOR2I(M(dx), M(dy)))
            moved.add(r)
    for r, (x, y, rot) in EXPLICIT.items():
        fps[r].SetPosition(pcbnew.VECTOR2I(M(x), M(y)))
        fps[r].SetOrientationDegrees(rot)
        moved.add(r)
    for r in moved:
        if has_copper(b, fps[r]):
            raise SystemExit("ABORTED: %s has copper attached" % r)
    return moved


def outline(b):
    for d in b.GetDrawings():
        if d.GetLayer() == pcbnew.Edge_Cuts and isinstance(d, pcbnew.PCB_SHAPE):
            e = d.GetEnd()
            d.SetEnd(pcbnew.VECTOR2I(e.x, M(H_NEW)))
        elif d.GetLayer() == pcbnew.Dwgs_User:          # group frames of the 150 x 100 layout: hidden in K1
            d.SetLayer(pcbnew.User_9)
        elif d.GetLayer() == pcbnew.Cmts_User and isinstance(d, pcbnew.PCB_SHAPE):
            d.SetLayer(pcbnew.User_9)                      # old M3 markers; new ones below
    for z in b.Zones():
        ol = z.Outline()
        for i in range(ol.TotalVertices()):
            v = ol.CVertex(i)
            if T(v.y) > H_NEW:
                ol.SetVertex(i, pcbnew.VECTOR2I(v.x, M(H_NEW)))


def holes(b):
    yards = [yard(f) for f in b.GetFootprints()]
    out = []
    for name, (x1, y1, x2, y2) in HOLE_SEARCH:
        best = None
        x = x1
        while x <= x2:
            y = y1
            while y <= y2:
                d = min(rdist(x, y, r) for r in yards)
                if best is None or d > best[0]:
                    best = (d, x, y)
                y += 0.5
            x += 0.5
        out.append((name, best[1], best[2], best[0]))
        c = pcbnew.PCB_SHAPE(b, pcbnew.SHAPE_T_CIRCLE)
        c.SetLayer(pcbnew.Cmts_User)
        c.SetCenter(pcbnew.VECTOR2I(M(best[1]), M(best[2])))
        c.SetEnd(pcbnew.VECTOR2I(M(best[1] + 1.6), M(best[2])))
        c.SetWidth(M(0.15))
        b.Add(c)
    return out


def checks(b, hole_list):
    fps = {f.GetReference(): f for f in b.GetFootprints()}
    env = [("DevKit", fab(fps["U501"])), ("OLED", fab(fps["J116"])), ("IMU", fab(fps["J115"]))] + USB
    tall = env + [(r, yard(fps[r])) for r in TALL]
    res = {"buttons": [], "holes": [], "under_usb": [], "outline": (150.0, H_NEW)}
    for ref, name in BUTTONS.items():
        p = fps[ref].GetPosition()
        px, py = T(p.x), T(p.y)
        n, d = min(((n, rdist(px, py, r)) for n, r in tall), key=lambda a: a[1])
        hole = min(rdist(hx, hy, yard(fps[ref])) for _, hx, hy, _ in hole_list)
        res["buttons"].append((name, round(px, 1), round(py, 1), n, round(d, 1), round(hole, 1)))
    for name, hx, hy, d in hole_list:
        res["holes"].append((name, hx, hy, round(d, 2), round(min(hx, hy, 150 - hx, H_NEW - hy), 2)))
    for f in b.GetFootprints():
        y = yard(f)
        for n, r in USB:
            if y[0] < r[2] and r[0] < y[2] and y[1] < r[3] and r[1] < y[3] and f.GetReference() != "U501":
                res["under_usb"].append(f.GetReference())
    res["under_usb"] = sorted(set(res["under_usb"]))
    res["usb_over_board"] = round(H_NEW - 63.84, 1)
    res["usb_overhang"] = round(63.84 + 30.0 - H_NEW, 1)
    return res


def drc(pcb):
    rep = OUT / (pcb.stem + "_drc.json")
    subprocess.run([CLI, "pcb", "drc", "--format", "json", "-o", str(rep), str(pcb)], capture_output=True)
    d = json.loads(rep.read_text())
    types = {}
    for v in d["violations"]:
        types[v["type"]] = types.get(v["type"], 0) + 1
    length = 0.0
    for u in d["unconnected_items"]:
        a, c = u["items"][:2]
        length += math.hypot(a["pos"]["x"] - c["pos"]["x"], a["pos"]["y"] - c["pos"]["y"])
    return types, len(d["unconnected_items"]), round(length)


def adopt_main():
    """--main: apply K1 to RoverCore.kicad_pcb itself (working variant since 2026-11-16). The 150 x 100 state stays
    reproducible from commit 0b50567 (git show 0b50567:RoverCore.kicad_pcb)."""
    if list(ROOT.glob("~*.lck")) + list(ROOT.glob("*.lck")):
        raise SystemExit("ABORTED: KiCad lock files present")
    pcb = ROOT / "RoverCore.kicad_pcb"
    b = pcbnew.LoadBoard(str(pcb))
    e = b.GetBoardEdgesBoundingBox()
    if abs(T(e.GetHeight()) - 100.0) > 0.5:
        raise SystemExit("ABORTED: board outline is not 150 x 100 mm; K1 was applied already")
    moved = apply(b)
    outline(b)
    hl = holes(b)
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    b.Save(str(pcb))
    s = subprocess.run([KPY, str(ROOT / "hardware/scripts/silk_cleanup.py")], capture_output=True, text=True)
    if s.returncode:
        raise SystemExit("silk_cleanup failed: " + s.stdout[-300:] + s.stderr[-300:])
    print("K1 applied to %s: %d footprints moved; M3 markers %s" % (pcb, len(moved), [(h[1], h[2]) for h in hl]))


def main():
    if list(ROOT.glob("~*.lck")) + list(ROOT.glob("*.lck")):
        raise SystemExit("ABORTED: KiCad lock files present")
    OUT.mkdir(parents=True, exist_ok=True)
    shutil.copy(ROOT / "RoverCore.kicad_pcb", PCB)
    shutil.copy(ROOT / "RoverCore.kicad_pro", PCB.with_suffix(".kicad_pro"))
    for name in ("fp-lib-table", "sym-lib-table"):   # project libraries resolve via ${KIPRJMOD}/hardware
        if (ROOT / name).exists():
            shutil.copy(ROOT / name, OUT / name)
    if not (OUT / "hardware").exists():
        (OUT / "hardware").symlink_to(ROOT / "hardware")
    b = pcbnew.LoadBoard(str(PCB))
    moved = apply(b)
    outline(b)
    hl = holes(b)
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    b.Save(str(PCB))
    s = subprocess.run([KPY, str(ROOT / "hardware/scripts/silk_cleanup.py"), "--board", str(PCB)], capture_output=True,
                       text=True)
    if s.returncode:
        raise SystemExit("silk_cleanup failed: " + s.stdout[-300:] + s.stderr[-300:])
    b = pcbnew.LoadBoard(str(PCB))
    res = checks(b, hl)
    res["moved"] = len(moved)
    res["drc_K1"] = drc(PCB)
    res["drc_base"] = drc(ROOT / "RoverCore.kicad_pcb")
    (OUT / "K1_checks.json").write_text(json.dumps(res, indent=1, ensure_ascii=False))
    print(json.dumps(res, indent=1, ensure_ascii=False))


if __name__ == "__main__" and "--main" in sys.argv:
    adopt_main()
elif __name__ == "__main__" and "--compare" not in sys.argv:
    main()


def compare():
    """Identical populated views of both variants (render_populated_review) and side-by-side composites."""
    import render_populated_review as rp
    iso = ["--side", "top", "--rotate", "-45,0,45", "--zoom", "0.9"]
    views = [("top", ["--side", "top"]), ("iso", iso), ("bottom", ["--side", "bottom"])]
    sets = {"base": (ROOT / "RoverCore.kicad_pcb", OUT / "views_150x100", "150 x 100 mm (Stand main) - "),
            "K1": (PCB, OUT / "views_K1_150x85", "K1 150 x 85 mm (Boardkopie) - ")}
    for key, (src, out, label) in sets.items():
        out.mkdir(parents=True, exist_ok=True)
        pop = rp.build(True, src, out)
        rp.render(pop, "populated", views, out, label)
        bare = rp.build(False, src, out)
        rp.render(bare, "without_modules", [("top", ["--side", "top"]), ("iso", iso)], out, label)
        rp.status_list(src, out)
    for view in ("populated_top", "populated_iso", "without_modules_top", "without_modules_iso", "populated_bottom"):
        a = (OUT / "views_150x100" / (view + ".png"))
        b = (OUT / "views_K1_150x85" / (view + ".png"))
        svg = ['<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="2400" '
               'height="3720"><rect width="2400" height="3720" fill="white"/>',
               '<text x="30" y="50" font-family="Helvetica" font-size="40">Vergleich %s: oben 150 x 100 mm, unten K1 '
               '150 x 85 mm (gleiche Ansicht, gleicher Renderer)</text>' % view,
               '<image xlink:href="%s" x="0" y="70" width="2400" height="1830"/>' % a,
               '<image xlink:href="%s" x="0" y="1890" width="2400" height="1830"/>' % b, "</svg>"]
        s = OUT / ("compare_%s.svg" % view)
        s.write_text("\n".join(svg))
        subprocess.run(["rsvg-convert", "-o", str(OUT / ("compare_%s.png" % view)), str(s)], check=True)
    print("compare images in", OUT)


if __name__ == "__main__" and "--compare" in sys.argv:
    compare()
