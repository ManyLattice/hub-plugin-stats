"""Сбор и хранение клонов репозиториев hub-plugin-* владельца по GitHub Traffic. Чистая логика: gh и часы подставляются."""
import json
import os
import subprocess
import tempfile

PREFIX = "hub-plugin-"


def gh(*args):
    r = subprocess.run(["gh", "api", *args], capture_output=True, text=True, timeout=60)
    if r.returncode:
        raise RuntimeError((r.stderr or r.stdout).strip()[:300])
    return json.loads(r.stdout)


def discover(owner, run=subprocess.run):
    r = run(["gh", "repo", "list", owner, "--limit", "200", "--json", "name,isPrivate"], capture_output=True, text=True,
            timeout=60)
    if r.returncode:
        raise RuntimeError((r.stderr or r.stdout).strip()[:300])
    return sorted(x["name"] for x in json.loads(r.stdout) if x["name"].startswith(PREFIX) and not x["isPrivate"])


def merge(history, repo, clones):
    """История {репо: {день: [count, uniques]}}. День из ответа GitHub заменяет сохранённый: сегодняшний растёт,
    прошлые окончательны. Возвращает число новых дней."""
    days = history.setdefault(repo, {})
    new = 0
    for c in clones:
        day = c["timestamp"][:10]
        new += day not in days
        days[day] = [c["count"], c["uniques"]]
    return new


def load(path):
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def save(path, history):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path))
    with os.fdopen(fd, "w") as f:
        json.dump(history, f, ensure_ascii=False, indent=1, sort_keys=True)
    os.replace(tmp, path)


def collect(owner, path, call=gh, find=discover):
    """Один сбор: все репо плагинов, их clones за последние 14 дней — в файл истории. Репо без доступа пропускает."""
    history = load(path)
    errors = {}
    for repo in find(owner):
        try:
            data = call(f"repos/{owner}/{repo}/traffic/clones")
        except RuntimeError as e:
            errors[repo] = str(e)
            continue
        merge(history, repo, data.get("clones", []))
    save(path, history)
    return history, errors


def summary(history, today, windows=(7, 30)):
    """Строки сводки по репо: всего и по окнам (клонов, уникальных за день — сумма уникальных по дням, не уникальные
    люди), первый день истории. today — 'YYYY-MM-DD'."""
    from datetime import date, timedelta
    t = date.fromisoformat(today)
    rows = []
    for repo, days in sorted(history.items()):
        row = {"repo": repo, "since": min(days) if days else None,
               "total": [sum(v[0] for v in days.values()), sum(v[1] for v in days.values())]}
        for w in windows:
            lo = (t - timedelta(days=w - 1)).isoformat()
            sel = [v for d, v in days.items() if d >= lo]
            row[f"d{w}"] = [sum(v[0] for v in sel), sum(v[1] for v in sel)]
        rows.append(row)
    return rows


def render(rows):
    out = [f"{'репо':28} {'с':10} {'7д':>9} {'30д':>9} {'всего':>9}   (клонов/уникальных за день)"]
    for r in rows:
        f = lambda v: f"{v[0]}/{v[1]}"
        out.append(f"{r['repo']:28} {r['since'] or '-':10} {f(r['d7']):>9} {f(r['d30']):>9} {f(r['total']):>9}")
    out.append("В счёт входят ваши установки, ревью-клоны и обновления плагина, не только чужие.")
    return "\n".join(out)
