"""Environment installation and diagnostics without the template generator (RoverCore)."""

import json
import subprocess

from kit_test_support import ROOT, EnvPatch, TempDirTest, requires_kicad
from tools.environment import installer as environment


@requires_kicad
class InstallerTests(TempDirTest):
    def run_install(self):
        return environment.install(skip_venv=True, verify_plugins=False, report_path=self.tmp / "report.json")

    def test_first_and_repeated_installation(self):
        first = self.run_install()
        steps = {s["step"]: s for s in first["steps"]}
        self.assertNotEqual(first["overall"], "FAIL", first["failed"])
        self.assertEqual(steps["kicad"]["status"], "PASS")
        self.assertEqual(steps["library_paths"]["status"], "PASS")
        self.assertNotIn("kicad_templates", steps, "RoverCore must not install KiCad templates")
        second = self.run_install()
        self.assertEqual(second["changed"], [])
        report = json.loads((self.tmp / "report.json").read_text())
        self.assertEqual(report["kind"], "install")
        self.assertIn("ipc", {s["step"] for s in report["steps"]})

    def test_missing_kicad_aborts(self):
        with EnvPatch(KICAD_CLI=str(self.tmp / "missing-cli")):
            report = self.run_install()
        self.assertEqual(report["overall"], "FAIL")
        self.assertIn("abort", report["failed"])

    def test_doctor_is_read_only_and_template_free(self):
        templates = self.tmp / "templates"
        with EnvPatch(KICAD_USER_TEMPLATE_DIR=str(templates)):
            report = environment.doctor(report_path=self.tmp / "doctor.json")
        self.assertFalse(templates.exists())
        self.assertEqual(report["changed"], [])
        self.assertNotIn("kicad_templates", {s["step"] for s in report["steps"]})


class LauncherTests(TempDirTest):
    def test_local_launcher_passes_options_and_exit_status(self):
        env = {"KICAD_CLI": str(self.tmp / "missing"), "ROVERCORE_KIT_ROOT": "",
               "PATH": "/usr/bin:/bin:/opt/homebrew/bin:/usr/local/bin"}
        with EnvPatch(**env):
            result = subprocess.run([str(ROOT / "scripts/kit"), "install", "--skip-venv", "--no-plugin-verify",
                                     "--report", str(self.tmp / "r.json")],
                                    capture_output=True, text=True, timeout=300, stdin=subprocess.DEVNULL)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("kicad-cli not found", result.stdout)
        self.assertTrue((self.tmp / "r.json").is_file())

    def test_generator_and_gui_commands_are_absent(self):
        result = subprocess.run([str(ROOT / "scripts/kit"), "--help"], capture_output=True, text=True, timeout=120)
        self.assertEqual(result.returncode, 0, result.stderr)
        for command in ("doctor", "verify", "export", "thermal", "libraries"):
            self.assertIn(command, result.stdout)
        for command in ("create", "templates", "gui", "manager", "package"):
            self.assertNotIn("    " + command + " ", result.stdout)

    def test_venv_stamp_skips_reinstall(self):
        # Never install from a test: only exercise setup_venv when it must be a no-op.
        if not environment.venv_up_to_date():
            self.skipTest("repository .venv missing or older than requirements.txt; run scripts/kit install")
        step = environment.setup_venv()
        self.assertEqual(step["status"], "UNCHANGED", step)


if __name__ == "__main__":
    import unittest

    unittest.main()
