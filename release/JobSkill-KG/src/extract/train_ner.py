"""在 Chinese-SkillSpan 上微调中文 BERT 做技能 span 抽取（LSKT 四类）。

训练集：dev 划分（2141 句）；评测集：test 划分（2590 句）。
输出模型：models/jobskill-ner；指标：eval/ner_metrics.json

用法：
    PYTHONPATH=.pkgs python3 src/extract/train_ner.py --epochs 3
"""
from __future__ import annotations

import argparse
import json
import os
import random
import time

import torch
from torch.utils.data import DataLoader, Dataset
from transformers import AutoModelForTokenClassification, AutoTokenizer

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA = os.path.join(ROOT, "eval", "skillspan_spans.jsonl")
MODEL_DIR = os.path.join(ROOT, "models", "bert-base-chinese")
OUT_DIR = os.path.join(ROOT, "models", "jobskill-ner")
METRICS = os.path.join(ROOT, "eval", "ner_metrics.json")

DEVICE = torch.device("mps" if torch.backends.mps.is_available() else "cpu")

LABELS = ["O", "B-S", "I-S", "B-K", "I-K", "B-T", "I-T", "B-L", "I-L"]
LABEL2ID = {l: i for i, l in enumerate(LABELS)}
ID2LABEL = {i: l for l, i in LABEL2ID.items()}


def spans_to_tags(text: str, spans: list[dict]) -> list[str]:
    tags = ["O"] * len(text)
    for s in spans:
        st, en, lab = s["start"], s["end"], s["label"]
        for k in range(st, min(en, len(text))):
            tags[k] = f"{'B' if k == st else 'I'}-{lab}"
    return tags


def tags_to_spans(tags: list[str]):
    spans = []
    cur = None
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


class SkillSpanDataset(Dataset):
    def __init__(self, rows, tok, max_len=192):
        self.rows = rows
        self.tok = tok
        self.max_len = max_len

    def __len__(self):
        return len(self.rows)

    def __getitem__(self, i):
        r = self.rows[i]
        text = r["text"]
        enc = self.tok(
            text,
            max_length=self.max_len,
            truncation=True,
            padding="max_length",
            return_offsets_mapping=True,
            return_tensors=None,
        )
        char_tags = spans_to_tags(text, r["spans"])
        labels = []
        for (s, e) in enc["offset_mapping"]:
            if e <= s:  # special token / 空
                labels.append(-100)
            else:
                labels.append(LABEL2ID[char_tags[min(s, len(char_tags) - 1)]])
        enc = {k: torch.tensor(v) for k, v in enc.items() if k != "offset_mapping"}
        enc["labels"] = torch.tensor(labels)
        return enc


def evaluate(model, tok, rows, batch_size: int = 32, max_len: int = 192):
    """按 offset_mapping 对齐到字符，避免多字 token（英文/数字/前导空格）导致错位。"""
    model.eval()
    gold, pred = [], []
    with torch.no_grad():
        for i in range(0, len(rows), batch_size):
            batch = rows[i : i + batch_size]
            enc = tok([r["text"] for r in batch], max_length=max_len, truncation=True,
                      padding=True, return_offsets_mapping=True, return_tensors="pt")
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
                pred.append({(s0, e0, l) for s0, e0, l in tags_to_spans(tags)})
                gold.append({(x["start"], x["end"], x["label"]) for x in r["spans"]})
    tp = sum(len(g & p) for g, p in zip(gold, pred))
    n_pred = sum(len(p) for p in pred)
    n_gold = sum(len(g) for g in gold)
    p_ = tp / n_pred if n_pred else 0.0
    r_ = tp / n_gold if n_gold else 0.0
    f_ = 2 * p_ * r_ / (p_ + r_) if (p_ + r_) else 0.0
    return {"precision": round(p_, 4), "recall": round(r_, 4), "f1": round(f_, 4),
            "n_gold": n_gold, "n_pred": n_pred, "tp": tp}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--epochs", type=int, default=3)
    ap.add_argument("--batch", type=int, default=16)
    ap.add_argument("--lr", type=float, default=3e-5)
    ap.add_argument("--max-len", type=int, default=192)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--eval-limit", type=int, default=0)
    args = ap.parse_args()

    random.seed(42)
    torch.manual_seed(42)

    rows = [json.loads(l) for l in open(DATA, encoding="utf-8")]
    train_rows = [r for r in rows if r["split"] == "dev"]
    test_rows = [r for r in rows if r["split"] == "test"]
    if args.limit:
        train_rows = train_rows[: args.limit]
        test_rows = test_rows[: args.limit]
    if args.eval_limit:
        test_rows = test_rows[: args.eval_limit]
    print(f"train={len(train_rows)} test={len(test_rows)}", flush=True)

    tok = AutoTokenizer.from_pretrained(MODEL_DIR)
    model = AutoModelForTokenClassification.from_pretrained(
        MODEL_DIR, num_labels=len(LABELS), id2label=ID2LABEL, label2id=LABEL2ID
    ).to(DEVICE)
    print(f"device={DEVICE}", flush=True)

    ds = SkillSpanDataset(train_rows, tok, args.max_len)
    dl = DataLoader(ds, batch_size=args.batch, shuffle=True)
    ev = DataLoader(SkillSpanDataset(test_rows, tok, args.max_len), batch_size=args.batch)

    opt = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=0.01)
    total = len(dl) * args.epochs
    sched = torch.optim.lr_scheduler.LambdaLR(opt, lambda s: min(1.0, (s + 1) / max(1, total * 0.1)))

    best = None
    step = 0
    for ep in range(args.epochs):
        model.train()
        t0 = time.time()
        run = 0.0
        for batch in dl:
            out = model(
                input_ids=batch["input_ids"].to(DEVICE),
                attention_mask=batch["attention_mask"].to(DEVICE),
                token_type_ids=batch.get("token_type_ids").to(DEVICE) if batch.get("token_type_ids") is not None else None,
                labels=batch["labels"].to(DEVICE),
            )
            loss = out.loss
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()
            sched.step()
            opt.zero_grad()
            run += loss.item()
            step += 1
            if step % 20 == 0:
                print(f"  ep{ep} step{step} loss={run / 20:.4f} ({time.time() - t0:.0f}s)", flush=True)
                run = 0.0
        m = evaluate(model, tok, test_rows, max_len=args.max_len)
        print(f"[epoch {ep}] {m} ({time.time() - t0:.0f}s)", flush=True)
        if best is None or m["f1"] > best["f1"]:
            best = m
            os.makedirs(OUT_DIR, exist_ok=True)
            model.save_pretrained(OUT_DIR)
            tok.save_pretrained(OUT_DIR)

    best = best or {}
    best["train_size"] = len(train_rows)
    best["test_size"] = len(test_rows)
    best["epochs"] = args.epochs
    with open(METRICS, "w", encoding="utf-8") as fh:
        json.dump(best, fh, ensure_ascii=False, indent=2)
    print("BEST:", json.dumps(best, ensure_ascii=False), "->", OUT_DIR)


if __name__ == "__main__":
    main()
