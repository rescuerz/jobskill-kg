# cnSchema 扩展说明（JobSkill-KG v0.1）

本体的两个文件：

- [`cns_jobskill.ttl`](cns_jobskill.ttl)：OWL/Turtle 定义
- [`context.jsonld`](context.jsonld)：导出 JSON-LD 时使用的 `@context`

命名空间：`http://data.openkg.cn/dataset/jobskill-kg#`（数据集发布后即为可解析地址）

## 一、复用的 cnSchema / schema.org 词汇（9 个）

| 词汇 | cnSchema 中文标签 | 在本体中的用途 |
|---|---|---|
| `schema:JobPosting` | 招聘信息 | 岗位主实体 |
| `schema:Occupation` | 职业 | 岗位与职业分类的桥接 |
| `schema:Organization` | 组织 | 招聘企业 |
| `schema:Place` / `schema:PostalAddress` | 地点 / 邮政地址 | 工作城市 |
| `schema:MonetaryAmount` | 金额 | 薪酬区间的父类 |
| `schema:EducationalOccupationalProgram` | 教育职业项目 | 校招/培养项目（预留） |
| `schema:Demand` | 需求 | 岗位需求（预留） |
| `schema:title` / `schema:name` | 标题 / 名称 | 岗位名、技能名 |
| `schema:datePosted` | 发布日期 | 岗位发布时间 |

## 二、新增的类与属性（18 个：5 个类 + 13 个属性）

| 名称 | 类型 | 父类 / domain → range | 为什么 schema.org 不够 |
|---|---|---|---|
| `cns:Skill` | 类 | `schema:Thing` | schema.org 只有 `knowsAbout` 属性，无法承载技能的类型、等级、必要性；技能需要独立标识以便跨岗位复用与归一 |
| `cns:SkillCategory` | 类 | `schema:Thing` | 技能需要分类树（编程语言/框架/数据库/证书）才能做聚合统计 |
| `cns:JobFamily` | 类 | `schema:Thing` | `schema:Occupation` 粒度偏粗且偏"职业"，岗位族用于按族统计与推荐 |
| `cns:SalaryRange` | 类 | `schema:MonetaryAmount` | 招聘薪资是"区间 + 薪数"（15–25K·14 薪），单一 `value` 表达不了 |
| `cns:JobRequirement` | 类 | `schema:Thing` | 把学历/经验/专业/证书组织成可复用节点，便于跨岗位比较 |
| `cns:requiresSkill` | 属性 | `JobPosting → Skill` | 需要携带 `proficiency`/`necessity` 修饰，不能复用 `schema:skills`（纯文本） |
| `cns:belongsToFamily` | 属性 | `JobPosting → JobFamily` | — |
| `cns:hasSalaryRange` | 属性 | `JobPosting → SalaryRange` | — |
| `cns:inCategory` | 属性 | `Skill → SkillCategory` | — |
| `cns:skillType` | 属性 | `Skill → xsd:string` | 取值 K/S/T/L，对齐 ESCO 四维 |
| `cns:proficiency` | 属性 | `Skill → xsd:string` | 了解/熟悉/精通 |
| `cns:necessity` | 属性 | `Skill → xsd:string` | 必备/加分 |

| `cns:escoCode` | 属性 | `Skill → xsd:string` | 与 ESCO 技能概念对齐的编号，用于跨标准互操作 |
| `cns:educationLevel` | 属性 | `JobPosting → xsd:string` | 学历要求（不限/大专/本科/硕士/博士） |
| `cns:experienceYears` | 属性 | `JobPosting → xsd:string` | 经验要求（应届/1-3/3-5/5-10/10+） |
| `cns:monthlyMin` | 属性 | `SalaryRange → xsd:decimal` | 月薪下限（k） |
| `cns:monthlyMax` | 属性 | `SalaryRange → xsd:decimal` | 月薪上限（k） |
| `cns:salaryMonths` | 属性 | `SalaryRange → xsd:integer` | 年薪月数（13/14/15 薪） |

## 三、设计原则

1. **能复用就不新增**：先查 cnSchema 4.0 是否有对应词，没有再扩。
2. **每个新增都要能回答"为什么不够"**：上表第三列即答辩口径。
3. **命名规范**：类用大驼峰英文、属性用 lowerCamel；每个词给 `rdfs:label` 中英文 + `rdfs:comment`。
4. **可回馈社区**：扩展定稿后向 [cnschema/cnSchema](https://github.com/cnschema/cnSchema) 提 issue，说明需求与设计。

## 四、对齐 ESCO

`cns:Skill` 的 `skillType` 采用 ESCO 的 LSKT 四维：

- **K** Knowledge：知识/理论/标准（如"机器学习""ISO 27001"）
- **S** Skill：可执行的技能动作（如"用 PyTorch 训练模型"）
- **T** Transversal：通用能力（如"沟通协调能力"）
- **L** Language：语言能力与等级（如"英语六级""日语 N2"）

这样标注体系可直接与 [Chinese-SkillSpan](https://arxiv.org/abs/2604.23009) 的 gold 数据对齐，评测结果具备可比性。
