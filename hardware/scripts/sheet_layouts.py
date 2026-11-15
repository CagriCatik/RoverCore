"""Layout specs for relayout_sheet.py (positions only - no electrical content).

parts: ref -> (x, y, rotation[, field overrides such as _ref_at/_val_at/_stub])
wire: local nets drawn as direct wires (one net label stays at the anchor pin)
groups: key -> (title, (x1, y1, x2, y2), comment)
flags: nets that carry a PWR_FLAG; flag_at: net -> (ref, pin) where the flag sits
hier_local: hierarchical nets that keep a local label (net name unchanged) -> pin for the hierarchical label
"""

R = {"_ref_at": (2.54, -1.27), "_val_at": (2.54, 1.27)}      # field text right of a vertical two-pin part
TPF = {"_ref_at": (2.54, -2.54), "_val_at": (2.54, 0.0)}

LAYOUTS = {}

LAYOUTS["Power"] = {
    "parts": {
        "J101": (45.72, 91.44, 90, {"_ref_at": (15.24, -6.35), "_val_at": (15.24, -3.81)}),
        "TP101": (76.2, 83.82, 0, TPF),
        "F101": (96.52, 101.6, 90),
        "Q101": (132.08, 104.14, 90, {"_ref_at": (-5.08, -11.43), "_val_at": (-5.08, -8.89)}),
        "R101": (132.08, 134.62, 0, R),
        "D102": (147.32, 116.84, 270, {"_ref_at": (12.7, -1.27), "_val_at": (12.7, 1.27)}),
        "TP102": (180.34, 83.82, 0, TPF),
        "D101": (185.42, 116.84, 270, {"_ref_at": (12.7, -1.27), "_val_at": (12.7, 1.27)}),
        "C101": (205.74, 116.84, 0, R),
        "C102": (226.06, 116.84, 0, R),
        "TP103": (256.54, 129.54, 0, TPF),
    },
    "wire": ["VBAT_IN", "VBAT_FUSED", "Q101_GATE", "VBAT_PROT"],
    "anchor": {"VBAT_IN": ("TP101", "1"), "VBAT_PROT": ("TP102", "1"), "Q101_GATE": ("R101", "1"),
               "VBAT_FUSED": ("F101", "2")},
    "hier_local": {"VBAT_PROT": ("C102", "1")},
    "flags": ["VBAT_IN", "GND"], "flag_at": {"VBAT_IN": ("TP101", "1"), "GND": ("TP103", "1")}, "flag_prefix": "1",
    "groups": {
        "in": ("1  Battery input and fuse", (22.86, 66.04, 116.84, 152.4),
               "XT30 J101: pin 1 = minus, pin 2 = plus (KiCad silkscreen;\\ncheck against the battery lead, O-15).\\n"
               "Fuse 15 A mini blade, candidate (O-17)."),
        "rp": ("2  Reverse-polarity protection", (116.84, 66.04, 172.72, 152.4),
               "Q101 conducts with correct polarity\\n(VGS = -VBAT). D102 limits |VGS| during\\nTVS clamping; R101 pulls the gate."),
        "out": ("3  TVS, bulk -> VBAT_PROT", (172.72, 66.04, 269.24, 152.4),
                "SMBJ13A clamp, 330 uF + 10 uF bulk.\\nVBAT_PROT feeds LogicPower, ServoPower\\nand Controller (hierarchical pin)."),
    },
    "notes": {"head": ("Battery input 3S (9.0-12.6 V): XT30 -> fuse -> reverse-polarity P-FET -> TVS -> bulk. "
                       "All parts are candidates (O-17).", 22.86, 58.42),
              "main": ("Hauptschalter trennt die LiPo-Versorgung. USB kann den Controller weiterhin versorgen.\\n"
                       "Main disconnect outside the VCU, independent of firmware: LiPo -> main switch -> Y splitter -> "
                       "ESC and VCU (J101).\\nMotor current does not flow through the VCU. Switch selection open (O-34).",
                       22.86, 165.1)},
}

