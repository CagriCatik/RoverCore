"""Builds and runs the host sequence tests of firmware/app/enable_fsm.c (O-35 Rev1).

Skipped when no C compiler is available. The C test models U505/U506 and samples the
firmware at different intervals, including short supply interruptions.
"""
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CC = shutil.which("cc") or shutil.which("gcc") or shutil.which("clang")


@unittest.skipUnless(CC, "no C compiler")
class EnableFsmHostTest(unittest.TestCase):
    def test_sequences(self):
        with tempfile.TemporaryDirectory() as d:
            exe = Path(d) / "test_enable_fsm"
            subprocess.run([CC, "-std=c99", "-Wall", "-Wextra", "-Werror", "-I", str(ROOT / "firmware/app"),
                            str(ROOT / "firmware/app/enable_fsm.c"), str(ROOT / "firmware/tests/test_enable_fsm.c"),
                            "-o", str(exe)], check=True, capture_output=True, text=True)
            run = subprocess.run([str(exe)], capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
            self.assertIn("all tests passed", run.stdout)


if __name__ == "__main__":
    unittest.main()
