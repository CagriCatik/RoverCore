#!/usr/bin/env python3
"""Routing step 3 (K1, 2026-11-16): servo rail +V_SERVO from the output shunt RS402 to J102-J105, and the two
Micro-Fit signal lines that cross the rail band. Applied once to RoverCore.kicad_pcb; group "servo_rail_routing".

Up to 11.2 A (two blocked steering servos plus reserve, see the supply document). On F the VSERVO_REG pours occupy
the area north of RS402, so the rail leaves RS402 pad 2 through a 12-via field onto B, runs on B to the 5.6 mm
band between the Micro-Fit connectors and the AUX/ESC headers, and continues there on F and B in parallel (stitched)
to the connector pins. The Micro-Fit signal pins (J102/J103 pin 1) are routed first on F through the band, so the
pours fill around them. Refuses to run when the group exists or when +V_SERVO already has copper.
"""
from pathlib import Path
import sys

import pcbnew

sys.path.insert(0, str(Path(__file__).resolve().parent))
from route_servo_trial import Router, Abort  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
GROUP = "servo_rail_routing"
VS = "+V_SERVO"


def route(r):
    F, B = pcbnew.F_Cu, pcbnew.B_Cu
    A = "/Actuators/"
    # signals through the band first
    r.track(A + "SERVO_FRONT_OUT", F, 0.25, [("J102", "1"), (98.81, 10.9), (98.81, 19.8), (100.3, 21.27), ("R222", "2")])
    r.track(A + "SERVO_REAR_OUT", F, 0.25, [("J103", "1"), (112.5, 19.9), (113.3, 20.7), ("R223", "2")])
    # RS402 pad 2 -> via field -> B
    r.zone("rail_shunt_f", VS, F, [(85.0, 21.9), (92.3, 21.9), (92.3, 27.0), (85.0, 27.0)], 0.25, 2)
    for x in (87.4, 88.6, 89.8, 91.0):
        for y in (22.8, 24.4, 26.0):
            r.via(VS, x, y, 0.8, 0.4)
    band_b = [(85.0, 11.0), (100.6, 11.0), (100.6, 8.4), (102.4, 8.4), (102.4, 11.0), (114.6, 11.0), (114.6, 8.4),
              (116.4, 8.4), (116.4, 11.0), (122.6, 11.0), (122.6, 16.6), (92.4, 16.6), (92.4, 27.0), (85.0, 27.0)]
    r.zone("rail_b", VS, B, band_b, 0.25, 2)
    band_f = [(92.6, 11.3), (100.6, 11.3), (100.6, 8.4), (102.4, 8.4), (102.4, 11.3), (114.6, 11.3), (114.6, 8.4),
              (116.4, 8.4), (116.4, 11.3), (122.6, 11.3), (122.6, 16.6), (108.0, 16.6), (108.0, 18.0), (106.1, 18.0),
              (106.1, 16.6), (98.4, 16.6), (98.4, 18.0), (96.6, 18.0), (96.6, 16.6), (92.6, 16.6)]
    r.zone("rail_band_f", VS, F, band_f, 0.25, 2)
    for x in (94.0, 96.0, 103.5, 106.0, 109.0, 117.0, 120.5):
        r.via(VS, x, 13.9, 0.8, 0.4)


def main():
    pcb = Path(sys.argv[sys.argv.index("--board") + 1]) if "--board" in sys.argv else ROOT / "RoverCore.kicad_pcb"
    try:
        if list(pcb.parent.glob("~*.lck")) + list(pcb.parent.glob("*.lck")):
            raise Abort("KiCad lock files present")
        b = pcbnew.LoadBoard(str(pcb))
        if any(g.GetName() == GROUP for g in b.Groups()):
            raise Abort("group %s already exists" % GROUP)
        code = b.FindNet(VS).GetNetCode()
        if any(t.GetNetCode() == code for t in b.GetTracks()) or any(z.GetNetCode() == code for z in b.Zones()):
            raise Abort("+V_SERVO already has copper")
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
    b.Save(str(pcb))
    print("saved", pcb, "items", len(r.items))


if __name__ == "__main__":
    main()
