#!/usr/bin/env python3
"""Render schematic review images (overview + one detail per functional group) for every sheet.

The images are RENDERED VIEWS: kicad-cli 10.0.7 exports each sheet as SVG, rsvg-convert rasterises it.
They are not GUI screenshots. Detail crops are computed from the positions of the group's symbols in the
current sheet file, at a fixed scale, so 'before' and 'after' show the same functional group at the same zoom
even if the parts moved.

Usage: python3 hardware/scripts/render_schematic_review.py OUTPUT_DIR
Writes OUTPUT_DIR/<Sheet>_overview.png and OUTPUT_DIR/<Sheet>_NN_<group>.png (generated output, not source).
"""
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.core import kicad_env  # noqa: E402

DETAIL_DPI = 300           # detail crops: 300 dpi -> 11.8 px/mm
OVERVIEW_WIDTH = 2480      # overview: whole page, about 150 dpi on A3
MARGIN = {"U": 30.0, "J": 22.0}
DEFAULT_MARGIN = 20.0

GROUPS = {
    "RoverCore": [("sheet-blocks", ["*"])],
    "Power": [
        ("battery-input-and-fuse", ["J101", "F101", "TP101"]),
        ("reverse-protection-and-tvs", ["Q101", "D101", "D102", "R101", "TP102"]),
        ("bulk-capacitors", ["C101", "C102", "TP103"]),
    ],
    "LogicPower": [
        ("buck-regulator", ["U301", "L301", "C301", "C302", "C303", "C304"]),
        ("feedback-and-enable", ["R301", "R302", "R303", "R304", "R305", "C305"]),
        ("output-capacitors", ["C306", "C307", "TP301", "TP302"]),
    ],
    "ServoPower": [
        ("input-and-power-stage", ["C401", "C402", "C403", "C404", "C405", "Q401", "Q402", "L401", "RS401"]),
        ("controller-and-bootstrap", ["U401", "D401", "C411", "C412", "C413", "C414", "C418", "C419", "R413"]),
        ("run-and-default-off", ["R405", "R406", "C420", "Q403", "Q404", "R407", "R414", "R415", "Q407", "R420"]),
        ("current-sense-and-kelvin", ["NT401", "NT402", "RF401", "CF401", "NT404", "NT405", "RS402", "U402", "C416"]),
        ("output-and-feedback", ["C406", "C407", "C408", "C409", "C410", "NT403", "R403", "R404", "TP401", "TP402"]),
        ("measurement-outputs", ["R410", "R411", "C417", "D403", "R417", "Q405", "Q406", "R418", "R419",
                                 "R412", "C415", "D404", "R416", "TP403"]),
    ],
    "Controller": [
        ("devkit-socket", ["U501"]),
        ("5v-feed-and-3v3", ["D501", "TP503", "C501", "C502", "TP502", "TP504"]),
        ("supervisor-and-vbat-sense", ["U504", "C505", "R510", "Q505", "Q506", "R505", "R506", "R507", "R508", "R509",
                                       "C504", "D506", "TP505"]),
        ("operator-and-defaults", ["R501", "R502", "SW501", "R504", "D502", "TP501"]),
        ("programming-and-restart", ["SW502", "SW503"]),
        ("restart-interlock", ["U505", "U506", "R515", "R516", "R517", "C506", "C507", "C508"]),
        ("enable-button-node", ["R502", "R518", "SW501"]),
    ],
    "Sensors_Display": [
        ("imu-j115", ["J115", "R803"]),
        ("i2c-bus", ["R801", "R802", "TP801", "TP802"]),
        ("oled-j116", ["J116"]),
    ],
    "Actuators": [
        ("buffer-u201", ["U201", "C201", "C202", "R209"]),
        ("oe-gate-u204", ["U204", "C203"]),
        ("input-and-gate-pulls", ["R201", "R202", "R203", "R204", "R205", "R206", "R207", "R208",
                                  "R211", "R212", "R213", "R214", "R215", "R216", "R217", "R218"]),
        ("esc-and-front-servo", ["Q201", "D201", "R221", "R231", "R241", "J106", "Q202", "D202", "R222", "R232", "R242", "J102"]),
        ("rear-and-reserve-servos", ["Q203", "D203", "R223", "R233", "R243", "J103", "Q204", "D204", "R224", "R234", "R244",
                                     "J104", "Q205", "D205", "R225", "R235", "R245", "J105"]),
    ],
    "Lighting_IO": [
        ("5v-output-switches", ["U601", "U602", "U603", "R601", "R602", "R603", "C601", "C602", "C603", "C604", "C605", "C606"]),
        ("led-outputs", ["U202", "R604", "R605", "R606", "C607", "C608", "R607", "R608", "R609", "R610",
                         "D601", "D602", "D603", "D604", "J108", "J109", "J110", "J111", "TP602"]),
        ("buzzer", ["BZ101", "D605", "Q601", "R611", "R612"]),
        ("ibus-input", ["J107", "D606", "R613", "R614", "U203", "C610", "TP601"]),
        ("extension-uart", ["J112", "R615", "R616", "R617", "D607", "D608"]),
    ],
}


