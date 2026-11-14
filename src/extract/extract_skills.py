"""从岗位文本中抽取技能 span：NER 模型 + 词典匹配融合，并推断等级/必要性。

输入：data/processed/jobs.jsonl
输出：data/processed/job_skills.jsonl
     {"doc_id", "job_family", "skills":[{text,label,start,end,confidence,proficiency,necessity,source}]}

用法：
    PYTHONPATH=.pkgs python3 src/extract/extract_skills.py [--limit N]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

import torch
from transformers import AutoModelForTokenClassification, AutoTokenizer

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "src"))

from extract.train_ner import ID2LABEL, tags_to_spans  # noqa: E402

JOBS = os.path.join(ROOT, "data", "processed", "jobs.jsonl")
LEX = os.path.join(ROOT, "data", "lexicon", "skill_lexicon.tsv")
CURATED = os.path.join(ROOT, "data", "lexicon", "tech_skills.txt")
OUT = os.path.join(ROOT, "data", "processed", "job_skills.jsonl")
MODEL = os.path.join(ROOT, "models", "jobskill-ner")

DEVICE = torch.device("mps" if torch.backends.mps.is_available() else "cpu")

# 过于泛化的动作词，作为技能没有区分度
GENERIC = {
    "开发", "设计", "分析", "管理", "维护", "优化", "研发", "制定", "研究", "协调", "支持",
    "测试", "监控", "部署", "实施", "培训", "评估", "规划", "推动", "落地", "搭建", "负责",
    "参与", "完成", "推进", "保障", "提升", "改善", "处理", "解决", "编写", "撰写", "整理",
    "收集", "学习", "跟进", "对接", "梳理", "输出", "交付", "运营", "建设", "开展", "执行",
}

PROF_PAT = [
    (re.compile(r"(精通|深入理解|深刻理解|专家级)"), "精通"),
    (re.compile(r"(熟练掌握|熟练使用|熟练|熟悉|掌握|会用|能使用)"), "熟悉"),
    (re.compile(r"(了解|接触过|略有了解)"), "了解"),
]
NEC_PAT = [
    (re.compile(r"(优先|加分|plus|更佳|者优先)"), "加分"),
    (re.compile(r"(必须|要求|至少|需具备|必备|硬性)"), "必备"),
]


def split_sentences(text: str) -> list[str]:
    parts = re.split(r"[。；;\n①②③④⑤⑥⑦⑧⑨⑩]", text)
    return [p.strip(" ，,、·-—") for p in parts if len(p.strip()) >= 4]


def load_lexicon(use_mined: bool = False) -> list[tuple[str, str, int, float]]:
    """两层词典：

    1) 人工整理的技术词表（高精度，conf 0.98）
    2) 从 gold 标注挖出来的词表（只保留 >=4 字或高频的，conf 0.8）
    返回 [(surface, type, count, conf)]，按长度降序便于最长匹配。
    """
    items = []
    seen = set()
    if os.path.exists(CURATED):
        for line in open(CURATED, encoding="utf-8"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            cols = line.split("\t")
            surface, typ = cols[0].strip(), (cols[1].strip() if len(cols) > 1 else "S")
            if len(surface) < 2 or surface in seen:
                continue
            seen.add(surface)
            items.append((surface, typ, 99, 0.98))

    if not use_mined:
        items.sort(key=lambda x: -len(x[0]))
        return items

    for line in open(LEX, encoding="utf-8").read().splitlines()[1:]:
        cols = line.split("\t")
        if len(cols) < 4:
            continue
        surface, typ, cnt = cols[0], cols[1], int(cols[2])
        if surface in seen or surface in GENERIC:
            continue
        if len(surface) < 4 and cnt < 3:   # 短词必须是高频真词
            continue
        if len(surface) < 3:
            continue
        seen.add(surface)
        items.append((surface, typ, cnt, 0.8))
    items.sort(key=lambda x: -len(x[0]))
    return items


def build_trie(items):
    """把词典建成字符 trie，实现句子级最长匹配（避免 7000×20000 的暴力 in 检查）。"""
    trie: dict = {}
    for surface, typ, cnt, _conf in items:
        node = trie
        for ch in surface:
            node = node.setdefault(ch, {})
        node["$"] = (surface, typ, cnt, _conf)
    return trie


def trie_match(sent: str, trie: dict):
    """返回 [(start, end, (surface, type, count))]，贪心最长、不重叠。"""
    out = []
    i, n = 0, len(sent)
    while i < n:
        node = trie
        j = i
        best = None
        while j < n and sent[j] in node:
            node = node[sent[j]]
            j += 1
            if "$" in node:
                best = (i, j, node["$"])
        if best:
            out.append(best)
            i = best[1]
        else:
            i += 1
    return out


TRIM_CHARS = "的和及与等或并其了着对把为以用途"


def clean_span(sent: str, start: int, end: int):
    """裁掉模型预测片段两端的虚词/连接词，返回新的 (start, end, text)；过短返回 None。"""
    while start < end and sent[start] in TRIM_CHARS:
        start += 1
    while end > start and sent[end - 1] in TRIM_CHARS:
        end -= 1
    text = sent[start:end].strip()
    if len(text) < 2 or len(text) > 20:
        return None
    return start, end, text


def context_window(sent: str, start: int, end: int, w: int = 12) -> str:
    return sent[max(0, start - w) : start] + "|" + sent[end : end + w]


def infer_modifiers(ctx: str) -> tuple[str, str]:
    left = ctx.split("|")[0]
    prof = "熟悉"
    for pat, val in PROF_PAT:
        if pat.search(left[-8:] if len(left) > 8 else left):
            prof = val
            break
    nec = "必备"
    for pat, val in NEC_PAT:
        if pat.search(ctx):
            nec = val
            break
    return prof, nec


@torch.no_grad()
def predict_batch(model, tok, sents: list[str], max_len: int = 128):
    """按 offset_mapping 对齐到字符（不能用 token 序号直接当字符下标）。"""
    enc = tok(
        sents,
        max_length=max_len,
        truncation=True,
        padding=True,
        return_offsets_mapping=True,
        return_tensors="pt",
    )
    offsets = enc.pop("offset_mapping")
    enc = {k: v.to(DEVICE) for k, v in enc.items()}
    logits = model(**enc).logits
    probs = torch.softmax(logits, dim=-1).max(-1).values.cpu()
    ids = logits.argmax(-1).cpu()
    out = []
    for i, sent in enumerate(sents):
        tags = ["O"] * len(sent)
        conf = [0.0] * len(sent)
        for (s0, e0), lid, pb in zip(offsets[i].tolist(), ids[i].tolist(), probs[i].tolist()):
            if e0 <= s0:
                continue
            lab = ID2LABEL[lid]
            for k in range(s0, min(e0, len(sent))):
                tags[k] = lab
                conf[k] = pb
        spans = []
        for st, en, lab in tags_to_spans(tags):
            c = sum(conf[st:en]) / max(1, en - st)
            spans.append((st, en, lab, c))
        out.append(spans)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--batch", type=int, default=64)
    ap.add_argument("--use-model", action="store_true",
                    help="把微调 BERT 的预测也并入（默认关闭：模型边界噪声大，KG 以词典为主）")
    ap.add_argument("--no-model", action="store_true")
    ap.add_argument("--mined", action="store_true", help="把 gold 挖出的词表也并入（噪声大，默认关闭）")
    args = ap.parse_args()

    use_model = args.use_model and not args.no_model
    if not use_model:
        tok, model = None, None
    else:
        tok = AutoTokenizer.from_pretrained(MODEL)
        model = AutoModelForTokenClassification.from_pretrained(MODEL).to(DEVICE).eval()
    lex = load_lexicon(use_mined=args.mined)
    trie = build_trie(lex)
    print(f"词典 {len(lex)} 条，model={'on' if use_model else 'off'}，device={DEVICE}", flush=True)

    jobs = [json.loads(l) for l in open(JOBS, encoding="utf-8")]
    if args.limit:
        jobs = jobs[: args.limit]

    n_out = 0
    total_skills = 0
    with open(OUT, "w", encoding="utf-8") as fh:
        for ji, job in enumerate(jobs):
            text = f"{job['description']}\n{job['requirement']}"
            sents = split_sentences(text)
            if not sents:
                continue
            preds = predict_batch(model, tok, sents, max_len=128) if use_model else [[] for _ in sents]

            found = {}
            for sent, spans in zip(sents, preds):
                # 1) 模型预测
                for s, e, lab, pconf in spans:
                    cleaned = clean_span(sent, s, e)
                    if not cleaned:
                        continue
                    s, e, stext = cleaned
                    if pconf < 0.85 or stext in GENERIC:
                        continue
                    key = (stext, lab)
                    prof, nec = infer_modifiers(context_window(sent, s, e))
                    cand = {"text": stext, "label": lab, "confidence": round(float(0.4 + 0.5 * pconf), 3),
                            "proficiency": prof, "necessity": nec, "source": "model"}
                    old = found.get(key)
                    if not old or cand["confidence"] > old["confidence"]:
                        found[key] = cand
                # 2) 词典最长匹配
                for idx, end, (surface, typ, cnt, conf) in trie_match(sent, trie):
                    prof, nec = infer_modifiers(context_window(sent, idx, end))
                    c = conf
                    key = (surface, typ)
                    old = found.get(key)
                    cand = {"text": surface, "label": typ, "confidence": c,
                            "proficiency": prof, "necessity": nec, "source": "lexicon"}
                    if not old or c > old["confidence"]:
                        found[key] = cand
            skills = list(found.values())
            total_skills += len(skills)
            fh.write(json.dumps({"doc_id": job["doc_id"], "job_family": job["job_family"],
                                 "skills": skills}, ensure_ascii=False) + "\n")
            n_out += 1
            if (ji + 1) % 200 == 0:
                print(f"  {ji + 1}/{len(jobs)} docs, {total_skills} skills", flush=True)

    print(f"完成 {n_out} 个岗位，共 {total_skills} 个技能提及，平均 {total_skills / max(1, n_out):.1f} 个/岗")
    print("->", OUT)


if __name__ == "__main__":
    main()
