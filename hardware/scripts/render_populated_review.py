#!/usr/bin/env python3
"""Populated review views (owner review 2026-11-16): the carrier with every placed part, plus the plugged DevKit,
OLED and IMU, rendered with KiCad's 3D renderer on a COPY of the board in qa/generated/populated/.

Parts without a verified 3D model get an ENVELOPE body in that copy only: a plain box (VRML) with the documented
or assumed dimensions below, magenta for carrier parts, blue for the plug-in modules. Envelopes are not vendor
models and are never written to the library or to RoverCore.kicad_pcb. Every footprint is listed in
model_status.csv with one of: library model, generic library model (socket), envelope (review), no body (pad), missing.
Views: populated_top / _bottom / _iso and without_modules_top / _iso (sockets visible, modules removed), each
with a caption naming the envelope parts; gap_map.png shows the free board area (courtyards, envelopes, M3
keep-outs and power pours counted as occupied). Run with the KiCad Python.
"""
from pathlib import Path
import csv
import os
import shutil
import subprocess

import pcbnew

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "qa/generated/populated"
CLI = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
MODEL_DIR = Path("/Applications/KiCad/KiCad.app/Contents/SharedSupport/3dmodels")
T, M = pcbnew.ToMM, pcbnew.FromMM
CARRIER, MODULE = (1.0, 0.0, 1.0), (0.15, 0.45, 1.0)

# ref: list of (kind, box, z0, z1, source); box "fab" = bounding box of the footprint's F.Fab outline,
# otherwise (x1, y1, x2, y2) in footprint coordinates (mm)
DEVKIT_PCB = (-1.27, -1.565, 24.13, 61.30)          # Espressif DXF v1.1 via make_devkit_socket.py
ENVELOPES = {
    "U501": [("module", DEVKIT_PCB, 11.0, 12.6, "DevKit-PCB 25,4 x 62,865 mm (DXF v1.1); Unterkante 11,0 mm = "
                                               "Buchse 8,5 mm (KiCad-Modell) + Stiftleistenkragen 2,5 mm (Annahme)"),
             ("module", (2.43, -7.85, 20.43, 17.65), 12.6, 15.7, "WROOM-1 18 x 25,5 x 3,1 mm, Antennenüberstand "
                                                              "6,31 mm (DXF), Lage mittig (O-4)"),
             ("module", (1.13, 55.70, 8.33, 61.30), 12.6, 15.2, "Micro-USB UART, x aus DXF, Tiefe/Höhe geschätzt"),
             ("module", (14.53, 55.70, 21.73, 61.30), 12.6, 15.2, "Micro-USB USB, x aus DXF, Tiefe/Höhe geschätzt")],
    "J116": [("module", "fab", 8.51, 14.71, "OLED-Modul: Umriss aus Adafruit-Boarddatei (Footprint), Dicke 6,2 mm "
                                          "(Adafruit 326), auf Buchse 8,51 mm (Annahme Lage)")],
    "J115": [("module", "fab", 8.51, 13.11, "IMU-Modul: 25,4 x 17,78 mm (Footprint), Dicke 4,6 mm (Adafruit 4438), "
                                          "auf Buchse 8,51 mm")],
    "J101": [("carrier", "fab", 0.0, 5.0, "XT30PW-M: Gehäuse 9,0 x 9,9 mm (AMASS V1.2); Höhe nicht angegeben, "
                                        "Annahme 5 mm"), ],
    "J102": [("carrier", "fab", 0.0, 10.0, "Micro-Fit 43650-0300: Umriss aus Footprint; Höhe Annahme 10 mm "
                                         "(Molex-Zeichnung nicht gelesen)")],
    "J103": [("carrier", "fab", 0.0, 10.0, "wie J102")],
    "BZ101": [("carrier", "fab", 0.0, 4.0, "CMT-8540S: 8,5 x 4,0 mm aus der Typbezeichnung, Datenblatt nicht "
                                          "lesbar (HTTP 403)")],
    "Q101": [("carrier", "fab", 0.0, 1.05, "PowerPAK SO-8: Umriss aus Footprint, Höhe Annahme 1,05 mm")],
    "Q401": [("carrier", "fab", 0.0, 1.05, "PG-TDSON-8 6,15 x 5,15 mm (Footprint), Höhe Annahme 1,05 mm")],
    "Q402": [("carrier", "fab", 0.0, 1.05, "wie Q401")],
}
for r in ("D601", "D602", "D603", "D604", "D606", "D607", "D608"):
    ENVELOPES[r] = [("carrier", "fab", 0.0, 0.4, "DPY0002A (X2SON) 0,6 x 1,0 mm (Footprint), Höhe Annahme 0,4 mm")]
