#!/usr/bin/env python3
"""Symbols and footprints for the two plug-in modules on Sensors_Display (female header on the carrier).

Source of every number below: the original Adafruit EagleCAD files (CC BY-SA, Adafruit Industries),
read with an XML parser, not from photos:
  - adafruit/Adafruit-LSM6DSOX-PCB  Adafruit_LSM6DSOX.brd/.sch   (product 4438, commit c05abef 2020-09-07)
  - adafruit/Adafruit-128x64-Monochrome-OLED-PCB  "Adafruit 0.96in 128x64 OLED STEMMA QT.brd/.sch"
    (product 326, STEMMA QT revision; board files commit 1031d65 2020-08-06, XML conversion 2797692 2026-06-03)
Eagle coordinates are top view, origin lower-left, y up. Footprint coordinates: origin at pad 1, KiCad y down,
x = X - X_pad1, y = Y_pad1 - Y. The module is plugged component side UP, so the carrier top view equals the
module top view (no mirroring). Pads are the carrier female-header pads (1.0 mm drill like the module).

4438 (board 25.40 x 17.78 mm, corners R2.54): JP1 1x9 at Y = 2.54, X = 2.54 + 2.54 (n - 1):
  1 VIN, 2 3Vo, 3 GND, 4 SCL, 5 SDA, 6 DO, 7 CS, 8 INT1, 9 INT2. JP2 1x5 (aux bus) at Y = 15.24 is not used.
  Mounting holes 2.5 mm plated at (2.54, 15.24) and (22.86, 15.24).
326 STEMMA QT (board 29.21 x 31.75 mm with a 19.05 x 5.08 mm notch at Y < 5.08 between X 5.08..24.13):
  JP2 1x8 at Y = 29.21, X = 23.495 - 2.54 (n - 1): 1 Data(SDA), 2 Clk(SCL), 3 DC/A0, 4 Rst, 5 CS, 6 3Vo, 7 Vin, 8 GND.
  Mounting holes 2.5 mm plated at (2.54, 2.54), (26.67, 2.54), (2.54, 29.21), (26.67, 29.21).
  The two holes in the header row (Y = 29.21) are only 3.175 mm from pads 1 and 8: a standoff there would collide
  with the carrier socket body, so only the two holes on the corner tabs (Y = 2.54) get carrier NPTH holes.

Usage: python3 hardware/scripts/make_sensor_module_sockets.py   (rewrites only these library items)
"""
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from make_devkit_socket import SYM_LIB, FP_DIR, prop, pin, rect, line, poly, text  # noqa: E402

HOLE = 2.7  # carrier NPTH for an M2.5 standoff screw (module holes 2.5 mm plated)
# Carrier socket: Samtec SSW-1xx-01-T-S (drawing SSW-1XX-XX-XXX-X-XX-XXX-XX rev CJ, sheet 1): body 2.41 mm wide,
# length N x 2.54 + 0.51 mm, 8.51 mm above the board, tail 0.79 x 0.41 mm, 2.64 mm long (lead style -01).
# The drawing gives no PCB hole; 1.0 mm drill leaves 0.11 mm on the 0.89 mm tail diagonal (check, O-31).
SOCKET_W, SOCKET_EXTRA, SOCKET_H = 2.41, 0.51, 8.51

