#!/usr/bin/env python3
"""Trial routing of the LTC7803 servo regulator (ServoPower), applied once to RoverCore.kicad_pcb.

Scope (owner instruction 2026-11-16): input loop incl. GND return, gate drives incl. their returns, bootstrap,
Kelvin sense and feedback, plus the power pours the regulator needs (SW, ISNS_PWR, VSERVO_REG). Everything else
stays unrouted. Stackup intent (docs/vcu/rev1-platzierung.md, section "Lagenaufbau"):
  F.Cu  parts, power pours, short critical routing; reference In1 (0.1 mm prepreg)
  In1   GND, solid
  In2   GND, solid (reference for B.Cu, 0.1 mm prepreg)
  B.Cu  BG, sense pair, feedback, EXTVCC; reference In2
All items are put into the group "servo_trial_routing" so they can be selected or removed as one block.
The script refuses to run when that group already exists, when KiCad lock files exist, or when any
track/via/zone is already on the board for the nets it routes (manual work is never overwritten).
It also applies the placement changes the routing needs (D401 to B.Cu, RS402 turned, its Kelvin ties moved)
and reports them. Run with the KiCad Python; --board for a copy, --dry-run to check without saving.
"""
from pathlib import Path
import argparse
import sys

import pcbnew

ROOT = Path(__file__).resolve().parents[2]
MM = pcbnew.FromMM
GROUP = "servo_trial_routing"


class Abort(Exception):
    pass


def V(x, y):
    return pcbnew.VECTOR2I(MM(x), MM(y))


class Router:
    def __init__(self, board):
        self.b = board
        self.items = []
        self.fps = {f.GetReference(): f for f in board.GetFootprints()}

    def net(self, name):
        n = self.b.FindNet(name)
        if n is None or n.GetNetCode() <= 0:
            raise Abort("net not found: %s" % name)
        return n

    def pad(self, ref, num, i=0):
        pads = [p for p in self.fps[ref].Pads() if p.GetNumber() == num]
        if not pads:
            raise Abort("pad %s.%s not found" % (ref, num))
        c = pads[i].GetPosition()
        return pcbnew.ToMM(c.x), pcbnew.ToMM(c.y)

    def track(self, net, layer, width, pts):
        n = self.net(net)
        pts = [self.pad(*p) if isinstance(p[0], str) else p for p in pts]
        for a, b in zip(pts, pts[1:]):
            t = pcbnew.PCB_TRACK(self.b)
            t.SetStart(V(*a))
            t.SetEnd(V(*b))
            t.SetWidth(MM(width))
            t.SetLayer(layer)
            t.SetNet(n)
            self.b.Add(t)
            self.items.append(t)

    def via(self, net, x, y, size=0.45, drill=0.25):
        v = pcbnew.PCB_VIA(self.b)
        v.SetViaType(pcbnew.VIATYPE_THROUGH)
        v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
        v.SetPosition(V(x, y))
        v.SetWidth(MM(size))
        v.SetDrill(MM(drill))
        v.SetNet(self.net(net))
        self.b.Add(v)
        self.items.append(v)

    def zone(self, name, net, layer, pts, clearance=0.2, priority=1, thermal=False):
        z = pcbnew.ZONE(self.b)
        z.SetZoneName(name)
        z.SetLayer(layer)
        z.SetNet(self.net(net))
        ol = z.Outline()
        ol.NewOutline()
        for x, y in pts:
            ol.Append(MM(x), MM(y))
        z.SetLocalClearance(MM(clearance))
        z.SetMinThickness(MM(0.2))
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL if thermal else pcbnew.ZONE_CONNECTION_FULL)
        z.SetAssignedPriority(priority)
        self.b.Add(z)
        self.items.append(z)


