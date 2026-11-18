#!/usr/bin/env python3
"""Project 3D models (VRML) built from the manufacturers' package drawings (3D model review, 2026-11-18).

Usage: python3 make_package_models.py
Writes hardware/libraries/3d-models/project/*.wrl. These are OWN models (MIT, like the repository), drawn from the
dimensions below; they are not vendor files. They exist because neither the KiCad 10.0.7 library (the footprints
reference model files the official kicad-packages3D repository does not contain, checked on master and tag 10.0.7)
nor an account-free vendor or community source offers them. Coordinates are footprint coordinates of the KiCad
footprints used on the board (origin and pin positions read from the board), z up from the board top, mm.
Nominal values are used where the drawing gives a range. VRML only: rendered by KiCad, not part of a STEP export.

Sources (read 2026-11-18):
- PowerPAK SO-8 Single (Q101 SiRA99DP): Vishay "Package Information PowerPAK SO-8 (Single/Dual)", doc 71655,
  rev. 13-Feb-17; SiRA99DP datasheet doc 71023 names the package PowerPAK SO-8 Single.
- PG-TDSON-8-6 (Q401/Q402 BSC026N04LS): Infineon package outline infineon-pg-tdson-8-6-spo; package from the
  Infineon product page of BSC026N04LS.
- DPY0002A X1SON (D601-D604, D606-D608 TPD1E05U06DPYR): TI datasheet SLVSBO7O (Aug 2024), outline 4224561/C.
- XT30PW-M (J101): AMASS specification V1.2 "XT30PW-M" (customer drawing). The drawing gives no body height;
  5.2 mm is scaled from its end view (ESTIMATE).
"""
import math
from pathlib import Path

OUT = Path(__file__).resolve().parents[2] / "hardware/libraries/3d-models/project"
S = 1 / 2.54                         # KiCad reads VRML in 0.1 inch
BODY, TIN, GOLD, YELLOW, MARK = (0.12, 0.12, 0.13), (0.82, 0.82, 0.80), (0.86, 0.70, 0.30), (1.0, 0.80, 0.10), \
    (0.85, 0.85, 0.85)


class Model:
    def __init__(self):
        self.shapes = []

    def box(self, x1, y1, x2, y2, z0, z1, rgb):
        p = [(x, y, z) for z in (z0, z1) for x, y in ((x1, y1), (x2, y1), (x2, y2), (x1, y2))]
        f = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
        self.shapes.append((p, f, rgb))

    def cyl(self, cx, cy, r, z0, z1, rgb, n=20, axis="z", length=None):
        """Cylinder along z (default) or along y (axis 'y': from cy to cy+length at height z0, radius r)."""
        ring = [(r * math.cos(2 * math.pi * k / n), r * math.sin(2 * math.pi * k / n)) for k in range(n)]
        if axis == "z":
            p = [(cx + a, cy + b, z) for z in (z0, z1) for a, b in ring]
        else:
            p = [(cx + a, cy + t, z0 + b) for t in (0, length) for a, b in ring]
        f = [tuple(reversed(range(n))), tuple(range(n, 2 * n))] + \
            [(k, (k + 1) % n, n + (k + 1) % n, n + k) for k in range(n)]
        if axis == "y":                  # (x, t, z) is the opposite handedness of (x, y, z): pre-reverse the faces
            f = [tuple(reversed(face)) for face in f]
        self.shapes.append((p, f, rgb))

    def write(self, path):
        out = ["#VRML V2.0 utf8"]
        for p, f, rgb in self.shapes:
            pts = ", ".join("%.4f %.4f %.4f" % (x * S, -y * S, z * S) for x, y, z in p)   # VRML y = -footprint y
            # y is mirrored for VRML, which flips the handedness: reverse every face so that normals point out
            idx = ",".join(",".join(str(i) for i in reversed(face)) + ",-1" for face in f)
            out.append("Shape { appearance Appearance { material Material { diffuseColor %.3f %.3f %.3f "
                       "specularColor 0.2 0.2 0.2 shininess 0.3 } }\n geometry IndexedFaceSet { solid FALSE "
                       "coord Coordinate { point [ %s ] } coordIndex [ %s ] } }" % (rgb + (pts, idx)))
        path.write_text("\n".join(out) + "\n")


