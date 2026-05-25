"""
test_delivery.py — Automated test suite for FastBox Delivery Simulator
=======================================================================
Covers:
  - Unit tests for every core function
  - End-to-end tests for base_case.json + all 10 provided test cases
  - Edge cases (no packages, single agent, unknown warehouse, etc.)

Run with:
    python test_delivery.py
    python test_delivery.py -v      # verbose
"""

import json
import math
import os
import sys
import unittest
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from utils import (
    euclidean_distance,
    load_data,
    normalize_data,
    assign_packages,
    simulate_deliveries,
    generate_report,
    export_csv,
)

HERE = Path(__file__).parent  # project root (where test_case_*.json live)


# ── helpers ──────────────────────────────────────────────────────────

def run_pipeline(filepath: str | Path, use_delays: bool = False) -> tuple[dict, dict]:
    """Load → normalise → assign → simulate → report. Returns (report, delivery_log)."""
    raw = load_data(str(filepath))
    warehouses, agents, packages = normalize_data(raw)
    assignments = assign_packages(packages, warehouses, agents)
    log = simulate_deliveries(assignments, agents, warehouses, use_delays=use_delays)
    report = generate_report(log, agents)
    return report, log


# ══════════════════════════════════════════════════════════════════════
# 1. MATHS
# ══════════════════════════════════════════════════════════════════════

class TestEuclideanDistance(unittest.TestCase):

    def test_same_point_zero(self):
        self.assertAlmostEqual(euclidean_distance([0, 0], [0, 0]), 0.0)

    def test_345_triangle(self):
        self.assertAlmostEqual(euclidean_distance([0, 0], [3, 4]), 5.0)

    def test_negative_coords(self):
        self.assertAlmostEqual(euclidean_distance([-1, -1], [2, 3]), 5.0)

    def test_horizontal_line(self):
        self.assertAlmostEqual(euclidean_distance([0, 5], [10, 5]), 10.0)

    def test_symmetry(self):
        a, b = [7, 3], [1, 11]
        self.assertAlmostEqual(euclidean_distance(a, b), euclidean_distance(b, a))

    def test_float_coords(self):
        self.assertAlmostEqual(euclidean_distance([0.0, 0.0], [1.0, 1.0]),
                               math.sqrt(2), places=6)


# ══════════════════════════════════════════════════════════════════════
# 2. JSON NORMALISATION
# ══════════════════════════════════════════════════════════════════════

class TestNormalizeData(unittest.TestCase):

    DICT_FMT = {
        "warehouses": {"W1": [0, 0], "W2": [10, 10]},
        "agents":     {"A1": [5, 5]},
        "packages":   [{"id": "P1", "warehouse": "W1", "destination": [3, 4]}],
    }

    LIST_FMT = {
        "warehouses": [{"id": "W1", "location": [0, 0]}],
        "agents":     [{"id": "A1", "location": [5, 5]}],
        "packages":   [{"id": "P1", "warehouse_id": "W1", "destination": [3, 4]}],
    }

    def test_dict_format_warehouses(self):
        wh, _, _ = normalize_data(self.DICT_FMT)
        self.assertEqual(wh["W1"], [0, 0])

    def test_dict_format_agents(self):
        _, ag, _ = normalize_data(self.DICT_FMT)
        self.assertEqual(ag["A1"], [5, 5])

    def test_dict_format_package_warehouse_key(self):
        _, _, pkgs = normalize_data(self.DICT_FMT)
        self.assertEqual(pkgs[0]["warehouse"], "W1")

    def test_list_format_warehouses(self):
        wh, _, _ = normalize_data(self.LIST_FMT)
        self.assertEqual(wh["W1"], [0, 0])

    def test_list_format_package_warehouse_key(self):
        _, _, pkgs = normalize_data(self.LIST_FMT)
        self.assertEqual(pkgs[0]["warehouse"], "W1")

    def test_unknown_warehouse_raises(self):
        bad = {
            "warehouses": {"W1": [0, 0]},
            "agents":     {"A1": [1, 1]},
            "packages":   [{"id": "P1", "warehouse": "W99", "destination": [2, 2]}],
        }
        with self.assertRaises(ValueError):
            normalize_data(bad)

    def test_empty_input(self):
        wh, ag, pkgs = normalize_data({"warehouses": {}, "agents": {}, "packages": []})
        self.assertEqual(wh, {})
        self.assertEqual(ag, {})
        self.assertEqual(pkgs, [])


# ══════════════════════════════════════════════════════════════════════
# 3. PACKAGE ASSIGNMENT
# ══════════════════════════════════════════════════════════════════════

