#!/usr/bin/env python3
"""生成周一至周六夫妻减脂午餐批量备餐方案，并更新历史记录。"""

from __future__ import annotations

import json
import os
import re
import ssl
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

BEIJING = timezone(timedelta(hours=8))
ROOT = Path(__file__).resolve().parents[1]
HISTORY_PATH = ROOT / "data" / "history.json"
WEEKDAYS_CN = ("周一", "周二", "周三", "周四", "周五", "周六")


def llm_config() -> tuple[str, str, str]:
    key = (
        os.environ.get("LLM_API_KEY")
        or os.environ.get("DEEPSEEK_API_KEY")
        or os.environ.get("OPENAI_API_KEY")
        or ""
    )
    base = os.environ.get("LLM_BASE_URL", "https://api.deepseek.com/v1").rstrip("/")
    model = os.environ.get("LLM_MODEL", "deepseek-chat")
    return key, base, model


def chat_completion(system: str, user: str) -> str:
    key, base, model = llm_config()
    if not key:
        raise RuntimeError("缺少 LLM_API_KEY / DEEPSEEK_API_KEY / OPENAI_API_KEY")

    payload = {
        "model": model,
        "temperature": 0.85,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        f"{base}/chat/completions",
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {key}",
            "User-Agent": "LeanLunch/1.0",
        },
    )
    ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(req, timeout=180, context=ctx) as resp:
            raw = resp.read()
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")[:800]
        raise RuntimeError(f"LLM HTTP {e.code}: {detail}") from e

    data = json.loads(raw.decode("utf-8"))
    try:
        return str(data["choices"][0]["message"]["content"]).strip()
    except (KeyError, IndexError, TypeError) as e:
        raise RuntimeError(f"LLM 响应格式异常: {repr(data)[:500]}") from e