MODULES = {
    "Adafruit_4438_LSM6DSOX_Socket": dict(
        fp="Adafruit_4438_LSM6DSOX_Socket_1x09_P2.54mm",
        ref="J", pins=["VIN", "3Vo", "GND", "SCL", "SDA", "DO", "CS", "INT1", "INT2"],
        pad1=(2.54, 2.54), step=+2.54, board=(0.0, 0.0, 25.40, 17.78), notch=None,
        holes=[(2.54, 15.24), (22.86, 15.24)], fab_holes=[],
        unused=[("JP2 aux 1x5 - no header, no socket", 12.7, 15.24)],
        title="Adafruit 4438 LSM6DSOX", socket="SSW-109-01-T-S",
        desc="Carrier female header 1x9 2.54 mm for Adafruit 4438 (LSM6DSOX), plugged component side up. "
             "Pins per Adafruit_LSM6DSOX.brd: 1 VIN, 2 3Vo, 3 GND, 4 SCL, 5 SDA, 6 DO, 7 CS, 8 INT1, 9 INT2. "
             "Two NPTH 2.7 mm for M2.5 standoffs at the module holes; aux header JP2 unused.",
        datasheet="https://github.com/adafruit/Adafruit-LSM6DSOX-PCB"),
    "Adafruit_326_OLED_Socket": dict(
        fp="Adafruit_326_OLED128x64_Socket_1x08_P2.54mm",
        ref="J", pins=["Data", "Clk", "DC", "Rst", "CS", "3Vo", "Vin", "GND"],
        pad1=(23.495, 29.21), step=-2.54, board=(0.0, 0.0, 29.21, 31.75), notch=(5.08, 0.0, 24.13, 5.08),
        holes=[(2.54, 2.54), (26.67, 2.54)], fab_holes=[(2.54, 29.21), (26.67, 29.21)],
        unused=[],
        title="Adafruit 326 OLED 0.96in", socket="SSW-108-01-T-S",
        desc="Carrier female header 1x8 2.54 mm for Adafruit 326 (0.96in 128x64 SSD1306, STEMMA QT revision), plugged "
             "component side up. Pins per 'Adafruit 0.96in 128x64 OLED STEMMA QT.brd': 1 Data, 2 Clk, 3 DC/A0, 4 Rst, "
             "5 CS, 6 3Vo, 7 Vin, 8 GND. NPTH 2.7 mm only at the two corner-tab holes; the holes beside the header "
             "are too close to the socket for a standoff.",
        datasheet="https://github.com/adafruit/Adafruit-128x64-Monochrome-OLED-PCB"),
}



def socket_model(n, dx=0.0, rot=0):
    """KiCad library model of a generic 2.54 mm vertical female socket (not the Samtec part; review 2026-11-16)."""
    return ('\t(model "${KICAD10_3DMODEL_DIR}/Connector_PinSocket_2.54mm.3dshapes/PinSocket_1x%02d_P2.54mm_Vertical.step"\n'
            '\t\t(offset\n\t\t\t(xyz %s 0 0)\n\t\t)\n\t\t(scale\n\t\t\t(xyz 1 1 1)\n\t\t)\n'
            '\t\t(rotate\n\t\t\t(xyz 0 0 %s)\n\t\t)\n\t)\n') % (n, dx, rot)

def symbol(name, m):
    n = len(m["pins"])
    top = round((n - 1) * 2.54 / 2, 2)
    top = round(round(top / 2.54) * 2.54, 2)
    pins = "".join(pin(str(i + 1), p, -7.62, round(top - i * 2.54, 2), 0) for i, p in enumerate(m["pins"]))
    y_top, y_bot = round(top + 2.54, 2), round(top - (n - 1) * 2.54 - 2.54, 2)
    return ('\t(symbol "%s"\n\t\t(exclude_from_sim no)\n\t\t(in_bom yes)\n\t\t(on_board yes)\n' % name
            + prop("Reference", m["ref"], -5.08, y_top + 1.27, justify="left")
            + prop("Value", m["title"], -5.08, y_bot - 1.27, justify="left")
            + prop("Footprint", "ProjectFootprints:" + m["fp"], 0, y_bot - 3.81, hide=True)
            + prop("Datasheet", m["datasheet"], 0, y_bot - 6.35, hide=True)
            + prop("Description", m["desc"], 0, 0, hide=True)
            + prop("ki_keywords", "Adafruit module socket header", 0, 0, hide=True)
            + '\t\t(symbol "%s_0_1"\n\t\t\t(rectangle\n\t\t\t\t(start -5.08 %s)\n\t\t\t\t(end 5.08 %s)\n'
              '\t\t\t\t(stroke\n\t\t\t\t\t(width 0.254)\n\t\t\t\t\t(type default)\n\t\t\t\t)\n\t\t\t\t(fill\n'
              '\t\t\t\t\t(type background)\n\t\t\t\t)\n\t\t\t)\n\t\t)\n' % (name, y_top, y_bot)
            + '\t\t(symbol "%s_1_1"\n%s\t\t)\n\t\t(embedded_fonts no)\n\t)\n' % (name, pins))