def leadless_8(name, e_mold, e_lead, d, a, b, land, c, pin_x, rows=(-1.905, -0.635, 0.635, 1.905)):
    """SO-8-style leadless power package: body, 4 leads on each side (pins 1-4 at x < 0), pin-1 dot."""
    m = Model()
    m.box(-e_mold / 2, -d / 2, e_mold / 2, d / 2, 0.0, a, BODY)
    for side in (-1, 1):
        for y in rows:
            x_out = side * e_lead / 2
            x_in = side * (e_lead / 2 - land)
            m.box(min(x_out, x_in), y - b / 2, max(x_out, x_in), y + b / 2, 0.0, c, TIN)
    m.cyl(pin_x + 0.75, rows[0] + 0.35, 0.3, a, a + 0.01, MARK)
    m.write(OUT / name)


def dpy0002a():
    m = Model()
    L, W, H = 1.0, 0.6, 0.375            # 0.9-1.1, 0.5-0.7, 0.30-0.45 -> nominal
    m.box(-L / 2, -W / 2, L / 2, W / 2, 0.02, H, BODY)
    for x in (-0.325, 0.325):            # pads 0.2-0.3 x 0.45-0.55, pitch 0.65
        m.box(x - 0.125, -0.25, x + 0.125, 0.25, 0.0, 0.03, TIN)
    m.box(-0.45, -0.25, -0.35, 0.25, H, H + 0.005, MARK)   # pin 1 side marker (TI: pin 1 index area)
    m.write(OUT / "TI_DPY0002A_X1SON-2_1.0x0.6mm.wrl")


def xt30pw_m():
    """AMASS XT30PW-M on the KiCad footprint AMASS_XT30PW-M_1x02_P2.50mm_Horizontal: contact tails at (0|0) and
    (-5|0), pegs at (-8|-10) and (3|-10); housing 9.9 wide (x -7.45..2.45), 9.0 deep (y -13.15..-4.15), mating face
    at y = -13.15; ears with pegs give 13.3 over all (x -9.15..4.15)."""
    m = Model()
    H = 5.2                              # body height: not dimensioned, scaled from the end view (estimate)
    zc = 2.6                             # contact axis height (estimate, centre of the body)
    m.box(-7.45, -13.15, 2.45, -4.15, 0.0, H, YELLOW)
    for xe in (-8.0, 3.0):               # mounting ears with Ø 1.0 pegs
        m.box(xe - 1.15, -11.2, xe + 1.15, -8.8, 0.0, 1.2, YELLOW)
        m.cyl(xe, -10.0, 0.5, -1.6, 0.0, YELLOW)
    for xc in (0.0, -5.0):
        m.box(xc - 1.6, -13.2, xc + 1.6, -12.85, 0.9, 4.3, BODY)     # mating opening (dark face)
        m.cyl(xc, -13.0, 1.0, zc, 0, GOLD, axis="y", length=8.6)   # male pin Ø 2.0 inside the housing
        m.cyl(xc, -4.15, 0.85, zc, 0, GOLD, axis="y", length=4.15)  # tail out of the back
        m.cyl(xc, 0.0, 0.85, -1.9, zc + 0.85, GOLD)                 # tail bent down into the PCB (Ø 1.7 hole)
    m.write(OUT / "AMASS_XT30PW-M_horizontal.wrl")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    # Vishay 71655: E 6.15 (leads), E1 5.89 (mould), D 5.15, A 1.04, b 0.41, L 0.61, c 0.28; pins on x
    leadless_8("Vishay_PowerPAK_SO-8_Single.wrl", 5.89, 6.15, 5.15, 1.04, 0.41, 0.61, 0.28, -2.67)
    # Infineon PG-TDSON-8-6: 6.15 over leads, 5.9 mould, 5.15 wide, 1.0 high, lead 0.44, land 0.55, lead 0.25
    leadless_8("Infineon_PG-TDSON-8-6.wrl", 5.9, 6.15, 5.15, 1.0, 0.44, 0.55, 0.25, -2.863)
    dpy0002a()
    xt30pw_m()
    for p in sorted(OUT.glob("*.wrl")):
        print("written", p.name)


if __name__ == "__main__":
    main()
