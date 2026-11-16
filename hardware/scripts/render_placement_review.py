#!/usr/bin/env python3
"""Placement review images, top and bottom side separately, with KiCad's own ratsnest including GND.

Copper (tracks, vias and the filled zones of the outer layer of the view) is drawn under the parts: own side
solid, the other outer layer faint; the inner GND planes are not drawn. The ratsnest is not computed here: it is the list of unconnected item pairs from `kicad-cli pcb drc`
(KiCad connectivity, the same lines the PCB editor draws). GND is drawn in black, the critical power, switch,
gate-drive and feedback nets in colour, all other nets thin grey. Each view exists for the top side (seen from
above) and the bottom side (seen from below, mirrored); parts of the other side are shown faint.
Run with the KiCad Python (pcbnew); writes SVG (+ PNG if rsvg-convert exists) to qa/generated/placement/.
Usage: <KiCad python> hardware/scripts/render_placement_review.py
"""
from pathlib import Path
import json
import re
import shutil
import subprocess
import tempfile

import pcbnew

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "qa/generated/placement"
CLI = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
T = pcbnew.ToMM
SCALE = 12.0  # px per mm
COLOURS = {
    "GND": "#000000",
    "/Power/VBAT_IN": "#d62728", "/Power/VBAT_FUSED": "#d62728", "/Power/VBAT_PROT": "#ff7f0e",
    "/ServoPower/SW_SERVO": "#9467bd", "/ServoPower/ISNS_PWR": "#9467bd", "/ServoPower/VSERVO_REG": "#2ca02c",
    "+V_SERVO": "#2ca02c", "/LogicPower/SW_5V": "#9467bd", "+5V": "#1f77b4", "+3V3": "#17becf",
    "/ServoPower/TG_SERVO": "#e377c2", "/ServoPower/BG_SERVO": "#e377c2", "/ServoPower/BOOST_SERVO": "#e377c2",
    "/ServoPower/INTVCC_SERVO": "#e377c2", "/ServoPower/SENSE_P": "#8c564b", "/ServoPower/SENSE_N": "#8c564b",
    "/ServoPower/SENSE_P_K": "#8c564b", "/ServoPower/VFB_SERVO": "#bcbd22", "/ServoPower/VFB_TAP": "#bcbd22",
    "/ServoPower/ITH_SERVO": "#bcbd22", "/LogicPower/FB_5V": "#bcbd22", "/LogicPower/BOOT_5V": "#e377c2",
}
VIEWS = {  # name: (x1, y1, x2, y2) in mm
    "overview": (-8, -14, 158, 108),
    "detail_input_logic": (-2, -2, 37, 78),
    "detail_servo_regulator": (33, -2, 95, 50),
    "detail_devkit_usb": (90, -12, 152, 102),
    "detail_logic_supply": (-1, 46, 36, 66),
    "detail_output_stages": (91, 6, 123, 47),
    "detail_controller_periphery": (119, 64, 151, 101),
}
LEGEND = [("GND", "#000000"), ("VBAT_IN/FUSED", "#d62728"), ("VBAT_PROT", "#ff7f0e"), ("SW / ISNS", "#9467bd"),
          ("VSERVO / +V_SERVO", "#2ca02c"), ("+5V", "#1f77b4"), ("+3V3", "#17becf"),
          ("Gate/Boost/INTVCC", "#e377c2"), ("Sense", "#8c564b"), ("Feedback/ITH", "#bcbd22"), ("other", "#999999")]


def ratsnest(pcb):
    with tempfile.TemporaryDirectory() as d:
        out = Path(d) / "drc.json"
        subprocess.run([CLI, "pcb", "drc", "--format", "json", "-o", str(out), str(pcb)], capture_output=True)
        data = json.loads(out.read_text())
    edges = []
    for u in data.get("unconnected_items", []):
        a, b = u["items"][:2]
        m = re.search(r"\[([^\]]*)\]", a["description"])
        edges.append((m.group(1) if m else "", (a["pos"]["x"], a["pos"]["y"]), (b["pos"]["x"], b["pos"]["y"])))
    return edges


