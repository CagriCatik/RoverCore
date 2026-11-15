"""Shared helpers for one-time schematic bootstraps (KiCad 10.0.7 file format).

Symbols are copied verbatim from KiCad's official libraries; every pin gets a
short wire stub ending in a net label, hierarchical label or power symbol, so
connectivity can be checked with `kicad-cli sch export netlist`. Bootstraps
write a sheet once; afterwards the KiCad file is the hardware truth.
"""
import math
from pathlib import Path
import re
import sys
import uuid

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.core import kicad_env  # noqa: E402

PROJECT = "RoverCore"
STUB = 5.08
PIN = re.compile(r'\(pin \w+ \w+\s*\(at ([-\d.]+) ([-\d.]+) (\d+)\).*?\(number "([^"]*)"', re.S)
META = ("Manufacturer", "MPN", "LCSC")


def require_closed_kicad():
    if list(ROOT.glob("*.lck")) or list(ROOT.glob("~*.lck")) or kicad_env.running_kicad():
        raise SystemExit("KiCad is running or a lock file exists; close KiCad first.")


class Sheet:
    def __init__(self, namespace, root_uuid, sheet_uuid, title, comment):
        self.ns = uuid.UUID(namespace)
        self.path = "/%s/%s" % (root_uuid, sheet_uuid)
        self.title, self.comment = title, comment
        self.libs, self.items, self.endpoints = set(), [], {}
        self.pwr = 0

    def uid(self, label):
        return str(uuid.uuid5(self.ns, label))

    # ---------- library access ----------
    @staticmethod
    def _block(text, name):
        start = text.index('\n\t(symbol "%s"\n' % name) + 1
        depth, i, in_str = 0, start, False
        while True:
            c = text[i]
            if in_str:
                if c == "\\":
                    i += 1
                elif c == '"':
                    in_str = False
            elif c == '"':
                in_str = True
            elif c == "(":
                depth += 1
            elif c == ")":
                depth -= 1
                if depth == 0:
                    return text[start:i + 1]
            i += 1

    @classmethod
    def lib_symbol(cls, lib_id):
        lib, name = lib_id.split(":")
        block = cls._block((kicad_env.shared_support() / "symbols" / (lib + ".kicad_sym")).read_text(), name)
        if "(extends" in block:
            raise SystemExit("Derived symbol %s is not supported" % lib_id)
        return block.replace('(symbol "%s"' % name, '(symbol "%s"' % lib_id, 1)

    @classmethod
    def pin_points(cls, lib_id):
        return {m.group(4): (float(m.group(1)), float(m.group(2)), int(m.group(3)))
                for m in PIN.finditer(cls.lib_symbol(lib_id))}

    # ---------- geometry ----------
    @staticmethod
    def place(x, y, rot, px, py):
        a = math.radians(rot)
        return (round(x + px * math.cos(a) - py * math.sin(a), 4),
                round(y - (px * math.sin(a) + py * math.cos(a)), 4))

    @staticmethod
    def outward(rot, pin_angle):
        a = math.radians(pin_angle + 180 + rot)
        return round(math.cos(a)), -round(math.sin(a))

    @classmethod
    def vertical(cls, lib_id, rot):
        pts = [cls.place(0, 0, rot, px, py) for px, py, _ in cls.pin_points(lib_id).values()]
        return len(pts) > 1 and len({p[0] for p in pts}) < len({p[1] for p in pts})

    # ---------- s-expression pieces ----------
    @staticmethod
    def prop(name, value, at, hide=False, angle=0, justify=None):
        hidden = "\n\t\t\t\t(hide yes)" if hide else ""
        just = "\n\t\t\t\t(justify %s)" % justify if justify else ""
        return ('\t\t(property "%s" "%s"\n\t\t\t(at %s %s %d)\n\t\t\t(effects\n\t\t\t\t(font\n'
                "\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t)%s%s\n\t\t\t)\n\t\t)\n") % (
                    name, value.replace('"', "'"), at[0], at[1], angle, just, hidden)

    def _symbol(self, lib_id, ref, value, footprint, x, y, rot, pins, fields, in_bom=True):
        self.libs.add(lib_id)
        power = ref.startswith("#")
        body = ("\t(symbol\n\t\t(lib_id \"%s\")\n\t\t(at %s %s %d)\n\t\t(unit 1)\n\t\t(exclude_from_sim no)\n"
                "\t\t(in_bom %s)\n\t\t(on_board %s)\n\t\t(dnp no)\n\t\t(uuid \"%s\")\n"
                % (lib_id, x, y, rot, "yes" if (in_bom and not power) else "no", "no" if power else "yes",
                   self.uid("symbol-" + ref)))
        if power:
            ref_at, val_at, just, angle = (x, y + 3.81), (x, y + 5.08), None, 0
        elif self.vertical(lib_id, rot):
            ref_at, val_at, just = (x + 6.35, y - 1.27), (x + 6.35, y + 1.27), "left"
            angle = rot if rot in (90, 270) else 0
        else:
            ref_at, val_at, just = (x, y - 3.81), (x, y + 3.81), None
            angle = rot if rot in (90, 270) else 0
        body += self.prop("Reference", ref, ref_at, hide=power, angle=angle, justify=just)
        body += self.prop("Value", value, val_at, hide=ref.startswith("#PWR") and value == "GND",
                          angle=angle, justify=just)
        body += self.prop("Footprint", footprint, (x, y), hide=True)
        body += self.prop("Datasheet", fields.get("Datasheet", "~"), (x, y), hide=True)
        body += self.prop("Description", fields.get("Description", ""), (x, y), hide=True)
        for key in META + tuple(k for k in fields if k not in META + ("Datasheet", "Description")):
            if key in fields:
                body += self.prop(key, fields[key], (x, y), hide=True)
        for number in sorted(pins):
            body += '\t\t(pin "%s"\n\t\t\t(uuid "%s")\n\t\t)\n' % (number, self.uid("pin-%s-%s" % (ref, number)))
        body += ("\t\t(instances\n\t\t\t(project \"%s\"\n\t\t\t\t(path \"%s\"\n\t\t\t\t\t(reference \"%s\")\n"
                 "\t\t\t\t\t(unit 1)\n\t\t\t\t)\n\t\t\t)\n\t\t)\n\t)\n") % (PROJECT, self.path, ref)
        self.items.append(body)

    def wire(self, x1, y1, x2, y2, key):
        self.items.append(("\t(wire\n\t\t(pts\n\t\t\t(xy %s %s) (xy %s %s)\n\t\t)\n\t\t(stroke\n\t\t\t(width 0)\n"
                           "\t\t\t(type default)\n\t\t)\n\t\t(uuid \"%s\")\n\t)\n") % (x1, y1, x2, y2, self.uid("wire-" + key)))

    def label(self, net, x, y, direction, key, hierarchical=None):
        angle, justify = {(1, 0): (0, "left"), (-1, 0): (180, "right"), (0, -1): (90, "left"),
                          (0, 1): (270, "right")}[direction]
        if hierarchical:
            self.items.append(("\t(hierarchical_label \"%s\"\n\t\t(shape %s)\n\t\t(at %s %s %d)\n\t\t(effects\n"
                               "\t\t\t(font\n\t\t\t\t(size 1.27 1.27)\n\t\t\t)\n\t\t\t(justify %s)\n\t\t)\n"
                               "\t\t(uuid \"%s\")\n\t)\n") % (net, hierarchical, x, y, angle, justify,
                                                          self.uid("hlabel-" + key)))
        else:
            self.items.append(("\t(label \"%s\"\n\t\t(at %s %s %d)\n\t\t(effects\n\t\t\t(font\n\t\t\t\t(size 1.27 1.27)\n"
                               "\t\t\t)\n\t\t\t(justify %s bottom)\n\t\t)\n\t\t(uuid \"%s\")\n\t)\n")
                              % (net, x, y, angle, justify, self.uid("label-" + key)))

    def note(self, text, x, y, key):
        self.items.append(("\t(text \"%s\"\n\t\t(exclude_from_sim no)\n\t\t(at %s %s 0)\n\t\t(effects\n\t\t\t(font\n"
                           "\t\t\t\t(size 1.27 1.27)\n\t\t\t)\n\t\t\t(justify left bottom)\n\t\t)\n\t\t(uuid \"%s\")\n\t)\n")
                          % (text.replace('"', "'"), x, y, self.uid("text-" + key)))

    # ---------- parts ----------
    def part(self, ref, lib_id, value, footprint, xyr, pins, fields, power_nets, hier=None, in_bom=True):
        """pins: {number: net}; power_nets: {net: lib_id of the power symbol}; hier: {net: shape}."""
        x, y, rot = xyr
        hier = hier or {}
        self._symbol(lib_id, ref, value, footprint, x, y, rot, pins, fields, in_bom)
        pts, done = self.pin_points(lib_id), set()
        for number, net in sorted(pins.items()):
            lx, ly, langle = pts[number]
            px, py = self.place(x, y, rot, lx, ly)
            self.endpoints.setdefault((px, py), set()).add(net)
            if (px, py) in done:
                continue
            done.add((px, py))
            dx, dy = self.outward(rot, langle)
            ex, ey = round(px + dx * STUB, 4), round(py + dy * STUB, 4)
            self.wire(px, py, ex, ey, "%s-%s" % (ref, number))
            if net in power_nets:
                self.pwr += 1
                name = power_nets[net].split(":")[1]
                self._symbol(power_nets[net], "#PWR%s%02d" % (ref, self.pwr), name, "", ex, ey,
                             0 if name == "GND" else 0, {"1": net}, {})
            else:
                self.label(net, ex, ey, (dx, dy), "%s-%s" % (ref, number), hier.get(net))

    def check(self):
        clash = {k: v for k, v in self.endpoints.items() if len(v) > 1}
        if clash:
            raise SystemExit("Different nets share a pin endpoint: %s" % clash)

    def render(self):
        self.check()
        libs = "\n".join("\n".join("\t" + l for l in self.lib_symbol(lib).splitlines()) for lib in sorted(self.libs))
        return ("(kicad_sch\n\t(version 20260306)\n\t(generator \"eeschema\")\n\t(generator_version \"10.0\")\n"
                "\t(uuid \"%s\")\n\t(paper \"A4\")\n\t(title_block\n\t\t(title \"%s\")\n\t\t(rev \"A\")\n"
                "\t\t(comment 1 \"%s\")\n\t)\n\t(lib_symbols\n%s\n\t)\n%s\t(embedded_fonts no)\n)\n"
                % (self.uid("sheet-file"), self.title, self.comment, libs, "".join(self.items)))


