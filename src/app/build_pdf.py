"""把 docs/report.md 渲染成 PDF（A4，可直接交作业）。

做法：markdown → 带打印样式的 HTML → Chrome headless --print-to-pdf

用法：
    PYTHONPATH=.pkgs python3 src/app/build_pdf.py
输出：
    docs/JobSkill-KG技术报告.pdf
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile

import markdown

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(ROOT, "docs", "report.md")
OUT = os.path.join(ROOT, "docs", "JobSkill-KG技术报告.pdf")
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

CSS = """
@page { size: A4; margin: 18mm 16mm 18mm 16mm; }
* { box-sizing: border-box; }
body { font-family: -apple-system, "PingFang SC", "Songti SC", "Microsoft YaHei", sans-serif;
       font-size: 10.5pt; line-height: 1.75; color: #1a1d24; margin: 0; }
h1 { font-size: 20pt; margin: 0 0 6mm; padding-bottom: 3mm; border-bottom: 2px solid #2f6fe8; }
h2 { font-size: 14pt; margin: 9mm 0 3mm; padding-left: 3mm; border-left: 4px solid #2f6fe8;
     page-break-after: avoid; }
h3 { font-size: 11.5pt; margin: 6mm 0 2mm; page-break-after: avoid; }
p, li { orphans: 2; widows: 2; }
blockquote { margin: 3mm 0; padding: 2mm 4mm; background: #f3f5f9; border-left: 3px solid #c9d4e8;
             color: #4a5162; font-size: 9.8pt; }
code { background: #f0f2f6; padding: 0.3mm 1.2mm; border-radius: 2px;
       font-family: "SF Mono", Menlo, monospace; font-size: 9pt; }
pre { background: #f6f8fb; border: 1px solid #e3e7ef; border-radius: 3px; padding: 3mm;
      overflow: hidden; page-break-inside: avoid; }
pre code { background: none; padding: 0; font-size: 8.6pt; }
table { width: 100%; border-collapse: collapse; margin: 3mm 0; font-size: 9.5pt;
        page-break-inside: avoid; }
th { background: #f3f5f9; text-align: left; font-weight: 600; }
th, td { border: 1px solid #dfe4ec; padding: 1.6mm 2.4mm; vertical-align: top; }
hr { border: none; border-top: 1px solid #e3e7ef; margin: 6mm 0; }
a { color: #2f6fe8; text-decoration: none; }
strong { font-weight: 650; }
"""

HTML = """<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8">
<title>JobSkill-KG 技术报告</title>
<style>{css}</style></head>
<body>{body}</body></html>
"""


def main() -> None:
    if not os.path.exists(SRC):
        sys.exit(f"找不到 {SRC}")
    text = open(SRC, encoding="utf-8").read()
    body = markdown.markdown(
        text,
        extensions=["tables", "fenced_code", "sane_lists", "toc"],
        output_format="html5",
    )
    html = HTML.format(css=CSS, body=body)

    tmp = tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8")
    tmp.write(html)
    tmp.close()

    profile = os.path.join(ROOT, ".chrome-tmp")
    os.makedirs(profile, exist_ok=True)
    cmd = [
        CHROME, "--headless=new", "--disable-gpu", "--no-sandbox",
        f"--user-data-dir={profile}", "--no-first-run", "--no-default-browser-check",
        "--disable-extensions", "--disable-crash-reporter",
        "--no-pdf-header-footer", "--virtual-time-budget=3000",
        f"--print-to-pdf={OUT}", f"file://{tmp.name}",
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    os.unlink(tmp.name)
    if r.returncode != 0 or not os.path.exists(OUT):
        print(r.stdout[-800:]); print(r.stderr[-800:])
        sys.exit("Chrome 导出失败")

    size = os.path.getsize(OUT) / 1024
    print(f"PDF: {OUT}  ({size:.0f} KB)")
    # 粗略页数：PDF 里 /Type /Page 的个数
    raw = open(OUT, "rb").read()
    print("页数（估算）:", raw.count(b"/Type /Page") - raw.count(b"/Type /Pages"))


if __name__ == "__main__":
    main()
