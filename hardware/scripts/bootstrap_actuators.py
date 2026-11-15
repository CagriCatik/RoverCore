#!/usr/bin/env python3
"""One-time bootstrap of the Actuators sheet: 3.3 V -> 5 V output buffer, servo and ESC connectors.

Design basis: docs/vcu/rev1-pin-und-anschlussplan.md 3.1 and 4 (connector pinouts), Versorgung 3.12/3.13
(default states). U201 SN74LVC8T245PWR per TI SCES584D (May 2026): pins 1 VCCA, 2 DIR, 3-10 A1-A8,
11-13 GND, 14-21 B8-B1, 22 OE (active low, VCCA-referenced), 23/24 VCCB; Ioff +-2 uA; VCC isolation.

Per output channel to a connector (ESC, 4 servos), revised after review (no rail clamp):
  U201 B output -> gate of NTR4003N Q20x (open drain, 30 V) -> 470 Ohm -> connector pin 1;
  pull-up +5V -> BAT54 -> 2.2k to the drain, 100k drain pull-down.
  A foreign voltage on the signal pin (ESC BEC up to 7.4 V, servo rail fault 7.81 V) sees the drain and the
  reverse-biased BAT54 only: no current into +5V, with the VCU on or off; U201 is not connected to the pin.
  The stage inverts: A-input and gate pull-ups keep the line LOW while GPIO or U201 are Hi-Z; firmware inverts
  the LEDC outputs (GPIO matrix output inversion).
LED_1..3 leave this sheet as 5 V signals (LED_x_5V) with pull-downs; their connector protection is on
Lighting_IO. ESC connector pin 2 (BEC +) is not connected. The ACT_OE_N pull-up (R501) sits on Controller.

Usage: python3 hardware/scripts/bootstrap_actuators.py
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
FILE = "Actuators.kicad_sch"
NS = "7e2c5a90-1d3b-4c6f-8a2e-9b4d6f1c0201"
POWER_NETS = {"GND": "power:GND", "+3V3": "power:+3V3", "+5V": "power:+5V"}
GLOBAL = {
    "ACT_OE_N": "input", "ESC_PWM_3V3": "input", "SERVO_FRONT_PWM_3V3": "input", "SERVO_REAR_PWM_3V3": "input",
    "SERVO_AUX1_PWM_3V3": "input", "SERVO_AUX2_PWM_3V3": "input",
    "LED_1_3V3": "input", "LED_2_3V3": "input", "LED_3_3V3": "input",
    "LED_1_5V": "output", "LED_2_5V": "output", "LED_3_5V": "output", "+V_SERVO": "input",
}
R0603, C0603 = "Resistor_SMD:R_0603_1608Metric", "Capacitor_SMD:C_0603_1608Metric"
YAGEO_RC = "https://www.yageogroup.com/content/datasheet/asset/file/PYU-RC_GROUP_51_ROHS_L"
C100N = {"Manufacturer": "Yageo", "MPN": "CC0603KRX7R9BB104", "LCSC": "C14663",
         "Datasheet": "https://www.lcsc.com/datasheet/lcsc_datasheet_2211101700_YAGEO-CC0603KRX7R9BB104_C14663.pdf"}

def rc(mpn, lcsc, desc):
    return {"Manufacturer": "Yageo", "MPN": mpn, "LCSC": lcsc, "Datasheet": YAGEO_RC, "Description": desc}


R100K = ("RC0603FR-07100KL", "C14675")
QNTR = {"Manufacturer": "onsemi", "MPN": "NTR4003NT1G", "LCSC": "C82325",
        "Datasheet": "https://www.onsemi.com/download/data-sheet/pdf/ntr4003n-d.pdf"}
DBAT54 = {"Manufacturer": "Nexperia", "MPN": "BAT54,215", "LCSC": "C85084",
          "Datasheet": "https://www.lcsc.com/datasheet/lcsc_datasheet_2407241045_Nexperia-BAT54-215_C85084.pdf",
          "Description": "Blocks reverse current from the signal line into +5V (VCU on or off); VR 30 V, IR <= 2 uA at 25 V "
                         "(Nexperia BAT54 2022-07-01, LCSC copy)"}
R470 = ("RC0603FR-07470RL", "C114669")

# channel: (A pin, B pin, 3.3 V input net, buffer output net, connector net or None, connector ref, purpose)
CHANNELS = [
    (3, 21, "ESC_PWM_3V3", "ESC_PWM_B", "ESC_OUT", "J106", "ESC"),
    (4, 20, "SERVO_FRONT_PWM_3V3", "SERVO_FRONT_B", "SERVO_FRONT_OUT", "J102", "steering servo front"),
    (5, 19, "SERVO_REAR_PWM_3V3", "SERVO_REAR_B", "SERVO_REAR_OUT", "J103", "steering servo rear"),
    (6, 18, "SERVO_AUX1_PWM_3V3", "SERVO_AUX1_B", "SERVO_AUX1_OUT", "J104", "reserve servo 1"),
    (7, 17, "SERVO_AUX2_PWM_3V3", "SERVO_AUX2_B", "SERVO_AUX2_OUT", "J105", "reserve servo 2"),
    (8, 16, "LED_1_3V3", "LED_1_5V", None, None, "LED 1 data"),
    (9, 15, "LED_2_3V3", "LED_2_5V", None, None, "LED 2 data"),
    (10, 14, "LED_3_3V3", "LED_3_5V", None, None, "LED 3 data"),
]

MICROFIT = {"Manufacturer": "Molex", "MPN": "43650-0300", "LCSC": "C503478",
            "Description": "Micro-Fit 3.0 1x3 right angle THT; 1 signal, 2 +V_SERVO, 3 GND (RC order); keyed; "
                           "8 A per contact UL, 3-pin derating interpolated (Anschlussplan 4)"}
HEADER = {"Manufacturer": "generic", "MPN": "1x3 pin header 2.54 mm, vertical (part open)",
          "Description": "2.54 mm 1x3 header; silkscreen 'S + -' and 'max 0.5 A'"}


def parts():
    u = {"1": "+3V3", "2": "U201_DIR", "11": "GND", "12": "GND", "13": "GND", "22": "ACT_OE_N", "23": "+5V", "24": "+5V"}
    for a, b, inp, out, *_ in CHANNELS:
        u[str(a)], u[str(b)] = inp, out
    plist = [
        ("U201", "Logic_LevelTranslator:SN74LVC8T245", "SN74LVC8T245PWR", "Package_SO:TSSOP-24_4.4x7.8mm_P0.65mm",
         (190.5, 127.0, 0), u,
         {"Manufacturer": "Texas Instruments", "MPN": "SN74LVC8T245PWR", "LCSC": "C27643",
          "Datasheet": "https://ti.com/lit/pdf/SCES584", "_ref_at": (12.7, -27.94), "_val_at": (12.7, -25.4), "_stub": {"2": 25.4},
          "Description": "8-bit dual-supply translator A(3.3 V) -> B(5 V); DIR high = A to B; OE (ACT_OE_N) high = all "
                         "outputs Hi-Z; Ioff +-2 uA; VCC isolation below 100 mV (SCES584D)"}),
        ("C201", "Device:C", "100n 50V", C0603, (167.64, 86.36, 0), {"1": "+3V3", "2": "GND"},
         dict(C100N, Description="U201 VCCA decoupling, at pin 1")),
        ("C202", "Device:C", "100n 50V", C0603, (210.82, 86.36, 0), {"1": "+5V", "2": "GND"},
         dict(C100N, Description="U201 VCCB decoupling, at pins 23/24")),
        ("R209", "Device:R", "10k", R0603, (152.4, 86.36, 0), {"1": "+3V3", "2": "U201_DIR"},
         rc("RC0603FR-0710KL", "C98220", "DIR pull-up to VCCA: direction A -> B (DIR input current <= 2 uA -> 20 mV)")),
    ]
    for i, (a, b, inp, out, conn_net, conn, purpose) in enumerate(CHANNELS):
        if conn:   # inverted open-drain stage: idle (A high / B Hi-Z) must give a LOW line
            plist.append(("R%d" % (201 + i), "Device:R", "100k", R0603, (30.48 + 15.24 * i, 86.36, 0), {"1": "+3V3", "2": inp},
                          rc(*R100K, "A-input pull-up (%s): GPIO Hi-Z -> A high -> Q on -> line low (stage inverts)" % purpose)))
            plist.append(("R%d" % (211 + i), "Device:R", "100k", R0603, (236.22 + 15.24 * i, 86.36, 0), {"1": "+5V", "2": out},
                          rc(*R100K, "Gate pull-up (%s): U201 Hi-Z (ACT_OE_N high, VCC isolation) -> Q on -> line low" % purpose)))
        else:
            plist.append(("R%d" % (201 + i), "Device:R", "100k", R0603, (30.48 + 15.24 * i, 86.36, 0), {"1": inp, "2": "GND"},
                          rc(*R100K, "A-input pull-down (%s): defined low while GPIO is Hi-Z" % purpose)))
            plist.append(("R%d" % (211 + i), "Device:R", "100k", R0603, (236.22 + 15.24 * i, 86.36, 0), {"1": out, "2": "GND"},
                          rc(*R100K, "B-output pull-down (%s): data low while U201 is Hi-Z" % purpose)))
    for i, (a, b, inp, out, conn_net, conn, purpose) in enumerate(CHANNELS[:5]):
        x = 38.1 + 76.2 * i
        drv, pu = conn_net.replace("_OUT", "_DRV"), conn_net.replace("_OUT", "_PU")
        plist += [
            ("Q%d" % (201 + i), "Transistor_FET:Q_NMOS_GSD", "NTR4003N", "Package_TO_SOT_SMD:SOT-23", (x, 205.74, 0),
             {"1": out, "2": "GND", "3": drv},
             dict(QNTR, Description="Open-drain output stage (%s): drain withstands 30 V, so a foreign voltage on the signal "
                  "pin (ESC BEC 7.4 V, rail fault 7.81 V) reaches neither U201 nor +5V. VGS from U201 B = VCCB" % purpose)),
            ("D%d" % (201 + i), "ProjectSymbols:BAT54_SOT23", "BAT54", "Package_TO_SOT_SMD:SOT-23", (x + 10.16, 160.02, 0),
             {"1": "+5V", "3": pu}, dict(DBAT54)),
            ("R%d" % (231 + i), "Device:R", "2.2k", R0603, (x + 20.32, 182.88, 0), {"1": pu, "2": drv},
             rc("RC0603FR-072K2L", "C114662", "Pull-up for the open-drain line (%s): high = 5 V - VF(D) - I x 2.2k; 2.1 mA while low" % purpose)),
            ("R%d" % (241 + i), "Device:R", "100k", R0603, (x + 20.32, 223.52, 0), {"1": drv, "2": "GND"},
             rc(*R100K, "Line pull-down (%s): defined low with the VCU off" % purpose)),
            ("R%d" % (221 + i), "Device:R", "470", R0603, (x + 33.02, 205.74, 0), {"1": drv, "2": conn_net},
             rc(*R470, "Series resistor to %s (%s): limits a foreign source into Q (7.81 V / 470 Ohm = 17 mA)" % (conn, purpose))),
        ]
        pins = {"1": conn_net, "2": "NC" if conn == "J106" else "+V_SERVO", "3": "GND"}
        if conn in ("J102", "J103"):
            lib, fp, fields, value = "Connector_Generic:Conn_01x03", \
                "Connector_Molex:Molex_Micro-Fit_3.0_43650-0300_1x03_P3.00mm_Horizontal", dict(MICROFIT), "Micro-Fit 3"
        else:
            lib, fp, fields, value = "Connector_Generic:Conn_01x03", "Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical", \
                dict(HEADER), "Header 1x3"
        if conn == "J106":
            fields["Description"] = ("ESC (Hobbywing QuicRun Fusion Pro): 1 signal, 2 BEC + NOT CONNECTED, 3 GND; "
                                     "silkscreen 'BEC NC'")
        fields["Description"] = "%s – %s" % (purpose, fields["Description"])
        plist.append((conn, lib, value, fp, (x + 55.88, 241.3, 0), pins, fields))
    return plist


def build(root_uuid, sheet_uuid):
    s = Sheet(NS, root_uuid, sheet_uuid, "RoverCore VCU – Actuators (buffer U201, servo and ESC connectors)",
              "DRAFT – docs/vcu rev1 Pinplan 3.1/4, Versorgung 3.13")
    s.paper = "A3"
    for ref, lib, value, fp, xyr, pins, fields in parts():
        s.part(ref, lib, value, fp, xyr, pins, fields, POWER_NETS, {k: "global:" + v for k, v in GLOBAL.items()})
    s.note("U201 SN74LVC8T245: DIR = +3V3 (A -> B). ACT_OE_N high (R501 on Controller) or VCCA/VCCB < 100 mV -> "
           "all outputs Hi-Z; gate pull-ups -> Q20x on -> ESC and servo lines LOW (no pulse).", 25.4, 30.48, "h1")
    s.note("Connector outputs: B -> Q20x open drain (pull-up via BAT54 + 2.2k) -> 470 Ohm -> pin 1; inverted (firmware). J102/J103 Micro-Fit, "
           "J104/J105 2.54 mm headers (0.5 A budget), J106 ESC with pin 2 (BEC +) not connected.", 25.4, 35.56, "h2")
    s.note("ESD: a TVS at each connector pin must tolerate 7.81 V continuously (servo-rail fault, ESC BEC) – "
           "selection open (O-30). LED_1..3_5V go to Lighting_IO.", 25.4, 40.64, "h3")
    return s.render()


def main():
    require_closed_kicad()
    if (ROOT / FILE).exists():
        raise SystemExit("%s exists; edit it in KiCad instead of re-running the bootstrap." % FILE)
    root = ROOT_SCH.read_text()
    root_uuid = re.search(r'\(uuid "?([0-9a-f-]{36})"?\)', root).group(1)
    if FILE in root:
        raise SystemExit("Root already references %s" % FILE)
    sheet_uuid = str(uuid.uuid5(uuid.UUID(NS), "sheet-actuators"))
    block = sheet_block(root_uuid, sheet_uuid, "Actuators", FILE, 127.0, 157.48, 38.1, 15.24, "6", [])
    (ROOT / FILE).write_text(build(root_uuid, sheet_uuid))
    ROOT_SCH.write_text(root.replace("\t(sheet_instances\n", block + "\t(sheet_instances\n", 1))
    print("Wrote %s and added sheet 'Actuators' to %s" % (FILE, ROOT_SCH.name))


if __name__ == "__main__":
    main()
