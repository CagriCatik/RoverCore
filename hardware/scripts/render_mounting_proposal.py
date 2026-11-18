#!/usr/bin/env python3
"""Mounting proposal for K1 (mechanical rework, 2026-11-18). Review drawing only; the board is NOT changed.

Usage: <KiCad python> render_mounting_proposal.py BOARD.kicad_pcb OUT.png
Draws, in K1 coordinates (datum top-left outline corner, mm), the current outline 150 x 85 and the proposed
outline 160 x 85 (variant B: +10 mm on the right), all courtyards (grey), the parts that would have to move (orange,
with the shift), the DevKit field, the USB cable envelopes, the antenna keep-out and four M3 corner holes with:
hole Ø 3.2, screw head Ø 5.7, washer Ø 7.0, copper keep-out r 3.8, bottom hex standoff Ø 6.35 (dotted) and tool
access Ø 11 (dashed, r 5.5 free of tall parts). The current provisional H1-H4 are drawn as grey crosses.
All dimensions of the hardware are assumptions (see mounting_holes.py); chassis data does not exist yet.
"""
from pathlib import Path
import subprocess
import sys

import pcbnew

T = pcbnew.ToMM
SC = 8.0                     # px per mm
W_NEW, H = 160.0, 85.0
HOLES = {"A": (4.5, 4.5), "B": (4.5, 80.5), "C": (155.5, 4.5), "D": (155.5, 80.5)}
MOVES = {"J101": (0, 3.0), "TP101": (0, 3.0), "F101": (0, 3.0),
         "J108": (7.5, 0), "J109": (6.5, 0), "J110": (5.5, 0), "J111": (4.5, 0), "J112": (3.5, 0),
         "R520": (0, 0), "TP506": (0, 0)}   # LED row with 1 mm gaps (10.0 ... 61.0); R520/TP506 move, target open
USB = [(130.2 - 4.0, 61.0, 130.2 + 4.0, 85.0), (143.6 - 4.0, 61.0, 143.6 + 4.0, 85.0)]


