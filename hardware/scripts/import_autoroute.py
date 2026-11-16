#!/usr/bin/env python3
"""Import a Freerouting session (.ses) into a board and keep the new copper apart (routing step 4, K1).

Usage: <KiCad python> import_autoroute.py BOARD.kicad_pcb ROUTED.ses [--group NAME]
KiCad's SES import replaces all tracks. To keep the existing, hand-routed groups untouched, the session is imported
into a scratch copy; only tracks and vias that do not exist in the board already (same layer, net, width and end
points / position) are then added to the board, into the group (default "autoroute_k1"). Zones are refilled.
Refuses to run while KiCad lock files exist or when the group exists.
"""
from pathlib import Path
import shutil
import sys
import tempfile

import pcbnew


def sig(t):
    if t.GetClass() == "PCB_VIA":
        p = t.GetPosition()
        return ("V", t.GetNetname(), round(p.x, -3), round(p.y, -3), t.GetWidth(pcbnew.F_Cu), t.GetDrill())
    a, b = sorted([(t.GetStart().x, t.GetStart().y), (t.GetEnd().x, t.GetEnd().y)])
    return ("T", t.GetNetname(), t.GetLayer(), t.GetWidth(), tuple(round(v, -3) for v in a + b))


def main():
    pcb, ses = Path(sys.argv[1]), Path(sys.argv[2])
    name = sys.argv[sys.argv.index("--group") + 1] if "--group" in sys.argv else "autoroute_k1"
    if list(pcb.parent.glob("~*.lck")) + list(pcb.parent.glob("*.lck")):
        raise SystemExit("ABORTED: KiCad lock files present")
    b = pcbnew.LoadBoard(str(pcb))
    if any(g.GetName() == name for g in b.Groups()):
        raise SystemExit("ABORTED: group %s exists already" % name)
    have = {sig(t) for t in b.GetTracks()}
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d) / pcb.name
        shutil.copy(pcb, tmp)
        s = pcbnew.LoadBoard(str(tmp))
        if not pcbnew.ImportSpecctraSES(s, str(ses)):
            raise SystemExit("ABORTED: SES import failed")
        new = [t for t in s.GetTracks() if sig(t) not in have]
        g = pcbnew.PCB_GROUP(b)
        g.SetName(name)
        b.Add(g)
        nt = nv = 0
        for t in new:
            net = b.FindNet(t.GetNetname())
            if t.GetClass() == "PCB_VIA":
                v = pcbnew.PCB_VIA(b)
                v.SetViaType(t.GetViaType())
                v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
                v.SetPosition(t.GetPosition())
                v.SetWidth(t.GetWidth(pcbnew.F_Cu))
                v.SetDrill(t.GetDrill())
                v.SetNet(net)
                b.Add(v)
                g.AddItem(v)
                nv += 1
            else:
                n = pcbnew.PCB_TRACK(b)
                n.SetStart(t.GetStart())
                n.SetEnd(t.GetEnd())
                n.SetLayer(t.GetLayer())
                n.SetWidth(t.GetWidth())
                n.SetNet(net)
                b.Add(n)
                g.AddItem(n)
                nt += 1
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    b.Save(str(pcb))
    print("added %d tracks, %d vias into group %s (existing copper unchanged)" % (nt, nv, name))


if __name__ == "__main__":
    main()