def write_symbols():
    text_ = SYM_LIB.read_text()
    for name, m in MODULES.items():
        block = symbol(name, m)
        hit = re.search(r'(?ms)^\t\(symbol "%s"\n.*?^\t\)\n' % re.escape(name), text_)
        if hit:
            text_ = text_[:hit.start()] + block + text_[hit.end():]
        else:
            i = text_.rstrip().rfind(")")
            text_ = text_[:i] + block + text_[i:]
    SYM_LIB.write_text(text_)


def pad(num, x, y, shape):
    rr = "\n\t\t(roundrect_rratio 0.25)" if shape == "roundrect" else ""
    return ('\t(pad "%d" thru_hole %s\n\t\t(at %s %s)\n\t\t(size 1.7 1.7)\n\t\t(drill 1)\n'
            '\t\t(layers "*.Cu" "*.Mask")\n\t\t(remove_unused_layers no)%s\n\t)\n') % (num, shape, round(x, 3), round(y, 3), rr)


def npth(x, y):
    return ('\t(pad "" np_thru_hole circle\n\t\t(at %s %s)\n\t\t(size %s %s)\n\t\t(drill %s)\n'
            '\t\t(layers "*.Cu" "*.Mask")\n\t)\n') % (round(x, 3), round(y, 3), HOLE, HOLE, HOLE)


def circle(layer, x, y, r, w=0.1):
    return ('\t(fp_circle\n\t\t(center %s %s)\n\t\t(end %s %s)\n\t\t(stroke\n\t\t\t(width %s)\n\t\t\t(type solid)\n'
            '\t\t)\n\t\t(fill no)\n\t\t(layer "%s")\n\t)\n') % (round(x, 3), round(y, 3), round(x + r, 3), round(y, 3), w, layer)


