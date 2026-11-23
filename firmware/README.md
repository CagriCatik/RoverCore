# Firmware

The template is toolchain-neutral: STM32Cube + CMake, Zephyr, ESP-IDF,
Arduino, or other builds are NOT mixed by default. Select one target and
record toolchain pinning in docs/architecture.md.

- `app/`: target-independent application behavior, state machines, protocols.
- `bsp/`: board-specific pin definitions, clock trees, startup and vendor HAL.
- `drivers/`: stable interfaces, concrete peripheral/device adapters.
- `config/`: reviewed build configuration (not unverified pin assignments).
- `tests/`: host tests, mocks, embedded/HIL tests where applicable.
- `tools/`: flashing/debug helpers with explicit target and safety checks.

Hardware is authoritative for pinouts; firmware config tracks the reviewed
`hardware/interfaces/pinmap.csv` contract.

## Selected target (2026-11-23)

ESP-IDF v5.x, ESP32-S3-DevKitC-1 N16R8 v1.1, project in `esp32/`
(`idf.py set-target esp32s3 build`). Stage plan, safety rules and the split into
host tests, DevKit tests and carrier measurements: `docs/vcu/firmware-plan.md`.
Actuators stay locked unless `CONFIG_ROVERCORE_ACTUATORS_PERMITTED` is set (default n).
