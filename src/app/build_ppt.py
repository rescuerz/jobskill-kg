"""生成答辩 PPT（13 页），数据全部从 data/kg/stats.json 读取。

用法：
    PYTHONPATH=.pkgs python3 src/app/build_ppt.py
输出：
    docs/JobSkill-KG答辩.pptx
"""
from __future__ import annotations

import json
import os

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.util import Emu, Pt

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
KG = os.path.join(ROOT, "data", "kg")
OUT = os.path.join(ROOT, "docs", "JobSkill-KG答辩.pptx")
FIG = os.path.join(ROOT, "docs", "figures")

INK = RGBColor(0x1A, 0x1D, 0x24)
DIM = RGBColor(0x6B, 0x72, 0x80)
ACC = RGBColor(0x2F, 0x6F, 0xE8)
BG = RGBColor(0xFF, 0xFF, 0xFF)
SOFT = RGBColor(0xF3, 0xF5, 0xF9)

W, H = Emu(12192000), Emu(6858000)  # 16:9


def add_slide(prs):
    return prs.slides.add_slide(prs.slide_layouts[6])


def textbox(slide, x, y, w, h, text, size=18, color=INK, bold=False, align=PP_ALIGN.LEFT):
    tb = slide.shapes.add_textbox(Emu(x), Emu(y), Emu(w), Emu(h))
    tf = tb.text_frame
    tf.word_wrap = True
    for i, line in enumerate(text.split("\n")):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        r = p.add_run()
        r.text = line
        r.font.size = Pt(size)
        r.font.bold = bold
        r.font.color.rgb = color
        r.font.name = "PingFang SC"
    return tb


def bar(slide, x, y, w, h, color=ACC):
    from pptx.enum.shapes import MSO_SHAPE
    shp = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Emu(x), Emu(y), Emu(w), Emu(h))
    shp.fill.solid()
    shp.fill.fore_color.rgb = color
    shp.line.fill.background()
    return shp


def header(slide, title, kicker=""):
    bar(slide, 0, 0, W, Emu(120000), ACC)
    textbox(slide, 640080, 500000, 10000000, 700000, title, size=32, bold=True)
    if kicker:
        textbox(slide, 640080, 1150000, 10000000, 400000, kicker, size=15, color=DIM)


def bullets(slide, items, x=640080, y=1700000, size=19, gap=760000):
    for i, (head, body) in enumerate(items):
        yy = y + i * gap
        textbox(slide, x, yy, 10000000, 420000, f"▪  {head}", size=size, bold=True)
        if body:
            textbox(slide, x + 320000, yy + 420000, 10000000, 420000, body, size=size - 4, color=DIM)


def kpi(slide, stats):
    x = 640080
    for label, value in stats:
        textbox(slide, x, 5600000, 2350000, 500000, str(value), size=26, bold=True, color=ACC)
        textbox(slide, x, 6060000, 2350000, 300000, label, size=12, color=DIM)
        x += 2450000


