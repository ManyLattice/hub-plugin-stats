import os
import tempfile
import unittest

import main
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


class Owner(unittest.TestCase):
    def setUp(self):
        self.old = main.CONF
        main.CONF = os.path.join(tempfile.mkdtemp(), "settings.json")

    def tearDown(self):
        main.CONF = self.old

    def run_gh(self, out, code=0):
        return lambda *a, **k: type("R", (), {"returncode": code, "stdout": out})()

    def test_default_is_gh_account(self):
        self.assertEqual(main.owner(self.run_gh("someone\n")), "someone")

    def test_setting_wins(self):
        with open(main.CONF, "w") as f:
            f.write('{"owner": "other"}')
        self.assertEqual(main.owner(self.run_gh("someone")), "other")

    def test_no_gh_login_raises(self):
        with self.assertRaises(RuntimeError):
            main.owner(self.run_gh("", 1))


class Move(unittest.TestCase):
    def setUp(self):
        self.state = tempfile.mkdtemp()
        self.old = os.path.join(self.state, "stats")
        self.own = os.path.join(self.state, "stats-plugin")
        os.makedirs(self.old)

    def write(self, folder, name, text):
        os.makedirs(folder, exist_ok=True)
        with open(os.path.join(folder, name), "w") as f:
            f.write(text)

    def read(self, folder, name):
        with open(os.path.join(folder, name)) as f:
            return f.read()

    def test_own_files_move_and_core_files_stay(self):
        self.write(self.old, "clones.json", '{"r": {}}')
        self.write(self.old, "settings.json", '{"owner": "o"}')
        for n in ("state.json", "sent.jsonl", "ident.json"):
            self.write(self.old, n, n)
        self.assertEqual(sorted(main.move(self.state)), ["clones.json", "settings.json"])
        self.assertEqual(self.read(self.own, "clones.json"), '{"r": {}}')
        self.assertEqual(self.read(self.own, "settings.json"), '{"owner": "o"}')
        self.assertEqual(sorted(os.listdir(self.old)), ["ident.json", "sent.jsonl", "state.json"])
        self.assertEqual(sorted(os.listdir(self.own)), ["clones.json", "settings.json"])

    def test_only_history_moves_alone(self):
        self.write(self.old, "clones.json", "{}")
        self.assertEqual(main.move(self.state), ["clones.json"])
        self.assertFalse(os.path.exists(os.path.join(self.old, "clones.json")))

    def test_file_already_in_new_folder_is_not_overwritten(self):
        self.write(self.own, "clones.json", "new")
        self.write(self.old, "clones.json", "old")
        self.write(self.old, "settings.json", "old")
        self.assertEqual(main.move(self.state), ["settings.json"])
        self.assertEqual(self.read(self.own, "clones.json"), "new")
        self.assertEqual(os.listdir(self.old), ["clones.json"])

    def test_second_start_moves_nothing(self):
        self.write(self.old, "clones.json", "{}")
        main.move(self.state)
        self.assertEqual(main.move(self.state), [])
        self.assertEqual(self.read(self.own, "clones.json"), "{}")

    def test_nothing_to_move_creates_nothing(self):
        self.write(self.old, "state.json", "{}")
        self.assertEqual(main.move(self.state), [])
        self.assertFalse(os.path.exists(self.own))
        self.assertEqual(os.listdir(self.old), ["state.json"])

    def test_paths_live_in_own_folder(self):
        self.assertEqual(os.path.basename(os.path.dirname(main.FILE)), "stats-plugin")
        self.assertEqual(os.path.dirname(main.FILE), os.path.dirname(main.CONF))


if __name__ == "__main__":
    unittest.main()
