"""腾讯招聘（careers.tencent.com）采集适配器。

接口：
  列表 GET /tencentcareer/api/post/Query?pageIndex=&pageSize=100&language=zh-cn&area=cn
  详情 GET /tencentcareer/api/post/ByPostId?postId=&language=zh-cn
列表只有职责（Responsibility），要求（Requirement）需逐条取详情，约 2250 条。
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

LIST_API = "https://careers.tencent.com/tencentcareer/api/post/Query"
DETAIL_API = "https://careers.tencent.com/tencentcareer/api/post/ByPostId"
POST_URL = "https://careers.tencent.com/jobdesc.html?postId={id}"
OUT = os.path.join(RAW_DIR, "tencent.jsonl")


def fetch_list(page: int, size: int = 100) -> dict | None:
    return request_json(
        LIST_API,
        params={
            "timestamp": int(time.time() * 1000),
            "pageIndex": page,
            "pageSize": size,
            "language": "zh-cn",
            "area": "cn",
        },
        headers={"Referer": "https://careers.tencent.com/"},
    )


def fetch_detail(post_id: str) -> dict | None:
    data = request_json(
        DETAIL_API,
        params={"postId": post_id, "language": "zh-cn"},
        headers={"Referer": POST_URL.format(id=post_id)},
    )
    if not data or data.get("Code") != 200:
        return None
    return data.get("Data")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--size", type=int, default=100)
    ap.add_argument("--max", type=int, default=0, help="最多抓多少条，0=全部")
    args = ap.parse_args()

    seen = done_ids(OUT)
    print(f"已有 {len(seen)} 条，续采 …", flush=True)

    first = fetch_list(1, args.size)
    if not first or first.get("Code") != 200:
        print("首屏失败，退出")
        return
    total = first["Data"]["Count"]
    pages = (total + args.size - 1) // args.size
    print(f"total={total} pages={pages}", flush=True)

    # 1) 收集全部 PostId
    post_ids: list[str] = []
    for page in range(1, pages + 1):
        data = first if page == 1 else fetch_list(page, args.size)
        if not data or data.get("Code") != 200:
            print(f"list page {page} 失败", flush=True)
            polite_sleep(1.5)
            continue
        for p in data["Data"]["Posts"] or []:
            post_ids.append(str(p["PostId"]))
        print(f"list page {page}/{pages} (+{len(data['Data']['Posts'])})", flush=True)
        polite_sleep(0.3)

    post_ids = list(dict.fromkeys(post_ids))
    if args.max:
        post_ids = post_ids[: args.max]
    print(f"待取详情 {len(post_ids)} 条", flush=True)

    # 2) 逐条取详情
    n_new = 0
    with JsonlWriter(OUT) as w:
        for i, pid in enumerate(post_ids, 1):
            doc_id = f"tencent:{pid}"
            if doc_id in seen:
                continue
            d = fetch_detail(pid)
            if not d:
                print(f"  detail {pid} 失败", flush=True)
                polite_sleep(1.0)
                continue
            rec = make_record(
                source="tencent",
                source_id=pid,
                url=POST_URL.format(id=pid),
                title=d.get("RecruitPostName", ""),
                company="腾讯",
                department=d.get("BGName", ""),
                category=d.get("CategoryName", ""),
                locations=[d.get("LocationName", "")] if d.get("LocationName") else [],
                description=d.get("Responsibility", ""),
                requirement=d.get("Requirement", ""),
                experience=d.get("RequireWorkYearsName", "") or "",
                published_at=d.get("LastUpdateTime", "") or "",
                extras={
                    "productName": d.get("ProductName"),
                    "importantItem": d.get("ImportantItem"),
                    "postLightItem": d.get("PostLightItem"),
                },
            )
            w.write(rec)
            seen.add(doc_id)
            n_new += 1
            if i % 20 == 0:
                print(f"  detail {i}/{len(post_ids)} new={n_new}", flush=True)
            polite_sleep(0.35)

    print(f"完成，新增 {n_new} 条 -> {OUT}", flush=True)


if __name__ == "__main__":
    main()
