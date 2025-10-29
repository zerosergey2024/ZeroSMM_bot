import os
import argparse
from datetime import datetime
from typing import Dict, Any, List
import requests
import pandas as pd
import config as conf

VK_API = "https://api.vk.com/method/"
API_VERSION = "5.199"  # при необходимости обнови

def vk_call(method: str, params: Dict[str, Any]) -> Dict[str, Any]:
    params = {**params, "v": API_VERSION}
    resp = requests.get(VK_API + method, params=params, timeout=30)
    data = resp.json()
    if "error" in data:
        raise RuntimeError(f"VK API error: {data['error']}")
    return data["response"]

def parse_stats_item(item: Dict[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    ts = item.get("day", item.get("date", 0)) or 0
    out["date"] = datetime.utcfromtimestamp(int(ts)).date().isoformat()

    visitors = item.get("visitors") or {}
    out["visitors"]   = visitors.get("visitors")
    out["views"]      = visitors.get("views")

    subs = item.get("subscribers") or {}
    out["subscribed"]   = subs.get("subscribed", subs.get("new"))
    out["unsubscribed"] = subs.get("unsubscribed", subs.get("lost"))

    activity = item.get("activity") or {}
    out["likes"]     = activity.get("likes")
    out["comments"]  = activity.get("comments")
    out["reposts"]   = activity.get("copies", activity.get("reposts"))

    return out

def get_group_stats(group_id: int, date_from: str, date_to: str, access_token: str) -> List[Dict[str, Any]]:
    resp = vk_call("stats.get", {
        "group_id": group_id,
        "interval": "day",
        "date_from": date_from,
        "date_to": date_to,
        "access_token": access_token,
    })
    items = resp if isinstance(resp, list) else resp.get("stats", [])
    return [parse_stats_item(x) for x in items]

def main():
    parser = argparse.ArgumentParser(description="VK group daily stats export")
    parser.add_argument("--group_id", type=int, required=True, help="ID сообщества без минуса")
    parser.add_argument("--date_from", type=str, required=True, help="YYYY-MM-DD")
    parser.add_argument("--date_to", type=str, required=True, help="YYYY-MM-DD")
    parser.add_argument("--out", type=str, default="vk_report.csv")
    args = parser.parse_args()

    token = conf.vk_access_token or os.getenv("VK_ACCESS_TOKEN")
    if not token or token.startswith("PUT_"):
        raise RuntimeError("VK_ACCESS_TOKEN не задан")

    stats = get_group_stats(args.group_id, args.date_from, args.date_to, token)
    df = pd.DataFrame(stats).sort_values("date")
    df.to_csv(args.out, index=False, encoding="utf-8")
    print(f"Сохранено: {args.out}")
    if len(df) > 0:
        print(df.tail(5))

if __name__ == "__main__":
    main()
