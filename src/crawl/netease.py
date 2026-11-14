"""网易招聘（hr.163.com）采集适配器。

接口：POST /api/hr163/position/queryPage
特点：列表接口直接返回 description（职责）与 requirement（要求），无需逐条取详情。
规模：约 2700 条，30 次请求左右。
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from crawl.common import (  # noqa: E402
    RAW_DIR,
    JsonlWriter,
    done_ids,
    make_record,
    polite_sleep,
    request_json,
)

API = "https://hr.163.com/api/hr163/position/queryPage"
DETAIL_URL = "https://hr.163.com/job-detail.html?id={id}"
OUT = os.path.join(RAW_DIR, "netease.jsonl")


def fetch_page(page: int, size: int = 100) -> dict | None:
    return request_json(
        API,
        method="POST",
        json_body={"currentPage": page, "pageSize": size},
        headers={"Referer": "https://hr.163.com/", "Origin": "https://hr.163.com"},
    )


def parse(item: dict) -> dict:
    jid = item.get("id")
    places = item.get("workPlaceNameList") or []
    return make_record(
        source="netease",
        source_id=str(jid),
        url=DETAIL_URL.format(id=jid),
        title=item.get("name", ""),
        company="网易",
        department=item.get("firstDepName", "") or item.get("productName", ""),
        category=item.get("firstPostTypeName", ""),
        locations=[p for p in places if p],
        description=item.get("description", ""),
        requirement=item.get("requirement", ""),
        education=item.get("reqEducationName", "") or "",
        experience=item.get("reqWorkYearsName", "") or "",
        extras={
            "productName": item.get("productName"),
            "workType": item.get("workType"),
            "recruitNum": item.get("recruitNum"),
            "updateTime": item.get("updateTime"),
        },
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", type=int, default=0, help="最多抓多少页，0=全部")
    ap.add_argument("--size", type=int, default=100)
    args = ap.parse_args()

    seen = done_ids(OUT)
    print(f"已有 {len(seen)} 条，续采 …", flush=True)

    first = fetch_page(1, args.size)
    if not first or first.get("code") != 200:
        print("首屏失败，退出")
        return
    total = first["data"]["total"]
    pages = (total + args.size - 1) // args.size
    if args.pages:
        pages = min(pages, args.pages)
    print(f"total={total} pages={pages} size={args.size}", flush=True)

    n_new = 0
    with JsonlWriter(OUT) as w:
        for page in range(1, pages + 1):
            data = first if page == 1 else fetch_page(page, args.size)
            if not data or data.get("code") != 200:
                print(f"page {page} 失败，跳过", flush=True)
                polite_sleep(1.0)
                continue
            batch = data["data"]["list"] or []
            for item in batch:
                rec = parse(item)
                if rec["doc_id"] in seen:
                    continue
                w.write(rec)
                seen.add(rec["doc_id"])
                n_new += 1
            print(f"page {page}/{pages} +{len(batch)} (total_new={n_new})", flush=True)
            polite_sleep(0.3)

    print(f"完成，新增 {n_new} 条 -> {OUT}", flush=True)


if __name__ == "__main__":
    main()
