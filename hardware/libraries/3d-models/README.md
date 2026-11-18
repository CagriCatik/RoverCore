# Verified 3D model library

Keep original vendor-provided STEP/STL files with traceable source and licence;
validate origin/orientation, height, courtyard and mechanical fit. Do not
substitute dummy 3D shapes as if they were sourced components.

## Project files

- `models.csv` lists every vendor model used on the board: references, file, the offset and rotation that align
  it to the footprint, source URL, retrieval date, SHA-256, licence note and how the fit was checked.
- The STEP files themselves live in `vendor/` and are **not in Git** (`.gitignore`): the vendor terms allow use
  for evaluation, not redistribution. A fresh checkout fetches them from the source in `models.csv`, checks the
  SHA-256 and then runs `hardware/scripts/assign_vendor_models.py` (already applied to `RoverCore.kicad_pcb`).
- Without the files, KiCad shows these parts without a body and `kit verify` reports them under `models_3d`.
- Fit check of a new model: `hardware/scripts/model_fit_check.py` renders the footprint alone with a candidate
  offset/rotation (top, front, side, iso).

## Own package models (`project/`)

For parts where neither the KiCad library (the footprints reference files that kicad-packages3D does not contain)
nor an account-free vendor or community source offers a model, `project/` holds own VRML models built by
`hardware/scripts/make_package_models.py` from the manufacturers' package drawings (sources and checked dimensions
per row in `models.csv`). They are in Git (MIT, own work). They render in KiCad but do not go into a STEP export.
Estimated dimensions (XT30PW-M height) are marked in `models.csv`.
