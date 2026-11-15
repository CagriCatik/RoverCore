#!/usr/bin/env python3
"""One-time bootstrap of the Sensors_Display sheet: IMU and OLED plug-in modules on the shared I2C bus.

Design basis (verified 2026-11-15, see docs/vcu/rev1-pin-und-anschlussplan.md section 9):
- J115: Adafruit 4438 LSM6DSOX, 1x9 header JP1 plugged into a carrier female header, component side up.
  VIN = +3V3 (on-module AP2112K-3.3, VIN 3-5 V per Adafruit), SCL/SDA level-shifted (BSS138) with 10k pull-ups
  to VIN on the bus side, INT1 straight from the sensor (3.3 V domain), DO/CS/INT2/3Vo not used.
  Address 0x6A (DO pulled down on the module, SJ1 open).
- J116: Adafruit 326 0.96in 128x64 SSD1306, STEMMA QT revision (2020-08-03): I2C is the default (SJ1/SJ2 closed),
  10k pull-ups to Vin on the bus side, address 0x3D (DC/A0 pulled up, SJ3 open), on-board reset IC (APX803):
  Rst, CS, DC, 3Vo not used.
- No STEMMA QT cables. Carrier pull-ups R801/R802 are DNP options; R803 holds IMU_INT1 low without the IMU.
Signals to the Controller are global labels (I2C_SDA, I2C_SCL, IMU_INT1), as on the Controller sheet.
Positions come from LAYOUTS["Sensors_Display"]; run relayout_sheet.py Sensors_Display afterwards.

Usage: python3 hardware/scripts/bootstrap_sensors_display.py
"""
from pathlib import Path
import re
import sys
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parent))
import schgen  # noqa: E402
from schgen import Sheet, sheet_block, require_closed_kicad  # noqa: E402
from sheet_layouts import LAYOUTS  # noqa: E402

ROOT = schgen.ROOT
ROOT_SCH = ROOT / "RoverCore.kicad_sch"
FILE = "Sensors_Display.kicad_sch"
NS = "8e1f4a37-2b6c-4d90-a5e3-7c0b9d2e0801"
POWER_NETS = {"GND": "power:GND", "+3V3": "power:+3V3"}
GLOBAL = {"I2C_SDA": "bidirectional", "I2C_SCL": "input", "IMU_INT1": "output"}
R0603 = "Resistor_SMD:R_0603_1608Metric"
YAGEO_RC = "https://www.yageogroup.com/content/datasheet/asset/file/PYU-RC_GROUP_51_ROHS_L"
TP = "TestPoint:TestPoint_Pad_D1.5mm"
SOCKET_NOTE = ("Carrier part: female header {n}x1 2.54 mm, through-hole; manufacturer part and height open (O-31). "
               "The module (bought separately) plugs in with its own male header. ")


