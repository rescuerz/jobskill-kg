"""打包 OpenKG 发布物：deliverable/ 目录 + CKAN 元数据草稿。

产出：
    deliverable/README.md            数据集说明（OpenKG 页面正文可直接用）
    deliverable/sample.jsonld        每族 20 条样例
    deliverable/full.jsonld          全量三元组
    deliverable/ontology.ttl         本体
    deliverable/context.jsonld       JSON-LD context
    deliverable/stats.json / stats.md
    deliverable/ckan_metadata.json   OpenKG（CKAN）数据集元数据草稿
    deliverable/nodes.csv, edges.csv Neo4j 导入文件

用法：python3 src/build/package.py
"""
from __future__ import annotations

import json
import os
import shutil

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
KG = os.path.join(ROOT, "data", "kg")
SCHEMA = os.path.join(ROOT, "schema")
OUT = os.path.join(ROOT, "deliverable")


def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    stats = json.load(open(os.path.join(KG, "stats.json"), encoding="utf-8"))

    # 本体同时提供 JSON-LD 版本（OpenKG 推荐格式）
    try:
        from rdflib import Graph
        g = Graph()
        g.parse(os.path.join(SCHEMA, "cns_jobskill.ttl"), format="turtle")
        g.serialize(destination=os.path.join(SCHEMA, "ontology.jsonld"),
                    format="json-ld", indent=2, auto_compact=True)
    except Exception as exc:  # noqa: BLE001
        print("  ! 生成 ontology.jsonld 失败:", exc)

    for src, dst in [
        (os.path.join(KG, "sample.jsonld"), "sample.jsonld"),
        (os.path.join(KG, "full.jsonld"), "full.jsonld"),
        (os.path.join(SCHEMA, "ontology.jsonld"), "ontology.jsonld"),
        (os.path.join(KG, "nodes.csv"), "nodes.csv"),
        (os.path.join(KG, "edges.csv"), "edges.csv"),
        (os.path.join(KG, "stats.json"), "stats.json"),
        (os.path.join(SCHEMA, "cns_jobskill.ttl"), "ontology.ttl"),
        (os.path.join(SCHEMA, "context.jsonld"), "context.jsonld"),
    ]:
        if os.path.exists(src):
            shutil.copyfile(src, os.path.join(OUT, dst))

    fam = stats["by_family"]
    bc = stats["by_company"]
    comp = " / ".join(f"{k} {v:,}" for k, v in bc.items())
    n_lex = sum(1 for l in open(os.path.join(ROOT, "data", "lexicon", "tech_skills.txt"),
                                encoding="utf-8") if l.strip() and not l.startswith("#"))
    top = stats["top_skills"][:15]
    readme = f"""# JobSkill-KG：中文 IT/算法岗位—技能知识图谱

## 数据集简介

面向开放域中文招聘文本构建的岗位—技能知识图谱，覆盖算法、后端、前端客户端、运维安全、数据、测试、
MLOps 七个岗位族，数据来自企业官方招聘站公开岗位（{comp}）。

岗位 {stats['jobs']:,} 个｜技能 {stats['skills']} 项｜分类 12 个｜关系边 {stats['edges']:,} 条；RDF 三元组 {stats['rdf_triples']:,} 条｜平均 {stats['avg_skills_per_job']} 技能/岗。

## 构建方法

1. 数据：公开渠道采集，保留来源 URL 与抓取时间；原始 JD 不分发。
2. 抽取：{n_lex} 条人工技术词表做字符级最长匹配（100 句 AI 标注参考集 exact F1=0.308，未经真人复核）；另在 Chinese-SkillSpan
   上微调中文 BERT 作为对照实验（同一 100 句参考集 exact F1 0.172），最终图谱以词表结果为主。
3. Schema：复用 cnSchema 的 JobPosting / Organization / Place / MonetaryAmount，扩展 21 个词
   （5 类 + 16 属性）；技能类型对齐 ESCO 的 LSKT 四维。

## 文件说明

`sample.jsonld` 样例｜`full.jsonld` 全量｜`ontology.ttl` / `ontology.jsonld` 本体｜
`context.jsonld` 上下文｜`nodes.csv` `edges.csv` Neo4j 导入｜`stats.json` 统计。
查询 API 见 `src/app/serve_api.py`，许可证 CC BY 4.0。
"""
    open(os.path.join(OUT, "README.md"), "w", encoding="utf-8").write(readme)

    md = ["# JobSkill-KG 统计\n", f"- 岗位：{stats['jobs']:,}", f"- 技能：{stats['skills']:,}",
          f"- 关系边：{stats['edges']:,}；RDF 三元组：{stats['rdf_triples']:,}", f"- 平均技能/岗：{stats['avg_skills_per_job']}\n",
          "## 岗位族\n", "| 岗位族 | 岗位数 |", "|---|---|"]
    md += [f"| {k} | {v:,} |" for k, v in fam.items()]
    md += ["\n## 技能 Top 30\n", "| 技能 | 类型 | 岗位数 |", "|---|---|---|"]
    md += [f"| {x['skill']} | {x['type']} | {x['jobs']:,} |" for x in stats["top_skills"][:30]]
    open(os.path.join(OUT, "stats.md"), "w", encoding="utf-8").write("\n".join(md))

    ckan = {
        "name": "jobskill-kg",
        "title": "中文 IT/算法岗位—技能知识图谱（JobSkill-KG）",
        "notes": readme.split("## 数据集简介", 1)[-1].strip()[:1200],
        "license_id": "cc-by",
        "owner_org": "personal",
        "tags": [{"name": t} for t in ["招聘", "技能", "岗位", "知识图谱"]],
        "groups": [{"name": "commerce"}],
        "resources": [
            {"name": "样例数据（JSON-LD）", "format": "JSON-LD", "url": "TBD"},
            {"name": "数据下载（JSON-LD）", "format": "JSON-LD", "url": "TBD"},
            {"name": "数据Schema（TTL）", "format": "TTL", "url": "TBD"},
            {"name": "数据Schema（JSON-LD）", "format": "JSON-LD", "url": "TBD"},
            {"name": "JSON-LD Context", "format": "JSON", "url": "TBD"},
            {"name": "数据访问API", "format": "API", "url": "TBD"},
            {"name": "Neo4j 导入文件", "format": "CSV", "url": "TBD"},
            {"name": "数据门户", "format": "HTML", "url": "TBD"},
        ],
    }
    json.dump(ckan, open(os.path.join(OUT, "ckan_metadata.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)

    sizes = {f: os.path.getsize(os.path.join(OUT, f)) for f in sorted(os.listdir(OUT))}
    for f, s in sizes.items():
        print(f"  {f:24s} {s / 1024:8.1f} KB")
    print("->", OUT)


if __name__ == "__main__":
    main()
