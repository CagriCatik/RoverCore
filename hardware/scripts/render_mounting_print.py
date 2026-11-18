#!/usr/bin/env python3
"""1:1 print template for the mechanical check on the vehicle (mounting review, 2026-11-18). Not a drawing release.

Usage: <KiCad python> render_mounting_print.py BOARD.kicad_pcb OUT.pdf
A4 landscape PDF at scale 1:1 (print at 100 % / "actual size"; check the 100 mm bars before using it). Top view in
K1 coordinates (datum = top-left outline corner) with:
- outline, hole centres H1-H4 with cross-hair, Ø 3.2 hole, washer Ø 7.0, copper keep-out r 3.8 (dashed);
- chain dimensions from the datum; 100 mm check bars horizontal and vertical;
- connector bodies with plug direction (J101 XT30, J102/J103 Micro-Fit, J104-J112, USB of the DevKit) from F.Fab;
- the outline of the DevKit field and the proposed SUPPORT zone on the bottom side (seen from the top), free of
  bottom pads/courtyards (+1.5 mm) and vias (SUPPORT, found by a search on the board, 2026-11-18).
Needs rsvg-convert.
"""
from pathlib import Path
import subprocess
import sys

import pcbnew

T = pcbnew.ToMM
PAGE_W, PAGE_H = 297.0, 210.0
OX, OY = 40.0, 45.0                        # page position of the K1 datum (mm)
SUPPORT = (129.0, 4.0, 143.0, 40.0)        # K1 mm, bottom side
SUPPORT_POINTS = [(136.0, 12.0), (136.0, 34.0)]