LAYOUTS["LogicPower"] = {
    "parts": {
        "C301": (35.56, 102.87, 0, R),
        "C302": (50.8, 102.87, 0, R),
        "R304": (71.12, 102.87, 0, R),
        "R305": (71.12, 129.54, 0, R),
        "U301": (114.3, 96.52, 0, {"_ref_at": (-7.62, -8.89), "_val_at": (1.27, -8.89)}),
        "C303": (142.24, 83.82, 0, R),
        "L301": (160.02, 96.52, 90),
        "C304": (182.88, 105.41, 0, R),
        "C305": (198.12, 105.41, 0, R),
        "C307": (213.36, 105.41, 0, R),
        "TP301": (236.22, 83.82, 0, TPF),
        "R301": (236.22, 105.41, 0, R),
        "R302": (236.22, 127.0, 0, R),
        "C306": (251.46, 127.0, 0, R),
        "R303": (236.22, 147.32, 0, R),
        "TP302": (261.62, 144.78, 0, TPF),
    },
    "wire": ["VBAT_PROT", "EN_5V", "BOOT_5V", "SW_5V", "+5V", "VSENSE_5V", "FB_5V"],
    "anchor": {"VBAT_PROT": ("C301", "1"), "EN_5V": ("R305", "1"), "BOOT_5V": ("C303", "1"), "SW_5V": ("L301", "1"),
               "+5V": ("C304", "1"), "VSENSE_5V": ("R302", "1"), "FB_5V": ("R303", "1")},
    "label_at": {"VSENSE_5V": (238.76, 118.11, (1, 0)), "FB_5V": (205.74, 135.89, (1, 0))},
    "flags": ["VBAT_PROT", "+5V"], "flag_at": {"VBAT_PROT": ("C302", "1"), "+5V": ("C307", "1")}, "flag_prefix": "3",
    "groups": {
        "in": ("1  Input and enable", (22.86, 66.04, 93.98, 162.56),
               "VBAT_PROT from Power. EN divider 69.8k/11.5k:\\non 8.65 V, off 8.04 V (logic stays on below\\nthe servo-rail cut-off 8.8 V)."),
        "buck": ("2  Buck TPS54302", (93.98, 66.04, 172.72, 162.56),
                 "L 10 uH, boot capacitor C303.\\nKeep the SW node small (layout)."),
        "out": ("3  Output and feedback", (172.72, 66.04, 274.32, 162.56),
                "Cout 3 x 22 uF (C307 for DC-bias margin). FB 100k/13.7k:\\n4.95 V nom., 4.74-5.16 V (1 %). R301 49.9 Ohm:\\nloop measurement injection point."),
    },
    "notes": {"head": ("5 V logic rail from VBAT_PROT (3S, 9.0-12.6 V). Upper limit 5.5 V (SK6812MINI-E, LVC8T245). "
                       "All parts are candidates (O-17).", 22.86, 58.42)},
}

