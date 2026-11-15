#!/usr/bin/env python3
"""One-time bootstrap of the Lighting_IO sheet: LED outputs, buzzer, i-BUS input, extension UART.

Design basis: docs/vcu/rev1-pin-und-anschlussplan.md 3, 3.1, 4 and 6; Versorgung 3.2, 3.8, 3.13 (O-21).
Parts (datasheets checked 2026-11-15):
- U601-U603 TI TPS2553DBVR (SLVS841G): current-limited switches for the external 5 V outputs, so a cable
  short does not pull down +5V (DevKit, buffers). IOS(min/max) per SLVS841G eq. 1/3: 93.1k -> 0.25/0.32 A
  (LEDs, 0.18 A), 100k -> 0.23/0.30 A (+5V_EXT, 0.2 A budget), 150k -> 0.155/0.21 A (receiver, ~0.1 A).
- U202 TI SN74LVC1T45DBVR (SCES515N): LED_4 3.3 V -> 5 V, DIR via pull-up.
- U203 TI SN74LVC1G17DBVR (SCES351Y): i-BUS input, Schmitt trigger at +3V3, inputs 5.5 V tolerant with Ioff.
- D601-D608 TI TPD1E05U06DPYR (SLVSBO7O): ESD at connector pins, VRWM 5.5 V - only on lines whose
  highest DC level is +5V (LED data, i-BUS, UART).
- Q601 onsemi NTR4501NT1G (Rev 16): buzzer low side, RDS(on) <= 105 mOhm at VGS 2.5 V; D605 PMEG4010CEH
  freewheel (1 A; stuck-on case 5.16 V / 10 Ohm = 0.52 A).
- BZ101 Same Sky CMT-8540S-SMT-TR, project footprint per datasheet rev 1.04.

Usage: python3 hardware/scripts/bootstrap_lighting_io.py
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
FILE = "Lighting_IO.kicad_sch"
NS = "5b8d1f3a-2e6c-4a7b-9d0e-1c3f5a7b0601"
POWER_NETS = {"GND": "power:GND", "+3V3": "power:+3V3", "+5V": "power:+5V"}
GLOBAL = {"LED_1_5V": "input", "LED_2_5V": "input", "LED_3_5V": "input", "LED_4_3V3": "input", "BUZZER": "input",
          "IBUS_RX_3V3": "output", "EXT_UART_TX": "input", "EXT_UART_RX": "output", "P3V3_OK": "input"}
R0603, C0603, C0805 = ("Resistor_SMD:R_0603_1608Metric", "Capacitor_SMD:C_0603_1608Metric",
                       "Capacitor_SMD:C_0805_2012Metric")
YAGEO_RC = "https://www.yageogroup.com/content/datasheet/asset/file/PYU-RC_GROUP_51_ROHS_L"
LCSC_NOTE = "manufacturer datasheet link not verified (O-22)"
C100N = {"Manufacturer": "Yageo", "MPN": "CC0603KRX7R9BB104", "LCSC": "C14663",
         "Datasheet": "https://www.lcsc.com/datasheet/lcsc_datasheet_2211101700_YAGEO-CC0603KRX7R9BB104_C14663.pdf"}
C4U7 = {"Manufacturer": "Yageo", "MPN": "CC0805KKX7R8BB475", "LCSC": "C354262",
        "Description": "4.7 uF 25 V X7R 0805; " + LCSC_NOTE}
TPD = {"Manufacturer": "Texas Instruments", "MPN": "TPD1E05U06DPYR", "LCSC": "C436349",
       "Datasheet": "https://ti.com/lit/pdf/SLVSBO7",
       "Description": "ESD at the connector pin: IEC 61000-4-2 +-12 kV contact, VRWM 5.5 V, 0.5 pF (SLVSBO7O); "
                      "pin 1 I/O, 2 GND; place at the connector"}
TPS = {"Manufacturer": "Texas Instruments", "MPN": "TPS2553DBVR", "LCSC": "C55266", "Datasheet": "https://www.ti.com/lit/pdf/SLVS841"}
JST3 = {"Manufacturer": "JST", "MPN": "B3B-PH-K-S(LF)(SN)", "LCSC": "open (O-22)"}
JST4 = {"Manufacturer": "JST", "MPN": "B4B-PH-K-S(LF)(SN)", "LCSC": "open (O-22)"}
NMOS = "Transistor_FET:Q_NMOS_GSD"
TP = "TestPoint:TestPoint_Pad_D1.5mm"


def rc(mpn, lcsc, desc):
    return {"Manufacturer": "Yageo", "MPN": mpn, "LCSC": lcsc, "Datasheet": YAGEO_RC, "Description": desc}


SWITCHES = [  # (ref, out net, RILIM ref, value, mpn, lcsc, purpose)
    ("U601", "+5V_LED", "R601", "93.1k", "RC0603FR-0793K1L", "C273780", "LED connectors J108-J111 (4 x 44 mA)"),
    ("U602", "+5V_EXT", "R602", "100k", "RC0603FR-07100KL", "C14675", "extension UART J112 (budget 0.2 A)"),
    ("U603", "+5V_RX", "R603", "150k", "RC0603FR-07150KL", "C114660", "receiver J107 (about 0.1 A)"),
]


def parts():
    p = []
    for k, (ref, out, rref, rval, mpn, lcsc, purpose) in enumerate(SWITCHES):
        x0 = 38.1 + 88.9 * k
        n = 601 + 2 * k
        p += [
            (ref, "ProjectSymbols:TPS2553DBV", "TPS2553", "Package_TO_SOT_SMD:SOT-23-6", (x0 + 25.4, 76.2, 0),
             {"1": "+5V", "3": "P3V3_OK" if ref == "U602" else "=1", "2": "GND", "6": out, "4": "NC", "5": "ILIM_%s" % ref},
             dict(TPS, _ref_at=(-7.62, -8.89), _val_at=(2.54, -8.89),
                  Description="5 V switch for %s; %s, auto-retry; FAULT unused" % (purpose, "EN = P3V3_OK (O-21: external device powered only while +3V3 is good; EN VIH 1.1 V)" if ref == "U602" else "EN tied to IN (always on)"))),
            (rref, "Device:R", rval, R0603, (x0 + 50.8, 83.82, 0), {"1": "ILIM_%s" % ref, "2": "GND"},
             rc(mpn, lcsc, "RILIM: IOS per SLVS841G eq. 1/3 (Lighting_IO docstring); keep the trace short")),
            ("C%d" % n, "Device:C", "100n 50V", C0603, (x0 - 5.08, 76.2, 0), {"1": "+5V", "2": "GND"},
             dict(C100N, Description="%s IN capacitor (>= 0.1 uF at the pin, SLVS841G)" % ref)),
            ("C%d" % (n + 1), "Device:C", "4.7u 25V", C0805, (x0 + 66.04, 76.2, 0), {"1": out, "2": "GND"},
             dict(C4U7, Description="%s output capacitor" % ref)),
        ]
    # ---- LED_4 level shifter ----
    p += [
        ("U202", "Logic_LevelTranslator:SN74LVC1T45DBV", "SN74LVC1T45DBVR", "Package_TO_SOT_SMD:SOT-23-6", (88.9, 144.78, 0),
         {"1": "+3V3", "2": "GND", "3": "LED_4_3V3", "4": "LED_4_5V", "5": "U202_DIR", "6": "+5V"},
         {"Manufacturer": "Texas Instruments", "MPN": "SN74LVC1T45DBVR", "LCSC": "C7843", "Datasheet": "https://www.ti.com/lit/pdf/SCES515",
          "_ref_at": (12.7, -10.16), "_val_at": (12.7, -7.62), "Description": "LED_4 3.3 V -> 5 V (no OE); pins 1 VCCA, 2 GND, 3 A, 4 B, 5 DIR, 6 VCCB (SCES515N Table 4-1); Ioff"}),
        ("R604", "Device:R", "10k", R0603, (55.88, 165.1, 0), {"1": "+3V3", "2": "U202_DIR"},
         rc("RC0603FR-0710KL", "C98220", "DIR pull-up: A -> B")),
        ("R605", "Device:R", "100k", R0603, (38.1, 165.1, 0), {"1": "LED_4_3V3", "2": "GND"},
         rc("RC0603FR-07100KL", "C14675", "A-input pull-down: LED_4 data low while GPIO39 is Hi-Z")),
        ("R606", "Device:R", "100k", R0603, (121.92, 165.1, 0), {"1": "LED_4_5V", "2": "GND"},
         rc("RC0603FR-07100KL", "C14675", "B-output pull-down")),
        ("C607", "Device:C", "100n 50V", C0603, (101.6, 121.92, 0), {"1": "+3V3", "2": "GND"}, dict(C100N, Description="U202 VCCA")),
        ("C608", "Device:C", "100n 50V", C0603, (116.84, 121.92, 0), {"1": "+5V", "2": "GND"}, dict(C100N, Description="U202 VCCB")),
    ]
    # ---- LED outputs J108-J111 ----
    for i in range(4):
        x = 152.4 + 55.88 * i
        p += [
            ("R%d" % (607 + i), "Device:R", "330", R0603, (x, 129.54, 0), {"1": "LED_%d_5V" % (i + 1), "2": "LED_%d_DIN" % (i + 1)},
             rc("RC0603FR-07330RL", "C105881", "LED data series resistor: short to GND <= 5.16 V / 330 Ohm = 16 mA; "
                "limits current into an unpowered LED")),
            ("D%d" % (601 + i), "Power_Protection:TPD1E05U06DPY", "TPD1E05U06", "Package_SON:Texas_DPY0002A_0.6x1mm_P0.65mm",
             (x + 15.24, 160.02, 0), {"1": "LED_%d_DIN" % (i + 1), "2": "GND"}, dict(TPD, _ref_at=(-8.89, 0.0), _val_at=(2.54, 5.08))),
            ("J%d" % (108 + i), "Connector_Generic:Conn_01x03", "LED %d" % (i + 1),
             "Connector_JST:JST_PH_B3B-PH-K_1x03_P2.00mm_Vertical", (x + 30.48, 186.69, 0),
             {"1": "+5V_LED", "2": "LED_%d_DIN" % (i + 1), "3": "GND"},
             dict(JST3, Description="SK6812MINI-E LED %d: 1 +5V_LED, 2 data in, 3 GND (JST PH, polarised)" % (i + 1))),
        ]
    # ---- buzzer ----
    p += [
        ("BZ101", "Device:Buzzer", "CMT-8540S-SMT-TR", "ProjectFootprints:MagneticBuzzer_SameSky_CMT-8540S-SMT", (50.8, 210.82, 180),
         {"1": "+5V", "2": "BZ_DRV"},
         {"_ref_at": (-12.7, -5.08), "_val_at": (-27.94, 5.08), "Manufacturer": "Same Sky", "MPN": "CMT-8540S-SMT-TR", "LCSC": "open (LCSC stock 0, O-23)",
          "Datasheet": "https://www.sameskydevices.com/product/resource/cmt-8540s-smt-tr.pdf",
          "Description": "Magnetic transducer, 5 V, coil 10-16 Ohm; drive only with LEDC 4 kHz / 50 % (rev 1.04)"}),
        ("D605", "Device:D_Schottky", "PMEG4010CEH", "Diode_SMD:D_SOD-123F", (88.9, 203.2, 0), {"1": "+5V", "2": "BZ_DRV"},
         {"Manufacturer": "Nexperia", "MPN": "PMEG4010CEH,115", "LCSC": "C193342",
          "Datasheet": "https://assets.nexperia.com/documents/data-sheet/PMEG4010CEH.pdf",
          "Description": "Buzzer freewheel diode, 1 A (stuck-on current 0.52 A)"}),
        ("Q601", NMOS, "NTR4501N", "Package_TO_SOT_SMD:SOT-23", (86.36, 233.68, 0), {"1": "BZ_G", "2": "GND", "3": "BZ_DRV"},
         {"Manufacturer": "onsemi", "MPN": "NTR4501NT1G", "LCSC": "C85416", "Datasheet": "https://www.onsemi.com/pdf/datasheet/ntr4501n-d.pdf",
          "Description": "Buzzer low side: 20 V, 3.2 A, RDS(on) <= 105 mOhm at VGS 2.5 V, VGS(th) 0.65-1.2 V, VGS +-12 V "
                         "(NTR4501N/D Rev 16); pinout 1 G, 2 S, 3 D"}),
        ("R611", "Device:R", "100", R0603, (55.88, 248.92, 90), {"1": "BUZZER", "2": "BZ_G"},
         rc("RC0603FR-07100RL", "C105588", "Gate series resistor")),
        ("R612", "Device:R", "100k", R0603, (73.66, 256.54, 0), {"1": "BZ_G", "2": "GND"},
         rc("RC0603FR-07100KL", "C14675", "Gate pull-down: buzzer off while GPIO12 is Hi-Z")),
        # ---- i-BUS input ----
        ("J107", "Connector_Generic:Conn_01x03", "i-BUS", "Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical",
         (198.12, 220.98, 0), {"1": "IBUS_IN", "2": "+5V_RX", "3": "GND"},
         {"Manufacturer": "generic", "MPN": "1x3 pin header 2.54 mm (part open)",
          "Description": "FS-iA6B i-BUS: 1 signal, 2 +5V_RX, 3 GND; receiver pin order not yet verified (O-10)"}),
        ("D606", "Power_Protection:TPD1E05U06DPY", "TPD1E05U06", "Package_SON:Texas_DPY0002A_0.6x1mm_P0.65mm",
         (190.5, 238.76, 0), {"1": "IBUS_IN", "2": "GND"}, dict(TPD, _ref_at=(-8.89, 0.0), _val_at=(2.54, 5.08))),
        ("R613", "Device:R", "2.2k", R0603, (132.08, 210.82, 0), {"1": "IBUS_IN", "2": "IBUS_A"},
         rc("RC0603FR-072K2L", "C114662", "Series resistor: limits current if the signal exceeds 5.5 V")),
        ("R614", "Device:R", "100k", R0603, (116.84, 233.68, 0), {"1": "IBUS_A", "2": "GND"},
         rc("RC0603FR-07100KL", "C14675", "Input pull-down: no characters without a receiver")),
        ("U203", "74xGxx:74LVC1G17", "SN74LVC1G17DBVR", "Package_TO_SOT_SMD:SOT-23-5", (147.32, 243.84, 0),
         {"1": "NC", "2": "IBUS_A", "3": "GND", "4": "IBUS_RX_3V3", "5": "+3V3"},
         {"Manufacturer": "Texas Instruments", "MPN": "SN74LVC1G17DBVR", "LCSC": "C7836", "Datasheet": "https://www.ti.com/lit/pdf/SCES351",
          "_ref_at": (7.62, -8.89), "_val_at": (7.62, -6.35), "Description": "Schmitt-trigger buffer at +3V3, input 5.5 V tolerant, Ioff; DBV pins 1 NC, 2 A, 3 GND, 4 Y, 5 VCC (SCES351Y)"}),
        ("C610", "Device:C", "100n 50V", C0603, (119.38, 259.08, 0), {"1": "+3V3", "2": "GND"}, dict(C100N, Description="U203 VCC")),
        ("TP601", "Connector:TestPoint", "IBUS_RX", TP, (172.72, 259.08, 0), {"1": "IBUS_RX_3V3"},
         {"Description": "Test point i-BUS after U203; bare copper pad, excluded from BOM", "_ref_at": (2.54, -1.27), "_val_at": (2.54, 1.27)}),
        # ---- extension UART J112 ----
        ("J112", "Connector_Generic:Conn_01x04", "EXT UART", "Connector_JST:JST_PH_B4B-PH-K_1x04_P2.00mm_Vertical",
         (320.04, 228.6, 0), {"1": "+5V_EXT", "2": "EXT_TX_C", "3": "EXT_RX_C", "4": "GND"},
         dict(JST4, Description="Extension UART: 1 +5V_EXT (<= 0.2 A, U602), 2 TX (from VCU), 3 RX (3.3 V, not 5 V tolerant), 4 GND")),
        ("R615", "Device:R", "1k", R0603, (220.98, 223.52, 0), {"1": "EXT_UART_TX", "2": "EXT_TX_C"},
         rc("RC0603FR-071KL", "C22548", "O-21: limits backfeed into an unpowered external device (<= 3.3 mA)")),
        ("R616", "Device:R", "4.7k", R0603, (236.22, 223.52, 0), {"1": "EXT_RX_C", "2": "EXT_UART_RX"},
         rc("RC0603FR-074K7L", "C99782", "O-21: limits current into GPIO48 while +3V3 is absent (<= 0.64 mA at 3.3 V level)")),
        ("R617", "Device:R", "10k", R0603, (248.92, 223.52, 0), {"1": "+3V3", "2": "EXT_UART_RX"},
         rc("RC0603FR-0710KL", "C98220", "RX idle-high pull-up to +3V3 (no clamp diode to +3V3: it would backfeed the rail)")),
        ("D607", "Power_Protection:TPD1E05U06DPY", "TPD1E05U06", "Package_SON:Texas_DPY0002A_0.6x1mm_P0.65mm",
         (266.7, 246.38, 0), {"1": "EXT_TX_C", "2": "GND"}, dict(TPD, _ref_at=(-8.89, 0.0), _val_at=(2.54, 5.08))),
        ("D608", "Power_Protection:TPD1E05U06DPY", "TPD1E05U06", "Package_SON:Texas_DPY0002A_0.6x1mm_P0.65mm",
         (292.1, 246.38, 0), {"1": "EXT_RX_C", "2": "GND"}, dict(TPD, _ref_at=(-8.89, 0.0), _val_at=(2.54, 5.08))),
        ("TP602", "Connector:TestPoint", "LED1", TP, (378.46, 129.54, 0), {"1": "LED_1_DIN"},
         {"Description": "Test point LED 1 data; bare copper pad, excluded from BOM", "_ref_at": (2.54, -1.27), "_val_at": (2.54, 1.27)}),
    ]
    return p


def build(root_uuid, sheet_uuid):
    s = Sheet(NS, root_uuid, sheet_uuid, "RoverCore VCU – Lighting_IO (LEDs, buzzer, i-BUS, extension UART)",
              "DRAFT – docs/vcu rev1 Pinplan 3/4/6, Versorgung 3.8/3.13")
    s.paper = "A3"
    for ref, lib, value, fp, xyr, pins, fields in parts():
        s.part(ref, lib, value, fp, xyr, pins, fields, POWER_NETS, {k: "global:" + v for k, v in GLOBAL.items()},
               in_bom=not ref.startswith("TP"))
    s.note("External 5 V outputs through current-limited switches U601-U603 (TPS2553): a cable short trips only that "
           "group, +5V for DevKit and buffers stays up. Limits 0.25-0.32 / 0.23-0.30 / 0.155-0.21 A.", 25.4, 30.48, "h1")
    s.note("Signals at connectors: series resistor + TPD1E05U06 (VRWM 5.5 V) - only lines whose highest DC level is +5V. "
           "Buzzer only with LEDC 4 kHz / 50 %; Q601 and D605 rated for the stuck-on 0.52 A.", 25.4, 35.56, "h2")
    return s.render()


def main():
    require_closed_kicad()
    if (ROOT / FILE).exists():
        raise SystemExit("%s exists; edit it in KiCad instead of re-running the bootstrap." % FILE)
    root = ROOT_SCH.read_text()
    root_uuid = re.search(r'\(uuid "?([0-9a-f-]{36})"?\)', root).group(1)
    if FILE in root:
        raise SystemExit("Root already references %s" % FILE)
    sheet_uuid = str(uuid.uuid5(uuid.UUID(NS), "sheet-lighting-io"))
    block = sheet_block(root_uuid, sheet_uuid, "Lighting_IO", FILE, 190.5, 50.8, 38.1, 15.24, "7", [])
    (ROOT / FILE).write_text(build(root_uuid, sheet_uuid))
    ROOT_SCH.write_text(root.replace("\t(sheet_instances\n", block + "\t(sheet_instances\n", 1))
    print("Wrote %s and added sheet 'Lighting_IO' to %s" % (FILE, ROOT_SCH.name))


if __name__ == "__main__":
    main()