class TestAssignPackages(unittest.TestCase):

    WH = {"W1": [0, 0], "W2": [100, 100]}
    AG = {"A1": [1, 1], "A2": [99, 99]}

    def test_nearest_agent_wins(self):
        pkgs = [{"id": "P1", "warehouse": "W1", "destination": [5, 5]}]
        result = assign_packages(pkgs, self.WH, self.AG)
        self.assertIn("P1", [p["id"] for p in result["A1"]])
        self.assertEqual(result["A2"], [])

    def test_all_packages_assigned(self):
        pkgs = [
            {"id": "P1", "warehouse": "W1", "destination": [5, 5]},
            {"id": "P2", "warehouse": "W2", "destination": [95, 95]},
            {"id": "P3", "warehouse": "W1", "destination": [2, 2]},
        ]
        result = assign_packages(pkgs, self.WH, self.AG)
        total = sum(len(v) for v in result.values())
        self.assertEqual(total, 3)

    def test_no_packages_returns_empty_lists(self):
        result = assign_packages([], self.WH, self.AG)
        self.assertTrue(all(v == [] for v in result.values()))

    def test_single_agent_gets_all(self):
        ag = {"A1": [0, 0]}
        pkgs = [
            {"id": "P1", "warehouse": "W1", "destination": [5, 5]},
            {"id": "P2", "warehouse": "W2", "destination": [95, 95]},
        ]
        result = assign_packages(pkgs, self.WH, ag)
        self.assertEqual(len(result["A1"]), 2)

    def test_agent_count_in_result_matches_input(self):
        pkgs = [{"id": "P1", "warehouse": "W1", "destination": [5, 5]}]
        result = assign_packages(pkgs, self.WH, self.AG)
        self.assertEqual(set(result.keys()), set(self.AG.keys()))


# ══════════════════════════════════════════════════════════════════════
# 4. DELIVERY SIMULATION
# ══════════════════════════════════════════════════════════════════════

class TestSimulateDeliveries(unittest.TestCase):
    """Agent at (0,0), warehouse W1 at (3,4), destination at (6,8)."""

    AG = {"A1": [0, 0]}
    WH = {"W1": [3, 4]}
    PKGS = [{"id": "P1", "warehouse": "W1", "destination": [6, 8]}]

    def _run(self, delays=False):
        asgn = assign_packages(self.PKGS, self.WH, self.AG)
        return simulate_deliveries(asgn, self.AG, self.WH, use_delays=delays)

    def test_pickup_distance(self):
        # (0,0) → (3,4) = 5.0
        log = self._run()
        self.assertAlmostEqual(log["A1"]["packages"][0]["pickup_distance"], 5.0, places=2)

    def test_delivery_distance(self):
        # (3,4) → (6,8) = 5.0
        log = self._run()
        self.assertAlmostEqual(log["A1"]["packages"][0]["delivery_distance"], 5.0, places=2)

    def test_total_distance_is_sum(self):
        log = self._run()
        pkg = log["A1"]["packages"][0]
        self.assertAlmostEqual(
            log["A1"]["total_distance"],
            pkg["pickup_distance"] + pkg["delivery_distance"],
            places=4,
        )

    def test_no_delay_values_neutral(self):
        log = self._run(delays=False)
        pkg = log["A1"]["packages"][0]
        self.assertEqual(pkg["delay_event"], "none")
        self.assertEqual(pkg["delay_minutes"], 0)

    def test_delay_keys_present_when_enabled(self):
        log = self._run(delays=True)
        pkg = log["A1"]["packages"][0]
        self.assertIn("delay_event", pkg)
        self.assertIn("delay_minutes", pkg)
        self.assertGreaterEqual(pkg["delay_minutes"], 0)

    def test_empty_agent_has_zero_distance(self):
        asgn = {"A1": []}
        log = simulate_deliveries(asgn, self.AG, self.WH, use_delays=False)
        self.assertEqual(log["A1"]["total_distance"], 0.0)


# ══════════════════════════════════════════════════════════════════════
# 5. REPORT GENERATION
# ══════════════════════════════════════════════════════════════════════