def main():
    b = pcbnew.LoadBoard(sys.argv[1])
    out = Path(sys.argv[2])
    e = b.GetBoardEdgesBoundingBox()
    ox, oy = T(e.GetLeft()) + 0.05, T(e.GetTop()) + 0.05
    W, H = T(e.GetWidth()) - 0.1, T(e.GetHeight()) - 0.1

    def P(x, y):
        return x + OX, y + OY

    def fab_rect(ref):
        fp = b.FindFootprintByReference(ref)
        xs, ys = [], []
        for g in fp.GraphicalItems():
            if g.GetLayer() == pcbnew.F_Fab and isinstance(g, pcbnew.PCB_SHAPE):
                bb = g.GetBoundingBox()
                xs += [T(bb.GetLeft()) - ox, T(bb.GetRight()) - ox]
                ys += [T(bb.GetTop()) - oy, T(bb.GetBottom()) - oy]
        return min(xs), min(ys), max(xs), max(ys)

    s = ['<svg xmlns="http://www.w3.org/2000/svg" width="%smm" height="%smm" viewBox="0 0 %s %s">'
         % (PAGE_W, PAGE_H, PAGE_W, PAGE_H),
         '<rect width="%s" height="%s" fill="white"/>' % (PAGE_W, PAGE_H),
         '<defs><pattern id="hatch" width="2" height="2" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
         '<line x1="0" y1="0" x2="0" y2="2" stroke="#2a8a2a" stroke-width="0.3"/></pattern></defs>',
         '<style>text{font-family:Helvetica;fill:#111} .d{stroke:#1f4fd0;stroke-width:0.15;fill:none} '
         '.dt{fill:#1f4fd0;font-size:2.4px}</style>']
    x0, y0 = P(0, 0)
    s.append('<rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" fill="#f4f4ec" stroke="#000" stroke-width="0.3"/>'
             % (x0, y0, W, H))
    # DevKit field and support zone
    dx1, dy1, dx2, dy2 = fab_rect("U501")
    a, c = P(dx1, max(dy1, 0)), P(dx2, dy2)
    s.append('<rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" fill="none" stroke="#1f4fd0" stroke-width="0.2" '
             'stroke-dasharray="1 0.6"/>' % (a[0], a[1], c[0] - a[0], c[1] - a[1]))
    s.append('<text x="%.2f" y="%.2f" font-size="2.4px" fill="#1f4fd0">DevKit-Feld (gesteckt)</text>' % (a[0] + 1, c[1] - 1.5))
    a, c = P(SUPPORT[0], SUPPORT[1]), P(SUPPORT[2], SUPPORT[3])
    s.append('<rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" fill="url(#hatch)" stroke="#2a8a2a" '
             'stroke-width="0.25"/>' % (a[0], a[1], c[0] - a[0], c[1] - a[1]))
    for sx, sy in SUPPORT_POINTS:
        q = P(sx, sy)
        s.append('<circle cx="%.2f" cy="%.2f" r="2.5" fill="none" stroke="#2a8a2a" stroke-width="0.35"/>' % q)
        s.append('<path d="M%.2f %.2f h3 M%.2f %.2f v3" stroke="#2a8a2a" stroke-width="0.2" transform="translate(-1.5 -1.5)"/>'
                 % (q[0], q[1] + 1.5, q[0] + 1.5, q[1]))
    s.append('<text x="%.2f" y="%.2f" font-size="2.2px" fill="#2a8a2a">Auflage Unterseite</text>' % (a[0] + 0.5, c[1] + 3))
    s.append('<text x="%.2f" y="%.2f" font-size="2.2px" fill="#2a8a2a">x %.0f-%.0f, y %.0f-%.0f</text>'
             % (a[0] + 0.5, c[1] + 5.6, SUPPORT[0], SUPPORT[2], SUPPORT[1], SUPPORT[3]))
    # antenna keep-out of the DevKit footprint on the board (rule area of U501, all copper layers)
    for z in b.FindFootprintByReference("U501").Zones():
        if z.GetIsRuleArea():
            bb = z.GetBoundingBox()
            ka = P(T(bb.GetLeft()) - ox, max(T(bb.GetTop()) - oy, -8))
            kc = P(T(bb.GetRight()) - ox, T(bb.GetBottom()) - oy)
            s.append('<rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" fill="#c02020" fill-opacity="0.12" '
                     'stroke="#c02020" stroke-width="0.2"/>' % (ka[0], ka[1], kc[0] - ka[0], kc[1] - ka[1]))
            s.append('<text x="%.2f" y="%.2f" font-size="2px" fill="#c02020">Antennenfreiraum (keine Auflage)</text>'
                     % (ka[0] + 0.5, ka[1] - 0.8))
    # connectors with plug direction
    # horizontal plugs get an arrow; J104-J112 are vertical (plug from above, cable leaves upwards)
    conns = {"J101": "left", "J102": "up", "J103": "up", "J104": None, "J105": None, "J106": None,
             "J107": None, "J108": None, "J109": None, "J110": None, "J111": None, "J112": None}
    for ref, d in conns.items():
        try:
            r = fab_rect(ref)
        except ValueError:
            continue
        a, c = P(r[0], r[1]), P(r[2], r[3])
        s.append('<rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" fill="#ddd" stroke="#555" stroke-width="0.15"/>'
                 % (a[0], a[1], c[0] - a[0], c[1] - a[1]))
        s.append('<text x="%.2f" y="%.2f" font-size="1.8px" text-anchor="middle">%s</text>'
                 % ((a[0] + c[0]) / 2, (a[1] + c[1]) / 2 + 0.6, ref))
        if d:
            mx, my = (a[0] + c[0]) / 2, (a[1] + c[1]) / 2
            vec = {"left": (-1, 0), "up": (0, -1), "down": (0, 1)}[d]
            ex = (a[0] - 6, my) if d == "left" else (mx, a[1] - 6) if d == "up" else (mx, c[1] + 6)
            st = (a[0], my) if d == "left" else (mx, a[1]) if d == "up" else (mx, c[1])
            s.append('<path d="M%.2f %.2f L%.2f %.2f" stroke="#c06000" stroke-width="0.35"/>' % (st + ex))
            s.append('<circle cx="%.2f" cy="%.2f" r="0.6" fill="#c06000"/>' % ex)
            del vec
    # USB of the DevKit (bottom end of the DevKit field, plugs point down / +y)
    for ux in (130.2, 143.6):
        q = P(ux, dy2)
        s.append('<path d="M%.2f %.2f v8" stroke="#c06000" stroke-width="0.35"/>' % q)
        s.append('<text x="%.2f" y="%.2f" font-size="1.8px" text-anchor="middle" fill="#c06000">USB</text>'
                 % (q[0], q[1] + 10))
    # holes
    holes = []
    for ref in ("H1", "H2", "H3", "H4"):
        fp = b.FindFootprintByReference(ref)
        p = fp.GetPosition()
        holes.append((ref, round(T(p.x) - ox, 2), round(T(p.y) - oy, 2)))
    for ref, x, y in holes:
        q = P(x, y)
        s.append('<circle cx="%.2f" cy="%.2f" r="3.8" fill="none" stroke="#c02020" stroke-width="0.15" '
                 'stroke-dasharray="0.6 0.4"/>' % q)
        s.append('<circle cx="%.2f" cy="%.2f" r="3.5" fill="none" stroke="#444" stroke-width="0.15"/>' % q)
        s.append('<circle cx="%.2f" cy="%.2f" r="1.6" fill="none" stroke="#000" stroke-width="0.25"/>' % q)
        s.append('<path d="M%.2f %.2f h10 M%.2f %.2f v10" stroke="#000" stroke-width="0.12"/>'
                 % (q[0] - 5, q[1], q[0], q[1] - 5))
        s.append('<text x="%.2f" y="%.2f" font-size="2.6px" font-weight="bold">%s</text>' % (q[0] + 2.2, q[1] - 2.2, ref))

    def dim_h(x1, x2, y, label):
        a, c = P(x1, y), P(x2, y)
        s.append('<path class="d" d="M%.2f %.2f H%.2f M%.2f %.2f v-1 v2 M%.2f %.2f v-1 v2"/>'
                 % (a[0], a[1], c[0], a[0], a[1], c[0], c[1]))
        s.append('<text class="dt" x="%.2f" y="%.2f" text-anchor="middle">%s</text>' % ((a[0] + c[0]) / 2, a[1] - 0.6, label))

    def dim_v(y1, y2, x, label):
        a, c = P(x, y1), P(x, y2)
        s.append('<path class="d" d="M%.2f %.2f V%.2f M%.2f %.2f h-1 h2 M%.2f %.2f h-1 h2"/>'
                 % (a[0], a[1], c[1], a[0], a[1], c[0], c[1]))
        mx, my = a[0] - 0.6, (a[1] + c[1]) / 2
        s.append('<text class="dt" x="%.2f" y="%.2f" text-anchor="middle" transform="rotate(-90 %.2f %.2f)">%s</text>'
                 % (mx, my, mx, my, label))
    dim_h(0, W, -22, "%.1f" % W)
    dim_v(0, H, -22, "%.1f" % H)
    for k, (ref, x, y) in enumerate(sorted(holes, key=lambda h: h[1])):
        dim_h(0, x, -6 - 3.6 * k, "%s %.1f" % (ref, x))
    for k, (ref, x, y) in enumerate(sorted(holes, key=lambda h: h[2])):
        dim_v(0, y, -6 - 3.6 * k, "%s %.1f" % (ref, y))
    # 100 mm check bars
    bx, by = 40.0, 160.0
    s.append('<path d="M%.1f %.1f h100 M%.1f %.1f v-3 v6 M%.1f %.1f v-3 v6" stroke="#000" stroke-width="0.3"/>'
             % (bx, by, bx, by, bx + 100, by))
    for k in range(11):
        s.append('<path d="M%.1f %.1f v-1.5" stroke="#000" stroke-width="0.2"/>' % (bx + 10 * k, by))
    s.append('<text x="%.1f" y="%.1f" font-size="3px" text-anchor="middle">Kontrollmaß 100,0 mm</text>' % (bx + 50, by + 5))
    vx, vy = 268.0, 45.0
    s.append('<path d="M%.1f %.1f v100 M%.1f %.1f h-3 h6 M%.1f %.1f h-3 h6" stroke="#000" stroke-width="0.3"/>'
             % (vx, vy, vx, vy, vx, vy + 100))
    s.append('<text x="%.1f" y="%.1f" font-size="3px" text-anchor="middle" transform="rotate(-90 %.1f %.1f)">'
             'Kontrollmaß 100,0 mm</text>' % (vx + 4.5, vy + 50, vx + 4.5, vy + 50))
    notes = [
        "RoverCore Rev 1 / K1 - Befestigung VORLÄUFIG (keine Chassismaße). Maßstab 1:1 - mit 100 % / 'Tatsächliche Größe' "
        "drucken, beide Kontrollmaße nachmessen.",
        "Draufsicht von oben, Bezug linke obere Konturecke, mm. H1-H4: M3, NPTH Ø 3,2; Kreis Ø 7,0 = Scheibe; rot "
        "gestrichelt r 3,8 = Kupfersperre (F/B).",
        "Grün: Auflage UNTERSEITE unter dem DevKit (±1,5 mm zu Pads/Courtyards, keine Vias, ≥ 3 mm zum roten "
        "Antennenfreiraum) - breit, isolierend, ohne scharfe Kanten,",
        "kein Metall (Lötstopplack ist kein Scheuerschutz); Höhe = gemessener Abstand Chassis-Platine, Platine nicht "
        "vorspannen.",
        "Orange: Steckrichtung der waagrechten Stecker (J101, J102/J103, DevKit-USB); J104-J112 senkrecht. Lochabstände: H1-H2 42,5 / H2-H3 94,9 / H3-H4 55,0 / H1-H4 146,8 / "
        "H2-H4 147,0 mm.",
    ]
    for i, ln in enumerate(notes):
        s.append('<text x="15" y="%.1f" font-size="2.6px">%s</text>' % (174 + i * 4.0, ln))
    s.append("</svg>")
    svg = out.with_suffix(".svg")
    out.parent.mkdir(parents=True, exist_ok=True)
    svg.write_text("\n".join(s))
    subprocess.run(["rsvg-convert", "-f", "pdf", "-o", str(out), str(svg)], check=True)
    subprocess.run(["rsvg-convert", "-f", "png", "-d", "150", "-p", "150", "-o", str(out.with_suffix(".png")), str(svg)],
                   check=True)
    svg.unlink()
    print("written", out, holes)


if __name__ == "__main__":
    main()
