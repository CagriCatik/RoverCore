#!/usr/bin/env python3
"""Re-draw an existing sheet with a new layout WITHOUT electrical changes.

Inputs: the current sheet file (symbols: lib_id, fields, UUIDs, pin UUIDs, BOM flag, label kinds) and the
project netlist exported by kicad-cli (pin -> net). The layout spec (sheet_layouts.py) only gives positions,
rotations, field offsets, group frames, comments, PWR_FLAG nets and the local nets to be drawn as wires.
References, values, footprints and all other fields are copied; connectivity comes from the netlist.

Usage:
  python3 hardware/scripts/relayout_sheet.py SHEET [SHEET ...]     (writes the sheet files in place)
  python3 hardware/scripts/relayout_sheet.py --check BASELINE.xml   (compares the current netlist with a baseline)
Refuses to run while KiCad is open or lock files exist.
"""
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parent))
import schgen  # noqa: E402
from schgen import Sheet, require_closed_kicad  # noqa: E402

ROOT = schgen.ROOT
NS = "4c2a9e10-6b7d-4f1e-8a35-2d9c0e7b1a00"


def netlist():
    with tempfile.TemporaryDirectory() as d:
        out = Path(d) / "net.xml"
        subprocess.run([str(schgen.kicad_env.kicad_cli_path()), "sch", "export", "netlist", "--format", "kicadxml",
                        "-o", str(out), str(ROOT / "RoverCore.kicad_sch")], check=True, capture_output=True)
        return ET.parse(out).getroot()


def pin_nets(root):
    nets = {}
    for n in root.find("nets"):
        for node in n.findall("node"):
            nets[(node.get("ref"), node.get("pin"))] = n.get("name")
    return nets


def connectivity(root):
    """{net name: sorted members} plus {ref: (value, footprint)} - the comparison basis."""
    nets = {}
    for n in root.find("nets"):
        name = n.get("name")
        members = tuple(sorted(x.get("ref") + "." + x.get("pin") for x in n.findall("node")))
        if name.startswith("unconnected-"):
            name = "unconnected:" + ",".join(members)
        nets[name] = members
    parts = {c.get("ref"): (c.findtext("value"), c.findtext("footprint")) for c in root.find("components")}
    return nets, parts


def blocks(text, head):
    """Top-level s-expression blocks of the sheet file that start with '\\t(head'."""
    out, i = [], 0
    key = "\n\t(" + head
    while True:
        i = text.find(key, i)
        if i < 0:
            return out
        j, depth, k, s = i + 1, 0, i + 1, False
        while True:
            c = text[k]
            if s:
                if c == "\\":
                    k += 1
                elif c == '"':
                    s = False
            elif c == '"':
                s = True
            elif c == "(":
                depth += 1
            elif c == ")":
                depth -= 1
                if depth == 0:
                    break
            k += 1
        blk = text[j:k + 1]
        if re.match(r"\t\(%s[\s\n]" % re.escape(head), blk):
            out.append(blk)
        i = k


def extract(sheet):
    text = (ROOT / ("%s.kicad_sch" % sheet)).read_text()
    info = {"file_uuid": re.search(r'\n\t\(uuid "([^"]+)"\)', text).group(1),
            "paper": re.search(r'\(paper "([^"]+)"\)', text).group(1),
            "title": re.search(r'\(title "([^"]*)"\)', text).group(1),
            "comment": (re.search(r'\(comment 1 "([^"]*)"\)', text) or [None, ""])[1],
            "symbols": {}, "global": {}, "hier": {}, "power": set()}
    for blk in blocks(text, "symbol"):
        lib = re.search(r'\(lib_id "([^"]+)"\)', blk).group(1)
        props = re.findall(r'\(property "([^"]+)" "((?:[^"\\]|\\.)*)"', blk)
        ref = dict(props)["Reference"]
        if ref.startswith("#"):
            if lib.startswith("power:") and lib != "power:PWR_FLAG":
                info["power"].add(lib.split(":")[1])
            continue
        path = re.search(r'\(path "/([0-9a-f-]+)/([0-9a-f-]+)"', blk)
        info["root_uuid"], info["sheet_uuid"] = path.group(1), path.group(2)
        fields = {k: v for k, v in props if k not in ("Reference", "Value", "Footprint")}
        fields["_uuid"] = re.search(r'\n\t\t\(uuid "([^"]+)"\)', blk).group(1)
        if "\n\t\t(dnp yes)" in blk:
            fields["_dnp"] = True
        fields["_pin_uuids"] = dict(re.findall(r'\(pin "([^"]+)"\n\t\t\t\(uuid "([^"]+)"\)', blk))
        at = re.search(r'\n\t\t\(at ([-\d.]+) ([-\d.]+) (\d+)\)', blk)
        info["symbols"][ref] = dict(lib=lib, value=dict(props)["Value"], footprint=dict(props)["Footprint"],
                                    fields=fields, in_bom="(in_bom yes)" in blk,
                                    at=(float(at.group(1)), float(at.group(2)), int(at.group(3))))
    for blk in blocks(text, "global_label"):
        info["global"][re.search(r'global_label "([^"]+)"', blk).group(1)] = re.search(r'\(shape (\w+)\)', blk).group(1)
    for blk in blocks(text, "hierarchical_label"):
        info["hier"][re.search(r'hierarchical_label "([^"]+)"', blk).group(1)] = re.search(r'\(shape (\w+)\)', blk).group(1)
    return info


