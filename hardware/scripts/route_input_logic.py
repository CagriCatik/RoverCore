#!/usr/bin/env python3
"""Routing step 2 (2026-11-16): input chain, VBAT_PROT distribution to the servo stage and the logic supply, and
the TPS54302 stage (LogicPower) locally. Applied once to RoverCore.kicad_pcb.

Same rules as route_servo_trial.py (stackup: F/In1 GND/In2 GND/B, see docs/vcu/rev1-platzierung.md 3a):
* VBAT_IN and VBAT_FUSED as pours on F and B (about 10 A input current at full servo load, estimate), stitched;
* VBAT_PROT node at the Q101 source pins, feed to the servo stage as a pour on F (corridor y 27.6-29.9) with a
  parallel pour on B below the feedback trace, joined by via rows at both ends; 1 mm trace to the logic supply;
* TPS54302: input loop C301/C302 at VIN/GND, SW between the C301 pads to L301, boot cap C303 between the pin rows,
  FB/EN dividers at the pins, +5V sense from the output capacitors on B, output and GND pours with vias.
All items go into the group "input_logic_routing". Refuses to run when the group exists, when KiCad lock files
exist, or when copper already exists on the nets only this step routes. Run with the KiCad Python.
"""
from pathlib import Path
import argparse
import sys

import pcbnew

sys.path.insert(0, str(Path(__file__).resolve().parent))
from route_servo_trial import Router, Abort  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
GROUP = "input_logic_routing"
OWN_NETS = ["/Power/VBAT_IN", "/Power/VBAT_FUSED", "/Power/Q101_GATE", "/LogicPower/SW_5V", "/LogicPower/BOOT_5V",
            "/LogicPower/FB_5V", "/LogicPower/VSENSE_5V", "/LogicPower/EN_5V"]


