#!/usr/bin/env python3
"""One-time bootstrap of the Controller sheet: DevKit socket, 5 V feed, 3.3 V distribution, fail-safe levels.

Design basis: docs/vcu/rev1-versorgung-und-boardwahl.md 3.11/3.12/3.13 and
docs/vcu/rev1-pin-und-anschlussplan.md (GPIO plan, hardware/interfaces/pinmap.csv).

- U501: carrier socket for an original ESP32-S3-DevKitC-1-N16R8 v1.1 (project symbol/footprint from
  make_devkit_socket.py; pads 1-22 = DevKit J1, 23-44 = DevKit J3, pin 1 marked on silkscreen).
- 5 V feed: carrier +5V -> Schottky D501 -> DevKit 5V pin. The DevKit's own USB diodes and D501 form a
  diode-OR: USB never feeds the carrier rails, the carrier never feeds the USB host. Replaces jumper JP101.
- 3.3 V: the DevKit LDO is the only 3.3 V source (+3V3); carrier load <= 50 mA.
- Fail-safe: ACT_OE_N pulled up (buffers off); the servo rail default OFF lives on ServoPower
  (SERVO_PWR_EN, R414/R407/Q404/R415) so it holds without this sheet's parts.
Signals to the other sheets are global labels; VBAT_PROT comes hierarchically from Power.

Usage: python3 hardware/scripts/bootstrap_controller.py
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
FILE = "Controller.kicad_sch"
NS = "3d7b9e21-5c4a-4f80-9b6e-2a1c8d4e0501"
POWER_NETS = {"GND": "power:GND", "+3V3": "power:+3V3", "+5V": "power:+5V"}
HIER = {"VBAT_PROT": "input"}
GLOBAL = {
    "VSERVO_SENSE": "input", "ISERVO_SENSE": "input", "SERVO_PWR_EN": "output", "ACT_OE_N": "output",
    "IMU_INT1": "input", "I2C_SDA": "bidirectional", "I2C_SCL": "output", "BUZZER": "output",
    "ESC_PWM_3V3": "output", "SERVO_FRONT_PWM_3V3": "output", "SERVO_REAR_PWM_3V3": "output",
    "SERVO_AUX1_PWM_3V3": "output", "SERVO_AUX2_PWM_3V3": "output",
    "LED_1_3V3": "output", "LED_2_3V3": "output", "LED_3_3V3": "output", "LED_4_3V3": "output",
    "IBUS_RX_3V3": "input", "EXT_UART_TX": "output", "EXT_UART_RX": "input", "P3V3_OK": "output",
}

R0603, C0603, C0805 = ("Resistor_SMD:R_0603_1608Metric", "Capacitor_SMD:C_0603_1608Metric",
                       "Capacitor_SMD:C_0805_2012Metric")
YAGEO_RC = "https://www.yageogroup.com/content/datasheet/asset/file/PYU-RC_GROUP_51_ROHS_L"
LCSC_NOTE = "manufacturer datasheet link not verified (O-22)"
TP = "TestPoint:TestPoint_Pad_D1.5mm"


def rc(mpn, lcsc, desc):
    return {"Manufacturer": "Yageo", "MPN": mpn, "LCSC": lcsc, "Datasheet": YAGEO_RC, "Description": desc}


C100N = {"Manufacturer": "Yageo", "MPN": "CC0603KRX7R9BB104", "LCSC": "C14663",
         "Datasheet": "https://www.lcsc.com/datasheet/lcsc_datasheet_2211101700_YAGEO-CC0603KRX7R9BB104_C14663.pdf"}

DBAT54 = {"Manufacturer": "Nexperia", "MPN": "BAT54,215", "LCSC": "C85084",
          "Datasheet": "https://www.lcsc.com/datasheet/lcsc_datasheet_2407241045_Nexperia-BAT54-215_C85084.pdf",
          "Description": "O-21 clamp ADC node -> +3V3: pin <= VDD + 240 mV at <= 0.1 mA (Nexperia BAT54 2022-07-01, LCSC copy)"}
QNTR4171 = {"Manufacturer": "onsemi", "MPN": "NTR4171PT1G", "LCSC": "C146715",
            "Datasheet": "https://www.lcsc.com/datasheet/lcsc_datasheet_1810301521_onsemi-NTR4171PT1G_C146715.pdf",
            "Description": "P-MOSFET -30 V, VGS +-12 V, IDSS <= 1 uA at -24 V, RDS(on) <= 110 mOhm at -4.5 V (NTR4171P/D Rev 2); "
                           "pinout 1 G, 2 S, 3 D"}
QNTR = {"Manufacturer": "onsemi", "MPN": "NTR4003NT1G", "LCSC": "C82325",
        "Datasheet": "https://www.onsemi.com/download/data-sheet/pdf/ntr4003n-d.pdf"}
NTR_NOTE = ("30 V, VGS(th) 0.8-1.4 V, RDS(on) <= 2.0 Ohm at VGS 2.5 V, IDSS <= 1 uA at 25 degC "
            "(NTR4003N/D Rev 6); pinout 1 G, 2 S, 3 D")
NMOS = "Transistor_FET:Q_NMOS_GSD"

# DevKit socket pin -> net (pads 1-22 = J1-1..22, 23-44 = J3-1..22); "NC" = reserved, see pinmap.csv
SOCKET = {
    1: "+3V3", 2: "=1", 3: "NC", 4: "VBAT_SENSE", 5: "VSERVO_SENSE", 6: "IMU_INT1", 7: "SERVO_PWR_EN",
    8: "SERVO_FRONT_PWM_3V3", 9: "SERVO_REAR_PWM_3V3", 10: "SERVO_AUX1_PWM_3V3", 11: "SPARE_GPIO18",
    12: "I2C_SDA", 13: "NC", 14: "NC", 15: "I2C_SCL", 16: "ENABLE_BTN_N", 17: "STATUS_LED", 18: "BUZZER",
    19: "ESC_PWM_3V3", 20: "SERVO_AUX2_PWM_3V3", 21: "+5V_DEVKIT", 22: "GND",
    23: "GND", 24: "NC", 25: "NC", 26: "ISERVO_SENSE", 27: "ACT_OE_N", 28: "LED_1_3V3", 29: "LED_2_3V3",
    30: "LED_3_3V3", 31: "LED_4_3V3", 32: "NC", 33: "NC", 34: "NC", 35: "NC", 36: "NC", 37: "NC",
    38: "EXT_UART_RX", 39: "EXT_UART_TX", 40: "IBUS_RX_3V3", 41: "NC", 42: "NC", 43: "GND", 44: "GND",
}


def parts():
    return [
        ("U501", "ProjectSymbols:ESP32-S3-DevKitC-1_Socket", "DevKitC-1-N16R8 v1.1",
         "ProjectFootprints:ESP32-S3-DevKitC-1_v1.1_Socket_2x1x22_P2.54mm", (205.74, 147.32, 0),
         {str(k): v for k, v in SOCKET.items()},
         {"Manufacturer": "Espressif", "MPN": "ESP32-S3-DevKitC-1-N16R8 (v1.1, original only)",
          "Datasheet": "https://docs.espressif.com/projects/esp-dev-kits/en/latest/esp32s3/esp32-s3-devkitc-1/user_guide_v1.1.html",
          "_ref_at": (-15.24, -38.1), "_val_at": (-15.24, -35.56),
          "Description": "Socket = 2 x 1x22 female header 2.54 mm (part open, height O-4); pads 1-22 J1, 23-44 J3; "
                         "RST, strapping, USB, UART0, GPIO35-38 not connected (pinmap.csv)"}),
        # ---- 5 V feed and 3.3 V distribution ----
        ("D501", "Device:D_Schottky", "PMEG4010CEH", "Diode_SMD:D_SOD-123F", (63.5, 63.5, 180),
         {"1": "+5V_DEVKIT", "2": "+5V"},
         {"Manufacturer": "Nexperia", "MPN": "PMEG4010CEH,115", "LCSC": "C193342",
          "Datasheet": "https://assets.nexperia.com/documents/data-sheet/PMEG4010CEH.pdf",
          "Description": "Carrier +5V -> DevKit 5V pin; diode-OR with the DevKit USB diodes (no backfeed either way). "
                         "40 V 1 A; VF max 490 mV at 0.5 A (25 degC, pulsed; Nexperia v.3 2023-10-12); "
                         "cathode copper >= 1 cm2 (Rth(j-a) 150 K/W)"}),
        ("TP503", "Connector:TestPoint", "+5V_DEVKIT", TP, (91.44, 63.5, 0), {"1": "+5V_DEVKIT"},
         {"_ref_at": (2.54, -1.27), "_val_at": (2.54, 1.27), "Description": "Test point DevKit 5V pin; bare copper pad, excluded from BOM"}),
        ("C501", "Device:C", "10u 25V", C0805, (63.5, 101.6, 0), {"1": "+3V3", "2": "GND"},
         {"Manufacturer": "Samsung", "MPN": "CL21A106KAYNNNE", "LCSC": "C15850",
          "Description": "+3V3 bulk at the socket for carrier loads (IMU, OLED, INA240, buffer VCCA); X5R 0805; " + LCSC_NOTE}),
        ("C502", "Device:C", "100n 50V", C0603, (78.74, 101.6, 0), {"1": "+3V3", "2": "GND"},
         dict(C100N, Description="+3V3 decoupling at the socket")),
        ("TP502", "Connector:TestPoint", "+3V3", TP, (99.06, 96.52, 0), {"1": "+3V3"},
         {"_ref_at": (2.54, -1.27), "_val_at": (2.54, 1.27), "Description": "Test point +3V3 (DevKit LDO); bare copper pad, excluded from BOM"}),
        ("TP504", "Connector:TestPoint", "GND", TP, (116.84, 96.52, 0), {"1": "GND"},
         {"_ref_at": (2.54, -1.27), "_val_at": (2.54, 1.27), "Description": "Test point GND; bare copper pad, excluded from BOM"}),
        # ---- fail-safe level for the output buffers ----
        ("R501", "Device:R", "10k", R0603, (63.5, 147.32, 0), {"1": "+3V3", "2": "ACT_OE_N"},
         rc("RC0603FR-0710KL", "C98220", "ACT_OE_N pull-up: U201 outputs Hi-Z at reset/boot; without DevKit VCCA = 0 "
            "and the SN74LVC8T245 VCC isolation keeps both ports Hi-Z")),
        # ---- enable button ----
        ("R502", "Device:R", "10k", R0603, (63.5, 190.5, 0), {"1": "+3V3", "2": "ENABLE_BTN_N"},
         rc("RC0603FR-0710KL", "C98220", "Button pull-up: not pressed = high; no RC at the pin (O-21) - debounce in firmware")),
        ("SW501", "Switch:SW_Push", "Enable", "Button_Switch_SMD:SW_SPST_TL3342", (116.84, 205.74, 0),
         {"1": "ENABLE_BTN_N", "2": "GND"},
         {"Manufacturer": "E-Switch", "MPN": "TL3342F160QG", "LCSC": "C2886898",
          "Description": "Enable (Freigabe) push button, active low; candidate, JLC stock 0 on 2026-11-15 (O-28)"}),
        # ---- status LED ----
        ("R504", "Device:R", "1k", R0603, (63.5, 241.3, 0), {"1": "STATUS_LED", "2": "LED_STAT_A"},
         rc("RC0603FR-071KL", "C22548", "LED current about 1.3 mA at VF 2.0 V (estimate)")),
        ("D502", "Device:LED", "LED status", "LED_SMD:LED_0603_1608Metric", (101.6, 241.3, 180),
         {"1": "GND", "2": "LED_STAT_A"},
         {"Description": "Status LED, 0603, AlGaInP (VF <= 2.4 V at 2 mA required with 3.3 V drive); part open (O-28)"}),
        # ---- battery voltage measurement (candidate, protection need documented in 3.13) ----
        ("R505", "Device:R", "120k", R0603, (297.18, 76.2, 0), {"1": "VBAT_SW", "2": "VBAT_DIV"},
         rc("RC0603FR-07120KL", "C114607", "VBAT divider top: 12.6 V -> 1.80 V, 9.0 V -> 1.29 V, 21.5 V clamp -> 3.07 V")),
        ("R506", "Device:R", "20k", R0603, (312.42, 109.22, 0), {"1": "VBAT_DIV", "2": "GND"},
         rc("RC0603FR-0720KL", "C105575", "VBAT divider bottom; source impedance 17 kOhm")),
        ("C504", "Device:C", "1n 50V C0G", C0603, (327.66, 109.22, 0), {"1": "VBAT_DIV", "2": "GND"},
         {"Manufacturer": "Yageo", "MPN": "CC0603JRNPO9BN102", "LCSC": "C106246",
          "Description": "VBAT_SENSE filter, tau 17 us; small so the node follows when Q505 opens (O-21); " + LCSC_NOTE}),
        ("D506", "ProjectSymbols:BAT54_SOT23", "BAT54", "Package_TO_SOT_SMD:SOT-23", (345.44, 124.46, 90),
         {"1": "VBAT_DIV", "3": "+3V3"}, dict(DBAT54)),
        ("R507", "Device:R", "10k", R0603, (360.68, 144.78, 0), {"1": "VBAT_DIV", "2": "VBAT_SENSE"},
         rc("RC0603FR-0710KL", "C98220", "Series resistor to GPIO4 (the voltage bound is D506)")),
        ("Q505", "Transistor_FET:Q_PMOS_GSD", "NTR4171P", "Package_TO_SOT_SMD:SOT-23", (297.18, 50.8, 0),
         {"1": "VBAT_SW_G", "2": "VBAT_PROT", "3": "VBAT_SW"},
         dict(QNTR4171, Description="O-21: normally-off switch for the VBAT divider; on only while P3V3_OK is high. " + QNTR4171["Description"])),
        ("R508", "Device:R", "100k", R0603, (271.78, 50.8, 0), {"1": "VBAT_PROT", "2": "VBAT_SW_G"},
         rc("RC0603FR-07100KL", "C14675", "Q505 gate-source: off without drive")),
        ("R509", "Device:R", "100k", R0603, (271.78, 81.28, 0), {"1": "VBAT_SW_G", "2": "VBAT_SW_DRV"},
         rc("RC0603FR-07100KL", "C14675", "Q505 gate drive: VGS = -0.5 x VBAT (-4.5 V at 9 V, -10.75 V at 21.5 V; limit +-12 V)")),
        ("Q506", NMOS, "NTR4003N", "Package_TO_SOT_SMD:SOT-23", (276.86, 111.76, 0),
         {"1": "P3V3_OK", "2": "GND", "3": "VBAT_SW_DRV"},
         dict(QNTR, Description="Turns Q505 on while P3V3_OK is high; " + NTR_NOTE)),
        ("U504", "ProjectSymbols:TLV809E_DBZ", "TLV809ED29DBZR", "Package_TO_SOT_SMD:SOT-23", (276.86, 165.1, 0),
         {"3": "+3V3", "1": "GND", "2": "P3V3_OK"},
         {"Manufacturer": "Texas Instruments", "MPN": "TLV809ED29DBZR", "LCSC": "C2864833", "Datasheet": "https://www.ti.com/lit/pdf/SLVSES2",
          "_ref_at": (-10.16, -7.62), "_val_at": (2.54, -7.62),
          "Description": "P3V3_OK = +3V3 good: VIT- 2.93 V +-2 %, hysteresis 1.2 %, release delay tD 33-67 ms (variant D), "
                         "falling detection tPD_HL <= 50 us, push-pull, defined below VDD 0.7 V (SLVSES2J)"}),
        ("C505", "Device:C", "100n 50V", C0603, (256.54, 165.1, 0), {"1": "+3V3", "2": "GND"}, dict(C100N, Description="U504 VDD")),
        ("R510", "Device:R", "100k", R0603, (304.8, 172.72, 0), {"1": "P3V3_OK", "2": "GND"},
         rc("RC0603FR-07100KL", "C14675", "P3V3_OK pull-down: low while U504 is unpowered (VDD < 0.7 V) or the DevKit is missing")),
        ("TP505", "Connector:TestPoint", "VBAT_SENSE", TP, (345.44, 104.14, 0), {"1": "VBAT_SENSE"},
         {"_ref_at": (2.54, -1.27), "_val_at": (2.54, 1.27), "Description": "Test point VBAT_SENSE; bare copper pad, excluded from BOM"}),
        ("TP501", "Connector:TestPoint", "GPIO18", TP, (368.3, 104.14, 0), {"1": "SPARE_GPIO18"},
         {"_ref_at": (2.54, -1.27), "_val_at": (2.54, 1.27), "Description": "Spare GPIO18 (input only: high- and low-level power-up glitch); bare copper pad"}),
    ]


def build(root_uuid, sheet_uuid):
    s = Sheet(NS, root_uuid, sheet_uuid, "RoverCore VCU – Controller (DevKit, 5 V, 3.3 V, defaults)",
              "DRAFT – docs/vcu rev1 Versorgung 3.11-3.13, Pinplan")
    s.paper = "A3"
    plist = parts()
    for ref, lib, value, fp, xyr, pins, fields in plist:
        s.part(ref, lib, value, fp, xyr, pins, fields, POWER_NETS,
               dict(HIER, **{k: "global:" + v for k, v in GLOBAL.items()}), in_bom=not ref.startswith("TP"))
    p = next(x for x in plist if x[0] == "C501")
    x, y, rot = p[4]
    lx, ly, la = s.pin_points(p[1])["1"]
    px, py = s.place(x, y, rot, lx, ly)
    dx, dy = s.outward(rot, la)
    s._symbol("power:PWR_FLAG", "#FLG501", "PWR_FLAG", "", round(px + dx * schgen.STUB, 4),
              round(py + dy * schgen.STUB, 4), 0, {"1": "+3V3"}, {})
    s.note("Controller: original ESP32-S3-DevKitC-1-N16R8 v1.1 in socket U501 (pin 1 of J1 and J3 marked; antenna "
           "end and USB end on silkscreen). +3V3 = DevKit LDO output only.", 25.4, 30.48, "h1")
    s.note("5 V: carrier +5V -> D501 -> DevKit 5V pin. With the DevKit USB diodes this is a diode-OR: USB and battery "
           "may be connected at the same time; USB never feeds carrier rails (replaces JP101).", 25.4, 35.56, "h2")
    s.note("Defaults with ESP32 in reset, booting or missing: servo rail OFF (ServoPower R414/Q404/R415), "
           "output buffers Hi-Z (R501), buzzer off, button reads high. Firmware: rail first, then ACT_OE_N low.",
           25.4, 40.64, "h3")
    s.note("O-21: U504 (TLV809E) sets P3V3_OK only while +3V3 >= 2.93 V; it closes the divider switches Q505/Q405 and enables +5V_EXT. BAT54 clamps hold ADC pins <= VDD + 0.24 V.",
           25.4, 45.72, "h4")
    return s.render()


def wire(a, b, key):
    return ("\t(wire\n\t\t(pts\n\t\t\t(xy %s %s) (xy %s %s)\n\t\t)\n\t\t(stroke\n\t\t\t(width 0)\n\t\t\t(type default)\n"
            "\t\t)\n\t\t(uuid \"%s\")\n\t)\n" % (a[0], a[1], b[0], b[1], uuid.uuid5(uuid.UUID(NS), key)))


def main():
    require_closed_kicad()
    if (ROOT / FILE).exists():
        raise SystemExit("%s exists; edit it in KiCad instead of re-running the bootstrap." % FILE)
    root = ROOT_SCH.read_text()
    root_uuid = re.search(r'\(uuid "?([0-9a-f-]{36})"?\)', root).group(1)
    if FILE in root:
        raise SystemExit("Root already references %s" % FILE)
    # ServoPower block sits at (127.0, 86.36), 38.1 x 15.24; its VBAT_PROT feed runs down x = 114.3 to y = 93.98
    if "(xy 114.3 58.42) (xy 114.3 93.98)" not in root:
        raise SystemExit("Root sheet layout differs from the expected one; add the Controller sheet by hand.")
    sheet_uuid = str(uuid.uuid5(uuid.UUID(NS), "sheet-controller"))
    sx, sy, w, h = 127.0, 121.92, 38.1, 15.24
    block = sheet_block(root_uuid, sheet_uuid, "Controller", FILE, sx, sy, w, h, "5",
                        [("VBAT_PROT", "input", "left", 7.62)])
    pin_y = round(sy + 7.62, 4)
    extra = wire((114.3, 93.98), (114.3, pin_y), "root-wire-0") + wire((114.3, pin_y), (sx, pin_y), "root-wire-1")
    extra += ("\t(junction\n\t\t(at 114.3 93.98)\n\t\t(diameter 0)\n\t\t(color 0 0 0 0)\n\t\t(uuid \"%s\")\n\t)\n"
              % uuid.uuid5(uuid.UUID(NS), "root-junction"))
    (ROOT / FILE).write_text(build(root_uuid, sheet_uuid))
    anchor = "\t(sheet_instances\n"
    ROOT_SCH.write_text(root.replace(anchor, block + extra + anchor, 1))
    print("Wrote %s and added sheet 'Controller' to %s" % (FILE, ROOT_SCH.name))


if __name__ == "__main__":
    main()
