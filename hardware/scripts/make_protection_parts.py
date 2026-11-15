#!/usr/bin/env python3
"""Project symbols for the O-21 / Actuators protection rework (KiCad 10.0.7 has no matching symbols).

- BAT54_SOT23: Nexperia BAT54 product data sheet (2022-07-01) Table 2: 1 anode, 2 n.c., 3 cathode.
  Footprint Package_TO_SOT_SMD:SOT-23 (pad 2 unused).
- TLV809E_DBZ: TI SLVSES2J Table 6-1, DBZ standard pinout: 1 GND, 2 RESET (push-pull, active low), 3 VDD.

Usage: python3 hardware/scripts/make_protection_parts.py   (rewrites only these two symbols)
"""
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from make_devkit_socket import SYM_LIB, prop  # noqa: E402
from make_lighting_parts import pin  # noqa: E402


def body(name, start, end):
    return ('\t\t(symbol "%s_0_1"\n\t\t\t(rectangle\n\t\t\t\t(start %s %s)\n\t\t\t\t(end %s %s)\n\t\t\t\t(stroke\n'
            '\t\t\t\t\t(width 0.254)\n\t\t\t\t\t(type default)\n\t\t\t\t)\n\t\t\t\t(fill\n\t\t\t\t\t(type background)\n'
            '\t\t\t\t)\n\t\t\t)\n\t\t)\n') % (name, start[0], start[1], end[0], end[1])


def diode_body(name):
    # triangle anode (left) -> cathode bar (right), standard diode drawing
    return ('\t\t(symbol "%s_0_1"\n'
            '\t\t\t(polyline\n\t\t\t\t(pts\n\t\t\t\t\t(xy -1.27 1.27) (xy -1.27 -1.27) (xy 1.27 0) (xy -1.27 1.27)\n\t\t\t\t)\n'
            '\t\t\t\t(stroke\n\t\t\t\t\t(width 0.254)\n\t\t\t\t\t(type default)\n\t\t\t\t)\n\t\t\t\t(fill\n\t\t\t\t\t(type none)\n\t\t\t\t)\n\t\t\t)\n'
            '\t\t\t(polyline\n\t\t\t\t(pts\n\t\t\t\t\t(xy 1.27 1.27) (xy 1.27 -1.27) (xy 1.778 -1.27)\n\t\t\t\t)\n'
            '\t\t\t\t(stroke\n\t\t\t\t\t(width 0.254)\n\t\t\t\t\t(type default)\n\t\t\t\t)\n\t\t\t\t(fill\n\t\t\t\t\t(type none)\n\t\t\t\t)\n\t\t\t)\n'
            '\t\t\t(polyline\n\t\t\t\t(pts\n\t\t\t\t\t(xy 1.27 1.27) (xy 0.762 1.27)\n\t\t\t\t)\n'
            '\t\t\t\t(stroke\n\t\t\t\t\t(width 0.254)\n\t\t\t\t\t(type default)\n\t\t\t\t)\n\t\t\t\t(fill\n\t\t\t\t\t(type none)\n\t\t\t\t)\n\t\t\t)\n'
            '\t\t)\n') % name


def symbol(name, ref, fp, ds, descr, pins, graphics, ref_at=(0, 3.81), val_at=(0, -3.81)):
    return ('\t(symbol "%s"\n\t\t(pin_names\n\t\t\t(hide yes)\n\t\t)\n\t\t(exclude_from_sim no)\n\t\t(in_bom yes)\n\t\t(on_board yes)\n' % name
            if ref == "D" else '\t(symbol "%s"\n\t\t(exclude_from_sim no)\n\t\t(in_bom yes)\n\t\t(on_board yes)\n' % name) \
        + prop("Reference", ref, ref_at[0], ref_at[1]) + prop("Value", name, val_at[0], val_at[1]) \
        + prop("Footprint", fp, 0, -6.35, hide=True) + prop("Datasheet", ds, 0, -8.89, hide=True) \
        + prop("Description", descr, 0, 0, hide=True) + graphics \
        + '\t\t(symbol "%s_1_1"\n%s\t\t)\n\t\t(embedded_fonts no)\n\t)\n' % (name, pins)


def put(block, name):
    t = SYM_LIB.read_text()
    m = re.search(r'(?ms)^\t\(symbol "%s"\n.*?^\t\)\n' % re.escape(name), t)
    if m:
        t = t[:m.start()] + block + t[m.end():]
    else:
        i = t.rstrip().rfind(")")
        t = t[:i] + block + t[i:]
    SYM_LIB.write_text(t)


if __name__ == "__main__":
    put(symbol("BAT54_SOT23", "D", "Package_TO_SOT_SMD:SOT-23",
               "https://www.lcsc.com/datasheet/lcsc_datasheet_2407241045_Nexperia-BAT54-215_C85084.pdf",
               "Schottky 30 V 200 mA, SOT-23 single: 1 anode, 2 n.c., 3 cathode (Nexperia BAT54, 2022-07-01)",
               pin("passive", "1", "A", -3.81, 0, 0) + pin("passive", "3", "K", 3.81, 0, 180),
               diode_body("BAT54_SOT23")), "BAT54_SOT23")
    put(symbol("TLV809E_DBZ", "U", "Package_TO_SOT_SMD:SOT-23",
               "https://www.ti.com/lit/pdf/SLVSES2",
               "Voltage supervisor, push-pull active-low RESET; DBZ standard pinout 1 GND, 2 RESET, 3 VDD (TI SLVSES2J)",
               pin("power_in", "3", "VDD", 0, 7.62, 270) + pin("power_in", "1", "GND", 0, -7.62, 90)
               + pin("output", "2", "~{RESET}", 12.7, 0, 180),
               body("TLV809E_DBZ", (-5.08, 5.08), (10.16, -5.08)), ref_at=(-5.08, 6.35), val_at=(3.81, 6.35)), "TLV809E_DBZ")
    print("wrote BAT54_SOT23 and TLV809E_DBZ")
