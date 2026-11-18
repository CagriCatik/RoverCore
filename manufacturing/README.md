# Manufacturing

`fabrication/generated` / `assembly/generated` (ignored) hold WIP exports.
When approved, capture named immutable release packages under `releases/`,
including Gerbers, drills, assembly position files, BOM, IPC outputs as
applicable, build notes, source commit and SHA-256 manifests.

Do not edit exported Gerber/drill files manually. Use KiCad output jobs or
KiCad CLI to regenerate from approved design.

## RoverCore status (2026-11-18)

Current DRAFT package: `releases/generated/rev-A2-DRAFT` (variant B, 160 x 85 mm, NO-GO). `rev-A1-DRAFT` and
`rev-A0-tooling-DRAFT` are superseded (marked with `SUPERSEDED.txt`); do not upload them. Fabrication stays stopped
until the vehicle check and the open reviews are done.
