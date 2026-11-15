#!/usr/bin/env python3
"""Compare the DevKit socket U501 in the exported netlist with hardware/interfaces/pinmap.csv.

Every one of the 44 pads is classified:
  signal        - pinmap net and schematic net agree
  power         - +3V3 / +5V_DEVKIT / GND pins
  expected NC   - pinmap direction 'reserved' (strapping GPIO3/45/46, USB, UART0, PSRAM, RGB LED) and the pad
                  carries a no-connect (KiCad names the net 'unconnected-(U501-<pin name>-Pad<n>)')
  DEVIATION     - anything else (the script exits with status 1)
Since 2026-11-15 EN (J1-3, RESET SW502) and GPIO0 (J3-14, BOOT SW503) are connected and checked as signals.
The pin name embedded in the unconnected net is also checked against the pinmap GPIO, so a no-connect
on the wrong pad is caught. Prints a Markdown table for docs/vcu/rev1-pin-und-anschlussplan.md.

Usage: python3 hardware/scripts/check_socket_pinmap.py   (needs KiCad 10 kicad-cli; writes only to a temp dir)
"""
from pathlib import Path
import csv
import re
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.core import kicad_env  # noqa: E402

ALIASES = {"+3V3_DEVKIT": "+3V3"}  # pinmap uses the DevKit name, the schematic the power-net name


def netlist():
    with tempfile.TemporaryDirectory() as d:
        out = Path(d) / "net.xml"
        subprocess.run([str(kicad_env.kicad_cli_path()), "sch", "export", "netlist", "--format", "kicadxml", "-o", str(out),
                        str(ROOT / "RoverCore.kicad_sch")], check=True, capture_output=True)
        root = ET.parse(out).getroot()
    pads = {}
    for net in root.find("nets"):
        for node in net.findall("node"):
            if node.get("ref") == "U501":
                pads[int(node.get("pin"))] = (net.get("name"), node.get("pinfunction") or "")
    return pads


def main():
    pads = netlist()
    rows, bad = [], 0
    for r in csv.DictReader(open(ROOT / "hardware/interfaces/pinmap.csv")):
        if r["reference"] != "U501":
            continue
        m = re.match(r"J([13])-(\d+)$", r["pin_number"])
        pad = int(m.group(2)) + (0 if m.group(1) == "1" else 22)
        net, func = pads.pop(pad, ("<missing>", ""))
        want = ALIASES.get(r["schematic_net"], r["schematic_net"])
        name = net if net.startswith("unconnected-") else net.rsplit("/", 1)[-1]
        if r["direction"] == "reserved":
            nc = re.match(r"unconnected-\(U501-(.+)-Pad(\d+)\)$", name)
            gpio = r["mcu_port"]
            label = {"GPIO43": "TX", "GPIO44": "RX", "CHIP_PU": "RST"}.get(gpio, gpio)
            pin_ok = bool(nc) and int(nc.group(2)) == pad and nc.group(1).split("/")[-1] == label
            cls = "expected NC" if pin_ok else "DEVIATION"
        elif r["direction"].startswith("power"):
            cls = "power" if name == want else "DEVIATION"
        else:
            cls = "signal" if name == want else "DEVIATION"
        bad += cls == "DEVIATION"
        rows.append((pad, r["pin_number"], r["mcu_port"], want, name, cls))
    for pad, (net, _) in sorted(pads.items()):
        bad += 1
        rows.append((pad, "?", "?", "<not in pinmap>", net, "DEVIATION"))
    print("| Pad | DevKit-Pin | Port | pinmap.csv | Netz im Schaltplan | Einstufung |")
    print("|---:|---|---|---|---|---|")
    for row in sorted(rows):
        print("| %d | %s | %s | %s | %s | %s |" % row)
    counts = {}
    for row in rows:
        counts[row[5]] = counts.get(row[5], 0) + 1
    print("\nSummary: %s" % ", ".join("%s %d" % kv for kv in sorted(counts.items())))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