class TestGenerateReport(unittest.TestCase):

    def _make_log(self, n_packages: int, total_dist: float) -> dict:
        pkgs = [
            {"id": f"P{i}", "warehouse": "W1", "warehouse_loc": [0, 0],
             "destination": [1, 1], "pickup_distance": 1.0,
             "delivery_distance": 1.0, "delay_event": "none", "delay_minutes": 0}
            for i in range(n_packages)
        ]
        return {"A1": {"start": [0, 0], "packages": pkgs, "total_distance": total_dist}}

    def test_efficiency_calculation(self):
        report = generate_report(self._make_log(4, 100.0), {"A1": [0, 0]})
        self.assertAlmostEqual(report["agents"]["A1"]["efficiency"], 25.0)

    def test_packages_delivered_count(self):
        report = generate_report(self._make_log(3, 90.0), {"A1": [0, 0]})
        self.assertEqual(report["agents"]["A1"]["packages_delivered"], 3)

    def test_best_agent_lower_efficiency_wins(self):
        log = {
            "A1": {"start": [0,0], "packages": [
                {"id":"P1","warehouse":"W1","warehouse_loc":[0,0],
                 "destination":[1,1],"pickup_distance":1,"delivery_distance":9,
                 "delay_event":"none","delay_minutes":0}
            ], "total_distance": 10.0},
            "A2": {"start": [0,0], "packages": [
                {"id":"P2","warehouse":"W1","warehouse_loc":[0,0],
                 "destination":[1,1],"pickup_distance":1,"delivery_distance":4,
                 "delay_event":"none","delay_minutes":0}
            ], "total_distance": 5.0},
        }
        report = generate_report(log, {"A1": [0,0], "A2": [0,0]})
        self.assertEqual(report["best_agent"], "A2")

    def test_no_deliveries_best_agent_is_none(self):
        log = {"A1": {"start": [0,0], "packages": [], "total_distance": 0.0}}
        report = generate_report(log, {"A1": [0,0]})
        self.assertIsNone(report["best_agent"])

    def test_report_has_required_keys(self):
        report = generate_report(self._make_log(1, 10.0), {"A1": [0, 0]})
        self.assertIn("agents", report)
        self.assertIn("best_agent", report)
        self.assertIn("packages_delivered", report["agents"]["A1"])
        self.assertIn("total_distance",     report["agents"]["A1"])
        self.assertIn("efficiency",         report["agents"]["A1"])


# ══════════════════════════════════════════════════════════════════════
# 6. FILE LOADING
# ══════════════════════════════════════════════════════════════════════