def collect(board):
    parts = []
    for fp in board.GetFootprints():
        side = "B" if fp.GetLayer() == pcbnew.B_Cu else "F"
        fp.BuildCourtyardCaches()
        cy = fp.GetCourtyard(pcbnew.B_CrtYd if side == "B" else pcbnew.F_CrtYd)
        bb = cy.BBox() if cy.OutlineCount() else fp.GetBoundingBox(False)
        pads = []
        for p in fp.Pads():
            b = p.GetBoundingBox()
            lay = "both" if p.GetAttribute() in (pcbnew.PAD_ATTRIB_PTH, pcbnew.PAD_ATTRIB_NPTH) else side
            pads.append((lay, T(b.GetX()), T(b.GetY()), T(b.GetWidth()), T(b.GetHeight())))
        parts.append(dict(ref=fp.GetReference(), side=side, box=(T(bb.GetX()), T(bb.GetY()), T(bb.GetWidth()),
                                                                  T(bb.GetHeight())), pads=pads))
    copper = {"F": [], "B": [], "via": [], "zone": {"F": [], "B": []}}
    for t in board.GetTracks():
        if t.GetClass() == "PCB_VIA":
            copper["via"].append((T(t.GetPosition().x), T(t.GetPosition().y), T(t.GetWidth(pcbnew.F_Cu)) / 2))
        elif t.GetLayer() in (pcbnew.F_Cu, pcbnew.B_Cu):
            copper["F" if t.GetLayer() == pcbnew.F_Cu else "B"].append(
                (T(t.GetStart().x), T(t.GetStart().y), T(t.GetEnd().x), T(t.GetEnd().y), T(t.GetWidth())))
    for z in board.Zones():
        for side, lay in (("F", pcbnew.F_Cu), ("B", pcbnew.B_Cu)):
            if not z.IsOnLayer(lay):
                continue
            ps = z.GetFilledPolysList(lay)
            for i in range(ps.OutlineCount()):
                ch = ps.Outline(i)
                copper["zone"][side].append(" ".join("%.3f,%.3f" % (T(ch.CPoint(k).x), T(ch.CPoint(k).y))
                                                     for k in range(ch.PointCount())))
    draw = []
    for d in board.GetDrawings():
        layer = d.GetLayerName()
        if isinstance(d, pcbnew.PCB_TEXT):
            draw.append(("text", layer, d.GetText(), T(d.GetPosition().x), T(d.GetPosition().y)))
        elif d.GetShape() == pcbnew.SHAPE_T_RECTANGLE:
            draw.append(("rect", layer, T(d.GetStart().x), T(d.GetStart().y), T(d.GetEnd().x), T(d.GetEnd().y)))
        elif d.GetShape() == pcbnew.SHAPE_T_CIRCLE:
            draw.append(("circle", layer, T(d.GetCenter().x), T(d.GetCenter().y), T(d.GetRadius())))
    return parts, draw, copper


CU = {"F": "#d04040", "B": "#3a6ad0"}


