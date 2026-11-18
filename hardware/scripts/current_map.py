#!/usr/bin/env python3
"""DC current distribution in the actual copper of one net (routing review, 2026-11-16). ESTIMATE, not a measurement.

Usage: <KiCad python> current_map.py BOARD.kicad_pcb CASE OUTDIR [--grid 0.1] [--region X0 Y0 X1 Y1 (K1 coordinates)]
CASE is one of CASES below (net, layers, source terminal, sink terminals with load currents from the power budget).

Model: the net's copper (filled zones, tracks, pads, via rings) is rasterised per layer on a square grid; neighbouring
copper cells are joined by the sheet conductance of 35 um copper, vias and plated pad holes join the layers with the
barrel resistance (plating 20 um assumed, IPC class 2 average), terminals (pads) are equipotential. The source pad is
held at 0 V, each sink draws its load current; the linear network is solved directly (scipy).
Not modelled: temperature rise and copper heating (IPC-2152 needs board/environment data), plating tolerance, solder
fill of holes, skin effect / switching ripple (DC only), contact resistance of connectors.

Prints the voltage drop to every sink, the current of every via / pad barrel, the highest linear current densities
(A per mm of copper width) per layer with their positions, and writes one PNG map per layer into OUTDIR.
"""
from pathlib import Path
import math
import struct
import sys
import zlib

import numpy as np
import pcbnew
import scipy.sparse as sp
import scipy.sparse.linalg as spl
from scipy.sparse.csgraph import connected_components

T, M = pcbnew.ToMM, pcbnew.FromMM
RHO = 1.72e-8          # Ohm*m, copper at 20 degC
T_CU = 35e-6           # m, outer and inner copper of the stackup (3a)
T_PLATE = 20e-6        # m, hole plating (assumption)
Z = {"F.Cu": 0.0, "In1.Cu": 0.135, "In2.Cu": 1.41, "B.Cu": 1.545}  # mm, copper layer positions from the stackup
G_TERM = 1e4           # S per cell, pad terminal tie (equipotential pad)

# Loads: rev1-versorgung-und-boardwahl.md 3.2/3.4/3.10 and rev1-pin-und-anschlussplan.md (worst case, blocked servos).
CASES = {
    "vservo": dict(net="+V_SERVO", layers=["F.Cu", "B.Cu"], source=[("RS402", "2")],
                   sinks=[("J102 front servo", [("J102", "2")], 5.1), ("J103 rear servo", [("J103", "2")], 5.1),
                          ("J104 reserve", [("J104", "2")], 0.5), ("J105 reserve", [("J105", "2")], 0.5)]),
    # 10.1 A VCU input at 9.0 V (3.10); 0.75 A of it to the 5 V buck (1.13 A x 5.08 V / (9 V x 0.85), estimate)
    "vbat": dict(net="/Power/VBAT_PROT", layers=["F.Cu", "B.Cu"], source=[("Q101", "1"), ("Q101", "2"), ("Q101", "3")],
                 sinks=[("servo buck Q401 drain", [("Q401", "5")], 9.35), ("5 V buck U301", [("U301", "3")], 0.75)]),
    # track-routed supply nets (0.4 mm power class), loads from the 5 V budget (3.2) and the TPS2553 table
    # (Anschlussplan 8); for the switched outputs the upper current limit I_OS max is used as the worst case
    "5v": dict(net="+5V", layers=["F.Cu", "B.Cu"], source=[("L301", "2")],
               sinks=[("D501 -> DevKit", [("D501", "2")], 0.55), ("U601 LED switch", [("U601", "1")], 0.32),
                      ("U602 EXT switch", [("U602", "1")], 0.30), ("U603 RX switch", [("U603", "1")], 0.21),
                      ("BZ101 buzzer", [("BZ101", "1")], 0.15)]),
    "5v_devkit": dict(net="/Controller/+5V_DEVKIT", layers=["F.Cu", "B.Cu"], source=[("D501", "1")],
                      sinks=[("DevKit 5V pin", [("U501", "21")], 0.55)]),
    "5v_led": dict(net="/Lighting_IO/+5V_LED", layers=["F.Cu", "B.Cu"], source=[("U601", "6")],
                   sinks=[("J%d" % j, [("J%d" % j, "1")], 0.08) for j in (108, 109, 110, 111)]),
    "5v_ext": dict(net="/Lighting_IO/+5V_EXT", layers=["F.Cu", "B.Cu"], source=[("U602", "6")],
                   sinks=[("J112", [("J112", "1")], 0.30)]),
    "5v_rx": dict(net="/Lighting_IO/+5V_RX", layers=["F.Cu", "B.Cu"], source=[("U603", "6")],
                  sinks=[("J107", [("J107", "2")], 0.21)]),
    # servo return current (11.2 A) from the connectors to the battery connector (9.35 A, input current of the servo
    # buck) and to the low-side FET Q402 (1.85 A, average freewheel share = output minus input current; estimate)
    "gnd_servo": dict(net="GND", layers=["F.Cu", "In1.Cu", "In2.Cu", "B.Cu"], source=[("J101", "1")],
                      sinks=[("J102 front servo", [("J102", "3")], -5.1), ("J103 rear servo", [("J103", "3")], -5.1),
                             ("J104 reserve", [("J104", "3")], -0.5), ("J105 reserve", [("J105", "3")], -0.5),
                             ("Q402 source", [("Q402", "1"), ("Q402", "2"), ("Q402", "3")], 1.85)]),
}


