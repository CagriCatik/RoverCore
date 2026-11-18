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
    # +5V trunk (current check, current_map.py 5v): pour at C304-C307 -> via -> B diagonal -> via -> F -> via at
    # (50.34, 63.6), where the branches to D501/DevKit, U601-U603 and the buzzer leave. It carries up to 1.5 A (switch
    # limits at maximum, estimate) in 0.4 mm copper (3.5-4.8 A/mm) and single 0.3 mm vias of about 1.06 A. Same path
    # at 1.0 mm, plus a second via next to each of the three trunk vias.
    "5v_trunk": ([("T", "+5V", B, (32.4, 58.0, 39.39, 64.75)),
                   ("T", "+5V", F, (39.39, 64.75, 41.42, 64.75)),
                   ("T", "+5V", F, (41.42, 64.75, 41.64, 64.97)),
                   ("T", "+5V", F, (41.64, 64.97, 46.28, 64.97)),
                   ("T", "+5V", F, (46.28, 64.97, 47.81, 64.97)),
                   ("T", "+5V", F, (47.81, 64.97, 48.04, 65.19)),
                   ("T", "+5V", F, (48.04, 65.19, 49.63, 63.6)),
                   ("T", "+5V", F, (49.63, 63.6, 50.34, 63.6))],
                 [("+5V", 1.0, (0.6, 0.3), [(B, [(32.4, 58.0), (39.39, 64.75)]),
                                            (F, [(39.39, 64.75), (41.42, 64.75), (41.64, 64.97), (46.28, 64.97), (47.81, 64.97), (48.04, 65.19), (49.63, 63.6), (50.34, 63.6)])]),
                  ("+5V", 0.6, (0.6, 0.3), [("via", (31.5, 58.0)), (B, [(31.5, 58.0), (32.4, 58.0)]),
                                            (F, [(31.5, 58.0), (32.4, 58.0)]),
                                            ("via", (40.29, 64.75)), (B, [(39.39, 64.75), (40.29, 64.75)]),
                                            ("via", (49.44, 63.6)), (B, [(49.44, 63.6), (50.34, 63.6)])])]),
    # +5V branch to D501/DevKit (current check, current_map.py 5v): 130 mm and 7 layer changes from the trunk to
    # D501 at 0.55 A, 108 mV copper drop where document 3.11 assumes 50 mV for socket + traces. Every segment widened
    # to the largest of 0.8/0.6/0.5 mm that keeps 0.2 mm clearance; two B segments near (97, 45) stay at 0.4 mm.
    # The detour itself remains (a reroute would touch the other +5V feeds along the path).
    "5v_devkit_branch": ([("T", "+5V", B, (50.34, 63.6, 53.93, 67.19)),
                          ("T", "+5V", B, (53.93, 67.19, 53.93, 68.75)),
                          ("T", "+5V", F, (79.95, 68.75, 53.93, 68.75)),
                          ("T", "+5V", B, (79.95, 68.75, 81.32, 67.38)),
                          ("T", "+5V", B, (81.32, 67.38, 81.32, 57.48)),
                          ("T", "+5V", F, (83.03, 55.77, 81.32, 57.48)),
                          ("T", "+5V", F, (95.5, 55.77, 83.03, 55.77)),
                          ("T", "+5V", B, (100.05, 38.92, 99.73, 39.23)),
                          ("T", "+5V", F, (97.14, 36.0, 100.05, 38.92)),
                          ("T", "+5V", F, (97.14, 32.9, 97.14, 36.0)),
                          ("T", "+5V", F, (98.03, 32.9, 97.14, 32.9)),
                          ("T", "+5V", F, (99.1, 31.83, 98.03, 32.9)),
                          ("T", "+5V", F, (100.18, 32.9, 99.1, 31.83)),
                          ("T", "+5V", F, (102.84, 32.9, 100.18, 32.9)),
                          ("T", "+5V", F, (108.54, 32.9, 102.84, 32.9)),
                          ("T", "+5V", F, (109.43, 32.9, 108.54, 32.9)),
                          ("T", "+5V", F, (110.5, 31.83, 109.43, 32.9)),
                          ("T", "+5V", F, (111.57, 32.9, 110.5, 31.83)),
                          ("T", "+5V", F, (114.24, 32.9, 111.57, 32.9)),
                          ("T", "+5V", F, (114.24, 32.9, 117.54, 32.9)),
                          ("T", "+5V", F, (117.54, 32.9, 117.54, 33.12)),
                          ("T", "+5V", B, (117.54, 33.12, 117.66, 33.25)),
                          ("T", "+5V", B, (117.66, 33.25, 117.66, 53.34)),
                          ("T", "+5V", F, (119.2, 53.34, 117.66, 53.34))],
                         [("+5V", 0.8, (0.6, 0.3), [(B, [(50.34, 63.6), (53.93, 67.19)]), (B, [(79.95, 68.75), (81.32, 67.38)]), (F, [(95.5, 55.77), (83.03, 55.77)]), (F, [(98.03, 32.9), (97.14, 32.9)]), (F, [(99.1, 31.83), (98.03, 32.9)]), (F, [(102.84, 32.9), (100.18, 32.9)]), (F, [(108.54, 32.9), (102.84, 32.9)]), (F, [(109.43, 32.9), (108.54, 32.9)]), (F, [(110.5, 31.83), (109.43, 32.9)]), (F, [(114.24, 32.9), (111.57, 32.9)]), (F, [(114.24, 32.9), (117.54, 32.9)]), (F, [(117.54, 32.9), (117.54, 33.12)]), (F, [(119.2, 53.34), (117.66, 53.34)])]),
                          ("+5V", 0.6, (0.6, 0.3), [(B, [(53.93, 67.19), (53.93, 68.75)]), (F, [(79.95, 68.75), (53.93, 68.75)]), (B, [(81.32, 67.38), (81.32, 57.48)]), (F, [(83.03, 55.77), (81.32, 57.48)]), (B, [(100.05, 38.92), (99.73, 39.23)]), (F, [(97.14, 32.9), (97.14, 36.0)]), (B, [(117.54, 33.12), (117.66, 33.25)])]),
                          ("+5V", 0.5, (0.6, 0.3), [(F, [(97.14, 36.0), (100.05, 38.92)]), (F, [(100.18, 32.9), (99.1, 31.83)]), (F, [(111.57, 32.9), (110.5, 31.83)]), (B, [(117.66, 33.25), (117.66, 53.34)])])]),
    # +5V to D501, shorter (review 2026-11-18): D501 was fed over the northern loop (up to y 33 and back down on B to
    # y 53, 2 vias). The loop keeps feeding D201-D205, R211-R215 and U201; D501 gets a direct link from the via at
    # (95.5, 55.77): B, one via, F along y 54.6-55.6 to the anode (0.8 mm). The old descent is removed.
    "5v_devkit_direct": ([("T", "+5V", F, (117.54, 32.9, 117.54, 33.12)), ("V", "+5V", (117.54, 33.12)),
                          ("T", "+5V", B, (117.54, 33.12, 117.66, 33.25)), ("T", "+5V", B, (117.66, 33.25, 117.66, 53.34)),
                          ("V", "+5V", (117.66, 53.34)), ("T", "+5V", F, (119.2, 53.34, 117.66, 53.34))],
                         [("+5V", 0.8, (0.6, 0.3), [
                             (B, [(95.5, 55.77), (98.2, 55.77), (99.4, 54.6)]), ("via", (99.4, 54.6)),
                             (F, [(99.4, 54.6), (103.8, 54.6), (104.6, 55.4), (113.2, 55.4)])]),
                          # 0.6 mm past the J115 mounting hole (hole clearance 0.25 mm, 0.31 mm kept)
                          ("+5V", 0.6, (0.6, 0.3), [(F, [(113.2, 55.4), (113.4, 55.6), (116.8, 55.6), (118.8, 53.6),
                                                         (119.2, 53.34)])])]),
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


