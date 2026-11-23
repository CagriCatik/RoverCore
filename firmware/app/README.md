# Firmware app

See `../README.md` for the module boundary and select the platform before
adding generated source files. Do not create fake working build targets.

## Modules

- `enable_fsm.c/.h`: enable (Freigabe) state machine S0/S1/S2 for O-35 Rev1
  (docs/vcu/rev1-versorgung-und-boardwahl.md 3.18, 3.20). Platform-independent;
  host sequence tests in `../tests/test_enable_fsm.c`, run by
  `qa/tests/test_firmware_enable_fsm.py`. No target build exists yet.
- `supervisor.c/.h`: binds `enable_fsm` to the board: supply check (thresholds are
  proposals, rev1-versorgung 3.7), sampling-gap fault, `ACT_ARMED` edge flag, output
  locking (`actuators_permitted`), no automatic re-enable. Host tests in
  `../tests/test_supervisor.c`, run by `qa/tests/test_firmware_supervisor.py`.
- `diag.c/.h`: status-LED patterns and the serial `RC ...` diagnostic line.
- `sense.h`: nominal scaling of the ADC pin voltages (estimates, not calibrated).

Target integration: `../esp32/` (ESP-IDF), plan and test levels in
`docs/vcu/firmware-plan.md`.
