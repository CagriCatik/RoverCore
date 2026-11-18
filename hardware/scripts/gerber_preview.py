#!/usr/bin/env python3
"""Preview images rendered from the exported Gerber and Excellon files (fabrication review, 2026-11-18).

Usage: python3 gerber_preview.py PACKAGE_DIR OUTDIR [--scale PX_PER_MM]
PACKAGE_DIR is an export of `scripts/kit export` (fabrication/gerbers, fabrication/drill: all *.drl, merged or
separate PTH/NPTH). The images are drawn from
the exported files, not from the board, so they show what a fabricator receives. Review images, not source.
Supported subset (what KiCad 10.0.7 writes): FS/MO, apertures C/R/O and macros with primitives 1/4/20/21, D01/D02/D03,
G01/G02/G03 with G75, regions G36/G37, LPD/LPC; Excellon tools with X/Y hits (no routed slots). Anything else stops
the script with an error instead of being skipped.
Writes one PNG per copper, mask, silkscreen and paste layer, a drill map, and realistic top/bottom composites.
Needs rsvg-convert.
"""
import math
from pathlib import Path
import re
import subprocess
import sys


def num(s, fmt):
    neg = s.startswith("-")
    s = s.lstrip("+-")
    v = int(s) / 10 ** fmt
    return -v if neg else v


def evalm(expr, args):
    e = re.sub(r"\$(\d+)", lambda m: repr(args[int(m.group(1)) - 1]), expr).replace("x", "*").replace("X", "*")
    return float(eval(e, {"__builtins__": {}}))


class Gerber:
    def __init__(self, path):
        self.fmt, self.ap, self.macros, self.items = 6, {}, {}, []
        self.parse(Path(path).read_text())

    def parse(self, text):
        x = y = 0.0
        cur, mode, region, pol, path = None, "G01", False, "D", []
        for blk in re.findall(r"%[^%]*%|[^*%\s][^*%]*\*", text):
            b = blk.strip("%").strip()
            if blk.startswith("%"):
                self.ext(b, pol)
                if b.startswith("LP"):
                    pol = b[2]
                continue
            b = b.rstrip("*")
            if b.startswith("G04") or b in ("G75", "M02"):
                continue
            m = re.match(r"^(G0[123])?(?:X([+-]?\d+))?(?:Y([+-]?\d+))?(?:I([+-]?\d+))?(?:J([+-]?\d+))?(D0[123])?$", b)
            if b.startswith("G36"):
                region, path = True, []
                continue
            if b.startswith("G37"):
                if path:
                    self.items.append(("region", pol, path))
                region, path = False, []
                continue
            if re.match(r"^D(\d{2,})$", b) and int(b[1:]) >= 10:
                cur = int(b[1:])
                continue
            if not m:
                raise SystemExit("unsupported Gerber block: %r" % b)
            g, sx, sy, si, sj, d = m.groups()
            if g:
                mode = g
            nx = num(sx, self.fmt) if sx else x
            ny = num(sy, self.fmt) if sy else y
            i = num(si, self.fmt) if si else 0.0
            j = num(sj, self.fmt) if sj else 0.0
            if d == "D02" or (d is None and region and not (sx or sy)):
                if region and path:
                    self.items.append(("region", pol, path))
                path = [("M", nx, ny)] if region else []
            elif d == "D01" or (d is None and (sx or sy)):
                seg = ("L", nx, ny) if mode == "G01" else ("A", nx, ny, x + i, y + j, mode == "G02", x, y)
                if region:
                    if not path:
                        path = [("M", x, y)]
                    path.append(seg)
                else:
                    self.items.append(("draw", pol, cur, x, y, seg))
            elif d == "D03":
                self.items.append(("flash", pol, cur, nx, ny))
            x, y = nx, ny

    def ext(self, b, pol):
        if b.startswith("FS"):
            m = re.match(r"FSLAX(\d)(\d)Y\d\d", b.rstrip("*"))
            self.fmt = int(m.group(2))
        elif b.startswith("MO") and "MM" not in b:
            raise SystemExit("only metric Gerber supported")
        elif b.startswith("AM"):
            lines = [l.strip() for l in b.split("*") if l.strip()]
            self.macros[lines[0][2:]] = [l for l in lines[1:] if not l.startswith("0")]
        elif b.startswith("AD"):
            m = re.match(r"ADD(\d+)([A-Za-z_][A-Za-z_0-9.]*),?([^*]*)\*", b)
            self.ap[int(m.group(1))] = (m.group(2), [float(v) for v in m.group(3).split("X") if v])
        elif b.startswith(("TF", "TA", "TO", "TD", "LP", "IP")):
            if b.startswith("IP") and "POS" not in b:
                raise SystemExit("negative image polarity not supported")
        elif b.startswith(("LM", "LR", "LS", "SR")):
            raise SystemExit("unsupported transform %s" % b[:2])


