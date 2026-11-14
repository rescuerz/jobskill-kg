# JobSkill-KG 演示站点

中文 IT/算法岗位—技能知识图谱的可交互演示（单文件，无外部依赖）。

- 岗位 4,904｜技能 390｜关系边 169,490
- 四个功能：岗位族画像 / 技能检索岗位 / 技能差距分析 / 技能分类

## 部署到 GitHub Pages

```bash
# 在仓库根目录
git subtree push --prefix gh-pages origin gh-pages
# 或在 GitHub 仓库 Settings → Pages 里把 Source 选成 gh-pages 分支
```

部署后地址形如 `https://<user>.github.io/<repo>/`，把它填到 OpenKG 数据集页的「数据门户」。
