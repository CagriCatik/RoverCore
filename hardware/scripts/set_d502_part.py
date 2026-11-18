#!/usr/bin/env python3
"""D502 status LED: part number and BOM data (O-28, 2026-11-18).

Usage: <KiCad python> set_d502_part.py
Würth Elektronik 150060RS75000 (WL-SMCW, 0603, red, AlInGaP), from the manufacturer datasheet
https://www.we-online.com/components/products/datasheet/150060RS75000.pdf (rev. 002.009, 2019-02-26):
VF typ 2.0 V / max 2.4 V at 20 mA, IF max 30 mA, dominant wavelength 625 nm, pin 1 = cathode (polarity mark),
1.6 x 0.8 x 0.7 mm. Meets the requirement VF <= 2.4 V (already at 20 mA; at about 1.5 mA lower). Pin 1 = cathode
matches Device:LED / LED_0603_1608Metric (pad 1 = K, net GND). LCSC number not verified, so no LCSC field.
Edits only the D502 symbol properties in Controller.kicad_sch; then build_board.py syncs the fields to the board.
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import schgen  # noqa: E402

SCH = Path(__file__).resolve().parents[2] / "Controller.kicad_sch"
URL = "https://www.we-online.com/components/products/datasheet/150060RS75000.pdf"


def main():
    schgen.require_closed_kicad()
    s = SCH.read_text()
    i = s.index('(property "Reference" "D502"')
    start = s.rfind("\t(symbol\n", 0, i)
    end = s.index("\t\t(pin ", i)
    blk = s[start:end]
    if '"150060RS75000"' in blk:
        raise SystemExit("ABORTED: D502 already set")
    new = blk.replace('(property "Value" "LED status"', '(property "Value" "LED red"', 1)
    new = new.replace('(property "Datasheet" "~"', '(property "Datasheet" "%s"' % URL, 1)
    old_desc = ('(property "Description" "Status LED, 0603, AlGaInP (VF <= 2.4 V at 2 mA required with 3.3 V drive); '
                'part open (O-28)"')
    if old_desc not in new:
        raise SystemExit("ABORTED: unexpected D502 description")
    new = new.replace(old_desc, '(property "Description" "Status LED, 0603, red AlInGaP, VF max 2.4 V at 20 mA; '
                                'about 1.5 mA via R504 1 k at 3.3 V (estimate)"', 1)
    extra = ''.join('\t\t(property "%s" "%s"\n\t\t\t(at 35.56 228.6 0)\n\t\t\t(effects\n\t\t\t\t(font\n'
                    '\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t)\n\t\t\t\t(hide yes)\n\t\t\t)\n\t\t)\n' % kv
                    for kv in (("Manufacturer", "Würth Elektronik"), ("MPN", "150060RS75000")))
    new = new + extra
    SCH.write_text(s[:start] + new + s[end:])
    print("D502 set to Würth Elektronik 150060RS75000")


if __name__ == "__main__":
    main()
