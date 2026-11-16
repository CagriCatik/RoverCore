#!/usr/bin/env python3
"""Symbol and footprint for the ESP32-S3-DevKitC-1 v1.1 carrier socket (two 1x22 female headers).

Pin assignment: Espressif ESP32-S3-DevKitC-1 User Guide v1.1, header blocks J1 and J3
(also hardware/interfaces/pinmap.csv). Geometry: Espressif DXF
DXF_ESP32-S3-DevKitC-1_V1.1_20220429.dxf as evaluated in docs/vcu/rev1-versorgung-und-boardwahl.md 2.3:
board 25.40 x 62.865 mm, rows 22.86 mm apart (x = 1.27 / 24.13), pin 1 of both rows at the
antenna end (y = 61.30), pitch 2.54 mm, antenna overhang 18.0 x 6.31 mm beyond the board edge.
The overhang's x position is not dimensioned in the evaluated DXF data; it is drawn centred and
must be confirmed on the real board (O-4).

Footprint view = top of the carrier with the DevKit plugged in component side up:
J1 is the left row, J3 the right row, antenna end at the top, USB connectors at the bottom.
Pads 1-22 = J1-1..J1-22, pads 23-44 = J3-1..J3-22. All symbol pins are passive (socket).

Usage: python3 hardware/scripts/make_devkit_socket.py   (rewrites only these two library items)
"""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
SYM_LIB = ROOT / "hardware/libraries/symbols/ProjectSymbols.kicad_sym"
FP_DIR = ROOT / "hardware/libraries/footprints/ProjectFootprints.pretty"
NAME = "ESP32-S3-DevKitC-1_Socket"
FP_NAME = "ESP32-S3-DevKitC-1_v1.1_Socket_2x1x22_P2.54mm"

J1 = ["3V3", "3V3", "RST", "GPIO4", "GPIO5", "GPIO6", "GPIO7", "GPIO15", "GPIO16", "GPIO17", "GPIO18",
      "GPIO8", "GPIO3", "GPIO46", "GPIO9", "GPIO10", "GPIO11", "GPIO12", "GPIO13", "GPIO14", "5V", "G"]
J3 = ["G", "TX", "RX", "GPIO1", "GPIO2", "GPIO42", "GPIO41", "GPIO40", "GPIO39", "GPIO38", "GPIO37",
      "GPIO36", "GPIO35", "GPIO0", "GPIO45", "GPIO48", "GPIO47", "GPIO21", "GPIO20", "GPIO19", "G", "G"]
assert len(J1) == len(J3) == 22

PITCH, ROW = 2.54, 22.86



def socket_model(n, dx=0.0, rot=0):
    """KiCad library model of a generic 2.54 mm vertical female socket (not the Samtec part; review 2026-11-16)."""
    return ('\t(model "${KICAD10_3DMODEL_DIR}/Connector_PinSocket_2.54mm.3dshapes/PinSocket_1x%02d_P2.54mm_Vertical.step"\n'
            '\t\t(offset\n\t\t\t(xyz %s 0 0)\n\t\t)\n\t\t(scale\n\t\t\t(xyz 1 1 1)\n\t\t)\n'
            '\t\t(rotate\n\t\t\t(xyz 0 0 %s)\n\t\t)\n\t)\n') % (n, dx, rot)

def font():
    return "(effects\n\t\t\t\t\t\t(font\n\t\t\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t\t\t)\n\t\t\t\t\t)"


def prop(name, value, x, y, hide=False, justify=None):
    j = "\n\t\t\t\t(justify %s)" % justify if justify else ""
    h = "\n\t\t\t\t(hide yes)" if hide else ""
    return ('\t\t(property "%s" "%s"\n\t\t\t(at %s %s 0)\n\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 1.27 1.27)\n'
            '\t\t\t\t)%s%s\n\t\t\t)\n\t\t)\n') % (name, value, x, y, j, h)


