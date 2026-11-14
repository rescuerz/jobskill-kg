# OpenKG 发布操作手册（JobSkill-KG）

> 依据 openkg.cn 官方流程整理，配合 `deliverable/` 目录使用。
> 动手提交时用更精简的 [submission_checklist.md](submission_checklist.md)（10 项自查表）；
> 本文保留完整流程与背景说明。

## 一、前置：账号与权限

| 步骤 | 操作 | 说明 |
|---|---|---|
| 1 | <http://openkg.cn/register/> 注册普通用户 | 即时生效，只能浏览下载 |
| 2 | <http://openkg.cn/personal-form/> 提交「个人发布申请」 | 审核 3–5 个工作日，授权邮件发到填写的邮箱 |
| 3 | 收到授权后登录 <http://data.openkg.cn/user/login> | 若原账号未升级，按邮件提示操作 |

> 邮件里写的授权账号与普通账号**用同一邮箱**即可对应；`https` 证书已过期，用 `http`。

## 二、发布前要准备的 6 个文件

| 文件 | 来源 | 说明 |
|---|---|---|
| `README.md` | `deliverable/README.md` | 数据集简介，可直接粘进 CKAN 的 notes |
| `sample.jsonld` | 自动生成 | 每族 ≤20 条脱敏样例 |
| `full.jsonld` | 自动生成 | 全量三元组 |
| `ontology.ttl` | `schema/cns_jobskill.ttl` | 本体 |
| `context.jsonld` | `schema/context.jsonld` | JSON-LD 上下文 |
| `nodes.csv` / `edges.csv` | 自动生成 | Neo4j 导入文件 |

生成命令：

```bash
PYTHONPATH=.pkgs:src python3 src/build/build_kg.py
PYTHONPATH=.pkgs:src python3 src/build/package.py
```

## 三、创建数据集（data.openkg.cn）

1. 登录后确认账号有「增加数据集」权限；没有就找助教要到 `个人` 机构的编辑权限。
2. 点「增加数据集」，按下表填元数据：

| 字段 | 填什么 |
|---|---|
| 标题 | 中文 IT/算法岗位—技能知识图谱（JobSkill-KG） |
| URL | 数据门户地址（GitHub Pages / 演示站点，可先留空后补） |
| 许可证 | Creative Commons Attribution（CC BY 4.0） |
| 机构 | 个人（personal） |
| 分类 | 商业（commerce） |
| 标签 | 招聘、技能、岗位、信息抽取、IT |
| 简介 | 粘贴 `deliverable/README.md` 正文（四段式：简介/构建方法/数据内容/应用） |

3. 「下一步：添加数据」，依次加资源（名称严格按官方示例）：

| 资源名 | 文件 | 格式 |
|---|---|---|
| 样例数据 | sample.jsonld | JSON-LD |
| 数据下载（JSON-LD） | full.jsonld | JSON-LD |
| 数据Schema | ontology.ttl | TTL |
| JSON-LD Context | context.jsonld | JSON |
| Neo4j导入文件 | nodes.csv + edges.csv | CSV |
| 数据门户 | 站点 URL | HTML |
| 数据访问API | （可选）检索服务 URL | URL |

4. 保存后把页面链接填进 `deliverable/README.md` 与报告。

## 四、常见退回原因

| 原因 | 规避 |
|---|---|
| 简介只有一句话，看不出资源内容 | 用四段式模板 |
| 只挂了一个数据文件，没有 Schema/样例 | 至少 4 个资源 |
| 许可证没填 | 选 CC BY 4.0 |
| 文件太大（>1GB） | 当前 full.jsonld 约 7.5 MB，无风险 |
| 机构选错（机构表单 vs 个人表单） | 个人作业一律走 `personal` |

## 五、发布后

- 在 README 与报告中引用数据集页 URL
- 若后续更新数据，直接在数据集页「编辑」追加资源，版本号写进简介
- 把本体扩展提成 cnSchema 的 issue（<https://github.com/cnschema/cnSchema/issues>），说明新增的 18 个词（5 类 + 13 属性）与理由
