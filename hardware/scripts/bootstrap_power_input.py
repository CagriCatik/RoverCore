#!/usr/bin/env python3
"""One-time bootstrap of the RoverCore Power sheet: battery input and input protection.

Writes Power.kicad_sch (child sheet) and adds the sheet to RoverCore.kicad_sch.
Symbols are copied verbatim from KiCad 10.0.7's official libraries; pins are
connected by net labels or power symbols placed exactly on pin endpoints.
Design basis: docs/vcu/rev1-versorgung-und-boardwahl.md section 3.9 (3S).

After the bootstrap the KiCad files are the hardware truth; edit them in
KiCad. The script refuses to run when Power.kicad_sch already exists or a
KiCad lock file is present. Verify the result with
`kicad-cli sch export netlist` and `scripts/kit verify .`.

Usage: python3 hardware/scripts/bootstrap_power_input.py
"""
import math
from pathlib import Path
import re
import sys
import uuid

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.core import kicad_env  # noqa: E402

PROJECT = "RoverCore"
ROOT_SCH = ROOT / "RoverCore.kicad_sch"
SHEET_FILE = "Power.kicad_sch"
NS = uuid.UUID("2b6c8c0e-1d43-4f0a-9b6e-52f0c4a7d101")  # stable UUIDs -> reviewable diffs

XT30 = "Pin 1 = minus, pin 2 = plus per KiCad footprint silkscreen; confirm against the battery lead (O-15)"

# ref, lib_id, value, footprint, (x, y, rotation), {pin number: net}, extra fields
PARTS = [
    ("J101", "Connector_Generic:Conn_01x02", "XT30PW-M",
     "Connector_AMASS:AMASS_XT30PW-M_1x02_P2.50mm_Horizontal", (40.64, 101.6, 0),
     {"1": "GND", "2": "VBAT_IN"},
     {"Manufacturer": "Amass", "MPN": "XT30PW-M30.G.Y", "LCSC": "C431092",
      "Datasheet": "https://www.china-amass.net/xt30pw-m-product/", "Description": "Battery input, 3S LiPo. " + XT30}),
    ("F101", "Device:Fuse", "15A",
     "Fuse:Fuseholder_Blade_Mini_Keystone_3568", (73.66, 101.6, 90),
     {"1": "VBAT_IN", "2": "VBAT_FUSED"},
     {"Manufacturer": "Keystone", "MPN": "3568", "LCSC": "C5249699",
      "Fuse_Insert": "Littelfuse 0297015.WXNV (15 A mini blade, candidate O-17)",
      "Datasheet": "https://www.keyelco.com/userAssets/file/M65p42.pdf",
      "Description": "Mini blade fuse holder; insert is a candidate pending protection coordination (O-17)"}),
    ("Q101", "Transistor_FET:Si7141DP", "SiRA99DP",
     "Package_SO:PowerPAK_SO-8_Single", (127.0, 101.6, 0),
     {"1": "VBAT_PROT", "2": "VBAT_PROT", "3": "VBAT_PROT", "4": "Q101_GATE", "5": "VBAT_FUSED"},
     {"Manufacturer": "Vishay", "MPN": "SiRA99DP-T1-GE3", "LCSC": "C3289459",
      "Datasheet": "https://www.vishay.com/doc?71023",
      "Description": "Reverse-polarity P-MOSFET, -30 V, 2.65 mOhm max at -4.5 V; symbol Si7141DP has the same PowerPAK SO-8 pinout (S 1-3, G 4, D 5)"}),
    ("R101", "Device:R", "10k",
     "Resistor_SMD:R_0603_1608Metric", (116.84, 134.62, 0),
     {"1": "Q101_GATE", "2": "GND"},
     {"Description": "Gate pull-down of Q101; value with D102 pending (O-17)"}),
    ("D102", "Device:D_Zener", "15V",
     "Diode_SMD:D_SOD-123", (139.7, 134.62, 90),
     {"1": "VBAT_PROT", "2": "Q101_GATE"},
     {"Manufacturer": "onsemi", "MPN": "MMSZ5245BT1G", "LCSC": "C129730",
      "Datasheet": "https://www.onsemi.com/pdf/datasheet/mmsz5221bt1-d.pdf",
      "Description": "Gate-source clamp of Q101, Vz 14.25-15.75 V (candidate, O-17)"}),
    ("D101", "Device:D_Zener", "SMBJ13A",
     "Diode_SMD:D_SMB", (165.1, 134.62, 270),
     {"1": "VBAT_PROT", "2": "GND"},
     {"Manufacturer": "Littelfuse", "MPN": "SMBJ13A", "LCSC": "C151252",
      "Datasheet": "https://www.vishay.com/doc?88392",
      "Description": "600 W unidirectional TVS, VRWM 13 V, VC 21.5 V at 27.9 A (10/1000 us); candidate, protection proof open (O-17)"}),
    ("C101", "Device:C_Polarized", "330u 35V",
     "Capacitor_SMD:CP_Elec_10x10.5", (190.5, 134.62, 0),
     {"1": "VBAT_PROT", "2": "GND"},
     {"Manufacturer": "Rubycon", "MPN": "35PJV330M10X10.5", "LCSC": "C3274921",
      "Description": "Input bulk, hybrid polymer, ESR max 20 mOhm, 2.8 A ripple (candidate)"}),
    ("C102", "Device:C", "10u 50V X7R",
     "Capacitor_SMD:C_1210_3225Metric", (210.82, 134.62, 0),
     {"1": "VBAT_PROT", "2": "GND"},
     {"Manufacturer": "Samsung", "MPN": "CL32B106KBJNNNE", "LCSC": "C138687",
      "Description": "Input decoupling at the protection node; regulator MLCCs sit at each regulator"}),
    ("TP101", "Connector:TestPoint", "VBAT_IN", "TestPoint:TestPoint_Pad_D1.5mm", (58.42, 83.82, 0),
     {"1": "VBAT_IN"}, {"Description": "Test point battery input (before fuse)"}),
    ("TP102", "Connector:TestPoint", "VBAT_PROT", "TestPoint:TestPoint_Pad_D1.5mm", (149.86, 83.82, 0),
     {"1": "VBAT_PROT"}, {"Description": "Test point protected battery rail"}),
    ("TP103", "Connector:TestPoint", "GND", "TestPoint:TestPoint_Pad_D1.5mm", (231.14, 134.62, 0),
     {"1": "GND"}, {"Description": "Test point ground"}),
]
POWER = "power:GND"
FLAG = "power:PWR_FLAG"


