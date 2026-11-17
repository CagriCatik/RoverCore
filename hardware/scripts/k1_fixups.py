#!/usr/bin/env python3
"""Local fixes on K1 after autorouting (routing step 6, 2026-11-16). No new autorouting run.

Usage: <KiCad python> k1_fixups.py BOARD.kicad_pcb STEP [STEP ...]
Each step removes named copper (matched by net, layer and end points within 0.02 mm) and adds replacement copper
that is checked for 0.2 mm clearance and hole spacing (stitch_gnd_vias.Copper) before it is added; a step whose
new copper fails the check changes nothing. Added items go into group "k1_fixups". Zones are refilled afterwards.
The hand-routed groups (servo_trial_routing, input_logic_routing, servo_rail_routing) are never touched.
"""
from pathlib import Path
import math
import sys

import pcbnew

sys.path.insert(0, str(Path(__file__).resolve().parent))
import stitch_gnd_vias as sg  # noqa: E402

T, M = pcbnew.ToMM, pcbnew.FromMM
F, B = pcbnew.F_Cu, pcbnew.B_Cu
PROTECTED = {"servo_trial_routing", "input_logic_routing", "servo_rail_routing"}
VBAT, RUN, INH = "/Power/VBAT_PROT", "/ServoPower/RUN_SERVO", "/ServoPower/SERVO_RUN_INH"

