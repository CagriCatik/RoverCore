# RoverCore

KiCad 10.0.7 project created from the **Generic PCB** template
of PCB-Project-Template 2.0.0 on 2026-11-14.

| Path | Owns |
| --- | --- |
| `RoverCore.kicad_pro/.kicad_sch/.kicad_pcb` | Native KiCad project (hardware truth) |
| `hardware/` | Custom libraries (`${KIPRJMOD}`), interfaces, constraints, mechanical, simulation |
| `firmware/` | Optional firmware, BSP and drivers |
| `components/` | Component records, datasheets, SPICE models |
| `manufacturing/` | Release checklist, approvals, generated exports |
| `docs/` | Requirements, architecture, interfaces, bring-up, decisions |
| `qa/` | Verification configuration, design reviews, reports |

## Project status

Modular VCU carrier board (Rev 1) for a plug-in ESP32-S3-DevKitC-1, IMU and
OLED. Current work package: power design and board selection, see
[docs/vcu/rev1-versorgung-und-boardwahl.md](docs/vcu/rev1-versorgung-und-boardwahl.md).
GPIO and connector plan (draft):
[docs/vcu/rev1-pin-und-anschlussplan.md](docs/vcu/rev1-pin-und-anschlussplan.md),
machine-readable in `hardware/interfaces/pinmap.csv`.
Schematic: sheet `Power` with battery input and input protection (draft, candidates);
other sheets and the board are still empty. GPIOs and footprints are not frozen.

## Everyday commands (run from this repository)

```sh
scripts/kit install                       # once: local .venv (kicad-python, numpy, scipy)
scripts/kit doctor                        # read-only environment diagnostics
scripts/kit verify .                      # ERC, DRC, parity, libraries, metadata, 3D, BOM
scripts/kit export . --revision A1        # NO-GO draft manufacturing outputs
scripts/kit thermal analyze .             # steady-state thermal estimate
```

The tooling is vendored from PCB-Project-Template; source commit, license and
local changes are in [`tools/VENDORED.md`](tools/VENDORED.md). A clean ERC/DRC
run is a tooling result only; it does not establish electrical, thermal or
fabrication readiness. See `AGENTS.md` for the rules that apply to automated edits.

## VCU-Review und lokale Werkzeuge

[Review](docs/vcu/rev1-review-2026-11-15.md) · [Werkzeuge](docs/vcu/tooling-integration.md)
