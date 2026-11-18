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
    "overview": (-8, -14, 158, 93),
    "detail_input_logic": (-2, -2, 37, 78),
    "detail_servo_regulator": (33, -2, 95, 50),
    "detail_devkit_usb": (90, -12, 152, 102),
    "detail_logic_supply": (-1, 46, 36, 66),
    "detail_output_stages": (91, 6, 123, 47),
    "detail_controller_periphery": (119, 62, 151, 101),
    "operator_zone": (30, 36, 152, 88),
}
# Module and plug envelopes for the operator review (owner review 2026-11-16). Outlines are the footprints' F.Fab
# module outlines; heights are ESTIMATES (socket body 8.51 mm from the footprint description, module PCB 1.6 mm
# plus parts; DevKit socket height is open, O-4). USB: ESP32-S3-DevKitC-1 v1.1 has two Micro-USB receptacles at the
# lower board edge (Espressif user guide v1.1; DXF_ESP32-S3-DevKitC-1_V1.1_20220429, evaluated in
# rev1-versorgung-und-boardwahl.md 2.3): UART x 2.4-9.6, USB x 15.8-23.0 (DXF, origin lower left). In board
# coordinates (footprint origin J1-1 at 125.5|2.54; x = 125.5 - 1.27 + x_dxf) the receptacle centres are at
# x = 130.2 and 143.6 on the edge y = 63.84. Plug space per port: ESTIMATE overmold 11 mm wide, 30 mm long incl.
# strain relief, z 10.4-17.4 mm (receptacle centre about 13.9 mm: socket 8.5 + header collar 2.5 + PCB 1.6
# + half receptacle 1.3, all assumed; see render_populated_review.py).
USB_Y, USB_W, USB_L = 63.84, 11.0, 30.0
ENVELOPES = [  # (ref or None, label, height range mm, rect override)
    ("U501", "DevKit (Huelle, ca. 15,7 mm, Sockel O-4 offen)", (0.0, 15.7), None),
    ("J116", "OLED-Modul (Huelle, ca. 14,7 mm)", (0.0, 14.7), None),
    ("J115", "IMU-Modul (Huelle, ca. 13,1 mm)", (0.0, 13.1), None),
    (None, "Micro-USB UART (Stecker+Kabel, Schaetzung)", (10.4, 17.4),
     (130.2 - USB_W / 2, USB_Y, 130.2 + USB_W / 2, USB_Y + USB_L)),
    (None, "Micro-USB USB (Stecker+Kabel, Schaetzung)", (10.4, 17.4),
     (143.6 - USB_W / 2, USB_Y, 143.6 + USB_W / 2, USB_Y + USB_L)),
]
TALL = ["L401", "C406", "C407", "C101", "J101", "J102", "J103", "J104", "J105", "J106", "J107", "BZ101"]
BUTTONS = ["SW501", "SW502", "SW503"]
FINGER_R = 10.0  # review criterion (estimate): fingertip ~16 mm plus margin, no tall object inside this radius
NO_MODEL = ["BZ101", "D601", "D602", "D603", "D604", "D606", "D607", "D608", "J101", "J102", "J103", "J115", "J116",
            "Q101", "Q401", "Q402", "U501"]  # verify: models_3d (no model assigned / model file missing)
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


def fab_rect(board, ref):
    fp = board.FindFootprintByReference(ref)
    xs, ys = [], []
    for g in fp.GraphicalItems():
        if g.GetLayer() == pcbnew.F_Fab and isinstance(g, pcbnew.PCB_SHAPE):
            bb = g.GetBoundingBox()
            xs += [T(bb.GetLeft()), T(bb.GetRight())]
            ys += [T(bb.GetTop()), T(bb.GetBottom())]
    return (min(xs), min(ys), max(xs), max(ys))


def envelopes(board):
    out = []
    for ref, label, z, rect in ENVELOPES:
        out.append((label, rect or fab_rect(board, ref), z))
    return out


def rect_dist(px, py, r):
    dx = max(r[0] - px, 0, px - r[2])
    dy = max(r[1] - py, 0, py - r[3])
    return (dx * dx + dy * dy) ** 0.5


