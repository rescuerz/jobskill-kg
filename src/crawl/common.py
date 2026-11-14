"""采集公共工具：限速、重试、断点续采、统一记录格式。"""
from __future__ import annotations

import hashlib
import json
import os
import random
import time
from datetime import datetime, timezone

import requests

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

_session = requests.Session()
_session.headers.update(
    {
        "User-Agent": UA,
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9",
    }
)

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RAW_DIR = os.path.join(ROOT, "data", "raw")


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def request_json(
    url: str,
    *,
    method: str = "GET",
    json_body: dict | None = None,
    params: dict | None = None,
    headers: dict | None = None,
    timeout: int = 25,
    retries: int = 4,
    base_delay: float = 1.0,
):
    """带指数退避的 JSON 请求；失败返回 None，不抛异常中断整轮采集。"""
    last_err = None
    for attempt in range(retries):
        try:
            if method.upper() == "POST":
                resp = _session.post(
                    url, json=json_body, params=params, headers=headers, timeout=timeout
                )
            else:
                resp = _session.get(url, params=params, headers=headers, timeout=timeout)
            if resp.status_code == 200:
                return resp.json()
            last_err = f"HTTP {resp.status_code}"
        except Exception as exc:  # noqa: BLE001
            last_err = repr(exc)
        sleep = base_delay * (2**attempt) + random.uniform(0, 0.3)
        print(f"  ! {last_err} -> retry {attempt + 1}/{retries} in {sleep:.1f}s", flush=True)
        time.sleep(sleep)
    print(f"  x give up: {url} ({last_err})", flush=True)
    return None


def polite_sleep(seconds: float = 0.35) -> None:
    time.sleep(seconds + random.uniform(0, 0.15))


def done_ids(path: str, key: str = "doc_id") -> set[str]:
    """断点续采：读取已写入的记录 id。"""
    ids: set[str] = set()
    if not os.path.exists(path):
        return ids
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                ids.add(json.loads(line)[key])
            except Exception:  # noqa: BLE001
                continue
    return ids


class JsonlWriter:
    """追加写 jsonl，自动建目录，flush 每条。"""

    def __init__(self, path: str):
        self.path = path
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self._fh = open(path, "a", encoding="utf-8")

    def write(self, record: dict) -> None:
        self._fh.write(json.dumps(record, ensure_ascii=False) + "\n")
        self._fh.flush()

    def close(self) -> None:
        self._fh.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


def make_record(
    *,
    source: str,
    source_id: str,
    url: str,
    title: str,
    company: str,
    description: str = "",
    requirement: str = "",
    locations: list[str] | None = None,
    category: str = "",
    department: str = "",
    education: str = "",
    experience: str = "",
    published_at: str = "",
    extras: dict | None = None,
) -> dict:
    """统一记录格式。description=岗位职责，requirement=任职要求。"""
    text = f"{title}\n{description}\n{requirement}"
    return {
        "doc_id": f"{source}:{source_id}",
        "source": source,
        "source_id": str(source_id),
        "url": url,
        "crawled_at": now_iso(),
        "title": (title or "").strip(),
        "company": company,
        "department": department,
        "category": category,
        "locations": locations or [],
        "description": (description or "").strip(),
        "requirement": (requirement or "").strip(),
        "education": education,
        "experience": experience,
        "published_at": published_at,
        "content_sha256": sha256(text),
        "extras": extras or {},
    }
