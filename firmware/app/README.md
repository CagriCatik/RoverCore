# Firmware app

See `../README.md` for the module boundary and select the platform before
adding generated source files. Do not create fake working build targets.

## Modules

- `enable_fsm.c/.h`: enable (Freigabe) state machine S0/S1/S2 for O-35 Rev1
  (docs/vcu/rev1-versorgung-und-boardwahl.md 3.18, 3.20). Platform-independent;
  host sequence tests in `../tests/test_enable_fsm.c`, run by
  `qa/tests/test_firmware_enable_fsm.py`. No target build exists yet.