def uid(label):
    return str(uuid.uuid5(NS, label))


def library_text(lib):
    return (kicad_env.shared_support() / "symbols" / (lib + ".kicad_sym")).read_text()


def _block(text, name):
    start = text.index('\n\t(symbol "%s"\n' % name) + 1
    depth, i, in_str = 0, start, False
    while True:
        c = text[i]
        if in_str:
            if c == "\\":
                i += 1
            elif c == '"':
                in_str = False
        elif c == '"':
            in_str = True
        elif c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
        i += 1


def lib_symbol(lib_id):
    lib, name = lib_id.split(":")
    block = _block(library_text(lib), name)
    if "(extends" in block:
        raise SystemExit("Derived symbol %s is not supported" % lib_id)
    return block.replace('(symbol "%s"' % name, '(symbol "%s"' % lib_id, 1)


PIN = re.compile(r'\(pin \w+ \w+\s*\(at ([-\d.]+) ([-\d.]+) (\d+)\).*?\(number "([^"]*)"', re.S)
STUB = 5.08


def pin_points(lib_id):
    """pin number -> (x, y, angle); the angle points from the pin end towards the symbol body."""
    return {m.group(4): (float(m.group(1)), float(m.group(2)), int(m.group(3)))
            for m in PIN.finditer(lib_symbol(lib_id))}


def outward(rot, pin_angle):
    """Unit vector (schematic coordinates, y down) pointing away from the body."""
    a = math.radians(pin_angle + 180 + rot)
    return round(math.cos(a)), -round(math.sin(a))


def place(x, y, rot, px, py):
    """Symbol-local pin (y up) -> schematic coordinates (y down), rotation counter-clockwise."""
    a = math.radians(rot)
    rx = px * math.cos(a) - py * math.sin(a)
    ry = px * math.sin(a) + py * math.cos(a)
    return round(x + rx, 4), round(y - ry, 4)


def prop(name, value, at, hide=False, indent="\t\t", angle=0, justify=None):
    hidden = "\n%s\t\t(hide yes)" % indent if hide else ""
    just = "\n%s\t\t(justify %s)" % (indent, justify) if justify else ""
    return ('%s(property "%s" "%s"\n%s\t(at %s %s %d)\n%s\t(effects\n%s\t\t(font\n%s\t\t\t(size 1.27 1.27)\n'
            "%s\t\t)%s%s\n%s\t)\n%s)\n") % (indent, name, value.replace('"', "'"), indent, at[0], at[1], angle,
                                           indent, indent, indent, indent, just, hidden, indent, indent)


def vertical(lib_id, rot):
    """True when the placed symbol's pins are stacked vertically (fields then go to the right)."""
    pts = [place(0, 0, rot, px, py) for px, py, _ in pin_points(lib_id).values()]
    return len(pts) > 1 and len({p[0] for p in pts}) < len({p[1] for p in pts})


