#!/usr/bin/env python3
"""每周串联：生成减脂午餐方案 → 邮件推送。"""

from __future__ import annotations

import json
import sys
import traceback
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

BEIJING = timezone(timedelta(hours=8))
ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = Path(__file__).resolve().parent

sys.path.insert(0, str(SCRIPTS))

from email_push import push_menu_file as email_menu  # noqa: E402
from email_push import push_text as email_text  # noqa: E402
from email_push import smtp_configured  # noqa: E402
from generate_menu import generate, resolve_week_monday  # noqa: E402


def notify_error(msg: str) -> None:
    print(msg, file=sys.stderr)
    body = f"[减脂午餐方案失败]\n{msg[:1500]}"
    if smtp_configured():
        try:
            email_text(body, subject="减脂午餐方案失败")
        except Exception as e:  # noqa: BLE001
            print(f"email error notify failed: {e}", file=sys.stderr)


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser(description="生成并发送本周减脂午餐备餐方案")
    ap.add_argument("--monday", help="指定周一 YYYY-MM-DD")
    ap.add_argument("--no-email", action="store_true", help="只生成不发信")
    args = ap.parse_args()

    now = datetime.now(BEIJING)
    monday = date.fromisoformat(args.monday) if args.monday else resolve_week_monday()
    saturday = monday + timedelta(days=5)
    week_label = f"{monday.isoformat()}～{saturday.isoformat()}"

    log_dir = ROOT / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    status_path = log_dir / "last-run-status.json"

    def write_status(status: str, detail: str = "", menu: str = "") -> None:
        status_path.write_text(
            json.dumps(
                {
                    "week_start": monday.isoformat(),
                    "status": status,
                    "detail": detail,
                    "menu": menu,
                    "ts": now.isoformat(timespec="seconds"),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    print(f"=== LeanLunch weekly {week_label} ===")
    try:
        print("[1/2] generate menu...")
        menu = generate(monday)
        print(f"  menu: {menu}")

        print("[2/2] deliver...")
        if args.no_email:
            print("  SKIP email (--no-email)")
            write_status("ok", detail="no-email", menu=str(menu.relative_to(ROOT)))
        elif smtp_configured():
            email_menu(menu, week_label)
            print("  pushed via: email")
            write_status("ok", detail="email", menu=str(menu.relative_to(ROOT)))
        else:
            print("  SKIP: 未配置 SMTP（EMAIL_TO+SMTP_HOST）")
            write_status("ok", detail="no-smtp", menu=str(menu.relative_to(ROOT)))

        print("=== done ===")
        return 0
    except Exception as e:  # noqa: BLE001
        tb = traceback.format_exc()
        (log_dir / f"error-{monday.isoformat()}.log").write_text(tb, encoding="utf-8")
        write_status("failed", detail=str(e))
        notify_error(f"{e}\n\n详见 logs/error-{monday.isoformat()}.log")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
