#!/usr/bin/env python3
"""Synchronise RoverCore.kicad_pcb with the schematic; optional bootstrap placement.

Scripted equivalent of KiCad "Update PCB from Schematic" (KiCad 10.0.7, pcbnew Python module of the bundle).

Default (sync) - safe to run at any time, it never moves anything that is already on the board:
  - adds missing footprints (parked right of the board outline, listed in the output), removes footprints whose
    symbol is gone (board-only footprints stay), swaps a footprint whose library id changed and keeps its
    position, rotation, side and lock state;
  - reference, value, all symbol fields (extra fields hidden; fields no longer in the symbol removed),
    sheet name/file, symbol path (/sheet-uuid/symbol-uuid), DNP and BOM exclusion set AND cleared;
  - every pad gets exactly the netlist net; pads not in the netlist (mechanical pads, removed pins) get no net.
  - positions, sides, outline, zones, tracks and all drawings stay untouched.
--bootstrap [--sheet NAME] - applies the provisional placement from board_layout.py ON TOP of the sync:
  explicit positions and shelf packing (only footprints of NAME with --sheet) and, without --sheet, the
  provisional outline/frames/notes. It only replaces drawings in its own group "bootstrap_layout".
  It overwrites positions of the listed footprints, including manual fine placement - use deliberately.
Before saving, the run stops without writing on: unknown references in the layout, packing overflow,
unplaced footprints (bootstrap), footprints that cannot be loaded, netlist pins without a pad.

Run with the KiCad Python:
  /Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3 \
      hardware/scripts/build_board.py [--bootstrap [--sheet NAME]] [--dry-run] [--board PCB] [--layout FILE]
Refuses to run while KiCad lock files exist. Check afterwards: scripts/kit verify .  (schematic_parity)
"""
from pathlib import Path
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
GROUP = "bootstrap_layout"
MANDATORY = ("Reference", "Value", "Footprint", "Datasheet", "Description")


class Abort(Exception):
    pass


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
    fp = pcbnew.FootprintLoad(str(path), name) if path.is_dir() else None
    if fp is None:
        raise Abort("footprint not found: %s (%s)" % (fpid, path))
    fp.SetFPIDAsString(fpid)
    return fp


_LIB_FIELDS = {}


def library_fields(fpid):
    """Field names defined by the library footprint itself (e.g. KiLib_Generator); these are never removed."""
    if fpid not in _LIB_FIELDS:
        _LIB_FIELDS[fpid] = {f.GetName() for f in load_fp(fpid).GetFields()}
    return _LIB_FIELDS[fpid]


def courtyard(fp):
    """Front/back courtyard box (x, y, w, h) in mm, absolute; footprint bounding box if it has no courtyard."""
    fp.BuildCourtyardCaches()
    cy = fp.GetCourtyard(pcbnew.B_CrtYd if fp.GetLayer() == pcbnew.B_Cu else pcbnew.F_CrtYd)
    bb = cy.BBox() if cy.OutlineCount() else fp.GetBoundingBox(False)
    return (pcbnew.ToMM(bb.GetX()), pcbnew.ToMM(bb.GetY()), pcbnew.ToMM(bb.GetWidth()), pcbnew.ToMM(bb.GetHeight()))


def read_netlist(root):
    comps, pin_net = {}, {}
    for c in root.find("components"):
        ref = c.get("ref")
        props = {p.get("name"): p.get("value") for p in c.findall("property")}
        fields = {f.get("name"): (f.text or "") for f in c.find("fields")} if c.find("fields") is not None else {}
        sheet = c.find("sheetpath")
        comps[ref] = dict(value=c.findtext("value"), fpid=c.findtext("footprint"), fields=fields, props=props,
                          path=sheet.get("tstamps") + c.findtext("tstamps"))
    for n in root.find("nets"):
        for node in n.findall("node"):
            pin_net[(node.get("ref"), node.get("pin"))] = board_net_name(n.get("name"))
    return comps, pin_net


