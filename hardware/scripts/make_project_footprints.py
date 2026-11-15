#!/usr/bin/env python3
"""Create project footprints whose copper follows the manufacturer land patterns (O-26).

Graphics and 3D model are taken from the KiCad 10.0.7 footprint named in each
entry; all pads are replaced by the manufacturer dimensions below and the
courtyard is widened when the new pads need it. Sources (mm):

- Vishay WSL1020, doc 30183 rev 27-Mar-2024, "Solder Pad Dimensions": pad 1.00 x 5.65, outer span 3.50.
- Panasonic OS-CON SVPG case C8 (16SVPG270MX), land pattern AAB8000COL10 (31-Oct-25): a 2.1, b 9.1, c 1.6.
- ADI LTC7803 Rev B p. 36, MSE16 (05-08-1667 Rev F) recommended solder pad layout: pad 0.305 x 0.889,
  pitch 0.50, row gap 3.20-3.45 (midpoint used), exposed pad 1.651 x 2.845 (kept from KiCad, identical).
- Infineon BSC026N04LS Rev 2.3, Fig. 2 "Outline Boardpads (TDSON-8)": pins 0.5 x 0.925 at 2.863 from centre,
  pitch 1.27; drain 4.41 x 4.455 incl. four 0.6 x 0.8 fingers, edge 3.325 from centre. Paste windows of the
  drain body are an approximation of the drawing and must be checked before ordering a stencil.

Usage: python3 hardware/scripts/make_project_footprints.py   (overwrites only ProjectFootprints.pretty files)
"""
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.core import kicad_env  # noqa: E402

OUT = ROOT / "hardware/libraries/footprints/ProjectFootprints.pretty"


def pad(num, x, y, w, h, layers=("F.Cu", "F.Mask", "F.Paste"), shape="roundrect", extra=""):
    rr = "\n\t\t(roundrect_rratio 0.1)" if shape == "roundrect" else ""
    return ('\t(pad "%s" smd %s\n\t\t(at %s %s)\n\t\t(size %s %s)\n\t\t(layers %s)%s%s\n\t)\n'
            % (num, shape, round(x, 4), round(y, 4), round(w, 4), round(h, 4),
               " ".join('"%s"' % l for l in layers), rr, extra))


def wsl1020():
    return [pad("1", -1.25, 0, 1.00, 5.65), pad("2", 1.25, 0, 1.00, 5.65)]


def svpg_c8():
    return [pad("1", -2.8, 0, 3.5, 1.6), pad("2", 2.8, 0, 3.5, 1.6)]


def mse16(src_text):
    """Keep pad positions/numbering of the KiCad MSOP-16 rows, apply ADI pad size and row spacing; keep pad 17."""
    x = round(3.325 / 2 + 0.889 / 2, 4)  # gap midpoint 3.325 -> pad centre 2.1070
    pads = []
    for m in re.finditer(r'\t\(pad "(\d+)" smd \w+\n\t\t\(at ([-\d.]+) ([-\d.]+)\)', src_text):
        n, px, py = m.group(1), float(m.group(2)), float(m.group(3))
        if n == "17":
            continue
        pads.append(pad(n, x if px > 0 else -x, py, 0.889, 0.305))
    ep = re.findall(r'(?ms)^\t\(pad "17".*?^\t\)\n', src_text)
    return pads + ep


def tdson8():
    pads = []
    for i, y in enumerate((-1.905, -0.635, 0.635, 1.905), 1):
        pads.append(pad(str(i), -2.863, y, 0.925, 0.5, extra="\n\t\t(solder_paste_margin -0.05)"))
    pads.append(pad("5", (-1.13 + 2.525) / 2, 0, 3.655, 4.41, layers=("F.Cu", "F.Mask"), shape="rect"))
    for y in (-1.905, -0.635, 0.635, 1.905):
        pads.append(pad("5", 2.925, y, 0.8, 0.6, layers=("F.Cu", "F.Mask"), shape="rect"))
        pads.append(pad("", 2.95, y, 0.75, 0.5, layers=("F.Paste",), shape="rect"))
    cx = (-1.13 + 2.525) / 2
    for dx in (-0.85, 0.85):          # approximate 2 x 2 windows 1.5 x 1.5, 0.2 web (check Fig. 2)
        for dy in (-0.85, 0.85):
            pads.append(pad("", cx + dx, dy, 1.5, 1.5, layers=("F.Paste",), shape="rect"))
    return pads


