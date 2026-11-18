# Mechanical design and integration

Enclosure CAD, mounting patterns, height restrictions, connectors, keep-outs,
bolts, center-of-mass and assembly clearances. Keep real source CAD plus the
corresponding export(s) when redistribution rights permit.

## RoverCore K1 mounting (provisional, 2026-11-18)

No chassis or enclosure data yet. Four M3 holes, NPTH 3.2 mm, footprint
`ProjectFootprints:MountingHole_3.2mm_M3_NPTH_Keepout`, positions in K1 coordinates (top-left outline corner,
y down, board 150 x 85 mm): H1 (21.0 | 4.0), H2 (4.0 | 43.0), H3 (91.0 | 81.0), H4 (146.0 | 81.0).
Criteria and search: `hardware/scripts/mounting_holes.py`; report section 3n. Confirm against the vehicle before
fabrication; the DevKit field top right has no support of its own.