def park_position(board, k):
    """Parking slot for newly added footprints: columns right of the board outline."""
    bb = board.GetBoardEdgesBoundingBox()
    x0 = pcbnew.ToMM(bb.GetRight()) + 10.0 if bb.GetWidth() > 0 else 200.0
    y0 = pcbnew.ToMM(bb.GetTop()) if bb.GetWidth() > 0 else 0.0
    return pcbnew.VECTOR2I(MM(x0 + (k // 20) * 12.0), MM(y0 + (k % 20) * 8.0))


def sync(board, comps, pin_net, log):
    existing = {fp.GetReference(): fp for fp in board.GetFootprints()}
    # load every needed footprint first: nothing is changed if one is missing
    fresh = {}
    for ref, info in comps.items():
        fp = existing.get(ref)
        if fp is None or fp.GetFPIDAsString() != info["fpid"]:
            fresh[ref] = load_fp(info["fpid"])
    parked = 0
    for ref, new in sorted(fresh.items()):
        old = existing.get(ref)
        if old is not None:  # library id changed: keep placement
            new.SetPosition(old.GetPosition())
            if old.GetLayer() == pcbnew.B_Cu:
                new.Flip(new.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
            new.SetOrientation(old.GetOrientation())
            new.SetLocked(old.IsLocked())
            board.Remove(old)
            log.append("swapped %s -> %s (position kept)" % (ref, comps[ref]["fpid"]))
        else:
            new.SetPosition(park_position(board, parked))
            parked += 1
            log.append("added %s %s (parked outside the outline)" % (ref, comps[ref]["fpid"]))
        board.Add(new)
        existing[ref] = new
    for ref in sorted(set(existing) - set(comps)):
        if not existing[ref].IsBoardOnly():
            board.Remove(existing[ref])
            log.append("removed %s (no symbol)" % ref)
            del existing[ref]
    netinfo = {}
    for name in sorted(set(pin_net.values())):
        item = board.FindNet(name)
        if item is None:
            item = pcbnew.NETINFO_ITEM(board, name)
            board.Add(item)
        netinfo[name] = item
    for ref, info in comps.items():
        fp = existing[ref]
        fp.SetReference(ref)
        fp.SetValue(info["value"])
        wanted = {k: v for k, v in info["fields"].items() if k not in ("Footprint", "Value", "Reference")}
        keep = set(MANDATORY) | set(wanted) | library_fields(info["fpid"])
        for fld in list(fp.GetFields()):
            if fld.GetName() not in keep:  # symbol field that no longer exists
                fp.Remove(fld)
                log.append("%s: field %s removed" % (ref, fld.GetName()))
        for name, text in wanted.items():
            known = fp.HasField(name)
            fp.SetField(name, text)
            fld = fp.GetField(name)
            if not known and fld is not None and name not in MANDATORY:
                fld.SetVisible(False)  # like Update PCB from Schematic: extra fields hidden
                fld.SetLayer(pcbnew.B_Fab if fp.GetLayer() == pcbnew.B_Cu else pcbnew.F_Fab)
        fp.SetPath(pcbnew.KIID_PATH(info["path"]))
        fp.SetSheetname(info["props"].get("Sheetname", ""))
        fp.SetSheetfile(info["props"].get("Sheetfile", ""))
        attrs = fp.GetAttributes()
        attrs = attrs | pcbnew.FP_EXCLUDE_FROM_BOM if "exclude_from_bom" in info["props"] \
            else attrs & ~pcbnew.FP_EXCLUDE_FROM_BOM
        fp.SetAttributes(attrs)
        fp.SetDNP("dnp" in info["props"])
        numbers = set()
        for pad in fp.Pads():
            numbers.add(pad.GetNumber())
            net = pin_net.get((ref, pad.GetNumber())) if pad.GetNumber() else None
            if net is None:
                pad.SetNetCode(0)
            else:
                pad.SetNet(netinfo[net])
        missing = sorted(p for (r, p) in pin_net if r == ref and p not in numbers)
        if missing:
            raise Abort("%s: netlist pins without pad %s" % (ref, missing))
    return existing


def bootstrap(board, fps, layout, sheet, log):
    targets = {r for r, fp in fps.items() if sheet is None or fp.GetSheetname() == sheet}
    unknown = sorted(set(layout["parts"]) - set(fps))
    unknown += sorted(r for (*_, refs) in layout.get("pack", []) for r in refs.split() if r not in fps)
    if unknown:
        raise Abort("layout names unknown parts %s" % unknown)
    for ref, place in layout["parts"].items():
        if ref not in targets:
            continue
        fp = fps[ref]
        x, y, rot = place[:3]
        side = place[3] if len(place) > 3 else "F"
        if (side == "B") != (fp.GetLayer() == pcbnew.B_Cu):
            fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
        fp.SetOrientationDegrees(rot)
        fp.SetPosition(pcbnew.VECTOR2I(MM(x), MM(y)))
    packed, overflow = set(), []
    for (zx1, zy1, zx2, zy2, refs) in layout.get("pack", []):
        refs = [r for r in refs.split() if r in targets]
        cx, cy, row_h = zx1, zy1, 0.0
        for ref in sorted(refs, key=lambda r: -courtyard(fps[r])[3]):
            fp = fps[ref]
            if fp.GetLayer() == pcbnew.B_Cu:
                fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
            fp.SetOrientationDegrees(0)
            bx, by, bw, bh = courtyard(fp)
            if cx + bw > zx2:
                cx, cy, row_h = zx1, cy + row_h + 0.6, 0.0
            if cy + bh > zy2:
                overflow.append(ref)
            px, py = pcbnew.ToMM(fp.GetPosition().x) + cx - bx, pcbnew.ToMM(fp.GetPosition().y) + cy - by
            fp.SetPosition(pcbnew.VECTOR2I(MM(round(px, 3)), MM(round(py, 3))))  # 1 um grid: reproducible
            cx += bw + 0.6
            row_h = max(row_h, bh)
            packed.add(ref)
    unplaced = sorted(targets - set(layout["parts"]) - packed)
    if unplaced or overflow:
        raise Abort("bootstrap: unplaced %s, packing overflow %s" % (unplaced, overflow))
    log.append("bootstrap placement applied to %d footprints%s" % (len(targets), " of sheet " + sheet if sheet else ""))
    if sheet is None:
        draw_bootstrap(board, layout)
        log.append("bootstrap drawings (group %s) replaced" % GROUP)


def draw_bootstrap(board, layout):
    for g in list(board.Groups()):
        if g.GetName() == GROUP:
            for item in list(g.GetItems()):
                board.Remove(item)
            board.Remove(g)
    group = pcbnew.PCB_GROUP(board)
    group.SetName(GROUP)
    board.Add(group)

    def add(item):
        board.Add(item)
        group.AddItem(item)

    def rect(x1, y1, x2, y2, layer, width):
        r = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_RECTANGLE)
        r.SetStart(pcbnew.VECTOR2I(MM(x1), MM(y1)))
        r.SetEnd(pcbnew.VECTOR2I(MM(x2), MM(y2)))
        r.SetLayer(layer)
        r.SetWidth(MM(width))
        add(r)

    def text(s, x, y, layer, size):
        t = pcbnew.PCB_TEXT(board)
        t.SetText(s)
        t.SetPosition(pcbnew.VECTOR2I(MM(x), MM(y)))
        t.SetLayer(layer)
        t.SetTextSize(pcbnew.VECTOR2I(MM(size), MM(size)))
        t.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_LEFT)
        add(t)

    rect(*layout["outline"], pcbnew.Edge_Cuts, 0.1)
    for (x1, y1, x2, y2, label) in layout.get("zones", []):
        rect(x1, y1, x2, y2, pcbnew.Dwgs_User, 0.15)
        text(label, x1 + 0.5, y1 + 1.2, pcbnew.Dwgs_User, 1.0)
    for (cx, cy, dia, label) in layout.get("holes", []):
        c = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_CIRCLE)
        c.SetCenter(pcbnew.VECTOR2I(MM(cx), MM(cy)))
        c.SetEnd(pcbnew.VECTOR2I(MM(cx + dia / 2), MM(cy)))
        c.SetLayer(pcbnew.Cmts_User)
        c.SetWidth(MM(0.15))
        add(c)
    for (s, x, y) in layout.get("notes", []):
        text(s, x, y, pcbnew.Cmts_User, 1.2)


def load_layout(args):
    """LAYOUT from board_layout.py, or from the file given with --layout (tests)."""
    path = Path(args[args.index("--layout") + 1]) if "--layout" in args else Path(__file__).resolve().parent / "board_layout.py"
    scope = {}
    exec(compile(path.read_text(), str(path), "exec"), scope)
    return scope["LAYOUT"]


def main():
    require_closed()
    args = sys.argv[1:]
    sheet = args[args.index("--sheet") + 1] if "--sheet" in args else None
    if sheet and "--bootstrap" not in args:
        raise SystemExit("--sheet only together with --bootstrap")
    pcb = Path(args[args.index("--board") + 1]) if "--board" in args else PCB  # tests use a copy
    comps, pin_net = read_netlist(netlist())
    board = pcbnew.LoadBoard(str(pcb))
    log = []
    try:
        fps = sync(board, comps, pin_net, log)
        if "--bootstrap" in args:
            bootstrap(board, fps, load_layout(args), sheet, log)
    except Abort as e:
        raise SystemExit("ABORTED, board not written: %s" % e)
    for line in log:
        print(line)
    if "--dry-run" in args:
        print("dry run: board not written")
        return
    board.Save(str(pcb))
    print("saved: %d footprints, %d nets" % (len(fps), len(set(pin_net.values()))))


if __name__ == "__main__":
    main()