def local_name(sheet, info, net):
    if net.startswith("unconnected-"):
        return "NC"
    if net.startswith("/"):
        name = net.rsplit("/", 1)[1]
        return name
    return net


def build(sheet, spec, nets):
    info = extract(sheet)
    syms = dict(info["symbols"])
    # parts added by this layout step (electrical change, listed in the spec): lib, value, footprint, pins, fields
    for ref, (lib, value, footprint, pins, fields) in spec.get("new", {}).items():
        if ref in syms:
            continue  # already in the sheet: from now on taken from the sheet like every other part
        uuids = {num: None for num in pins}
        syms[ref] = dict(lib=lib, value=value, footprint=footprint, fields=dict(fields, _pin_uuids=uuids),
                         in_bom=not ref.startswith("TP"), at=None, new_pins=pins)
    missing, extra = set(syms) - set(spec["parts"]), set(spec["parts"]) - set(syms)
    if missing or extra:
        raise SystemExit("%s: layout spec mismatch, missing %s, unknown %s" % (sheet, sorted(missing), sorted(extra)))
    s = Sheet(NS, info["root_uuid"], info["sheet_uuid"], info["title"], info["comment"])
    s.paper, s.file_uuid = info["paper"], info["file_uuid"]
    s.wired = list(spec.get("wire", []))
    s.anchor = {k: tuple(v) for k, v in spec.get("anchor", {}).items()}
    s.label_only = {tuple(v) for v in spec.get("label_only", [])}
    s.label_at = dict(spec.get("label_at", {}))
    power_nets = {p: "power:" + p for p in info["power"]}
    hier = dict({k: v for k, v in info["hier"].items()}, **{k: "global:" + v for k, v in info["global"].items()})
    # global labels introduced by this layout step (new inter-sheet nets), net -> shape
    hier.update({k: "global:" + v for k, v in spec.get("globals", {}).items()})
    # nets that carry a local label as well as the hierarchical label (keeps the net name chosen by KiCad):
    # pins get local labels / wires, the hierarchical label sits at the stub end of the given pin
    hier_local = spec.get("hier_local", {})
    for net in hier_local:
        hier.pop(net)
    for ref, place in spec["parts"].items():
        sym = syms[ref]
        x, y, rot = place[:3]
        extra_fields = place[3] if len(place) > 3 else {}
        pins = dict(sym.get("new_pins", {}))
        for num in sym["fields"]["_pin_uuids"]:
            if num in pins:
                continue
            net = nets.get((ref, num))
            if net is None:
                raise SystemExit("%s: pin %s.%s not in netlist" % (sheet, ref, num))
            pins[num] = local_name(sheet, info, net)
        pins.update(spec.get("pins", {}).get(ref, {}))
        fields = dict(sym["fields"], **extra_fields)
        value = fields.pop("_value", sym["value"])   # value change of an existing part (listed electrical change)
        fields = {k: v for k, v in fields.items() if v is not None}  # None removes a field (e.g. stale LCSC)
        if all(v is None for v in fields["_pin_uuids"].values()):
            fields.pop("_pin_uuids")
            fields.pop("_uuid", None)
        s.part(ref, sym["lib"], value, sym["footprint"], (x, y, rot), pins, fields, power_nets, hier,
               in_bom=sym["in_bom"])
    s.route()
    for net, (ref, num) in hier_local.items():
        pin = s.pins[(ref, num)]
        s.label(net, pin["e"][0], pin["e"][1], pin["dir"], "hier-%s" % net, info["hier"][net])
    for n, net in enumerate(spec.get("flags", []), 1):
        ref, num = spec["flag_at"][net] if net in spec.get("flag_at", {}) else \
            next(k for k, v in sorted(s.pins.items()) if v["net"] == net)
        pin = s.pins[(ref, num)]
        ex, ey = pin["e"]
        s._symbol("power:PWR_FLAG", "#FLG%s%02d" % (spec["flag_prefix"], n), "PWR_FLAG", "", ex, ey, 0, {"1": net}, {})
    for key, (title, box, comment) in spec.get("groups", {}).items():
        s.group(title, *box, key, comment)
    for key, (text, x, y) in spec.get("notes", {}).items():
        s.note(text, x, y, key)
    (ROOT / ("%s.kicad_sch" % sheet)).write_text(s.render())
    return s.fallbacks


def check(baseline):
    base_nets, base_parts = connectivity(ET.parse(baseline).getroot())
    nets, parts = connectivity(netlist())
    ok = True
    for k in sorted(set(base_nets) | set(nets)):
        if base_nets.get(k) != nets.get(k):
            ok = False
            print("NET DIFF", k, base_nets.get(k), "->", nets.get(k))
    for k in sorted(set(base_parts) | set(parts)):
        if base_parts.get(k) != parts.get(k):
            ok = False
            print("PART DIFF", k, base_parts.get(k), "->", parts.get(k))
    print("connectivity identical: %s (%d nets, %d parts)" % (ok, len(nets), len(parts)))
    return 0 if ok else 1


if __name__ == "__main__":
    if sys.argv[1] == "--check":
        sys.exit(check(sys.argv[2]))
    require_closed_kicad()
    from sheet_layouts import LAYOUTS  # noqa: E402
    nets = pin_nets(netlist())
    for sheet in sys.argv[1:]:
        fb = build(sheet, LAYOUTS[sheet], nets)
        print(sheet, "written; label fallbacks:", fb or "none")
