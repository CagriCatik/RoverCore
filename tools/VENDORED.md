# Vendored board tooling

RoverCore carries the board-tooling part of PCB-Project-Template so that
`scripts/kit` works from this repository alone, without a second checkout.

| Item | Value |
| --- | --- |
| Source | `https://github.com/CagriCatik/PCB-Project-Template` |
| Source commit | `db2a4846e00e38126f91e897023e84909ba111dd` (2026-11-23, "kit export: shareable GLB/STL view models without restricted 3D models"); updated from `c28a376f0dd5bddb55cffc98bd07f630ea71973f`, before that from `f349dc7e2170e77a2fb7e9efadbcb06f562cd6b6` and before that from `65486a57c34182e49e1d76b4ed9779de235f1fb9` (2026-10-18) by three-way merges, see below |
| Kit version | 2.0.0 (`tools/__init__.py`) |
| License | MIT, Copyright (c) 2026 Çağrı Çatık – same text as the repository [`LICENSE`](../LICENSE) |
| Vendored on | 2026-11-15, updated 2026-11-23 |

## Included

| Path | Purpose |
| --- | --- |
| `tools/core/` | paths (`kicad_env.py`), subprocess/common helpers, S-expression parser |
| `tools/kicad/` | kicad-cli adapter, design model, library tables, portability, IPC diagnostics |
| `tools/quality/` | `verify` quality gates (ERC, DRC + parity, libraries, footprints, pin/pad, metadata, 3D, BOM); optional firmware build |
| `tools/release/exports.py` | NO-GO draft / GO release manufacturing exports with manifest and hashes |
| `tools/thermal/` | steady-state thermal estimate |
| `tools/project/components.py` | component records used by the BOM gate |
| `tools/project/contracts.py`, `assumptions.py`, `tools/quality/power_budget.py`, `tools/core/evidence.py` | `kit contracts check`, `kit assumptions check`, `kit power-budget calculate` (added 2026-11-23) |
| `tools/schematic/` | `kit schematic snapshot\|compare\|review\|lint\|status` (added 2026-11-23) |
| `tools/quality/board_model.py`, `board_diff.py`, `fab_check.py`, `gerber_preview.py`, `model_fit.py`, `mounting.py`, `power_paths.py` | `kit board diff`, `kit fab check\|preview`, `kit models fit`, `kit mounting print`, `kit power paths` (added 2026-11-23, from RoverCore's former `hardware/scripts` review scripts) |
| `tools/plugins/` | plugin status/verification (InteractiveHtmlBom used by exports) |
| `tools/environment/installer.py` | `doctor` and `install` (creates `.venv`) |
| `tools/cli/main.py`, `tools/__main__.py` | CLI entry point |
| `scripts/kit` | local launcher (`python -m tools`, prefers `.venv`) |
| `requirements.txt` | pinned Python dependencies for `.venv` (kicad-python, numpy, scipy) |
| `qa/fixtures/` | tooling fixtures built from KiCad's official libraries (not reviewed circuits) and their builder |
| `qa/tests/kit_test_support.py`, `test_verification.py`, `test_manufacturing.py`, `test_thermal.py`, `test_ipc.py`, `test_plugins.py`, `test_components.py`, `test_installer.py`, `test_design_contracts.py`, `test_schematic.py`, `test_board_review.py`, `test_board_tools.py` | tool tests |

## Deliberately not included

Project generator and templates (`tools/project/templates.py`, `profiles.py`,
`registry.py`, `meta/templates/`, `hardware/native-defaults/`), the PySide6 GUI
(`tools/gui/`), the interactive manager (`tools/cli/interactive.py`), kit
packaging (`tools/release/packaging.py`), installer shell wrappers and their
tests (`test_templates`, `test_gui`, `test_manager`, `test_layout`,
`test_toolchains`, `test_hardening`). Also the `carrier` command
(`tools/project/carrier.py`, `test_carrier.py`): it validates the socket inventory of the
template's `esp32-carrier` project layout and its tests need the generator and PlatformIO;
RoverCore checks its DevKit socket with `hardware/scripts/check_socket_pinmap.py`.

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
- `tools/release/exports.py`: no local change any more. The two RoverCore fixes of
  2026-11-18 (separate PTH/NPTH drill files, BOM grouped by `${DNP}`) are in the template
  since `f349dc7`, together with a drill file-name check and a BOM-vs-schematic DNP check;
  the template version replaced the local one.
- `qa/tests/test_components.py`, `test_thermal.py`, `test_installer.py`: use
  fixture copies instead of the project generator; installer tests check the
  template-free behaviour and the local launcher.
- `qa/tests/kit_test_support.py`: `create_seeded_project()` stands in for the generator in
  `test_design_contracts.py` (fixture copy renamed to the board name plus the empty contract
  seeds and the pinmap header, same content as the template seeds).
- `qa/tests/test_schematic.py`: two tests skipped – the kit-repository Git rule (RoverCore's
  AGENTS.md allows local commits only) and generated-project content.
- `tools/cli/main.py`: additionally without the `carrier` command.

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

Updating from a newer template commit: three-way merge per file (base = the source commit
above, ours = RoverCore, theirs = the new template commit, e.g. `git merge-file`), keep the
local modifications listed above, update the source commit here, rerun the tests and
`scripts/kit verify .`, then export a trial package and compare it with the current DRAFT
package (`scripts/kit compare-exports`).

Update 2026-11-23 (`65486a5` → `f349dc7`): 120 tests OK (3 skipped), `verify` PASS (required
gates; advisory metadata/BOM findings unchanged). A trial export compared with
`rev-A3-DRAFT`: first run differed only in `assembly/ibom.html` (iBOM bounding box of the
keep-out-only footprint H4); a second run was identical in all 42 artifacts. iBOM is
therefore not always reproducible for H4; this comes from the plugin, not from the kit
update (unchanged iBOM call, standalone runs give the A3 value). New BOM/drill checks:
`drill_file_consistency` COMPLETE. The new `contracts`, `assumptions` and `power-budget`
commands stop with a missing-file error until RoverCore has filled
`hardware/interfaces/design-contracts.json`, `assumptions.json`,
`hardware/simulations/power/budget.json` and `firmware/bsp/pin-bindings.json`.

Update 2026-11-23 (`f349dc7` → `c28a376`): `tools/cli/main.py` and `tools/project/assumptions.py`
merged without conflict (local modifications kept), seven new `tools/quality` modules and two test
files copied unchanged. 147 tests OK (3 skipped), `verify` PASS (required gates; advisory
metadata/BOM findings unchanged).

Update 2026-11-23 (`c28a376` → `db2a484`): `exports.py`, `verification.py` and
`test_manufacturing.py` taken over unchanged; `tools/cli/main.py` merged (the local `%` fix is now in
the template). `qa/verification.json` sets `restricted_3d_models` to `*/3d-models/vendor/*`, so the
vendor connector models (J102/J103, not redistributable) stay out of `mechanical/board-view.glb/.stl`.
