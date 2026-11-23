#!/usr/bin/env python3
"""Dimensioned top view of the mounting holes (mounting review, 2026-11-18). Review image, not a drawing release.

Usage: <KiCad python> render_mounting_drawing.py BOARD.kicad_pcb OUT.png [BACKGROUND.png]
Reads the board outline and the footprints H1-H4 from the board and draws, in K1 coordinates (datum = top-left
outline corner): outline with overall size, hole centres with Ø, washer Ø 7.0 mm and copper keep-out r 3.8 mm,
chain dimensions from the datum to every hole and the hole-to-hole distances. With BACKGROUND (`scripts/kit fab preview`
composite, 10 px/mm, 2 mm margin) the Gerber top view is drawn faintly underneath. Needs rsvg-convert.
"""
from pathlib import Path
import base64
import math
import subprocess
import sys

import pcbnew

T = pcbnew.ToMM
S = 10.0           # px per mm
MARGIN = 22.0      # mm around the board for dimensions


def main():
    b = pcbnew.LoadBoard(sys.argv[1])
    out = Path(sys.argv[2])
    bg = Path(sys.argv[3]) if len(sys.argv) > 3 else None
    e = b.GetBoardEdgesBoundingBox()
    ox, oy = T(e.GetLeft()) + 0.05, T(e.GetTop()) + 0.05
    W, H = T(e.GetWidth()) - 0.1, T(e.GetHeight()) - 0.1
    holes = []
    for r in ("H1", "H2", "H3", "H4"):
        fp = b.FindFootprintByReference(r)
        p = fp.GetPosition()
        d = T(next(iter(fp.Pads())).GetDrillSize().x)
        holes.append((r, round(T(p.x) - ox, 2), round(T(p.y) - oy, 2), d))
    vw, vh = W + 2 * MARGIN, H + MARGIN + 21
    s = ['<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="%d" '
         'height="%d" viewBox="%.2f %.2f %.2f %.2f">' % (vw * S, vh * S, -MARGIN, -MARGIN, vw, vh),
         '<rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" fill="white"/>' % (-MARGIN, -MARGIN, vw, vh),
         '<style>text{font-family:Helvetica;fill:#111} .d{stroke:#1f4fd0;stroke-width:0.18;fill:none} '
         '.dt{fill:#1f4fd0;font-size:2.2px} .h{font-size:2.6px;font-weight:bold}</style>']
    if bg and bg.exists():
        data = base64.b64encode(bg.read_bytes()).decode()
        # gerber_preview box starts 2 mm outside the drill/outline extent; outline corner is at -0.05/-0.05
        s.append('<image xlink:href="data:image/png;base64,%s" x="%.2f" y="%.2f" width="%.2f" height="%.2f" '
                 'opacity="0.35"/>' % (data, -2.05, -2.05, W + 4.1, H + 4.1))
    s.append('<rect x="0" y="0" width="%.2f" height="%.2f" fill="none" stroke="#000" stroke-width="0.3"/>' % (W, H))

    def dim_h(x1, x2, y, label):
        s.append('<path class="d" d="M%.2f %.2f H%.2f M%.2f %.2f v-1.2 v2.4 M%.2f %.2f v-1.2 v2.4"/>'
                 % (x1, y, x2, x1, y, x2, y))
        s.append('<text class="dt" x="%.2f" y="%.2f" text-anchor="middle">%s</text>' % ((x1 + x2) / 2, y - 0.6, label))

    def dim_v(y1, y2, x, label):
        s.append('<path class="d" d="M%.2f %.2f V%.2f M%.2f %.2f h-1.2 h2.4 M%.2f %.2f h-1.2 h2.4"/>'
                 % (x, y1, y2, x, y1, x, y2))
        s.append('<text class="dt" x="%.2f" y="%.2f" text-anchor="middle" transform="rotate(-90 %.2f %.2f)">%s'
                 '</text>' % (x - 0.6, (y1 + y2) / 2, x - 0.6, (y1 + y2) / 2, label))
    dim_h(0, W, -16, "%.1f" % W)
    dim_v(0, H, -16, "%.1f" % H)
    for k, (r, x, y, d) in enumerate(sorted(holes, key=lambda h: h[1])):
        dim_h(0, x, -4 - 3 * k, "%s x %.1f" % (r, x))
        s.append('<path class="d" d="M%.2f %.2f V%.2f" stroke-dasharray="0.6 0.6"/>' % (x, -4 - 3 * k, y))
    for k, (r, x, y, d) in enumerate(sorted(holes, key=lambda h: h[2])):
        dim_v(0, y, -4 - 3 * k, "%s y %.1f" % (r, y))
        s.append('<path class="d" d="M%.2f %.2f H%.2f" stroke-dasharray="0.6 0.6"/>' % (-4 - 3 * k, y, x))
    for r, x, y, d in holes:
        s.append('<circle cx="%.2f" cy="%.2f" r="3.8" fill="#e05050" fill-opacity="0.18" stroke="#c02020" '
                 'stroke-width="0.15" stroke-dasharray="0.5 0.4"/>' % (x, y))
        s.append('<circle cx="%.2f" cy="%.2f" r="3.5" fill="none" stroke="#555" stroke-width="0.12"/>' % (x, y))
        s.append('<circle cx="%.2f" cy="%.2f" r="%.2f" fill="#000"/>' % (x, y, d / 2))
        s.append('<path d="M%.2f %.2f h3 M%.2f %.2f v3" stroke="#000" stroke-width="0.12" transform="translate(-1.5 0)"/>'
                 % (x, y, x + 1.5, y - 1.5))
        anchor = "start" if x < W - 25 else "end"
        tx = x + 4.5 if anchor == "start" else x - 4.5
        ty = y + 1
        if y > H - 6:                      # holes at the lower edge: label below the board
            tx, ty, anchor = x, H + 4.2, "middle"
        s.append('<text class="h" x="%.2f" y="%.2f" text-anchor="%s">%s  Ø%.1f NPTH (%.1f | %.1f)</text>'
                 % (tx, ty, anchor, r, d, x, y))
    pairs = [("H1", "H2"), ("H2", "H3"), ("H3", "H4"), ("H1", "H4"), ("H1", "H3"), ("H2", "H4")]
    hp = {r: (x, y) for r, x, y, _ in holes}
    lines = ["Abstände Lochmitte: " + ", ".join("%s-%s %.1f" % (a, c, math.hypot(hp[a][0] - hp[c][0],
                                                                           hp[a][1] - hp[c][1])) for a, c in pairs)]
    lines.append("K1-Koordinaten in mm, Bezug linke obere Konturecke, y nach unten. Rot gestrichelt: Kupfersperre "
                 "r 3,8 mm (F/B), grau: Scheibe Ø 7,0 mm.")
    lines.append("VORLÄUFIG: keine Chassis-/Gehäusemaße vorhanden; Lage vor der Fertigung am Fahrzeug bestätigen.")
    for i, ln in enumerate(lines):
        s.append('<text x="%.2f" y="%.2f" font-size="2.3px" fill="%s">%s</text>'
                 % (-MARGIN + 2, H + 9 + i * 3.4, "#b00000" if i == 2 else "#111", ln))
    s.append("</svg>")
    svg = out.with_suffix(".svg")
    out.parent.mkdir(parents=True, exist_ok=True)
    svg.write_text("\n".join(s))
    subprocess.run(["rsvg-convert", "-o", str(out), str(svg)], check=True)
    svg.unlink()
    print("written", out, holes)


if __name__ == "__main__":
    main()
