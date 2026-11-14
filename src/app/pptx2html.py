"""把 pptx 按真实坐标渲染成 HTML —— 用途有两个：
    1. 视觉自检：没有 LibreOffice 也能看到每页的真实排版（位置、字号、图片尺寸都来自 pptx）
    2. 答辩备份：现场 PowerPoint 打不开时，直接用浏览器放这份

用法：
    PYTHONPATH=.pkgs python3 src/app/pptx2html.py
输出：
    docs/slides.html（自包含，图片内嵌 base64）
"""
from __future__ import annotations

import base64
import io
import os

from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(ROOT, "docs", "JobSkill-KG答辩.pptx")
OUT = os.path.join(ROOT, "docs", "slides.html")

PX_W = 1280                       # 画布宽
EMU_PER_PX = 12192000 / PX_W      # 16:9 版面横向 12,192,000 EMU


def color_of(run, default="#1a1d24"):
    try:
        rgb = run.font.color.rgb
        return f"#{rgb}" if rgb else default
    except Exception:
        return default


def shape_html(sh, z):
    left = sh.left / EMU_PER_PX
    top = sh.top / EMU_PER_PX
    w = sh.width / EMU_PER_PX
    h = sh.height / EMU_PER_PX
    base = f"left:{left:.1f}px;top:{top:.1f}px;width:{w:.1f}px;height:{h:.1f}px;"

    if sh.shape_type == MSO_SHAPE_TYPE.PICTURE:
        blob = sh.image.blob
        ext = sh.image.ext or "png"
        b64 = base64.b64encode(blob).decode()
        return f'<img style="position:absolute;{base}object-fit:contain" src="data:image/{ext};base64,{b64}">'

    if sh.has_text_frame and sh.text_frame.text.strip():
        parts = []
        for para in sh.text_frame.paragraphs:
            align = {1: "left", 2: "center", 3: "right"}.get(
                int(para.alignment) if para.alignment is not None else 1, "left")
            spans = []
            for r in para.runs:
                pt = r.font.size.pt if r.font.size else 18
                px = pt * (960 / (13.3333 * 72)) / (960 / PX_W) * 0  # 占位，下面直接算
                px = pt * (PX_W / (13.3333 * 72))  # 1pt -> px
                weight = "700" if r.font.bold else "400"
                spans.append(
                    f'<span style="font-size:{px:.1f}px;font-weight:{weight};'
                    f'color:{color_of(r)}">{r.text}</span>')
            if spans:
                parts.append(f'<div style="text-align:{align};line-height:1.35">{"".join(spans)}</div>')
        if parts:
            return f'<div style="position:absolute;{base}overflow:hidden">{"".join(parts)}</div>'

    # 纯色块（标题条等）
    try:
        fill = sh.fill
        if fill.type is not None and fill.fore_color.rgb is not None:
            return f'<div style="position:absolute;{base}background:#{fill.fore_color.rgb}"></div>'
    except Exception:
        pass
    return ""


def main() -> None:
    prs = Presentation(SRC)
    slides = []
    for idx, slide in enumerate(prs.slides, 1):
        body = "".join(shape_html(sh, idx) for sh in slide.shapes)
        slides.append(f'<section class="slide" data-i="{idx}">{body}'
                      f'<div class="num">{idx} / {len(prs.slides)}</div></section>')

    html = f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8">
<title>JobSkill-KG 答辩（HTML 备份）</title>
<style>
  body{{margin:0;background:#0b0d12;font-family:-apple-system,"PingFang SC",sans-serif;color:#1a1d24}}
  .slide{{position:relative;width:{PX_W}px;height:{PX_W * 9 // 16}px;background:#fff;
          margin:24px auto;box-shadow:0 8px 40px rgba(0,0,0,.5);overflow:hidden}}
  .num{{position:absolute;right:16px;bottom:10px;color:#b9c0cc;font-size:12px}}
  @media print{{body{{background:#fff}}.slide{{margin:0;box-shadow:none;page-break-after:always}}}}
</style></head>
<body>{"".join(slides)}</body></html>
"""
    open(OUT, "w", encoding="utf-8").write(html)
    print(f"{len(prs.slides)} 页 -> {OUT}  ({os.path.getsize(OUT)/1e6:.1f} MB)")


if __name__ == "__main__":
    main()