LAYOUTS["Controller"] = {
    "parts": {
        # 1 - 5 V feed and 3.3 V
        "D501": (55.88, 78.74, 180, {"_ref_at": (2.54, -3.81), "_val_at": (10.16, 3.81)}),
        "TP503": (81.28, 68.58, 0, TPF),
        "C501": (40.64, 109.22, 0, R),
        "C502": (58.42, 109.22, 0, R),
        "TP502": (76.2, 109.22, 180, {"_ref_at": (8.89, 1.27), "_val_at": (8.89, 3.81)}),
        "TP504": (93.98, 104.14, 0, TPF),
        # 2 - operator
        "R501": (35.56, 157.48, 0, R),
        "R502": (60.96, 157.48, 0, R),
        "SW501": (78.74, 177.8, 0),
        "R504": (35.56, 205.74, 0, R),
        "D502": (35.56, 228.6, 90, {"_ref_at": (12.7, -1.27), "_val_at": (12.7, 1.27)}),
        "TP501": (78.74, 210.82, 0, TPF),
        # 3 - DevKit socket
        "U501": (180.34, 162.56, 0, {"_ref_at": (-15.24, -38.1), "_val_at": (-15.24, -35.56),
                                     "Description": "Socket = 2 x 1x22 female header 2.54 mm (part open, height O-4); "
                                                    "pads 1-22 J1, 23-44 J3; EN (J1-3) -> RESET SW502, GPIO0 (J3-14) "
                                                    "-> BOOT SW503; other strapping pins, USB, UART0, GPIO35-38 not "
                                                    "connected (pinmap.csv)",
                                     "_stub": {"4": 33.02, "11": 33.02, "16": 33.02, "17": 33.02, "21": 33.02}}),
        # 4 - VBAT measurement
        "Q505": (261.62, 93.98, 180, {"_ref_at": (-10.16, -1.27), "_val_at": (-10.16, 1.27)}),
        "R508": (289.56, 78.74, 0, R),
        "R509": (289.56, 96.52, 0, R),
        "Q506": (287.02, 130.81, 0, {"_ref_at": (5.08, -1.27), "_val_at": (5.08, 1.27)}),
        "R505": (259.08, 137.16, 0, R),
        "R506": (259.08, 165.1, 0, R),
        "C504": (241.3, 165.1, 0, R),
        "D506": (309.88, 137.16, 90, {"_ref_at": (12.7, -1.27), "_val_at": (12.7, 1.27)}),
        "R507": (330.2, 146.05, 90),
        "TP505": (350.52, 135.89, 0, TPF),
        # 5 - supervisor
        "U504": (259.08, 215.9, 0, {"_ref_at": (-7.62, -10.16), "_val_at": (2.54, -10.16)}),
        "C505": (241.3, 215.9, 0, R),
        "R510": (297.18, 228.6, 0, R),
        # 6 - programming and restart (added after d53365c)
        "SW502": (345.44, 215.9, 0),
        "SW503": (345.44, 236.22, 0),
    },
    # parts added after the layout review (electrical change; see docs/vcu/rev1-pin-und-anschlussplan.md 9)
    "new": {
        "SW502": ("Switch:SW_Push", "RESET", "Button_Switch_SMD:SW_SPST_TL3342", {"1": "DEVKIT_EN", "2": "GND"},
                  {"Manufacturer": "E-Switch", "MPN": "TL3342F160QG", "LCSC": "C2886898",
                   "Description": "RESET: shorts DevKit EN (CHIP_PU) to GND like DevKit SW2; DevKit keeps R5 10k pull-up "
                                  "and C6 1 uF (schematic V1.1 20221130 sheet 2); no carrier RC. Not a power switch. "
                                  "Candidate, JLC stock 0 on 2026-11-15 (O-28)"}),
        "SW503": ("Switch:SW_Push", "BOOT", "Button_Switch_SMD:SW_SPST_TL3342", {"1": "STRAP_GPIO0", "2": "GND"},
                  {"Manufacturer": "E-Switch", "MPN": "TL3342F160QG", "LCSC": "C2886898",
                   "Description": "BOOT: GPIO0 to GND like DevKit SW1; released = strapping 1 (SPI boot) via the "
                                  "ESP32-S3 internal pull-up, no carrier pull-up/-down. Download: hold BOOT, press "
                                  "RESET, release BOOT. Candidate (O-28)"}),
    },
    "wire": ["+5V_DEVKIT", "LED_STAT_A", "ENABLE_BTN_N", "VBAT_PROT", "VBAT_SW", "VBAT_SW_G", "VBAT_SW_DRV",
             "VBAT_DIV", "VBAT_SENSE", "P3V3_OK"],
    "anchor": {"+5V_DEVKIT": ("D501", "1"), "LED_STAT_A": ("R504", "2"), "ENABLE_BTN_N": ("R502", "2"),
               "VBAT_PROT": ("Q505", "2"), "VBAT_SW": ("R505", "1"), "VBAT_SW_G": ("Q505", "1"),
               "VBAT_SW_DRV": ("R509", "2"), "VBAT_DIV": ("R506", "1"), "VBAT_SENSE": ("R507", "2"),
               "P3V3_OK": ("U504", "2")},
    "label_only": [("U501", "21"), ("U501", "16"), ("U501", "4"), ("Q506", "1")],
    "pins": {"U501": {"2": "=1", "3": "DEVKIT_EN", "36": "STRAP_GPIO0"}},
    "label_at": {"VBAT_PROT": (264.16, 69.85, (1, 0)), "VBAT_DIV": (281.94, 146.05, (1, 0))},
    "flags": ["+3V3"], "flag_at": {"+3V3": ("C501", "1")}, "flag_prefix": "5",
    "groups": {
        "pwr": ("1  5 V feed and 3.3 V", (22.86, 55.88, 106.68, 127.0),
                "Carrier +5V -> D501 -> DevKit 5V pin (diode-OR with the\\nDevKit USB diodes, own extension, Versorgung 3.11).\\n+3V3 = DevKit LDO only."),
        "op": ("2  Operator and defaults", (22.86, 132.08, 106.68, 248.92),
               "R501: ACT_OE_N high at reset (buffers Hi-Z).\\nSW501 enable button, no RC at the pin (O-21,\\nfirmware debounce). D502 status LED. TP501 = GPIO18."),
        "sock": ("3  DevKit socket U501", (111.76, 55.88, 231.14, 248.92),
                 "Original ESP32-S3-DevKitC-1-N16R8 v1.1; pads 1-22 = J1,\\n23-44 = J3. Reserved pins: no-connect (pinmap.csv).\\nSignals leave as global labels to the other sheets."),
        "vbat": ("4  VBAT measurement (O-21)", (236.22, 55.88, 370.84, 182.88),
                 "Q505 closes the divider only while P3V3_OK is high; C504 1 nF,\\nD506 holds VBAT_DIV <= +3V3 + 0.24 V. 12.6 V -> 1.80 V."),
        "sup": ("5  3.3 V supervisor -> P3V3_OK", (236.22, 187.96, 309.88, 248.92),
                "TLV809E 2.93 V: P3V3_OK high only while +3V3 is good\\n(33-67 ms delay). Drives Q506 here, Q406 (ServoPower)\\nand U602 EN (Lighting_IO)."),
        "prog": ("6  Programmierung und Neustart", (314.96, 187.96, 370.84, 248.92),
                 "RESET SW502: EN -> GND (DevKit R5 10k, C6 1 uF).\\nBOOT SW503: GPIO0 -> GND, internal pull-up\\n"
                 "= SPI boot. Download: hold BOOT, press\\nRESET, release BOOT. RESET is no power switch."),
    },
    "notes": {"head": ("Controller: DevKit socket, 5 V feed, 3.3 V, defaults and protected measurement inputs "
                       "(Versorgung 3.11-3.13).", 22.86, 48.26)},
}

