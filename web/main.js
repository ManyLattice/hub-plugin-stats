// Вкладка «Статистика»: клоны плагинов владельца по GitHub Traffic. Данные собирает процесс плагина (main.py) и пишет
// последним постом в канал; страница показывает его.
const CHANNEL = "stats";
const NOTE = "В счёт входят и ваши установки, и ревью-клоны, и обновления плагина: это верхняя граница чужих установок.";

export default function register(hub) {
  const el = (...a) => hub.el(...a);
  let loaded = 0;
  let box = null;

  const paint = (d) => {
    box.replaceChildren(el("p", "jev-state", NOTE));
    if (!d.rows.length) { box.append(el("p", null, "Истории пока нет: первый сбор — при запуске процесса.")); return; }
    const t = el("table", "stats-table");
    const head = el("tr");
    for (const h of ["Плагин", "История с", "7 дней", "30 дней", "Всего"]) head.append(el("th", null, h));
    t.append(head);
    const f = (v) => `${v[0]} / ${v[1]}`;
    for (const r of d.rows) {
      const tr = el("tr");
      for (const c of [r.repo, r.since || "-", f(r.d7), f(r.d30), f(r.total)]) tr.append(el("td", null, c));
      t.append(tr);
    }
    box.append(t, el("p", "jev-state", "Клонов / уникальных за день (сумма по дням, не уникальные люди). Обновлено " + d.at));
    for (const [repo, e] of Object.entries(d.errors || {})) box.append(el("p", "jev-state", `${repo}: ${e}`));
  };

  const tick = async (snap) => {
    const top = (snap.feeds || {})[CHANNEL] || 0;
    if (top <= loaded && box.childElementCount) return;
    loaded = top;
    const posts = await hub.feed(0);
    for (const p of posts.reverse()) {
      if (!String(p.by).startsWith("плагин ")) continue;
      try { paint(JSON.parse(p.text)); return; } catch {}
    }
    box.replaceChildren(el("p", null, "Данных пока нет: процесс плагина ещё не собирал статистику."));
  };

  hub.addStyle("web/stats.css");
  hub.addView({
    id: "stats", title: "Статистика", subtitle: "клоны плагинов", icon: "board",
    render(root, snap) {
      if (!box) { box = el("div", "stats"); root.replaceChildren(box); }
      tick(snap);
    },
  });
}
