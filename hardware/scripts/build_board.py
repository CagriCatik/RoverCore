#!/usr/bin/env python3
"""Transfer the schematic footprints into RoverCore.kicad_pcb and apply the provisional placement.

Scripted equivalent of KiCad "Update PCB from Schematic" for the first board import (KiCad 10.0.7, pcbnew
Python module of the KiCad bundle): every schematic component gets its library footprint with reference,
value, symbol fields, sheet name/file and the symbol path (/sheet-uuid/symbol-uuid), so a later
"Update PCB from Schematic" in the PCB editor matches the footprints by path. Pads get the netlist nets.
Footprints already on the board keep their position unless the layout spec gives one.
Placement, provisional outline and provisional holes come from board_layout.py (positions only).

Run with the KiCad Python:  /Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3 \
    hardware/scripts/build_board.py [--dump SIZES.json]
Refuses to run while KiCad lock files exist. Check afterwards with: scripts/kit verify .  (schematic_parity)
"""
from pathlib import Path
import json
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

import pcbnew

ROOT = Path(__file__).resolve().parents[2]
PCB = ROOT / "RoverCore.kicad_pcb"
CLI = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
FP_GLOBAL = Path("/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints")
FP_LOCAL = {"ProjectFootprints": ROOT / "hardware/libraries/footprints/ProjectFootprints.pretty"}
MM = pcbnew.FromMM


def require_closed():
    locks = list(ROOT.glob("~*.lck")) + list(ROOT.glob("*.lck"))
    if locks:
        raise SystemExit("lock files present (KiCad open?): %s" % [p.name for p in locks])


def netlist():
    with tempfile.TemporaryDirectory() as d:
        out = Path(d) / "net.xml"
        subprocess.run([CLI, "sch", "export", "netlist", "--format", "kicadxml", "-o", str(out),
                        str(ROOT / "RoverCore.kicad_sch")], check=True, capture_output=True)
        return ET.parse(out).getroot()


def board_net_name(name):
    """The XML netlist unescapes names; KiCad keeps '/' inside a pin name escaped as {slash} (not a sheet separator)."""
    if name.startswith("unconnected-("):
        return "unconnected-(" + name[len("unconnected-("):-1].replace("/", "{slash}") + ")"
    return name


def load_fp(fpid):
    lib, name = fpid.split(":", 1)
    path = FP_LOCAL.get(lib, FP_GLOBAL / (lib + ".pretty"))
    fp = pcbnew.FootprintLoad(str(path), name)
    if fp is None:
        raise SystemExit("footprint not found: %s (%s)" % (fpid, path))
    fp.SetFPIDAsString(fpid)
    return fp


def courtyard(fp):
    """Front courtyard box (x, y, w, h) in mm, absolute; footprint bounding box if it has no courtyard."""
    fp.BuildCourtyardCaches()
    cy = fp.GetCourtyard(pcbnew.F_CrtYd)
    bb = cy.BBox() if cy.OutlineCount() else fp.GetBoundingBox(False)
    return (pcbnew.ToMM(bb.GetX()), pcbnew.ToMM(bb.GetY()), pcbnew.ToMM(bb.GetWidth()), pcbnew.ToMM(bb.GetHeight()))