LAYOUTS["ServoPower"] = {
    "parts": {
        # 1 input capacitors
        "C401": (33.02, 88.9, 0, R), "C402": (48.26, 88.9, 0, R), "C403": (63.5, 88.9, 0, R),
        "C404": (78.74, 88.9, 0, R), "C405": (93.98, 88.9, 0, R),
        # 2 RUN / default off
        "R414": (33.02, 144.78, 0, R), "R407": (33.02, 172.72, 0, R),
        "Q403": (63.5, 160.02, 0, {"_ref_at": (5.08, -1.27), "_val_at": (5.08, 1.27)}),
        "Q404": (40.64, 200.66, 0, {"_ref_at": (5.08, -1.27), "_val_at": (5.08, 1.27)}),
        "R415": (30.48, 223.52, 0, R),
        "R405": (93.98, 144.78, 0, R), "R406": (93.98, 172.72, 0, R), "C420": (106.68, 172.72, 0, R),
        # 3 controller
        "U401": (165.1, 144.78, 0, {"_ref_at": (-12.7, -19.05), "_val_at": (2.54, -19.05)}),
        "C414": (129.54, 187.96, 0, R),
        "C419": (147.32, 200.66, 0, R), "R413": (165.1, 200.66, 0, R), "C418": (165.1, 226.06, 0, R),
        "C412": (200.66, 187.96, 0, R), "C413": (215.9, 187.96, 0, R),
        "D401": (213.36, 76.2, 0, {"_ref_at": (-2.54, -3.81), "_val_at": (-2.54, 3.81)}),
        "C411": (198.12, 93.98, 0, R),
        # 4 power stage
        "Q401": (254.0, 88.9, 0, {"_ref_at": (5.08, -2.54), "_val_at": (5.08, 0.0)}),
        "Q402": (254.0, 119.38, 0, {"_ref_at": (5.08, -2.54), "_val_at": (5.08, 0.0)}),
        "L401": (276.86, 104.14, 90),
        "RS401": (299.72, 104.14, 90),
        "NT401": (287.02, 121.92, 0), "NT402": (312.42, 121.92, 0),
        "RF401": (294.64, 139.7, 0, R), "CF401": (320.04, 139.7, 180, {"_ref_at": (-2.54, 1.27), "_val_at": (-2.54, -1.27)}),
        # 5 output, shunt, feedback
        "C406": (336.55, 88.9, 0, R), "C407": (351.79, 88.9, 0, R), "C408": (368.3, 88.9, 0, R),
        "C409": (382.27, 88.9, 0, R), "C410": (396.24, 88.9, 0, R),
        "RS402": (340.36, 128.27, 0, R),
        "NT404": (355.6, 116.84, 0), "NT405": (355.6, 139.7, 0),
        "TP401": (370.84, 147.32, 0, TPF), "TP402": (398.78, 147.32, 0, TPF),
        "NT403": (372.11, 106.68, 0), "R403": (386.08, 115.57, 0, R), "R404": (386.08, 138.43, 0, R),
        # 6 measurement
        "C416": (246.38, 190.5, 0, R),
        "U402": (261.62, 210.82, 0, {"_ref_at": (5.08, -11.43), "_val_at": (5.08, -8.89)}),
        "R412": (289.56, 210.82, 90), "C415": (294.64, 233.68, 0, R),
        "D404": (294.64, 193.04, 90, {"_ref_at": (12.7, -1.27), "_val_at": (12.7, 1.27)}),
        "R416": (309.88, 210.82, 90), "TP403": (320.04, 198.12, 0, TPF),
        "Q405": (363.22, 190.5, 180, {"_ref_at": (-7.62, -6.35), "_val_at": (-7.62, -3.81)}),
        "R418": (393.7, 182.88, 0, R), "R419": (393.7, 205.74, 0, R),
        "Q406": (391.16, 233.68, 0, {"_ref_at": (-12.7, 6.35), "_val_at": (-12.7, 8.89)}),
        "R410": (360.68, 218.44, 0, R), "R411": (360.68, 236.22, 0, R), "C417": (342.9, 236.22, 0, R),
        "D403": (339.09, 213.36, 90, {"_ref_at": (-7.62, -8.89), "_val_at": (-7.62, -6.35)}),
        "R417": (322.58, 241.3, 270),
    },
    "pins": {"U401": {"8": "=7"}, "U402": {"3": "=2", "7": "=2"}},
    "wire": ["VBAT_PROT", "SERVO_RUN_INH", "SERVO_PWR_EN", "RUN_SERVO", "ITH_SERVO", "ITH_RC", "INTVCC_SERVO",
             "BOOST_SERVO", "SW_SERVO", "ISNS_PWR", "SENSE_P_K", "SENSE_P", "SENSE_N", "VSERVO_REG", "+V_SERVO",
             "VFB_TAP", "VFB_SERVO", "ISENSE_RAW", "ISERVO_FILT", "ISERVO_SENSE", "VSERVO_SW", "VSERVO_SW_G",
             "VSERVO_SW_DRV", "VSERVO_DIV"],
    "anchor": {"VBAT_PROT": ("C401", "1"), "SERVO_RUN_INH": ("R407", "1"), "SERVO_PWR_EN": ("Q404", "1"),
               "RUN_SERVO": ("R406", "1"), "ITH_SERVO": ("R413", "1"), "ITH_RC": ("C418", "1"),
               "INTVCC_SERVO": ("C412", "1"), "BOOST_SERVO": ("C411", "1"), "SW_SERVO": ("L401", "1"),
               "ISNS_PWR": ("RS401", "1"), "SENSE_P_K": ("RF401", "1"), "SENSE_P": ("RF401", "2"),
               "SENSE_N": ("CF401", "2"), "VSERVO_REG": ("C406", "1"), "+V_SERVO": ("TP401", "1"),
               "VFB_TAP": ("NT403", "2"), "VFB_SERVO": ("R404", "1"), "ISENSE_RAW": ("U402", "5"),
               "ISERVO_FILT": ("C415", "1"), "ISERVO_SENSE": ("R416", "2"), "VSERVO_SW": ("R410", "1"),
               "VSERVO_SW_G": ("R418", "2"), "VSERVO_SW_DRV": ("R419", "2"), "VSERVO_DIV": ("R411", "1")},
    "label_only": [("U401", n) for n in ("12", "6", "11", "1", "9", "5", "14", "15", "16", "13", "10", "2", "3", "4")]
                  + [("R414", "1"), ("R405", "1"), ("Q401", "5"), ("D401", "2"), ("Q405", "2"), ("R418", "1"),
                     ("U402", "8"), ("U402", "1"), ("NT404", "2"), ("NT405", "2"), ("Q406", "1")],
    # net names on free wire segments instead of the short stubs between the divider resistors
    "label_at": {"VSERVO_DIV": (344.17, 227.33, (1, 0)), "VSERVO_SW_G": (375.92, 190.5, (1, 0)),
                 "VSERVO_SW_DRV": (393.7, 210.82, (0, 1))},
    "flags": ["VSERVO_REG"], "flag_at": {"VSERVO_REG": ("C410", "1")}, "flag_prefix": "4",
    "groups": {
        "in": ("1  Input capacitors", (22.86, 55.88, 114.3, 106.68),
               "4 x 10 uF/50 V + 100 nF at the power stage\\n(input ripple up to 5.6 A at 12.6 V)."),
        "run": ("2  RUN and default OFF", (22.86, 111.76, 114.3, 248.92),
                "Default OFF: Q403 holds RUN low; only SERVO_PWR_EN high (Q404)\\nreleases it. RUN 9.6 V on / 8.8 V off, C420 delay 1.75 ms."),
        "ctl": ("3  LTC7803 controller", (119.38, 55.88, 233.68, 248.92),
                "375 kHz, forced continuous, 100 % duty, EXTVCC from the output.\\nCompensation R413/C418/C419 and soft-start C414 are start values.\\nBoost D401/C411 (CB >= 100 x Ciss)."),
        "pwr": ("4  Power stage and RSENSE", (238.76, 55.88, 332.74, 160.02),
                "BSC026N04LS x 2, L 3.3 uH candidate, RS401 3 mOhm.\\nNT401/NT402: Kelvin taps; RF401/CF401 sense filter."),
        "out": ("5  Output, RS402 and feedback", (332.74, 55.88, 407.67, 160.02),
                "Feedback tap NT403 before RS402; RS402 2 mOhm with\\nKelvin taps NT404/NT405 for the INA240. 6.80 V nom."),
        "meas": ("6  Measurement outputs (O-18, O-21)", (238.76, 165.1, 407.67, 248.92),
                 "INA240A3: 0.2 V/A -> ISERVO_SENSE; VSERVO divider switched by Q405 (on only with P3V3_OK).\\n"
                 "BAT54 D403/D404 hold the ADC nodes <= +3V3 + 0.24 V; small filter caps (O-21)."),
    },
    "notes": {"head": ("Servo rail 6.8 V (candidate, O-19) from VBAT_PROT, 3S; LTC7803 synchronous buck with output "
                       "current sense. Kelvin routing happens in the PCB.", 22.86, 48.26)},
}

