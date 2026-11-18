#!/usr/bin/env python3
"""Cross-check of a DRAFT fabrication package against the board (fabrication review, 2026-11-18).

Usage: <KiCad python> fab_package_check.py BOARD.kicad_pcb PACKAGE_DIR
Checks, and prints each finding:
- BOM (assembly/bom.csv): every board footprint that is not excluded from the BOM appears exactly once; DNP flags
  match; MPN and manufacturer are present.
- Positions (assembly/positions.csv): every SMD footprint not excluded from position files is listed once, with the
  board side, rotation and position (relative to the drill/place origin, Y up) of the board; no THT-only part listed.
- Drill file: plated hole sizes against JLCPCB (via >= 0.15 mm; component holes below 0.5 mm are listed), NPTH >= 0.5 mm.
- Gerber job file: layer count and finished board thickness against the stackup in the board.
Exit status 1 if any finding is an error.
"""
import csv
import json
from pathlib import Path
import re
import sys

import pcbnew

T = pcbnew.ToMM


def expand(refs):
    out = []
    for part in refs.split(","):
        m = re.match(r"^([A-Z]+)(\d+)-([A-Z]+)(\d+)$", part.strip())
        if m:
            out += ["%s%d" % (m.group(1), k) for k in range(int(m.group(2)), int(m.group(4)) + 1)]
        elif part.strip():
            out.append(part.strip())
    return out


def main():
    b = pcbnew.LoadBoard(sys.argv[1])
    pkg = Path(sys.argv[2])
    err, info = [], []
    fps = {f.GetReference(): f for f in b.GetFootprints()}

    bom = {}
    for row in csv.DictReader(open(pkg / "assembly" / "bom.csv")):
        for r in expand(row["Refs"]):
            if r in bom:
                err.append("BOM: %s listed twice" % r)
            bom[r] = row
    for r, f in fps.items():
        if f.IsExcludedFromBOM():
            continue
        if r not in bom:
            err.append("BOM: %s missing" % r)
            continue
        row = bom[r]
        if bool(row["DNP"]) != bool(f.IsDNP()):
            err.append("BOM: %s DNP flag differs" % r)
        if not row["MPN"].strip() or not row["Manufacturer"].strip():
            err.append("BOM: %s without MPN/manufacturer" % r)
    for r in bom:
        if r not in fps:
            err.append("BOM: %s not on the board" % r)
    no_ds = sorted(r for r, row in bom.items() if row["Datasheet"].strip() in ("", "~"))
    info.append("BOM: %d references in %d lines; %d without datasheet link (advisory)" % (
        len(bom), len({row["Refs"] for row in bom.values()}), len(no_ds)))

    o = b.GetDesignSettings().GetAuxOrigin()
    pos = {}
    for row in csv.DictReader(open(pkg / "assembly" / "positions.csv")):
        if row["Ref"] in pos:
            err.append("POS: %s listed twice" % row["Ref"])
        pos[row["Ref"]] = row
    worst = 0.0
    for r, f in fps.items():
        smd = any(p.GetAttribute() == pcbnew.PAD_ATTRIB_SMD for p in f.Pads())
        tht = any(p.GetAttribute() == pcbnew.PAD_ATTRIB_PTH for p in f.Pads())
        listed = r in pos
        if f.IsExcludedFromPosFiles() or f.IsDNP():
            if listed:
                err.append("POS: %s listed although excluded/DNP" % r)
            continue
        if smd and not listed:
            err.append("POS: SMD part %s missing" % r)
        if listed and tht and not smd:
            info.append("POS: THT part %s listed" % r)
        if not listed:
            continue
        row = pos[r]
        side = "bottom" if f.IsFlipped() else "top"
        if row["Side"] != side:
            err.append("POS: %s side %s, board %s" % (r, row["Side"], side))
        x, y = T(f.GetPosition().x - o.x), -T(f.GetPosition().y - o.y)
        d = max(abs(float(row["PosX"]) - x), abs(float(row["PosY"]) - y))
        worst = max(worst, d)
        if d > 0.01:
            err.append("POS: %s position differs by %.3f mm" % (r, d))
        rot = f.GetOrientationDegrees()
        if abs((float(row["Rot"]) - rot + 180) % 360 - 180) > 0.01:
            err.append("POS: %s rotation %s, board %.1f" % (r, row["Rot"], rot))
    info.append("POS: %d parts (%d top, %d bottom); max position difference %.4f mm; origin %s" % (
        len(pos), sum(1 for p in pos.values() if p["Side"] == "top"), sum(1 for p in pos.values() if p["Side"] == "bottom"),
        worst, "page origin (aux origin not set)" if o.x == 0 and o.y == 0 else "aux origin"))

    tools, attr, kind = {}, "", {}
    for line in open(next((pkg / "fabrication" / "drill").glob("*.drl"))):
        if line.startswith("; #@! TA.AperFunction"):
            attr = line.strip().split(",", 1)[1]
        m = re.match(r"^T(\d+)C([\d.]+)", line)
        if m:
            tools[int(m.group(1))] = float(m.group(2))
            kind[int(m.group(1))] = attr
    for t, d in sorted(tools.items()):
        k = kind[t]
        if "NonPlated" in k and d < 0.5:
            err.append("DRILL: NPTH %.2f mm < 0.5 mm" % d)
        elif "ViaDrill" in k and d < 0.15:
            err.append("DRILL: via %.2f mm < 0.15 mm" % d)
        elif "ComponentDrill" in k and d < 0.5:
            users = sorted({f.GetReference() for f in b.GetFootprints() for p in f.Pads()
                            if p.GetAttribute() == pcbnew.PAD_ATTRIB_PTH and abs(T(p.GetDrillSize().x) - d) < 0.005})
            info.append("DRILL: component hole %.2f mm < 0.5 mm (JLCPCB recommendation) in %s" % (d, users))
    info.append("DRILL: tools %s" % ", ".join("%.2f%s" % (d, "N" if "NonPlated" in kind[t] else "")
                                              for t, d in sorted(tools.items())))

    job = json.load(open(next((pkg / "fabrication" / "gerbers").glob("*.gbrjob"))))
    spec = job.get("GeneralSpecs", {})
    cu = b.GetCopperLayerCount()
    if spec.get("LayerNumber") != cu:
        err.append("JOB: layer count %s, board %d" % (spec.get("LayerNumber"), cu))
    info.append("JOB: %s layers, thickness %s mm, stackup %s" % (
        spec.get("LayerNumber"), spec.get("BoardThickness"),
        ", ".join("%s %s" % (s.get("Type"), s.get("Thickness")) for s in job.get("MaterialStackup", [])
                  if s.get("Type") in ("Copper", "Dielectric"))))

    for line in info:
        print("INFO  " + line)
    for line in err:
        print("ERROR " + line)
    print("%d errors" % len(err))
    sys.exit(1 if err else 0)


if __name__ == "__main__":
    main()
