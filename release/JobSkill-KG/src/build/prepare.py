"""把 raw/*.jsonl 清洗成岗位级语料，并做岗位族归类与字段抽取。

用法：
    PYTHONPATH=.pkgs:src python3 src/build/prepare.py

输出：
    data/processed/jobs.jsonl      每条 = 一个岗位（含 job_family / education / experience）
    data/processed/stats.json      语料统计
"""
from __future__ import annotations

import glob
import json
import os
import re
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RAW = os.path.join(ROOT, "data", "raw")
OUT_DIR = os.path.join(ROOT, "data", "processed")

# 岗位族规则：先按标题匹配，标题不中再看正文
FAMILY_RULES = [
    ("算法", ["算法", "机器学习", "深度学习", "nlp", "自然语言", "计算机视觉", "cv工程",
              "推荐", "搜索", "大模型", "llm", "语音", "图像", "多模态", "aigc", "强化学习"]),
    ("数据", ["数据分析", "数据开发", "数据仓库", "数仓", "数据挖掘", "数据科学", "bi工程",
              "etl", "数据治理", "指标体系", "数据产品"]),
    ("后端", ["后端", "服务端", "java开发", "go开发", "c++开发", "架构师", "微服务",
              "分布式", "中间件", "数据库内核", "基础架构"]),
    ("前端客户端", ["前端", "客户端", "ios", "android", "web开发", "react", "vue",
                    "小程序", "跨端", "flutter"]),
    ("测试", ["测试开发", "自动化测试", "性能测试", "qa", "测试工程师", "质量保障"]),
    ("运维安全", ["运维", "sre", "安全", "渗透", "风控", "dba", "网络工程",
                  "云计算", "基础设施", "devops"]),
    ("MLOps", ["mlops", "算法工程", "推理优化", "模型部署", "训练框架", "平台工程",
               "高性能计算", "cuda"]),
]

# 明确排除的岗位（非 IT）
EXCLUDE = ["游戏策划", "游戏美术", "原画", "ui设计", "视觉设计", "市场", "销售", "运营",
           "人力资源", "财务", "法务", "行政", "采购", "供应链", "公关", "品牌", "产品经理",
           "产品运营", "用户研究", "内容运营", "编辑"]

# 招聘站点自己的岗位大类：命中即排除（产品/设计岗常因正文提到 AI 被误判为算法岗）
NON_IT_CATEGORY = ["产品", "设计", "市场", "销售", "运营", "人力资源", "职能", "游戏策划",
                   "游戏艺术", "内容", "战略", "营销", "公关", "法务", "财务", "行政"]

# 技术类大类（正文兜底归类只在这些大类里放行）
TECH_CATEGORY = ["技术", "程序", "研发", "数据", "算法", "测试", "运维", "安全", "工程", "开发"]

# 标题里出现这些强技术信号，即使站点把它归到"产品/运营"大类也保留（如数据分析师）
TECH_TITLE_RE = re.compile(
    r"(数据分析|数据开发|数据挖掘|数据科学|算法工程师|机器学习|深度学习|自然语言|计算机视觉|"
    r"大模型|NLP|推荐算法|搜索算法|后端|服务端|前端|客户端|测试开发|运维|SRE|安全工程师|"
    r"Java|Golang|C\+\+|Python开发|架构师|全栈|嵌入式|音视频|图形|引擎|基础架构)")

EDU_RE = re.compile(r"(博士|硕士|研究生|本科|大专|专科)")
EXP_RE = re.compile(r"(应届|经验不限|不限经验|\d+\s*[-~—至到]\s*\d+\s*年|\d+\s*年以上)")
SALARY_RE = re.compile(
    r"(\d+(?:\.\d+)?)\s*[-~—至]\s*(\d+(?:\.\d+)?)\s*([kK千万])\s*(?:[·xX*×]\s*(\d+)\s*薪)?"
)


def norm_city(c: str) -> str:
    return re.sub(r"(市|省|自治区|特别行政区)$", "", (c or "").strip())