LAYOUTS["Actuators"] = {
    "parts": {
        "U201": (203.2, 106.68, 0, {'_ref_at': (12.7, -27.94), '_val_at': (12.7, -25.4)}),
        "C201": (170.18, 76.2, 0, R),
        "C202": (236.22, 76.2, 0, R),
        "R209": (172.72, 134.62, 90),
        "R201": (33.02, 101.6, 0, R),
        "R202": (48.26, 101.6, 0, R),
        "R203": (63.5, 101.6, 0, R),
        "R204": (78.74, 101.6, 0, R),
        "R205": (93.98, 101.6, 0, R),
        "R206": (109.22, 101.6, 0, R),
        "R207": (124.46, 101.6, 0, R),
        "R208": (139.7, 101.6, 0, R),
        "R211": (27.94, 180.34, 0, {"_ref_at": (-8.89, -1.27), "_val_at": (-8.89, 1.27)}),
        "R212": (104.14, 180.34, 0, {"_ref_at": (-8.89, -1.27), "_val_at": (-8.89, 1.27)}),
        "R213": (180.34, 180.34, 0, {"_ref_at": (-8.89, -1.27), "_val_at": (-8.89, 1.27)}),
        "R214": (256.54, 180.34, 0, {"_ref_at": (-8.89, -1.27), "_val_at": (-8.89, 1.27)}),
        "R215": (332.74, 180.34, 0, {"_ref_at": (-8.89, -1.27), "_val_at": (-8.89, 1.27)}),
        "R216": (259.08, 101.6, 0, R),
        "R217": (274.32, 101.6, 0, R),
        "R218": (289.56, 101.6, 0, R),
        "Q201": (38.1, 210.82, 0, {"_ref_at": (-12.7, 8.89), "_val_at": (-12.7, 11.43)}),
        "D201": (41.91, 172.72, 0, {'_ref_at': (-2.54, -3.81), '_val_at': (-2.54, 3.81)}),
        "R231": (50.8, 186.69, 0, R),
        "R241": (50.8, 231.14, 0, R),
        "R221": (63.5, 205.74, 90),
        "J106": (96.52, 208.28, 0, {"_ref_at": (-7.62, 7.62), "_val_at": (-7.62, 10.16)}),
        "Q202": (114.3, 210.82, 0, {"_ref_at": (-12.7, 8.89), "_val_at": (-12.7, 11.43)}),
        "D202": (118.11, 172.72, 0, {'_ref_at': (-2.54, -3.81), '_val_at': (-2.54, 3.81)}),
        "R232": (127.0, 186.69, 0, R),
        "R242": (127.0, 231.14, 0, R),
        "R222": (139.7, 205.74, 90),
        "J102": (172.72, 208.28, 0, {"_ref_at": (-7.62, 7.62), "_val_at": (-7.62, 10.16)}),
        "Q203": (190.5, 210.82, 0, {"_ref_at": (-12.7, 8.89), "_val_at": (-12.7, 11.43)}),
        "D203": (194.31, 172.72, 0, {'_ref_at': (-2.54, -3.81), '_val_at': (-2.54, 3.81)}),
        "R233": (203.2, 186.69, 0, R),
        "R243": (203.2, 231.14, 0, R),
        "R223": (215.9, 205.74, 90),
        "J103": (248.92, 208.28, 0, {"_ref_at": (-7.62, 7.62), "_val_at": (-7.62, 10.16)}),
        "Q204": (266.7, 210.82, 0, {"_ref_at": (-12.7, 8.89), "_val_at": (-12.7, 11.43)}),
        "D204": (270.51, 172.72, 0, {'_ref_at': (-2.54, -3.81), '_val_at': (-2.54, 3.81)}),
        "R234": (279.4, 186.69, 0, R),
        "R244": (279.4, 231.14, 0, R),
        "R224": (292.1, 205.74, 90),
        "J104": (325.12, 208.28, 0, {"_ref_at": (-7.62, 7.62), "_val_at": (-7.62, 10.16)}),
        "Q205": (342.9, 210.82, 0, {"_ref_at": (-12.7, 8.89), "_val_at": (-12.7, 11.43)}),
        "D205": (346.71, 172.72, 0, {'_ref_at': (-2.54, -3.81), '_val_at': (-2.54, 3.81)}),
        "R235": (355.6, 186.69, 0, R),
        "R245": (355.6, 231.14, 0, R),
        "R225": (368.3, 205.74, 90),
        "J105": (401.32, 208.28, 0, {"_ref_at": (-7.62, 7.62), "_val_at": (-7.62, 10.16)}),
    },
    "wire": ['U201_DIR', 'ESC_PWM_B', 'ESC_DRV', 'ESC_PU', 'ESC_OUT', 'SERVO_FRONT_B', 'SERVO_FRONT_DRV', 'SERVO_FRONT_PU', 'SERVO_FRONT_OUT', 'SERVO_REAR_B', 'SERVO_REAR_DRV', 'SERVO_REAR_PU', 'SERVO_REAR_OUT', 'SERVO_AUX1_B', 'SERVO_AUX1_DRV', 'SERVO_AUX1_PU', 'SERVO_AUX1_OUT', 'SERVO_AUX2_B', 'SERVO_AUX2_DRV', 'SERVO_AUX2_PU', 'SERVO_AUX2_OUT'],
    "anchor": {'U201_DIR': ('R209', '2'), 'ESC_PWM_B': ('R211', '2'), 'ESC_DRV': ('R241', '1'), 'ESC_PU': ('D201', '3'), 'ESC_OUT': ('R221', '2'), 'SERVO_FRONT_B': ('R212', '2'), 'SERVO_FRONT_DRV': ('R242', '1'), 'SERVO_FRONT_PU': ('D202', '3'), 'SERVO_FRONT_OUT': ('R222', '2'), 'SERVO_REAR_B': ('R213', '2'), 'SERVO_REAR_DRV': ('R243', '1'), 'SERVO_REAR_PU': ('D203', '3'), 'SERVO_REAR_OUT': ('R223', '2'), 'SERVO_AUX1_B': ('R214', '2'), 'SERVO_AUX1_DRV': ('R244', '1'), 'SERVO_AUX1_PU': ('D204', '3'), 'SERVO_AUX1_OUT': ('R224', '2'), 'SERVO_AUX2_B': ('R215', '2'), 'SERVO_AUX2_DRV': ('R245', '1'), 'SERVO_AUX2_PU': ('D205', '3'), 'SERVO_AUX2_OUT': ('R225', '2')},
    "label_only": [("U201", n) for n in ("21", "20", "19", "18", "17")],
    "groups": {
        "buf": ("1  Output buffer U201 and idle levels", (22.86, 55.88, 407.67, 139.7),
                "SN74LVC8T245: A = 3.3 V (GPIO), B = 5 V, DIR via R209 = A -> B, OE = ACT_OE_N (pull-up R501 on Controller).\\n"
                "R201-R205 pull-ups (servo/ESC stage inverts), R206-R208 pull-downs (LED data); R216-R218 LED pull-downs (to Lighting_IO)."),
        "out": ("2  Open-drain outputs ESC J106, servos J102-J105", (22.86, 144.78, 407.67, 248.92),
                "Q20x NTR4003N (30 V) with BAT54 + 2.2k pull-up from +5V: a foreign voltage on the signal pin reaches neither +5V nor U201 (VCU on or off).\\n"
                "INVERTED stage - firmware inverts the LEDC outputs. R21x gate pull-ups keep the lines low while U201 is Hi-Z. J106 pin 2 (ESC BEC +) not connected."),
    },
    "notes": {"head": ("Actuators: 3.3 V -> 5 V buffer and protected servo/ESC outputs (Pinplan 3.1, 4, 7).", 22.86, 48.26)},
}