class TestLoadData(unittest.TestCase):

    def test_missing_file_raises_file_not_found(self):
        with self.assertRaises(FileNotFoundError):
            load_data("no_such_file_xyz_123.json")

    def test_valid_file_returns_dict(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as fh:
            json.dump({"warehouses": {}, "agents": {}, "packages": []}, fh)
            tmp = fh.name
        try:
            data = load_data(tmp)
            self.assertIsInstance(data, dict)
        finally:
            os.unlink(tmp)

    def test_invalid_json_raises_value_error(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as fh:
            fh.write("{not: valid json!!}")
            tmp = fh.name
        try:
            with self.assertRaises(ValueError):
                load_data(tmp)
        finally:
            os.unlink(tmp)


# ══════════════════════════════════════════════════════════════════════
# 7. BASE CASE (list format)
# ══════════════════════════════════════════════════════════════════════

class TestBaseCase(unittest.TestCase):
    """base_case.json uses the list-format schema."""

    FILE = HERE / "base_case.json"

    def setUp(self):
        if not self.FILE.exists():
            self.skipTest("base_case.json not found")
        self.report, self.log = run_pipeline(self.FILE)

    def test_report_keys_present(self):
        self.assertIn("agents", self.report)
        self.assertIn("best_agent", self.report)

    def test_all_5_packages_delivered(self):
        total = sum(s["packages_delivered"] for s in self.report["agents"].values())
        self.assertEqual(total, 5)

    def test_best_agent_is_valid_agent(self):
        self.assertIn(self.report["best_agent"], self.report["agents"])

    def test_total_distance_positive(self):
        for stats in self.report["agents"].values():
            if stats["packages_delivered"] > 0:
                self.assertGreater(stats["total_distance"], 0)

    def test_efficiency_matches_formula(self):
        for aid, stats in self.report["agents"].items():
            if stats["packages_delivered"] > 0:
                expected = round(stats["total_distance"] / stats["packages_delivered"], 2)
                self.assertAlmostEqual(stats["efficiency"], expected, places=1)


# ══════════════════════════════════════════════════════════════════════
# 8. ALL 10 TEST CASES — individual + batch
# ══════════════════════════════════════════════════════════════════════

def _make_test_case_class(tc_num: int):
    """Dynamically build a TestCase class for test_case_N.json."""

    filename = f"test_case_{tc_num}.json"
    filepath = HERE / filename

    class _TCTest(unittest.TestCase):

        FILE = filepath

        def setUp(self):
            if not self.FILE.exists():
                self.skipTest(f"{filename} not found")
            raw = load_data(str(self.FILE))
            self.warehouses, self.agents, self.packages = normalize_data(raw)
            self.assignments = assign_packages(self.packages, self.warehouses, self.agents)
            self.log = simulate_deliveries(
                self.assignments, self.agents, self.warehouses, use_delays=False
            )
            self.report = generate_report(self.log, self.agents)

        def test_all_packages_assigned(self):
            total = sum(len(v) for v in self.assignments.values())
            self.assertEqual(
                total, len(self.packages),
                f"{filename}: {len(self.packages)} packages expected, {total} assigned",
            )

        def test_report_has_required_keys(self):
            self.assertIn("agents", self.report)
            self.assertIn("best_agent", self.report)

        def test_all_agents_present_in_report(self):
            for aid in self.agents:
                self.assertIn(aid, self.report["agents"])

        def test_delivered_count_equals_package_count(self):
            total_delivered = sum(
                s["packages_delivered"] for s in self.report["agents"].values()
            )
            self.assertEqual(total_delivered, len(self.packages))

        def test_efficiency_non_negative(self):
            for aid, stats in self.report["agents"].items():
                self.assertGreaterEqual(stats["efficiency"], 0,
                    f"{filename} agent {aid}: negative efficiency")

        def test_total_distance_non_negative(self):
            for aid, stats in self.report["agents"].items():
                self.assertGreaterEqual(stats["total_distance"], 0)

        def test_best_agent_is_valid(self):
            ba = self.report["best_agent"]
            if ba is not None:
                self.assertIn(ba, self.report["agents"])

        def test_best_agent_has_lowest_efficiency(self):
            """The best_agent must have the minimum efficiency among active agents."""
            active = {
                aid: s for aid, s in self.report["agents"].items()
                if s["packages_delivered"] > 0
            }
            if not active:
                return
            min_eff = min(s["efficiency"] for s in active.values())
            best = self.report["best_agent"]
            self.assertAlmostEqual(
                self.report["agents"][best]["efficiency"], min_eff, places=1,
                msg=f"{filename}: best_agent {best} does not have lowest efficiency"
            )

        def test_efficiency_formula_correct(self):
            for aid, stats in self.report["agents"].items():
                if stats["packages_delivered"] > 0:
                    expected = round(stats["total_distance"] / stats["packages_delivered"], 2)
                    self.assertAlmostEqual(stats["efficiency"], expected, places=1,
                        msg=f"{filename} agent {aid}: efficiency formula mismatch")

    _TCTest.__name__ = f"TestCase{tc_num:02d}"
    _TCTest.__qualname__ = _TCTest.__name__
    return _TCTest


# Register TC classes in module namespace so unittest discovers them
for _n in range(1, 11):
    _cls = _make_test_case_class(_n)
    globals()[_cls.__name__] = _cls


# ══════════════════════════════════════════════════════════════════════
# 9. BATCH SUMMARY ACROSS ALL TEST CASES
# ══════════════════════════════════════════════════════════════════════

class TestBatchAllCases(unittest.TestCase):
    """High-level batch checks that iterate all 10 test cases at once."""

    TC_FILES = sorted(HERE.glob("test_case_*.json"))

    def test_found_all_10_test_case_files(self):
        self.assertEqual(len(self.TC_FILES), 10,
            f"Expected 10 test case files, found {len(self.TC_FILES)}")

    def test_no_package_left_unassigned_across_all(self):
        for fp in self.TC_FILES:
            with self.subTest(file=fp.name):
                raw = load_data(str(fp))
                wh, ag, pkgs = normalize_data(raw)
                asgn = assign_packages(pkgs, wh, ag)
                self.assertEqual(sum(len(v) for v in asgn.values()), len(pkgs))

    def test_report_valid_across_all(self):
        for fp in self.TC_FILES:
            with self.subTest(file=fp.name):
                report, _ = run_pipeline(fp)
                self.assertIn("agents", report)
                self.assertIn("best_agent", report)
                self.assertIsNotNone(report["best_agent"])

    def test_no_negative_distances_across_all(self):
        for fp in self.TC_FILES:
            with self.subTest(file=fp.name):
                report, log = run_pipeline(fp)
                for aid, entry in log.items():
                    self.assertGreaterEqual(entry["total_distance"], 0)


# ══════════════════════════════════════════════════════════════════════
# 10. CSV EXPORT
# ══════════════════════════════════════════════════════════════════════

class TestCsvExport(unittest.TestCase):

    def test_csv_created(self):
        report, _ = run_pipeline(HERE / "base_case.json")
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as fh:
            tmp = fh.name
        try:
            export_csv(report, filename=tmp)
            self.assertTrue(os.path.exists(tmp))
            content = Path(tmp).read_text()
            self.assertIn("agent_id", content)
            self.assertIn("efficiency", content)
        finally:
            os.unlink(tmp)


if __name__ == "__main__":
    unittest.main(verbosity=2)