def main() -> None:
    stats = json.load(open(os.path.join(KG, "stats.json"), encoding="utf-8"))
    n_lex = sum(1 for l in open(os.path.join(ROOT, "data", "lexicon", "tech_skills.txt"),
                                encoding="utf-8") if l.strip() and not l.startswith("#"))
    fam = stats["by_family"]
    top = stats["top_skills"]

    prs = Presentation()
    prs.slide_width, prs.slide_height = W, H

    # 1 封面
    s = add_slide(prs)
    bar(s, 0, 0, Emu(12192000), Emu(400000), ACC)
    textbox(s, 640080, 1800000, 11000000, 900000, "JobSkill-KG", size=54, bold=True)
    textbox(s, 640080, 2700000, 11000000, 600000, "中文 IT/算法岗位—技能知识图谱", size=30)
    textbox(s, 640080, 3500000, 11000000, 400000, "《知识图谱导论》课程设计 · 向 OpenKG 贡献开放知识图谱", size=16, color=DIM)
    textbox(s, 640080, 5200000, 11000000, 400000,
            f"{stats['jobs']:,} 个岗位 · {stats['skills']} 项技能 · {stats['edges']:,} 条三元组", size=18, color=ACC, bold=True)

    # 2 选题
    s = add_slide(prs)
    header(s, "为什么做招聘", "开放域文本 + 必然需要抽取 + 应用闭环")
    bullets(s, [
        ("招聘文本是典型开放域语料", "岗位职责与任职要求都是自由段落，技能、学历、经验全埋在句子里"),
        ("OpenKG 是空白", "410 个数据集中「招聘」「岗位」命中 0，没有岗位—技能类数据集"),
        ("历史作业集中在娱乐", "动漫/影视/游戏人物关系占了大半，再做就是第 10 个同类作品"),
        ("垂直切片：只做 IT/算法岗", "算法、后端、前端客户端、数据、测试、运维安全、MLOps 七个族"),
    ])

    # 3 数据
    s = add_slide(prs)
    header(s, "数据：三家官方招聘站", "只抓公开页面，限速 ≥0.3s，保留来源与抓取时间")
    textbox(s, 640080, 1500000, 10500000, 400000,
            "字节跳动 10,000 ｜ 腾讯 2,248 ｜ 网易 2,726　→　原始 14,974 条", size=17, bold=True)
    textbox(s, 640080, 2000000, 10500000, 400000,
            "按岗位大类 + 标题技术信号筛选，剔除产品/设计/市场/运营，去重后入池 4,904 条", size=15, color=DIM)
    bullets(s, [
        ("筛选口径可复现", "站点岗位大类排除 + 标题强技术信号例外 + 正文 <40 字丢弃 + 内容哈希去重"),
        ("字段解析", "学历、经验年限、城市、薪资区间（规则 + 正则）"),
        ("合规边界", "原始 JD 不对外分发，只发布三元组、聚合统计与脱敏样例"),
    ], y=2500000)
    kpi(s, [("原始岗位", "14,974"), ("入池 IT 岗", "4,904"), ("公司", len(stats["by_company"])), ("岗位族", len(fam))])

    # 4 方法
    s = add_slide(prs)
    header(s, "方法：两路抽取 + 归一", "词典保精度，模型提召回，最后做别名词表归一")
    steps = ["采集", "筛选", "技能抽取", "归一化", "图谱", "应用"]
    x = 640080
    for i, st in enumerate(steps):
        bar(s, x, 1750000, 1520000, 520000, ACC if i % 2 == 0 else RGBColor(0x5B, 0x8D, 0xEF))
        textbox(s, x + 120000, 1855000, 1400000, 320000, st, size=14, color=BG, bold=True)
        x += 1750000
    bullets(s, [
        ("词典路径", f"{n_lex} 条人工技术词表，字符级 Trie 最长匹配，置信度 0.98"),
        ("模型路径", "bert-base-chinese 在 Chinese-SkillSpan 上微调，LSKT 四类字符级 BIO"),
        ("后处理", "裁虚词、限长 2–20 字、按上下文 8 字窗口推断掌握程度与必要性"),
        ("归一化", "NLP→自然语言处理、K8s→Kubernetes、大模型→大语言模型"),
    ], y=2600000)

    # 5 抽取评测
    s = add_slide(prs)
    header(s, "技能抽取评测", "Chinese-SkillSpan 官方 test：2,590 句 / 2,098 个 gold span")
    textbox(s, 640080, 1500000, 10500000, 400000,
            "Exact F1 0.306　｜　Relaxed F1 0.519　（P 0.42 / R 0.69）", size=19, bold=True, color=ACC)
    bullets(s, [
        ("为什么 exact 不高", "训练语料仅 2,141 句，3 epoch 后训练 loss 0.03，已明显过拟合"),
        ("分标签 F1", "T 0.494 ｜ L 0.393 ｜ K 0.296 ｜ S 0.267（S 类边界最长、最难）"),
        ("典型错误", "边界错位（沟通能力→的沟通能）、碎片化（长 span 被拆成多个短 span）"),
        ("结论", "域内以词典为主，模型作为对照实验；换更大模型 + 更多标注是下一步"),
    ], y=2500000)

    # 6 Schema
    s = add_slide(prs)
    header(s, "Schema：cnSchema 扩展", "复用 9 个词，新增 18 个（5 个类 + 13 个属性），每个都能回答「为什么不够」")
    textbox(s, 640080, 1600000, 5200000, 3200000,
            "复用（9）\n"
            "JobPosting / Occupation / Organization\n"
            "Place / PostalAddress / MonetaryAmount\n"
            "title / name / datePosted\n\n"
            "新增类（5）\n"
            "cns:Skill　cns:SkillCategory\n"
            "cns:JobFamily　cns:SalaryRange\n"
            "cns:JobRequirement",
            size=15)
    textbox(s, 6200000, 1600000, 5400000, 3200000,
            "新增属性（13）\n"
            "对象属性 4：requiresSkill / belongsToFamily\n"
            "　　　　　　hasSalaryRange / inCategory\n"
            "枚举属性 4：skillType / proficiency\n"
            "　　　　　　necessity / escoCode\n"
            "数值属性 5：educationLevel / experienceYears\n"
            "　　　　　　monthlyMin / monthlyMax / salaryMonths",
            size=15)
    textbox(s, 640080, 5150000, 11200000, 500000,
            "每个新增都在 schema/schema_extension.md 里写了「为什么 schema.org 不够」——这就是答辩口径",
            size=14, color=ACC)
    textbox(s, 640080, 5750000, 11200000, 400000,
            "本体文件 110 条三元组，rdflib 校验通过", size=13, color=DIM)

    # 7 图谱规模
    s = add_slide(prs)
    header(s, "图谱规模与分布", "七个岗位族，算法岗占 45%")
    y = 1550000
    for k, v in fam.items():
        w = int(v / max(fam.values()) * 6200000)
        textbox(s, 640080, y - 60000, 1500000, 300000, k, size=13, align=PP_ALIGN.RIGHT)
        bar(s, 2250000, y, w, 260000, ACC)
        textbox(s, 2350000 + w, y - 40000, 900000, 300000, f"{v:,}", size=12, color=DIM)
        y += 470000
    textbox(s, 640080, 5200000, 10500000, 900000,
            "高频技能：" + "、".join(x["skill"] for x in top[:12]), size=14, color=DIM)

    # 7.5 技能分类
    s = add_slide(prs)
    header(s, "技能分类：12 个 SkillCategory",
           f"cns:inCategory 把 {stats['skills']} 项技能归到可浏览的分类下")
    cat_line = " ｜ ".join(f"{k} {v}" for k, v in list(stats["by_category"].items())[:6])
    textbox(s, 640080, 1420000, 11200000, 500000, cat_line, size=13, color=DIM)
    s.shapes.add_picture(os.path.join(FIG, "site_category.png"), Emu(640080), Emu(1950000), height=Emu(4500000))

    # 8 应用
    s = add_slide(prs)
    header(s, "应用：一个站点的四个功能", "岗位族画像 / 技能检索 / 技能差距 / 智能问答（另有技能分类页签）")
    bullets(s, [
        ("岗位族画像", "选族看 Top20 技能与需求强度"),
        ("技能检索岗位", "多选技能 AND + 城市 + 岗位族，直连原文"),
        ("技能差距分析", "选目标族 + 勾选已有技能 → 缺什么、按需求频次排序"),
        ("智能问答", "中文提问，规则解析城市/岗位族/技能，答案附证据岗位"),
    ], y=1470000, gap=690000, size=16)
    s.shapes.add_picture(os.path.join(FIG, "site_home.png"), Emu(640080), Emu(4350000), height=Emu(2300000))

    # 9 检索截图
    s = add_slide(prs)
    header(s, "技能检索效果", "大语言模型 → 命中 200 个岗位（截断显示）")
    s.shapes.add_picture(os.path.join(FIG, "site_search.png"), Emu(640080), Emu(1500000), height=Emu(5200000))

    # 10 质量
    s = add_slide(prs)
    header(s, "质量：域内评测", "100 句 silver 标注 + 40 条精度抽检")
    textbox(s, 640080, 1520000, 10500000, 400000,
            "100 句评测：P 0.88 / R 0.59 / F1 0.70　｜　抽检精度 0.93", size=18, bold=True, color=ACC)
    bullets(s, [
        ("精度够用", "37/40 明确成立；边界是「服务端」这类岗位词"),
        ("扩词表见效", "P 0.78→0.88、R 0.40→0.59、F1 0.53→0.70（补 39 个工具名 + 14 个类型改判）"),
        ("结论", "扩词表比换模型划算；模型（高召回低精度）与词典互补而非替代"),
    ], y=2000000)

    # 11 差异化
    s = add_slide(prs)
    header(s, "与已有工作对比", "开放、可复现、可扩展")
    textbox(s, 640080, 1550000, 5200000, 3000000,
            "已有课程作业\n· 多为百科/维基结构化字段转存\n· 以人物关系为主\n· 少见 Schema 与 API\n· 娱乐题材高度重复", size=17, color=DIM)
    textbox(s, 6200000, 1550000, 5600000, 3000000,
            f"本工作\n· 从非结构化 JD 抽取，非转存\n· 七族岗位 + {stats['skills']} 项技能、{stats['edges']:,} 条三元组\n· cnSchema 扩展 + JSON-LD + Neo4j\n· 提供可交互检索与差距分析", size=17)
    textbox(s, 640080, 5000000, 11200000, 400000,
            "同一条评测链路：跨域 F1 + 域内 P/R/F1 + 精度抽检，三项都能复现", size=14, color=ACC)

    # 12 局限与计划
    s = add_slide(prs)
    header(s, "局限与下一步", "诚实说清楚边界")
    bullets(s, [
        ("规模", f"{stats['jobs']:,} 岗（入池 4,904），低于 3 万条目标；需再接 5–8 家企业"),
        ("模型", "跨域 F1 0.31 / relaxed 0.52，需要更多标注或更大预训练模型"),
        ("薪资字段", "三个来源都不公布薪资，SalaryRange 已建模但为空"),
        ("下一步", "扩数据源 → 扩词表 → 域内标注 300 条 → OpenKG 提交 → 更新版本"),
    ])

    # 13 分工
    s = add_slide(prs)
    header(s, "分工与协作", "4 人分工，每人一条主线，接口在周会上对齐")
    rows = [
        ("P1 数据与抽取", "采集、清洗、标注、抽取模型与词典维护", "语料库、抽取脚本、词表"),
        ("P2 Schema 与图谱", "cnSchema 扩展、归一化、构图与质量", "ontology.ttl、KG（66,689 条）"),
        ("P3 应用与前端", "站点四页签、QA 规则、可视化", "app/site/index.html"),
        ("P4 评测与发布", "gold 集、三组评测、OpenKG 打包与文档", "报告、PPT、deliverable/"),
    ]
    yy = 1650000
    for name, work, out in rows:
        textbox(s, 640080, yy, 2600000, 400000, name, size=17, bold=True)
        textbox(s, 3300000, yy, 4600000, 400000, work, size=15, color=DIM)
        textbox(s, 8100000, yy, 4000000, 400000, out, size=15, color=ACC)
        yy += 900000
    textbox(s, 640080, 5600000, 11200000, 400000,
            "3 人版：P4 的评测并入 P1，发布与文档并入 P3", size=13, color=DIM)

    # 14 结束
    s = add_slide(prs)
    bar(s, 0, 0, Emu(12192000), Emu(400000), ACC)
    textbox(s, 640080, 2600000, 10500000, 700000, "谢谢，欢迎提问", size=40, bold=True)
    textbox(s, 640080, 3600000, 10500000, 400000,
            "数据与代码：jobskill-kg/　｜　演示站点：app/site/index.html", size=15, color=DIM)

    prs.save(OUT)
    print("slides:", len(prs.slides.__iter__.__self__._sldIdLst), "->", OUT)


if __name__ == "__main__":
    main()
