#!/usr/bin/env python3
"""Explicit links for the K1 bottlenecks the autorouter left open (routing step 5, 2026-11-16).

Usage: <KiCad python> route_k1_links.py BOARD.kicad_pcb
Each link is a polyline per layer with vias between layers; every segment and via is checked against copper of
other nets (stitch_gnd_vias.Copper, 0.2 mm) before anything is added. A link that fails the check is skipped and
reported. Group "k1_links".
- RUN_SERVO: the escape via of U401 pin 6 is enclosed on B (VBAT_FUSED pour, feedback trace) and on F (VBAT feed
  corridor). B hop east to the free F column at x 43, inside the corridor pour west to x 39.3 (the pour splits there; both
  halves stay joined through the parallel B pour and its via rows), down onto Q403 pin 3 (RUN), west of the
  SERVO_EN_SRC track along the transistor row.
- VBAT_PROT to the RUN divider R405/R414: via next to R405 pad 1 down into the B VBAT_PROT pour.
"""
from pathlib import Path
import sys

import pcbnew

sys.path.insert(0, str(Path(__file__).resolve().parent))
import stitch_gnd_vias as sg  # noqa: E402

M = pcbnew.FromMM
F, B = pcbnew.F_Cu, pcbnew.B_Cu
LINKS = [
    ("/ServoPower/RUN_SERVO", 0.2, (0.45, 0.25), [
        (B, [(39.95, 19.0), (39.95, 20.6), (43.0, 20.6), (43.0, 21.0)]),
        ("via", (43.0, 21.0)),
        (F, [(43.0, 21.0), (43.0, 28.0), (40.3, 28.0), (39.3, 29.0), (39.3, 31.0), (38.91, 31.45)])]),
    ("/Power/VBAT_PROT", 0.4, (0.6, 0.3), [
        (F, [(40.35, 38.95), (40.4, 37.6)]),
        ("via", (40.4, 37.6)),
        (B, [(40.4, 37.6), (40.4, 35.0)])]),
]

# links after autorouting (--post): replacements for autorouted segments that violated clearance
POST_LINKS = [  # none applied yet; see report 3i (IMU_INT1 near DevKit pin 12 remains a clearance finding)
]


def main():
    pcb = Path(sys.argv[1])
    links = POST_LINKS if "--post" in sys.argv else LINKS
    b = pcbnew.LoadBoard(str(pcb))
    g = next((x for x in b.Groups() if x.GetName() == "k1_links"), None)
    if g is None:
        g = pcbnew.PCB_GROUP(b)
        g.SetName("k1_links")
        b.Add(g)
    for net, w, (vd, dr), parts in links:
        ni = b.FindNet(net)
        cu = sg.Copper(b, ni.GetNetCode())
        # RUN_SERVO: ignoring the pour here was a mistake - the route split in_vbat_prot_f into two islands. Kept so
        # the autorouting run stays reproducible; k1_fixups.py run_unroute/run_reroute replace it afterwards.
        if net.endswith("RUN_SERVO"):
            cu.zones = [z for z in cu.zones if z.GetZoneName() != "in_vbat_prot_f"]
        sg.STUB = w
        bad = []
        for kind, data in parts:
            if kind == "via":
                if not cu.free_point(data[0], data[1], vd / 2, [F, B]):
                    bad.append("via %s" % (data,))
            else:
                for s, e in zip(data, data[1:]):
                    if not cu.free_stub(s, e, kind):
                        bad.append("%s %s-%s" % ("F" if kind == F else "B", s, e))
        if bad:
            print("SKIPPED %s: %s" % (net, "; ".join(bad)))
            continue
        for kind, data in parts:
            if kind == "via":
                v = pcbnew.PCB_VIA(b)
                v.SetViaType(pcbnew.VIATYPE_THROUGH)
                v.SetLayerPair(F, B)
                v.SetPosition(pcbnew.VECTOR2I(M(data[0]), M(data[1])))
                v.SetWidth(M(vd))
                v.SetDrill(M(dr))
                v.SetNet(ni)
                b.Add(v)
                g.AddItem(v)
            else:
                for s, e in zip(data, data[1:]):
                    t = pcbnew.PCB_TRACK(b)
                    t.SetStart(pcbnew.VECTOR2I(M(s[0]), M(s[1])))
                    t.SetEnd(pcbnew.VECTOR2I(M(e[0]), M(e[1])))
                    t.SetWidth(M(w))
                    t.SetLayer(kind)
                    t.SetNet(ni)
                    b.Add(t)
                    g.AddItem(t)
        print("added", net)
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    b.Save(str(pcb))


if __name__ == "__main__":
    main()
