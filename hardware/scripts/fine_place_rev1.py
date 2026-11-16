#!/usr/bin/env python3
"""Electrical fine placement Rev1: logic supply, output stages and controller periphery (2026-11-16).

Sets explicit positions (mm) and rotations for the listed footprints only; the courtyard packing of
build_board.py --bootstrap was only the starting point. Rotation conventions used below (KiCad, y down):
  0603/0805/1210: r0 pad 1 west, r180 pad 1 east, r90 pad 1 south, r-90 pad 1 north
  SOT-23 (3 pin): r0 pin 3 east; r90 pin 3 north (pin 1 SW, pin 2 SE); r-90 pin 3 south (pin 1 NE, pin 2 NW);
                  r180 pin 3 west (pin 1 SE)
Refuses to move a footprint that already has copper attached (manual routing is never moved), and refuses to
run while KiCad lock files exist. Run with the KiCad Python; --board for a copy, --dry-run to check only.
"""
from pathlib import Path
import argparse
import sys

import pcbnew

ROOT = Path(__file__).resolve().parents[2]

# ---- logic supply TPS54302 (input cap across VIN/GND, SW between its pads to L301, boot cap at the pins)
LOGIC = {
    "C302": (12.0, 52.75, 0),        # 100 nF next to C301 on the VIN side, GND pad to its own via
    "C303": (8.0, 58.7, 0),          # boot cap directly under U301: BOOT pin 6 / SW pin 2 (between the pin rows)
    "L301": (17.3, 56.0, 0),         # 2.7 mm closer to U301: shorter SW node
    "C304": (22.5, 56.0, 90), "C305": (25.8, 56.0, 90), "C307": (29.1, 56.0, 90),
    "R301": (6.3, 49.6, -90),        # +5V sense (from the output caps) -> VSENSE
    "R302": (6.3, 52.7, -90),        # VSENSE -> FB, FB pad next to pin 4
    "C306": (4.6, 52.7, -90),        # feed-forward parallel to R302
    "R303": (2.9, 52.7, 90),         # FB -> GND, FB pad south
    "R305": (4.3, 56.0, 180),        # EN -> GND, EN pad at pin 5
    "R304": (4.6, 58.6, 90),         # VBAT -> EN, EN pad north
    "TP301": (32.4, 58.0, 0), "TP302": (32.4, 54.0, 0),
}

# ---- output stages: one column per channel, ordered like the connectors (west -> east)
ACT = {}
for x0, (q, r21, r22, r23, r24, d) in zip(
        (95.0, 100.7, 106.4, 112.1, 117.8),
        (("Q204", "R214", "R224", "R234", "R244", "D204"),     # AUX1  -> J104
         ("Q202", "R212", "R222", "R232", "R242", "D202"),     # FRONT -> J102
         ("Q205", "R215", "R225", "R235", "R245", "D205"),     # AUX2  -> J105
         ("Q203", "R213", "R223", "R233", "R243", "D203"),     # REAR  -> J103
         ("Q201", "R211", "R221", "R231", "R241", "D201"))):   # ESC   -> J106
    # rows 1.3 mm apart so that every reference fits between them (owner review 2026-11-16)
    ACT[r22] = (x0 + 1.2, 22.1, 90)    # 470 R series, OUT pad north (connector side)
    ACT[q] = (x0 + 1.2, 26.9, 90)      # drain (DRV) north
    ACT[d] = (x0 + 1.2, 31.95, 180)    # +5V -> PU, PU pin west
    ACT[r24] = (x0 - 1.6, 22.4, 90)    # DRV -> GND
    ACT[r23] = (x0 - 1.6, 26.7, 90)    # PU -> DRV
    ACT[r21] = (x0 - 1.6, 31.0, 90)    # gate pull-up, gate pad north
ACT.update({
    # AUX/ESC headers 1.5 mm south: the strip to the Micro-Fit connectors carries the function labels of both rows
    "J104": (95.0, 18.0, 90), "J105": (104.5, 18.0, 90), "J106": (114.0, 18.0, 90),
    "Q206": (119.0, 37.0, 90),         # OUT_LOCK clamp on ESC_DRV, below the ESC column
    "U201": (106.0, 42.1, 90),         # B side (pins 13-24) north towards the stages, A side south
    "C202": (101.0, 38.7, 90),         # VCCB (+5V) at pins 23/24
    "C201": (101.0, 44.8, 90),        # VCCA (+3V3) at pin 1
    "R216": (105.8, 35.8, 180), "R217": (108.9, 35.8, 0), "R218": (112.0, 35.8, 0),   # LED B-side pull-downs
    "R209": (101.5, 48.0, 90),         # DIR pull-up at pin 2
    "R201": (103.1, 48.0, 90), "R202": (104.7, 48.0, 90), "R203": (106.3, 48.0, 90),
    "R204": (107.9, 48.0, 90), "R205": (109.5, 48.0, 90),                             # A-side pull-ups
    "R206": (111.1, 48.0, -90), "R207": (112.7, 48.0, -90), "R208": (114.3, 48.0, -90),  # LED A-side pull-downs
    "U204": (97.5, 42.1, 0), "C203": (97.5, 45.4, 180),
    "R501": (94.6, 42.1, -90),         # ACT_OE_N pull-up (Controller sheet) at the U204 input
})

