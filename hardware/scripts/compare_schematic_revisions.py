#!/usr/bin/env python3
"""Compare the electrical content of the schematic between a Git revision and the working tree.

Checks: nets (name and pin members, from kicad-cli netlists), components (value, footprint, every field, sheet
path), per sheet the hierarchical labels, global labels and sheet pins, the symbol flags in_bom / on_board / dnp /
exclude_from_sim, and symbol and pin UUIDs. Layout (positions, wires, texts) is deliberately not compared.
The old revision is extracted with `git archive` into a temporary directory; the working tree is not touched.

Usage: python3 hardware/scripts/compare_schematic_revisions.py REV   (exit status 1 on any difference)
"""
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.core import kicad_env  # noqa: E402

sys.path.insert(0, str(ROOT / "hardware/scripts"))
from relayout_sheet import blocks  # noqa: E402


def netlist(project_dir):
    with tempfile.TemporaryDirectory() as d:
        out = Path(d) / "net.xml"
        subprocess.run([str(kicad_env.kicad_cli_path()), "sch", "export", "netlist", "--format", "kicadxml", "-o", str(out),
                        str(Path(project_dir) / "RoverCore.kicad_sch")], check=True, capture_output=True)
        root = ET.parse(out).getroot()
    nets = {}
    for n in root.find("nets"):
        members = tuple(sorted(x.get("ref") + "." + x.get("pin") for x in n.findall("node")))
        name = n.get("name")
        nets["unconnected:" + ",".join(members) if name.startswith("unconnected-") else name] = members
    comps = {}
    for c in root.find("components"):
        fields = tuple(sorted((f.get("name"), f.text or "") for f in (c.find("fields") if c.find("fields") is not None else [])))
        props = tuple(sorted((p.get("name"), p.get("value") or "") for p in c.findall("property")))
        comps[c.get("ref")] = dict(value=c.findtext("value"), footprint=c.findtext("footprint"),
                                   sheet=c.find("sheetpath").get("names"), fields=fields, props=props,
                                   libsource=(c.find("libsource").get("lib"), c.find("libsource").get("part")))
    return nets, comps


def sheet_items(project_dir):
    out = {}
    for f in sorted(Path(project_dir).glob("*.kicad_sch")):
        t = f.read_text()
        syms = {}
        for blk in blocks(t, "symbol"):
            ref = re.search(r'\(property "Reference" "([^"]+)"', blk).group(1)
            if ref.startswith("#"):
                continue
            flags = tuple(re.search(r'\(%s (\w+)\)' % k, blk).group(1) for k in ("in_bom", "on_board", "dnp", "exclude_from_sim"))
            uid = re.search(r'\n\t\t\(uuid "([^"]+)"\)', blk).group(1)
            pins = tuple(sorted(re.findall(r'\(pin "([^"]+)"\n\t\t\t\(uuid "([^"]+)"\)', blk)))
            syms[ref] = dict(flags=flags, uuid=uid, pins=pins, lib=re.search(r'\(lib_id "([^"]+)"\)', blk).group(1))
        hier = sorted(set(re.findall(r'\(hierarchical_label "([^"]+)"\n\t\t\(shape (\w+)\)', t)))
        glob = sorted(set(re.findall(r'\(global_label "([^"]+)"\n\t\t\(shape (\w+)\)', t)))
        sheet_pins = sorted(re.findall(r'\(pin "([^"]+)" (\w+)\n', t)) if f.name == "RoverCore.kicad_sch" else []
        sheets = sorted(re.findall(r'\(property "Sheetfile" "([^"]+)"', t))
        out[f.name] = dict(symbols=syms, hier=hier, glob=glob, sheet_pins=sheet_pins, sheets=sheets)
    return out


def main(rev):
    with tempfile.TemporaryDirectory() as d:
        archive = subprocess.run(["git", "-C", str(ROOT), "archive", rev], check=True, capture_output=True).stdout
        subprocess.run(["tar", "-x", "-C", d], input=archive, check=True)
        old_nets, old_comps = netlist(d)
        old_items = sheet_items(d)
    new_nets, new_comps = netlist(ROOT)
    new_items = sheet_items(ROOT)
    diffs = []
    for k in sorted(set(old_nets) | set(new_nets)):
        if old_nets.get(k) != new_nets.get(k):
            diffs.append("net %s: %s -> %s" % (k, old_nets.get(k), new_nets.get(k)))
    for k in sorted(set(old_comps) | set(new_comps)):
        if old_comps.get(k) != new_comps.get(k):
            diffs.append("component %s: %s -> %s" % (k, old_comps.get(k), new_comps.get(k)))
    for f in sorted(set(old_items) | set(new_items)):
        o, n = old_items.get(f), new_items.get(f)
        if o is None or n is None:
            diffs.append("sheet file %s only in %s" % (f, "new" if o is None else "old"))
            continue
        for key in ("hier", "glob", "sheet_pins", "sheets"):
            if o[key] != n[key]:
                diffs.append("%s %s: %s -> %s" % (f, key, o[key], n[key]))
        for ref in sorted(set(o["symbols"]) | set(n["symbols"])):
            if o["symbols"].get(ref) != n["symbols"].get(ref):
                diffs.append("%s symbol %s: %s -> %s" % (f, ref, o["symbols"].get(ref), n["symbols"].get(ref)))
    n_sym = sum(len(v["symbols"]) for v in new_items.values())
    print("compared against %s: %d nets, %d components, %d symbols in %d sheet files" % (rev, len(new_nets), len(new_comps), n_sym, len(new_items)))
    for line in diffs:
        print("DIFF", line)
    print("result: %s" % ("IDENTICAL" if not diffs else "%d differences" % len(diffs)))
    return 1 if diffs else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
