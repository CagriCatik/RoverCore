"""Provisional PCB placement for build_board.py - positions only (mm; origin top left, y down; rotation CCW deg).

Status: FIRST FUNCTIONAL PLACEMENT, not a mechanical release. Outline, mounting holes and connector access are
provisional and must be matched with the chassis (docs/vcu/rev1-platzierung.md).

parts:   ref -> (x, y, rotation[, "F"/"B"])     explicit positions (critical loops, connectors, modules)
pack:    zone frames whose listed parts are shelf-packed by courtyard size (small parts of a functional group)
outline: provisional Edge.Cuts rectangle (x1, y1, x2, y2)
zones:   functional group frames and keep-out notes on Dwgs.User (x1, y1, x2, y2, label)
holes:   provisional mounting-hole markers on Cmts.User only (cx, cy, diameter, label) - nothing drilled
"""

W, H = 150.0, 100.0

PARTS = {
    # ---- 1 input protection (Power): XT30 mating from the left edge, fuse, reverse-polarity FET, TVS, bulk
    "J101": (14.0, 12.0, 90), "F101": (19.0, 24.0, 0), "Q101": (30.0, 33.5, 90),
    "C101": (9.0, 37.0, 0), "D101": (22.0, 39.0, 0), "C102": (31.0, 41.0, 90),
    "D102": (24.5, 35.5, 0), "R101": (34.5, 34.0, 90),
    "TP101": (4.0, 25.0, 0), "TP102": (18.5, 31.0, 0), "TP103": (19.0, 44.0, 0),
    # ---- 2 logic supply (LogicPower): TPS54302, input cap across VIN/GND, SW straight to L301, outputs beside
    "U301": (8.0, 56.0, 180), "C301": (12.0, 56.0, 270), "C302": (12.0, 51.5, 270),
    "L301": (20.0, 56.0, 0), "C304": (26.5, 56.0, 90), "C305": (30.0, 56.0, 90), "C307": (33.5, 56.0, 90),
    "C303": (7.5, 60.0, 0),
    # ---- 3 servo regulator (ServoPower): hot loop Q401/Q402 + C401-C405, SW node -> L401 -> RS401 -> outputs
    "Q401": (51.0, 14.0, 270), "Q402": (57.0, 14.0, 90),
    "C405": (54.0, 19.3, 0), "C401": (54.0, 22.0, 0), "C402": (54.0, 25.3, 0),
    "C403": (54.0, 22.0, 0, "B"), "C404": (54.0, 25.3, 0, "B"),
    "L401": (66.5, 10.5, 0), "RS401": (75.5, 10.5, 0), "NT401": (74.25, 13.6, 270), "NT402": (76.75, 13.6, 270),
    "C406": (83.0, 8.0, 90), "C407": (90.5, 8.0, 90),
    "C408": (81.0, 18.0, 90), "C409": (84.5, 18.0, 90), "C410": (88.0, 18.0, 90),
    "RS402": (85.0, 25.0, 90), "NT404": (81.4, 26.25, 180), "NT405": (81.4, 23.75, 180), "NT403": (87.0, 27.1, 270),
    "U402": (86.0, 33.0, 0),
    # LTC7803 support parts at their pins (U401 pins left: 1 SS 16.25 ... 8 GND 19.75; right: 16 SW ... 9 INTVCC)
    "U401": (43.0, 18.0, 0),
    "C411": (47.0, 14.0, 90),             # BOOST (pin 14) - SW: bottom pad BOOST, top pad SW towards Q401 sources
    "D401": (44.6, 13.6, 90),             # INTVCC -> BOOST, anode side at C411
    "C412": (45.6, 22.3, 270), "C413": (47.4, 22.3, 270),   # INTVCC pins 9/10 -> GND, directly below the pins
    "C414": (38.1, 13.3, 90),             # SS (pin 1)
    "CF401": (38.1, 16.5, 270), "RF401": (35.6, 16.5, 90),  # sense filter at SENSE+/- (pins 2/3)
    "R404": (38.1, 19.7, 270), "R403": (35.6, 19.7, 90),    # feedback divider at VFB (pin 4), GND end at pins 7/8
    "C419": (40.6, 22.3, 270), "R413": (40.6, 25.5, 270), "C418": (38.1, 25.5, 270),  # ITH (pin 5) compensation
    # ---- 4 actuator outputs (Actuators): steering Micro-Fit at the top edge, aux/ESC headers, buffer U201
    "J102": (98.5, 9.7, 0), "J103": (112.5, 9.7, 0),
    "J104": (95.0, 16.5, 90), "J105": (104.5, 16.5, 90), "J106": (114.0, 16.5, 90),
    "U201": (106.0, 33.0, 0), "U204": (99.0, 26.0, 0),
    # ---- 5 controller: DevKit socket at the right edge, antenna keep-out beyond the top edge, USB end inside
    "U501": (125.5, 2.54, 0),
    # ---- 6 sensors and display (module sockets)
    "J116": (88.0, 66.0, 0), "J115": (97.5, 96.0, 0),
    # ---- 7 other interfaces (Lighting_IO): connectors along the bottom edge
    "J108": (8.0, 96.0, 0), "J109": (19.0, 96.0, 0), "J110": (30.0, 96.0, 0), "J111": (41.0, 96.0, 0),
    "J112": (52.0, 96.0, 0), "J107": (59.0, 84.0, 0), "BZ101": (50.0, 81.0, 0),
}