# ---- operator zone (owner review 2026-11-16): ENABLE with the status LED in the free strip above the OLED,
# RESET / BOOT as a separate service group between OLED and DevKit. Centres keep >= 10 mm to the module and
# USB-plug envelopes (finger access, see the report) and the buttons are 26 mm apart from ENABLE.
OPERATOR = {
    "SW501": (81.5, 53.0, 0), "D502": (89.5, 53.0, 0), "R504": (89.5, 55.2, 0),
    "SW502": (101.5, 55.0, 90), "SW503": (113.5, 55.0, 90),
}

# ---- controller periphery below the DevKit (USB plug zone: flat SMD only). Courtyards >= 2 mm from the board
# edge and >= 4 mm from the M3 marker at (146.5, 96.5).
CTRL = {
    "D501": (120.6, 53.34, 180), "TP503": (121.0, 57.0, 0),        # DevKit 5 V feed next to DevKit pin 21
    # 3V3 supervisor
    "U504": (124.5, 68.5, 0), "C505": (128.2, 68.5, 0), "R510": (124.5, 72.3, -90),
    # battery-loss supervisor with SENSE divider / filter at pin 5
    "U505": (134.0, 68.5, 0), "R517": (130.2, 66.9, 180),
    "C507": (138.0, 67.3, 0), "C506": (138.0, 69.3, 0), "R516": (138.0, 71.2, 0), "R515": (138.0, 73.1, 180),
    # enable button buffer -> latch clock, debounce at the buffer input
    "U507": (126.0, 77.5, 0), "C510": (129.8, 76.1, 0),
    "C511": (124.4, 81.0, -90), "R502": (126.0, 81.0, 90), "R518": (127.6, 81.0, -90),
    # VBAT_OK buffer and latch
    "U508": (134.0, 77.5, 0), "C509": (137.8, 76.1, 0),
    "U506": (142.5, 77.5, 0), "C508": (146.4, 77.0, -90), "R519": (142.5, 80.6, 180), "TP501": (146.0, 81.4, 0),
    # VBAT measurement
    "Q505": (125.4, 86.0, 0), "R508": (122.6, 86.0, 90), "R509": (122.6, 89.6, -90), "Q506": (125.4, 90.0, 0),
    "R505": (129.2, 86.0, 0), "R506": (129.2, 88.6, 180), "C504": (129.2, 91.2, 180), "R507": (129.2, 93.8, 180),
    "D506": (133.0, 88.0, 0), "TP505": (125.2, 95.8, 0),
    # 3V3 bulk and test points
    "C501": (131.5, 96.6, 0), "C502": (135.3, 96.6, 0), "TP502": (137.5, 93.0, 0), "TP504": (141.0, 93.0, 0),
}
# ---- O-37 output lock moved into the free area between OLED and DevKit, next to its loads (U204, Q206)
O37 = {  # 4.5 mm below the service buttons, 1 mm gaps for the references
    "R520": (96.5, 67.7, 0), "C512": (100.0, 65.5, 0), "D507": (100.0, 68.5, 0),
    "U515": (105.0, 68.5, 0), "R523": (108.3, 68.9, 90), "U516": (111.5, 68.5, 0), "C513": (109.8, 65.6, 0),
    "R521": (111.5, 72.4, 0), "R522": (111.5, 74.4, 180),
    "Q507": (105.0, 73.9, -90), "R524": (105.0, 78.2, -90), "TP506": (108.2, 77.0, 0),
}

# ---- LED/UART connector row 2 mm east: J108 was 2 mm from the M3 marker at (3.5, 96.5)
EDGE = {"J108": (10.0, 96.0, 0), "J109": (21.0, 96.0, 0), "J110": (32.0, 96.0, 0), "J111": (43.0, 96.0, 0),
        "J112": (54.0, 96.0, 0)}

# ---- input protection (2026-11-16): current path left to right J101 -> F101 -> Q101; Q101 turned so that its
# VBAT_PROT pins (1-3) face east into the feed corridor to the servo stage (y 27.6-29.9); gate parts north of Q101,
# TVS and capacitors at the VBAT_PROT node below it, bulk C101 towards the logic supply.
INPUT = {
    "F101": (16.6, 24.5, 0), "TP101": (11.5, 24.5, 0),
    "Q101": (33.6, 27.0, 180), "D102": (33.4, 22.7, 180), "R101": (31.0, 20.3, 180),
    "D101": (32.3, 32.6, 180), "C102": (33.5, 36.8, 180), "C101": (21.8, 39.5, 180),
    "TP102": (30.0, 39.6, 0), "TP103": (30.0, 43.0, 0),
}

