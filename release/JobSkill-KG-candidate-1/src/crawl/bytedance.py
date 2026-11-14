"""字节跳动招聘（jobs.bytedance.com）采集适配器。

接口：POST /api/v1/search/job/posts
    body 必须严格为：{"keyword","limit","offset","job_category_id_list","location_code_list"}
    （多传字段会返回 405）
特点：列表直接返回 description（职责）与 requirement（要求），无需详情请求。
注意：接口 count 上限显示 10000，offset 超过后返回空列表即停。
"""
from __future__ import annotations

import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from crawl.common import (  # noqa: E402
    RAW_DIR,
    JsonlWriter,
    done_ids,
    make_record,
    polite_sleep,
    request_json,
)

API = "https://jobs.bytedance.com/api/v1/search/job/posts"
DETAIL = "https://jobs.bytedance.com/experienced/position/{id}/detail"
OUT = os.path.join(RAW_DIR, "bytedance.jsonl")
HEADERS = {
    "Referer": "https://jobs.bytedance.com/experienced/position",
    "Origin": "https://jobs.bytedance.com",
    "Accept": "application/json, text/plain, */*",
}


def fetch(offset: int, limit: int = 100) -> dict | None:
    return request_json(
        API,
        method="POST",
        json_body={
            "keyword": "",
            "limit": limit,
            "offset": offset,
            "job_category_id_list": [],
            "location_code_list": [],
        },
        headers=HEADERS,
    )


def parse(item: dict) -> dict:
    jid = item.get("id")
    cities = [c.get("name", "") for c in (item.get("city_list") or []) if c.get("name")]
    if not cities and item.get("city_info"):
        cities = [item["city_info"].get("name", "")]
    cat = (item.get("job_category") or {}).get("name", "")
    ts = item.get("publish_time")
    published = (
        time.strftime("%Y-%m-%d", time.localtime(ts / 1000)) if isinstance(ts, (int, float)) else ""
    )
    return make_record(
        source="bytedance",
        source_id=str(jid),
        url=DETAIL.format(id=jid),
        title=item.get("title", ""),
        company="字节跳动",
        department="",
        category=cat,
        locations=cities,
        description=item.get("description", ""),
        requirement=item.get("requirement", ""),
        published_at=published,
        extras={
            "recruit_type": (item.get("recruit_type") or {}).get("name"),
            "code": item.get("code"),
        },
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=100)
    ap.add_argument("--max-offset", type=int, default=10000)
    args = ap.parse_args()

    seen = done_ids(OUT)
    print(f"已有 {len(seen)} 条，续采 …", flush=True)

    n_new = 0
    offset = 0
    with JsonlWriter(OUT) as w:
        while offset < args.max_offset:
            data = fetch(offset, args.limit)
            if not data or data.get("code") != 0:
                print(f"offset {offset} 失败，重试一次", flush=True)
                polite_sleep(2.0)
                data = fetch(offset, args.limit)
                if not data or data.get("code") != 0:
                    break
            items = data["data"].get("job_post_list") or []
            if not items:
                print("空列表，结束", flush=True)
                break
            for it in items:
                rec = parse(it)
                if rec["doc_id"] in seen:
                    continue
                w.write(rec)
                seen.add(rec["doc_id"])
                n_new += 1
            print(f"offset {offset} +{len(items)} (new={n_new})", flush=True)
            offset += args.limit
            polite_sleep(0.4)

    print(f"完成，新增 {n_new} 条 -> {OUT}", flush=True)


if __name__ == "__main__":
    main()
