#!/usr/bin/env python3
"""One-time bootstrap of the ServoPower sheet: LTC7803 servo rail with output current sensing.

Design basis: docs/vcu/rev1-versorgung-und-boardwahl.md sections 3.4-3.6 (3S,
6.8 V candidate, 11 A design target). LTC7803 details from datasheet Rev A
(Rev B not yet obtained). Kelvin sense connections and the feedback tap are
explicit net ties (NT401-NT405) so they can be routed as separate traces.
Writes ServoPower.kicad_sch and adds the sheet to RoverCore.kicad_sch, fed
from the Power sheet's VBAT_PROT pin. Signals to the Controller sheet are global labels. SERVO_PWR_EN (active high,
default OFF) replaced SERVO_PWR_DIS on 2026-11-15.

Usage: python3 hardware/scripts/bootstrap_servo_power.py
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
FILE = "ServoPower.kicad_sch"
NS = "9a4f2c1e-7b3d-4e6a-8c5f-0d2b1a3e4401"
POWER_NETS = {"GND": "power:GND", "+3V3": "power:+3V3"}
HIER = {"VBAT_PROT": "input"}
GLOBAL = {"SERVO_PWR_EN": "input", "VSERVO_SENSE": "output", "ISERVO_SENSE": "output", "+V_SERVO": "output"}

YAGEO_RC = "https://www.yageogroup.com/content/datasheet/asset/file/PYU-RC_GROUP_51_ROHS_L"
R0603, C0603, C0805 = ("Resistor_SMD:R_0603_1608Metric", "Capacitor_SMD:C_0603_1608Metric",
                       "Capacitor_SMD:C_0805_2012Metric")
NT = "NetTie:NetTie-2_SMD_Pad0.5mm"
FET, NMOS_SMALL = "Transistor_FET:Q_NMOS_SSSGD_AvalancheRated", "Transistor_FET:Q_NMOS_GSD"


def rc(mpn, lcsc, desc):
    return {"Manufacturer": "Yageo", "MPN": mpn, "LCSC": lcsc, "Datasheet": YAGEO_RC, "Description": desc}


LCSC_NOTE = "manufacturer datasheet link not verified (O-22); series checked on the LCSC copy"


def mlcc(mfr, mpn, lcsc, desc):
    return {"Manufacturer": mfr, "MPN": mpn, "LCSC": lcsc, "Description": desc + "; " + LCSC_NOTE}


# Small-part selection from the 2026-11-15 sourcing check (JLCPCB stock at that date).
PARTS_DATA = {
    "C10U50": {"Manufacturer": "Samsung", "MPN": "CL32B106KBJNNNE", "LCSC": "C138687",
               "Description": "10 uF 50 V X7R 1210 input capacitor; " + LCSC_NOTE},
    "C100N": {"Manufacturer": "Yageo", "MPN": "CC0603KRX7R9BB104", "LCSC": "C14663",
              "Datasheet": "https://www.lcsc.com/datasheet/lcsc_datasheet_2211101700_YAGEO-CC0603KRX7R9BB104_C14663.pdf"},
    "C1N": mlcc("Yageo", "CC0603JRNPO9BN102", "C106246", "1 nF 50 V C0G"),
    "C4U7": mlcc("Yageo", "CC0805KKX7R8BB475", "C354262", "4.7 uF 25 V X7R 0805"),
    "C1U": mlcc("Samsung", "CL10B105KA8NNNC", "C29936", "1 uF 25 V X7R 0603"),
    "C33N": mlcc("Samsung", "CL10B333KB8NNNC", "C21117", "33 nF 50 V X7R"),
    "C3N3": mlcc("Yageo", "CC0603JRNPO9BN332", "C107048", "3.3 nF 50 V C0G"),
    "C100P": mlcc("Samsung", "CL10C101JB8NNNC", "C14858", "100 pF 50 V C0G"),
    "R100": {"Manufacturer": "Yageo", "MPN": "RC0603FR-07100RL", "LCSC": "open (O-22)", "Datasheet": YAGEO_RC},
    "R1K": rc("RC0603FR-071KL", "C22548", ""),
    "R11K": rc("RC0603FR-0711KL", "C137801", ""),
    "R140K": rc("RC0603FR-07140KL", "C185372", ""),
    "R20K": rc("RC0603FR-0720KL", "C105575", ""),
    "R47K": rc("RC0603FR-0747KL", "C105579", ""),
    "R75K": {"Manufacturer": "Yageo", "MPN": "RT0603BRD0775KL", "LCSC": "C723587",
             "Description": "thin film 0.1 %, 25 ppm/K; " + LCSC_NOTE},
    "R10K01": {"Manufacturer": "Yageo", "MPN": "RT0603BRD0710KL", "LCSC": "C95204",
               "Description": "thin film 0.1 %, 25 ppm/K; " + LCSC_NOTE},
    "QNTR": {"Manufacturer": "onsemi", "MPN": "NTR4003NT1G", "LCSC": "C82325",
             "Datasheet": "https://www.onsemi.com/download/data-sheet/pdf/ntr4003n-d.pdf",
             "Description": "30 V N-MOSFET, VGS(th) 0.8-1.4 V, RDS(on) <= 2.0 Ohm at VGS 2.5 V / 1.5 Ohm at 4.0 V, "
                            "IDSS <= 1 uA at 25 degC (NTR4003N/D Rev 6, Jan 2026); pinout 1 G, 2 S, 3 D"},
    "DBOOT": {"Value": "BAS316", "Footprint": "Diode_SMD:D_SOD-323",
              "fields": {"Manufacturer": "Nexperia", "MPN": "BAS316,115", "LCSC": "C109218",
                         "Description": "Boost diode INTVCC->BOOST; reverse voltage about VIN; fast PN chosen for low hot leakage "
                                        "(30 uA max at 150 degC, 25 V) below the 30 uA min charge pump; costs ~0.4 V gate drive "
                                        "vs Schottky (O-25); " + LCSC_NOTE}},
}


def parts():
    P = PARTS_DATA
    return [
        # ---- controller ----
        ("U401", "ProjectSymbols:LTC7803", "LTC7803", "ProjectFootprints:ADI_MSE16_MSOP-16-1EP_ThermalVias",
         (101.6, 226.06, 0),
         {"12": "VBAT_PROT", "6": "RUN_SERVO", "11": "VSERVO_REG", "1": "SS_SERVO", "7": "GND", "8": "GND",
          "9": "INTVCC_SERVO", "5": "ITH_SERVO", "14": "BOOST_SERVO", "15": "TG_SERVO", "16": "SW_SERVO",
          "13": "BG_SERVO", "10": "INTVCC_SERVO", "2": "SENSE_P", "3": "SENSE_N", "4": "VFB_SERVO", "17": "GND"},
         {"Manufacturer": "Analog Devices", "MPN": "LTC7803EMSE#PBF", "LCSC": "C1016554",
          "Datasheet": "https://www.analog.com/media/en/technical-documentation/data-sheets/ltc7803.pdf",
          "_ref_at": (-12.7, -19.05), "_val_at": (2.54, -19.05),
          "Description": "Sync buck controller, 100 % duty; FREQ=GND 375 kHz, PLLIN/SPREAD=GND fixed, MODE=INTVCC "
                         "forced continuous, EXTVCC=VOUT (6.8 V > 4.7 V switchover); pins per Rev A"}),
        # ---- power stage ----
        ("Q401", FET, "BSC026N04LS", "ProjectFootprints:Infineon_PG-TDSON-8_BSC026N04LS", (152.4, 96.52, 0),
         {"1": "SW_SERVO", "2": "SW_SERVO", "3": "SW_SERVO", "4": "TG_SERVO", "5": "VBAT_PROT"},
         {"Manufacturer": "Infineon", "MPN": "BSC026N04LS", "LCSC": "C3039672",
          "Datasheet": "https://www.infineon.com/dgdl/Infineon-BSC026N04LS-DS-v02_01-EN.pdf?fileId=5546d462525dbac40152ae7e3a463fb0",
          "Description": "Top FET, 40 V, 3.6 mOhm max at VGS 4.5 V; generic SSSGD symbol (S 1-3, G 4, D 5) matches PG-TDSON-8"}),
        ("Q402", FET, "BSC026N04LS", "ProjectFootprints:Infineon_PG-TDSON-8_BSC026N04LS", (152.4, 147.32, 0),
         {"1": "GND", "2": "GND", "3": "GND", "4": "BG_SERVO", "5": "SW_SERVO"},
         {"Manufacturer": "Infineon", "MPN": "BSC026N04LS", "LCSC": "C3039672",
          "Datasheet": "https://www.infineon.com/dgdl/Infineon-BSC026N04LS-DS-v02_01-EN.pdf?fileId=5546d462525dbac40152ae7e3a463fb0",
          "Description": "Bottom FET, same type as Q401"}),
        ("L401", "Device:L", "3.3u", "Inductor_SMD:L_Coilcraft_XAL1010-XXX", (190.5, 119.38, 90),
         {"1": "SW_SERVO", "2": "ISNS_PWR"},
         {"Manufacturer": "Coilcraft", "MPN": "XAL1010-332MED", "LCSC": "C3911672",
          "Description": "3.3 uH candidate (2.2 uH alternative): Isat 27.4 A (-30 %, 25 degC), Irms 18.2 A (+20 K), "
                         "DCR max 4.10 mOhm (Coilcraft doc 804-1); datasheet source open (coilcraft.com blocks automated access)"}),
        ("RS401", "Device:R", "3m", "ProjectFootprints:R_Vishay_WSL1020", (238.76, 119.38, 90),
         {"1": "ISNS_PWR", "2": "VSERVO_REG"},
         {"Manufacturer": "Vishay", "MPN": "WSL10203L000FEA", "LCSC": "C844481", "Datasheet": "https://www.vishay.com/doc?30183",
          "Description": "LTC7803 current sense 3 mOhm 1 %, 2 W, wide terminal; land pattern per Vishay doc 30183 (O-26)"}),
        ("NT401", "Device:NetTie_2", "Kelvin", NT, (213.36, 88.9, 0), {"1": "ISNS_PWR", "2": "SENSE_P_K"},
         {"Description": "Kelvin tap SENSE+ at RS401 pad 1 (inductor side); route SENSE+ and SENSE- as a close pair"}),
        ("NT402", "Device:NetTie_2", "Kelvin", NT, (259.08, 88.9, 0), {"1": "VSERVO_REG", "2": "SENSE_N"},
         {"Description": "Kelvin tap SENSE- at RS401 pad 2 (output side); no filter resistor (SENSE- draws ~0.7 mA at 6.8 V)"}),
        ("RF401", "Device:R", "100", R0603, (233.68, 60.96, 90), {"1": "SENSE_P_K", "2": "SENSE_P"},
         dict(P["R100"], Description="Sense filter RF in SENSE+ only (datasheet Fig. 2a); RF*CF = ESL/RSENSE, start value, tune in lab")),
        ("CF401", "Device:C", "1n C0G", C0603, (264.16, 63.5, 0), {"1": "SENSE_P", "2": "SENSE_N"},
         dict(P["C1N"], Description="Sense filter CF across SENSE+/SENSE- near the IC (datasheet Fig. 2a)")),
        # ---- input capacitors ----
        *[("C%d" % (401 + i), "Device:C", "10u 50V", "Capacitor_SMD:C_1210_3225Metric", (40.64 + 12.7 * i, 129.54, 0),
           {"1": "VBAT_PROT", "2": "GND"}, P["C10U50"]) for i in range(4)],
        ("C405", "Device:C", "100n 50V", C0603, (91.44, 129.54, 0), {"1": "VBAT_PROT", "2": "GND"},
         dict(P["C100N"], Description="VIN pin decoupling at U401 pin 12")),
        # ---- output capacitors ----
        *[("C%d" % (406 + i), "Device:C_Polarized", "270u 16V", "ProjectFootprints:CP_Panasonic_OSCON_SVPG_C8", (251.46 + 12.7 * i, 154.94, 0),
           {"1": "VSERVO_REG", "2": "GND"},
           {"Manufacturer": "Panasonic", "MPN": "16SVPG270MX", "LCSC": "C2161621",
            "Description": "Polymer 270 uF 16 V, ESR max 10 mOhm; land pattern per Panasonic AAB8000COL10 (O-26); datasheet source open"})
          for i in range(2)],
        *[("C%d" % (408 + i), "Device:C", "22u 25V", "Capacitor_SMD:C_1210_3225Metric", (276.86 + 12.7 * i, 154.94, 0),
           {"1": "VSERVO_REG", "2": "GND"},
           {"Manufacturer": "Murata", "MPN": "GRM32ER71E226KE15L", "LCSC": "C21397",
            "Datasheet": "https://www.lcsc.com/datasheet/lcsc_datasheet_2308111542_Murata-Electronics-GRM32ER71E226KE15L_C21397.pdf",
            "Description": "22 uF 25 V X7R; Murata typ. DC bias at 6.8 V to be read from SimSurfing"})
          for i in range(3)],
        # ---- controller support ----
        ("D401", "Device:D", P["DBOOT"]["Value"], P["DBOOT"]["Footprint"], (132.08, 177.8, 0),
         {"1": "BOOST_SERVO", "2": "INTVCC_SERVO"}, P["DBOOT"]["fields"]),
        ("C411", "Device:C", "1u 25V", C0603, (172.72, 177.8, 0), {"1": "BOOST_SERVO", "2": "SW_SERVO"},
         dict(P["C1U"], Description="Bootstrap capacitor CB: datasheet requires >= 100 x top-FET input capacitance (BSC026N04LS Ciss max 3.22 nF -> >= 0.32 uF); 1 uF 25 V X7R, DC bias at 5 V not verified; manufacturer datasheet link not verified (O-22)")),
        ("C412", "Device:C", "4.7u", C0805, (124.46, 266.7, 0), {"1": "INTVCC_SERVO", "2": "GND"},
         dict(P["C4U7"], Description="INTVCC >= 4.7 uF ceramic (datasheet pin functions)")),
        ("C413", "Device:C", "1u", C0603, (139.7, 266.7, 0), {"1": "INTVCC_SERVO", "2": "GND"},
         dict(P["C1U"], Description="Extra 1 uF at INTVCC/GND pins (layout checklist)")),
        ("C414", "Device:C", "33n", C0603, (40.64, 266.7, 0), {"1": "SS_SERVO", "2": "GND"},
         dict(P["C33N"], Description="Soft start 33 nF -> about 2.1 ms (0.8 V / 12.5 uA)")),
        ("R413", "Device:R", "11k", R0603, (55.88, 266.7, 0), {"1": "ITH_SERVO", "2": "ITH_RC"},
         dict(P["R11K"], Description="ITH compensation RC, start value from datasheet Fig. 13 (5 V/10 A); tune in lab")),
        ("C418", "Device:C", "3.3n", C0603, (71.12, 266.7, 0), {"1": "ITH_RC", "2": "GND"},
         dict(P["C3N3"], Description="ITH compensation CC, start value Fig. 13")),
        ("C419", "Device:C", "100p C0G", C0603, (86.36, 266.7, 0), {"1": "ITH_SERVO", "2": "GND"},
         dict(P["C100P"], Description="ITH compensation CC2, start value Fig. 13")),
        # ---- feedback (tap explicit) ----
        ("NT403", "Device:NetTie_2", "FB tap", NT, (213.36, 172.72, 0), {"1": "VSERVO_REG", "2": "VFB_TAP"},
         {"Description": "Feedback tap: single point at the output capacitors, BEFORE the output shunt RS402"}),
        ("R403", "Device:R", "75.0k 0.1%", R0603, (236.22, 185.42, 0), {"1": "VFB_TAP", "2": "VFB_SERVO"},
         dict(P["R75K"], Description="Feedback top: 0.8 V x (1 + 75.0/10.0) = 6.80 V, 6.69-6.91 V with VFB +-1.5 %")),
        ("R404", "Device:R", "10.0k 0.1%", R0603, (236.22, 231.14, 0), {"1": "VFB_SERVO", "2": "GND"},
         dict(P["R10K01"], Description="Feedback bottom")),
        # ---- RUN / shutdown ----
        ("R405", "Device:R", "140k", R0603, (35.56, 182.88, 0), {"1": "VBAT_PROT", "2": "RUN_SERVO"},
         dict(P["R140K"], Description="RUN divider top: on 9.60 V, off 8.80 V")),
        ("R406", "Device:R", "20k", R0603, (50.8, 210.82, 0), {"1": "RUN_SERVO", "2": "GND"},
         dict(P["R20K"], Description="RUN divider bottom; RUN at 21.5 V TVS clamp about 2.7 V")),
        ("Q403", NMOS_SMALL, "NTR4003N", "Package_TO_SOT_SMD:SOT-23", (81.28, 182.88, 0),
         {"1": "SERVO_RUN_INH", "2": "GND", "3": "RUN_SERVO"},
         dict(P["QNTR"], Description="Holds RUN low unless SERVO_PWR_EN enables the rail (default OFF); " + P["QNTR"]["Description"])),
        ("R414", "Device:R", "100k", R0603, (40.64, 71.12, 0), {"1": "VBAT_PROT", "2": "SERVO_RUN_INH"},
         rc("RC0603FR-07100KL", "C14675", "Inhibit pull-up from VBAT_PROT: Q403 on (rail OFF) whenever SERVO_PWR_EN is not driven high; "
            "with R407 VGS = 0.6875 x VBAT: 6.32 V at 9.2 V, 14.8 V at 21.5 V TVS clamp")),
        ("R407", "Device:R", "220k", R0603, (60.96, 71.12, 0), {"1": "SERVO_RUN_INH", "2": "GND"},
         rc("RC0603FR-07220KL", "C123420", "Q403 gate divider bottom; limits VGS below 20 V at the TVS clamp")),
        ("Q404", NMOS_SMALL, "NTR4003N", "Package_TO_SOT_SMD:SOT-23", (109.22, 71.12, 0),
         {"1": "SERVO_PWR_EN", "2": "GND", "3": "SERVO_RUN_INH"},
         dict(P["QNTR"], Description="Servo enable: GPIO7 high (VOH >= 2.60 V) pulls the Q403 gate low; " + P["QNTR"]["Description"])),
        ("C420", "Device:C", "100n 50V", C0603, (66.04, 210.82, 0), {"1": "RUN_SERVO", "2": "GND"},
         dict(P["C100N"], Description="RUN delay: 17.5 kOhm x 100 nF = 1.75 ms, so the Q403 inhibit (gate tau about 6 us) wins the race at plug-in")),
        ("R415", "Device:R", "100k", R0603, (124.46, 76.2, 0), {"1": "SERVO_PWR_EN", "2": "GND"},
         rc("RC0603FR-07100KL", "C14675", "Q404 gate pull-down: GPIO7 Hi-Z (reset, boot, DevKit missing) -> rail OFF")),
        # ---- output shunt and current sense ----
        ("RS402", "Device:R", "2m", "ProjectFootprints:R_Vishay_WSL1020", (309.88, 119.38, 90),
         {"1": "VSERVO_REG", "2": "+V_SERVO"},
         {"Manufacturer": "Vishay", "MPN": "WSL10202L000FEA", "LCSC": "C1711510", "Datasheet": "https://www.vishay.com/doc?30183",
          "Description": "Output current shunt 2 mOhm 1 %, 2 W (O-18); outside the regulator feedback"}),
        ("NT404", "Device:NetTie_2", "Kelvin", NT, (304.8, 88.9, 0), {"1": "VSERVO_REG", "2": "ISERV_P"},
         {"Description": "Kelvin tap INA240 IN+ at RS402 pad 1"}),
        ("NT405", "Device:NetTie_2", "Kelvin", NT, (350.52, 88.9, 0), {"1": "+V_SERVO", "2": "ISERV_N"},
         {"Description": "Kelvin tap INA240 IN- at RS402 pad 2"}),
        ("U402", "Amplifier_Current:INA240A1D", "INA240A3D", "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm", (375.92, 60.96, 0),
         {"1": "ISERV_N", "2": "GND", "3": "GND", "4": "GND", "5": "ISENSE_RAW", "6": "+3V3", "7": "GND", "8": "ISERV_P"},
         {"Manufacturer": "Texas Instruments", "MPN": "INA240A3DR", "LCSC": "C2060584",
          "Datasheet": "https://www.ti.com/lit/ds/symlink/ina240.pdf",
          "_ref_at": (10.16, -6.35), "_val_at": (10.16, -3.81),
          "Description": "Gain 100 V/V, REF1/REF2 to GND (unidirectional); symbol INA240A1D has the same SOIC-8 pinout; no input filter (datasheet 9.1.1)"}),
        ("C416", "Device:C", "100n 50V", C0603, (360.68, 119.38, 0), {"1": "+3V3", "2": "GND"},
         dict(P["C100N"], Description="INA240 supply decoupling")),
        ("R412", "Device:R", "1k", R0603, (381.0, 119.38, 0), {"1": "ISENSE_RAW", "2": "ISERVO_FILT"},
         dict(P["R1K"], Description="ADC RC filter with C415, about 160 Hz")),
        ("C415", "Device:C", "1u", C0603, (401.32, 119.38, 0), {"1": "ISERVO_FILT", "2": "GND"},
         dict(P["C1U"], Description="ADC RC filter capacitor")),
        ("R416", "Device:R", "10k", R0603, (391.16, 190.5, 0), {"1": "ISERVO_FILT", "2": "ISERVO_SENSE"},
         rc("RC0603FR-0710KL", "C98220", "O-21: limits current from C415 into an unpowered GPIO1 (<= 0.22 mA, tau 10 ms)")),
        # ---- servo rail voltage sense ----
        ("R410", "Device:R", "100k", R0603, (345.44, 190.5, 0), {"1": "+V_SERVO", "2": "VSERVO_DIV"},
         rc("RC0603FR-07100KL", "C14675", "VSERVO divider: 6.91 V -> 2.21 V, 7.81 V -> 2.50 V (ADC ATTEN3 0-2.9 V)")),
        ("R411", "Device:R", "47k", R0603, (345.44, 238.76, 0), {"1": "VSERVO_DIV", "2": "GND"},
         dict(P["R47K"], Description="VSERVO divider bottom; node clamped by Q405 while +3V3 is absent (O-21)")),
        ("C417", "Device:C", "100n 50V", C0603, (360.68, 238.76, 0), {"1": "VSERVO_DIV", "2": "GND"},
         dict(P["C100N"], Description="VSERVO_SENSE filter")),
        ("R417", "Device:R", "10k", R0603, (383.54, 220.98, 0), {"1": "VSERVO_DIV", "2": "VSERVO_SENSE"},
         rc("RC0603FR-0710KL", "C98220", "O-21: series resistor to GPIO5")),
        ("Q405", NMOS_SMALL, "NTR4003N", "Package_TO_SOT_SMD:SOT-23", (320.04, 208.28, 0),
         {"1": "VSERVO_SH_G", "2": "GND", "3": "VSERVO_DIV"},
         dict(P["QNTR"], Description="O-21 shunt: clamps VSERVO_DIV to GND while +3V3 is absent; " + P["QNTR"]["Description"])),
        ("R418", "Device:R", "100k", R0603, (259.08, 208.28, 0), {"1": "+V_SERVO", "2": "VSERVO_SH_G"},
         rc("RC0603FR-07100KL", "C14675", "Shunt gate pull-up from the rail: VGS = 0.6875 x V_SERVO (>= 2.5 V above 3.64 V)")),
        ("R419", "Device:R", "220k", R0603, (271.78, 208.28, 0), {"1": "VSERVO_SH_G", "2": "GND"},
         rc("RC0603FR-07220KL", "C123420", "Shunt gate divider bottom")),
        ("Q406", NMOS_SMALL, "NTR4003N", "Package_TO_SOT_SMD:SOT-23", (276.86, 236.22, 0),
         {"1": "MEAS_EN_SP", "2": "GND", "3": "VSERVO_SH_G"},
         dict(P["QNTR"], Description="O-21: +3V3 present -> shunt Q405 off; " + P["QNTR"]["Description"])),
        ("R420", "Device:R", "10k", R0603, (304.8, 236.22, 0), {"1": "+3V3", "2": "MEAS_EN_SP"},
         rc("RC0603FR-0710KL", "C98220", "Q406 gate from +3V3: VGS = 3.251 V x 100/110 = 2.96 V")),
        ("R421", "Device:R", "100k", R0603, (325.12, 236.22, 0), {"1": "MEAS_EN_SP", "2": "GND"},
         rc("RC0603FR-07100KL", "C14675", "Q406 gate pull-down: +3V3 absent or floating (no DevKit) -> shunt on")),
        # ---- test points ----
        ("TP401", "Connector:TestPoint", "+V_SERVO", "TestPoint:TestPoint_Pad_D1.5mm", (330.2, 147.32, 0),
         {"1": "+V_SERVO"}, {"Description": "Test point servo rail; bare copper pad, excluded from BOM"}),
        ("TP402", "Connector:TestPoint", "GND", "TestPoint:TestPoint_Pad_D1.5mm", (345.44, 147.32, 0),
         {"1": "GND"}, {"Description": "Test point GND; bare copper pad, excluded from BOM"}),
        ("TP403", "Connector:TestPoint", "ISERVO", "TestPoint:TestPoint_Pad_D1.5mm", (401.32, 147.32, 0),
         {"1": "ISERVO_SENSE"}, {"Description": "Test point current-sense output; bare copper pad, excluded from BOM"}),
    ]


def build(root_uuid, sheet_uuid):
    s = Sheet(NS, root_uuid, sheet_uuid, "RoverCore VCU – ServoPower: servo rail (LTC7803) and current sense",
              "DRAFT – candidates per docs/vcu/rev1-versorgung-und-boardwahl.md 3.4-3.6, not released")
    s.paper = "A3"
    plist = parts()
    for ref, lib, value, fp, xyr, pins, fields in plist:
        s.part(ref, lib, value, fp, xyr, pins, fields, POWER_NETS, dict(HIER, **{k: "global:" + v for k, v in GLOBAL.items()}),
               in_bom=not ref.startswith(("TP", "NT")))
    for n, (ref, number, net) in enumerate((("C406", "1", "VSERVO_REG"),), 1):  # +3V3 flag sits on Controller (source)
        p = next(x for x in plist if x[0] == ref)
        x, y, rot = p[4]
        lx, ly, la = s.pin_points(p[1])[number]
        px, py = s.place(x, y, rot, lx, ly)
        dx, dy = s.outward(rot, la)
        s._symbol("power:PWR_FLAG", "#FLG4%02d" % n, "PWR_FLAG", "", round(px + dx * schgen.STUB, 4),
                  round(py + dy * schgen.STUB, 4), 0, {"1": net}, {})
    s.note("Servo rail 6.8 V (candidate, O-19) from VBAT_PROT, 3S. LTC7803 at 375 kHz, forced continuous, 100 % duty; "
           "RSENSE 3 mOhm, L 3.3 uH candidate. Feedback tapped at the output capacitors before RS402.", 25.4, 30.48, "h1")
    s.note("Kelvin: NT401/NT402 (LTC7803 SENSE at RS401), NT404/NT405 (INA240 at RS402), NT403 (feedback tap). "
           "Route each pair as separate close traces from the shunt pads. Compensation and RF/CF are start values.",
           25.4, 35.56, "h2")
    s.note("Default OFF: R414/R407 hold Q403 on (RUN low) from VBAT_PROT; only SERVO_PWR_EN high (Q404) releases RUN. "
           "Regulator shutdown, not a power disconnect. VSERVO_SENSE, ISERVO_SENSE, +V_SERVO are global labels.", 25.4, 40.64, "h3")
    return s.render()


def main():
    require_closed_kicad()
    if (ROOT / FILE).exists():
        raise SystemExit("%s exists; edit it in KiCad instead of re-running the bootstrap." % FILE)
    root = ROOT_SCH.read_text()
    root_uuid = re.search(r'\(uuid "?([0-9a-f-]{36})"?\)', root).group(1)
    if FILE in root:
        raise SystemExit("Root already references %s" % FILE)
    m = re.search(r'\t\(sheet\n.*?\(property "Sheetfile" "Power\.kicad_sch".*?\n\t\)\n', root, re.S)
    at = re.search(r'\(at ([\d.]+) ([\d.]+)\)\n\t\t\(size ([\d.]+) ([\d.]+)\)', m.group(0))
    px, py, pw, ph = (float(v) for v in at.groups())
    pin_x, pin_y = round(px + pw, 4), round(py + 7.62, 4)
    sheet_uuid = str(uuid.uuid5(uuid.UUID(NS), "sheet-servopower"))
    sx, sy = round(px + pw + 25.4, 4), round(py + ph + 20.32, 4)
    block = sheet_block(root_uuid, sheet_uuid, "ServoPower", FILE, sx, sy, pw, ph, "4",
                        [("VBAT_PROT", "input", "left", 7.62)])
    bend_x = round(pin_x + 12.7, 4)
    wires = ""
    for i, (a, b) in enumerate((((bend_x, pin_y), (bend_x, round(sy + 7.62, 4))),
                                ((bend_x, round(sy + 7.62, 4)), (sx, round(sy + 7.62, 4))))):
        wires += ("\t(wire\n\t\t(pts\n\t\t\t(xy %s %s) (xy %s %s)\n\t\t)\n\t\t(stroke\n\t\t\t(width 0)\n\t\t\t(type default)\n"
                  "\t\t)\n\t\t(uuid \"%s\")\n\t)\n" % (a[0], a[1], b[0], b[1], uuid.uuid5(uuid.UUID(NS), "root-wire-%d" % i)))
    wires += ("\t(junction\n\t\t(at %s %s)\n\t\t(diameter 0)\n\t\t(color 0 0 0 0)\n\t\t(uuid \"%s\")\n\t)\n"
              % (bend_x, pin_y, uuid.uuid5(uuid.UUID(NS), "root-junction")))
    (ROOT / FILE).write_text(build(root_uuid, sheet_uuid))
    anchor = "\t(sheet_instances\n"
    ROOT_SCH.write_text(root.replace(anchor, block + wires + anchor, 1))
    print("Wrote %s and added sheet 'ServoPower' to %s" % (FILE, ROOT_SCH.name))


if __name__ == "__main__":
    main()