def read_text(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8").strip()


def strip_fence(text: str) -> str:
    text = text.strip()
    m = re.match(r"^```(?:markdown|md|text)?\s*([\s\S]*?)\s*```$", text)
    if m:
        return m.group(1).strip()
    return text


def load_history() -> dict:
    if not HISTORY_PATH.exists():
        return {"weeks": []}
    return json.loads(HISTORY_PATH.read_text(encoding="utf-8"))


def save_history(data: dict) -> None:
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    HISTORY_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def monday_of(d: date) -> date:
    return d - timedelta(days=d.weekday())


def resolve_week_monday(today: date | None = None) -> date:
    """周日生成下一周；其余日子生成本周。"""
    today = today or datetime.now(BEIJING).date()
    if today.weekday() == 6:  # Sunday
        return today + timedelta(days=1)
    return monday_of(today)


def week_dates(monday: date) -> dict[str, str]:
    return {
        "monday": monday.isoformat(),
        "tuesday": (monday + timedelta(days=1)).isoformat(),
        "wednesday": (monday + timedelta(days=2)).isoformat(),
        "thursday": (monday + timedelta(days=3)).isoformat(),
        "friday": (monday + timedelta(days=4)).isoformat(),
        "saturday": (monday + timedelta(days=5)).isoformat(),
    }


def history_constraints(history: dict) -> str:
    weeks = history.get("weeks") or []
    recent = weeks[-4:]
    if not recent:
        return (
            "- 尚无历史记录。\n"
            "- 本周主食 1–2 种；除主食外必须 5–6 道菜。\n"
            "- 优先：糙米/杂粮/薯类主食 + 鸡胸/鳕鱼或三文鱼（煎烤）/虾/里脊/瘦牛 + 大量绿叶/十字花科蔬菜。"
        )

    lines = ["最近几周记录（越靠后越近）："]
    for w in recent:
        lines.append(
            f"- {w.get('week_start')}: 菜品数={w.get('dish_count')}；"
            f"主食={w.get('staples', '')}；纯蛋白={w.get('proteins', '')}；"
            f"荤素={w.get('mixed', '')}；菜名={w.get('dishes', '')}"
        )

    lines.append("")
    lines.append("- 本周菜名请与最近两周明显错开，避免同菜名重复。")
    lines.append("- 主食与蛋白种类也尽量轮换（例如上周鸡胸则本周可鱼/虾/牛肉）。")
    lines.append("- 除主食外菜品必须 5–6 道；鱼只用鳕鱼或三文鱼且煎/烤。")
    lines.append("- 除鱼以外一律炒/炖/卤，禁止香煎鸡胸等「煎」法。")
    lines.append("- 严禁辣椒/麻辣；虾皮不用，虾肉可用。")
    return "\n".join(lines)


def parse_record_line(content: str) -> dict:
    """从【记录】行提取摘要；失败则尽量兜底。"""
    m = re.search(r"【记录】(.+)$", content, re.M)
    raw = m.group(1).strip() if m else ""

    dish_count = ""
    staples = ""
    proteins = ""
    mixed = ""
    dishes = ""

    cm = re.search(r"菜品数\s*=\s*(\d+)", raw)
    if cm:
        dish_count = cm.group(1)
    sm = re.search(r"主食\s*=\s*([^；;]+)", raw)
    if sm:
        staples = sm.group(1).strip()
    pm = re.search(r"纯蛋白\s*=\s*([^；;]+)", raw)
    if pm:
        proteins = pm.group(1).strip()
    mm = re.search(r"荤素\s*=\s*([^；;]+)", raw)
    if mm:
        mixed = mm.group(1).strip()
    dm = re.search(r"本周菜名\s*=\s*(.+)$", raw)
    if dm:
        dishes = dm.group(1).strip()

    if not dishes:
        # 兜底：从「二、本周菜」段落抽非主食菜名
        section = re.search(
            r"二、本周菜[\s\S]*?(?=三、|$)",
            content,
        )
        block = section.group(0) if section else content
        names = re.findall(
            r"^\d+\.\s*【(?:纯蛋白|荤素)】\s*([^—\n（(]+)",
            block,
            re.M,
        )
        names = [n.strip(" -—") for n in names if n.strip()]
        if names:
            dishes = "|".join(names)
            if not dish_count:
                dish_count = str(len(names))

    return {
        "dish_count": dish_count or "未识别",
        "staples": staples,
        "proteins": proteins,
        "mixed": mixed,
        "dishes": dishes,
        "record_raw": raw,
    }


def build_messages(monday: date) -> tuple[str, str, dict]:
    dates = week_dates(monday)
    history = load_history()
    system = read_text("config/system_prompt.md")
    user_tpl = read_text("config/user_prompt.md")
    couple = read_text("config/couple.md")
    user = (
        user_tpl.replace("{{monday}}", dates["monday"])
        .replace("{{tuesday}}", dates["tuesday"])
        .replace("{{wednesday}}", dates["wednesday"])
        .replace("{{thursday}}", dates["thursday"])
        .replace("{{friday}}", dates["friday"])
        .replace("{{saturday}}", dates["saturday"])
        .replace("{{couple}}", couple)
        .replace("{{history}}", history_constraints(history))
    )
    return system, user, dates


def generate(monday: date | None = None, retries: int = 2) -> Path:
    monday = monday or resolve_week_monday()
    system, user, dates = build_messages(monday)
    last_err: Exception | None = None
    content = ""

    for attempt in range(1, retries + 1):
        try:
            content = strip_fence(chat_completion(system, user))
            validate_menu(content)
            break
        except Exception as e:  # noqa: BLE001
            last_err = e
            fail_path = ROOT / "logs" / "last-failed-content.txt"
            fail_path.parent.mkdir(parents=True, exist_ok=True)
            fail_path.write_text(
                f"# attempt {attempt} error: {e}\n\n{content}\n",
                encoding="utf-8",
            )
            if attempt == retries:
                raise
            print(f"  retry {attempt}/{retries}: {e}")
    else:
        raise last_err or RuntimeError("生成失败")

    out_dir = ROOT / "menus"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{monday.isoformat()}.txt"
    header = (
        f"夫妻减脂午餐备餐方案（{dates['monday']} 至 {dates['saturday']}）\n"
        f"一次做完 · 分装 12 盒冷冻 · 每天微波 + 新鲜蔬菜素材\n\n"
    )
    out_path.write_text(header + content.strip() + "\n", encoding="utf-8")

    rec = parse_record_line(content)
    history = load_history()
    weeks = [
        w for w in history.get("weeks", []) if w.get("week_start") != monday.isoformat()
    ]
    weeks.append(
        {
            "week_start": monday.isoformat(),
            "week_end": dates["saturday"],
            "dish_count": rec["dish_count"],
            "staples": rec["staples"],
            "proteins": rec["proteins"],
            "mixed": rec["mixed"],
            "dishes": rec["dishes"],
            "file": str(out_path.relative_to(ROOT)),
            "generated_at": datetime.now(BEIJING).isoformat(timespec="seconds"),
        }
    )
    history["weeks"] = weeks[-20:]
    save_history(history)
    return out_path


def validate_menu(content: str) -> None:
    """校验板块与禁忌；标题允许轻微空格差异。"""
    compact = re.sub(r"\s+", "", content)
    required_compact = (
        "一、本周主食",
        "二、本周菜",
        "三、12个饭盒怎么装",
        "四、备餐与冷冻要点",
        "五、当天加热时另配的蔬菜素材",
        "六、本周购物清单",
        "【记录】",
    )
    for block in required_compact:
        if block not in compact:
            raise RuntimeError(f"生成结果缺少「{block}」，请重试")
    for name in WEEKDAYS_CN:
        if name not in content:
            raise RuntimeError(f"生成结果缺少「{name}」，请重试")
    for bad in (
        "辣椒",
        "麻辣",
        "香辣",
        "剁椒",
        "虾皮",
        "鲈鱼",
        "带鱼",
        "草鱼",
        "巴沙鱼",
        "清蒸鱼",
    ):
        if bad in content:
            raise RuntimeError(f"生成结果含禁忌词「{bad}」，已拒绝，请重试")
    if "鳕鱼" in content or "三文鱼" in content:
        if "煎" not in content and "烤" not in content:
            raise RuntimeError("鱼类须为鳕鱼/三文鱼，且做法为煎或烤")
        if re.search(r"清蒸.{0,6}(鳕鱼|三文鱼)|(鳕鱼|三文鱼).{0,6}清蒸", content):
            raise RuntimeError("鳕鱼/三文鱼不可清蒸，须煎或烤")
    # 非鱼菜禁止「煎」：每个「煎」窗口须紧挨鳕鱼/三文鱼
    for m in re.finditer(r".{0,10}煎.{0,10}", content):
        window = m.group(0)
        if "鳕鱼" in window or "三文鱼" in window:
            continue
        raise RuntimeError(f"非鱼菜不可用煎（仅鳕鱼/三文鱼可煎）：…{window.strip()}…")
    # 菜品数：记录行或「二、本周菜」下条目
    rec = parse_record_line(content)
    count = None
    if str(rec.get("dish_count", "")).isdigit():
        count = int(rec["dish_count"])
    if count is None:
        section = re.search(r"二、本周菜[\s\S]*?(?=三、|$)", content)
        if section:
            count = len(
                re.findall(
                    r"^\d+\.\s*【(?:纯蛋白|荤素)】",
                    section.group(0),
                    re.M,
                )
            )
    if count is not None and count not in (5, 6):
        raise RuntimeError(f"除主食外菜品须为 5–6 道，当前识别为 {count}")


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser(description="生成夫妻减脂午餐周方案")
    ap.add_argument("--monday", help="指定本周周一日期 YYYY-MM-DD")
    args = ap.parse_args()
    monday = date.fromisoformat(args.monday) if args.monday else resolve_week_monday()
    path = generate(monday)
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