def route(r):
    F, B = pcbnew.F_Cu, pcbnew.B_Cu
    VP, VI, VF, G = "/Power/VBAT_PROT", "/Power/VBAT_IN", "/Power/VBAT_FUSED", "/Power/Q101_GATE"
    LP = "/LogicPower/"
    # ---- input: J101 pin 2 -> F101 (VBAT_IN), F101 -> Q101 drain (VBAT_FUSED), both layers
    for lay, nm in ((F, "f"), (B, "b")):
        r.zone("in_vbat_in_" + nm, VI, lay, [(10.4, 15.0), (19.8, 15.0), (19.8, 29.6), (10.4, 29.6)], 0.25, 2)
    r.zone("in_vbat_fused_f", VF, F, [(24.9, 24.0), (35.3, 24.0), (35.3, 29.6), (24.9, 29.6)], 0.25, 2)
    r.zone("in_vbat_fused_b", VF, B, [(24.9, 22.0), (35.3, 22.0), (35.3, 28.7), (24.9, 28.7)], 0.25, 2)
    for x, y in ((28.5, 25.0), (28.5, 26.6), (28.5, 28.2), (29.6, 25.8), (29.6, 27.4)):
        r.via(VF, x, y, 0.8, 0.4)
    for x, y in ((12.0, 20.5), (13.6, 20.5), (12.0, 22.0), (13.6, 22.0)):
        r.via(VI, x, y, 0.8, 0.4)
    # ---- Q101 gate: D102 (gate west, VBAT east) and R101; gate trace above the drain, VBAT trace east of pin 4
    r.track(G, F, 0.3, [("D102", "2"), (31.75, 23.75), (36.6, 23.75), (36.6, 25.095), ("Q101", "4")])
    r.track(G, F, 0.3, [("R101", "1"), ("D102", "2")])
    r.track(VP, F, 0.3, [("D102", "1"), (37.3, 22.7), (37.3, 26.365), ("Q101", "3")])
    r.via("GND", 29.3, 20.3)
    r.track("GND", F, 0.3, [("R101", "2"), (29.3, 20.3)])
    # ---- VBAT_PROT node, feed corridor to the servo stage (F) and parallel pour on B, logic branch
    r.zone("in_vbat_prot_f", VP, F,
           [(35.4, 25.8), (38.0, 25.8), (38.0, 26.9), (53.7, 26.9), (53.7, 29.9), (35.9, 29.9), (35.9, 41.0),
            (24.0, 41.0), (24.0, 38.0), (33.3, 38.0), (33.3, 29.6), (35.4, 29.6)], 0.25, 3)  # overlaps servo_vbat_f
    r.zone("in_vbat_prot_b", VP, B, [(33.3, 29.1), (53.4, 29.1), (53.4, 35.4), (33.3, 35.4)], 0.25, 2)
    for x, y in ((34.0, 30.25), (35.2, 30.25), (34.0, 34.6), (35.2, 34.6),
                 (49.6, 29.2), (50.6, 29.2), (51.6, 29.2), (52.6, 29.2)):
        r.via(VP, x, y, 0.8, 0.4)
    r.track(VP, F, 1.0, [(25.0, 40.6), (25.0, 46.6), (13.0, 46.6), (10.5, 49.1), (10.5, 52.2), (10.9, 52.5)])
    # GND of the input parts
    for x, y in ((28.3, 32.0), (28.3, 33.2), (30.9, 36.0), (30.9, 37.4), (16.2, 41.5), (17.6, 41.5), (19.0, 41.5)):
        r.via("GND", x, y, 0.8, 0.4)
    r.track("GND", F, 1.0, [("D101", "2"), (28.3, 32.6)])
    r.track("GND", F, 1.0, [("C102", "2"), (30.9, 36.7)])
    r.track("GND", F, 1.5, [("C101", "2"), (17.6, 41.5)])
    r.via("GND", 31.3, 43.0)
    r.track("GND", F, 0.5, [("TP103", "1"), (31.3, 43.0)])

    # ---- TPS54302 input loop: C301 straddles VIN (pin 3) and GND (pin 1); C302 at C301's VIN pad
    r.track(VP, F, 0.6, [("U301", "3"), (10.65, 55.05)])
    r.track(VP, F, 0.6, [("C302", "1"), (11.4, 53.95)])
    r.track("GND", F, 0.6, [("U301", "1"), (10.65, 57.0)])
    for x, y in ((12.0, 58.75), (13.9, 57.5), (10.9, 58.6), (13.6, 52.75)):
        r.via("GND", x, y, 0.8 if x != 10.9 else 0.6, 0.4 if x != 10.9 else 0.3)
    r.track("GND", F, 0.4, [("C302", "2"), (13.6, 52.75)])
    r.track("GND", F, 0.6, [("C301", "2"), (12.0, 58.75)])
    r.track("GND", F, 0.6, [("C301", "2"), (13.9, 57.5)])
    r.track("GND", F, 0.4, [("U301", "1"), (10.9, 58.6)])
    # SW: pin 2 between the C301 pads to L301; boot cap C303 under the IC, SW side between the pin rows
    r.track(LP + "SW_5V", F, 0.6, [("U301", "2"), ("L301", "1")])
    r.track(LP + "SW_5V", F, 0.25, [(8.6, 56.0), (8.0, 56.45), (8.0, 58.2), ("C303", "2")])
    r.track(LP + "BOOT_5V", F, 0.3, [("U301", "6"), (6.9, 57.6), ("C303", "1")])
    # FB divider at pin 4, VSENSE node, +5V sense from the output capacitors on B
    r.track(LP + "FB_5V", F, 0.25, [("U301", "4"), (6.3, 54.4), ("R302", "2")])
    r.track(LP + "FB_5V", F, 0.25, [("R303", "1"), ("C306", "2"), ("R302", "2")])
    r.track(LP + "VSENSE_5V", F, 0.25, [("C306", "1"), ("R302", "1")])
    r.track(LP + "VSENSE_5V", F, 0.25, [("R301", "2"), ("R302", "1")])
    r.via("GND", 2.9, 50.9)
    r.track("GND", F, 0.3, [("R303", "2"), (2.9, 50.9)])
    r.via("+5V", 6.3, 47.9)
    r.track("+5V", F, 0.25, [("R301", "1"), (6.3, 47.9)])
    r.track("+5V", B, 0.25, [(6.3, 47.9), (31.0, 47.9), (31.0, 57.0)])
    r.via("+5V", 31.0, 57.0)
    r.track("+5V", F, 0.25, [(31.0, 57.0), ("C307", "1")])
    # EN divider: R305 at pin 5, R304 VBAT end via B to C302's VBAT pad
    r.track(LP + "EN_5V", F, 0.25, [("R305", "1"), ("U301", "5")])
    r.track(LP + "EN_5V", F, 0.25, [("R304", "2"), (5.0, 56.4), ("R305", "1")])
    r.via("GND", 2.6, 56.0)
    r.track("GND", F, 0.3, [("R305", "2"), (2.6, 56.0)])
    r.via(VP, 4.6, 60.3)
    r.track(VP, F, 0.25, [("R304", "1"), (4.6, 60.3)])
    r.track(VP, B, 0.25, [(4.6, 60.3), (10.0, 60.3), (10.0, 53.6)])
    r.via(VP, 10.0, 53.6)
    r.track(VP, F, 0.25, [(10.0, 53.6), ("C302", "1")])
    # output: +5V pour over the capacitor row incl. TP301, GND pour with vias under the GND pads incl. TP302
    r.zone("logic_5v_f", "+5V", F, [(18.5, 56.7), (33.3, 56.7), (33.3, 59.6), (18.5, 59.6)], 0.25, 2)
    r.zone("logic_gnd_out_f", "GND", F, [(20.9, 52.6), (33.3, 52.6), (33.3, 55.6), (20.9, 55.6)], 0.2, 1)
    for x in (22.5, 25.8, 29.1):
        r.via("GND", x, 53.3, 0.8, 0.4)
    r.track("+5V", F, 1.5, [("L301", "2"), (20.5, 57.475)])


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--board", default=str(ROOT / "RoverCore.kicad_pcb"))
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    pcb = Path(a.board)
    try:
        if list(pcb.parent.glob("~*.lck")) + list(pcb.parent.glob("*.lck")):
            raise Abort("KiCad lock files present")
        b = pcbnew.LoadBoard(str(pcb))
        if any(g.GetName() == GROUP for g in b.Groups()):
            raise Abort("group %s already exists" % GROUP)
        codes = {b.FindNet(n).GetNetCode() for n in OWN_NETS if b.FindNet(n)}
        busy = [t for t in b.GetTracks() if t.GetNetCode() in codes] + [z for z in b.Zones() if z.GetNetCode() in codes]
        if busy:
            raise Abort("%d items already on the nets of this step; not overwriting manual work" % len(busy))
        r = Router(b)
        route(r)
        g = pcbnew.PCB_GROUP(b)
        g.SetName(GROUP)
        b.Add(g)
        for it in r.items:
            g.AddItem(it)
        pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    except Abort as e:
        raise SystemExit("ABORTED, board not written: %s" % e)
    kinds = [i.GetClass() for i in r.items]
    print("tracks %d, vias %d, zones %d" % (kinds.count("PCB_TRACK"), kinds.count("PCB_VIA"), kinds.count("ZONE")))
    if a.dry_run:
        print("dry run, not saved")
        return
    b.Save(str(pcb))
    print("saved", pcb)


if __name__ == "__main__":
    sys.exit(main())