def classify(title: str, body: str) -> str:
    t = (title or "").lower()
    for fam, kws in FAMILY_RULES:
        if any(k in t for k in kws):
            return fam
    b = (body or "").lower()
    for fam, kws in FAMILY_RULES:
        if any(k in b for k in kws):
            return fam
    return "其他"


def is_excluded(title: str) -> bool:
    t = (title or "").lower()
    return any(k in t for k in EXCLUDE)


def parse_education(text: str) -> str:
    hits = EDU_RE.findall(text or "")
    order = ["博士", "硕士", "研究生", "本科", "大专", "专科"]
    for o in order:
        if o in hits:
            return "硕士" if o == "研究生" else ("大专" if o == "专科" else o)
    return "不限"


def parse_experience(text: str) -> str:
    m = EXP_RE.search(text or "")
    if not m:
        return "不限"
    s = m.group(1).replace(" ", "")
    if s in ("应届",):
        return "应届"
    if "不限" in s:
        return "不限"
    nums = [int(x) for x in re.findall(r"\d+", s)]
    if not nums:
        return "不限"
    if "以上" in s:
        return "10年以上" if nums[0] >= 10 else f"{nums[0]}年以上"
    lo = nums[0]
    for label, (a, b) in {"1-3": (1, 3), "3-5": (3, 5), "5-10": (5, 10)}.items():
        if a <= lo < b:
            return label
    return "不限"


def parse_salary(text: str):
    m = SALARY_RE.search(text or "")
    if not m:
        return None
    lo, hi, unit, months = m.groups()
    lo, hi = float(lo), float(hi)
    if unit == "万":
        lo, hi = lo * 10, hi * 10  # 万元/月 → k/月
    elif unit == "千":
        pass
    return {"min": lo, "max": hi, "months": int(months) if months else 12}


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    seen_hash: set[str] = set()
    rows = []
    for path in sorted(glob.glob(os.path.join(RAW, "*.jsonl"))):
        n = 0
        for line in open(path, encoding="utf-8"):
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            n += 1
            if r["content_sha256"] in seen_hash:
                continue
            if is_excluded(r["title"]):
                continue
            cat = r.get("category") or ""
            strong_title = bool(TECH_TITLE_RE.search(r["title"]))
            if any(k in cat for k in NON_IT_CATEGORY) and not strong_title:
                continue
            body = f"{r['description']}\n{r['requirement']}"
            if len(body) < 40:  # 正文太短，抽不出东西
                continue
            fam = classify(r["title"], body)
            if fam == "其他":
                # 正文兜底只对技术大类放行，避免产品/策划岗混入
                if any(k in cat for k in TECH_CATEGORY):
                    fam = classify("", body)
                if fam == "其他":
                    continue
            seen_hash.add(r["content_sha256"])
            r["job_family"] = fam
            r["education_level"] = parse_education(r["requirement"] or body)
            r["experience_years"] = parse_experience(r["requirement"] or body) or "不限"
            r["salary"] = parse_salary(f"{r['title']}\n{body}")
            r["locations"] = [norm_city(c) for c in r["locations"] if c]
            rows.append(r)
        print(f"{os.path.basename(path)}: {n} 条 -> 累计入池 {len(rows)}")

    out = os.path.join(OUT_DIR, "jobs.jsonl")
    with open(out, "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    stats = {
        "jobs": len(rows),
        "by_source": dict(Counter(r["source"] for r in rows)),
        "by_family": dict(Counter(r["job_family"] for r in rows).most_common()),
        "by_city": dict(Counter(c for r in rows for c in r["locations"]).most_common(15)),
        "by_education": dict(Counter(r["education_level"] for r in rows).most_common()),
        "by_experience": dict(Counter(r["experience_years"] for r in rows).most_common()),
        "with_salary": sum(1 for r in rows if r.get("salary")),
        "avg_body_len": round(sum(len(r["description"]) + len(r["requirement"]) for r in rows) / max(1, len(rows)), 1),
    }
    with open(os.path.join(OUT_DIR, "stats.json"), "w", encoding="utf-8") as fh:
        json.dump(stats, fh, ensure_ascii=False, indent=2)
    print(json.dumps(stats, ensure_ascii=False, indent=2))
    print(f"-> {out}")


if __name__ == "__main__":
    main()