# step: (remove list, add list). remove: ("T", net, layer, (x1, y1, x2, y2)) or ("V", net, (x, y)).
# add: (net, width, (via_d, drill), parts) with parts as in route_k1_links.py; "ignore_zones" optional.
STEPS = {
    # stray VBAT repair copper at R405/R414: a gap-link via sat in R414's SMD pad, an autorouted via ended outside
    # the B pour. R414 pad 1 and R405 pad 1 are joined on F and reach the B VBAT pour through one via.
    "vbat_r405": ([("V", VBAT, (41.25, 34.87)), ("V", VBAT, (39.57, 37.26)), ("V", VBAT, (41.25, 35.85)),
                   ("T", VBAT, B, (39.57, 37.26, 41.25, 34.87)), ("T", VBAT, B, (40.4, 37.6, 39.57, 37.26)),
                   ("T", VBAT, F, (41.25, 34.87, 41.25, 35.85))], []),
    # RUN: Q403 pin 3 is boxed in on F by the autorouted SERVO_RUN_INH route; via in the 0.93 mm gap right of the
    # pad, short B jog inside the VBAT B pour (it only notches the pour, the rest stays joined), via onto the RUN
    # trace at Q408 pin 3.
    "run_q403": ([], [(RUN, 0.2, (0.45, 0.25), [
        (F, [(38.91, 31.75), (40.1, 31.75)]), ("via", (40.1, 31.75)),
        (B, [(40.1, 31.75), (40.1, 34.4), (39.6, 34.9), (39.6, 35.84)]), ("via", (39.6, 35.84))],
        ("in_vbat_prot_b",))]),
    # VBAT_PROT: R405's island (pad 1, via, B stub) to R414 pad 1 (main VBAT_PROT island) with one via.
    # RUN_SERVO, take back the pre-route of k1_links: it ran 4 mm inside the F VBAT_PROT pour (U401 -> Q403) and
    # split in_vbat_prot_f into two islands (113 mm2 -> 72 + 36 mm2). Replacement in "run_reroute" (added below).
    "run_unroute": ([("V", RUN, (43.0, 21.0)), ("T", RUN, B, (39.95, 19.0, 39.95, 20.6)),
                     ("T", RUN, B, (39.95, 20.6, 43.0, 20.6)), ("T", RUN, B, (43.0, 20.6, 43.0, 21.0)),
                     ("T", RUN, F, (43.0, 21.0, 43.0, 28.0)), ("T", RUN, F, (43.0, 28.0, 40.3, 28.0)),
                     ("T", RUN, F, (40.3, 28.0, 39.3, 29.0)), ("T", RUN, F, (39.3, 29.0, 39.3, 31.0)),
                     ("T", RUN, F, (39.3, 31.0, 38.91, 31.45)), ("T", RUN, F, (38.91, 31.74, 38.91, 31.45))], []),
    # RUN_SERVO replacement: the hand-routed VFB_TAP (B, y 28.3) lies under the whole F VBAT band, so RUN cannot cross
    # the band on B. It leaves U401 on B under the servo VBAT column (corridor between servo_vbat_b and VFB_TAP), hops
    # over VFB_TAP on F east of the band, runs down on B along the east edge of the B VBAT pour and joins the RUN
    # network at C420 (RUN filter). Both VBAT pours stay whole; 3 vias. Found with the grid search on the copper.
    "run_reroute": ([], [(RUN, 0.2, (0.45, 0.25), [
        (B, [(39.95, 19.0), (40.55, 19.6), (41.4, 19.6), (45.2, 23.4), (46.0, 23.6), (48.6, 26.2), (49.4, 26.2),
             (51.0, 27.8), (58.8, 27.8)]), ("via", (58.8, 27.8)),
        (F, [(58.8, 27.8), (58.0, 28.6), (56.4, 28.6), (54.4, 30.6), (54.2, 30.6)]), ("via", (54.2, 30.6)),
        (B, [(54.2, 30.6), (53.9, 30.9), (53.9, 36.7), (53.6, 37.0), (51.0, 37.0), (50.6, 37.4), (50.0, 37.4),
             (49.4, 38.0), (48.8, 38.0)]), ("via", (48.8, 38.0)),
        (F, [(48.8, 38.0), (47.7, 38.95)])])]),
    # VBAT_PROT stitching at Q101 (current check, current_map.py vbat): the B VBAT pour was fed from Q101 only through
    # a 0.5-0.6 mm neck of the F pour to the D101 vias (estimated 9 A/mm there). Six vias 0.8/0.4 mm along the bottom
    # edge of the F band, inside both pours and south of the hand-routed VFB_TAP (B, y 28.3).
    "vbat_stitch": ([], [(VBAT, 0.4, (0.8, 0.4), [("via", (x, 29.55)) for x in (36.4, 37.5, 38.6, 39.7, 40.8, 41.9)])]),
    "vbat_r414": ([], [(VBAT, 0.4, (0.6, 0.3), [
        ("via", (40.4, 35.0)), (F, [(40.4, 35.0), (41.25, 34.87)])])]),
    # GND of R407 pad 2 / Q407 pin 2 lies above the B VBAT pour: one GND via on the existing trace (the pour leaves
    # a clearance ring around it; the plane connection goes to In1/In2).
    "gnd_r407": ([], [("GND", 0.2, (0.45, 0.25), [("via", (46.55, 33.9))], ("in_vbat_prot_b",))]),
    # IMU_INT1 clearance at DevKit pin 12: the autorouted diagonal cut the pad corner. Replaced by a right angle at
    # the same 0.17 mm pad distance the trace already keeps along the pin row (board rule 0.15 mm).
    # ACT_ARMED_FB leaves pin 11 straight east instead of diagonally, which frees the corner for IMU_INT1.
    "imu_int1": ([("T", "IMU_INT1", B, (126.62, 29.80, 126.03, 29.21)), ("T", "IMU_INT1", B, (126.62, 38.80, 126.62, 29.80)),
                  ("T", "/Controller/ACT_ARMED_FB", B, (127.42, 29.86, 125.50, 27.94))],
                 [("/Controller/ACT_ARMED_FB", 0.2, (0.45, 0.25), [(B, [(125.50, 27.94), (127.42, 27.94), (127.42, 29.86)])],
                   (), 0.15),
                  ("IMU_INT1", 0.2, (0.45, 0.25), [(B, [(126.62, 38.80), (126.62, 29.21), (126.03, 29.21)])], (), 0.15)]),
    # +V_SERVO branch (Q405 pin 2, R418 pin 1, measurement/discharge parts, mA only -> 0.25 mm): the autorouted island
    # already ends in a via at (74.91, 34.58). From there on B east below the VSERVO_SW_G via, north past the end of
    # the feedback trace and into the B rail pour south of RS402 (not to the INA240 Kelvin tie NT405).
    "vservo_branch": ([], [("+V_SERVO", 0.25, (0.45, 0.25), [
        (B, [(74.91, 34.58), (78.3, 34.58), (78.3, 33.35), (82.6, 33.35), (82.6, 27.3), (85.4, 26.7)])])]),
    # VBAT_PROT to the lower half (R520 -> LOCK_SUP, R508/Q505 VBAT_SW switch, R515 loss-sense divider; all mA, the
    # 0.4 mm power width is kept): from the south edge of the B VBAT pour, one F hop over the autorouted B diagonal
    # (62.1,30.2)-(47.1,45.2) that fences the pour in, then on B straight south in the free corridor x 55.4-58.6 to
    # the start of the autorouted lower VBAT_PROT trace at R520 (via onto its F end point). Path found with a grid
    # search on the actual copper, 3 vias.
    "vbat_lower": ([], [(VBAT, 0.4, (0.6, 0.3), [
        (B, [(53.2, 35.2), (53.2, 36.2)]), ("via", (53.2, 36.2)),
        (F, [(53.2, 36.2), (55.4, 38.4)]), ("via", (55.4, 38.4)),
        (B, [(55.4, 38.4), (55.4, 43.8), (55.8, 44.2), (55.8, 62.0), (58.6, 64.8), (58.6, 72.0), (60.39, 74.98)]),
        ("via", (60.39, 74.98))])]),
    # SERVO_PWR_EN: DevKit pin 7 (GPIO) to the Q404/R415 end of the servo enable, 0.2 mm signal. F along y 29.2 north
    # of the servo regulator's feedback/sense parts, B along the south edge of the rail pour and above the two sense
    # traces, F again into pin 7 (west of the ACT_OE_N via). Found with the grid search on the actual copper; the
    # passage between R221's pads was blocked in the search on purpose. 2 vias.
    "servo_pwr_en": ([], [("SERVO_PWR_EN", 0.2, (0.45, 0.25), [
        (F, [(49.39, 31.17), (54.4, 31.17), (56.4, 29.2), (83.2, 29.2)]), ("via", (83.2, 29.2)),
        (B, [(83.2, 29.2), (83.8, 28.6), (83.8, 28.0), (84.2, 27.6), (94.8, 27.6), (99.8, 22.6), (116.2, 22.6),
             (118.8, 20.0)]), ("via", (118.8, 20.0)),
        (F, [(118.8, 20.0), (122.2, 20.0), (123.4, 19.0), (124.0, 18.4), (125.5, 17.78)])])]),
}


