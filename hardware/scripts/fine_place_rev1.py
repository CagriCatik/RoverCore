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
    ACT[r22] = (x0 + 1.2, 20.6, 90)    # 470 R series, OUT pad north (connector side)
    ACT[q] = (x0 + 1.2, 24.4, 90)      # drain (DRV) north
    ACT[d] = (x0 + 1.2, 28.6, 180)     # +5V -> PU, PU pin west
    ACT[r24] = (x0 - 1.6, 20.9, 90)    # DRV -> GND
    ACT[r23] = (x0 - 1.6, 24.4, 90)    # PU -> DRV
    ACT[r21] = (x0 - 1.6, 28.0, 90)    # gate pull-up, gate pad north
ACT.update({
    "Q206": (119.0, 32.4, 90),         # OUT_LOCK clamp on ESC_DRV, in the ESC column
    "U201": (106.0, 37.0, 90),         # B side (pins 13-24) north towards the stages, A side south
    "C202": (101.0, 33.8, 90),         # VCCB (+5V) at pins 23/24
    "C201": (101.0, 40.2, -90),        # VCCA (+3V3) at pin 1
    "R216": (105.8, 31.6, 180), "R217": (108.9, 31.6, 0), "R218": (112.0, 31.6, 0),   # LED B-side pull-downs
    "R209": (101.5, 43.4, 90),         # DIR pull-up at pin 2
    "R201": (103.1, 43.4, 90), "R202": (104.7, 43.4, 90), "R203": (106.3, 43.4, 90),
    "R204": (107.9, 43.4, 90), "R205": (109.5, 43.4, 90),                             # A-side pull-ups
    "R206": (111.1, 43.4, -90), "R207": (112.7, 43.4, -90), "R208": (114.3, 43.4, -90),  # LED A-side pull-downs
    "U204": (97.5, 37.0, 0), "C203": (97.5, 40.3, 180),
    "R501": (94.6, 37.0, -90),         # ACT_OE_N pull-up (Controller sheet) at the U204 input
})

# ---- controller periphery below the DevKit (USB plug zone: flat SMD only)
CTRL = {
    "D501": (120.6, 53.34, 180), "TP503": (121.0, 57.0, 0),        # DevKit 5 V feed next to DevKit pin 21
    # 3V3 supervisor
    "U504": (124.0, 75.0, 0), "C505": (127.5, 75.0, 0), "R510": (124.0, 78.3, -90),
    # battery-loss supervisor with SENSE divider / filter at pin 5
    "U505": (131.5, 75.0, 0), "C507": (135.2, 73.6, 0), "R517": (127.8, 72.9, 180),
    "C506": (135.2, 75.3, 0), "R516": (135.2, 77.0, 0), "R515": (135.2, 78.7, 180),
    # enable button buffer -> latch clock
    "U507": (139.0, 75.0, 0), "C510": (142.6, 73.6, 0),
    "C511": (138.6, 78.4, -90), "R502": (140.2, 78.4, 90), "R518": (141.8, 78.4, -90),
    # VBAT_OK buffer and latch
    "U508": (146.2, 75.0, 0), "C509": (149.05, 75.0, -90),
    "U506": (145.9, 81.0, 0), "C508": (149.05, 80.6, -90), "R519": (145.4, 84.0, 180),
    # O-37 output lock
    "C513": (143.5, 87.4, 0), "U515": (139.0, 90.0, 0), "U516": (145.0, 90.0, 0), "R523": (142.0, 90.4, 90),
    "R521": (148.9, 86.9, -90), "R522": (148.9, 90.1, -90),
    "Q507": (139.0, 94.2, -90), "R524": (139.0, 97.9, -90), "TP506": (142.2, 96.6, 0),
    "D507": (134.5, 90.0, 0), "C512": (134.5, 87.0, 0), "R520": (131.0, 89.2, 0),
    # VBAT measurement
    "Q505": (125.4, 82.5, 0), "R508": (122.6, 82.5, 90), "R509": (122.6, 86.0, -90), "Q506": (125.4, 86.4, 0),
    "R505": (128.9, 82.5, 0), "R506": (128.9, 84.2, 180), "C504": (128.9, 85.9, 180), "R507": (128.9, 87.6, 180),
    "D506": (132.4, 84.5, 0), "TP505": (125.0, 90.6, 0),
    # 3V3 bulk, test points, status LED
    "C501": (124.5, 93.5, 0), "C502": (124.5, 95.6, 0), "TP502": (126.8, 97.9, 0), "TP504": (130.2, 97.9, 0),
    "R504": (146.5, 95.6, 0), "D502": (146.5, 97.9, 0), "TP501": (148.7, 93.4, 0),
}

GROUPS = {"logic": LOGIC, "actuators": ACT, "controller": CTRL}


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
    b.Save(str(pcb))
    print("saved %s (%d footprints placed)" % (pcb, moved))


if __name__ == "__main__":
    sys.exit(main())