def svg(view, side, parts, draw, edges, copper):
    x1, y1, x2, y2 = view
    w, h = x2 - x1, y2 - y1
    mirror = side == "B"
    tf = ' transform="translate(%s,0) scale(-1,1)"' % (x1 + x2) if mirror else ""
    s = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="%s %s %s %s">'
         % (w * SCALE, (h + 9) * SCALE, x1, y1, w, h + 9),
         '<rect x="%s" y="%s" width="%s" height="%s" fill="white"/>' % (x1, y1, w, h + 9), "<g%s>" % tf]
    for kind, layer, *a in draw:
        if kind == "rect":
            col, wid, dash = ("black", 0.3, "") if layer == "Edge.Cuts" else ("#3355cc", 0.12, ' stroke-dasharray="1,0.6"')
            s.append('<rect x="%s" y="%s" width="%s" height="%s" fill="none" stroke="%s" stroke-width="%s"%s/>'
                     % (min(a[0], a[2]), min(a[1], a[3]), abs(a[2] - a[0]), abs(a[3] - a[1]), col, wid, dash))
        elif kind == "circle":
            s.append('<circle cx="%s" cy="%s" r="%s" fill="none" stroke="#cc3300" stroke-width="0.2"/>' % tuple(a))
    for s_ in (("B", "F") if side == "F" else ("F", "B")):  # other outer layer first, faint
        own = s_ == side
        for pts in copper["zone"][s_]:
            s.append('<polygon points="%s" fill="%s" opacity="%s"/>' % (pts, CU[s_], 0.28 if own else 0.08))
        for x1_, y1_, x2_, y2_, w_ in copper[s_]:
            s.append('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="%s" stroke-linecap="round" '
                     'opacity="%s"/>' % (x1_, y1_, x2_, y2_, CU[s_], w_, 0.9 if own else 0.25))
    for x_, y_, r_ in copper["via"]:
        s.append('<circle cx="%s" cy="%s" r="%s" fill="#666"/>' % (x_, y_, r_))
    for p in parts:  # other side faint, own side solid
        own = p["side"] == side
        bx, by, bw, bh = p["box"]
        s.append('<rect x="%s" y="%s" width="%s" height="%s" fill="%s" stroke="%s" stroke-width="0.08"/>'
                 % (bx, by, bw, bh, "#f3f0e0" if own else "none", "#999" if own else "#ddd"))
        for lay, px, py, pw, ph in p["pads"]:
            if lay in (side, "both"):
                s.append('<rect x="%s" y="%s" width="%s" height="%s" fill="#c8a040"/>' % (px, py, pw, ph))
            elif not own:
                s.append('<rect x="%s" y="%s" width="%s" height="%s" fill="#eee"/>' % (px, py, pw, ph))
    for net, a, b in edges:
        col = COLOURS.get(net)
        wid = 0.3 if net == "GND" else (0.35 if col else 0.06)
        s.append('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="%s" opacity="%s"/>'
                 % (a[0], a[1], b[0], b[1], col or "#999", wid, 0.85 if col else 0.6))
    s.append("</g>")
    for p in sorted(parts, key=lambda p: p["side"] == side):  # own side last, on top
        bx, by, bw, bh = p["box"]
        cx = (x1 + x2) - (bx + bw / 2) if mirror else bx + bw / 2
        own = p["side"] == side
        fs = max(0.6, min(1.6, min(bw, bh) * 0.45))
        s.append('<text x="%s" y="%s" font-size="%s" text-anchor="middle" dominant-baseline="middle" '
                 'font-family="Helvetica" fill="%s">%s</text>' % (cx, by + bh / 2, fs, "#222" if own else "#bbb", p["ref"]))
    for kind, layer, *a in draw:
        if kind == "text":
            tx = (x1 + x2) - a[1] - 20 if mirror else a[1]
            s.append('<text x="%s" y="%s" font-size="1.3" fill="#3355cc" font-family="Helvetica">%s</text>'
                     % (tx, a[2], a[0].replace("&", "&amp;")))
    s.append('<rect x="%s" y="%s" width="%s" height="9" fill="white"/>' % (x1, y2, w))
    ly = y2 + 2.0
    title = ("Oberseite (von oben)" if side == "F" else "Unterseite (von unten gesehen, gespiegelt)") + \
        " - Kupfer rot (F) / blau (B), Luftlinien = KiCad-Ratsnest (DRC unconnected_items), GND schwarz"
    s.append('<text x="%s" y="%s" font-size="1.6" font-family="Helvetica" fill="#000">%s</text>' % (x1 + 1, ly, title))
    lx = x1 + 1
    for name, col in LEGEND:
        s.append('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="0.5"/>' % (lx, ly + 3, lx + 3, ly + 3, col))
        s.append('<text x="%s" y="%s" font-size="1.3" font-family="Helvetica">%s</text>' % (lx + 3.5, ly + 3.4, name))
        lx += 4.5 + 0.75 * len(name)
    s.append("</svg>")
    return "\n".join(s)


def main():
    pcb = ROOT / "RoverCore.kicad_pcb"
    board = pcbnew.LoadBoard(str(pcb))
    parts, draw, copper = collect(board)
    edges = ratsnest(pcb)
    OUT.mkdir(parents=True, exist_ok=True)
    for name, view in VIEWS.items():
        for side in ("F", "B"):
            stem = "%s_%s" % (name, "top" if side == "F" else "bottom")
            f = OUT / (stem + ".svg")
            f.write_text(svg(view, side, parts, draw, edges, copper))
            if shutil.which("rsvg-convert"):
                subprocess.run(["rsvg-convert", "-o", str(OUT / (stem + ".png")), str(f)], check=True)
    print("wrote %d views to %s (%d ratsnest edges)" % (2 * len(VIEWS), OUT, len(edges)))


if __name__ == "__main__":
    main()
