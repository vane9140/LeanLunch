#!/usr/bin/env bash
# 每周日任务：加载 env → 生成下周减脂午餐方案 → 发邮件 → 同步 git
set -euo pipefail

REPO_DIR="${LEAN_LUNCH_REPO_DIR:-/home/vane914/Family/LeanLunch}"
LOG_DIR="${LEAN_LUNCH_LOG_DIR:-$REPO_DIR/logs}"
# 默认复用选题日报的邮件/LLM 配置；也可单独用 lean-lunch/env
ENV_FILE="${LEAN_LUNCH_ENV_FILE:-$HOME/.config/fengmai-topics/env}"
ALT_ENV="$HOME/.config/lean-lunch/env"
BRANCH="${LEAN_LUNCH_BRANCH:-main}"
# 固定本仓库，避免复用 fengmai-topics/env 里的 GITHUB_REPO
LEAN_LUNCH_GITHUB_REPO="${LEAN_LUNCH_GITHUB_REPO:-vane9140/LeanLunch}"

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
# source 之后再锁定仓库名，防止被共用 env 覆盖
GITHUB_REPO="$LEAN_LUNCH_GITHUB_REPO"

cd "$REPO_DIR"

pi_git_push() {
  echo "[git] commit + push menus/history..."
  git add menus/*.txt data/history.json config/ README.md scripts/ 2>/dev/null || true
  if git diff --cached --quiet; then
    echo "  nothing to commit"
    return 0
  fi
  local day
  day="$(TZ=Asia/Shanghai date +%Y-%m-%d)"
  git -c user.name="${GIT_AUTHOR_NAME:-lean-lunch-pi}" \
      -c user.email="${GIT_AUTHOR_EMAIL:-lean-lunch-pi@local}" \
      commit -m "weekly lean lunch $day [pi]"
  if [[ -n "${GITHUB_TOKEN:-}" ]]; then
    if ! git remote get-url origin >/dev/null 2>&1; then
      git remote add origin "https://github.com/${GITHUB_REPO}.git"
    fi
    git push "https://x-access-token:${GITHUB_TOKEN}@github.com/${GITHUB_REPO}.git" "HEAD:${BRANCH}" \
      || echo "  WARN: git push failed (create GitHub repo ${GITHUB_REPO} or check token)"
  else
    echo "  SKIP push: GITHUB_TOKEN not set"
    git push origin "HEAD:${BRANCH}" 2>/dev/null \
      || echo "  WARN: push skipped/failed (configure remote/token)"
  fi
}

echo "[1/2] python3 scripts/run_weekly.py"
python3 scripts/run_weekly.py
echo "[2/2] sync git"
pi_git_push
echo "=== done ==="