def contours(ps):
    out = []
    for i in range(ps.OutlineCount()):
        for h in range(-1, ps.HoleCount(i)):
            c = ps.Outline(i) if h < 0 else ps.Hole(i, h)
            out.append(np.array([(T(c.CPoint(k).x), T(c.CPoint(k).y)) for k in range(c.PointCount())]))
    return out


def raster(conts, x0, y0, nx, ny, g):
    """Even-odd scanline fill of polygon contours at the cell centres."""
    m = np.zeros((ny, nx), bool)
    if not conts:
        return m
    a = np.concatenate([c for c in conts])
    b = np.concatenate([np.roll(c, -1, axis=0) for c in conts])
    ys = y0 + (np.arange(ny) + 0.5) * g
    xs = x0 + (np.arange(nx) + 0.5) * g
    for j, y in enumerate(ys):
        s = (a[:, 1] <= y) != (b[:, 1] <= y)
        if not s.any():
            continue
        xa, ya, xb, yb = a[s, 0], a[s, 1], b[s, 0], b[s, 1]
        xi = np.sort(xa + (y - ya) * (xb - xa) / (yb - ya))
        for k in range(0, len(xi) - 1, 2):
            m[j, (xs >= xi[k]) & (xs < xi[k + 1])] = True
    return m


def shape(item, layer):
    ps = pcbnew.SHAPE_POLY_SET()
    item.TransformShapeToPolygon(ps, layer, 0, M(0.005), pcbnew.ERROR_INSIDE)
    return contours(ps)


def png(path, rgb):
    h, w, _ = rgb.shape
    raw = b"".join(b"\x00" + rgb[r].astype(np.uint8).tobytes() for r in range(h))
    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
    Path(path).write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
                           + chunk(b"IDAT", zlib.compress(raw, 6)) + chunk(b"IEND", b""))


# A/mm -> colour: <0.5 dark blue, 0.5-1 blue, 1-2 green, 2-3 yellow, 3-5 orange, >5 red
STEPS = [(0.5, (40, 60, 120)), (1.0, (40, 120, 220)), (2.0, (60, 180, 80)), (3.0, (230, 210, 40)),
         (5.0, (240, 130, 30)), (1e9, (220, 30, 30))]


