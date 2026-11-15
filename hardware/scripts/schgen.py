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
        self.paper = "A4"
        self.file_uuid = None      # keep the sheet file uuid when re-laying out an existing sheet
        self.wired = []            # nets drawn as direct wires instead of labels (route())
        self.anchor = {}           # net -> (ref, pin) that keeps the label of a wired net
        self.pins = {}             # (ref, pin) -> dict(p, e, net, dir)
        self.segs = []             # (net, (x1, y1), (x2, y2)) of every wire
        self.points = []           # (net, (x, y)) of pin points, stub ends, label and power anchors
        self.fallbacks = []
        self.power_nets = {}
        self.label_only = set()    # (ref, pin) of wired nets that keep a plain label (e.g. dense connector rows)

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
        path = (ROOT / "hardware/libraries/symbols" / (lib + ".kicad_sym") if lib == "ProjectSymbols"
                else kicad_env.shared_support() / "symbols" / (lib + ".kicad_sym"))
        block = cls._block(path.read_text(), name)
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
                   fields.get("_uuid") or self.uid("symbol-" + ref)))
        if "_ref_at" in fields:  # explicit field offsets for large symbols
            (rdx, rdy), (vdx, vdy) = fields["_ref_at"], fields["_val_at"]
            ref_at, val_at, just = (x + rdx, y + rdy), (x + vdx, y + vdy), "left"
            angle = rot if rot in (90, 270) else 0   # KiCad draws field text relative to the symbol rotation
        elif ref.startswith("#FLG"):  # keep the flag text clear of the net symbol at the same point
            ref_at, val_at, just, angle = (x, y + 3.81), (round(x - 1.27, 4), round(y - 2.54, 4)), "right", 0
        elif power:
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
        for key in META + tuple(k for k in fields if k not in META + ("Datasheet", "Description")
                                and not k.startswith("_")):
            if key in fields:
                body += self.prop(key, fields[key], (x, y), hide=True)
        for number in sorted(pins):
            body += '\t\t(pin "%s"\n\t\t\t(uuid "%s")\n\t\t)\n' % (
                number, fields.get("_pin_uuids", {}).get(number) or self.uid("pin-%s-%s" % (ref, number)))
        body += ("\t\t(instances\n\t\t\t(project \"%s\"\n\t\t\t\t(path \"%s\"\n\t\t\t\t\t(reference \"%s\")\n"
                 "\t\t\t\t\t(unit 1)\n\t\t\t\t)\n\t\t\t)\n\t\t)\n\t)\n") % (PROJECT, self.path, ref)
        self.items.append(body)

    def wire(self, x1, y1, x2, y2, key, net=None):
        if net is not None:
            self.segs.append((net, (x1, y1), (x2, y2)))
        self.items.append(("\t(wire\n\t\t(pts\n\t\t\t(xy %s %s) (xy %s %s)\n\t\t)\n\t\t(stroke\n\t\t\t(width 0)\n"
                           "\t\t\t(type default)\n\t\t)\n\t\t(uuid \"%s\")\n\t)\n") % (x1, y1, x2, y2, self.uid("wire-" + key)))

    def label(self, net, x, y, direction, key, hierarchical=None):
        angle, justify = {(1, 0): (0, "left"), (-1, 0): (180, "right"), (0, -1): (90, "left"),
                          (0, 1): (270, "right")}[direction]
        if hierarchical and hierarchical.startswith("global:"):
            self.items.append(("\t(global_label \"%s\"\n\t\t(shape %s)\n\t\t(at %s %s %d)\n\t\t(fields_autoplaced yes)\n"
                               "\t\t(effects\n\t\t\t(font\n\t\t\t\t(size 1.27 1.27)\n\t\t\t)\n\t\t\t(justify %s)\n\t\t)\n"
                               "\t\t(uuid \"%s\")\n\t\t(property \"Intersheetrefs\" \"${INTERSHEET_REFS}\"\n\t\t\t(at %s %s 0)\n"
                               "\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t)\n\t\t\t\t(hide yes)\n\t\t\t)\n\t\t)\n\t)\n")
                              % (net, hierarchical.split(":", 1)[1], x, y, angle, justify, self.uid("glabel-" + key), x, y))
        elif hierarchical:
            self.items.append(("\t(hierarchical_label \"%s\"\n\t\t(shape %s)\n\t\t(at %s %s %d)\n\t\t(effects\n"
                               "\t\t\t(font\n\t\t\t\t(size 1.27 1.27)\n\t\t\t)\n\t\t\t(justify %s)\n\t\t)\n"
                               "\t\t(uuid \"%s\")\n\t)\n") % (net, hierarchical, x, y, angle, justify,
                                                          self.uid("hlabel-" + key)))
        else:
            self.items.append(("\t(label \"%s\"\n\t\t(at %s %s %d)\n\t\t(effects\n\t\t\t(font\n\t\t\t\t(size 1.27 1.27)\n"
                               "\t\t\t)\n\t\t\t(justify %s bottom)\n\t\t)\n\t\t(uuid \"%s\")\n\t)\n")
                              % (net, x, y, angle, justify, self.uid("label-" + key)))

    # ---------- direct wiring ----------
    @staticmethod
    def _on(q, a, b):
        """q on segment a-b (inclusive), axis-parallel segments only."""
        (x1, y1), (x2, y2) = a, b
        eps = 1e-6
        if abs(x1 - x2) < eps:
            return abs(q[0] - x1) < eps and min(y1, y2) - eps <= q[1] <= max(y1, y2) + eps
        if abs(y1 - y2) < eps:
            return abs(q[1] - y1) < eps and min(x1, x2) - eps <= q[0] <= max(x1, x2) + eps
        return False

    def _ok(self, net, seg):
        a, b = seg
        for n, q in self.points:
            if n != net and self._on(q, a, b):
                return False
        for n, c, d in self.segs:
            if n == net:
                continue
            if self._on(a, c, d) or self._on(b, c, d) or self._on(c, a, b) or self._on(d, a, b):
                return False
            # collinear overlap without shared endpoints
            if (abs(a[0] - b[0]) < 1e-6 and abs(c[0] - d[0]) < 1e-6 and abs(a[0] - c[0]) < 1e-6) or \
               (abs(a[1] - b[1]) < 1e-6 and abs(c[1] - d[1]) < 1e-6 and abs(a[1] - c[1]) < 1e-6):
                lo1, hi1 = sorted((a[1], b[1]) if abs(a[0] - b[0]) < 1e-6 else (a[0], b[0]))
                lo2, hi2 = sorted((c[1], d[1]) if abs(c[0] - d[0]) < 1e-6 else (c[0], d[0]))
                if lo1 < hi2 - 1e-6 and lo2 < hi1 - 1e-6:
                    return False
        return True

    def route(self):
        """Connect the stub ends of every net in self.wired with orthogonal wires (L shapes) where this cannot touch
        another net; members that cannot be routed keep a net label (recorded in self.fallbacks)."""
        for net in self.wired:
            members = sorted([k for k, v in self.pins.items() if v["net"] == net and k not in self.label_only],
                             key=lambda k: (k != self.anchor.get(net), k))
            for k in sorted(k for k, v in self.pins.items() if v["net"] == net and k in self.label_only):
                pin = self.pins[k]
                self.label(net, pin["e"][0], pin["e"][1], pin["dir"], "%s-%s" % k, pin["hier"])
            if not members:
                continue
            done, nodes = [members[0]], [self.pins[members[0]]["e"]]
            pending = members[1:]
            while pending:
                best = None
                for m in pending:
                    e = self.pins[m]["e"]
                    for t in sorted(nodes, key=lambda q: abs(q[0] - e[0]) + abs(q[1] - e[1])):
                        for corner in ((t[0], e[1]), (e[0], t[1])):
                            path = [s for s in ((e, corner), (corner, t)) if s[0] != s[1]]
                            if all(self._ok(net, s) for s in path):
                                cost = abs(t[0] - e[0]) + abs(t[1] - e[1])
                                if best is None or cost < best[0]:
                                    best = (cost, m, path)
                                break
                        else:
                            continue
                        break
                if best is None:
                    break
                _, m, path = best
                for i, (a, b) in enumerate(path):
                    self.wire(a[0], a[1], b[0], b[1], "route-%s-%s-%s-%d" % (net, m[0], m[1], i), net)
                    nodes += [a, b]
                    self.points += [(net, a), (net, b)]
                done.append(m)
                pending.remove(m)
            for m in [members[0]] + pending:
                pin = self.pins[m]
                if m != members[0]:
                    self.fallbacks.append((net, m))
                ex, ey = pin["e"]
                if net in self.power_nets:
                    self.pwr += 1
                    name = self.power_nets[net].split(":")[1]
                    self._symbol(self.power_nets[net], "#PWR%s%02d" % (m[0], self.pwr), name, "", ex, ey, 0, {"1": net}, {})
                else:
                    self.label(net, ex, ey, pin["dir"], "%s-%s" % m, pin["hier"])
            # junctions: points with three or more wire ends, or a wire end inside another wire of the net
            ends = {}
            for n, a, b in self.segs:
                if n == net:
                    for q in (a, b):
                        ends[q] = ends.get(q, 0) + 1
            for q, cnt in ends.items():
                inner = any(self._on(q, a, b) and q not in (a, b) for n, a, b in self.segs if n == net)
                if cnt >= 3 or inner:
                    self.items.append("\t(junction\n\t\t(at %s %s)\n\t\t(diameter 0)\n\t\t(color 0 0 0 0)\n"
                                      "\t\t(uuid \"%s\")\n\t)\n" % (q[0], q[1], self.uid("junction-%s-%s-%s" % (net, q[0], q[1]))))

    def group(self, title, x1, y1, x2, y2, key, comment=None):
        """Dashed frame with a bold heading (and optional one-line comment) for a functional group."""
        self.items.append(("\t(rectangle\n\t\t(start %s %s)\n\t\t(end %s %s)\n\t\t(stroke\n\t\t\t(width 0)\n"
                           "\t\t\t(type dash)\n\t\t)\n\t\t(fill\n\t\t\t(type none)\n\t\t)\n\t\t(uuid \"%s\")\n\t)\n")
                          % (x1, y1, x2, y2, self.uid("group-" + key)))
        self.items.append(("\t(text \"%s\"\n\t\t(exclude_from_sim no)\n\t\t(at %s %s 0)\n\t\t(effects\n\t\t\t(font\n"
                           "\t\t\t\t(size 2 2)\n\t\t\t\t(thickness 0.4)\n\t\t\t\t(bold yes)\n\t\t\t)\n"
                           "\t\t\t(justify left bottom)\n\t\t)\n\t\t(uuid \"%s\")\n\t)\n")
                          % (title.replace('"', "'"), round(x1 + 1.27, 2), round(y1 + 3.81, 2), self.uid("group-title-" + key)))
        if comment:
            self.note(comment, round(x1 + 1.27, 2), round(y1 + 5.08, 2), "group-comment-" + key, "left top")

    def note(self, text, x, y, key, justify="left bottom"):
        self.items.append(("\t(text \"%s\"\n\t\t(exclude_from_sim no)\n\t\t(at %s %s 0)\n\t\t(effects\n\t\t\t(font\n"
                           "\t\t\t\t(size 1.27 1.27)\n\t\t\t)\n\t\t\t(justify %s)\n\t\t)\n\t\t(uuid \"%s\")\n\t)\n")
                          % (text.replace('"', "'"), x, y, justify, self.uid("text-" + key)))

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
            if net.startswith("="):  # "=<pin>": tie directly to another pin of the same symbol with a wire
                ox, oy, _ = pts[net[1:]]
                qx, qy = self.place(x, y, rot, ox, oy)
                self.wire(px, py, qx, qy, "%s-%s-tie" % (ref, number))
                continue
            if net == "NC":  # deliberately unconnected pin: no-connect flag directly on the pin
                self.items.append("\t(no_connect\n\t\t(at %s %s)\n\t\t(uuid \"%s\")\n\t)\n"
                                  % (px, py, self.uid("nc-%s-%s" % (ref, number))))
                continue
            self.endpoints.setdefault((px, py), set()).add(net)
            if (px, py) in done:
                continue
            done.add((px, py))
            dx, dy = self.outward(rot, langle)
            stub = fields.get("_stub", {}).get(number, STUB)  # optional longer stub to stagger crowded labels
            ex, ey = round(px + dx * stub, 4), round(py + dy * stub, 4)
            self.wire(px, py, ex, ey, "%s-%s" % (ref, number), net)
            self.pins[(ref, number)] = dict(p=(px, py), e=(ex, ey), net=net, dir=(dx, dy), hier=hier.get(net))
            self.points += [(net, (px, py)), (net, (ex, ey))]
            self.power_nets.update(power_nets)
            if net in self.wired:
                continue
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
                "\t(uuid \"%s\")\n\t(paper \"%s\")\n\t(title_block\n\t\t(title \"%s\")\n\t\t(rev \"A\")\n"
                "\t\t(comment 1 \"%s\")\n\t)\n\t(lib_symbols\n%s\n\t)\n%s\t(embedded_fonts no)\n)\n"
                % (self.file_uuid or self.uid("sheet-file"), self.paper, self.title, self.comment, libs, "".join(self.items)))


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
