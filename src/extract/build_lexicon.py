"""从 gold 标注里挖技能词表，并与人工种子词合并，产出词典抽取用的 lexicon。

输入：
    eval/skillspan_spans.jsonl   （Chinese-SkillSpan 的 gold span）
    data/lexicon/seed_skills.txt （人工种子词，可选，一行一个，支持 "词<TAB>类型<TAB>规范名"）
输出：
    data/lexicon/skill_lexicon.tsv
        surface \t type \t count \t canonical

用法：
    python3 src/extract/build_lexicon.py
"""
from __future__ import annotations

import json
import os
import re
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SPANS = os.path.join(ROOT, "eval", "skillspan_spans.jsonl")
SEED = os.path.join(ROOT, "data", "lexicon", "seed_skills.txt")
OUT = os.path.join(ROOT, "data", "lexicon", "skill_lexicon.tsv")

# 归一化时要剥掉的前后缀
PREFIX = re.compile(r"^(熟悉|熟练|掌握|精通|了解|会使用|使用|具备|具有|能够|能|有)")
SUFFIX = re.compile(r"(能力|经验|技能|相关|知识)$")
PUNCT = re.compile(r"[\s\u3000，。、；：（）()【】\[\]「」\"'·•\-—_/\\|]+")


def norm(s: str) -> str:
    s = PUNCT.sub("", s or "")
    s = PREFIX.sub("", s)
    s = SUFFIX.sub("", s)
    return s.strip()


def main() -> None:
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    cnt: Counter[str] = Counter()
    types: dict[str, Counter] = defaultdict(Counter)

    for line in open(SPANS, encoding="utf-8"):
        r = json.loads(line)
        for sp in r["spans"]:
            raw = sp["text"].strip()
            key = norm(raw)
            if not (2 <= len(key) <= 24):
                continue
            cnt[key] += 1
            types[key][sp["label"]] += 1

    # 人工种子词
    if os.path.exists(SEED):
        for line in open(SEED, encoding="utf-8"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t")
            w = parts[0].strip()
            t = parts[1].strip() if len(parts) > 1 else "S"
            cnt[w] += 1
            types[w][t] += 1

    rows = []
    for w, c in cnt.items():
        t = types[w].most_common(1)[0][0]
        rows.append((w, t, c, w))
    rows.sort(key=lambda x: (-x[2], -len(x[0])))

    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write("surface\ttype\tcount\tcanonical\n")
        for r in rows:
            fh.write("\t".join(str(x) for x in r) + "\n")

    print(f"词表 {len(rows)} 条 -> {OUT}")
    from collections import Counter as C
    print("类型分布：", dict(C(r[1] for r in rows)))
    print("Top20：", [r[0] for r in rows[:20]])


if __name__ == "__main__":
    main()