def symbol(lib_id, ref, value, footprint, x, y, rot, pins, fields, path):
    body = ("\t(symbol\n\t\t(lib_id \"%s\")\n\t\t(at %s %s %d)\n\t\t(unit 1)\n\t\t(exclude_from_sim no)\n"
            "\t\t(in_bom %s)\n\t\t(on_board %s)\n\t\t(dnp no)\n\t\t(uuid \"%s\")\n"
            % (lib_id, x, y, rot, "no" if ref.startswith("#") else "yes", "no" if ref.startswith("#") else "yes",
               uid("symbol-" + ref)))
    if ref.startswith("#"):
        ref_at, val_at = (x, y + 3.81), (x, y + 5.08)
    elif vertical(lib_id, rot):
        ref_at, val_at = (x + 6.35, y - 1.27), (x + 6.35, y + 1.27)
    else:
        ref_at, val_at = (x, y - 3.81), (x, y + 3.81)
    # KiCad renders field text relative to the symbol rotation; compensate to keep it horizontal.
    just = "left" if not ref.startswith("#") and vertical(lib_id, rot) else None
    angle = rot if rot in (90, 270) else 0
    body += prop("Reference", ref, ref_at, hide=ref.startswith("#"), justify=just, angle=angle)
    body += prop("Value", value, val_at, hide=ref.startswith("#PWR"), justify=just, angle=angle)
    body += prop("Footprint", footprint, (x, y), hide=True)
    body += prop("Datasheet", fields.get("Datasheet", "~"), (x, y), hide=True)
    body += prop("Description", fields.get("Description", ""), (x, y), hide=True)
    for key in ("Manufacturer", "MPN", "LCSC", "Fuse_Insert"):
        if key in fields:
            body += prop(key, fields[key], (x, y), hide=True)
    for number in sorted(pins):
        body += '\t\t(pin "%s"\n\t\t\t(uuid "%s")\n\t\t)\n' % (number, uid("pin-%s-%s" % (ref, number)))
    body += ("\t\t(instances\n\t\t\t(project \"%s\"\n\t\t\t\t(path \"%s\"\n\t\t\t\t\t(reference \"%s\")\n"
             "\t\t\t\t\t(unit 1)\n\t\t\t\t)\n\t\t\t)\n\t\t)\n\t)\n") % (PROJECT, path, ref)
    return body


def label(net, x, y, direction, key):
    angle, justify = {(1, 0): (0, "left"), (-1, 0): (180, "right"), (0, -1): (90, "left"),
                      (0, 1): (270, "right")}[direction]
    return ("\t(label \"%s\"\n\t\t(at %s %s %d)\n\t\t(effects\n\t\t\t(font\n\t\t\t\t(size 1.27 1.27)\n\t\t\t)\n"
            "\t\t\t(justify %s bottom)\n\t\t)\n\t\t(uuid \"%s\")\n\t)\n") % (net, x, y, angle, justify,
                                                                         uid("label-" + key))


def wire(x1, y1, x2, y2, key):
    return ("\t(wire\n\t\t(pts\n\t\t\t(xy %s %s) (xy %s %s)\n\t\t)\n\t\t(stroke\n\t\t\t(width 0)\n"
            "\t\t\t(type default)\n\t\t)\n\t\t(uuid \"%s\")\n\t)\n") % (x1, y1, x2, y2, uid("wire-" + key))


def text_note(text, x, y, key):
    return ("\t(text \"%s\"\n\t\t(exclude_from_sim no)\n\t\t(at %s %s 0)\n\t\t(effects\n\t\t\t(font\n"
            "\t\t\t\t(size 1.27 1.27)\n\t\t\t)\n\t\t\t(justify left bottom)\n\t\t)\n\t\t(uuid \"%s\")\n\t)\n"
            % (text.replace('"', "'"), x, y, uid("text-" + key)))


