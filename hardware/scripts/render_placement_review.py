#!/usr/bin/env python3
"""Placement review images: courtyards, pads, group frames, provisional outline and ratsnest (MST per net).

Run with the KiCad Python (pcbnew); writes SVG and, if rsvg-convert exists, PNG to qa/generated/placement/
(generated output, not committed). Critical power and feedback nets are drawn in colour, all others thin grey.
Usage: <KiCad python> hardware/scripts/render_placement_review.py
"""
from pathlib import Path
import math
import shutil
import subprocess

import pcbnew

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "qa/generated/placement"
T = pcbnew.ToMM
SCALE = 10.0  # px per mm
COLOURS = {
    "/Power/VBAT_IN": "#d62728", "/Power/VBAT_FUSED": "#d62728", "/Power/VBAT_PROT": "#ff7f0e",
    "/ServoPower/SW_SERVO": "#9467bd", "/ServoPower/ISNS_PWR": "#9467bd", "/ServoPower/VSERVO_REG": "#2ca02c",
    "+V_SERVO": "#2ca02c", "/LogicPower/SW_5V": "#9467bd", "+5V": "#1f77b4", "+3V3": "#17becf",
    "/ServoPower/TG_SERVO": "#e377c2", "/ServoPower/BG_SERVO": "#e377c2", "/ServoPower/BOOST_SERVO": "#e377c2",
    "/ServoPower/SENSE_P": "#8c564b", "/ServoPower/SENSE_N": "#8c564b", "/ServoPower/VFB_SERVO": "#bcbd22",
    "/LogicPower/FB_5V": "#bcbd22", "/LogicPower/BOOT_5V": "#e377c2", "OUT_LOCK": "#7f7f7f",
}
VIEWS = {  # name: (x1, y1, x2, y2) in mm
    "overview": (-8, -14, 158, 108),
    "detail_input_logic": (-2, -2, 37, 78),
    "detail_servo_regulator": (33, -2, 95, 50),
    "detail_devkit_usb": (90, -12, 152, 102),
}


def mst(points):
    if len(points) < 2:
        return []
    done, edges = {0}, []
    while len(done) < len(points):
        best = None
        for i in done:
            for j in range(len(points)):
                if j in done:
                    continue
                d = math.dist(points[i], points[j])
                if best is None or d < best[0]:
                    best = (d, i, j)
        done.add(best[2])
        edges.append((points[best[1]], points[best[2]]))
    return edges


def main():
    board = pcbnew.LoadBoard(str(ROOT / "RoverCore.kicad_pcb"))
    nets = {}
    shapes, texts = [], []
    for fp in board.GetFootprints():
        fp.BuildCourtyardCaches()
        cy = fp.GetCourtyard(pcbnew.F_CrtYd)
        bb = cy.BBox() if cy.OutlineCount() else fp.GetBoundingBox(False)
        shapes.append(("crt", T(bb.GetX()), T(bb.GetY()), T(bb.GetWidth()), T(bb.GetHeight())))
        texts.append((fp.GetReference(), T(bb.Centre().x), T(bb.Centre().y), min(T(bb.GetWidth()), T(bb.GetHeight()))))
        for p in fp.Pads():
            b = p.GetBoundingBox()
            shapes.append(("pad", T(b.GetX()), T(b.GetY()), T(b.GetWidth()), T(b.GetHeight())))
            if p.GetNetname() and not p.GetNetname().startswith("unconnected-") and p.GetNetname() != "GND":
                nets.setdefault(p.GetNetname(), []).append((T(p.GetPosition().x), T(p.GetPosition().y)))
    draw = []
    for d in board.GetDrawings():
        layer = d.GetLayerName()
        if isinstance(d, pcbnew.PCB_TEXT):
            draw.append(("text", layer, d.GetText(), T(d.GetPosition().x), T(d.GetPosition().y)))
        elif d.GetShape() == pcbnew.SHAPE_T_RECTANGLE:
            draw.append(("rect", layer, T(d.GetStart().x), T(d.GetStart().y), T(d.GetEnd().x), T(d.GetEnd().y)))
        elif d.GetShape() == pcbnew.SHAPE_T_CIRCLE:
            draw.append(("circle", layer, T(d.GetCenter().x), T(d.GetCenter().y), T(d.GetRadius())))
    OUT.mkdir(parents=True, exist_ok=True)
    for name, (x1, y1, x2, y2) in VIEWS.items():
        w, h = (x2 - x1) * SCALE, (y2 - y1) * SCALE
        s = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="%s %s %s %s">'
             % (w, h, x1, y1, x2 - x1, y2 - y1), '<rect x="%s" y="%s" width="%s" height="%s" fill="white"/>'
             % (x1, y1, x2 - x1, y2 - y1)]
        for kind, layer, *a in draw:
            if kind == "rect":
                col, dash = ("black", "") if layer == "Edge.Cuts" else ("#3355cc", ' stroke-dasharray="1,0.6"')
                s.append('<rect x="%s" y="%s" width="%s" height="%s" fill="none" stroke="%s" stroke-width="%s"%s/>'
                         % (min(a[0], a[2]), min(a[1], a[3]), abs(a[2] - a[0]), abs(a[3] - a[1]), col,
                            0.3 if layer == "Edge.Cuts" else 0.15, dash))
            elif kind == "circle":
                s.append('<circle cx="%s" cy="%s" r="%s" fill="none" stroke="#cc3300" stroke-width="0.2"/>' % tuple(a))
            elif kind == "text":
                s.append('<text x="%s" y="%s" font-size="1.4" fill="#3355cc" font-family="Helvetica">%s</text>'
                         % (a[1], a[2], a[0].replace("&", "&amp;")))
        for kind, x, y, bw, bh in shapes:
            if kind == "crt":
                s.append('<rect x="%s" y="%s" width="%s" height="%s" fill="#f3f0e0" stroke="#999" stroke-width="0.08"/>'
                         % (x, y, bw, bh))
        for kind, x, y, bw, bh in shapes:
            if kind == "pad":
                s.append('<rect x="%s" y="%s" width="%s" height="%s" fill="#c8a040"/>' % (x, y, bw, bh))
        for net, pts in nets.items():
            col = COLOURS.get(net)
            for (a, b) in mst(pts):
                s.append('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="%s" opacity="%s"/>'
                         % (a[0], a[1], b[0], b[1], col or "#888", 0.35 if col else 0.06, 0.9 if col else 0.6))
        for ref, x, y, size in texts:
            fs = max(0.6, min(1.6, size * 0.45))
            s.append('<text x="%s" y="%s" font-size="%s" text-anchor="middle" dominant-baseline="middle" '
                     'font-family="Helvetica" fill="#222">%s</text>' % (x, y, fs, ref))
        s.append("</svg>")
        svg = OUT / (name + ".svg")
        svg.write_text("\n".join(s))
        if shutil.which("rsvg-convert"):
            subprocess.run(["rsvg-convert", "-o", str(OUT / (name + ".png")), str(svg)], check=True)
        print("wrote", OUT / name)


if __name__ == "__main__":
    main()
