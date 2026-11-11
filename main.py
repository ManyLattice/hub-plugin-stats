"""Процесс плагина «Статистика»: раз в день (и при старте) собирает клоны репозиториев hub-plugin-* владельца GitHub,
копит историю в файле вне репо хаба и пишет сводку в канал плагина — страница показывает последний пост.
CLI: `python3 main.py report` — сводка из накопленной истории без сети."""
import datetime
import json
import os
import subprocess
import sys
import time

import stats

STATE = os.environ.get("HUB_STATE_DIR", os.path.expanduser("~/.hub-core"))
NAME = os.environ.get("HUB_EXTENSION", "stats")
CHANNEL = NAME.split(":")[-1]
FILE = os.path.join(STATE, "stats", "clones.json")
CONF = os.path.join(STATE, "stats", "settings.json")   # {"owner": "<аккаунт GitHub>"}
EVERY = 24 * 3600
RETRY = 3600


def owner(run=subprocess.run):
    try:
        with open(CONF) as f:
            name = json.load(f).get("owner")
    except (OSError, ValueError):
        name = None
    if name:
        return name
    r = run(["gh", "api", "user", "--jq", ".login"], capture_output=True, text=True, timeout=30)
    if r.returncode or not r.stdout.strip():
        raise RuntimeError("не удалось определить аккаунт GitHub: выполните `gh auth login` или задайте owner в " + CONF)
    return r.stdout.strip()


def today():
    return datetime.datetime.now(datetime.timezone.utc).date().isoformat()


def payload(history, errors):
    return {"rows": stats.summary(history, today()), "errors": errors, "at": today()}


def run_once(put):
    history, errors = stats.collect(owner(), FILE)
    put(payload(history, errors))
    return not errors


def main():
    from core import spool
    put = lambda data: spool.put(os.path.join(STATE, "spool"), "ext.post", None,
                                 {"plugin": CHANNEL, "text": json.dumps(data, ensure_ascii=False), "channel": "plugin",
                                  "owner": False, "sender": NAME}, src=f"ext:{NAME}")
    while True:
        try:
            ok = run_once(put)
        except Exception as e:   # нет сети, gh не вошёл: повторим позже
            print("stats:", e, flush=True)
            ok = False
        time.sleep(EVERY if ok else RETRY)


if __name__ == "__main__":
    if sys.argv[1:] == ["report"]:
        print(stats.render(stats.summary(stats.load(FILE), today())))
    else:
        main()
