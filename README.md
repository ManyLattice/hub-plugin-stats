# hub-plugin-stats

Плагин для [Agents Hub](https://github.com/flagman/agents-hub-core): статистика клонов репозиториев `hub-plugin-*` по GitHub Traffic.

![Статистика](icon.png)

- раз в сутки (и при старте) процесс собирает `traffic/clones` через `gh api` для всех публичных репо владельца с префиксом `hub-plugin-`;
- история копится в `~/.hub-core/stats/clones.json` дольше 14 дней GitHub, дубли по дню не плодятся;
- вкладка «Статистика» на странице хаба; в терминале - `python3 main.py report`;
- владелец по умолчанию - аккаунт, под которым вы вошли в `gh`; меняется в `~/.hub-core/stats/settings.json` (`{"owner": "..."}`).

В счёт клонов входят и ваши установки, ревью-клоны и обновления плагина: цифры - верхняя граница чужих установок. «Уникальных» - за день, их сумма по дням не равна числу людей. Нужен вход `gh auth login` с правом push к репо.

Тесты: `PYTHONPATH=. python3 -m unittest discover -s tests`