def power_sheet(root_uuid, sheet_uuid):
    path = "/%s/%s" % (root_uuid, sheet_uuid)
    libs = sorted({p[1] for p in PARTS} | {POWER, FLAG})
    out = ["(kicad_sch\n\t(version 20260306)\n\t(generator \"eeschema\")\n\t(generator_version \"10.0\")\n"
           "\t(uuid \"%s\")\n\t(paper \"A4\")\n" % uid("power-sheet"),
           "\t(title_block\n\t\t(title \"RoverCore VCU – Power: battery input and protection\")\n\t\t(rev \"A\")\n"
           "\t\t(comment 1 \"DRAFT – candidates per docs/vcu/rev1-versorgung-und-boardwahl.md 3.9, not released\")\n\t)\n",
           "\t(lib_symbols\n" + "\n".join("\n".join("\t" + l for l in lib_symbol(l).splitlines()) for l in libs)
           + "\n\t)\n"]
    pwr = 0
    endpoints = {}
    for ref, lib_id, value, fp, (x, y, rot), pins, fields in PARTS:
        out.append(symbol(lib_id, ref, value, fp, x, y, rot, pins, fields, path))
        pts = pin_points(lib_id)
        done = set()
        for number, net in sorted(pins.items()):
            lx, ly, langle = pts[number]
            px, py = place(x, y, rot, lx, ly)
            endpoints.setdefault((px, py), set()).add(net)
            if (px, py) in done:  # stacked pins (Q101 source) share one stub
                continue
            done.add((px, py))
            dx, dy = outward(rot, langle)
            ex, ey = round(px + dx * STUB, 4), round(py + dy * STUB, 4)
            out.append(wire(px, py, ex, ey, "%s-%s" % (ref, number)))
            if net == "GND":
                pwr += 1
                out.append(symbol(POWER, "#PWR%03d" % pwr, "GND", "", ex, ey, 0, {"1": "GND"}, {}, path))
            else:
                out.append(label(net, ex, ey, (dx, dy), "%s-%s" % (ref, number)))
    clash = {k: v for k, v in endpoints.items() if len(v) > 1}
    if clash:
        raise SystemExit("Different nets share a pin endpoint: %s" % clash)
    # Power flags: the battery connector is a passive source for VBAT_IN and GND.
    jx, jy, jrot = PARTS[0][4]
    pts = pin_points(PARTS[0][1])
    for n, (number, net) in enumerate((("2", "VBAT_IN"), ("1", "GND")), 1):
        lx, ly, langle = pts[number]
        px, py = place(jx, jy, jrot, lx, ly)
        dx, dy = outward(jrot, langle)
        mx, my = round(px + dx * STUB, 4), round(py + dy * STUB, 4)  # at the stub end
        out.append(symbol(FLAG, "#FLG%03d" % n, "PWR_FLAG", "", mx, my, 0, {"1": net}, {}, path))
    out.append(text_note("Battery input 3S (9.0-12.6 V): XT30 -> fuse -> reverse-polarity P-FET -> TVS -> bulk. "
                         "All parts are candidates (O-17). " + XT30 + ".", 30.48, 55.88, "header"))
    out.append(text_note("Q101 conducts when VBAT is correct (VGS = -VBAT); D102 limits |VGS| during TVS clamping. "
                         "VBAT_PROT feeds the regulators (next step).", 30.48, 60.96, "fet"))
    out.append("\t(embedded_fonts no)\n)\n")
    return "".join(out)


def sheet_block(sheet_uuid):
    x, y, w, h = 63.5, 50.8, 38.1, 15.24
    return ("\t(sheet\n\t\t(at %s %s)\n\t\t(size %s %s)\n\t\t(exclude_from_sim no)\n\t\t(in_bom yes)\n"
            "\t\t(on_board yes)\n\t\t(dnp no)\n\t\t(fields_autoplaced yes)\n\t\t(stroke\n\t\t\t(width 0.1524)\n"
            "\t\t\t(type solid)\n\t\t)\n\t\t(fill\n\t\t\t(color 0 0 0 0.0000)\n\t\t)\n\t\t(uuid \"%s\")\n"
            % (x, y, w, h, sheet_uuid)
            + prop("Sheetname", "Power", (x, round(y - 0.7116, 4)))
            + prop("Sheetfile", SHEET_FILE, (x, round(y + h + 0.5846, 4)), hide=True)
            + "\t\t(instances\n\t\t\t(project \"%s\"\n\t\t\t\t(path \"/%s\"\n\t\t\t\t\t(page \"2\")\n\t\t\t\t)\n"
              "\t\t\t)\n\t\t)\n\t)\n" % (PROJECT, ROOT_UUID))


def main():
    global ROOT_UUID
    if list(ROOT.glob("*.lck")) or list(ROOT.glob("~*.lck")) or kicad_env.running_kicad():
        raise SystemExit("KiCad is running or a lock file exists; close KiCad first.")
    target = ROOT / SHEET_FILE
    if target.exists():
        raise SystemExit("%s exists; edit it in KiCad instead of re-running the bootstrap." % SHEET_FILE)
    root = ROOT_SCH.read_text()
    if "(sheet\n" in root:
        raise SystemExit("Root schematic already has sheets; refusing to modify it.")
    ROOT_UUID = re.search(r'\(uuid "?([0-9a-f-]{36})"?\)', root).group(1)
    sheet_uuid = uid("sheet-power")
    target.write_text(power_sheet(ROOT_UUID, sheet_uuid))
    anchor = "\t(sheet_instances\n"
    if root.count(anchor) != 1:
        raise SystemExit("Unexpected root schematic layout")
    ROOT_SCH.write_text(root.replace(anchor, sheet_block(sheet_uuid) + anchor, 1))
    print("Wrote %s and added sheet 'Power' to %s" % (target.name, ROOT_SCH.name))


if __name__ == "__main__":
    main()