def match_track(t, net, layer, xy):
    if t.GetClass() != "PCB_TRACK" or t.GetNetname() != net or t.GetLayer() != layer:
        return False
    a = (T(t.GetStart().x), T(t.GetStart().y), T(t.GetEnd().x), T(t.GetEnd().y))
    fwd = max(abs(a[i] - xy[i]) for i in range(4))
    rev = max(abs(a[i] - xy[(i + 2) % 4]) for i in range(4))
    return min(fwd, rev) < 0.02


def remove_all(b, specs):
    """Resolve every spec against one snapshot of the tracks, then remove (the KiCad 10 bindings return a broken
    track list after a removal, so nothing is looked up after the first one)."""
    tracks = list(b.GetTracks())
    hits, missing = [], []
    for spec in specs:
        found = None
        for t in tracks:
            if spec[0] == "V" and t.GetClass() == "PCB_VIA" and t.GetNetname() == spec[1]:
                p = t.GetPosition()
                if math.hypot(T(p.x) - spec[2][0], T(p.y) - spec[2][1]) < 0.02:
                    found = t
            elif spec[0] == "T" and match_track(t, spec[1], spec[2], spec[3]):
                found = t
            if found:
                break
        if found is None:
            missing.append(spec)
            continue
        g = found.GetParentGroup()
        if g and g.GetName() in PROTECTED:
            raise SystemExit("ABORTED: %s belongs to the protected group %s" % (spec, g.GetName()))
        hits.append(found)
    for t in hits:
        g = t.GetParentGroup()
        if g:
            g.RemoveItem(t)
        b.Remove(t)
    return len(hits), missing, tracks  # keep the wrappers alive until the board is saved (bindings crash otherwise)


