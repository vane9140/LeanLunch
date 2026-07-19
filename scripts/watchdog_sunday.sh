#!/usr/bin/env bash
# 周日 08:00 主任务失败时，08:25 自动补跑一次
set -euo pipefail

REPO_DIR="${LEAN_LUNCH_REPO_DIR:-/home/vane914/Family/LeanLunch}"
LOG_DIR="${LEAN_LUNCH_LOG_DIR:-$REPO_DIR/logs}"
STATUS_FILE="$LOG_DIR/last-run-status.json"
ENV_FILE="${LEAN_LUNCH_ENV_FILE:-$HOME/.config/fengmai-topics/env}"
ALT_ENV="$HOME/.config/lean-lunch/env"

mkdir -p "$LOG_DIR"
TS="$(TZ=Asia/Shanghai date +%Y-%m-%d-%H%M)"
LOG="$LOG_DIR/watchdog-$TS.log"
exec > >(tee -a "$LOG") 2>&1

echo "=== LeanLunch watchdog $TS ==="

if [[ -f "$ALT_ENV" ]]; then
  ENV_FILE="$ALT_ENV"
fi
if [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
fi

# 周日生成的是「下一周」周一；与 resolve_week_monday 一致
expected_monday="$(
  python3 - <<'PY'
from datetime import date, timedelta, datetime, timezone
BEIJING = timezone(timedelta(hours=8))
today = datetime.now(BEIJING).date()
if today.weekday() == 6:
    monday = today + timedelta(days=1)
else:
    monday = today - timedelta(days=today.weekday())
print(monday.isoformat())
PY
)"

need_rerun=1
if [[ -f "$STATUS_FILE" ]]; then
  status="$(python3 -c "import json;print(json.load(open('$STATUS_FILE',encoding='utf-8')).get('status',''))")"
  week="$(python3 -c "import json;print(json.load(open('$STATUS_FILE',encoding='utf-8')).get('week_start',''))")"
  menu="$(python3 -c "import json;print(json.load(open('$STATUS_FILE',encoding='utf-8')).get('menu',''))")"
  echo "status=$status week_start=$week expected=$expected_monday menu=$menu"
  if [[ "$status" == "ok" && "$week" == "$expected_monday" && -n "$menu" && -f "$REPO_DIR/$menu" ]]; then
    need_rerun=0
  fi
else
  echo "no status file"
fi

if [[ "$need_rerun" -eq 0 ]]; then
  echo "OK: Sunday run already succeeded, skip"
  exit 0
fi

echo "WARN: Sunday run missing/failed → rerun pi_weekly.sh"
"$REPO_DIR/scripts/pi_weekly.sh"
echo "=== watchdog done ==="