def main():
    b = pcbnew.LoadBoard(sys.argv[1])
    out = Path(sys.argv[2])
    e = b.GetBoardEdgesBoundingBox()
    ox, oy = T(e.GetLeft()) + 0.05, T(e.GetTop()) + 0.05
    m = 14.0
    vw, vh = W_NEW + 2 * m, H + 2 * m + 26
    s = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="%.1f %.1f %.1f %.1f">'
         % (vw * SC, vh * SC, -m, -m, vw, vh),
         '<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="white"/>' % (-m, -m, vw, vh),
         '<style>text{font-family:Helvetica;fill:#111}</style>']
    s.append('<rect x="0" y="0" width="%.1f" height="%.1f" fill="#eef3ec" stroke="#2a8a2a" stroke-width="0.35" '
             'stroke-dasharray="1.2 0.6"/>' % (W_NEW, H))
    s.append('<rect x="0" y="0" width="150" height="85" fill="#f6f6f0" stroke="#000" stroke-width="0.3"/>')
    s.append('<text x="155" y="44" font-size="2.4px" fill="#2a8a2a" text-anchor="middle">+10</text>')
    for f in b.GetFootprints():
        ref = f.GetReference()
        f.BuildCourtyardCaches()
        for L in (pcbnew.F_CrtYd,):
            c = f.GetCourtyard(L)
            if not c.OutlineCount() or ref.startswith("H"):
                continue
            bb = c.BBox()
            x1, y1, x2, y2 = T(bb.GetLeft()) - ox, T(bb.GetTop()) - oy, T(bb.GetRight()) - ox, T(bb.GetBottom()) - oy
            if ref in MOVES:
                dx, dy = MOVES[ref]
                s.append('<rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" fill="none" stroke="#c06000" '
                         'stroke-width="0.2" stroke-dasharray="0.6 0.4"/>' % (x1, y1, x2 - x1, y2 - y1))
                s.append('<rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" fill="#ffd9a8" stroke="#c06000" '
                         'stroke-width="0.25"/>' % (x1 + dx, y1 + dy, x2 - x1, y2 - y1))
                s.append('<text x="%.2f" y="%.2f" font-size="1.8px" text-anchor="middle">%s</text>'
                         % ((x1 + x2) / 2 + dx, (y1 + y2) / 2 + dy + 0.6, ref))
            elif ref == "U501":
                s.append('<rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" fill="#dfe8fb" stroke="#1f4fd0" '
                         'stroke-width="0.2"/>' % (x1, max(y1, 0), x2 - x1, y2 - max(y1, 0)))
                s.append('<text x="%.2f" y="30" font-size="2.4px" fill="#1f4fd0">DevKit</text>' % (x1 + 8))
            else:
                s.append('<rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" fill="#d8d8d8" stroke="#999" '
                         'stroke-width="0.08"/>' % (x1, y1, x2 - x1, y2 - y1))
    for z in b.FindFootprintByReference("U501").Zones():
        if z.GetIsRuleArea():
            bb = z.GetBoundingBox()
            x1, y1, x2, y2 = T(bb.GetLeft()) - ox, T(bb.GetTop()) - oy, T(bb.GetRight()) - ox, T(bb.GetBottom()) - oy
            s.append('<rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" fill="#c02020" fill-opacity="0.15" '
                     'stroke="#c02020" stroke-width="0.25"/>' % (x1, y1, x2 - x1, y2 - y1))
            s.append('<text x="%.2f" y="%.2f" font-size="2.2px" fill="#c02020">Antenne (über der Kante)</text>'
                     % (x1, y1 - 0.8))
    for x1, y1, x2, y2 in USB:
        s.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="none" stroke="#1f4fd0" '
                 'stroke-width="0.2" stroke-dasharray="0.8 0.5"/>' % (x1, y1, x2 - x1, y2 - y1))
    s.append('<text x="127" y="70" font-size="1.8px" fill="#1f4fd0">USB-Stecker/Kabel</text>')
    for r in ("H1", "H2", "H3", "H4"):
        p = b.FindFootprintByReference(r).GetPosition()
        x, y = T(p.x) - ox, T(p.y) - oy
        s.append('<path d="M%.2f %.2f l2 2 m-2 0 l2 -2" stroke="#777" stroke-width="0.3" transform="translate(-1 -1)"/>'
                 % (x, y))
        s.append('<text x="%.2f" y="%.2f" font-size="1.8px" fill="#777">%s alt</text>' % (x + 1.5, y - 1.2, r))
    for name, (x, y) in HOLES.items():
        s.append('<circle cx="%.2f" cy="%.2f" r="5.5" fill="none" stroke="#7a3fb0" stroke-width="0.2" '
                 'stroke-dasharray="0.8 0.5"/>' % (x, y))
        s.append('<circle cx="%.2f" cy="%.2f" r="3.8" fill="#c02020" fill-opacity="0.12" stroke="#c02020" '
                 'stroke-width="0.15"/>' % (x, y))
        s.append('<circle cx="%.2f" cy="%.2f" r="3.5" fill="none" stroke="#333" stroke-width="0.15"/>' % (x, y))
        s.append('<circle cx="%.2f" cy="%.2f" r="2.85" fill="none" stroke="#333" stroke-width="0.12"/>' % (x, y))
        s.append('<circle cx="%.2f" cy="%.2f" r="3.175" fill="none" stroke="#2a8a2a" stroke-width="0.15" '
                 'stroke-dasharray="0.3 0.3"/>' % (x, y))
        s.append('<circle cx="%.2f" cy="%.2f" r="1.6" fill="#000"/>' % (x, y))
        ty = -1.8 if y < 40 else H + 3.6          # labels outside the board
        s.append('<text x="%.2f" y="%.2f" font-size="2.6px" font-weight="bold" text-anchor="middle">%s (%.1f | %.1f)</text>'
                 % (x, ty, name, x, y))
    # pattern dimensions
    s.append('<path d="M4.5 -6 H155.5 M4.5 -7 v2 M155.5 -7 v2" stroke="#1f4fd0" stroke-width="0.2"/>')
    s.append('<text x="80" y="-7" font-size="2.4px" fill="#1f4fd0" text-anchor="middle">Lochabstand 151,0</text>')
    s.append('<path d="M-6 4.5 V80.5 M-7 4.5 h2 M-7 80.5 h2" stroke="#1f4fd0" stroke-width="0.2"/>')
    s.append('<text x="-7.2" y="42.5" font-size="2.4px" fill="#1f4fd0" text-anchor="middle" '
             'transform="rotate(-90 -7.2 42.5)">Lochabstand 76,0</text>')
    lines = [
        "VORSCHLAG Variante B - Board nicht geändert. Kontur 160 x 85 (rechts +10 mm, grün), vier M3-Bohrungen an",
        "den Ecken, Lochbild 151 x 76 mm, Lochmitte 4,5 mm vom Rand.",
        "Je Loch: schwarz Ø 3,2 NPTH; grau Kopf Ø 5,7 und Scheibe Ø 7,0; rot Kupfersperre r 3,8; grün gepunktet",
        "Abstandshalter SW 5,5 (Ø 6,35, Unterseite); violett gestrichelt Werkzeugfreiraum Ø 11 (keine hohen Teile).",
        "Orange = Teile, die wandern (gestrichelt = heute): J101/TP101/F101 3 mm nach unten (VBAT_IN/VBAT_FUSED",
        "neu führen); LED-Reihe J108-J112 mit 1 mm Abstand ab x 10 (LED-Leitungen neu); R520/TP506 versetzen.",
        "Rechts: Erweiterung ohne Bauteile; C und D frei von DevKit, USB-Kabel und Antenne (C ca. 9 mm, zu prüfen).",
        "Grau x = bisherige H1-H4 (entfallen). Alle Beschlagmaße sind Annahmen; Chassismaße fehlen.",
    ]
    for i, ln in enumerate(lines):
        s.append('<text x="%.1f" y="%.1f" font-size="2.4px">%s</text>' % (-m + 2, H + 9 + i * 3.3, ln))
    s.append("</svg>")
    svg = out.with_suffix(".svg")
    out.parent.mkdir(parents=True, exist_ok=True)
    svg.write_text("\n".join(s))
    subprocess.run(["rsvg-convert", "-o", str(out), str(svg)], check=True)
    svg.unlink()
    print("written", out)


if __name__ == "__main__":
    main()
