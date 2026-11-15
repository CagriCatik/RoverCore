# Rules for Codex / Claude / other agents (RoverCore)

Created from the Generic PCB template of PCB-Project-Template 2.0.0.

## Architecture invariants

1. One KiCad 10.0.7 project; `.kicad_pro`, `.kicad_sch`, `.kicad_pcb` at the root.
2. Hardware truth lives in the schematic, board and verified part datasheets;
   `hardware/interfaces/pinmap.csv` is a reviewed interface artifact, not a second truth.
3. Keep firmware HAL/BSP (`firmware/bsp`) separate from application logic (`firmware/app`).
4. Custom KiCad libraries are local under `hardware/libraries` and referenced via `${KIPRJMOD}`.
5. Generated outputs are not source. Never hand-edit Gerbers, drill, position files,
   PDFs or ERC/DRC reports.

## Before changing native KiCad files

- Confirm KiCad 10.0.7; refuse scripted writes while `~*.lck` lock files exist.
- Use the real KiCad CLI/APIs; never fabricate reports or claim IPC is available when it is not.
- Make small, auditable changes and re-run `scripts/kit verify`.
- Never substitute dummy 3D models or invented datasheets for real vendor data.
- Label every calculation as an estimate; estimates do not replace measurement.

## Verification and release

- ERC, DRC and schematic parity run with the pinned toolchain; review warnings and exclusions.
- After routing there must be no unintended unconnected items.
- Confirm connector orientation/pinout, polarity, voltage domains, current, protection,
  copper/thermal limits, DFM clearances and supply chain.
- Firmware changes need module-level and hardware-interface edge-case tests.
- A GO release needs a signed approval (`manufacturing/approval.example.json`), a clean Git
  commit, passing release-mode verification, and explicit `--authorize`.

## Git ownership

Since 2026-11-15 the owner has authorized agents to stage and commit **locally**
on `main`: stage only the reviewed files by explicit path (no `git add -A`/`.`),
one coherent change per commit, and report each commit. Agents must not run
`push`, `pull`, `merge`, `rebase`, `reset`, `clean`, `stash`, `tag`, `cherry-pick`,
amend or rewrite history, or working-tree-changing `checkout`/`switch`, and must
not create branches, pull requests or releases. `git fetch` for comparison is
allowed. Pushing stays with the owner. Never commit locks, `.kicad_prl`,
backups, generated QA output or unlicensed vendor assets.
