"""域内评测：用人工复核过的 spans 作为 gold，计算词典预标的 P/R/F1。

用法：
    PYTHONPATH=.pkgs python3 src/extract/eval_domain.py
输入：
    eval/domain_review.jsonl（status=reviewed 的条目参与评测）
输出：
    eval/domain_report.json
"""
from __future__ import annotations

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "src"))
from extract.extract_skills import build_trie, load_lexicon, trie_match  # noqa: E402

DATA = os.path.join(ROOT, "eval", "domain_review.jsonl")
OUT = os.path.join(ROOT, "eval", "domain_report.json")


def overlap(a, b) -> bool:
    return a[2] == b[2] and a[0] < b[1] and b[0] < a[1]


def main() -> None:
    rows = [json.loads(l) for l in open(DATA, encoding="utf-8")]
    trie = build_trie(load_lexicon())  # 用“当前词表”重新预测，便于对比扩词前后
    reviewed = [r for r in rows if r.get("status") == "reviewed"]
    if not reviewed:
        print(f"还没有复核过的条目（0/{len(rows)}）。打开 {DATA}，把 status 改成 reviewed 即可。")
        return

    tp = n_pred = n_gold = rtp = 0
    per_label = {k: {"tp": 0, "pred": 0, "gold": 0} for k in "SKTL"}
    for r in reviewed:
        gold = {(s["start"], s["end"], s["label"]) for s in r["spans"]}
        pred = {(a, b, typ) for a, b, (surface, typ, cnt, conf) in trie_match(r["text"], trie)}
        tp += len(gold & pred)
        n_pred += len(pred)
        n_gold += len(gold)
        for k in "SKTL":
            per_label[k]["tp"] += len({x for x in gold if x[2] == k} & {x for x in pred if x[2] == k})
            per_label[k]["pred"] += len([x for x in pred if x[2] == k])
            per_label[k]["gold"] += len([x for x in gold if x[2] == k])
        # relaxed：同标签且有重叠
        used = set()
        for g in gold:
            for p in pred:
                if p not in used and overlap(g, p):
                    used.add(p)
                    rtp += 1
                    break

    def prf(t, p, g):
        prec = t / p if p else 0.0
        rec = t / g if g else 0.0
        return round(prec, 4), round(rec, 4), round(2 * prec * rec / (prec + rec), 4) if prec + rec else 0.0

    report = {
        "reviewed": len(reviewed),
        "total": len(rows),
        "exact": dict(zip(["precision", "recall", "f1"], prf(tp, n_pred, n_gold))),
        "relaxed": dict(zip(["precision", "recall", "f1"], prf(rtp, n_pred, n_gold))),
        "per_label": {k: dict(zip(["precision", "recall", "f1"],
                                  prf(v["tp"], v["pred"], v["gold"]))) for k, v in per_label.items()},
    }
    json.dump(report, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print("->", OUT)


if __name__ == "__main__":
    main()
