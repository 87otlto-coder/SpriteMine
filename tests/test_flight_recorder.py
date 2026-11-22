"""Synthetic session format tests; no ROM, Mesen or copyrighted capture required."""
import importlib.util
import json
from pathlib import Path
import tempfile
import sys
import unittest

SPEC = importlib.util.spec_from_file_location(
    "flight_recorder", Path(__file__).parents[1] / "research/mesence/flight_recorder.py")
recorder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(recorder)


class RecorderTests(unittest.TestCase):
    def session(self, folder, records):
        path = Path(folder) / "capture.jsonl"
        path.write_text("".join(json.dumps(r) + "\n" for r in records), encoding="utf-8")
        return path

    def rows(self):
        return [{"type": "header", "schema": 1, "regions": {"ram": {"size": 257}}},
                {"type": "sample", "seq": 1, "full": True, "time": {"frame": 1, "tick": 1},
                 "changed_bytes": {"ram": 257}, "memory": {"ram": {"0": "00" * 256, "256": "01"}}},
                {"type": "sample", "seq": 2, "full": False, "time": {"frame": 31, "tick": 31},
                 "changed_bytes": {"ram": 1}, "memory": {"ram": {"256": "ff"}}},
                {"type": "end", "reason": "frame_limit"}]

    def test_find_writes_filters_events_and_reports_truncation(self):
        rows = self.rows()
        event = {"kind": "write", "address": 896, "value": 32, "frame": 17, "cpu_cycle": 9}
        rows.insert(-1, {"type": "burst", "time": {"frame": 18},
                         "event_totals": {"write": 4}, "events": {
                             "write2": {**event, "cpu_cycle": 10},
                             "write1": event,
                             "write3": {**event, "value": 7},
                         }})
        with tempfile.TemporaryDirectory() as tmp:
            path = self.session(tmp, rows)
            result = recorder.find_writes(path, address=896, value=32, first=17, last=17)
            self.assertEqual([9, 10], [e["cpu_cycle"] for e in result["matches"]])
            self.assertEqual(1, result["omitted_writes_in_candidate_bursts"])
            self.assertTrue(result["footer"])
            self.assertEqual([], recorder.find_writes(path, address=896, first=18)["matches"])

    def test_delta_reconstruction_and_verified_compression(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self.session(tmp, self.rows())
            before = list(recorder.snapshots(path))
            packed = recorder.package(Path(tmp))
            self.assertFalse(path.exists())
            self.assertEqual(before, list(recorder.snapshots(packed)))
            self.assertEqual(before[0][1]["ram"][-1], 1)
            self.assertEqual(before[1][1]["ram"][-1], 255)
            self.assertEqual(recorder.summarize(packed)["samples"], 2)

    def test_missing_baseline_rejected(self):
        rows = self.rows()
        rows[1]["full"] = False
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "baseline"):
                list(recorder.snapshots(self.session(tmp, rows)))

    def test_missing_checkpoint_page_and_invalid_delta_rejected(self):
        for corrupt in ("missing", "offset", "length", "sequence"):
            rows = self.rows()
            if corrupt == "missing": del rows[1]["memory"]["ram"]["256"]
            if corrupt == "offset": rows[2]["memory"]["ram"] = {"257": "ff"}
            if corrupt == "length": rows[2]["memory"]["ram"] = {"256": "ffff"}
            if corrupt == "sequence": rows[2]["seq"] = 9
            with self.subTest(corrupt=corrupt), tempfile.TemporaryDirectory() as tmp:
                with self.assertRaises(ValueError):
                    list(recorder.snapshots(self.session(tmp, rows)))

    def test_incomplete_session_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = recorder.summarize(self.session(tmp, self.rows()[:-1]))
            self.assertIsNone(report["footer"])
            self.assertEqual(report["samples"], 2)

    def test_checkpoint_replaces_memory(self):
        rows = self.rows()
        full = dict(rows[1], seq=3)
        rows.insert(3, full)
        with tempfile.TemporaryDirectory() as tmp:
            captured = list(recorder.snapshots(self.session(tmp, rows)))
            self.assertEqual(captured[-1][1]["ram"][-1], 1)

    def test_configuration_bounds(self):
        for value in ("0", "-1", "3601"):
            with self.assertRaises(Exception): recorder.bounded(1, 3600)(value)

    def test_child_log_is_capped_without_blocking(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "emulator.log"
            code = recorder.run_logged([sys.executable, "-c", "print('x' * 2097152)"],
                                       cwd=tmp, env=None, log_path=log, timeout=10, headless=True)
            self.assertEqual(code, 0)
            self.assertEqual(log.stat().st_size, 1048576)


if __name__ == "__main__":
    unittest.main()
