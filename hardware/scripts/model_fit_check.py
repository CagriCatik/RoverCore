#!/usr/bin/env python3
"""Fit check of a 3D model against a footprint of the board (3D model review, 2026-11-18).

Usage: <KiCad python> model_fit_check.py BOARD.kicad_pcb REF MODEL OUTDIR [--offset X Y Z] [--rot RX RY RZ]
Copies footprint REF from the board onto an otherwise empty scratch board in OUTDIR (pads, silkscreen, Fab and
courtyard as on the board, orientation 0), replaces its 3D models by MODEL with the given offset (mm) and rotation
(degrees), and renders top, front, side and iso views. The board file itself is never written. Used to align
vendor STEP files before their offset/rotation is entered in the footprint; the images are review output only.
"""
from pathlib import Path
import subprocess
import sys

import pcbnew

M = pcbnew.FromMM
CLI = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"


def arg(name, n):
    if name not in sys.argv:
        return [0.0] * n
    k = sys.argv.index(name)
    return [float(v) for v in sys.argv[k + 1:k + 1 + n]]


def main():
    src, ref, model, out = sys.argv[1], sys.argv[2], sys.argv[3], Path(sys.argv[4])
    off, rot = arg("--offset", 3), arg("--rot", 3)
    out.mkdir(parents=True, exist_ok=True)
    b = pcbnew.LoadBoard(src)
    fp = b.FindFootprintByReference(ref)
    nb = pcbnew.CreateEmptyBoard()
    nfp = pcbnew.FOOTPRINT(fp)
    nfp.SetParent(nb)
    if nfp.IsFlipped():
        nfp.Flip(nfp.GetPosition(), pcbnew.FLIP_DIRECTION_TOP_BOTTOM)
    nfp.SetOrientationDegrees(0)
    nfp.SetPosition(pcbnew.VECTOR2I(M(50), M(50)))
    nfp.Models().clear()
    m = pcbnew.FP_3DMODEL()
    m.m_Filename = str(Path(model).resolve())
    m.m_Offset = pcbnew.VECTOR3D(*off)
    m.m_Rotation = pcbnew.VECTOR3D(*rot)
    m.m_Scale = pcbnew.VECTOR3D(1, 1, 1)
    nfp.Add3DModel(m)
    nb.Add(nfp)
    bb = nfp.GetBoundingBox(False)
    pad = M(4)
    x1, y1, x2, y2 = bb.GetLeft() - pad, bb.GetTop() - pad, bb.GetRight() + pad, bb.GetBottom() + pad
    for a, c in (((x1, y1), (x2, y1)), ((x2, y1), (x2, y2)), ((x2, y2), (x1, y2)), ((x1, y2), (x1, y1))):
        s = pcbnew.PCB_SHAPE(nb)
        s.SetShape(pcbnew.SHAPE_T_SEGMENT)
        s.SetLayer(pcbnew.Edge_Cuts)
        s.SetStart(pcbnew.VECTOR2I(*a))
        s.SetEnd(pcbnew.VECTOR2I(*c))
        s.SetWidth(M(0.1))
        nb.Add(s)
    pcb = out / ("fit_%s.kicad_pcb" % ref)
    nb.Save(str(pcb))
    views = {"top": ["--side", "top"], "front": ["--side", "front"], "left": ["--side", "left"],
             "iso": ["--perspective", "--rotate", "-55,0,35"]}
    for name, a in views.items():
        subprocess.run([CLI, "pcb", "render", "-o", str(out / ("fit_%s_%s.png" % (ref, name))), "--width", "1000",
                        "--height", "700", "--quality", "high", "--background", "opaque"] + a + [str(pcb)],
                       check=True, capture_output=True)
    print("rendered", ", ".join(views), "to", out)


if __name__ == "__main__":
    main()
