# 夫妻减脂午餐周方案

每周日早上 8:00（北京时间）自动生成下一周周一至周六的减脂午餐批量备餐方案，从 `vane914@126.com` 发到 `vane914@gmail.com`，并把菜单同步到 GitHub（`vane9140/LeanLunch`）。若 8:00 失败，8:25 看门狗会自动补跑一次。

与家庭晚餐方案互补：晚餐给全家；本项目专给夫妻二人午餐减脂备餐（一次做完、分装冷冻、微波复热）。

## 目录

- `config/`：夫妻规则与提示词（可改）
- `menus/`：已生成的周菜单文本
- `data/history.json`：菜名历史（避免连续两周高度重复）
- `scripts/`：生成、发信、cron

## 手动跑一次

```bash
/home/vane914/Family/LeanLunch/scripts/pi_weekly.sh
```

只生成不发信：

```bash
cd /home/vane914/Family/LeanLunch
set -a && source ~/.config/fengmai-topics/env && set +a
python3 scripts/run_weekly.py --no-email
```

## 安装周日定时

```bash
/home/vane914/Family/LeanLunch/scripts/setup_cron.sh
```

## 配置

默认复用 `~/.config/fengmai-topics/env` 里的 DeepSeek 与 SMTP。

若要单独配置，可新建 `~/.config/lean-lunch/env`（会优先生效），参考 `.env.example`。