# ---- interfaces (2026-11-16): one column per connector (ESD diode at the pin, series R above it), LED power
# switch U601 between J108-J111, LED4 level shifter at J111, UART power and series parts at J112, iBUS buffer and
# power at J107 (moved 5 mm north to free the UART column), buzzer block in the free area above.
IFACE = {
    "D601": (12.0, 91.5, 90), "D602": (23.0, 91.5, 90), "D603": (34.0, 91.5, 90), "D604": (45.0, 91.5, 90),
    "D607": (56.0, 91.5, 90), "D608": (58.0, 91.5, 90), "TP602": (15.0, 91.5, 0),
    "R607": (12.0, 88.4, -90), "R608": (23.0, 88.4, -90), "R609": (34.0, 88.4, -90), "R610": (45.0, 88.4, -90),
    "R615": (56.0, 88.4, -90), "R616": (58.0, 88.4, 90), "R617": (60.2, 88.4, 90),
    "U601": (22.0, 83.0, 0), "C601": (18.6, 83.0, -90), "C602": (25.6, 82.6, -90), "R601": (22.0, 86.0, 180),
    "U202": (42.5, 83.0, 0), "C607": (39.2, 82.6, -90), "C603": (45.9, 82.6, -90),
    "R605": (39.0, 85.8, 180), "R606": (43.0, 85.8, 180), "R604": (47.2, 85.8, 180),
    "U602": (51.0, 83.0, 0), "C608": (48.1, 82.6, -90), "C604": (54.4, 82.6, -90), "R602": (51.0, 86.0, 180),
    "J107": (59.0, 79.0, 0), "D606": (61.6, 79.0, 0), "R613": (59.0, 75.6, 90), "R614": (57.3, 75.6, -90),
    "U203": (58.5, 71.0, 0), "C610": (61.8, 70.6, -90), "TP601": (62.0, 74.0, 0),
    "U603": (52.3, 77.5, 0), "C606": (55.5, 77.0, -90), "C605": (49.4, 77.0, -90), "R603": (51.6, 80.3, 180),
    "BZ101": (34.0, 71.5, 0), "Q601": (42.0, 70.5, 180), "D605": (42.6, 74.8, 180),
    "R611": (46.5, 71.5, 180), "R612": (46.5, 73.3, 0),
}

GROUPS = {"logic": LOGIC, "actuators": ACT, "operator": OPERATOR, "controller": CTRL, "o37": O37, "edge": EDGE, "input": INPUT, "interfaces": IFACE}


class Abort(Exception):
    pass


def has_copper(board, fp):
    pads = list(fp.Pads())
    for t in board.GetTracks():
        pts = [t.GetPosition()] if t.GetClass() == "PCB_VIA" else [t.GetStart(), t.GetEnd()]
        for p in pads:
            if t.GetNetCode() == p.GetNetCode() and t.GetNetCode() > 0 and any(p.HitTest(q) for q in pts):
                return True
    return False


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--board", default=str(ROOT / "RoverCore.kicad_pcb"))
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    pcb = Path(a.board)
    try:
        locks = list(pcb.parent.glob("~*.lck")) + list(pcb.parent.glob("*.lck"))
        if locks:
            raise Abort("KiCad lock files present: %s" % ", ".join(p.name for p in locks))
        b = pcbnew.LoadBoard(str(pcb))
        if abs(pcbnew.ToMM(b.GetBoardEdgesBoundingBox().GetHeight()) - 100.0) > 0.5:
            raise Abort("these positions belong to the 150 x 100 mm layout; the board is K1 "
                        "(make_compact_variant.py) - not applying")
        fps = {f.GetReference(): f for f in b.GetFootprints()}
        moved = 0
        for name, table in GROUPS.items():
            for ref, (x, y, rot) in table.items():
                if ref not in fps:
                    raise Abort("unknown reference %s" % ref)
                fp = fps[ref]
                if fp.GetLayer() != pcbnew.F_Cu:
                    raise Abort("%s is not on F.Cu" % ref)
                if has_copper(b, fp):
                    raise Abort("%s already has copper attached; not moving it" % ref)
                fp.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y)))
                fp.SetOrientationDegrees(rot)
                moved += 1
            print("%-10s %d footprints" % (name, len(table)))
    except Abort as e:
        raise SystemExit("ABORTED, board not written: %s" % e)
    if a.dry_run:
        print("dry run, not saved")
        return
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())  # moved THT pads: refill the planes
    b.Save(str(pcb))
    print("saved %s (%d footprints placed)" % (pcb, moved))


if __name__ == "__main__":
    sys.exit(main())