def pin(number, name, x, y, angle):
    return ('\t\t\t(pin passive line\n\t\t\t\t(at %s %s %d)\n\t\t\t\t(length 2.54)\n\t\t\t\t(name "%s"\n\t\t\t\t\t%s\n'
            '\t\t\t\t)\n\t\t\t\t(number "%s"\n\t\t\t\t\t%s\n\t\t\t\t)\n\t\t\t)\n') % (x, y, angle, name, font(), number, font())


def symbol():
    top = 13 * PITCH  # pins on the 2.54 grid: J1-1/J3-1 at y = 30.48, J1-22/J3-22 at y = -22.86
    pins = ""
    for i, n in enumerate(J1):
        pins += pin(str(i + 1), "J1-%d/%s" % (i + 1, n), -17.78, round(top - (i + 1) * PITCH, 2), 0)
    for i, n in enumerate(J3):
        pins += pin(str(23 + i), "J3-%d/%s" % (i + 1, n), 17.78, round(top - (i + 1) * PITCH, 2), 180)
    y_top, y_bot = round(top + 1.27 - PITCH + PITCH, 2), round(top - 22 * PITCH - 1.27, 2)
    return ('\t(symbol "%s"\n\t\t(exclude_from_sim no)\n\t\t(in_bom yes)\n\t\t(on_board yes)\n' % NAME
            + prop("Reference", "U", -15.24, y_top + 3.81, justify="left")
            + prop("Value", NAME, 15.24, y_top + 1.27, justify="right")
            + prop("Footprint", "ProjectFootprints:" + FP_NAME, 0, y_bot - 2.54, hide=True)
            + prop("Datasheet", "https://docs.espressif.com/projects/esp-dev-kits/en/latest/esp32s3/esp32-s3-devkitc-1/user_guide_v1.1.html", 0, y_bot - 5.08, hide=True)
            + prop("Description", "Carrier socket for an original Espressif ESP32-S3-DevKitC-1-N16R8 v1.1: two 1x22 female headers "
                   "2.54 mm, rows 22.86 mm apart; pins 1-22 = DevKit J1, 23-44 = DevKit J3 (User Guide v1.1)", 0, 0, hide=True)
            + prop("ki_keywords", "ESP32-S3 DevKitC socket carrier", 0, 0, hide=True)
            + '\t\t(symbol "%s_0_1"\n\t\t\t(rectangle\n\t\t\t\t(start -15.24 %s)\n\t\t\t\t(end 15.24 %s)\n'
              '\t\t\t\t(stroke\n\t\t\t\t\t(width 0.254)\n\t\t\t\t\t(type default)\n\t\t\t\t)\n\t\t\t\t(fill\n'
              '\t\t\t\t\t(type background)\n\t\t\t\t)\n\t\t\t)\n\t\t)\n' % (NAME, y_top, y_bot)
            + '\t\t(symbol "%s_1_1"\n%s\t\t)\n\t\t(embedded_fonts no)\n\t)\n' % (NAME, pins))


def write_symbol():
    text = SYM_LIB.read_text()
    block = symbol()
    m = re.search(r'(?ms)^\t\(symbol "%s"\n.*?^\t\)\n' % re.escape(NAME), text)
    if m:
        text = text[:m.start()] + block + text[m.end():]
    else:
        i = text.rstrip().rfind(")")
        text = text[:i] + block + text[i:]
    SYM_LIB.write_text(text)


def line(layer, x1, y1, x2, y2, w):
    return ('\t(fp_line\n\t\t(start %s %s)\n\t\t(end %s %s)\n\t\t(stroke\n\t\t\t(width %s)\n\t\t\t(type solid)\n'
            '\t\t)\n\t\t(layer "%s")\n\t)\n') % (round(x1, 3), round(y1, 3), round(x2, 3), round(y2, 3), w, layer)


def rect(layer, x1, y1, x2, y2, w):
    return ('\t(fp_rect\n\t\t(start %s %s)\n\t\t(end %s %s)\n\t\t(stroke\n\t\t\t(width %s)\n\t\t\t(type solid)\n'
            '\t\t)\n\t\t(fill no)\n\t\t(layer "%s")\n\t)\n') % (round(x1, 3), round(y1, 3), round(x2, 3), round(y2, 3), w, layer)


