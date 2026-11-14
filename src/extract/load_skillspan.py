"""解析 Chinese-SkillSpan 的 @@span##L 标注格式，转成 (text, spans) 与 BIO 序列。

- dev/test 为 instruction 格式：input 原文，output 带 @@...##X 标记
- train 文件无标注，跳过

用法：
    python3 src/extract/load_skillspan.py
输出：
    eval/skillspan_spans.jsonl
"""
from __future__ import annotations

import json
import os
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
EXT = os.path.join(ROOT, "data", "external", "cn_skillspan")
OUT = os.path.join(ROOT, "eval", "skillspan_spans.jsonl")


def parse_marked(out: str):
    """把 '@@片段##S' 解析成 (clean_text, [(start,end,label,text)])。"""
    buf: list[str] = []
    spans = []
    i = 0
    n = len(out)
    while i < n:
        if out.startswith("@@", i):
            j = out.find("##", i + 2)
            if j == -1:
                buf.append(out[i])
                i += 1
                continue
            label = out[j + 2] if j + 2 < n else "S"
            span_text = out[i + 2 : j]
            start = sum(len(b) for b in buf)
            spans.append((start, start + len(span_text), label, span_text))
            buf.append(span_text)
            i = j + 3
        else:
            buf.append(out[i])
            i += 1
    return "".join(buf), spans


def to_bio(text: str, spans, scheme: list[str]):
    tags = ["O"] * len(text)
    for start, end, label, _ in spans:
        for k in range(start, min(end, len(text))):
            tags[k] = f"{'B' if k == start else 'I'}-{label}"
    return tags


def main() -> None:
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    total = ok = bad = 0
    label_c = Counter()
    len_c = []
    rows = []
    for split in ["dev", "test"]:
        path = os.path.join(EXT, f"CN_skillspan_lkst_{split}.json")
        data = json.load(open(path, encoding="utf-8"))
        for rec in data:
            total += 1
            clean, spans = parse_marked(rec["output"])
            raw = rec["input"]
            # 校验：去标记文本应与原文一致（允许首尾空白差异）
            if clean.strip() != raw.strip():
                bad += 1
                continue
            ok += 1
            for s, e, lab, txt in spans:
                label_c[lab] += 1
                len_c.append(e - s)
            rows.append(
                {
                    "split": split,
                    "text": clean,
                    "spans": [{"start": s, "end": e, "label": lab, "text": txt} for s, e, lab, txt in spans],
                    "meta": rec.get("meta", {}),
                }
            )

    with open(OUT, "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"解析 {total} 条，成功 {ok}（{ok / max(1, total):.1%}），不一致 {bad}")
    print("标签分布：", dict(label_c))
    print(f"平均 span 长度：{sum(len_c) / max(1, len(len_c)):.1f} 字")
    print(f"有 span 的句子占比：{sum(1 for r in rows if r['spans']) / max(1, len(rows)):.1%}")
    print("->", OUT)


if __name__ == "__main__":
    main()