SOCKETS = {"U501", "J115", "J116"}  # generic KiCad library socket model (not the Samtec part)


def wrl_box(path, x1, y1, x2, y2, z0, z1, rgb, transparency):
    """VRML box in footprint coordinates; KiCad reads VRML in 0.1-inch units, y up."""
    s = 1 / 2.54
    X1, X2, Y1, Y2, Z0, Z1 = x1 * s, x2 * s, -y2 * s, -y1 * s, z0 * s, z1 * s
    pts = [(X1, Y1, Z0), (X2, Y1, Z0), (X2, Y2, Z0), (X1, Y2, Z0), (X1, Y1, Z1), (X2, Y1, Z1), (X2, Y2, Z1),
           (X1, Y2, Z1)]
    faces = "0,3,2,1,-1,4,5,6,7,-1,0,1,5,4,-1,1,2,6,5,-1,2,3,7,6,-1,3,0,4,7,-1"
    path.write_text("#VRML V2.0 utf8\nShape { appearance Appearance { material Material { diffuseColor %s %s %s "
                    "transparency %s } }\n geometry IndexedFaceSet { solid FALSE coord Coordinate { point [ %s ] }"
                    " coordIndex [ %s ] } }\n" % (rgb[0], rgb[1], rgb[2], transparency,
                                                  ", ".join("%.4f %.4f %.4f" % p for p in pts), faces))


def local_fab_box(fp):
    pos, ang = fp.GetPosition(), fp.GetOrientation()
    fp.SetOrientationDegrees(0)
    fp.SetPosition(pcbnew.VECTOR2I(0, 0))
    xs, ys = [], []
    for g in fp.GraphicalItems():
        if g.GetLayer() == pcbnew.F_Fab and isinstance(g, pcbnew.PCB_SHAPE):
            bb = g.GetBoundingBox()
            xs += [T(bb.GetLeft()), T(bb.GetRight())]
            ys += [T(bb.GetTop()), T(bb.GetBottom())]
    fp.SetOrientation(ang)
    fp.SetPosition(pos)
    return (min(xs), min(ys), max(xs), max(ys))


def model_exists(fn):
    fn = fn.replace("${KICAD10_3DMODEL_DIR}", str(MODEL_DIR)).replace("${KIPRJMOD}", str(ROOT))
    return os.path.exists(fn)


def build(with_modules, src=None, out=None):
    out = out or OUT
    b = pcbnew.LoadBoard(str(src or ROOT / "RoverCore.kicad_pcb"))
    mdir = out / "models"
    mdir.mkdir(parents=True, exist_ok=True)
    for ref, boxes in ENVELOPES.items():
        fp = b.FindFootprintByReference(ref)
        for i, (kind, box, z0, z1, _src) in enumerate(boxes):
            if kind == "module" and not with_modules:
                continue
            x1, y1, x2, y2 = local_fab_box(fp) if box == "fab" else box
            f = mdir / ("%s_%d.wrl" % (ref, i))
            wrl_box(f, x1, y1, x2, y2, z0, z1, MODULE if kind == "module" else CARRIER, 0.35 if kind == "module"
                    else 0.2)
            m = pcbnew.FP_3DMODEL()
            m.m_Filename = str(f)
            m.m_Scale = pcbnew.VECTOR3D(1, 1, 1)
            fp.Add3DModel(m)
    name = "RoverCore_review_%s.kicad_pcb" % ("populated" if with_modules else "without_modules")
    b.Save(str(out / name))
    return out / name


def caption(png, title, out):
    lines = [title,
             "Magenta = Hüllkörper Carrier-Bauteil ohne geprüftes Modell (Maße dokumentiert/angenommen, kein Herstellermodell):",
             "  J101 XT30, J102/J103 Micro-Fit, BZ101, Q101, Q401, Q402, D601-D604, D606-D608",
             "Blau = Hüllkörper der gesteckten Module (DevKit, OLED, IMU), Höhen geschätzt; Buchsenleisten = generisches KiCad-Modell",
             "Quelle der Maße und Status je Position: qa/generated/populated/model_status.csv, Bericht 3g"]
    svg = ['<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="2400" '
           'height="1830"><rect width="2400" height="1830" fill="white"/>',
           '<image xlink:href="%s" x="0" y="0" width="2400" height="1600"/>' % png.name]
    for i, ln in enumerate(lines):
        svg.append('<text x="30" y="%d" font-family="Helvetica" font-size="%d" fill="%s">%s</text>'
                   % (1640 + i * 38, 34 if i == 0 else 26, "#000" if i in (0, 4) else ("#b000b0" if i < 3 else "#1f4fd0"),
                      ln.replace("&", "&amp;")))
    svg.append("</svg>")
    s = png.with_suffix(".svg")
    s.write_text("\n".join(svg))
    subprocess.run(["rsvg-convert", "-o", str(out), str(s)], check=True, cwd=str(png.parent))


