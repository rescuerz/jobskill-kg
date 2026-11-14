"""生成域内评测复核包：抽 100 句岗位要求文本 + 词典预标结果，供人工复核。

用法：
    PYTHONPATH=.pkgs python3 src/extract/make_review_pack.py
输出：
    eval/domain_review.jsonl

复核方式：
    1. 打开 eval/domain_review.jsonl
    2. 每条把 spans 改成你认可的 [{start,end,text,label}]（可全删/可加），status 改为 reviewed
    3. 跑 PYTHONPATH=.pkgs python3 src/extract/eval_domain.py 得到域内 P/R/F1
"""
from __future__ import annotations

import json
import os
import random
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "src"))

from extract.extract_skills import build_trie, load_lexicon, trie_match  # noqa: E402

JOBS = os.path.join(ROOT, "data", "processed", "jobs.jsonl")
OUT = os.path.join(ROOT, "eval", "domain_review.jsonl")


def main() -> None:
    random.seed(11)
    lex = load_lexicon()
    trie = build_trie(lex)

    jobs = [json.loads(l) for l in open(JOBS, encoding="utf-8")]
    by_fam: dict[str, list] = {}
    for j in jobs:
        by_fam.setdefault(j["job_family"], []).append(j)

    # 按句抽样：优先带技能线索词的句子，保证样本有内容可标
    CUES = ("熟悉", "掌握", "精通", "了解", "使用", "具备", "负责", "搭建", "开发", "设计")
    cand_with, cand_plain = [], []
    for j in jobs:
        for seg in re.split(r"(?<=[。；;])", f"{j['requirement']}\n{j['description']}"):
            seg = seg.strip(" 　，,、")
            if not (20 <= len(seg) <= 160):
                continue
            (cand_with if any(c in seg for c in CUES) else cand_plain).append((j, seg))

    picked = []
    per = 70 // len(by_fam)
    for fam in by_fam:
        arr = [(j, t) for j, t in cand_with if j["job_family"] == fam]
        picked += random.sample(arr, min(per, len(arr)))
    picked += random.sample(cand_plain, min(30, len(cand_plain)))
    random.shuffle(picked)
    picked = picked[:100]

    rows = []
    for j, text in picked:
        spans = []
        for s, e, (surface, typ, cnt, conf) in trie_match(text, trie):
            spans.append({"start": s, "end": e, "text": surface, "label": typ})
        rows.append({
            "id": len(rows) + 1,
            "doc_id": j["doc_id"],
            "family": j["job_family"],
            "title": j["title"],
            "text": text,
            "pre_spans": spans,
            "spans": spans,
            "status": "todo",
        })

    with open(OUT, "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"生成 {len(rows)} 条例句，其中 {sum(1 for r in rows if r['pre_spans'])} 条有预标 -> {OUT}")


if __name__ == "__main__":
    main()
