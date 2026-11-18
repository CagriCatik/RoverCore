"""Re-import behaviour of hardware/scripts/build_board.py on a copy of the board (needs the KiCad 10 Python).

Checks: a normal sync keeps manual positions, sides and drawings; it restores wrong pad nets, clears nets of
pads that are not in the netlist (mechanical pads), sets and clears DNP / BOM exclusion, re-adds a deleted footprint; a layout
with unknown references aborts without writing. Skipped when the KiCad Python is not installed.
"""
import hashlib
import shutil
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
KPY = Path("/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3")
TOOL = ROOT / "hardware/scripts/build_board.py"


def kpy(code, *args):
    run = subprocess.run([str(KPY), "-c", textwrap.dedent(code), *map(str, args)], capture_output=True, text=True)
    if run.returncode:
        raise AssertionError(run.stdout + run.stderr)
    return run.stdout


def tool(*args):
    return subprocess.run([str(KPY), str(TOOL), *map(str, args)], capture_output=True, text=True)


@unittest.skipUnless(KPY.exists(), "KiCad Python not installed")
class BuildBoardSyncTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.pcb = Path(self.dir.name) / "copy.kicad_pcb"
        shutil.copy(ROOT / "RoverCore.kicad_pcb", self.pcb)

    def tearDown(self):
        self.dir.cleanup()

    def test_sync_keeps_placement_and_restores_data(self):
        kpy("""
            import pcbnew, sys
            b = pcbnew.LoadBoard(sys.argv[1]); fps = {f.GetReference(): f for f in b.GetFootprints()}
            fps["Q401"].SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(40), pcbnew.FromMM(40)))   # manual move
            fps["R520"].Flip(fps["R520"].GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)    # manual side change
            fps["C401"].Pads()[0].SetNet(b.FindNet("+3V3"))                                    # wrong net
            fps["R101"].SetDNP(True)                                                            # stale flag
            fps["TP101"].SetAttributes(fps["TP101"].GetAttributes() & ~pcbnew.FP_EXCLUDE_FROM_BOM)
            line = pcbnew.PCB_SHAPE(b, pcbnew.SHAPE_T_SEGMENT); line.SetLayer(pcbnew.Dwgs_User)
            line.SetStart(pcbnew.VECTOR2I(0, 0)); line.SetEnd(pcbnew.VECTOR2I(pcbnew.FromMM(5), 0)); b.Add(line)
            [p for p in fps["J102"].Pads() if p.GetNumber() == ""][0].SetNet(b.FindNet("GND"))   # mechanical pad
            b.Remove(fps["C512"])                                                               # deleted footprint
            b.Save(sys.argv[1])
        """, self.pcb)
        run = tool("--board", self.pcb)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertIn("added C512", run.stdout)
        out = kpy("""
            import pcbnew, sys
            b = pcbnew.LoadBoard(sys.argv[1]); fps = {f.GetReference(): f for f in b.GetFootprints()}
            T = pcbnew.ToMM
            print(round(T(fps["Q401"].GetPosition().x), 3), round(T(fps["Q401"].GetPosition().y), 3))
            print(fps["R520"].GetLayerName())
            print(fps["C401"].Pads()[0].GetNetname(), fps["C401"].Pads()[1].GetNetname())
            print(fps["R101"].IsDNP(), bool(fps["TP101"].GetAttributes() & pcbnew.FP_EXCLUDE_FROM_BOM))
            print(sum(1 for d in b.GetDrawings() if isinstance(d, pcbnew.PCB_SHAPE) and d.GetLayer() == pcbnew.Dwgs_User and d.GetShape() == pcbnew.SHAPE_T_SEGMENT))
            print("C512" in fps, len(fps))
            print(repr([p for p in fps["J102"].Pads() if p.GetNumber() == ""][0].GetNetname()))
        """, self.pcb).split("\n")
        self.assertEqual(out[0], "40.0 40.0")
        self.assertEqual(out[1], "B.Cu")
        self.assertEqual(out[2], "/Power/VBAT_PROT GND")
        self.assertEqual(out[3], "False True")
        self.assertEqual(out[4], "1")
        self.assertEqual(out[5], "True 257")  # 253 + mounting holes H1-H4 (2026-11-18)
        self.assertEqual(out[6], "''")

    def test_unknown_layout_reference_aborts_without_writing(self):
        layout = Path(self.dir.name) / "bad_layout.py"
        layout.write_text('LAYOUT = {"parts": {"X999": (0, 0, 0)}, "pack": [], "outline": (0, 0, 10, 10)}\n')
        before = hashlib.sha256(self.pcb.read_bytes()).hexdigest()
        run = tool("--board", self.pcb, "--bootstrap", "--layout", layout)
        self.assertNotEqual(run.returncode, 0)
        self.assertIn("ABORTED", run.stdout + run.stderr)
        self.assertEqual(before, hashlib.sha256(self.pcb.read_bytes()).hexdigest())


if __name__ == "__main__":
    unittest.main()