PACK = [
    # (x1, y1, x2, y2, refs) - shelf-packed inside the frame
    (36.0, 30.0, 52.0, 47.0, "R414 R407 Q403 Q404 R415 Q407 R420 R405 R406 C420 Q408"),
    (58.0, 30.0, 80.0, 47.0, "R412 C415 D404 R416 TP403 Q405 R418 R419 Q406 R410 R411 C417 D403 R417 C416 TP401 TP402"),
    (1.0, 62.0, 34.0, 75.0, "R301 R302 R303 R304 R305 C306 TP301 TP302"),
    (93.0, 39.0, 121.0, 62.0,
     "Q201 Q202 Q203 Q204 Q205 Q206 D201 D202 D203 D204 D205 R211 R212 R213 R214 R215 R221 R222 R223 R224 R225 "
     "R231 R232 R233 R234 R235 R241 R242 R243 R244 R245"),
    (93.0, 20.0, 121.0, 39.0, "C201 C202 C203 R201 R202 R203 R204 R205 R206 R207 R208 R209 R216 R217 R218"),
    # controller support parts below the DevKit (USB plug zone: low SMD parts only; buttons and test points
    # stay accessible with the DevKit plugged)
    (122.0, 66.0, 149.0, 99.0,
     "SW501 SW502 SW503 U504 U505 U506 U507 U508 U515 U516 D507 Q505 Q506 Q507 C501 C502 C504 C505 C506 C507 C508 "
     "C509 C510 C511 C512 C513 R501 R502 R504 R505 R506 R507 R508 R509 R510 R515 R516 R517 R518 R519 R520 R521 "
     "R522 R523 R524 D501 D506 D502 TP501 TP502 TP503 TP504 TP505 TP506"),
    (1.0, 77.0, 44.0, 91.0,
     "C601 C602 C603 C604 C605 C606 C607 C608 C610 D601 D602 D603 D604 D605 D606 D607 D608 Q601 R601 R602 R603 "
     "R604 R605 R606 R607 R608 R609 R610 R611 R612 R613 R614 R615 R616 R617 U202 U203 U601 U602 U603 TP601 TP602"),
    (60.0, 50.0, 80.0, 60.0, "R801 R802 R803 TP801 TP802"),
]

ZONES = [
    (0.0, 0.0, 35.0, 47.0, "1 Eingangsschutz (Power)"),
    (0.0, 47.0, 35.0, 76.0, "2 Logikversorgung +5V (LogicPower)"),
    (35.0, 0.0, 92.5, 48.0, "3 Servoregler LTC7803 (ServoPower)"),
    (92.5, 0.0, 121.5, 63.0, "4 Aktuatoranschluesse (Actuators)"),
    (121.5, 0.0, 150.0, 65.0, "5 Controller / DevKit"),
    (121.5, 65.0, 150.0, 100.0, "USB-Steckerzugang: nur flache Bauteile"),
    (57.0, 48.0, 121.5, 100.0, "6 Sensoren und Display"),
    (0.0, 76.0, 57.0, 100.0, "7 Schnittstellen (Lighting_IO)"),
]

HOLES = [(28.0, 4.0, 3.2, "M3?"), (54.0, 4.0, 3.2, "M3?"), (4.0, 36.0, 3.2, "M3?"), (91.0, 81.0, 3.2, "M3?"),
         (145.0, 81.0, 3.2, "M3?")]  # K1 (2026-11-16); the bootstrap outline below is the old 150 x 100

NOTES = [("VORLAEUFIG: Kontur 150 x 100 mm und Befestigung nicht mit dem Chassis abgestimmt. Keine Fertigungsfreigabe.",
          1.0, -3.0)]

LAYOUT = {"parts": PARTS, "pack": PACK, "outline": (0.0, 0.0, W, H), "zones": ZONES, "holes": HOLES, "notes": NOTES}