K1_EDGE_TOP_LEFT = (-0.05, -0.05)  # outline corner the coordinates below were written for (K1, 150 x 85 mm)


def board_offset(b):
    """The coordinates in STEPS refer to K1 with its outline corner at K1_EDGE_TOP_LEFT. If the whole board was
    moved in the editor (2026-11-17: by +62.25/+50.5 mm), every coordinate is shifted by the same offset."""
    e = b.GetBoardEdgesBoundingBox()
    return T(e.GetLeft()) - K1_EDGE_TOP_LEFT[0], T(e.GetTop()) - K1_EDGE_TOP_LEFT[1]


def shift_specs(specs, o):
    out = []
    for s in specs:
        if s[0] == "V":
            out.append((s[0], s[1], (s[2][0] + o[0], s[2][1] + o[1])))
        else:
            xy = s[3]
            out.append((s[0], s[1], s[2], (xy[0] + o[0], xy[1] + o[1], xy[2] + o[0], xy[3] + o[1])))
    return out


def shift_parts(parts, o):
    out = []
    for kind, data in parts:
        if kind == "via":
            out.append((kind, (data[0] + o[0], data[1] + o[1])))
        else:
            out.append((kind, [(x + o[0], y + o[1]) for x, y in data]))
    return out


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
        specs = shift_specs([r for s in steps for r in STEPS[s][0]], board_offset(b))
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
            parts = shift_parts(parts, board_offset(b))
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
