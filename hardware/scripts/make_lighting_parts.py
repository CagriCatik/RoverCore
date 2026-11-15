#!/usr/bin/env python3
"""Project library items for the Lighting_IO sheet.

- Symbol TPS2553DBV: TI SLVS841G (Oct 2026) Table 5-1, SOT-23 (DBV): 1 IN, 2 GND, 3 EN (active high for
  TPS2553), 4 FAULT (open drain, active low), 5 ILIM, 6 OUT. KiCad 10.0.7 has no TPS2553 symbol.
- Footprint MagneticBuzzer_SameSky_CMT-8540S-SMT: Same Sky CMT-8540S-SMT-TR datasheet rev 1.04 (2024-09-11),
  "Recommended PCB Layout, Top View": four 2.5 x 2.5 mm pads, 7.0 mm centre pitch (9.5 mm outside).
  Top view: '+' = bottom-right pad, '-' = top-right pad. The datasheet does not state the function of the
  two left pads, so they are mechanical pads without a number (no net). Body 8.5 x 8.5 mm.

Usage: python3 hardware/scripts/make_lighting_parts.py   (rewrites only these two library items)
"""
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from make_devkit_socket import SYM_LIB, FP_DIR, prop, font, rect, line, poly, text  # noqa: E402

SYM = "TPS2553DBV"
FP = "MagneticBuzzer_SameSky_CMT-8540S-SMT"


def pin(kind, number, name, x, y, angle):
    return ('\t\t\t(pin %s line\n\t\t\t\t(at %s %s %d)\n\t\t\t\t(length 2.54)\n\t\t\t\t(name "%s"\n\t\t\t\t\t%s\n'
            '\t\t\t\t)\n\t\t\t\t(number "%s"\n\t\t\t\t\t%s\n\t\t\t\t)\n\t\t\t)\n') % (kind, x, y, angle, name, font(), number, font())


def symbol():
    pins = (pin("power_in", "1", "IN", -10.16, 2.54, 0) + pin("input", "3", "EN", -10.16, -2.54, 0)
            + pin("power_in", "2", "GND", 0, -7.62, 90) + pin("power_out", "6", "OUT", 10.16, 2.54, 180)
            + pin("open_collector", "4", "~{FAULT}", 10.16, 0, 180) + pin("passive", "5", "ILIM", 10.16, -2.54, 180))
    return ('\t(symbol "%s"\n\t\t(exclude_from_sim no)\n\t\t(in_bom yes)\n\t\t(on_board yes)\n' % SYM
            + prop("Reference", "U", -7.62, 6.35, justify="left")
            + prop("Value", SYM, 7.62, 6.35, justify="right")
            + prop("Footprint", "Package_TO_SOT_SMD:SOT-23-6", 0, -10.16, hide=True)
            + prop("Datasheet", "https://www.ti.com/lit/pdf/SLVS841", 0, -12.7, hide=True)
            + prop("Description", "Current-limited power-distribution switch, 2.5-6.5 V, ILIM 75 mA-1.7 A via RILIM, "
                   "EN active high, FAULT open drain (TI SLVS841G Table 5-1, DBV)", 0, 0, hide=True)
            + prop("ki_keywords", "power switch current limit", 0, 0, hide=True)
            + '\t\t(symbol "%s_0_1"\n\t\t\t(rectangle\n\t\t\t\t(start -7.62 5.08)\n\t\t\t\t(end 7.62 -5.08)\n'
              '\t\t\t\t(stroke\n\t\t\t\t\t(width 0.254)\n\t\t\t\t\t(type default)\n\t\t\t\t)\n\t\t\t\t(fill\n'
              '\t\t\t\t\t(type background)\n\t\t\t\t)\n\t\t\t)\n\t\t)\n' % SYM
            + '\t\t(symbol "%s_1_1"\n%s\t\t)\n\t\t(embedded_fonts no)\n\t)\n' % (SYM, pins))


def write_symbol():
    t = SYM_LIB.read_text()
    block = symbol()
    m = re.search(r'(?ms)^\t\(symbol "%s"\n.*?^\t\)\n' % re.escape(SYM), t)
    if m:
        t = t[:m.start()] + block + t[m.end():]
    else:
        i = t.rstrip().rfind(")")
        t = t[:i] + block + t[i:]
    SYM_LIB.write_text(t)


def smd(num, x, y):
    return ('\t(pad "%s" smd rect\n\t\t(at %s %s)\n\t\t(size 2.5 2.5)\n\t\t(layers "F.Cu" "F.Mask" "F.Paste")\n\t)\n'
            % (num, x, y))


def footprint():
    b = ('(footprint "%s"\n\t(version 20260206)\n\t(generator "rovercore_make_lighting_parts")\n\t(generator_version "10.0")\n'
         '\t(layer "F.Cu")\n\t(descr "Same Sky CMT-8540S-SMT-TR magnetic buzzer 8.5 x 8.5 mm, land pattern per datasheet rev 1.04 '
         '(2024-09-11): pads 2.5 x 2.5 mm, pitch 7.0 mm; pad 1 = +, pad 2 = -, left pads mechanical (function not stated)")\n'
         '\t(tags "buzzer magnetic Same Sky CMT-8540S")\n') % FP
    b += text("Reference", "REF**", 0, -6.0, "F.SilkS")
    b += text("Value", FP, 0, 6.0, "F.Fab")
    for k in ("Datasheet", "Description"):
        b += ('\t(property "%s" ""\n\t\t(at 0 0 0)\n\t\t(layer "F.Fab")\n\t\t(hide yes)\n\t\t(effects\n\t\t\t(font\n'
              '\t\t\t\t(size 1.27 1.27)\n\t\t\t\t(thickness 0.15)\n\t\t\t)\n\t\t)\n\t)\n') % k
    b += "\t(attr smd)\n"
    b += rect("F.Fab", -4.25, -4.25, 4.25, 4.25, 0.1)
    b += text("user", "${REFERENCE}", 0, 0, "F.Fab", 1.0)
    # silkscreen: outline segments between the pads, '+' mark next to pad 1
    for (x1, y1, x2, y2) in ((-2.0, -4.4, 2.0, -4.4), (-2.0, 4.4, 2.0, 4.4), (-4.4, -2.0, -4.4, 2.0), (4.4, -2.0, 4.4, 2.0)):
        b += line("F.SilkS", x1, y1, x2, y2, 0.12)
    b += text("user", "+", 5.9, 3.5, "F.SilkS", 1.2)
    b += rect("F.CrtYd", -5.0, -5.0, 5.0, 5.0, 0.05)
    b += smd("1", 3.5, 3.5) + smd("2", 3.5, -3.5) + smd("", -3.5, 3.5) + smd("", -3.5, -3.5)
    b += "\t(embedded_fonts no)\n)\n"
    (FP_DIR / (FP + ".kicad_mod")).write_text(b)


if __name__ == "__main__":
    write_symbol()
    footprint()
    print("wrote", SYM, "and", FP)
