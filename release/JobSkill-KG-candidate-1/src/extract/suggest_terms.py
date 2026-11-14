"""词表缺口自动发现：从语料里挖出「高频但词表没覆盖」的技能候选，供人工审核后并入词表。

思路：
    1. 线索词 + 词性切分（jieba）抽候选短语；可选叠加微调 BERT 的预测
    2. 用当前词表做 Trie 匹配，删掉已被覆盖的候选
    3. 按出现频次排序，输出 TSV（含类型建议与例句）

用法：
    PYTHONPATH=.pkgs python3 src/extract/suggest_terms.py --limit 1500 --min-count 8
    PYTHONPATH=.pkgs python3 src/extract/suggest_terms.py --use-model --limit 500
输出：
    data/lexicon/suggested_terms.tsv
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "src"))

from extract.extract_skills import (  # noqa: E402
    GENERIC,
    build_trie,
    load_lexicon,
    trie_match,
)

JOBS = os.path.join(ROOT, "data", "processed", "jobs.jsonl")
OUT = os.path.join(ROOT, "data", "lexicon", "suggested_terms.tsv")

CUES = ["熟悉", "熟练掌握", "熟练使用", "熟练", "掌握", "精通", "了解", "使用", "具备", "具有",
        "负责", "参与", "搭建", "建设", "实现", "设计", "开发", "维护", "优化"]
OK_POS = {"n", "nz", "vn", "eng", "nrt", "nr", "ns", "j", "l", "an"}
STOP = {"工作", "能力", "经验", "公司", "团队", "项目", "业务", "系统", "平台", "技术", "产品",
        "服务", "管理", "开发", "设计", "分析", "相关", "以上", "以及", "进行", "完成", "支持",
        "要求", "优先", "负责", "具备", "熟悉", "掌握", "了解", "使用", "等内容", "方案", "方向",
        "经验优先", "工作经验", "业界领先", "业界", "面向", "过程", "场景", "方法", "原理", "效率",
        "环境", "国际", "定义", "工具", "流程", "框架", "模型", "数据", "语言", "系统"}

# 技能词常见的后缀：命中即认为更像技能名词
SUFFIX = ("算法", "模型", "框架", "引擎", "平台", "协议", "数据库", "工具", "语言", "库", "服务",
          "网关", "中间件", "集群", "网络", "芯片", "算子", "内核", "调度", "链路", "指标")
ASCII_RE = re.compile(r"[A-Za-z]")
# 模型边界错位产物：单个字母 + 中文（如 "I技术" "C验证"），是 AI技术/API验证 被切断的结果
FRAGMENT_RE = re.compile(r"^[A-Za-z]{1,2}[\u4e00-\u9fa5]")


def cue_candidates(sent: str, pseg):
    words = list(pseg.cut(sent))
    for i, (w, _flag) in enumerate(words):
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
    ap.add_argument("--limit", type=int, default=1500)
    ap.add_argument("--min-count", type=int, default=8)
    ap.add_argument("--use-model", action="store_true", help="叠加微调 BERT 的预测（更慢）")
    ap.add_argument("--top", type=int, default=60)
    args = ap.parse_args()

    import jieba.posseg as pseg

    trie = build_trie(load_lexicon())
    jobs = [json.loads(l) for l in open(JOBS, encoding="utf-8")][: args.limit]

    model = tok = None
    if args.use_model:
        import torch
        from transformers import AutoModelForTokenClassification, AutoTokenizer
        from extract.extract_skills import DEVICE, predict_batch
        from extract.extract_skills import split_sentences

        tok = AutoTokenizer.from_pretrained(os.path.join(ROOT, "models", "jobskill-ner"))
        model = AutoModelForTokenClassification.from_pretrained(
            os.path.join(ROOT, "models", "jobskill-ner")).to(DEVICE).eval()

    counter: Counter = Counter()
    types: dict[str, Counter] = defaultdict(Counter)
    example: dict[str, str] = {}

    for k, j in enumerate(jobs, 1):
        text = f"{j['requirement']}\n{j['description']}"
        for sent in re.split(r"(?<=[。；;])\n?", text):
            sent = sent.strip()
            if not (6 <= len(sent) <= 200):
                continue
            covered = [(a, b) for a, b, *_ in trie_match(sent, trie)]
            cands = list(cue_candidates(sent, pseg))

            if model is not None:
                for st, en, lab, conf in predict_batch(model, tok, [sent])[0]:
                    if conf >= 0.6:
                        cands.append((sent[st:en], lab))

            for item in cands:
                cand = item if isinstance(item, str) else item[0]
                lab = "S" if isinstance(item, str) else item[1]
                cand = cand.strip(" 　，,、。；")
                if not (2 <= len(cand) <= 14) or cand in GENERIC or cand in STOP:
                    continue
                # 已被词表覆盖就不算缺口
                pos = sent.find(cand)
                if pos >= 0 and any(pos < b and a < pos + len(cand) for a, b in covered):
                    continue
                # 过滤：岗位标题里的词（角色名）不是技能；无技术特征的长中文串也不收
                if cand in j["title"]:
                    continue
                if FRAGMENT_RE.match(cand):
                    continue
                if not (ASCII_RE.search(cand) or any(cand.endswith(suf) for suf in SUFFIX)):
                    continue
                counter[cand] += 1
                types[cand][lab] += 1
                example.setdefault(cand, sent[:70])
        if k % 300 == 0:
            print(f"  {k}/{len(jobs)}", flush=True)

    rows = [(c, n) for c, n in counter.most_common() if n >= args.min_count]
    rows.sort(key=lambda x: -x[1])
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write("candidate\tcount\ttype\texample\n")
        for c, n in rows:
            t = types[c].most_common(1)[0][0]
            fh.write(f"{c}\t{n}\t{t}\t{example[c]}\n")

    print(f"\n候选 {len(rows)} 个（出现 ≥{args.min_count} 次），前 {args.top}：")
    for c, n in rows[: args.top]:
        print(f"  {n:5d}  [{types[c].most_common(1)[0][0]}] {c}")
    print(f"\n-> {OUT}")


if __name__ == "__main__":
    main()
