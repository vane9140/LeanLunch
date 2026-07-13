#!/usr/bin/env bash
# 安装 / 更新 cron：每周日 08:15 Asia/Shanghai 跑 pi_weekly.sh
# （错开家庭晚餐 08:00，避免同时打 LLM/SMTP）
set -euo pipefail

REPO_DIR="${LEAN_LUNCH_REPO_DIR:-/home/vane914/Family/LeanLunch}"
ENV_FILE="${LEAN_LUNCH_ENV_FILE:-$HOME/.config/fengmai-topics/env}"
MARKER="# LeanLunch weekly"

mkdir -p "$(dirname "$HOME/.config/lean-lunch/env")" 2>/dev/null || true
chmod +x "$REPO_DIR/scripts/"*.sh "$REPO_DIR/scripts/"*.py 2>/dev/null || true

CRON_LINE="15 8 * * 0 TZ=Asia/Shanghai LEAN_LUNCH_REPO_DIR=$REPO_DIR LEAN_LUNCH_ENV_FILE=$ENV_FILE $REPO_DIR/scripts/pi_weekly.sh >> $REPO_DIR/logs/cron.log 2>&1"

EXISTING="$(crontab -l 2>/dev/null || true)"
FILTERED="$(printf '%s\n' "$EXISTING" | grep -vF "$MARKER" | grep -vF "LeanLunch/scripts/pi_weekly.sh" || true)"

{
  printf '%s\n' "$FILTERED"
  echo "$MARKER"
  echo "$CRON_LINE"
} | crontab -

echo "OK: cron installed"
echo "  $CRON_LINE"
echo ""
echo "当前 crontab:"
crontab -l
echo ""
echo "手动测试: $REPO_DIR/scripts/pi_weekly.sh"