def finger_check(board, env):
    rows = []
    for b_ in BUTTONS:
        fp = board.FindFootprintByReference(b_)
        px, py = T(fp.GetPosition().x), T(fp.GetPosition().y)
        obst = [(lab.split(" (")[0], r) for lab, r, z in env]
        for ref in TALL:
            f = board.FindFootprintByReference(ref)
            f.BuildCourtyardCaches()
            bb = f.GetCourtyard(pcbnew.F_CrtYd).BBox()
            obst.append((ref, (T(bb.GetLeft()), T(bb.GetTop()), T(bb.GetRight()), T(bb.GetBottom()))))
        name, d = min(((n, rect_dist(px, py, r)) for n, r in obst), key=lambda a: a[1])
        # M3 markers count as a low obstacle (screw head about 3 mm): courtyard keep-out 4 mm, not the finger radius
        fp.BuildCourtyardCaches()
        bb = fp.GetCourtyard(pcbnew.F_CrtYd).BBox()
        cr = (T(bb.GetLeft()), T(bb.GetTop()), T(bb.GetRight()), T(bb.GetBottom()))
        hole = min(rect_dist(hx, hy, cr) for hx, hy in holes_on_board(board, k1=False))
        rows.append((b_, px, py, name, d, hole))
    return rows


def holes_on_board(board, k1=True):
    """Mounting hole centres read from the board (footprints MountingHole*), K1 or absolute coordinates (mm)."""
    e = board.GetBoardEdgesBoundingBox()
    ox, oy = (T(e.GetLeft()) + 0.05, T(e.GetTop()) + 0.05) if k1 else (0.0, 0.0)
    return [(T(f.GetPosition().x) - ox, T(f.GetPosition().y) - oy) for f in board.GetFootprints()
            if "MountingHole" in f.GetFPIDAsString()]


def svg(view, side, parts, draw, edges, copper, env=None, fingers=None):
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
    if env and side == "F":
        for lab, r, z in env:
            s.append('<rect x="%s" y="%s" width="%s" height="%s" fill="#2b6cb0" fill-opacity="0.10" stroke="#2b6cb0" '
                     'stroke-width="0.35" stroke-dasharray="1.5,0.8"/>' % (r[0], r[1], r[2] - r[0], r[3] - r[1]))
        for p in parts:
            if p["ref"] in NO_MODEL and p["side"] == side:
                bx, by, bw, bh = p["box"]
                s.append('<rect x="%s" y="%s" width="%s" height="%s" fill="none" stroke="#e00000" stroke-width="0.3" '
                         'stroke-dasharray="0.6,0.4"/>' % (bx, by, bw, bh))
        for b_, px, py, name, d, _h in fingers or []:
            col = "#1a9850" if d >= FINGER_R else "#d73027"
            s.append('<circle cx="%s" cy="%s" r="%s" fill="%s" fill-opacity="0.12" stroke="%s" stroke-width="0.3"/>'
                     % (px, py, FINGER_R, col, col))
    s.append("</g>")
    if env and side == "F":
        for lab, r, z in env:
            s.append('<text x="%s" y="%s" font-size="1.6" fill="#2b6cb0" font-family="Helvetica">%s</text>'
                     % (r[0] + 0.8, r[1] + 2.4, lab))
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
    if env and side == "F":
        s.append('<text x="%s" y="%s" font-size="1.3" fill="#e00000" font-family="Helvetica">rot gestrichelt = kein '
                 '3D-Modell (%s); blau = Modul-/Steckerhuellen (Schaetzung); Kreise r = %g mm Fingerzugang '
                 '(gruen frei, rot verletzt)</text>' % (x1 + 1, y2 + 7.6, ", ".join(NO_MODEL), FINGER_R))
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


