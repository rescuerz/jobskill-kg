# OpenKG 提交前自查表（10 项）

> 拿到授权账号后，照着这张表从上往下点，约 15 分钟完成。
> 所有文件都在 `deliverable/`，字段文案可直接复制。

## 0. 文件就位检查

| 文件 | 大小 | 用途 | 校验 |
|---|---|---|---|
| `README.md` | 2.6 KB | 数据集页简介文案 | — |
| `sample.jsonld` | 305 KB | 样例数据（140 个岗位） | rdflib 解析 11,973 条三元组 ✓ |
| `full.jsonld` | 11.2 MB | 全量（4,865 个岗位） | rdflib 解析 **441,318 条三元组** ✓ |
| `ontology.ttl` | 5.6 KB | 本体 | rdflib 解析 110 条三元组 ✓ |
| `context.jsonld` | 1.6 KB | JSON-LD 上下文 | 已被上面两个文件引用 ✓ |
| `ontology.jsonld` | 11.6 KB | 本体的 JSON-LD 版（官方推荐格式） | rdflib 由 TTL 导出 ✓ |
| `nodes.csv` / `edges.csv` | 0.43 / 4.2 MB | Neo4j 导入 | 表头为 `:ID/:LABEL`、`:START_ID/:TYPE/:END_ID` ✓ |
| `stats.json` / `stats.md` | 4 KB | 规模统计 | — |

重新生成：`bash scripts/run_all.sh`

---

## 1. 账号权限

- [ ] 用授权邮箱登录 <http://data.openkg.cn/user/login>
- [ ] 页面能点到「增加数据集」（没有就找助教要 `个人` 机构的编辑权限）

## 2. 新建数据集：基础字段

| 字段 | 填什么 |
|---|---|
| 标题 | `中文 IT/算法岗位—技能知识图谱（JobSkill-KG）` |
| URL | 数据门户地址（见第 7 项） |
| 许可证 | `Creative Commons Attribution`（CC BY 4.0） |
| 机构 | `个人`（personal） |
| 分类 | `商业`（commerce） |
| 标签 | `招聘`、`技能`、`岗位`、`信息抽取`、`IT` |

- [ ] 六项已填，许可证与机构没选错

## 3. 简介（notes）

- [ ] 打开 `deliverable/README.md`，从「## 数据集简介」开始整段复制粘贴
      四段式：简介 / 构建方法 / 数据内容 / 应用，别只贴一句

## 4. 资源：逐个添加（6 项）

| 资源名（严格照写） | 上传文件 | 格式 |
|---|---|---|
| `样例数据` | sample.jsonld | JSON-LD |
| `数据下载（JSON-LD）` | full.jsonld | JSON-LD |
| `数据Schema` | ontology.ttl | TTL |
| `数据Schema（JSON-LD）` | ontology.jsonld | JSON-LD |
| `JSON-LD Context` | context.jsonld | JSON |
| `数据访问API` | `python3 src/app/serve_api.py` 启动，填 `/api/stats` 地址 | API |
| `Neo4j导入文件` | nodes.csv、edges.csv | CSV |
| `数据门户` | 站点 URL（链接类型） | HTML |

- [ ] 6 项齐全，命名与上表一致（OpenKG 页面靠资源名区分用途）

## 5. 文件大小与格式

- [ ] 单文件 < 1 GB：最大 `full.jsonld` 11.2 MB，无风险
- [ ] 上传后下载一次 `sample.jsonld`，确认不是 0 字节（CKAN 偶发上传失败）

## 6. 版权与合规声明

- [ ] 简介末尾保留这句：**原始招聘文本版权归原发布方，本数据集仅发布抽取后的结构化结果与脱敏样例**
- [ ] 没有上传任何原始 JD 全文（`data/raw/` 不进发布物）

## 7. 数据门户 URL

三选一，按可行性排序：

1. GitHub Pages：把仓库里的 `gh-pages/` 目录推到 `gh-pages` 分支（内含站点与数据下载），
   得到 `https://<user>.github.io/<repo>/`
2. 仓库 README 的 GitHub 链接（临时占位也能过审）
3. 校内可访问的静态页面

- [ ] 链接能在无痕窗口打开

## 8. 语义校验（已经做过，记一下结论即可）

- [ ] `sample.jsonld` / `full.jsonld` 都能被 rdflib 以 `format="json-ld"` 解析
- [ ] 谓词包含 `requiresSkill` / `skillType` / `inCategory` / `proficiency` / `necessity`
- [ ] `ontology.ttl` 里 13 个扩展词都有 `rdfs:label` 中英文与 `rdfs:comment`

## 9. 发布后回填

- [ ] 把数据集页 URL 写回 `jobskill-kg/README.md`、`docs/report.md`、`deliverable/README.md`
- [ ] 在 `docs/qa.md` 的 Q1 补一句「已发布，见 …」

## 10. 回馈社区（加分项）

- [ ] 到 <https://github.com/cnschema/cnSchema/issues> 提一个 issue：
      说明新增 `cns:Skill` / `cns:JobFamily` / `cns:SalaryRange` 等 13 个词的需求与设计
- [ ] issue 里附上本数据集页链接与 `ontology.ttl`

---

## 附：常见退回原因对照

| 退回原因 | 本项目的规避方式 |
|---|---|
| 简介只有一句话 | 四段式模板，约 1,200 字 |
| 只挂一个数据文件 | 6 个资源，含 Schema 与样例 |
| 许可证未选 | CC BY 4.0 |
| 文件超限 | 最大 11.2 MB |
| 机构选错 | 个人作业一律 `personal` |
| 无法访问数据门户 | 提供 GitHub Pages 或仓库链接 |
