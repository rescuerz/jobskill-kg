# 标注规范 v1（技能 span + 岗位字段）

> 适用范围：JobSkill-KG 项目的全部人工标注（gold 集、抽检、仲裁）。
> 本规范在 [Chinese-SkillSpan Guideline](https://sites.google.com/view/cn-skillspan-resources)（ESCO-LKST 中文标注规范）基础上裁剪与本地化，特此致谢。

---

## 1. 标什么、不标什么

**标注区**：岗位职责（`description`）与任职要求（`requirement`）两段正文。

**不标注**：

| 类型 | 例子 | 处理 |
|---|---|---|
| 岗位标题 | "算法工程师（NLP方向）" | 单独作为 `title` 字段，不标 span |
| 待遇/福利 | "六险一金、免费三餐、弹性工作" | 不标 |
| 年龄/性别/班次 | "35 岁以下""接受倒班" | 不标 |
| 口号/公司介绍 | "我们是一支年轻有激情的团队" | 不标 |
| 纯学历/年限 | "本科及以上""3 年以上经验" | 不标 span，走 §5 结构化字段 |

---

## 2. 四类标签（LSKT，对齐 ESCO）

| 标签 | 含义 | 判定问句 | 例子 |
|---|---|---|---|
| **L** Language | 自然语言能力/等级/证书 | 这是不是"语言"？ | 英语六级、日语 N2、普通话二甲、能用英文撰写文档 |
| **S** Skill | 可执行的技能动作/工具使用 | 能不能"做"出来？ | 用 PyTorch 训练模型、SQL 调优、Kubernetes 集群运维 |
| **K** Knowledge | 知识、理论、标准、资格 | 是不是"知道/持有"？ | 机器学习、TCP/IP、ISO 27001、PMP 证书 |
| **T** Transversal | 通用/软能力 | 是不是跨岗位的素质？ | 沟通协调能力、抗压能力、结果导向 |

**兜底优先级：L > S > K > T**（先判语境，仍不确定时按此顺序落位）。

> ⚠️ 编程语言（Python/Java/Go）属于 **K**（知识/工具实体），不是 L。L 只给自然语言。

---

## 3. 边界规则

1. **最小且语义充分**：取"单独拿出来仍能判断类别"的最短连续片段。
   - ✅ `数据可视化` ✅ `模型部署`　❌ `进行` ❌ `相关`
2. **去虚词**：删掉"能够/熟练/较强的/开展/相关/其/请"等。
   - "能够熟练地进行数据可视化" → `数据可视化`
3. **并列可拆，但不硬拆**：", / 、 / 和 / or" 连接且各自独立的才拆。
   - "设计数据模型、搭建指标体系、出具分析报告" → 三个 S
4. **不嵌套、不重叠**：同一句可有多个 span，但不得相交。
5. **版本号不入段**："Python 3.11、MySQL 8" → `Python`、`MySQL`
6. **偏移量**：起点从 0 开始、终点右开（与 Doccano 一致），span 必须是原文的连续子串，禁止拼接。

---

## 4. 冲突裁决（高频，必须背下来）

| 冲突 | 规则 | 例子 |
|---|---|---|
| K vs S | 执行/产出/落地 → S；作为实体/标准被"了解" → K；仍不确定优先 S | "熟悉通信协议"→`通信协议`(K)；"制定视觉流程"→`视觉流程制定`(S) |
| L vs S | 语言能力/等级/证书 → L；用语言去沟通写作 → S（可拆两段） | "用英语与海外客户邮件沟通"→`英语`(L)+`邮件沟通`(S) |
| L vs K | 自然语言 → L；编程语言证书 → K | "英语六级"→L；"OCJP-Java 认证"→K |
| T vs S | 可执行行为 → S；笼统素质 → T | "主动沟通协调"→S；"具备沟通能力"→T |
| S 内含 K 对象 | 只保留 S，不重复标 K | "按 ISO 9001 开展审核"→整段 S |
| T + 具体动作 | 落 S | "结果导向地提升转化率"→`提升转化率`(S) |

---

## 5. 结构化字段（span 之外，单独标）

| 字段 | 取值 | 规则 |
|---|---|---|
| `job_family` | 算法 / 数据 / 后端 / 前端客户端 / 测试 / 运维安全 / MLOps / 其他 | 按岗位职责主体判定，不看标题 |
| `education_level` | 不限 / 大专 / 本科 / 硕士 / 博士 | "本科及以上"→本科；多个取最高 |
| `experience_years` | 不限 / 应届 / 1-3 / 3-5 / 5-10 / 10+ | "3-5 年"→3-5；"经验不限"→不限 |
| `salary` | `{min,max,months}` 单位 k/月 | "15-25K·14薪"→{15,25,14}；"面议"→空 |
| `skill_proficiency` | 了解 / 熟悉 / 精通 | 原文未提→熟悉 |
| `skill_necessity` | 必备 / 加分 | "优先/加分/有…者优先"→加分；其余→必备 |

---

## 6. 质量与仲裁

- **双人独立标注**，抽样 10% 做三标仲裁
- **一致性门槛**：span 级 Cohen's Kappa ≥ 0.80（按精确匹配算）
- **争议记录**：每条争议写进 `eval/disputes.jsonl`，附最终裁定与理由，规范每两周迭代一版
- **验收样本**：500 条，其中 100 条为跨企业难例（长句、否定句、嵌套技能）

---

## 7. 标注格式

输出 JSONL，一行一条：

```json
{
  "doc_id": "netease:59824",
  "text": "……原文……",
  "spans": [
    {"start": 12, "end": 20, "text": "数据可视化", "label": "S"},
    {"start": 31, "end": 36, "text": "Python", "label": "K"}
  ],
  "fields": {
    "job_family": "数据",
    "education_level": "本科",
    "experience_years": "3-5",
    "salary": {"min": 15, "max": 25, "months": 14}
  }
}
```

工具：Doccano（span 标注）或 Label Studio；导出后统一转上述格式。

---

## 8. 域内复核包（评测用）

`eval/domain_review.jsonl` 已从 4,904 条岗位里抽了 100 句（70 句带技能线索词 + 30 句随机），
每句附词典预标结果。当前已由 LLM 按本规范标注一版（`status=reviewed`、`annotator=llm-assisted`，
属 silver 数据，未经人工复核），可直接复算；人工复核后把标注改掉即可升级为 gold。

复核步骤：

1. 逐条读 `text`，把 `spans` 改成你认可的标注（格式 `{start,end,text,label}`，可增删）；
2. `status` 改成 `reviewed`；
3. 跑评测：

```bash
PYTHONPATH=.pkgs python3 src/extract/eval_domain.py
```

输出 `eval/domain_report.json`，给出域内 exact / relaxed 的 P/R/F1，与跨域结果（§7.1）互为补充。
预标只作为起点，**以你的判断为准**：删掉不成立的、补上漏掉的，才是有效 gold。

## 9. 参考

- Chinese-SkillSpan: *A Span-Level Dataset for ESCO-Aligned Competency Extraction from Chinese Job Ads*, arXiv:2604.23009
- ESCO 技能分类：<https://esco.ec.europa.eu/>
- cnSchema 4.0：<https://github.com/cnschema/cnSchema>