def poly(layer, pts, w=0.12, fill="yes"):
    xy = " ".join("(xy %s %s)" % (round(x, 3), round(y, 3)) for x, y in pts)
    return ('\t(fp_poly\n\t\t(pts %s)\n\t\t(stroke\n\t\t\t(width %s)\n\t\t\t(type solid)\n\t\t)\n\t\t(fill %s)\n'
            '\t\t(layer "%s")\n\t)\n') % (xy, w, fill, layer)


def text(kind, value, x, y, layer, size=1.0, hide=False):
    h = "\n\t\t(hide yes)" if hide else ""
    if kind in ("Reference", "Value"):
        return ('\t(property "%s" "%s"\n\t\t(at %s %s 0)\n\t\t(layer "%s")%s\n\t\t(effects\n\t\t\t(font\n'
                '\t\t\t\t(size %s %s)\n\t\t\t\t(thickness 0.15)\n\t\t\t)\n\t\t)\n\t)\n') % (kind, value, x, y, layer, h, size, size)
    return ('\t(fp_text user "%s"\n\t\t(at %s %s 0)\n\t\t(layer "%s")\n\t\t(effects\n\t\t\t(font\n'
            '\t\t\t\t(size %s %s)\n\t\t\t\t(thickness 0.15)\n\t\t\t)\n\t\t)\n\t)\n') % (value, x, y, layer, size, size)


def pad(num, x, y, shape):
    rr = "\n\t\t(roundrect_rratio 0.25)" if shape == "roundrect" else ""
    return ('\t(pad "%d" thru_hole %s\n\t\t(at %s %s)\n\t\t(size 1.7 1.7)\n\t\t(drill 1)\n'
            '\t\t(layers "*.Cu" "*.Mask")\n\t\t(remove_unused_layers no)%s\n\t)\n') % (num, shape, round(x, 3), round(y, 3), rr)