def main():
    pcb, case, out = sys.argv[1], sys.argv[2], Path(sys.argv[3])
    g = float(sys.argv[sys.argv.index("--grid") + 1]) if "--grid" in sys.argv else 0.1
    c = CASES[case]
    out.mkdir(parents=True, exist_ok=True)
    b = pcbnew.LoadBoard(pcb)
    nc = b.FindNet(c["net"]).GetNetCode()
    lids = {ln: b.GetLayerID(ln) for ln in c["layers"]}
    pads = [(f.GetReference(), p) for f in b.GetFootprints() for p in f.Pads() if p.GetNetCode() == nc]
    tracks = [t for t in b.GetTracks() if t.GetNetCode() == nc]
    zones = [z for z in b.Zones() if z.GetNetCode() == nc]
    # extent: all copper of the net on the chosen layers
    ext = []
    for it in [p for _, p in pads] + tracks + zones:
        r = it.GetBoundingBox()
        ext.append((T(r.GetLeft()), T(r.GetTop()), T(r.GetRight()), T(r.GetBottom())))
    ext = np.array(ext)
    x0, y0 = ext[:, 0].min() - 0.5, ext[:, 1].min() - 0.5
    x1, y1 = ext[:, 2].max() + 0.5, ext[:, 3].max() + 0.5
    if "--region" in sys.argv:  # K1 coordinates (outline corner at -0.05/-0.05), shifted with the board
        k = sys.argv.index("--region")
        r = [float(v) for v in sys.argv[k + 1:k + 5]]
        e = b.GetBoardEdgesBoundingBox()
        ox, oy = T(e.GetLeft()) + 0.05, T(e.GetTop()) + 0.05
        x0, y0, x1, y1 = max(x0, r[0] + ox), max(y0, r[1] + oy), min(x1, r[2] + ox), min(y1, r[3] + oy)
    nx, ny = int((x1 - x0) / g) + 1, int((y1 - y0) / g) + 1
    masks = {}
    for ln, L in lids.items():
        conts = []
        for z in zones:
            if z.IsOnLayer(L):
                conts.append(contours(z.GetFilledPolysList(L)))
        m = np.zeros((ny, nx), bool)
        for cs in conts:
            m |= raster(cs, x0, y0, nx, ny, g)
        for t in tracks:
            if (t.GetClass() == "PCB_VIA" and t.IsOnLayer(L)) or (t.GetClass() == "PCB_TRACK" and t.GetLayer() == L):
                m |= raster(shape(t, L), x0, y0, nx, ny, g)
        for _, p in pads:
            if p.IsOnLayer(L):
                m |= raster(shape(p, L), x0, y0, nx, ny, g)
        masks[ln] = m
    # nodes
    idx, n = {}, 0
    for ln in c["layers"]:
        a = -np.ones((ny, nx), int)
        k = masks[ln].sum()
        a[masks[ln]] = np.arange(n, n + k)
        idx[ln] = a
        n += k
    rows, cols, vals = [], [], []
    gs = T_CU / RHO  # S, square cell

    def link(i, j, gg):
        rows.extend([i, j, i, j]); cols.extend([i, j, j, i]); vals.extend([gg, gg, -gg, -gg])
    edges = {}
    for ln in c["layers"]:
        a = idx[ln]
        h = (a[:, :-1] >= 0) & (a[:, 1:] >= 0)
        v = (a[:-1, :] >= 0) & (a[1:, :] >= 0)
        edges[ln] = (a[:, :-1][h], a[:, 1:][h], a[:-1, :][v], a[1:, :][v], h, v)
        for p_, q_ in ((a[:, :-1][h], a[:, 1:][h]), (a[:-1, :][v], a[1:, :][v])):
            rows.extend(np.concatenate([p_, q_, p_, q_])); cols.extend(np.concatenate([p_, q_, q_, p_]))
            vals.extend(np.concatenate([np.full(len(p_), gs)] * 2 + [np.full(len(p_), -gs)] * 2))

    def cell(ln, x, y):
        i, j = int((x - x0) / g), int((y - y0) / g)
        if 0 <= i < nx and 0 <= j < ny and idx[ln][j, i] >= 0:
            return idx[ln][j, i]
        return None
    barrels = []  # (label, x, y, drill, [(lnA, lnB, node a, node b, G)])
    for t in tracks:
        if t.GetClass() != "PCB_VIA":
            continue
        p = t.GetPosition()
        barrels.append(("via", T(p.x), T(p.y), T(t.GetDrill())))
    for ref, p in pads:
        if p.GetDrillSize().x > 0:
            q = p.GetPosition()
            barrels.append(("%s.%s" % (ref, p.GetNumber()), T(q.x), T(q.y), T(p.GetDrillSize().x)))
    bsegs = []
    for lab, x, y, d in barrels:
        ls = [ln for ln in c["layers"] if cell(ln, x, y) is not None]
        segs = []
        for la, lb in zip(ls, ls[1:]):
            gg = 1 / (RHO * (Z[lb] - Z[la]) * 1e-3 / (math.pi * d * 1e-3 * T_PLATE))
            na, nb = cell(la, x, y), cell(lb, x, y)
            link(na, nb, gg)
            segs.append((la, lb, na, nb, gg))
        bsegs.append((lab, x, y, d, segs))
    # terminals
    term = {}

    def terminal(key, padlist):
        nonlocal n
        tid = n
        n += 1
        hit = 0
        for ref, num in padlist:
            for r2, p in pads:
                if r2 == ref and p.GetNumber() == num:
                    for ln, L in lids.items():
                        if not p.IsOnLayer(L):
                            continue
                        pm = raster(shape(p, L), x0, y0, nx, ny, g) & masks[ln]
                        for k in idx[ln][pm]:
                            link(tid, k, G_TERM)
                            hit += 1
        if not hit:
            raise SystemExit("terminal %s: no copper cells" % key)
        term[key] = tid
    terminal("source", c["source"])
    for lab, pl, cur in c["sinks"]:
        terminal(lab, pl)
    A = sp.csr_matrix((vals, (rows, cols)), shape=(n, n))
    ncomp, lab = connected_components(A != 0, directed=False)
    comp = lab[term["source"]]
    keep = np.where(lab == comp)[0]
    for k, (sl, pl, cur) in enumerate(c["sinks"]):
        if lab[term[sl]] != comp:
            print("NOT CONNECTED to the source: %s" % sl)
    pos = -np.ones(n, int)
    pos[keep] = np.arange(len(keep))
    Ak = A[keep][:, keep].tocsr()
    Ivec = np.zeros(len(keep))
    for sl, pl, cur in c["sinks"]:
        if lab[term[sl]] == comp:
            Ivec[pos[term[sl]]] -= cur
    s = pos[term["source"]]
    free = np.array([i for i in range(len(keep)) if i != s])
    V = np.zeros(len(keep))
    V[free] = spl.spsolve(Ak[free][:, free].tocsc(), Ivec[free])
    Vn = np.full(n, np.nan)
    Vn[keep] = V
    print("case %s, net %s, grid %.2f mm, %d copper cells; ESTIMATE (35 um copper, 20 um plating, 20 degC)" %
          (case, c["net"], g, n, ))
    print("terminal drops (source = %s):" % ", ".join("%s.%s" % x for x in c["source"]))
    for sl, pl, cur in c["sinks"]:
        v = Vn[term[sl]]
        print("  %-24s draws %+6.2f A   potential %+8.2f mV vs source  (|V/I| %.2f mOhm)" %
              (sl, cur, v * 1e3, abs(v / cur) * 1e3 if cur else 0))
    # power
    loss = 0.0
    for ln in c["layers"]:
        p_, q_, r_, s_, h, v = edges[ln]
        for aa, bb_ in ((p_, q_), (r_, s_)):
            dv = Vn[aa] - Vn[bb_]
            loss += np.nansum(dv * dv * gs)
    print("copper loss in the modelled layers: %.3f W" % loss)
    print("barrels (vias / plated pad holes) carrying > 0.05 A:")
    rep = []
    for labl, x, y, d, segs in bsegs:
        if not segs or np.isnan(Vn[segs[0][2]]):
            continue
        cur = max(abs(Vn[na] - Vn[nb]) * gg for la, lb, na, nb, gg in segs)
        rep.append((cur, labl, x, y, d))
    rep.sort(reverse=True)
    for cur, labl, x, y, d in rep:
        if cur > 0.05:
            print("  %-8s (%6.2f, %6.2f) drill %.2f  %.2f A" % (labl, x, y, d, cur))
    # density maps
    for ln in c["layers"]:
        a = idx[ln]
        Vg = np.where(a >= 0, Vn[np.maximum(a, 0)], np.nan)
        ix = np.zeros((ny, nx)); iy = np.zeros((ny, nx))
        dx = (Vg[:, :-1] - Vg[:, 1:]) * gs
        dy = (Vg[:-1, :] - Vg[1:, :]) * gs
        dx = np.nan_to_num(dx); dy = np.nan_to_num(dy)
        ix[:, :-1] += dx / 2; ix[:, 1:] += dx / 2
        iy[:-1, :] += dy / 2; iy[1:, :] += dy / 2
        lin = np.hypot(ix, iy) / g  # A per mm of width
        lin[a < 0] = 0
        order = np.argsort(lin, axis=None)[::-1]
        print("%s: highest linear current density (A/mm of copper width), outside pads:" % ln)
        padm = np.zeros((ny, nx), bool)
        for _, p in pads:
            if p.IsOnLayer(lids[ln]):
                padm |= raster(shape(p, lids[ln]), x0, y0, nx, ny, g)
        shown = []
        for o in order:
            j, i = divmod(o, nx)
            if padm[j, i] or lin[j, i] <= 0:
                continue
            x, y = x0 + (i + 0.5) * g, y0 + (j + 0.5) * g
            if all(math.hypot(x - sx, y - sy) > 1.5 for sx, sy, _ in shown):
                shown.append((x, y, lin[j, i]))
            if len(shown) >= 6:
                break
        for x, y, v in shown:
            print("  (%6.2f, %6.2f)  %.2f A/mm" % (x, y, v))
        rgb = np.zeros((ny, nx, 3))
        rgb[masks[ln]] = (70, 70, 70)
        for k in range(len(STEPS)):  # ascending, higher bins overwrite
            lo = STEPS[k - 1][0] if k else 0.05
            sel = masks[ln] & (lin >= lo)
            rgb[sel] = STEPS[k][1]
        rgb[padm & masks[ln]] = (200, 200, 200)
        scale = max(1, int(round(0.1 / g * 4)))
        rgb = np.repeat(np.repeat(rgb, scale, 0), scale, 1)
        png(out / ("%s_%s.png" % (case, ln.replace(".", "_"))), rgb)
    print("maps: %s (grey: copper < 0.05 A/mm, light grey: pads; dark blue < 0.5, blue < 1, green < 2, yellow < 3,"
          " orange < 5, red >= 5 A/mm)" % out)


if __name__ == "__main__":
    main()
