"""Shared-return and independent branch scenarios for the VCU estimate."""
import unittest

from hardware.simulations.power.servo_voltage_budget import estimate


class ServoVoltageBudgetTests(unittest.TestCase):
    def test_shared_path_carries_all_loads_including_reserve(self):
        result = estimate(6.7, 0.01, [(5, 0.04), (4, 0.02), (1, 0.1)])
        self.assertAlmostEqual(result["total_current_a"], 10)
        for actual, expected in zip(result["connector_voltage_v"], [6.4, 6.52, 6.5]):
            self.assertAlmostEqual(actual, expected)

    def test_unloaded_branch_still_sees_common_drop(self):
        result = estimate(6.5, 0.02, [(5, 0.1), (0, 0.1)])
        self.assertAlmostEqual(result["connector_voltage_v"][1], 6.4)

    def test_impossible_drop_is_visible_not_clamped(self):
        self.assertLess(estimate(1, 1, [(2, 1)])["connector_voltage_v"][0], 0)

    def test_invalid_inputs_rejected(self):
        for bad in [-1, float("nan"), float("inf")]:
            for inputs in [(bad, 0, [(1, 0)]), (1, bad, [(1, 0)]),
                           (1, 0, [(bad, 0)]), (1, 0, [(1, bad)])]:
                with self.subTest(inputs=inputs), self.assertRaises(ValueError):
                    estimate(*inputs)

    def test_empty_load_list_rejected(self):
        with self.assertRaises(ValueError):
            estimate(6.5, 0, [])