def footprint():
    # Coordinates: origin at J1-1, +y towards the USB end. DXF (origin lower-left, y up) -> here:
    # x = X - 1.27, y = 61.30 - Y.
    bx0, bx1 = -1.27, 25.40 - 1.27
    by0, by1 = 61.30 - 62.865, 61.30 - 0.0
    ax0, ax1 = (25.40 - 18.0) / 2 - 1.27, (25.40 + 18.0) / 2 - 1.27        # assumed centred (O-4)
    ay0, ay1 = 61.30 - 69.15, 61.30 - 62.84
    body = ('(footprint "%s"\n\t(version 20260206)\n\t(generator "rovercore_make_devkit_socket")\n\t(generator_version "10.0")\n'
            '\t(layer "F.Cu")\n\t(descr "Carrier socket for Espressif ESP32-S3-DevKitC-1 v1.1: 2 x 1x22 female headers, 2.54 mm, '
            'rows 22.86 mm; pads 1-22 = J1, 23-44 = J3; outline from Espressif DXF V1.1 20220429; antenna overhang drawn '
            'centred (confirm, O-4)")\n\t(tags "ESP32-S3 DevKitC-1 socket")\n') % FP_NAME
    body += text("Reference", "REF**", ROW / 2, by0 - 9.5, "F.SilkS")
    body += text("Value", FP_NAME, ROW / 2, by1 + 3.5, "F.Fab")
    body += ('\t(property "Datasheet" ""\n\t\t(at 0 0 0)\n\t\t(layer "F.Fab")\n\t\t(hide yes)\n\t\t(effects\n\t\t\t(font\n'
             '\t\t\t\t(size 1.27 1.27)\n\t\t\t\t(thickness 0.15)\n\t\t\t)\n\t\t)\n\t)\n')
    body += ('\t(property "Description" ""\n\t\t(at 0 0 0)\n\t\t(layer "F.Fab")\n\t\t(hide yes)\n\t\t(effects\n\t\t\t(font\n'
             '\t\t\t\t(size 1.27 1.27)\n\t\t\t\t(thickness 0.15)\n\t\t\t)\n\t\t)\n\t)\n')
    body += "\t(attr through_hole)\n"
    # fabrication: DevKit outline, antenna overhang, USB positions
    body += rect("F.Fab", bx0, by0, bx1, by1, 0.1)
    body += rect("F.Fab", ax0, ay0, ax1, ay1, 0.1)
    body += text("user", "ANTENNA - no copper/parts", ROW / 2, (ay0 + ay1) / 2, "F.Fab", 0.8)
    body += text("user", "UART", (2.4 + 9.6) / 2 - 1.27, by1 - 1.5, "F.Fab", 0.8)
    body += text("user", "USB", (15.8 + 23.0) / 2 - 1.27, by1 - 1.5, "F.Fab", 0.8)
    body += text("user", "${REFERENCE}", ROW / 2, 30, "F.Fab", 1.0)
    # silkscreen: outline clear of the pads, pin-1 marks for both rows, orientation text
    o = 0.15
    body += rect("F.SilkS", bx0 - o, by0 - o, bx1 + o, by1 + o, 0.12)
    for x in (0.0, ROW):
        body += poly("F.SilkS", [(x - 2.2, -0.8), (x - 2.2, 0.8), (x - 1.4, 0.0)])
    body += text("user", "J1-1", 3.8, 0.0, "F.SilkS", 0.8)
    body += text("user", "J3-1", ROW - 3.8, 0.0, "F.SilkS", 0.8)
    body += text("user", "ANT", ROW / 2, 2.0, "F.SilkS", 1.0)
    body += text("user", "USB", ROW / 2, by1 - 2.0, "F.SilkS", 1.0)
    body += poly("F.SilkS", [(ROW / 2 - 1.0, by1 - 0.6), (ROW / 2 + 1.0, by1 - 0.6), (ROW / 2, by1 + 0.6)])
    # courtyard: DevKit outline plus antenna overhang, 0.25 mm
    c = 0.25
    body += rect("F.CrtYd", bx0 - c, ay0 - c, bx1 + c, by1 + c, 0.05)
    # antenna keep-out on all copper layers
    body += ('\t(zone\n\t\t(net 0)\n\t\t(net_name "")\n\t\t(layers "*.Cu")\n\t\t(uuid "6b0f3d6e-5d1a-4c55-9d1e-3c4e2a7b0e11")\n'
             '\t\t(name "DevKit antenna keep-out")\n\t\t(hatch edge 0.5)\n\t\t(connect_pads\n\t\t\t(clearance 0)\n\t\t)\n'
             '\t\t(min_thickness 0.25)\n\t\t(filled_areas_thickness no)\n\t\t(keepout\n\t\t\t(tracks not_allowed)\n'
             '\t\t\t(vias not_allowed)\n\t\t\t(pads not_allowed)\n\t\t\t(copperpour not_allowed)\n\t\t\t(footprints not_allowed)\n'
             '\t\t)\n\t\t(placement\n\t\t\t(enabled no)\n\t\t\t(sheetname "")\n\t\t)\n\t\t(fill\n\t\t\t(thermal_gap 0.5)\n'
             '\t\t\t(thermal_bridge_width 0.5)\n\t\t)\n\t\t(polygon\n\t\t\t(pts\n\t\t\t\t(xy %s %s) (xy %s %s) (xy %s %s) (xy %s %s)\n'
             '\t\t\t)\n\t\t)\n\t)\n') % (round(ax0 - 1, 3), round(ay0 - 1, 3), round(ax1 + 1, 3), round(ay0 - 1, 3),
                                        round(ax1 + 1, 3), round(ay1, 3), round(ax0 - 1, 3), round(ay1, 3))
    for i in range(22):
        body += pad(i + 1, 0.0, i * PITCH, "rect" if i == 0 else "roundrect")
    for i in range(22):
        body += pad(23 + i, ROW, i * PITCH, "rect" if i == 0 else "roundrect")
    body += socket_model(22, 0.0) + socket_model(22, ROW)  # J1 and J3, generic library sockets
    body += "\t(embedded_fonts no)\n)\n"
    FP_DIR.mkdir(parents=True, exist_ok=True)
    (FP_DIR / (FP_NAME + ".kicad_mod")).write_text(body)


if __name__ == "__main__":
    write_symbol()
    footprint()
    print("wrote", NAME, "and", FP_NAME)