def parts():
    return [
        ("J115", "ProjectSymbols:Adafruit_4438_LSM6DSOX_Socket", "Adafruit 4438 LSM6DSOX",
         "ProjectFootprints:Adafruit_4438_LSM6DSOX_Socket_1x09_P2.54mm",
         {"1": "+3V3", "2": "NC", "3": "GND", "4": "I2C_SCL", "5": "I2C_SDA", "6": "NC", "7": "NC", "8": "IMU_INT1",
          "9": "NC"},
         {"Manufacturer": "Adafruit (module)", "MPN": "4438 module + carrier female header 1x9 (part open, O-31)",
          "Datasheet": "https://github.com/adafruit/Adafruit-LSM6DSOX-PCB",
          "Description": SOCKET_NOTE.format(n=9) + "Pinout from Adafruit_LSM6DSOX.brd: 1 VIN, 2 3Vo, 3 GND, 4 SCL, "
                         "5 SDA, 6 DO, 7 CS, 8 INT1, 9 INT2. VIN = +3V3, address 0x6A, INT1 push-pull 3.3 V."}),
        ("J116", "ProjectSymbols:Adafruit_326_OLED_Socket", "Adafruit 326 OLED 128x64",
         "ProjectFootprints:Adafruit_326_OLED128x64_Socket_1x08_P2.54mm",
         {"1": "I2C_SDA", "2": "I2C_SCL", "3": "NC", "4": "NC", "5": "NC", "6": "NC", "7": "+3V3", "8": "GND"},
         {"Manufacturer": "Adafruit (module)", "MPN": "326 module (STEMMA QT rev.) + carrier female header 1x8 (part open, O-31)",
          "Datasheet": "https://github.com/adafruit/Adafruit-128x64-Monochrome-OLED-PCB",
          "Description": SOCKET_NOTE.format(n=8) + "Pinout from 'Adafruit 0.96in 128x64 OLED STEMMA QT.brd': 1 Data, "
                         "2 Clk, 3 DC/A0, 4 Rst, 5 CS, 6 3Vo, 7 Vin, 8 GND. I2C default, address 0x3D."}),
        ("R801", "Device:R", "4.7k", R0603, {"1": "+3V3", "2": "I2C_SDA"},
         {"Manufacturer": "Yageo", "MPN": "RC0603FR-074K7L", "Datasheet": YAGEO_RC, "_dnp": True,
          "Description": "DNP option: SDA pull-up only if the module pull-ups (10k || 10k = 5.0k) are missing; "
                         "LCSC number not checked"}),
        ("R802", "Device:R", "4.7k", R0603, {"1": "I2C_SCL", "2": "+3V3"},
         {"Manufacturer": "Yageo", "MPN": "RC0603FR-074K7L", "Datasheet": YAGEO_RC, "_dnp": True,
          "Description": "DNP option: SCL pull-up, see R801"}),
        ("R803", "Device:R", "100k", R0603, {"1": "IMU_INT1", "2": "GND"},
         {"Manufacturer": "Yageo", "MPN": "RC0603FR-07100KL", "LCSC": "C14675", "Datasheet": YAGEO_RC,
          "Description": "IMU_INT1 pull-down: defined low with the IMU missing or unpowered and while GPIO6 is Hi-Z; "
                         "33 uA load on the push-pull output"}),
        ("TP801", "Connector:TestPoint", "I2C_SDA", TP, {"1": "I2C_SDA"},
         {"Description": "Test point I2C_SDA (rise time measurement); bare copper pad, excluded from BOM"}),
        ("TP802", "Connector:TestPoint", "I2C_SCL", TP, {"1": "I2C_SCL"},
         {"Description": "Test point I2C_SCL; bare copper pad, excluded from BOM"}),
    ]


def build(root_uuid, sheet_uuid):
    s = Sheet(NS, root_uuid, sheet_uuid, "RoverCore VCU - Sensors_Display (IMU, OLED, I2C)",
              "DRAFT - docs/vcu rev1 Pinplan 9, Versorgung 3.11")
    s.paper = "A4"
    lay = LAYOUTS["Sensors_Display"]["parts"]
    for ref, lib, value, fp, pins, fields in parts():
        x, y, rot = lay[ref][:3]
        s.part(ref, lib, value, fp, (x, y, rot), pins, fields, POWER_NETS,
               {k: "global:" + v for k, v in GLOBAL.items()}, in_bom=not ref.startswith("TP"))
    return s.render()


def main():
    require_closed_kicad()
    if (ROOT / FILE).exists():
        raise SystemExit("%s exists; use relayout_sheet.py for layout changes." % FILE)
    root = ROOT_SCH.read_text()
    if FILE in root:
        raise SystemExit("Root already references %s" % FILE)
    root_uuid = re.search(r'\(uuid "?([0-9a-f-]{36})"?\)', root).group(1)
    sheet_uuid = str(uuid.uuid5(uuid.UUID(NS), "sheet-sensors-display"))
    block = sheet_block(root_uuid, sheet_uuid, "Sensors_Display", FILE, 190.5, 121.92, 38.1, 15.24, "8", [])
    (ROOT / FILE).write_text(build(root_uuid, sheet_uuid))
    anchor = "\t(sheet_instances\n"
    ROOT_SCH.write_text(root.replace(anchor, block + anchor, 1))
    print("Wrote %s and added sheet 'Sensors_Display' to %s" % (FILE, ROOT_SCH.name))


if __name__ == "__main__":
    main()
