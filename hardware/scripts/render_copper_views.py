#!/usr/bin/env python3
"""Copper views of the K1 board from the actual copper (routing review, 2026-11-18). Review images, not source.

Usage: <KiCad python> render_copper_views.py BOARD.kicad_pcb OUTDIR [--region X0 Y0 X1 Y1] [--net NET] [--scale PX_PER_MM]
       [--layers F.Cu,B.Cu] [--name NAME]
Without --region the whole board is drawn; region coordinates are K1 coordinates (outline corner at -0.05/-0.05),
so they stay valid when the board is moved in the editor. One PNG per layer plus one with F and B overlaid. With
--net that net is drawn in colour and everything else grey. Needs rsvg-convert.
"""
from pathlib import Path
import subprocess
import sys

import pcbnew

T = pcbnew.ToMM
COL = {"F.Cu": "#d23c3c", "B.Cu": "#3c78e6", "In1.Cu": "#c8a000", "In2.Cu": "#30a050"}


def arg(name, default=None, n=1):
    if name not in sys.argv:
        return default
    k = sys.argv.index(name)
    return sys.argv[k + 1] if n == 1 else sys.argv[k + 1:k + 1 + n]


def poly(ch, fill, op):
    pts = " ".join("%.3f,%.3f" % (T(ch.CPoint(k).x), T(ch.CPoint(k).y)) for k in range(ch.PointCount()))
    return '<polygon points="%s" fill="%s" opacity="%s"/>' % (pts, fill, op)


def render(b, layers, box, net, scale, out):
    x1, y1, x2, y2 = box
    s = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="%s %s %s %s">'
         % ((x2 - x1) * scale, (y2 - y1) * scale, x1, y1, x2 - x1, y2 - y1),
         '<rect x="%s" y="%s" width="%s" height="%s" fill="#101010"/>' % (x1, y1, x2 - x1, y2 - y1)]
    op = 0.6 if len(layers) > 1 else 0.9

    def col(c, item):
        return c if net is None or item.GetNetname() == net else "#5a5a5a"
    for ln in layers:
        L, c = b.GetLayerID(ln), COL[ln]
        for z in b.Zones():
            if not z.IsOnLayer(L):
                continue
            ps = z.GetFilledPolysList(L)
            for i in range(ps.OutlineCount()):
                s.append(poly(ps.Outline(i), col(c, z), op))
                for h in range(ps.HoleCount(i)):
                    s.append(poly(ps.Hole(i, h), "#101010", 1))
        for t in b.GetTracks():
            if t.GetClass() == "PCB_TRACK" and t.GetLayer() == L:
                s.append('<line x1="%.3f" y1="%.3f" x2="%.3f" y2="%.3f" stroke="%s" stroke-width="%.3f" '
                         'stroke-linecap="round" opacity="0.95"/>' % (T(t.GetStart().x), T(t.GetStart().y),
                                                                       T(t.GetEnd().x), T(t.GetEnd().y), col(c, t),
                                                                       T(t.GetWidth())))
        for fp in b.GetFootprints():
            for p in fp.Pads():
                if p.IsOnLayer(L):
                    ps = pcbnew.SHAPE_POLY_SET()
                    p.TransformShapeToPolygon(ps, L, 0, pcbnew.FromMM(0.01), pcbnew.ERROR_INSIDE)
                    for i in range(ps.OutlineCount()):
                        s.append(poly(ps.Outline(i), col(c, p), 0.95))
    for t in b.GetTracks():
        if t.GetClass() == "PCB_VIA":
            p = t.GetPosition()
            s.append('<circle cx="%.3f" cy="%.3f" r="%.3f" fill="%s" stroke="#000" stroke-width="0.03"/>'
                     % (T(p.x), T(p.y), T(t.GetWidth(pcbnew.F_Cu)) / 2,
                        "#e0e0e0" if net is None or t.GetNetname() == net else "#7a7a7a"))
            s.append('<circle cx="%.3f" cy="%.3f" r="%.3f" fill="#000"/>' % (T(p.x), T(p.y), T(t.GetDrill()) / 2))
    fs = max(0.5, min(1.2, (x2 - x1) / 120))
    for fp in b.GetFootprints():
        p = fp.GetPosition()
        if x1 < T(p.x) < x2 and y1 < T(p.y) < y2:
            s.append('<text x="%.2f" y="%.2f" font-size="%.2f" fill="#fff" font-family="Helvetica">%s</text>'
                     % (T(p.x), T(p.y), fs, fp.GetReference()))
    e = b.GetBoardEdgesBoundingBox()
    s.append('<rect x="%.3f" y="%.3f" width="%.3f" height="%.3f" fill="none" stroke="#e8e8a0" stroke-width="0.15"/>'
             % (T(e.GetLeft()), T(e.GetTop()), T(e.GetWidth()), T(e.GetHeight())))
    s.append("</svg>")
    out.with_suffix(".svg").write_text("\n".join(s))
    subprocess.run(["rsvg-convert", "-o", str(out.with_suffix(".png")), str(out.with_suffix(".svg"))], check=True)
    out.with_suffix(".svg").unlink()


def main():
    b = pcbnew.LoadBoard(sys.argv[1])
    outdir = Path(sys.argv[2])
    outdir.mkdir(parents=True, exist_ok=True)
    e = b.GetBoardEdgesBoundingBox()
    ox, oy = T(e.GetLeft()) + 0.05, T(e.GetTop()) + 0.05
    r = arg("--region", None, 4)
    box = ([float(r[0]) + ox, float(r[1]) + oy, float(r[2]) + ox, float(r[3]) + oy] if r else
           [T(e.GetLeft()) - 1, T(e.GetTop()) - 1, T(e.GetRight()) + 1, T(e.GetBottom()) + 1])
    net = arg("--net")
    scale = float(arg("--scale", "12"))
    layers = arg("--layers", "F.Cu,B.Cu").split(",")
    name = arg("--name", "copper")
    for ln in layers:
        render(b, [ln], box, net, scale, outdir / ("%s_%s" % (name, ln.replace(".", "_"))))
    if len(layers) > 1:
        render(b, layers, box, net, scale, outdir / ("%s_overlay" % name))
    print("written to %s" % outdir)


if __name__ == "__main__":
    main()
