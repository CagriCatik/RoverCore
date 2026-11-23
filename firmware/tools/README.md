# Firmware tools

See `../README.md` for the module boundary and select the platform before
adding generated source files. Do not create fake working build targets.

- `gen_pins.py`: writes `../bsp/esp32s3/rovercore_pins.h` from
  `hardware/interfaces/pinmap.csv`; `--check` exits 1 if the header is out of date.
