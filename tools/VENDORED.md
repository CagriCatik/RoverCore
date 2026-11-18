# Vendored board tooling

RoverCore carries the board-tooling part of PCB-Project-Template so that
`scripts/kit` works from this repository alone, without a second checkout.

| Item | Value |
| --- | --- |
| Source | `https://github.com/CagriCatik/PCB-Project-Template` |
| Source commit | `65486a57c34182e49e1d76b4ed9779de235f1fb9` (2026-10-18, "docs updated"); byte-identical to the `tools/` and `scripts/kit` removed from RoverCore in `b2d1831` (originally from `4c6b5f8`) |
| Kit version | 2.0.0 (`tools/__init__.py`) |
| License | MIT, Copyright (c) 2026 Çağrı Çatık – same text as the repository [`LICENSE`](../LICENSE) |
| Vendored on | 2026-11-15 |

## Included

| Path | Purpose |
| --- | --- |
| `tools/core/` | paths (`kicad_env.py`), subprocess/common helpers, S-expression parser |
| `tools/kicad/` | kicad-cli adapter, design model, library tables, portability, IPC diagnostics |
| `tools/quality/` | `verify` quality gates (ERC, DRC + parity, libraries, footprints, pin/pad, metadata, 3D, BOM); optional firmware build |
| `tools/release/exports.py` | NO-GO draft / GO release manufacturing exports with manifest and hashes |
| `tools/thermal/` | steady-state thermal estimate |
| `tools/project/components.py` | component records used by the BOM gate |
| `tools/plugins/` | plugin status/verification (InteractiveHtmlBom used by exports) |
| `tools/environment/installer.py` | `doctor` and `install` (creates `.venv`) |
| `tools/cli/main.py`, `tools/__main__.py` | CLI entry point |
| `scripts/kit` | local launcher (`python -m tools`, prefers `.venv`) |
| `requirements.txt` | pinned Python dependencies for `.venv` (kicad-python, numpy, scipy) |
| `qa/fixtures/` | tooling fixtures built from KiCad's official libraries (not reviewed circuits) and their builder |
| `qa/tests/kit_test_support.py`, `test_verification.py`, `test_manufacturing.py`, `test_thermal.py`, `test_ipc.py`, `test_plugins.py`, `test_components.py`, `test_installer.py` | tool tests |

## Deliberately not included

Project generator and templates (`tools/project/templates.py`, `profiles.py`,
`registry.py`, `meta/templates/`, `hardware/native-defaults/`), the PySide6 GUI
(`tools/gui/`), the interactive manager (`tools/cli/interactive.py`), kit
packaging (`tools/release/packaging.py`), installer shell wrappers and their
tests (`test_templates`, `test_gui`, `test_manager`, `test_layout`,
`test_toolchains`, `test_hardening`).

## Local modifications (diff against the source commit)

- `tools/cli/main.py`: removed the `templates`, `create`, `projects`, `open`,
  `manager`, `gui` and `package` commands; `install` lost its template options;
  banner names RoverCore.
- `tools/environment/installer.py`: `install` and `doctor` no longer install or
  report KiCad templates; messages point to `scripts/kit install`.
- `tools/core/kicad_env.py`: machine-local state directory renamed to
  `RoverCore-kit` so it never shares state with a separate template checkout.
- `tools/__init__.py`, `tools/thermal/geometry.py`, `tools/kicad/ipc.py`:
  docstring/messages only.
- `tools/release/exports.py` (2026-11-18): drill export with `--excellon-separate-th`
  (`<board>-PTH.drl`, `<board>-NPTH.drl`, no merged file); in a merged file the
  plated/non-plated distinction is only in X2 comment lines. Test expects
  `divider-PTH.drl` and no merged file.
- `tools/release/exports.py` (2026-11-18): BOM `--group-by` also groups by
  `${DNP}`. Without it a fitted part (R616) was merged into a DNP line
  (R801/R802) and marked DNP in the BOM while the position file placed it.
- `qa/tests/test_components.py`, `test_thermal.py`, `test_installer.py`: use
  fixture copies instead of the project generator; installer tests check the
  template-free behaviour and the local launcher.

## Use

```sh
scripts/kit install              # once: creates .venv from requirements.txt (network for pip)
scripts/kit doctor               # read-only environment diagnostics
scripts/kit verify .             # quality gates
scripts/kit export . --revision A1   # DRAFT / NO-GO unless a signed GO release is authorized
scripts/kit thermal analyze .    # needs hardware/simulations/thermal/power_sources.csv or --power
.venv/bin/python -m unittest discover -s qa/tests -t qa/tests
```

Results of these commands are tooling results only. They do not establish
electrical, thermal or fabrication readiness, and no fabrication release is
claimed. Requires KiCad 10.0.7 (official macOS DMG) at `/Applications/KiCad`
or `KICAD_APP`/`KICAD_CLI`.

Updating from a newer template commit: copy the files listed above, re-apply
the local modifications, update the source commit here and rerun the tests.
