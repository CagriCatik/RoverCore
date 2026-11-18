#!/usr/bin/env python3
"""Assign verified vendor 3D models to board footprints (3D model review, 2026-11-18).

Usage: <KiCad python> assign_vendor_models.py BOARD.kicad_pcb
Reads hardware/libraries/3d-models/models.csv (reference list, file, offset, rotation, source) and replaces the 3D
model entries of those footprints on the board. Only the 3D model list changes: pads, positions, rotation of the
footprint, nets and routing stay as they are. Refuses to run while KiCad lock files exist or when a listed model
file is missing (vendor files are not in Git, see hardware/libraries/3d-models/README.md). No zone refill is needed.
"""
import csv
from pathlib import Path
import sys

import pcbnew

ROOT = Path(__file__).resolve().parents[2]
TABLE = ROOT / "hardware/libraries/3d-models/models.csv"


def main():
    pcb = Path(sys.argv[1])
    if list(pcb.parent.glob("~*.lck")) + list(pcb.parent.glob("*.lck")):
        raise SystemExit("ABORTED: KiCad lock files present")
    rows = list(csv.DictReader(open(TABLE)))
    for r in rows:
        f = ROOT / "hardware/libraries/3d-models" / r["file"]
        if not f.exists():
            raise SystemExit("ABORTED: model file missing: %s (fetch it first, see README)" % f)
    b = pcbnew.LoadBoard(str(pcb))
    for r in rows:
        for ref in r["refs"].split():
            fp = b.FindFootprintByReference(ref)
            if fp is None:
                raise SystemExit("ABORTED: %s not on the board" % ref)
            before = [m.m_Filename for m in fp.Models()]
            fp.Models().clear()
            m = pcbnew.FP_3DMODEL()
            m.m_Filename = "${KIPRJMOD}/hardware/libraries/3d-models/" + r["file"]
            m.m_Offset = pcbnew.VECTOR3D(*[float(v) for v in r["offset_mm"].split()])
            m.m_Rotation = pcbnew.VECTOR3D(*[float(v) for v in r["rotation_deg"].split()])
            m.m_Scale = pcbnew.VECTOR3D(1, 1, 1)
            fp.Add3DModel(m)
            print("%s: %s -> %s" % (ref, ", ".join(Path(x).name for x in before) or "none", r["file"]))
    b.Save(str(pcb))


if __name__ == "__main__":
    main()
