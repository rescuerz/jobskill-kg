# v0.2 图谱约定

唯一权威本体为 schema/cns_jobskill.ttl。复用 schema.org 招聘、企业、地点等词汇，在 cnSchema 对应概念基础上扩展。仅有 cns 前缀不表示已经被 cnSchema 社区接收。

5 类：Skill、SkillCategory、JobFamily、SalaryRange、JobRequirement。16 个属性，包含新增 hasRequirement、forSkill、evidence。SalaryRange 等预留类没有当前数据实例，不能宣称完成薪资抽取。

JobPosting --hasRequirement--> JobRequirement --forSkill--> Skill --inCategory--> SkillCategory。
JobRequirement 的 proficiency 和 necessity 为该岗位对该技能的要求；共享 Skill 只承载名称、类型和分类。requiresSkill 是便捷投影。自定义对象属性使用 IRI 引用。

所有 4,904 条筛选岗位进入两种导出格式，包括 42 条无技能岗位。CSV 使用 Tab 分隔；properties 列 JSON 保存字面属性。JSON-LD 包含同样稳定 ID 与边。样例为每岗位族最多 20 条及其引用闭包。

节点数随要求节点增加，不能与旧版节点数直接当作知识覆盖提升比较。来源及偏移保存为 JSON 字符串 evidence，字段内字符位置从零开始，结束位置不含在片段内。公开包一般不含证据原句，三条演示岗位例外。