def main():
    require_closed()
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from board_layout import LAYOUT  # noqa: E402
    root = netlist()
    board = pcbnew.LoadBoard(str(PCB))
    existing = {fp.GetReference(): fp for fp in board.GetFootprints()}
    comps = {}
    for c in root.find("components"):
        ref = c.get("ref")
        props = {p.get("name"): p.get("value") for p in c.findall("property")}
        fields = {f.get("name"): (f.text or "") for f in c.find("fields")} if c.find("fields") is not None else {}
        sheet = c.find("sheetpath")
        comps[ref] = dict(value=c.findtext("value"), fpid=c.findtext("footprint"), fields=fields, props=props,
                          path=sheet.get("tstamps") + c.findtext("tstamps"))
    added = []
    for ref, info in sorted(comps.items()):
        fp = existing.get(ref)
        if fp is None or fp.GetFPIDAsString() != info["fpid"]:
            if fp is not None:
                board.Remove(fp)
            fp = load_fp(info["fpid"])
            board.Add(fp)
            added.append(ref)
        fp.SetReference(ref)
        fp.SetValue(info["value"])
        for name, text in info["fields"].items():
            if name not in ("Footprint", "Value", "Reference"):
                fp.SetField(name, text)
                fld = fp.GetField(name)
                if fld is not None and name not in ("Datasheet", "Description"):
                    fld.SetVisible(False)  # like Update PCB from Schematic: extra fields hidden
                    fld.SetLayer(pcbnew.F_Fab if fp.GetLayer() == pcbnew.F_Cu else pcbnew.B_Fab)
        fp.SetPath(pcbnew.KIID_PATH(info["path"]))
        fp.SetSheetname(info["props"].get("Sheetname", ""))
        fp.SetSheetfile(info["props"].get("Sheetfile", ""))
        attrs = fp.GetAttributes()
        if "exclude_from_bom" in info["props"]:
            attrs |= pcbnew.FP_EXCLUDE_FROM_BOM
        fp.SetAttributes(attrs)
        if "dnp" in info["props"]:
            fp.SetDNP(True)
    for ref in sorted(set(existing) - set(comps)):
        if not existing[ref].IsBoardOnly():
            board.Remove(existing[ref])
    # nets
    netinfo = {}
    for n in root.find("nets"):
        name = board_net_name(n.get("name"))
        item = board.FindNet(name)
        if item is None:
            item = pcbnew.NETINFO_ITEM(board, name)
            board.Add(item)
        netinfo[name] = item
    fps = {fp.GetReference(): fp for fp in board.GetFootprints()}
    for n in root.find("nets"):
        for node in n.findall("node"):
            fp = fps[node.get("ref")]
            for pad in fp.Pads():
                if pad.GetNumber() == node.get("pin"):
                    pad.SetNet(netinfo[board_net_name(n.get("name"))])
    # placement (positions in mm, rotation in degrees, side "F"/"B")
    for ref, place in LAYOUT["parts"].items():
        fp = fps.get(ref)
        if fp is None:
            raise SystemExit("layout names unknown part %s" % ref)
        x, y, rot = place[:3]
        side = place[3] if len(place) > 3 else "F"
        if (side == "B") != (fp.GetLayer() == pcbnew.B_Cu):
            fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
        fp.SetOrientationDegrees(rot)
        fp.SetPosition(pcbnew.VECTOR2I(MM(x), MM(y)))
    # shelf packing of the small parts of each functional group (courtyard boxes, rotation 0, 0.6 mm gap)
    packed, overflow = set(), []
    for (zx1, zy1, zx2, zy2, refs) in LAYOUT.get("pack", []):
        cx, cy, row_h = zx1, zy1, 0.0
        for ref in sorted(refs.split(), key=lambda r: -courtyard(fps[r])[3]):
            fp = fps[ref]
            fp.SetOrientationDegrees(0)
            bx, by, bw, bh = courtyard(fp)
            if cx + bw > zx2:
                cx, cy, row_h = zx1, cy + row_h + 0.6, 0.0
            if cy + bh > zy2:
                overflow.append(ref)
            pos = fp.GetPosition()
            fp.SetPosition(pcbnew.VECTOR2I(pos.x + MM(cx - bx), pos.y + MM(cy - by)))
            cx += bw + 0.6
            row_h = max(row_h, bh)
            packed.add(ref)
    unplaced = sorted(set(fps) - set(LAYOUT["parts"]) - packed)
    if unplaced or overflow:
        print("UNPLACED:", unplaced, "OVERFLOW:", overflow)
    # provisional outline and drawings (own layers, replaced on every run)
    for d in list(board.GetDrawings()):
        if d.GetLayer() in (pcbnew.Edge_Cuts, pcbnew.Dwgs_User, pcbnew.Cmts_User):
            board.Remove(d)
    x1, y1, x2, y2 = LAYOUT["outline"]
    rect = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_RECTANGLE)
    rect.SetStart(pcbnew.VECTOR2I(MM(x1), MM(y1)))
    rect.SetEnd(pcbnew.VECTOR2I(MM(x2), MM(y2)))
    rect.SetLayer(pcbnew.Edge_Cuts)
    rect.SetWidth(MM(0.1))
    board.Add(rect)
    for (bx1, by1, bx2, by2, label) in LAYOUT.get("zones", []):
        r = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_RECTANGLE)
        r.SetStart(pcbnew.VECTOR2I(MM(bx1), MM(by1)))
        r.SetEnd(pcbnew.VECTOR2I(MM(bx2), MM(by2)))
        r.SetLayer(pcbnew.Dwgs_User)
        r.SetWidth(MM(0.15))
        board.Add(r)
        t = pcbnew.PCB_TEXT(board)
        t.SetText(label)
        t.SetPosition(pcbnew.VECTOR2I(MM(bx1 + 0.5), MM(by1 + 1.2)))
        t.SetLayer(pcbnew.Dwgs_User)
        t.SetTextSize(pcbnew.VECTOR2I(MM(1.0), MM(1.0)))
        t.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_LEFT)
        board.Add(t)
    for (cx, cy, dia, label) in LAYOUT.get("holes", []):
        c = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_CIRCLE)
        c.SetCenter(pcbnew.VECTOR2I(MM(cx), MM(cy)))
        c.SetEnd(pcbnew.VECTOR2I(MM(cx + dia / 2), MM(cy)))
        c.SetLayer(pcbnew.Cmts_User)
        c.SetWidth(MM(0.15))
        board.Add(c)
    for (text, x, y) in LAYOUT.get("notes", []):
        t = pcbnew.PCB_TEXT(board)
        t.SetText(text)
        t.SetPosition(pcbnew.VECTOR2I(MM(x), MM(y)))
        t.SetLayer(pcbnew.Cmts_User)
        t.SetTextSize(pcbnew.VECTOR2I(MM(1.2), MM(1.2)))
        t.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_LEFT)
        board.Add(t)
    board.Save(str(PCB))
    print("footprints: %d (added %d), nets: %d" % (len(fps), len(added), len(netinfo)))
    if "--dump" in sys.argv:
        out = {}
        for fp in board.GetFootprints():
            cy = fp.GetCourtyard(pcbnew.F_CrtYd if fp.GetLayer() == pcbnew.F_Cu else pcbnew.B_CrtYd)
            bb = cy.BBox() if cy.OutlineCount() else fp.GetBoundingBox(False)
            out[fp.GetReference()] = dict(w=pcbnew.ToMM(bb.GetWidth()), h=pcbnew.ToMM(bb.GetHeight()),
                                          cx=pcbnew.ToMM(bb.Centre().x - fp.GetPosition().x),
                                          cy=pcbnew.ToMM(bb.Centre().y - fp.GetPosition().y),
                                          fpid=fp.GetFPIDAsString(), sheet=fp.GetSheetname())
        Path(sys.argv[sys.argv.index("--dump") + 1]).write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
