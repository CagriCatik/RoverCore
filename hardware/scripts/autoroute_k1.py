#!/usr/bin/env python3
"""Routing pipeline for the rest of K1 (routing steps 4-5, 2026-11-16). Reproducible, one board at a time.

Usage: <KiCad python> autoroute_k1.py BOARD.kicad_pcb [--passes N]
1. route_k1_links.py: explicit links for the bottlenecks (RUN escape, VBAT_PROT to the RUN divider) first,
   so the autorouter routes around them.
2. Specctra DSN export with all existing copper locked (exported as fixed). The DSN is edited so that
   - In1.Cu and In2.Cu are power planes (no signal routing on the GND planes, stackup 3a),
   - every outer-layer pour is a keep-out (signals must not split the power pours).
3. Freerouting 2.4.1 (the jar of the installed KiCad Freerouting plugin), headless.
4. import_autoroute.py: only new copper, group autoroute_k1.
5. close_gaps.py: remaining non-GND gaps with short B links; stitch_gnd_vias.py: GND vias to the planes.
Work files go next to the board in a folder "<board>_autoroute". Refuses to run while KiCad lock files exist.
"""
from pathlib import Path
import re
import subprocess
import sys

import pcbnew

HERE = Path(__file__).resolve().parent
JAR = Path.home() / "Documents/KiCad/10.0/3rdparty/plugins/app_freerouting_kicad-plugin/jar/freerouting-2.4.1.jar"
T = pcbnew.ToMM


def run(args, **kw):
    r = subprocess.run(args, capture_output=True, text=True, **kw)
    out = "\n".join(l for l in (r.stdout + r.stderr).splitlines()
                    if not re.search(r"stdpbase|swig|Debug: Adding", l))
    if r.returncode:
        raise SystemExit("FAILED: %s\n%s" % (" ".join(map(str, args)), out[-1500:]))
    return out


def main():
    pcb = Path(sys.argv[1]).resolve()
    passes = sys.argv[sys.argv.index("--passes") + 1] if "--passes" in sys.argv else "60"
    if list(pcb.parent.glob("~*.lck")) + list(pcb.parent.glob("*.lck")):
        raise SystemExit("ABORTED: KiCad lock files present")
    work = pcb.parent / (pcb.stem + "_autoroute")
    work.mkdir(exist_ok=True)
    py = sys.executable
    print(run([py, str(HERE / "route_k1_links.py"), str(pcb)]))
    # 2. locked copy -> DSN
    b = pcbnew.LoadBoard(str(pcb))
    for t in b.GetTracks():
        t.SetLocked(True)
    ko = []
    for z in b.Zones():
        if z.GetZoneName() in ("gnd_in1", "gnd_in2"):
            continue
        for lay, name in ((pcbnew.F_Cu, "F.Cu"), (pcbnew.B_Cu, "B.Cu")):
            if not z.IsOnLayer(lay):
                continue
            ol = z.Outline().Outline(0)
            pts = ["%d %d" % (round(T(ol.CPoint(i).x) * 1000), -round(T(ol.CPoint(i).y) * 1000))
                   for i in range(ol.PointCount())]
            pts.append(pts[0])
            ko.append('    (keepout "" (polygon %s 0  %s))' % (name, " ".join(pts)))
    dsn = work / "board.dsn"
    if not pcbnew.ExportSpecctraDSN(b, str(dsn)):
        raise SystemExit("FAILED: DSN export")
    t = dsn.read_text()
    for lay in ("In1.Cu", "In2.Cu"):
        t = t.replace("(layer %s\n      (type signal)" % lay, "(layer %s\n      (type power)" % lay)
    i = t.index("    (boundary")
    t = t[:i] + "\n".join(ko) + "\n" + t[i:]
    dsn.write_text(t)
    # 3. Freerouting
    ses = work / "board.ses"
    if ses.exists():
        ses.unlink()
    log = run(["java", "-Djava.awt.headless=true", "-jar", str(JAR), "-de", str(dsn), "-do", str(ses), "-mp", passes,
               "-mt", "8", "--gui.enabled=false"])
    (work / "freerouting.log").write_text(log)
    summary = [l for l in log.splitlines() if "Optimization stage completed" in l or "finished with state" in l]
    print("\n".join(s[s.find("INFO") + 5:][:220] for s in summary))
    if not ses.exists():
        raise SystemExit("FAILED: no session written")
    # 4./5.
    print(run([py, str(HERE / "import_autoroute.py"), str(pcb), str(ses)]))
    print(run([py, str(HERE / "close_gaps.py"), str(pcb)]))
    print(run([py, str(HERE / "stitch_gnd_vias.py"), str(pcb)]))


if __name__ == "__main__":
    main()
