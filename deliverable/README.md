# JobSkill-KG：中文 IT/算法岗位—技能知识图谱

## 数据集简介

面向开放域中文招聘文本构建的岗位—技能知识图谱，覆盖算法、后端、前端客户端、运维安全、数据、测试、
MLOps 七个岗位族，数据来自企业官方招聘站公开岗位（字节跳动 3,576 / 网易 529 / 腾讯 799）。

岗位 4,904 个｜技能 390 项｜分类 12 个｜关系边 169,490 条；RDF 三元组 450,983 条｜平均 10.43 技能/岗。

## 构建方法

1. 数据：公开渠道采集，保留来源 URL 与抓取时间；原始 JD 不分发。
2. 抽取：410 条人工技术词表做字符级最长匹配（100 句 AI 标注参考集 exact F1=0.308，未经真人复核）；另在 Chinese-SkillSpan
   上微调中文 BERT 作为对照实验（同一 100 句参考集 exact F1 0.172），最终图谱以词表结果为主。
3. Schema：复用 cnSchema 的 JobPosting / Organization / Place / MonetaryAmount，扩展 21 个词
   （5 类 + 16 属性）；技能类型对齐 ESCO 的 LSKT 四维。

## 文件说明

`sample.jsonld` 样例｜`full.jsonld` 全量｜`ontology.ttl` / `ontology.jsonld` 本体｜
`context.jsonld` 上下文｜`nodes.csv` `edges.csv` Neo4j 导入｜`stats.json` 统计。
查询 API 见 `src/app/serve_api.py`，许可证 CC BY 4.0。