def render(pcb, stem, sides, out=None, label=""):
    out = out or OUT
    for side, args in sides:
        raw = out / ("%s_%s_raw.png" % (stem, side))
        subprocess.run([CLI, "pcb", "render", "-o", str(raw), "--width", "2400", "--height", "1600", "--quality",
                        "basic"] + args + [str(pcb)], check=True, capture_output=True)
        caption(raw, "%s%s - %s (Review-Ansicht, Hüllkörper sind keine Herstellermodelle)" % (label, stem, side),
                out / ("%s_%s.png" % (stem, side)))


def status_list(src=None, out=None):
    out = out or OUT
    b = pcbnew.LoadBoard(str(src or ROOT / "RoverCore.kicad_pcb"))
    rows = []
    for fp in sorted(b.GetFootprints(), key=lambda f: f.GetReference()):
        ref, fpid = fp.GetReference(), fp.GetFPIDAsString()
        files = [m.m_Filename for m in fp.Models()]
        real = [f for f in files if model_exists(f)]
        if ref in SOCKETS:
            st = "generisches Bibliotheksmodell (Buchsenleiste) + Hüllkörper Modul (Review)"
        elif ref in ENVELOPES:
            st = "Hüllkörper (Review)" + ("; Bibliotheksdatei fehlt in dieser KiCad-Installation" if files else "")
        elif real:
            st = "Bibliotheksmodell"
        elif fpid.split(":")[-1].startswith(("TestPoint_Pad", "NetTie")):
            st = "kein Körper (Pad/Net-Tie)"
        else:
            st = "FEHLT"
        src = "; ".join(x[4] for x in ENVELOPES.get(ref, []))
        rows.append((ref, fpid, " | ".join(os.path.basename(f) for f in files), st, src))
    with open(out / "model_status.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["Referenz", "Footprint", "Modelldatei(en)", "Status", "Maße der Hülle / Quelle"])
        w.writerows(rows)
    counts = {}
    for r in rows:
        counts[r[3].split(";")[0]] = counts.get(r[3].split(";")[0], 0) + 1
    return rows, counts


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    shutil.copy(ROOT / "RoverCore.kicad_pro", OUT / "RoverCore_review_populated.kicad_pro")
    shutil.copy(ROOT / "RoverCore.kicad_pro", OUT / "RoverCore_review_without_modules.kicad_pro")
    iso = ["--side", "top", "--rotate", "-45,0,45", "--zoom", "0.9"]
    pop = build(True)
    render(pop, "populated", [("top", ["--side", "top"]), ("bottom", ["--side", "bottom"]), ("iso", iso)])
    bare = build(False)
    render(bare, "without_modules", [("top", ["--side", "top"]), ("iso", iso)])
    rows, counts = status_list()
    for k, v in sorted(counts.items()):
        print("%3d  %s" % (v, k))
    missing = [r[0] for r in rows if r[3] == "FEHLT"]
    print("missing:", " ".join(missing) if missing else "none")
    free, found = gap_map()
    print("free %.0f mm2; largest free rectangles: %s" % (free, ", ".join("%.0fx%.0f at (%.0f|%.0f)" % (
        x2 - x1, y2 - y1, x1, y1) for x1, y1, x2, y2 in found)))
    print("wrote", OUT)



def gap_map(step=0.5):
    """Free area map: board cells not covered by a courtyard, a module/plug envelope, a hole keep-out (r 4 mm) or an
    outer-layer power/GND pour. Returns free mm2, the largest free rectangles and writes gap_map.png."""
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from render_placement_review import ENVELOPES as ENV_REV, HOLES_REV, fab_rect
    b = pcbnew.LoadBoard(str(ROOT / "RoverCore.kicad_pcb"))
    W, H = int(150 / step), int(100 / step)
    occ = [[0] * W for _ in range(H)]

    def mark(x1, y1, x2, y2, v=1):
        for j in range(max(0, int(y1 / step)), min(H, int(y2 / step) + 1)):
            for i in range(max(0, int(x1 / step)), min(W, int(x2 / step) + 1)):
                occ[j][i] = max(occ[j][i], v)
    for fp in b.GetFootprints():
        fp.BuildCourtyardCaches()
        cy = fp.GetCourtyard(pcbnew.F_CrtYd if fp.GetLayer() == pcbnew.F_Cu else pcbnew.B_CrtYd)
        bb = cy.BBox() if cy.OutlineCount() else fp.GetBoundingBox(False)
        mark(T(bb.GetLeft()), T(bb.GetTop()), T(bb.GetRight()), T(bb.GetBottom()))
    for ref, _lab, _z, rect in ENV_REV:
        r = rect or fab_rect(b, ref)
        mark(*r, v=2)
    for hx, hy in HOLES_REV:
        mark(hx - 4, hy - 4, hx + 4, hy + 4, v=3)
    for z in b.Zones():
        if z.IsOnLayer(pcbnew.F_Cu) and z.GetNetname() != "GND" or (z.IsOnLayer(pcbnew.F_Cu) and
                                                                   z.GetZoneName().startswith(("servo", "in_", "logic"))):
            bb = z.GetBoundingBox()
            mark(T(bb.GetLeft()), T(bb.GetTop()), T(bb.GetRight()), T(bb.GetBottom()), v=4)
    free = sum(row.count(0) for row in occ) * step * step
    # largest empty rectangles (greedy, by histogram), reported down to 60 mm2
    found = []
    work = [row[:] for row in occ]
    for _ in range(8):
        hist = [0] * W
        best = (0, None)
        for j in range(H):
            for i in range(W):
                hist[i] = hist[i] + 1 if work[j][i] == 0 else 0
            stack = []
            for i in range(W + 1):
                h = hist[i] if i < W else 0
                start = i
                while stack and stack[-1][1] >= h:
                    s, hh = stack.pop()
                    area = hh * (i - s)
                    if area > best[0]:
                        best = (area, (s, j - hh + 1, i - 1, j))
                    start = s
                stack.append((start, h))
        if not best[1] or best[0] * step * step < 60:
            break
        i1, j1, i2, j2 = best[1]
        found.append((i1 * step, j1 * step, (i2 + 1) * step, (j2 + 1) * step))
        for j in range(j1, j2 + 1):
            for i in range(i1, i2 + 1):
                work[j][i] = 9
    cols = {0: "#ffffff", 1: "#c9c2a0", 2: "#7fa6e8", 3: "#e07070", 4: "#e7b9b9", 9: "#ffffff"}
    s = ['<svg xmlns="http://www.w3.org/2000/svg" width="1500" height="1100" viewBox="0 -2 150 110">',
         '<rect x="0" y="0" width="150" height="100" fill="white" stroke="black" stroke-width="0.3"/>']
    for j in range(H):
        for i in range(W):
            if occ[j][i]:
                s.append('<rect x="%s" y="%s" width="%s" height="%s" fill="%s"/>' % (i * step, j * step, step, step,
                                                                                   cols[occ[j][i]]))
    for k, (x1, y1, x2, y2) in enumerate(found):
        s.append('<rect x="%s" y="%s" width="%s" height="%s" fill="#30c030" fill-opacity="0.35" stroke="#108010" '
                 'stroke-width="0.3"/><text x="%s" y="%s" font-size="2.2" font-family="Helvetica">%d: %.0fx%.0f</text>'
                 % (x1, y1, x2 - x1, y2 - y1, x1 + 0.5, y1 + 2.4, k + 1, x2 - x1, y2 - y1))
    s.append('<text x="0" y="104" font-size="2.4" font-family="Helvetica">Lueckenkarte: beige = Courtyards, blau = '
             'Modul-/USB-Huellen, rot = M3-Freiraum r 4 mm, rosa = Leistungs-Kupferflaechen; gruen = groesste freie '
             'Rechtecke. Frei gesamt %.0f mm2 von 15000 mm2</text>' % free)
    s.append("</svg>")
    (OUT / "gap_map.svg").write_text("\n".join(s))
    subprocess.run(["rsvg-convert", "-o", str(OUT / "gap_map.png"), str(OUT / "gap_map.svg")], check=True)
    return free, found


if __name__ == "__main__":
    main()
