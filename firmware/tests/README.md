# Firmware tests

Host tests (C99, no target), built and run by the Python runners in `qa/tests`:

- `test_enable_fsm.c` → `qa/tests/test_firmware_enable_fsm.py`
- `test_supervisor.c` → `qa/tests/test_firmware_supervisor.py` (also checks the pin header)

DevKit tests (B) and carrier measurements (C) are manual and listed in
`docs/vcu/firmware-plan.md`; they are not replaced by these host tests.
