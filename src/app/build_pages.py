"""构建 GitHub Pages 站点：单文件站点 + 可下载的数据文件。

用法：
    PYTHONPATH=.pkgs:src python3 src/app/build_pages.py
输出：
    gh-pages/
        index.html        演示站点（同 app/site/index.html，附加下载区）
        data/*.jsonld     样例 / 本体 / context / 统计
        .nojekyll
        README.md
"""
from __future__ import annotations

import json
import os
import shutil

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SITE = os.path.join(ROOT, "app", "site", "index.html")
DELIV = os.path.join(ROOT, "deliverable")
OUT = os.path.join(ROOT, "gh-pages")

FILES = [
    ("sample.jsonld", "样例数据（140 个岗位，JSON-LD）"),
    ("ontology.ttl", "本体（cnSchema 扩展，Turtle）"),
    ("context.jsonld", "JSON-LD 上下文"),
    ("stats.json", "规模与分布统计"),
]

DL_BLOCK = """      <h3>下载</h3>
      <ul class="muted" style="line-height:1.9;padding-left:18px">
        {items}
        <li>全量数据与导入文件尚待公开发布，当前页面为发布候选稿</li>
      </ul>"""


def main() -> None:
    os.makedirs(os.path.join(OUT, "data"), exist_ok=True)

    items = []
    for name, desc in FILES:
        src = os.path.join(DELIV, name)
        if os.path.exists(src):
            shutil.copyfile(src, os.path.join(OUT, "data", name))
            size = os.path.getsize(src)
            human = f"{size / 1024:.0f} KB" if size < 1024 * 1024 else f"{size / 1e6:.2f} MB"
            items.append(f'<li><a href="data/{name}">{desc}</a><span class="tag">{human}</span></li>')

    html = open(SITE, encoding="utf-8").read()
    html = html.replace('<div id="dl"></div>', DL_BLOCK.format(items="\n        ".join(items)))
    open(os.path.join(OUT, "index.html"), "w", encoding="utf-8").write(html)

    open(os.path.join(OUT, ".nojekyll"), "w").write("")

    stats = json.load(open(os.path.join(DELIV, "stats.json"), encoding="utf-8"))
    readme = f"""# JobSkill-KG 演示站点

中文 IT/算法岗位—技能知识图谱的可交互演示（单文件，无外部依赖）。

- 岗位 {stats['jobs']:,}｜技能 {stats['skills']}｜关系边 {stats['edges']:,}
- 四个功能：岗位族画像 / 技能检索岗位 / 技能差距分析 / 技能分类

## 部署到 GitHub Pages

```bash
# 在仓库根目录
git subtree push --prefix gh-pages origin gh-pages
# 或在 GitHub 仓库 Settings → Pages 里把 Source 选成 gh-pages 分支
```

部署后地址形如 `https://<user>.github.io/<repo>/`，把它填到 OpenKG 数据集页的「数据门户」。
"""
    open(os.path.join(OUT, "README.md"), "w", encoding="utf-8").write(readme)

    print(f"pages -> {OUT}")
    for f in sorted(os.listdir(OUT)):
        p = os.path.join(OUT, f)
        print(f"  {f:14s} {'dir' if os.path.isdir(p) else str(round(os.path.getsize(p) / 1024)) + ' KB'}")


if __name__ == "__main__":
    main()
