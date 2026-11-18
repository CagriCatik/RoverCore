#!/usr/bin/env python3
"""Mounting holes H1-H4 in the root schematic (mounting review, 2026-11-18).

Usage: <KiCad python> add_mounting_symbols.py
Adds four Mechanical:MountingHole symbols (copied verbatim from KiCad's library, no pins, not in BOM) with the
project footprint ProjectFootprints:MountingHole_3.2mm_M3_NPTH_Keepout to RoverCore.kicad_sch, plus a note that the
positions are provisional. Then build_board.py (sync) brings them onto the board and mounting_holes.py places them.
Refuses to run while KiCad is open, a lock file exists or the symbols are already there.
"""
from pathlib import Path
import re
import sys
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parent))
import schgen  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
SCH = ROOT / "RoverCore.kicad_sch"
LIB = Path("/Applications/KiCad/KiCad.app/Contents/SharedSupport/symbols/Mechanical.kicad_sym")
FP = "ProjectFootprints:MountingHole_3.2mm_M3_NPTH_Keepout"
NS = uuid.UUID("7d0b5a3e-6c1f-4f7a-9d3e-2b1c0a9f8e71")
REFS = [("H1", 63.5), ("H2", 81.28), ("H3", 99.06), ("H4", 116.84)]
Y = 177.8


def block(text, start):
    depth = 0
    for j in range(start, len(text)):
        if text[j] == "(":
            depth += 1
        elif text[j] == ")":
            depth -= 1
            if depth == 0:
                return text[start:j + 1]
    raise ValueError("unbalanced")


def prop(name, value, x, y, hide=False, justify=None):
    eff = "(font (size 1.27 1.27))" + (" (justify %s)" % justify if justify else "") + (" (hide yes)" if hide else "")
    return '\t\t(property "%s" "%s"\n\t\t\t(at %.2f %.2f 0)\n\t\t\t(effects %s)\n\t\t)\n' % (name, value, x, y, eff)


def main():
    schgen.require_closed_kicad()
    s = SCH.read_text()
    if '(lib_id "Mechanical:MountingHole")' in s:
        raise SystemExit("ABORTED: mounting hole symbols exist already")
    root = re.search(r"\(uuid ([0-9a-f-]+)\)", s).group(1)
    lib = LIB.read_text()
    sym = block(lib, lib.index('(symbol "MountingHole"'))
    sym = sym.replace('(symbol "MountingHole"', '(symbol "Mechanical:MountingHole"', 1)
    if "(lib_symbols)" not in s:
        raise SystemExit("ABORTED: root sheet already has lib_symbols; extend the script")
    s = s.replace("(lib_symbols)", "(lib_symbols\n\t\t" + sym.replace("\n", "\n\t") + "\n\t)", 1)
    items = []
    for ref, x in REFS:
        u = uuid.uuid5(NS, ref)
        items.append(
            '\t(symbol\n\t\t(lib_id "Mechanical:MountingHole")\n\t\t(at %.2f %.2f 0)\n\t\t(unit 1)\n'
            '\t\t(exclude_from_sim no)\n\t\t(in_bom no)\n\t\t(on_board yes)\n\t\t(dnp no)\n'
            '\t\t(fields_autoplaced yes)\n\t\t(uuid "%s")\n' % (x, Y, u)
            + prop("Reference", ref, x + 2.54, Y - 1.27, justify="left")
            + prop("Value", "M3 NPTH", x + 2.54, Y + 1.27, justify="left")
            + prop("Footprint", FP, x, Y, hide=True)
            + prop("Datasheet", "~", x, Y, hide=True)
            + prop("Description", "Mounting hole M3, NPTH 3.2 mm, provisional position (no chassis data)", x, Y,
                   hide=True)
            + '\t\t(instances\n\t\t\t(project "%s"\n\t\t\t\t(path "/%s"\n\t\t\t\t\t(reference "%s")\n'
              '\t\t\t\t\t(unit 1)\n\t\t\t\t)\n\t\t\t)\n\t\t)\n\t)\n' % (schgen.PROJECT, root, ref))
    note = ('\t(text "Mounting: H1-H4 M3 NPTH 3.2 mm. Positions PROVISIONAL - no chassis/enclosure data;\\n'
            'confirm against the vehicle mounting before fabrication (docs/vcu/rev1-platzierung.md 3n)."\n'
            '\t\t(exclude_from_sim no)\n\t\t(at 63.5 170.18 0)\n\t\t(effects (font (size 1.27 1.27)) (justify left))\n'
            '\t\t(uuid "%s")\n\t)\n' % uuid.uuid5(NS, "note"))
    k = s.index("\t(sheet_instances")
    s = s[:k] + note + "".join(items) + s[k:]
    SCH.write_text(s)
    print("added", ", ".join(r for r, _ in REFS), "to", SCH.name)


if __name__ == "__main__":
    main()
