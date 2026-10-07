import os
import tempfile
import unittest

import stats

C = lambda day, n, u: {"timestamp": f"{day}T00:00:00Z", "count": n, "uniques": u}


class Stats(unittest.TestCase):
    def test_merge_dedups_by_day_and_updates_today(self):
        h = {}
        self.assertEqual(stats.merge(h, "r", [C("2026-10-06", 3, 2), C("2026-10-07", 1, 1)]), 2)
        self.assertEqual(stats.merge(h, "r", [C("2026-10-06", 3, 2), C("2026-10-07", 4, 2), C("2026-10-08", 0, 0)]), 1)
        self.assertEqual(h["r"], {"2026-10-06": [3, 2], "2026-10-07": [4, 2], "2026-10-08": [0, 0]})

    def test_history_outlives_github_window(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "s", "c.json")
            find = lambda o: ["hub-plugin-a"]
            stats.collect("o", p, call=lambda *a: {"clones": [C("2026-09-01", 5, 3)]}, find=find)
            h, _ = stats.collect("o", p, call=lambda *a: {"clones": [C("2026-10-07", 1, 1)]}, find=find)
            self.assertEqual(sorted(h["hub-plugin-a"]), ["2026-09-01", "2026-10-07"])

    def test_error_in_one_repo_does_not_stop_others(self):
        def call(path):
            if "bad" in path:
                raise RuntimeError("403")
            return {"clones": [C("2026-10-07", 2, 1)]}
        with tempfile.TemporaryDirectory() as d:
            h, errors = stats.collect("o", os.path.join(d, "c.json"), call=call, find=lambda o: ["hub-plugin-bad", "hub-plugin-ok"])
            self.assertIn("hub-plugin-ok", h)
            self.assertEqual(list(errors), ["hub-plugin-bad"])

    def test_summary_windows(self):
        h = {"r": {"2026-10-07": [2, 1], "2026-10-01": [5, 2], "2026-08-01": [10, 4]}}
        r = stats.summary(h, "2026-10-07")[0]
        self.assertEqual((r["d7"], r["d30"], r["total"], r["since"]), ([7, 3], [7, 3], [17, 7], "2026-08-01"))

    def test_discover_only_public_plugins(self):
        import json
        class R:
            returncode = 0
            stdout = json.dumps([{"name": "hub-plugin-x", "isPrivate": False}, {"name": "hub-plugin-p", "isPrivate": True},
                                 {"name": "other", "isPrivate": False}])
        self.assertEqual(stats.discover("o", run=lambda *a, **k: R), ["hub-plugin-x"])


if __name__ == "__main__":
    unittest.main()