def flash_svg(ger, code, x, y, col):
    kind, p = ger.ap[code]
    Y = -y
    if kind == "C":
        return '<circle cx="%.4f" cy="%.4f" r="%.4f" fill="%s"/>' % (x, Y, p[0] / 2, col)
    if kind == "R":
        return '<rect x="%.4f" y="%.4f" width="%.4f" height="%.4f" fill="%s"/>' % (x - p[0] / 2, Y - p[1] / 2, p[0], p[1], col)
    if kind == "O":
        r = min(p) / 2
        return '<rect x="%.4f" y="%.4f" width="%.4f" height="%.4f" rx="%.4f" fill="%s"/>' % (
            x - p[0] / 2, Y - p[1] / 2, p[0], p[1], r, col)
    if kind in ger.macros:
        out = []
        for prim in ger.macros[kind]:
            f = prim.split(",")
            c = int(f[0])
            v = [evalm(e, p) for e in f[1:]]
            if v[0] == 0:
                raise SystemExit("macro clear exposure not supported")
            if c == 1:
                out.append('<circle cx="%.4f" cy="%.4f" r="%.4f" fill="%s"/>' % (x + v[2], Y - v[3], v[1] / 2, col))
            elif c == 4:
                n, rot = int(v[1]), v[-1]
                pts = [rot2(v[2 + 2 * k], v[3 + 2 * k], rot) for k in range(n + 1)]
                out.append('<polygon points="%s" fill="%s"/>' % (" ".join("%.4f,%.4f" % (x + a, Y - b) for a, b in pts), col))
            elif c == 20:
                w, (x1, y1), (x2, y2) = v[1], rot2(v[2], v[3], v[6]), rot2(v[4], v[5], v[6])
                out.append('<line x1="%.4f" y1="%.4f" x2="%.4f" y2="%.4f" stroke="%s" stroke-width="%.4f"/>'
                           % (x + x1, Y - y1, x + x2, Y - y2, col, w))
            elif c == 21:
                w, h, cx, cy, rot = v[1:6]
                pts = [rot2(cx + sx * w / 2, cy + sy * h / 2, rot) for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
                out.append('<polygon points="%s" fill="%s"/>' % (" ".join("%.4f,%.4f" % (x + a, Y - b) for a, b in pts), col))
            else:
                raise SystemExit("macro primitive %d not supported" % c)
        return "".join(out)
    raise SystemExit("aperture %s not supported" % kind)


def rot2(a, b, deg):
    r = math.radians(deg)
    return a * math.cos(r) - b * math.sin(r), a * math.sin(r) + b * math.cos(r)


def arc_d(seg):
    _, ex, ey, cx, cy, cw, sx, sy = seg
    r = math.hypot(sx - cx, sy - cy)
    a0, a1 = math.atan2(sy - cy, sx - cx), math.atan2(ey - cy, ex - cx)
    sweep = (a0 - a1) % (2 * math.pi) if cw else (a1 - a0) % (2 * math.pi)
    if sweep < 1e-9:                               # full circle in G75 mode
        mx, my = 2 * cx - sx, 2 * cy - sy
        f = 0 if cw else 1
        return "A%.4f,%.4f 0 0 %d %.4f,%.4f A%.4f,%.4f 0 0 %d %.4f,%.4f" % (r, r, f, mx, -my, r, r, f, ex, -ey)
    return "A%.4f,%.4f 0 %d %d %.4f,%.4f" % (r, r, 1 if sweep > math.pi else 0, 0 if cw else 1, ex, -ey)


def layer_svg(ger, col, bg="none"):
    out = []
    for it in ger.items:
        c = col if it[1] == "D" else bg
        if it[0] == "flash":
            out.append(flash_svg(ger, it[2], it[3], it[4], c))
        elif it[0] == "draw":
            _, _, code, x0, y0, seg = it
            kind, p = ger.ap[code]
            if kind != "C":
                raise SystemExit("draw with non-circular aperture %s" % kind)
            d = "M%.4f,%.4f " % (x0, -y0) + ("L%.4f,%.4f" % (seg[1], -seg[2]) if seg[0] == "L" else arc_d(seg))
            out.append('<path d="%s" fill="none" stroke="%s" stroke-width="%.4f" stroke-linecap="round" '
                       'stroke-linejoin="round"/>' % (d, c, p[0]))
        else:
            d = []
            for s in it[2]:
                d.append("M%.4f,%.4f" % (s[1], -s[2]) if s[0] == "M" else
                         "L%.4f,%.4f" % (s[1], -s[2]) if s[0] == "L" else arc_d(s))
            out.append('<path d="%sZ" fill="%s" fill-rule="nonzero"/>' % (" ".join(d), c))
    return "\n".join(out)


def drills(path):
    tools, hits, cur, plated = {}, [], None, {}
    attr = "Plated"
    for line in Path(path).read_text().splitlines():
        if line.startswith("; #@! TF.FileFunction"):      # separate PTH / NPTH files: file-level attribute
            attr = "NonPlated" if "NonPlated" in line else "Plated"
        if line.startswith("; #@! TA.AperFunction"):
            attr = "NonPlated" if "NonPlated" in line else "Plated"
        m = re.match(r"^T(\d+)C([\d.]+)", line)
        if m:
            tools[int(m.group(1))] = float(m.group(2))
            plated[int(m.group(1))] = attr
            continue
        m = re.match(r"^T(\d+)$", line)
        if m:
            cur = int(m.group(1))
            continue
        m = re.match(r"^X([-\d.]+)Y([-\d.]+)$", line)
        if m:
            hits.append((float(m.group(1)), float(m.group(2)), tools[cur], plated[cur]))
        elif re.match(r"^(G00|G01|G85|M15|M16)", line):
            raise SystemExit("routed drill slots not supported")
    return hits


def write(svg_body, box, scale, out, bg):
    x0, y0, x1, y1 = box
    s = ('<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="%.3f %.3f %.3f %.3f">'
         '<rect x="%.3f" y="%.3f" width="%.3f" height="%.3f" fill="%s"/>%s</svg>'
         % ((x1 - x0) * scale, (y1 - y0) * scale, x0, y0, x1 - x0, y1 - y0, x0, y0, x1 - x0, y1 - y0, bg, svg_body))
    svg = out.with_suffix(".svg")
    svg.write_text(s)
    subprocess.run(["rsvg-convert", "-o", str(out.with_suffix(".png")), str(svg)], check=True)
    svg.unlink()


def main():
    pkg, outdir = Path(sys.argv[1]), Path(sys.argv[2])
    scale = float(sys.argv[sys.argv.index("--scale") + 1]) if "--scale" in sys.argv else 10
    outdir.mkdir(parents=True, exist_ok=True)
    gdir = pkg / "fabrication" / "gerbers"
    g = {p.stem.split("-", 1)[1]: Gerber(p) for p in sorted(gdir.glob("*.g*")) if p.suffix != ".gbrjob"
         and p.stem.split("-", 1)[1] in ("F_Cu", "In1_Cu", "In2_Cu", "B_Cu", "F_Mask", "B_Mask", "F_Silkscreen",
                                         "B_Silkscreen", "F_Paste", "B_Paste", "Edge_Cuts")}
    hits = [h for f in sorted((pkg / "fabrication" / "drill").glob("*.drl")) for h in drills(f)]
    xs = [h[0] for h in hits]
    ys = [-h[1] for h in hits]
    edge = layer_svg(g["Edge_Cuts"], "#e8e8a0")
    pts = re.findall(r"(-?\d+\.\d+),(-?\d+\.\d+)", edge)
    xs += [float(a) for a, _ in pts]
    ys += [float(b) for _, b in pts]
    ex, ey = [float(a) for a, _ in pts], [float(b) for _, b in pts]
    ebox = (min(ex), min(ey), max(ex) - min(ex), max(ey) - min(ey))   # board area for the composites (outline bbox)
    box = (min(xs) - 2, min(ys) - 2, max(xs) + 2, max(ys) + 2)
    dr = "".join('<circle cx="%.4f" cy="%.4f" r="%.4f" fill="%s"/>' % (x, -y, d / 2, "#000")
                 for x, y, d, _ in hits)
    cols = {"F_Cu": "#d23c3c", "In1_Cu": "#c8a000", "In2_Cu": "#30a050", "B_Cu": "#3c78e6", "F_Mask": "#b060d0",
            "B_Mask": "#b060d0", "F_Silkscreen": "#ffffff", "B_Silkscreen": "#ffffff", "F_Paste": "#a0a0a0",
            "B_Paste": "#a0a0a0"}
    mirror = ('<g transform="translate(%.3f,0) scale(-1,1)">' % (box[0] + box[2]), "</g>")
    for name, col in cols.items():
        body = layer_svg(g[name], col) + edge + (dr if name.endswith("Cu") else "")
        if name.startswith("B_"):
            body = mirror[0] + body + mirror[1]
        write(body, box, scale, outdir / ("gerber_%s" % name), "#101010")
    np_ = sum(1 for h in hits if h[3] == "NonPlated")
    drill_map = "".join('<circle cx="%.4f" cy="%.4f" r="%.4f" fill="%s"/>' % (
        x, -y, max(d / 2, 0.15), "#ff5050" if p == "NonPlated" else "#50c0ff") for x, y, d, p in hits)
    write(drill_map + edge, box, scale, outdir / "gerber_drill", "#101010")
    for side in ("F", "B"):
        body = ('<rect x="%.3f" y="%.3f" width="%.3f" height="%.3f" fill="#1f5a32"/>' % ebox
                + layer_svg(g["%s_Cu" % side], "#2f7a45") + layer_svg(g["%s_Mask" % side], "#d8b25a")
                + layer_svg(g["%s_Silkscreen" % side], "#f4f4f4") + dr + edge)
        if side == "B":
            body = mirror[0] + body + mirror[1]
        write(body, box, scale, outdir / ("gerber_composite_%s" % ("top" if side == "F" else "bottom")), "#202020")
    print("%d drill hits (%d non-plated), %d tool sizes" % (len(hits), np_, len({h[2] for h in hits})))
    for name, ger in sorted(g.items()):
        print("%-13s %5d objects" % (name, len(ger.items)))
    print("written to %s" % outdir)


if __name__ == "__main__":
    main()