def positions(sch_text):
    pos = {}
    for m in re.finditer(r'\n\t\(symbol\n\t\t\(lib_id "[^"]+"\)\n\t\t\(at ([-\d.]+) ([-\d.]+) \d+\)(.*?)\n\t\)(?=\n)', sch_text, re.S):
        ref = re.search(r'\(property "Reference" "([^"]+)"', m.group(3))
        if ref and not ref.group(1).startswith("#"):
            pos[ref.group(1)] = (float(m.group(1)), float(m.group(2)))
    for m in re.finditer(r'\n\t\(sheet\n\t\t\(at ([-\d.]+) ([-\d.]+)\)\n\t\t\(size ([-\d.]+) ([-\d.]+)\)', sch_text):
        x, y, w, h = map(float, m.groups())
        pos["sheet@%s,%s" % (x, y)] = (x + w / 2, y + h / 2)
    return pos


def paper_mm(sch_text):
    paper = re.search(r'\(paper "([^"]+)"\)', sch_text).group(1)
    return {"A4": (297.0, 210.0), "A3": (420.0, 297.0)}[paper]


def main(out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as d:
        subprocess.run([str(kicad_env.kicad_cli_path()), "sch", "export", "svg", "-o", d, str(ROOT / "RoverCore.kicad_sch")],
                       check=True, capture_output=True)
        for sheet, groups in GROUPS.items():
            svg = Path(d) / ("RoverCore.svg" if sheet == "RoverCore" else "RoverCore-%s.svg" % sheet)
            text = (ROOT / ("%s.kicad_sch" % sheet)).read_text()
            pw, ph = paper_mm(text)
            subprocess.run(["rsvg-convert", "-b", "white", "-w", str(OVERVIEW_WIDTH), str(svg), "-o",
                            str(out / ("%s_overview.png" % sheet))], check=True)
            big = Path(d) / ("%s_big.png" % sheet)
            px_per_mm = DETAIL_DPI / 25.4
            subprocess.run(["rsvg-convert", "-b", "white", "-w", str(int(pw * px_per_mm)), str(svg), "-o", str(big)], check=True)
            pos = positions(text)
            from PIL import Image
            img = Image.open(big)
            for n, (slug, refs) in enumerate(groups, 1):
                pts = list(pos.items()) if refs == ["*"] else [(r, pos[r]) for r in refs if r in pos]
                missing = [] if refs == ["*"] else [r for r in refs if r not in pos]
                if missing:
                    raise SystemExit("%s: refs not found %s" % (sheet, missing))
                x0 = min(p[0] - MARGIN.get(r[0], DEFAULT_MARGIN) for r, p in pts)
                x1 = max(p[0] + MARGIN.get(r[0], DEFAULT_MARGIN) for r, p in pts)
                y0 = min(p[1] - MARGIN.get(r[0], DEFAULT_MARGIN) for r, p in pts)
                y1 = max(p[1] + MARGIN.get(r[0], DEFAULT_MARGIN) for r, p in pts)
                box = [max(0, x0), max(0, y0), min(pw, x1), min(ph, y1)]
                crop = img.crop(tuple(int(v * px_per_mm) for v in box))
                name = "%s_%02d_%s.png" % (sheet, n, slug)
                crop.save(out / name)
                print(name, "x %.0f-%.0f mm, y %.0f-%.0f mm" % tuple(box[i] for i in (0, 2, 1, 3)))


if __name__ == "__main__":
    main(sys.argv[1])