def sheet_block(project_root_uuid, sheet_uuid, name, filename, x, y, w, h, page, pins):
    """pins: list of (name, shape, side 'left'|'right', y_offset)."""
    out = ("\t(sheet\n\t\t(at %s %s)\n\t\t(size %s %s)\n\t\t(exclude_from_sim no)\n\t\t(in_bom yes)\n"
           "\t\t(on_board yes)\n\t\t(dnp no)\n\t\t(fields_autoplaced yes)\n\t\t(stroke\n\t\t\t(width 0.1524)\n"
           "\t\t\t(type solid)\n\t\t)\n\t\t(fill\n\t\t\t(color 0 0 0 0.0000)\n\t\t)\n\t\t(uuid \"%s\")\n"
           % (x, y, w, h, sheet_uuid))
    out += Sheet.prop("Sheetname", name, (x, round(y - 0.7116, 4)), justify="left bottom")
    out += Sheet.prop("Sheetfile", filename, (x, round(y + h + 0.5846, 4)), hide=True, justify="left top")
    for pname, shape, side, dy in pins:
        px = x if side == "left" else round(x + w, 4)
        angle, just = (180, "left") if side == "left" else (0, "right")
        out += ("\t\t(pin \"%s\" %s\n\t\t\t(at %s %s %d)\n\t\t\t(uuid \"%s\")\n\t\t\t(effects\n\t\t\t\t(font\n"
                "\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t)\n\t\t\t\t(justify %s)\n\t\t\t)\n\t\t)\n"
                % (pname, shape, px, round(y + dy, 4), angle,
                   uuid.uuid5(uuid.UUID(sheet_uuid), "pin-" + pname), just))
    out += ("\t\t(instances\n\t\t\t(project \"%s\"\n\t\t\t\t(path \"/%s\"\n\t\t\t\t\t(page \"%s\")\n\t\t\t\t)\n"
            "\t\t\t)\n\t\t)\n\t)\n" % (PROJECT, project_root_uuid, page))
    return out
