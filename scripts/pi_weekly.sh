#!/usr/bin/env bash
# 每周日任务：加载 env → 生成下周减脂午餐方案 → 发邮件
set -euo pipefail

REPO_DIR="${LEAN_LUNCH_REPO_DIR:-/home/vane914/Family/LeanLunch}"
LOG_DIR="${LEAN_LUNCH_LOG_DIR:-$REPO_DIR/logs}"
# 默认复用选题日报的邮件/LLM 配置；也可单独用 lean-lunch/env
ENV_FILE="${LEAN_LUNCH_ENV_FILE:-$HOME/.config/fengmai-topics/env}"
ALT_ENV="$HOME/.config/lean-lunch/env"

mkdir -p "$LOG_DIR"
TS="$(TZ=Asia/Shanghai date +%Y-%m-%d-%H%M)"
LOG="$LOG_DIR/pi-weekly-$TS.log"
exec > >(tee -a "$LOG") 2>&1

echo "=== LeanLunch weekly $TS ==="

if [[ -f "$ALT_ENV" ]]; then
  ENV_FILE="$ALT_ENV"
fi

if [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
  echo "loaded env: $ENV_FILE"
else
  echo "WARN: env file not found: $ENV_FILE"
fi

export LLM_API_KEY="${LLM_API_KEY:-${DEEPSEEK_API_KEY:-${OPENAI_API_KEY:-}}}"
export LLM_BASE_URL="${LLM_BASE_URL:-https://api.deepseek.com/v1}"
export LLM_MODEL="${LLM_MODEL:-deepseek-chat}"

cd "$REPO_DIR"
echo "[run] python3 scripts/run_weekly.py"
python3 scripts/run_weekly.py
echo "=== done ==="