def footprint(name, m):
    X1, Y1 = m["pad1"]
    tx = lambda X: X - X1          # noqa: E731
    ty = lambda Y: Y1 - Y          # noqa: E731
    bx0, by0, bx1, by1 = m["board"]
    n = len(m["pins"])
    body = ('(footprint "%s"\n\t(version 20260206)\n\t(generator "rovercore_make_sensor_module_sockets")\n'
            '\t(generator_version "10.0")\n\t(layer "F.Cu")\n\t(descr "%s Source: %s (Eagle board file).")\n'
            '\t(tags "Adafruit module socket 2.54mm")\n') % (m["fp"], m["desc"], m["datasheet"])
    cx, cy = (tx(bx0) + tx(bx1)) / 2, (ty(by0) + ty(by1)) / 2
    body += text("Reference", "REF**", cx, min(ty(by0), ty(by1)) - 1.5, "F.SilkS")
    body += text("Value", m["fp"], cx, max(ty(by0), ty(by1)) + 1.5, "F.Fab")
    for k in ("Datasheet", "Description"):
        body += ('\t(property "%s" ""\n\t\t(at 0 0 0)\n\t\t(layer "F.Fab")\n\t\t(hide yes)\n\t\t(effects\n\t\t\t(font\n'
                 '\t\t\t\t(size 1.27 1.27)\n\t\t\t\t(thickness 0.15)\n\t\t\t)\n\t\t)\n\t)\n') % k
    body += "\t(attr through_hole)\n"
    # module outline (fabrication) incl. the OLED notch, and the module's own holes
    if m["notch"]:
        nx0, ny0, nx1, ny1 = m["notch"]
        pts = [(bx0, by0), (nx0, by0), (nx0, ny1), (nx1, ny1), (nx1, by0), (bx1, by0), (bx1, by1), (bx0, by1)]
        for a, b in zip(pts, pts[1:] + pts[:1]):
            body += line("F.Fab", tx(a[0]), ty(a[1]), tx(b[0]), ty(b[1]), 0.1)
    else:
        body += rect("F.Fab", tx(bx0), ty(by0), tx(bx1), ty(by1), 0.1)
    # carrier socket body (Samtec SSW) on F.Fab, centred on the pad row
    length = n * 2.54 + SOCKET_EXTRA
    mid = (n - 1) * m["step"] / 2
    body += rect("F.Fab", mid - length / 2, -SOCKET_W / 2, mid + length / 2, SOCKET_W / 2, 0.1)
    body += text("user", "SSW-1%02d-01-T-S, %.2f mm high" % (n, SOCKET_H), mid, SOCKET_W / 2 + 0.9, "F.Fab", 0.6)
    for X, Y in m["holes"] + m["fab_holes"]:
        body += circle("F.Fab", tx(X), ty(Y), 1.25)
    for X, Y in m["fab_holes"]:
        body += text("user", "no standoff", tx(X), ty(Y) + 2.2, "F.Fab", 0.6)
    for label, X, Y in m["unused"]:
        body += text("user", label, tx(X), ty(Y) + 2.0, "F.Fab", 0.6)
    body += text("user", m["title"] + " - component side up", cx, cy, "F.Fab", 0.8)
    body += text("user", "${REFERENCE}", cx, cy + 1.6, "F.Fab", 0.8)
    # silkscreen: module outline (clear of pads), pin-1 mark, pin names
    o = 0.15
    body += rect("F.SilkS", min(tx(bx0), tx(bx1)) - o, min(ty(by0), ty(by1)) - o,
                 max(tx(bx0), tx(bx1)) + o, max(ty(by0), ty(by1)) + o, 0.12)
    s = 1 if m["step"] > 0 else -1
    body += poly("F.SilkS", [(-s * 1.6, 1.2), (-s * 1.6, 2.4), (-s * 0.6, 1.8)])
    # pin names at the board's minimum text height (0.8 mm); 0.8 mm names do not fit the 2.54 mm pitch side by side,
    # so they alternate between the outer side of the pad row and the side under the module (owner review 2026-11-16)
    out = -1 if ty(by0) > 0 else 1
    for i, p in enumerate(m["pins"]):
        body += text("user", p, i * m["step"], (out if i % 2 == 0 else -out) * 1.85, "F.SilkS", 0.8)
    # courtyard: module outline + 0.25 mm (the module overhangs the socket)
    c = 0.25
    body += rect("F.CrtYd", min(tx(bx0), tx(bx1)) - c, min(ty(by0), ty(by1)) - c,
                 max(tx(bx0), tx(bx1)) + c, max(ty(by0), ty(by1)) + c, 0.05)
    for i in range(n):
        body += pad(i + 1, i * m["step"], 0.0, "rect" if i == 0 else "roundrect")
    for X, Y in m["holes"]:
        body += npth(tx(X), ty(Y))
    body += socket_model(n, 0.0, -90 if m["step"] > 0 else 90)  # pins along +x / -x (checked in the 3D render)
    body += "\t(embedded_fonts no)\n)\n"
    FP_DIR.mkdir(parents=True, exist_ok=True)
    (FP_DIR / (m["fp"] + ".kicad_mod")).write_text(body)


if __name__ == "__main__":
    write_symbols()
    for name, m in MODULES.items():
        footprint(name, m)
        print("wrote", name, "and", m["fp"])