def place(r, log):
    """Placement changes the routing needs (no circuit change)."""
    fps = r.fps
    # D401 (INTVCC -> BOOST) to the bottom side, under the BOOST / INTVCC escape: on the top side it sat inside the
    # loop pin16 (SW) - C411 - pin14 (BOOST) together with the TG escape and had no planar connection.
    d = fps["D401"]
    if d.GetLayer() != pcbnew.B_Cu:
        d.Flip(d.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
    d.SetPosition(V(47.2, 18.35))
    for deg in (0, 90, 180, 270):
        d.SetOrientationDegrees(deg)
        (x1, y1), (x2, y2) = r.pad("D401", "1"), r.pad("D401", "2")
        if abs(x1 - x2) < 0.01 and y1 < y2:
            break
    else:
        raise Abort("no D401 orientation with pad 1 above pad 2")
    log.append("D401 -> B.Cu (47.2, 18.35) r%g, pad1 BOOST %s, pad2 INTVCC %s"
               % (d.GetOrientationDegrees(), r.pad("D401", "1"), r.pad("D401", "2")))
    # RS402 output shunt: pad 1 (VSERVO_REG) towards the output caps' west strip, pad 2 (+V_SERVO) east towards
    # J102-J105. Before, pad 2 lay between the caps and pad 1, so the regulator current had to pass the output pad.
    s = fps["RS402"]
    s.SetPosition(V(84.5, 24.5))
    s.SetOrientationDegrees(0)
    if not r.pad("RS402", "1")[0] < r.pad("RS402", "2")[0]:
        raise Abort("RS402 pad order unexpected")
    log.append("RS402 -> (84.5, 24.5) r0, pad1 %s, pad2 %s" % (r.pad("RS402", "1"), r.pad("RS402", "2")))
    # Kelvin ties at the current-free bottom ends of the shunt pads (current enters and leaves at the top).
    for ref, pos, deg in (("NT403", (82.45, 27.0), 180), ("NT404", (83.5, 27.95), -90), ("NT405", (85.5, 27.95), -90)):
        fps[ref].SetPosition(V(*pos))
        fps[ref].SetOrientationDegrees(deg)
        log.append("%s -> %s r%g, pad1 %s" % (ref, pos, deg, r.pad(ref, "1")))
    # C405 (100 nF HF input cap) 0.65 mm closer to the drain tabs of Q401 and the source pins of Q402
    # (courtyards just clear), which shortens the high-frequency part of the input loop.
    fps["C405"].SetPosition(V(54.0, 18.65))
    log.append("C405 -> (54.0, 18.65), pads %s / %s" % (r.pad("C405", "1"), r.pad("C405", "2")))
    # U401 exposed-pad vias solid to the GND planes (heat path); the planes keep thermal reliefs elsewhere.
    fps["U401"].SetLocalZoneConnection(pcbnew.ZONE_CONNECTION_FULL)
    log.append("U401 zone connection -> solid")


def route(r):
    F, B, I1, I2 = pcbnew.F_Cu, pcbnew.B_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu
    SP = "/ServoPower/"
    # ---- planes (stackup intent): In1 and In2 GND over the whole board
    outline = [(0, 0), (150, 0), (150, 100), (0, 100)]
    r.zone("gnd_in1", "GND", I1, outline, 0.2, 0, thermal=True)
    r.zone("gnd_in2", "GND", I2, outline, 0.2, 0, thermal=True)

    # ---- input loop: Q401 drain - C405 / C401 / C402 (top), C403 / C404 (bottom) - Q402 source
    r.zone("servo_vbat_f", "/Power/VBAT_PROT", F, [(49.75, 12.75), (53.75, 12.75), (53.75, 27.6), (49.75, 27.6)], 0.25, 2)
    r.zone("servo_gnd_loop_f", "GND", F, [(54.2, 16.2), (58.3, 16.2), (58.3, 27.6), (54.2, 27.6)], 0.2, 1)
    r.zone("servo_vbat_b", "/Power/VBAT_PROT", B, [(50.6, 20.4), (53.4, 20.4), (53.4, 27.0), (50.6, 27.0)], 0.25, 2)
    r.zone("servo_gnd_loop_b", "GND", B, [(54.6, 20.4), (57.6, 20.4), (57.6, 27.0), (54.6, 27.0)], 0.2, 1)
    for y in (21.2, 22.6, 24.5, 25.9):  # bottom caps: VBAT vias west of pad 1, GND vias east of pad 2
        r.via("/Power/VBAT_PROT", 51.2, y, 0.8, 0.4)
        r.via("GND", 56.8, y, 0.8, 0.4)
    for x in (55.9, 56.9, 57.9):  # Q402 source / C405 GND to In1 and In2, directly below the source pins
        r.via("GND", x, 18.6, 0.8, 0.4)

    # ---- switch node, inductor, current shunt, output caps
    r.zone("servo_sw_f", SP + "SW_SERVO", F,
           [(49.85, 8.0), (64.4, 8.0), (64.4, 15.3), (54.6, 15.3), (54.6, 11.55), (49.85, 11.55)], 0.3, 2)
    r.zone("servo_isns_f", SP + "ISNS_PWR", F, [(68.4, 7.0), (74.75, 7.0), (74.75, 12.3), (68.4, 12.3)], 0.25, 2)
    r.zone("servo_vreg_f", SP + "VSERVO_REG", F,
           [(77.0, 7.3), (92.0, 7.3), (92.0, 13.2), (79.4, 13.2), (79.4, 18.6), (89.6, 18.6), (89.6, 21.4),
            (84.0, 21.4), (84.0, 24.5), (82.0, 24.5), (82.0, 21.4), (78.0, 21.4), (78.0, 12.3), (77.0, 12.3)], 0.25, 2)
    r.zone("servo_gnd_out_top_f", "GND", F, [(77.0, 0.6), (92.0, 0.6), (92.0, 6.9), (77.0, 6.9)], 0.2, 1)
    r.zone("servo_gnd_out_pocket_f", "GND", F, [(79.9, 13.6), (92.0, 13.6), (92.0, 18.2), (79.9, 18.2)], 0.2, 1)
    for x in (85.0, 86.5, 88.0):
        for y in (2.2, 5.2):
            r.via("GND", x, y, 0.8, 0.4)
    for x in (81.0, 84.5, 88.0):
        r.via("GND", x, 14.6, 0.8, 0.4)

    # ---- gate drive. TG with its return (SW from pin 16) as a pair on F to Q401 gate / source
    r.track(SP + "SW_SERVO", F, 0.3, [("U401", "16"), (45.6, 16.25), (45.6, 10.3), (50.365, 10.3), ("Q401", "3")])
    r.track(SP + "TG_SERVO", F, 0.3, [("U401", "15"), (46.1, 16.75), (46.1, 11.137), ("Q401", "4")])
    # bootstrap: BOOST pin 14 -> C411; C411 SW side -> Q401 source (strip between pin row and drain pad)
    r.track(SP + "BOOST_SERVO", F, 0.25, [("U401", "14"), (47.0, 17.25), ("C411", "1")])
    r.track(SP + "SW_SERVO", F, 0.4, [("C411", "2"), (47.6, 13.225), (48.6, 12.2), (50.365, 12.2), (50.365, 11.137)])
    # boost diode D401 on B: BOOST via -> D401 pad 1, D401 pad 2 -> INTVCC via -> C413
    r.via(SP + "BOOST_SERVO", 47.0, 16.3)
    r.track(SP + "BOOST_SERVO", B, 0.25, [(47.0, 16.3), ("D401", "1")])
    r.track(SP + "INTVCC_SERVO", B, 0.3, [("D401", "2"), (47.4, 20.5)])
    r.via(SP + "INTVCC_SERVO", 47.4, 20.5)
    r.track(SP + "INTVCC_SERVO", F, 0.3, [(47.4, 20.5), ("C413", "1")])
    # INTVCC pins 9/10 -> C412 -> C413
    r.track(SP + "INTVCC_SERVO", F, 0.3, [("U401", "10"), (45.75, 19.25), (45.75, 20.9)])
    r.track(SP + "INTVCC_SERVO", F, 0.3, [("U401", "9"), (45.75, 19.75)])
    r.track(SP + "INTVCC_SERVO", F, 0.3, [("C412", "1"), ("C413", "1")])
    # BG: F out of pin 13, via, B over In2 GND, via, F stub to Q402 gate. GND vias next to both BG vias.
    r.track(SP + "BG_SERVO", F, 0.3, [("U401", "13"), (49.3, 17.75)])
    r.via(SP + "BG_SERVO", 49.3, 17.75)
    r.track(SP + "BG_SERVO", B, 0.4, [(49.3, 17.75), (59.4, 17.75)])
    r.via(SP + "BG_SERVO", 59.4, 17.75)
    r.track(SP + "BG_SERVO", F, 0.3, [(59.4, 17.75), (58.905, 17.1), ("Q402", "4")])
    r.via("GND", 48.2, 19.6)
    # VIN (pin 12) into the VBAT pour; EXTVCC (pin 11) via B to the VSERVO_REG pour
    r.track("/Power/VBAT_PROT", F, 0.2, [("U401", "12"), (50.2, 18.25)])
    r.track(SP + "VSERVO_REG", F, 0.25, [("U401", "11"), (49.3, 18.75)])
    r.via(SP + "VSERVO_REG", 49.3, 18.75)
    r.track(SP + "VSERVO_REG", B, 0.3, [(49.3, 18.75), (50.15, 19.6), (79.2, 19.6), (80.0, 20.4)])
    r.via(SP + "VSERVO_REG", 80.0, 20.4)

    # ---- GND pins 7/8 to the exposed pad; small-signal GND vias
    r.track("GND", F, 0.3, [("U401", "7"), (42.4, 19.25)])
    r.track("GND", F, 0.25, [("U401", "8"), (41.6, 19.75), (41.6, 19.25)])
    for ref, (dx, dy) in (("C414", (0, -0.9)), ("R404", (0, 0.85)), ("C419", (0, 0.8)), ("C418", (0, 0.85)),
                          ("C412", (0, 0.85)), ("C413", (0, 0.85))):
        x, y = r.pad(ref, "2")
        r.via("GND", x + dx, y + dy)
        r.track("GND", F, 0.3, [(x, y), (x + dx, y + dy)])

    # ---- left side: soft-start, sense filter, feedback divider, compensation, RUN escape
    r.track(SP + "SS_SERVO", F, 0.2, [("U401", "1"), (40.0, 16.25), (40.0, 14.075), ("C414", "1")])
    r.track(SP + "SENSE_P", F, 0.2, [("U401", "2"), (39.2, 16.75), (39.2, 15.725), ("CF401", "1")])
    r.track(SP + "SENSE_P", F, 0.2, [("CF401", "1"), ("RF401", "2")])
    r.track(SP + "SENSE_N", F, 0.2, [("U401", "3"), ("CF401", "2")])
    r.track(SP + "VFB_SERVO", F, 0.2, [("U401", "4"), (38.9, 17.75), (38.9, 18.875), ("R404", "1")])
    r.track(SP + "VFB_SERVO", F, 0.2, [("R404", "1"), ("R403", "2")])
    r.track(SP + "ITH_SERVO", F, 0.2, [("U401", "5"), (39.45, 18.25), (39.45, 24.675), ("R413", "1")])
    r.track(SP + "ITH_SERVO", F, 0.2, [(39.45, 21.525), ("C419", "1")])
    r.track(SP + "ITH_RC", F, 0.2, [("R413", "2"), (39.0, 26.325), (39.0, 24.725), ("C418", "1")])
    r.track(SP + "RUN_SERVO", F, 0.2, [("U401", "6"), (40.1, 18.75), (39.95, 19.0)])
    r.via(SP + "RUN_SERVO", 39.95, 19.0)

    # ---- Kelvin sense RS401 -> RF401 / CF401: pair on B over In2 GND (P_K north, N south)
    r.track(SP + "SENSE_P_K", F, 0.2, [("NT401", "2"), (74.25, 14.8)])
    r.via(SP + "SENSE_P_K", 74.25, 14.8)
    r.track(SP + "SENSE_N", F, 0.2, [("NT402", "2"), (76.75, 14.8)])
    r.via(SP + "SENSE_N", 76.75, 14.8)
    r.track(SP + "SENSE_P_K", B, 0.2, [(74.25, 14.8), (74.25, 15.0), (34.5, 15.0), (34.5, 17.3)])
    r.track(SP + "SENSE_N", B, 0.2, [(76.75, 14.8), (76.75, 15.6), (36.85, 15.6), (36.85, 17.3)])
    r.via(SP + "SENSE_P_K", 34.5, 17.3)
    r.via(SP + "SENSE_N", 36.85, 17.3)
    r.track(SP + "SENSE_P_K", F, 0.2, [(34.5, 17.3), ("RF401", "1")])
    r.track(SP + "SENSE_N", F, 0.2, [(36.85, 17.3), ("CF401", "2")])

    # ---- feedback: VOUT tap NT403 (RS402 pad 1) -> R403 at the IC, on B over In2 GND
    r.track(SP + "VFB_TAP", F, 0.2, [("NT403", "2"), (81.4, 27.8)])
    r.via(SP + "VFB_TAP", 81.4, 27.8)
    r.track(SP + "VFB_TAP", B, 0.25, [(81.4, 27.8), (80.8, 28.4), (36.2, 28.4), (35.6, 27.8), (35.6, 21.5)])
    r.via(SP + "VFB_TAP", 35.6, 21.5)
    r.track(SP + "VFB_TAP", F, 0.2, [(35.6, 21.5), ("R403", "1")])
    # NT404 / NT405 sit on the shunt pads; their pad 2 (INA240 inputs) stays unrouted (not in this step).


ROUTED_NETS = ["/Power/VBAT_PROT", "GND", "/ServoPower/SW_SERVO", "/ServoPower/ISNS_PWR", "/ServoPower/VSERVO_REG",
               "/ServoPower/TG_SERVO", "/ServoPower/BG_SERVO", "/ServoPower/BOOST_SERVO",
               "/ServoPower/INTVCC_SERVO", "/ServoPower/SS_SERVO", "/ServoPower/SENSE_P", "/ServoPower/SENSE_N",
               "/ServoPower/SENSE_P_K", "/ServoPower/VFB_SERVO", "/ServoPower/VFB_TAP", "/ServoPower/ITH_SERVO",
               "/ServoPower/ITH_RC", "/ServoPower/RUN_SERVO"]


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
        if any(g.GetName() == GROUP for g in b.Groups()):
            raise Abort("group %s already exists; trial routing was applied before" % GROUP)
        codes = {b.FindNet(n).GetNetCode() for n in ROUTED_NETS if b.FindNet(n)}
        busy = [t for t in b.GetTracks() if t.GetNetCode() in codes] + \
               [z for z in b.Zones() if z.GetNetCode() in codes]
        if busy:
            raise Abort("%d tracks/vias/zones already exist on the routed nets; not overwriting manual work" % len(busy))
        r = Router(b)
        log = []
        place(r, log)
        route(r)
        g = pcbnew.PCB_GROUP(b)
        g.SetName(GROUP)
        b.Add(g)
        for it in r.items:
            g.AddItem(it)
        pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    except Abort as e:
        raise SystemExit("ABORTED, board not written: %s" % e)
    for line in log:
        print(line)
    n_t = sum(1 for i in r.items if i.GetClass() == "PCB_TRACK")
    n_v = sum(1 for i in r.items if i.GetClass() == "PCB_VIA")
    n_z = sum(1 for i in r.items if i.GetClass() == "ZONE")
    print("tracks %d, vias %d, zones %d" % (n_t, n_v, n_z))
    if a.dry_run:
        print("dry run, not saved")
        return
    b.Save(str(pcb))
    print("saved", pcb)


if __name__ == "__main__":
    sys.exit(main())
