# 由用户执行的 GitHub 发布

本目录是可公开的 JobSkill-KG v0.2 仓库内容。新建仓库名为 JobSkill-KG，目标为 rescuerz/JobSkill-KG。本轮不发布 OpenKG。

若使用 GitHub CLI，进入这个发布目录后执行：

```bash
gh auth login
git init -b main
git add .
git commit -m "Publish JobSkill-KG v0.2 with evidence queries and reference evaluation"
gh repo create rescuerz/JobSkill-KG --public --source=. --remote=origin --push
```

不要在包含原始数据和模型的开发目录直接执行 `git add .`。如果已经创建同名仓库，改为添加该仓库为 remote 并推送，不重复创建。

发布后匿名核验：

```bash
python3 scripts/verify_publication.py --repo rescuerz/JobSkill-KG
```

该命令检查公开状态、默认分支、README、全量数据包、评测报告和 API 源码的下载哈希。真正执行成功后才可称“已核验公开发布”。本地验收不等于已经发布。

需要在线演示时可以后续单独启用 GitHub Pages。当前交付支持本地运行，未承诺已部署公共 API 或网页。
