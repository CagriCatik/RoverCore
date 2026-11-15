#!/usr/bin/env python3
"""One-time bootstrap of the LogicPower sheet: 5 V logic rail with TPS54302 from VBAT_PROT.

Values: docs/vcu/rev1-versorgung-und-boardwahl.md section 3.8 (3S basis), with
R3 = 13.7 kOhm so that +5V stays below the WS2812B absolute maximum of 5.3 V
(4.74-5.16 V static with 1 % parts). Writes LogicPower.kicad_sch, adds a
VBAT_PROT output pin to the existing Power sheet symbol and wires it to the new
sheet in RoverCore.kicad_sch. Afterwards the KiCad files are the truth.

Usage: python3 hardware/scripts/bootstrap_logic_power.py
"""
from pathlib import Path
import re
import sys
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parent))
import schgen  # noqa: E402
from schgen import Sheet, sheet_block, require_closed_kicad  # noqa: E402

ROOT = schgen.ROOT
ROOT_SCH = ROOT / "RoverCore.kicad_sch"
FILE = "LogicPower.kicad_sch"
NS = "6c1e2a4d-0b77-4d5c-8f3a-1e9b2c5d0301"
GND, P5V, FLAG = "power:GND", "power:+5V", "power:PWR_FLAG"
POWER_NETS = {"GND": GND, "+5V": P5V}
HIER = {"VBAT_PROT": "input"}

YAGEO_DS = "https://www.yageogroup.com/content/datasheet/asset/file/PYU-RC_GROUP_51_ROHS_L"


def res(mpn, lcsc, desc):
    return {"Manufacturer": "Yageo", "MPN": mpn, "LCSC": lcsc, "Datasheet": YAGEO_DS, "Description": desc}


CAP_100N = {"Manufacturer": "Yageo", "MPN": "CC0603KRX7R9BB104", "LCSC": "C14663",
            "Datasheet": "https://www.lcsc.com/datasheet/lcsc_datasheet_2211101700_YAGEO-CC0603KRX7R9BB104_C14663.pdf",
            "Description": "100 nF 50 V X7R 0603 (50 V from part-number code / distributor data)"}
CAP_22U = {"Manufacturer": "Murata", "MPN": "GRM32ER71E226KE15L", "LCSC": "C21397",
           "Datasheet": "https://www.lcsc.com/datasheet/lcsc_datasheet_2308111542_Murata-Electronics-GRM32ER71E226KE15L_C21397.pdf",
           "Description": "22 uF 25 V X7R 1210 output capacitor (Murata spec sheet); DC-bias capacitance at 5 V not yet verified"}
CAP_75P = {"Manufacturer": "Yageo", "MPN": "CC0603JRNPO9BN750", "LCSC": "C282074",
           "Datasheet": "~",
           "Description": "75 pF 50 V C0G/NP0 0603 feed-forward (TI reference C6)"}
CAP_10U = {"Manufacturer": "Samsung", "MPN": "CL32B106KBJNNNE", "LCSC": "C138687",
           "Description": "10 uF 50 V X7R 1210 input capacitor (about 7.4 uF at 12 V, typical curve)"}

R_0603, C_0603 = "Resistor_SMD:R_0603_1608Metric", "Capacitor_SMD:C_0603_1608Metric"

