"""评测：在 Chinese-SkillSpan 全量 test 上算整体与分标签 P/R/F1，并抽样错误案例。

用法：
    PYTHONPATH=.pkgs python3 src/extract/eval_ner.py [--errors 20]
输出：
    eval/ner_report.json
    eval/error_samples.jsonl
"""
from __future__ import annotations

import argparse
import json
import os
import random

import torch
from transformers import AutoModelForTokenClassification, AutoTokenizer

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA = os.path.join(ROOT, "eval", "skillspan_spans.jsonl")
MODEL = os.path.join(ROOT, "models", "jobskill-ner")
OUT = os.path.join(ROOT, "eval", "ner_report.json")
ERR = os.path.join(ROOT, "eval", "error_samples.jsonl")

DEVICE = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
LABELS = ["O", "B-S", "I-S", "B-K", "I-K", "B-T", "I-T", "B-L", "I-L"]
ID2LABEL = {i: l for i, l in enumerate(LABELS)}


def relaxed_match(gold: set, pred: set) -> int:
    """宽松匹配：同标签且区间有重叠即算命中（一对一贪心），论文里的 Relaxed F1。"""
    used = set()
    hit = 0
    for g in sorted(gold):
        for p in sorted(pred):
            if p in used:
                continue
            if g[2] == p[2] and g[0] < p[1] and p[0] < g[1]:
                used.add(p)
                hit += 1
                break
    return hit


def tags_to_spans(tags):
    spans, cur = [], None
    for i, t in enumerate(tags):
        if t.startswith("B-"):
            if cur:
                spans.append(cur)
            cur = [i, i + 1, t[2:]]
        elif t.startswith("I-") and cur and cur[2] == t[2:]:
            cur[1] = i + 1
        else:
            if cur:
                spans.append(cur)
                cur = None
    if cur:
        spans.append(cur)
    return spans


@torch.no_grad()
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--errors", type=int, default=20)
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    tok = AutoTokenizer.from_pretrained(MODEL)
    model = AutoModelForTokenClassification.from_pretrained(MODEL).to(DEVICE).eval()

    rows = [json.loads(l) for l in open(DATA, encoding="utf-8") if json.loads(l)["split"] == "test"]
    if args.limit:
        rows = rows[: args.limit]

    rtp = 0
    rpred = 0
    rgold = 0
    tp = {k: 0 for k in "SKTL"}
    npred = {k: 0 for k in "SKTL"}
    ngold = {k: 0 for k in "SKTL"}
    errors = []

    batch_size = 32
    for i in range(0, len(rows), batch_size):
        batch = rows[i : i + batch_size]
        enc = tok([r["text"] for r in batch], max_length=128, truncation=True, padding=True,
                  return_offsets_mapping=True, return_tensors="pt")
        offsets = enc.pop("offset_mapping")
        logits = model(**{k: v.to(DEVICE) for k, v in enc.items()}).logits.argmax(-1).cpu()
        for bi, r in enumerate(batch):
            text = r["text"]
            tags = ["O"] * len(text)
            for (s0, e0), lid in zip(offsets[bi].tolist(), logits[bi].tolist()):
                if e0 <= s0:
                    continue
                lab = ID2LABEL[lid]
                for k in range(s0, min(e0, len(text))):
                    tags[k] = lab
            pred = {(s, e, l) for s, e, l in tags_to_spans(tags)}
            gold = {(x["start"], x["end"], x["label"]) for x in r["spans"]}
            for k in "SKTL":
                p = {x for x in pred if x[2] == k}
                g = {x for x in gold if x[2] == k}
                tp[k] += len(p & g)
                npred[k] += len(p)
                ngold[k] += len(g)
            rtp += relaxed_match(gold, pred)
            rpred += len(pred)
            rgold += len(gold)
            if pred != gold and len(errors) < args.errors * 5:
                errors.append({"text": r["text"], "gold": sorted(gold), "pred": sorted(pred)})

    def prf(t, p, g):
        prec = t / p if p else 0.0
        rec = t / g if g else 0.0
        f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
        return round(prec, 4), round(rec, 4), round(f1, 4)

    per = {k: dict(zip(["precision", "recall", "f1"], prf(tp[k], npred[k], ngold[k])))
           for k in "SKTL"}
    T, P, G = sum(tp.values()), sum(npred.values()), sum(ngold.values())
    overall = dict(zip(["precision", "recall", "f1"], prf(T, P, G)))
    rp = rtp / rpred if rpred else 0.0
    rr = rtp / rgold if rgold else 0.0
    rf = 2 * rp * rr / (rp + rr) if (rp + rr) else 0.0
    report = {"split": "test", "n_sentences": len(rows), "overall": overall,
              "relaxed": {"precision": round(rp, 4), "recall": round(rr, 4), "f1": round(rf, 4)},
              "per_label": per, "tp": T, "n_pred": P, "n_gold": G,
              "model": MODEL}
    json.dump(report, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    random.seed(0)
    with open(ERR, "w", encoding="utf-8") as fh:
        for e in random.sample(errors, min(args.errors, len(errors))):
            fh.write(json.dumps(e, ensure_ascii=False) + "\n")

    print(json.dumps(report, ensure_ascii=False, indent=2))
    print("->", OUT, ERR)


if __name__ == "__main__":
    main()
