"""从岗位文本里挖技能候选：线索词 + 词性过滤，按频次排序，人工筛选后并入 tech_skills.txt。

线索词：熟悉/掌握/熟练使用/精通/了解/使用/具备/要求/负责/参与/搭建/建设/实现/设计
取线索词后连续的 名词/专名/动名词/英文 片段（≤4 个词、≤14 字）。

用法：
    python3 src/extract/mine_skills.py --top 150
输出：
    data/lexicon/mined_candidates.tsv
"""
from __future__ import annotations

import argparse
import json
import os
import re
from collections import Counter

import jieba.posseg as pseg

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
JOBS = os.path.join(ROOT, "data", "processed", "jobs.jsonl")
OUT = os.path.join(ROOT, "data", "lexicon", "mined_candidates.tsv")

CUES = ["熟悉", "熟练掌握", "熟练使用", "熟练", "掌握", "精通", "了解", "使用", "具备", "具有",
        "负责", "参与", "搭建", "建设", "实现", "设计", "开发", "维护", "优化"]
OK_POS = {"n", "nz", "vn", "eng", "nrt", "nr", "ns", "j", "l", "an"}
STOP = {"工作", "能力", "经验", "公司", "团队", "项目", "业务", "系统", "平台", "技术", "产品",
        "服务", "管理", "开发", "设计", "分析", "相关", "以上", "以及", "进行", "完成", "支持",
        "要求", "优先", "负责", "具备", "熟悉", "掌握", "了解", "使用", "熟悉相关", "等内容"}


def candidates(sent: str):
    words = list(pseg.cut(sent))
    for i, (w, flag) in enumerate(words):
        if w not in CUES:
            continue
        buf, n = [], 0
        j = i + 1
        while j < len(words) and len(buf) < 4:
            w2, f2 = words[j]
            if f2 in OK_POS and len(w2) <= 8:
                buf.append(w2)
                n += len(w2)
                if n > 14:
                    break
                j += 1
            else:
                break
        if buf:
            cand = "".join(buf)
            if 2 <= len(cand) <= 14 and cand not in STOP:
                yield cand


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=150)
    args = ap.parse_args()

    cnt = Counter()
    for line in open(JOBS, encoding="utf-8"):
        j = json.loads(line)
        for seg in re.split(r"[。；;\n、]", f"{j['requirement']}\n{j['description']}"):
            if 4 <= len(seg) <= 120:
                for c in candidates(seg):
                    cnt[c] += 1

    rows = [(c, n) for c, n in cnt.most_common(args.top * 3)]
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write("candidate\tcount\n")
        for c, n in rows:
            fh.write(f"{c}\t{n}\n")
    for c, n in rows[: args.top]:
        print(f"{n:5d}  {c}")
    print(f"\n-> {OUT}（共 {len(cnt)} 个候选）")


if __name__ == "__main__":
    main()
