"""Host tests of the first firmware stage (supervisor, diagnostics, scaling) and pin-header parity.

- Builds and runs firmware/tests/test_supervisor.c (skipped without a C compiler).
- Checks that firmware/bsp/esp32s3/rovercore_pins.h is exactly what firmware/tools/gen_pins.py
  generates from hardware/interfaces/pinmap.csv.
These are host tests only; DevKit and carrier checks are listed in docs/vcu/firmware-plan.md.
"""
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CC = shutil.which("cc") or shutil.which("gcc") or shutil.which("clang")
APP = ROOT / "firmware/app"


@unittest.skipUnless(CC, "no C compiler")
class SupervisorHostTest(unittest.TestCase):
    def test_supervisor(self):
        with tempfile.TemporaryDirectory() as d:
            exe = Path(d) / "test_supervisor"
            subprocess.run([CC, "-std=c99", "-Wall", "-Wextra", "-Werror", "-Wconversion", "-I", str(APP),
                            str(APP / "enable_fsm.c"), str(APP / "supervisor.c"), str(APP / "diag.c"),
                            str(ROOT / "firmware/tests/test_supervisor.c"), "-o", str(exe)],
                           check=True, capture_output=True, text=True)
            run = subprocess.run([str(exe)], capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
            self.assertIn("all tests passed", run.stdout)


class PinHeaderParityTest(unittest.TestCase):
    def test_header_matches_pinmap(self):
        run = subprocess.run([sys.executable, str(ROOT / "firmware/tools/gen_pins.py"), "--check"],
                             capture_output=True, text=True, cwd=ROOT)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)


if __name__ == "__main__":
    unittest.main()
