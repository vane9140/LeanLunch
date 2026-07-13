#!/usr/bin/env python3
"""通过 SMTP 发送减脂午餐备餐方案邮件（标准库，无第三方依赖）。"""

from __future__ import annotations

import os
import smtplib
import ssl
from email.message import EmailMessage
from pathlib import Path


def _req(name: str) -> str:
    val = os.environ.get(name, "").strip()
    if not val:
        raise RuntimeError(f"缺少邮件配置: {name}")
    return val


def smtp_configured() -> bool:
    return bool(os.environ.get("SMTP_HOST") and os.environ.get("EMAIL_TO"))


def _recipients() -> list[str]:
    raw = _req("EMAIL_TO")
    return [x.strip() for x in raw.replace(";", ",").split(",") if x.strip()]


def send_email(
    subject: str,
    body_text: str,
    body_html: str | None = None,
    attachment: Path | None = None,
) -> None:
    host = _req("SMTP_HOST")
    port = int(os.environ.get("SMTP_PORT", "465"))
    user = os.environ.get("SMTP_USER", "").strip()
    password = os.environ.get("SMTP_PASSWORD", "").strip()
    from_addr = os.environ.get("SMTP_FROM", "").strip() or user
    if not from_addr:
        raise RuntimeError("缺少 SMTP_FROM 或 SMTP_USER")

    to_list = _recipients()

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = ", ".join(to_list)
    msg.set_content(body_text)
    if body_html:
        msg.add_alternative(body_html, subtype="html")

    if attachment and attachment.exists():
        data = attachment.read_bytes()
        msg.add_attachment(
            data,
            maintype="text",
            subtype="plain",
            filename=attachment.name,
        )

    context = ssl.create_default_context()
    use_ssl = os.environ.get("SMTP_SSL", "1").strip() not in ("0", "false", "False")
    use_starttls = os.environ.get("SMTP_STARTTLS", "0").strip() in ("1", "true", "True")

    if use_ssl and not use_starttls:
        with smtplib.SMTP_SSL(host, port, timeout=45, context=context) as smtp:
            if user and password:
                smtp.login(user, password)
            smtp.send_message(msg)
    else:
        with smtplib.SMTP(host, port, timeout=45) as smtp:
            smtp.ehlo()
            if use_starttls:
                smtp.starttls(context=context)
                smtp.ehlo()
            if user and password:
                smtp.login(user, password)
            smtp.send_message(msg)


def text_to_simple_html(text: str) -> str:
    import html as html_mod

    paras = []
    for block in text.split("\n"):
        if not block.strip():
            paras.append("<br>")
        else:
            paras.append(
                f"<p style='margin:0 0 10px'>{html_mod.escape(block)}</p>"
            )
    body = "\n".join(paras)
    return (
        "<!DOCTYPE html><html><head><meta charset='utf-8'></head>"
        f"<body style='font-family:-apple-system,BlinkMacSystemFont,Segoe UI,"
        f"PingFang SC,Microsoft YaHei,sans-serif;line-height:1.65;color:#222;"
        f"max-width:720px;margin:24px auto;padding:0 16px'>{body}</body></html>"
    )


def push_menu_file(path: Path, week_label: str) -> None:
    text = path.read_text(encoding="utf-8").strip()
    subject = os.environ.get(
        "EMAIL_SUBJECT",
        f"减脂午餐备餐方案 · {week_label}",
    ).replace("{week}", week_label)
    send_email(
        subject=subject,
        body_text=text,
        body_html=text_to_simple_html(text),
        attachment=path,
    )


def push_text(content: str, subject: str = "减脂午餐方案通知") -> None:
    send_email(subject=subject, body_text=content)


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser(description="SMTP 发送减脂午餐备餐方案")
    ap.add_argument("file", nargs="?", help="菜单文本文件")
    ap.add_argument("--text", help="直接发送纯文本")
    ap.add_argument("--subject", default="减脂午餐方案测试")
    ap.add_argument("--week", default="")
    args = ap.parse_args()

    if args.text:
        push_text(args.text, subject=args.subject)
        print("sent text email")
        return 0
    if not args.file:
        raise SystemExit("请提供 file 或 --text")
    push_menu_file(Path(args.file), args.week or Path(args.file).stem)
    print(f"sent {args.file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
