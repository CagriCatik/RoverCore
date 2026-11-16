#!/usr/bin/env python3
"""Close the remaining non-GND gaps after autorouting (routing step 5, K1) with short B.Cu links.

Usage: <KiCad python> close_gaps.py BOARD.kicad_pcb [--group NAME]
For every unconnected pair that KiCad's DRC reports on a net other than GND, try: a via at a free spot next to
each end (end on F) or the end itself (end on B), and a straight or L-shaped B.Cu trace between them, all with
0.2 mm clearance to copper of other nets on the layers used (same checks as stitch_gnd_vias.py). Power-class
nets get 0.4 mm traces and 0.6/0.3 mm vias, others 0.2 mm and 0.45/0.25 mm. Gaps without a free path are listed.
"""
from pathlib import Path
import json
import math
import re
import subprocess
import sys
import tempfile

import pcbnew

sys.path.insert(0, str(Path(__file__).resolve().parent))
from stitch_gnd_vias import Copper, CLI, M  # noqa: E402

POWER = {"+3V3", "+5V", "/Lighting_IO/+5V_LED", "/Lighting_IO/+5V_EXT", "/Lighting_IO/+5V_RX",
         "/Controller/+5V_DEVKIT", "+V_SERVO", "/Power/VBAT_PROT", "/Controller/LOCK_SUP"}


def gaps(pcb):
    with tempfile.TemporaryDirectory() as d:
        rep = Path(d) / "drc.json"
        subprocess.run([CLI, "pcb", "drc", "--format", "json", "-o", str(rep), str(pcb)], capture_output=True)
        data = json.loads(rep.read_text())
    out = []
    for u in data["unconnected_items"]:
        a, b = u["items"][:2]
        m = re.search(r"\[([^\]]*)\]", a["description"])
        net = m.group(1) if m else ""
        if net and net != "GND":
            lay = lambda it: pcbnew.B_Cu if "on B.Cu" in it["description"] and "F.Cu" not in it["description"] \
                else pcbnew.F_Cu  # noqa: E731
            out.append((net, (a["pos"]["x"], a["pos"]["y"], lay(a)), (b["pos"]["x"], b["pos"]["y"], lay(b))))
    return out


def spot(cu, x, y, r_via):
    for r in (0.0, 0.6, 0.9, 1.2, 1.6, 2.0):
        for k in range(16 if r else 1):
            a = 2 * math.pi * k / 16
            vx, vy = x + r * math.cos(a), y + r * math.sin(a)
            if cu.free_via(vx, vy, r_via):
                yield (vx, vy)


def main():
    pcb = Path(sys.argv[1])
    name = sys.argv[sys.argv.index("--group") + 1] if "--group" in sys.argv else "gap_links_k1"
    todo = gaps(pcb)
    b = pcbnew.LoadBoard(str(pcb))
    g = next((x for x in b.Groups() if x.GetName() == name), None)
    if g is None:
        g = pcbnew.PCB_GROUP(b)
        g.SetName(name)
        b.Add(g)
    done, failed = 0, []
    for net, p, q in todo:
        ni = b.FindNet(net)
        pw = net in POWER
        w, vd, dr = (0.4, 0.6, 0.3) if pw else (0.2, 0.45, 0.25)
        cu = Copper(b, ni.GetNetCode())
        import stitch_gnd_vias as sg
        old = sg.STUB
        sg.STUB = w
        ok = None
        for a in list(spot(cu, p[0], p[1], vd / 2))[:6]:
            if a != (p[0], p[1]) and not cu.free_stub((p[0], p[1]), a, p[2]):
                continue
            for c in list(spot(cu, q[0], q[1], vd / 2))[:6]:
                if c != (q[0], q[1]) and not cu.free_stub((q[0], q[1]), c, q[2]):
                    continue
                for mid in ([], [(a[0], c[1])], [(c[0], a[1])]):
                    path = [a] + mid + [c]
                    if all(cu.free_stub(s, e, pcbnew.B_Cu) for s, e in zip(path, path[1:])):
                        ok = (a, c, path)
                        break
                if ok:
                    break
            if ok:
                break
        sg.STUB = old
        if not ok:
            failed.append("%s (%.1f,%.1f)-(%.1f,%.1f)" % (net, p[0], p[1], q[0], q[1]))
            continue
        a, c, path = ok

        def add(item):
            b.Add(item)
            g.AddItem(item)
        for end, v in ((p, a), (q, c)):
            via = pcbnew.PCB_VIA(b)
            via.SetViaType(pcbnew.VIATYPE_THROUGH)
            via.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
            via.SetPosition(pcbnew.VECTOR2I(M(v[0]), M(v[1])))
            via.SetWidth(M(vd))
            via.SetDrill(M(dr))
            via.SetNet(ni)
            add(via)
            if v != (end[0], end[1]):
                t = pcbnew.PCB_TRACK(b)
                t.SetStart(pcbnew.VECTOR2I(M(end[0]), M(end[1])))
                t.SetEnd(pcbnew.VECTOR2I(M(v[0]), M(v[1])))
                t.SetWidth(M(w))
                t.SetLayer(end[2])
                t.SetNet(ni)
                add(t)
        for s, e in zip(path, path[1:]):
            t = pcbnew.PCB_TRACK(b)
            t.SetStart(pcbnew.VECTOR2I(M(s[0]), M(s[1])))
            t.SetEnd(pcbnew.VECTOR2I(M(e[0]), M(e[1])))
            t.SetWidth(M(w))
            t.SetLayer(pcbnew.B_Cu)
            t.SetNet(ni)
            add(t)
        done += 1
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    b.Save(str(pcb))
    print("gaps closed: %d; open: %d" % (done, len(failed)))
    for f in failed:
        print("  " + f)


if __name__ == "__main__":
    main()