LAYOUTS["Lighting_IO"] = {
    "parts": {
        "C601": (30.48, 101.6, 0, R),
        "U601": (71.12, 95.25, 0, {"_ref_at": (-7.62, -6.35), "_val_at": (1.27, -6.35)}),
        "R601": (93.98, 106.68, 0, R),
        "C602": (111.76, 101.6, 0, R),
        "C603": (160.02, 101.6, 0, R),
        "U602": (200.66, 95.25, 0, {"_ref_at": (-7.62, -6.35), "_val_at": (1.27, -6.35), "_stub": {"3": 12.7}}),
        "R602": (223.52, 106.68, 0, R),
        "C604": (241.3, 101.6, 0, R),
        "C605": (289.56, 101.6, 0, R),
        "U603": (330.2, 95.25, 0, {"_ref_at": (-7.62, -6.35), "_val_at": (1.27, -6.35)}),
        "R603": (353.06, 106.68, 0, R),
        "C606": (370.84, 101.6, 0, R),
        "U202": (91.44, 162.56, 0, {"_ref_at": (5.08, -13.97), "_val_at": (5.08, -11.43)}),
        "R605": (40.64, 177.8, 0, R),
        "R604": (50.8, 152.4, 0, R),
        "R606": (114.3, 177.8, 0, R),
        "C607": (27.94, 177.8, 0, R),
        "C608": (116.84, 147.32, 0, R),
        "R607": (132.08, 152.4, 0, R),
        "D601": (144.78, 172.72, 180, {'_ref_at': (5.08, 5.08), '_val_at': (5.08, 7.62)}),
        "J108": (170.18, 167.64, 0, {'_ref_at': (-2.54, 7.62), '_val_at': (-2.54, 10.16)}),
        "R608": (200.66, 152.4, 0, R),
        "D602": (213.36, 172.72, 180, {'_ref_at': (5.08, 5.08), '_val_at': (5.08, 7.62)}),
        "J109": (238.76, 167.64, 0, {'_ref_at': (-2.54, 7.62), '_val_at': (-2.54, 10.16)}),
        "R609": (269.24, 152.4, 0, R),
        "D603": (281.94, 172.72, 180, {'_ref_at': (5.08, 5.08), '_val_at': (5.08, 7.62)}),
        "J110": (307.34, 167.64, 0, {'_ref_at': (-2.54, 7.62), '_val_at': (-2.54, 10.16)}),
        "R610": (337.82, 152.4, 0, R),
        "D604": (350.52, 172.72, 180, {'_ref_at': (5.08, 5.08), '_val_at': (5.08, 7.62)}),
        "J111": (375.92, 167.64, 0, {'_ref_at': (-2.54, 7.62), '_val_at': (-2.54, 10.16)}),
        "TP602": (154.94, 147.32, 0, TPF),
        "BZ101": (68.58, 222.25, 0, {"_ref_at": (5.08, -1.27), "_val_at": (5.08, 1.27)}),
        "D605": (48.26, 222.25, 270, {"_ref_at": (-5.08, 2.54), "_val_at": (-5.08, 5.08)}),
        "Q601": (73.66, 245.11, 0, {"_ref_at": (5.08, -1.27), "_val_at": (5.08, 1.27)}),
        "R611": (53.34, 245.11, 90),
        "R612": (63.5, 254.0, 0, R),
        "U203": (157.48, 226.06, 0, {"_ref_at": (2.54, -12.7), "_val_at": (2.54, -10.16)}),
        "C610": (139.7, 240.03, 0, R),
        "TP601": (180.34, 210.82, 0, TPF),
        "R613": (210.82, 218.44, 270),
        "R614": (195.58, 228.6, 0, R),
        "D606": (224.79, 228.6, 180, {"_ref_at": (2.54, 5.08), "_val_at": (2.54, 7.62)}),
        "J107": (241.3, 220.98, 0, {'_ref_at': (2.54, -5.08), '_val_at': (2.54, 5.08)}),
        "R615": (299.72, 220.98, 90),
        "R616": (350.52, 241.3, 270),
        "R617": (316.23, 241.3, 90),
        "D607": (313.69, 231.14, 180, {"_ref_at": (-12.7, 3.81), "_val_at": (-12.7, 6.35)}),
        "D608": (370.84, 233.68, 180, {"_ref_at": (17.78, -1.27), "_val_at": (17.78, 1.27)}),
        "J112": (393.7, 220.98, 0, {"_ref_at": (2.54, -5.08), "_val_at": (2.54, 7.62)}),
    },
    "pins": {"U601": {"3": "=1"}, "U603": {"3": "=1"}},
    "wire": ["ILIM_U601", "ILIM_U602", "ILIM_U603", "+5V_LED", "+5V_EXT", "+5V_RX", "LED_1_DIN", "LED_2_DIN",
             "LED_3_DIN", "LED_4_DIN", "LED_4_5V", "BZ_DRV", "BZ_G", "IBUS_IN", "IBUS_A", "IBUS_RX_3V3",
             "EXT_TX_C", "EXT_RX_C", "EXT_UART_RX"],
    "anchor": {"ILIM_U601": ("R601", "1"), "ILIM_U602": ("R602", "1"), "ILIM_U603": ("R603", "1"),
               "+5V_LED": ("C602", "1"), "+5V_EXT": ("C604", "1"), "+5V_RX": ("C606", "1"),
               "LED_1_DIN": ("R607", "2"), "LED_2_DIN": ("R608", "2"), "LED_3_DIN": ("R609", "2"),
               "LED_4_DIN": ("R610", "2"), "LED_4_5V": ("U202", "4"), "BZ_DRV": ("D605", "2"), "BZ_G": ("R612", "1"),
               "IBUS_IN": ("J107", "1"), "IBUS_A": ("R614", "1"), "IBUS_RX_3V3": ("U203", "4"),
               "EXT_TX_C": ("R615", "2"), "EXT_RX_C": ("R616", "1"), "EXT_UART_RX": ("R616", "2")},
    "label_only": [("U202", "3"), ("U202", "5"), ("J108", "1"), ("J109", "1"), ("J110", "1"), ("J111", "1"), ("J112", "1"), ("J107", "2"), ("U203", "2")],
    "groups": {
        "sw": ("1  Current-limited 5 V outputs (TPS2553)", (22.86, 55.88, 407.67, 120.65),
               "A cable short trips only its group; +5V for DevKit and buffers stays up. Limits (SLVS841G eq. 1/3): U601 LEDs 0.25-0.32 A, "
               "U602 J112 0.23-0.30 A\\n(EN = P3V3_OK: external device powered only while +3V3 is good, O-21), U603 receiver 0.155-0.21 A. FAULT unused."),
        "led": ("2  LED outputs J108-J111 (SK6812MINI-E)", (22.86, 125.73, 407.67, 193.04),
                "LED_1..3_5V from U201 (Actuators), LED_4 via U202 SN74LVC1T45. 330 Ohm series (short to GND <= 16 mA), TPD1E05U06 ESD at the pin."),
        "bz": ("3  Buzzer", (22.86, 198.12, 116.84, 264.16),
               "CMT-8540S, LEDC 4 kHz / 50 % only.\\nQ601 NTR4501N, D605 freewheel (stuck-on\\n0.52 A), R612 gate pull-down."),
        "ibus": ("4  i-BUS input J107", (121.92, 198.12, 251.46, 264.16),
                 "2.2k series + 100k pull-down + ESD, SN74LVC1G17\\nat +3V3 (5.5 V tolerant, Ioff). Receiver pin order O-10."),
        "uart": ("5  Extension UART J112", (256.54, 198.12, 407.67, 248.92),
                 "TX 1k series; RX 4.7k series, 10k pull-up to +3V3, ESD to GND,\\nno clamp diode to +3V3 (O-21). +5V_EXT max. 0.2 A via U602."),
    },
    "notes": {"head": ("Lighting_IO: external 5 V outputs, LED data, buzzer, i-BUS input and extension UART (Pinplan 3, 4, 8).", 22.86, 48.26)},
}