def check(b, net, w, vd, parts, ignore_zones=()):
    cu = sg.Copper(b, b.FindNet(net).GetNetCode())
    cu.zones = [z for z in cu.zones if z.GetZoneName() not in ignore_zones]
    sg.STUB = w
    bad = []
    for kind, data in parts:
        if kind == "via":
            if not cu.free_via(data[0], data[1], vd / 2):
                bad.append("via %s" % (data,))
        else:
            for s, e in zip(data, data[1:]):
                if not cu.free_stub(s, e, kind):
                    bad.append("%s %s-%s" % ("F" if kind == F else "B", s, e))
    return bad


def add(b, g, net, w, vd, dr, parts):
    ni = b.FindNet(net)
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


def main():
    pcb = Path(sys.argv[1])
    if list(pcb.parent.glob("~*.lck")) + list(pcb.parent.glob("*.lck")):
        raise SystemExit("ABORTED: KiCad lock files present")
    args = sys.argv[2:]
    if "--phase" in args:
        k = args.index("--phase")
        args = args[:k] + args[k + 2:]
    steps = [s for s in args if not s.startswith("--")]
    if "--phase" not in sys.argv:  # the bindings break after a removal or a second load: one process per phase
        import subprocess
        for ph in ("remove", "add"):
            r = subprocess.run([sys.executable, __file__, str(pcb)] + steps + ["--phase", ph], capture_output=True,
                               text=True)
            out = "\n".join(l for l in (r.stdout + r.stderr).splitlines() if "stdpbase" not in l and "Debug:" not in l)
            print(out)
            if r.returncode:
                raise SystemExit(r.returncode)
        return
    phase = sys.argv[sys.argv.index("--phase") + 1]
    b = pcbnew.LoadBoard(str(pcb))
    if phase == "remove":
        specs = [r for s in steps for r in STEPS[s][0]]
        n, missing, _keep = remove_all(b, specs)
        if missing:
            print("not found (already removed?): %s" % missing)
        pcbnew.ZONE_FILLER(b).Fill(b.Zones())
        b.Save(str(pcb))
        print("steps %s: removed %d items" % (",".join(steps), n))
        return
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    g = next((x for x in b.Groups() if x.GetName() == "k1_fixups"), None)
    if g is None:
        g = pcbnew.PCB_GROUP(b)
        g.SetName("k1_fixups")
        b.Add(g)
    added = 0
    for s in steps:
        for item in STEPS[s][1]:
            net, w, (vd, dr), parts = item[:4]
            ign = item[4] if len(item) > 4 else ()
            sg.CLR = item[5] if len(item) > 5 else 0.2
            bad = check(b, net, w, vd, parts, ign)
            if bad:
                raise SystemExit("ABORTED %s (%s), additions not written (removals are): %s" % (s, net, "; ".join(bad)))
            add(b, g, net, w, vd, dr, parts)
            added += 1
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    b.Save(str(pcb))
    print("steps %s: added %d links" % (",".join(steps), added))


if __name__ == "__main__":
    main()