# ref, lib_id, value, footprint, (x, y, rot), pins {number: net}, fields
PARTS = [
    ("U301", "Regulator_Switching:TPS54302", "TPS54302", "Package_TO_SOT_SMD:TSOT-23-6", (127.0, 96.52, 0),
     {"1": "GND", "2": "SW_5V", "3": "VBAT_PROT", "4": "FB_5V", "5": "EN_5V", "6": "BOOT_5V"},
     {"Manufacturer": "Texas Instruments", "MPN": "TPS54302DDCR", "LCSC": "C311983",
      "Datasheet": "https://www.ti.com/lit/ds/symlink/tps54302.pdf",
      "Description": "4.5-28 V, 3 A sync buck, 400 kHz; pinout per SLVSDG6C Table 4-1 (DDC = TSOT-23-6)"}),
    ("C301", "Device:C", "10u 50V", "Capacitor_SMD:C_1210_3225Metric", (63.5, 129.54, 0),
     {"1": "VBAT_PROT", "2": "GND"}, CAP_10U),
    ("C302", "Device:C", "100n 50V", C_0603, (76.2, 129.54, 0), {"1": "VBAT_PROT", "2": "GND"},
     dict(CAP_100N, Description="100 nF VIN high-frequency decoupling at pin 3")),
    ("R304", "Device:R", "69.8k", R_0603, (91.44, 129.54, 0), {"1": "VBAT_PROT", "2": "EN_5V"},
     res("RC0603FR-0769K8L", "C137689", "EN divider top: on 8.65 V, off 8.04 V (EN eq. 1/2)")),
    ("R305", "Device:R", "11.5k", R_0603, (104.14, 129.54, 0), {"1": "EN_5V", "2": "GND"},
     res("RC0603FR-0711K5L", "C137802", "EN divider bottom; EN at 21.5 V TVS clamp about 3.0 V < 7 V abs max")),
    ("C303", "Device:C", "100n 50V", C_0603, (147.32, 129.54, 0), {"1": "BOOT_5V", "2": "SW_5V"},
     dict(CAP_100N, Description="Bootstrap capacitor BOOT-SW (SLVSDG6C 7.2.3.2)")),
    ("L301", "Device:L", "10u", "Inductor_SMD:L_Wuerth_XHMI-6060", (172.72, 96.52, 90),
     {"1": "SW_5V", "2": "+5V"},
     {"Manufacturer": "Wurth Elektronik", "MPN": "74439346100", "LCSC": "C2651185",
            "Description": "10 uH, Isat 9.7 A (-30 %), DCR max 29.2 mOhm"}),
    ("C304", "Device:C", "22u", "Capacitor_SMD:C_1210_3225Metric", (180.34, 129.54, 0),
     {"1": "+5V", "2": "GND"}, CAP_22U),
    ("C305", "Device:C", "22u", "Capacitor_SMD:C_1210_3225Metric", (193.04, 129.54, 0),
     {"1": "+5V", "2": "GND"}, CAP_22U),
    ("C307", "Device:C", "22u", "Capacitor_SMD:C_1210_3225Metric", (180.34, 157.48, 0),
     {"1": "+5V", "2": "GND"}, CAP_22U),
    ("R301", "Device:R", "49.9", R_0603, (208.28, 129.54, 0), {"1": "+5V", "2": "VSENSE_5V"},
     res("RC0603FR-0749R9L", "C114625", "Loop-injection resistor for Bode measurement (TI ref. R1)")),
    ("R302", "Device:R", "100k", R_0603, (223.52, 129.54, 0), {"1": "VSENSE_5V", "2": "FB_5V"},
     res("RC0603FR-07100KL", "C14675", "Feedback top")),
    ("C306", "Device:C", "75p C0G", C_0603, (236.22, 129.54, 0), {"1": "VSENSE_5V", "2": "FB_5V"},
     CAP_75P),
    ("R303", "Device:R", "13.7k", R_0603, (248.92, 129.54, 0), {"1": "FB_5V", "2": "GND"},
     res("RC0603FR-0713K7L", "C482771",
         "Feedback bottom: 4.95 V nom, 4.74-5.16 V with VREF +-2.5 % and 1 % parts")),
    ("TP301", "Connector:TestPoint", "+5V", "TestPoint:TestPoint_Pad_D1.5mm", (193.04, 78.74, 0),
     {"1": "+5V"}, {"Description": "Test point +5V; bare copper pad, no purchased part (excluded from BOM)"}),
    ("TP302", "Connector:TestPoint", "GND", "TestPoint:TestPoint_Pad_D1.5mm", (261.62, 129.54, 0),
     {"1": "GND"}, {"Description": "Test point GND at the 5 V stage; bare copper pad, excluded from BOM"}),
]


def stub_end(sheet, lib_id, xyr, number):
    x, y, rot = xyr
    lx, ly, langle = sheet.pin_points(lib_id)[number]
    px, py = sheet.place(x, y, rot, lx, ly)
    dx, dy = sheet.outward(rot, langle)
    return round(px + dx * schgen.STUB, 4), round(py + dy * schgen.STUB, 4)