LAYOUTS["Sensors_Display"] = {
    # J115 rotated 180 (pins right) faces J116 (pins left): SDA and SCL run as two straight wires, no crossing
    "parts": {
        "J115": (50.8, 101.6, 180, {"_ref_at": (5.08, -15.24), "_val_at": (5.08, 15.24), "_stub": {"1": 10.16}}),
        "J116": (246.38, 111.76, 0, {"_ref_at": (-5.08, -15.24), "_val_at": (-5.08, 15.24)}),
        "R803": (76.2, 93.98, 90),
        "R801": (127.0, 92.71, 0, R),
        "R802": (139.7, 113.03, 0, dict(R, _pwr_rot={"2": 180})),
        "TP801": (152.4, 96.52, 0, TPF),
        "TP802": (165.1, 109.22, 180, {"_ref_at": (8.89, 1.27), "_val_at": (8.89, 3.81)}),
    },
    "wire": ["I2C_SDA", "I2C_SCL", "IMU_INT1"],
    "anchor": {"I2C_SDA": ("J115", "5"), "I2C_SCL": ("J115", "4"), "IMU_INT1": ("J115", "8")},
    "label_at": {"I2C_SDA": (190.5, 101.6, (0, -1)), "I2C_SCL": (203.2, 104.14, (0, 1)),
                 "IMU_INT1": (66.04, 93.98, (0, -1))},
    "groups": {
        "imu": ("1  IMU J115 - Adafruit 4438", (22.86, 63.5, 101.6, 132.08),
                "LSM6DSOX module, component side up, JP1 1x9 only\\n(aux JP2 unused). VIN = +3V3 (AP2112K on module).\\n"
                "Addr 0x6A (DO open: module pull-down, SJ1 open).\\nINT1 push-pull 3.3 V. Two M2.5 standoffs."),
        "bus": ("2  Shared I2C bus", (106.68, 63.5, 210.82, 132.08),
                "Module pull-ups 10k to VIN (= +3V3) each: 10k || 10k = 5.0k.\\n"
                "Rise time approx. 0.21 us at 50 pF (estimate; 400 kHz: <= 0.3 us).\\n"
                "R801/R802 DNP option. R803 holds IMU_INT1 low without IMU."),
        "oled": ("3  OLED J116 - Adafruit 326", (215.9, 63.5, 274.32, 132.08),
                 "SSD1306 128x64, STEMMA QT rev.:\\nI2C default (SJ1/SJ2 closed).\\n"
                 "Addr 0x3D (A0 high, SJ3 open).\\nRst/CS/DC/3Vo open. Vin = +3V3."),
    },
    "notes": {"head": ("Sensors_Display: plug-in IMU and OLED on I2C0 (GPIO8 SDA, GPIO9 SCL) and IMU_INT1 (GPIO6). "
                       "No STEMMA QT cables. Both modules run from +3V3 (DevKit LDO).", 22.86, 58.42)},
}