ENTRIES = [
    ("R_Vishay_WSL1020", "Resistor_SMD.pretty/R_1020_2550Metric",
     "Vishay WSL1020 wide-terminal shunt, land pattern per Vishay doc 30183 (27-Mar-2024)", wsl1020),
    ("CP_Panasonic_OSCON_SVPG_C8", "Capacitor_SMD.pretty/CP_Elec_6.3x7.7",
     "Panasonic OS-CON SVPG case C8 (D6.3 L7.9), land pattern AAB8000COL10", svpg_c8),
    ("ADI_MSE16_MSOP-16-1EP_ThermalVias", "Package_SO.pretty/MSOP-16-1EP_3x4.039mm_P0.5mm_EP1.651x2.845mm_ThermalVias",
     "ADI MSE16 (05-08-1667 Rev F) per LTC7803 Rev B recommended solder pad layout; EP and vias from KiCad", None),
    ("Infineon_PG-TDSON-8_BSC026N04LS", "Package_SON.pretty/Infineon_PG-TDSON-8_6.15x5.15mm",
     "Infineon PG-TDSON-8 per BSC026N04LS Rev 2.3 Fig. 2; drain paste windows approximate", tdson8),
]


def extents(pads_text):
    xs, ys = [], []
    for m in re.finditer(r'\(at ([-\d.]+) ([-\d.]+)\)\n\t\t\(size ([-\d.]+) ([-\d.]+)\)', pads_text):
        x, y, w, h = map(float, m.groups())
        xs += [x - w / 2, x + w / 2]
        ys += [y - h / 2, y + h / 2]
    return min(xs), max(xs), min(ys), max(ys)


def build(name, src_rel, descr, fn):
    src = (kicad_env.shared_support() / "footprints" / (src_rel + ".kicad_mod")).read_text()
    old_name = re.search(r'^\(footprint "([^"]+)"', src).group(1)
    pads = "".join(mse16(src) if fn is None else fn())
    body = re.sub(r'(?ms)^\t\(pad .*?^\t\)\n', "", src)
    body = body.replace('(footprint "%s"' % old_name, '(footprint "%s"' % name, 1)
    body = re.sub(r'\(descr "[^"]*"\)', '(descr "%s; derived from KiCad %s")' % (descr, old_name), body, count=1)
    body = body.replace('(property "Value" "%s"' % old_name, '(property "Value" "%s"' % name)
    # courtyard: union of the KiCad courtyard and the new pads + 0.25 mm
    cx0, cx1, cy0, cy1 = extents(pads)
    pts = []
    for m in re.finditer(r'(?ms)^\t\(fp_\w+\n.*?^\t\)\n', body):   # one graphic block at a time
        if '(layer "F.CrtYd")' in m.group(0):
            pts += [tuple(map(float, p)) for p in re.findall(r'\((?:start|end|xy|mid) ([-\d.]+) ([-\d.]+)\)', m.group(0))]
    if pts:
        cx0, cx1 = min(cx0 - 0.25, min(p[0] for p in pts)), max(cx1 + 0.25, max(p[0] for p in pts))
        cy0, cy1 = min(cy0 - 0.25, min(p[1] for p in pts)), max(cy1 + 0.25, max(p[1] for p in pts))
    body = re.sub(r'(?ms)^\t\(fp_\w+\n(?:(?!^\t\(fp_|^\t\(pad|^\t\(embedded).)*?\(layer "F\.CrtYd"\).*?^\t\)\n', "", body)
    crt_rect = ('\t(fp_rect\n\t\t(start %s %s)\n\t\t(end %s %s)\n\t\t(stroke\n\t\t\t(width 0.05)\n\t\t\t(type solid)\n'
                '\t\t)\n\t\t(fill no)\n\t\t(layer "F.CrtYd")\n\t)\n') % (round(cx0, 2), round(cy0, 2), round(cx1, 2), round(cy1, 2))
    anchor = "\t(embedded_fonts no)\n"
    body = body.replace(anchor, crt_rect + pads + anchor, 1)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / (name + ".kicad_mod")).write_text(body)
    return name, (round(cx0, 2), round(cy0, 2), round(cx1, 2), round(cy1, 2))


if __name__ == "__main__":
    for e in ENTRIES:
        print(*build(*e))
