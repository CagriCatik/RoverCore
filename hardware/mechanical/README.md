# Mechanical design and integration

Enclosure CAD, mounting patterns, height restrictions, connectors, keep-outs,
bolts, center-of-mass and assembly clearances. Keep real source CAD plus the
corresponding export(s) when redistribution rights permit.

## RoverCore mounting (SUPERSEDED first draft, 2026-11-18)

No chassis or enclosure data yet. Four M3 holes, NPTH 3.2 mm, footprint
`ProjectFootprints:MountingHole_3.2mm_M3_NPTH_Keepout`, positions in K1 coordinates (top-left outline corner,
y down, board 150 x 85 mm): H1 (21.0 | 4.0), H2 (4.0 | 43.0), H3 (91.0 | 81.0), H4 (146.0 | 81.0).
Criteria and search: `hardware/scripts/mounting_holes.py`; report section 3n. Confirm against the vehicle before
fabrication; the DevKit field top right has no support of its own.

## RoverCore mounting, variant B (current, provisional until the vehicle check)

Outline 160 x 85 mm. Four M3 holes, NPTH 3.2 mm (footprint `MountingHole_3.2mm_M3_NPTH_Keepout`), K1 coordinates:
H1 (4.5 | 4.5), H2 (4.5 | 80.5), H3 (155.5 | 18.0), H4 (155.5 | 80.5). H3 sits 18 mm down so that washer, head
and standoff stay >= 15 mm (in plane) from the DevKit antenna keep-out. Set by `hardware/scripts/mount_rework_b.py`;
review in `docs/vcu/rev1-befestigung-vorschlag.md`.