def build(root_uuid, sheet_uuid):
    s = Sheet(NS, root_uuid, sheet_uuid, "RoverCore VCU – LogicPower: 5 V rail (TPS54302)",
              "DRAFT – candidates per docs/vcu/rev1-versorgung-und-boardwahl.md 3.8, not released")
    for ref, lib, value, fp, xyr, pins, fields in PARTS:
        s.part(ref, lib, value, fp, xyr, pins, fields, POWER_NETS, HIER,
               in_bom=not ref.startswith("TP"))
    # VBAT_PROT and +5V are only driven through passive parts: flag them for ERC.
    for n, (ref, number, net) in enumerate((("C301", "1", "VBAT_PROT"), ("C304", "1", "+5V")), 1):
        part = next(p for p in PARTS if p[0] == ref)
        ex, ey = stub_end(s, part[1], part[4], number)
        s._symbol(FLAG, "#FLG3%02d" % n, "PWR_FLAG", "", ex, ey, 0, {"1": net}, {})
    s.note("5 V logic rail from VBAT_PROT (3S, 9.0-12.6 V). TPS54302: L 10 uH, Cout 3 x 22 uF, "
           "FB 100k/13.7k -> 4.95 V nom, 4.74-5.16 V (1 %). WS2812B abs max 5.3 V limits the upper bound.",
           30.48, 55.88, "header")
    s.note("EN divider 69.8k/11.5k: on 8.65 V, off 8.04 V (logic stays on below the servo rail cut-off 8.8 V). "
           "R301 49.9 Ohm allows loop measurement. All parts are candidates (O-17).", 30.48, 60.96, "notes")
    return s.render()


def main():
    require_closed_kicad()
    if (ROOT / FILE).exists():
        raise SystemExit("%s exists; edit it in KiCad instead of re-running the bootstrap." % FILE)
    root = ROOT_SCH.read_text()
    root_uuid = re.search(r'\(uuid "?([0-9a-f-]{36})"?\)', root).group(1)
    if 'LogicPower.kicad_sch' in root:
        raise SystemExit("Root already references LogicPower")
    m = re.search(r'\t\(sheet\n.*?\(property "Sheetfile" "Power\.kicad_sch".*?\n\t\)\n', root, re.S)
    if not m:
        raise SystemExit("Power sheet symbol not found in root")
    power_block = m.group(0)
    at = re.search(r'\(at ([\d.]+) ([\d.]+)\)\n\t\t\(size ([\d.]+) ([\d.]+)\)', power_block)
    px, py, pw, ph = (float(v) for v in at.groups())
    if '(pin "VBAT_PROT"' in power_block:
        raise SystemExit("Power sheet already exposes VBAT_PROT")
    pin_y = round(py + 7.62, 4)
    power_uuid = re.search(r'\(uuid "([0-9a-f-]{36})"\)', power_block).group(1)
    pin = ("\t\t(pin \"VBAT_PROT\" output\n\t\t\t(at %s %s 0)\n\t\t\t(uuid \"%s\")\n\t\t\t(effects\n\t\t\t\t(font\n"
           "\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t)\n\t\t\t\t(justify right)\n\t\t\t)\n\t\t)\n"
           % (round(px + pw, 4), pin_y, uuid.uuid5(uuid.UUID(power_uuid), "pin-VBAT_PROT")))
    new_power = power_block.replace("\t\t(instances\n", pin + "\t\t(instances\n", 1)
    sheet_uuid = str(uuid.uuid5(uuid.UUID(NS), "sheet-logicpower"))
    lx = round(px + pw + 25.4, 4)
    logic = sheet_block(root_uuid, sheet_uuid, "LogicPower", FILE, lx, py, pw, ph, "3",
                        [("VBAT_PROT", "input", "left", 7.62)])
    wire = ("\t(wire\n\t\t(pts\n\t\t\t(xy %s %s) (xy %s %s)\n\t\t)\n\t\t(stroke\n\t\t\t(width 0)\n\t\t\t(type default)\n"
            "\t\t)\n\t\t(uuid \"%s\")\n\t)\n" % (round(px + pw, 4), pin_y, lx, pin_y,
                                                uuid.uuid5(uuid.UUID(NS), "root-wire-vbat")))
    (ROOT / FILE).write_text(build(root_uuid, sheet_uuid))
    root = root.replace(power_block, new_power + logic + wire, 1)
    ROOT_SCH.write_text(root)
    print("Wrote %s; added sheet 'LogicPower' and VBAT_PROT link to %s" % (FILE, ROOT_SCH.name))


if __name__ == "__main__":
    main()