def oblique(board, parts, env, fingers):
    """Isometric envelope view (no 3D models): board, module and plug envelopes, buttons, finger zones."""
    c30, s30 = 0.8660, 0.5

    def P(x, y, z):
        return ((x - y) * c30, (x + y) * s30 - z)

    def poly(pts, fill, op, stroke="#333"):
        return '<polygon points="%s" fill="%s" fill-opacity="%s" stroke="%s" stroke-width="0.25"/>' % (
            " ".join("%.2f,%.2f" % P(*q) for q in pts), fill, op, stroke)

    def box(r, z0, z1, fill, op):
        x1, y1, x2, y2 = r
        out = [poly([(x1, y2, z0), (x2, y2, z0), (x2, y2, z1), (x1, y2, z1)], fill, op),    # south face
               poly([(x2, y1, z0), (x2, y2, z0), (x2, y2, z1), (x2, y1, z1)], fill, op),    # east face
               poly([(x1, y1, z1), (x2, y1, z1), (x2, y2, z1), (x1, y2, z1)], fill, op)]    # top
        return out

    s = ['<svg xmlns="http://www.w3.org/2000/svg" width="2200" height="1500" viewBox="-95 -30 240 160">',
         '<rect x="-95" y="-30" width="240" height="160" fill="white"/>',
         poly([(0, 0, 0), (150, 0, 0), (150, 100, 0), (0, 100, 0)], "#2f6b3a", 0.9)]
    for p in parts:
        if p["side"] != "F":
            continue
        bx, by, bw, bh = p["box"]
        col = "#e00000" if p["ref"] in NO_MODEL else "#d8d0b0"
        s.append(poly([(bx, by, 0), (bx + bw, by, 0), (bx + bw, by + bh, 0), (bx, by + bh, 0)], col, 0.8, col))
    items = [(r, z, "#2b6cb0", 0.25) for lab, r, z in env]
    for b_ in BUTTONS:
        fp = board.FindFootprintByReference(b_)
        fp.BuildCourtyardCaches()
        bb = fp.GetCourtyard(pcbnew.F_CrtYd).BBox()
        items.append(((T(bb.GetLeft()), T(bb.GetTop()), T(bb.GetRight()), T(bb.GetBottom())), (0, 1.54), "#444", 0.9))
    for r, z, col, op in sorted(items, key=lambda it: it[0][2] + it[0][3]):
        s += box(r, z[0], z[1], col, op)
    for b_, px, py, name, d, _h in fingers:
        col = "#1a9850" if d >= FINGER_R else "#d73027"
        pts = [(px + FINGER_R * __import__("math").cos(a / 18 * 3.14159), py + FINGER_R *
                __import__("math").sin(a / 18 * 3.14159), 1.6) for a in range(36)]
        s.append('<polygon points="%s" fill="%s" fill-opacity="0.15" stroke="%s" stroke-width="0.3"/>'
                 % (" ".join("%.2f,%.2f" % P(*q) for q in pts), col, col))
        X, Y = P(px, py, 4)
        s.append('<text x="%.1f" y="%.1f" font-size="2.2" font-family="Helvetica" text-anchor="middle">%s</text>'
                 % (X, Y, {"SW501": "ENABLE", "SW502": "RESET", "SW503": "BOOT"}[b_]))
    s.append('<text x="-92" y="-24" font-size="3" font-family="Helvetica">Schraege Huellenansicht (isometrisch, '
             'keine 3D-Modelle): Modul- und USB-Huellen blau (Hoehen geschaetzt), Taster grau (1,54 mm laut '
             'KiCad-Modell),</text>')
    s.append('<text x="-92" y="-20" font-size="3" font-family="Helvetica">Fingerzonen r = %g mm (gruen frei); '
             'Micro-USB-Steckerraeume (UART, USB) nach Espressif-DXF v1.1, Steckergroesse geschaetzt</text>' % FINGER_R)
    s.append('<text x="-92" y="-16" font-size="3" fill="#c00000" font-family="Helvetica">Rote Flaechen = Bauteile '
             'ohne 3D-Modell: %s</text>' % ", ".join(NO_MODEL))
    s.append("</svg>")
    return "\n".join(s)


def main():
    pcb = ROOT / "RoverCore.kicad_pcb"
    board = pcbnew.LoadBoard(str(pcb))
    parts, draw, copper = collect(board)
    env = envelopes(board)
    fingers = finger_check(board, env)
    for b_, px, py, name, d, hole in fingers:
        print("finger access %s (%.1f|%.1f): nearest tall object %s at %.1f mm (criterion %g mm) %s; "
              "M3 marker %.1f mm from the courtyard (keep-out 4 mm) %s"
              % (b_, px, py, name, d, FINGER_R, "OK" if d >= FINGER_R else "VIOLATED", hole,
                 "OK" if hole >= 4 else "VIOLATED"))
    edges = ratsnest(pcb)
    OUT.mkdir(parents=True, exist_ok=True)
    for name, view in VIEWS.items():
        for side in ("F", "B"):
            stem = "%s_%s" % (name, "top" if side == "F" else "bottom")
            f = OUT / (stem + ".svg")
            f.write_text(svg(view, side, parts, draw, edges, copper, env, fingers))
            if shutil.which("rsvg-convert"):
                subprocess.run(["rsvg-convert", "-o", str(OUT / (stem + ".png")), str(f)], check=True)
    (OUT / "oblique_envelopes.svg").write_text(oblique(board, parts, env, fingers))
    if shutil.which("rsvg-convert"):
        subprocess.run(["rsvg-convert", "-o", str(OUT / "oblique_envelopes.png"), str(OUT / "oblique_envelopes.svg")],
                       check=True)
    print("wrote %d views + oblique_envelopes to %s (%d ratsnest edges)" % (2 * len(VIEWS), OUT, len(edges)))


if __name__ == "__main__":
    main()
