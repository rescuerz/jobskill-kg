"""生成一个自包含的静态演示站点（单文件 HTML，双击即可打开，无需服务器）。

输入：data/kg/stats.json, data/kg/skills_by_family.json, data/processed/jobs.jsonl,
      data/processed/job_skills.jsonl
输出：app/site/index.html

用法：python3 src/app/build_site.py
"""
from __future__ import annotations

import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
KG = os.path.join(ROOT, "data", "kg")
OUT_DIR = os.path.join(ROOT, "app", "site")


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    stats = json.load(open(os.path.join(KG, "stats.json"), encoding="utf-8"))
    by_fam = json.load(open(os.path.join(KG, "skills_by_family.json"), encoding="utf-8"))
    by_cat = json.load(open(os.path.join(KG, "skills_by_category.json"), encoding="utf-8"))

    jobs = {j["doc_id"]: j for j in (json.loads(l) for l in
                                     open(os.path.join(ROOT, "data", "processed", "jobs.jsonl"), encoding="utf-8"))}
    job_skills = {r["doc_id"]: [s["name"] for s in r["skills"]]
                  for r in (json.loads(l) for l in
                            open(os.path.join(KG, "job_skills_norm.jsonl"), encoding="utf-8"))}

    payload_jobs = []
    for did, j in jobs.items():
        sk = job_skills.get(did, [])
        if not sk:
            continue
        payload_jobs.append({
            "i": did,
            "t": j["title"],
            "c": j["company"],
            "f": j["job_family"],
            "l": j["locations"][:2],
            "e": j.get("education_level", "不限"),
            "y": j.get("experience_years", "不限"),
            "s": sk,
            "u": j["url"],
        })

    data = {
        "stats": {k: stats[k] for k in ["jobs", "skills", "nodes", "edges", "by_family", "by_company",
                                        "top_skills", "avg_skills_per_job"]},
        "families": by_fam,
        "categories": by_cat,
        "jobs": payload_jobs,
    }
    blob = json.dumps(data, ensure_ascii=False, separators=(",", ":"))

    html = HTML_TEMPLATE.replace("__DATA__", blob)
    path = os.path.join(OUT_DIR, "index.html")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(html)
    print(f"jobs in site: {len(payload_jobs)}")
    print(f"size: {os.path.getsize(path) / 1e6:.1f} MB -> {path}")


HTML_TEMPLATE = r"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>JobSkill-KG · 中文 IT/算法岗位技能图谱</title>
<style>
  :root{--bg:#0f1115;--card:#171a21;--line:#252a34;--fg:#e6e8ee;--dim:#8b93a7;--acc:#4f8cff;--acc2:#25c2a0;}
  *{box-sizing:border-box}
  body{margin:0;background:var(--bg);color:var(--fg);font:14px/1.6 -apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif}
  header{padding:28px 32px 8px}
  h1{margin:0 0 6px;font-size:22px;font-weight:650}
  .sub{color:var(--dim);font-size:13px}
  .stats{display:flex;gap:26px;margin:18px 0 0;flex-wrap:wrap}
  .stat b{font-size:22px;color:var(--acc);font-weight:700}
  .stat span{color:var(--dim);font-size:12px;margin-left:4px}
  nav{display:flex;gap:8px;padding:20px 32px 0;border-bottom:1px solid var(--line);flex-wrap:wrap}
  nav button{background:none;border:none;color:var(--dim);padding:8px 14px;cursor:pointer;font-size:14px;border-bottom:2px solid transparent}
  nav button.on{color:var(--fg);border-bottom-color:var(--acc)}
  main{padding:24px 32px 60px;max-width:1180px}
  .card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:18px 20px;margin-bottom:18px}
  .row{display:flex;gap:16px;flex-wrap:wrap;align-items:flex-end}
  label{color:var(--dim);font-size:12px;display:block;margin-bottom:6px}
  select,input{background:#0d1017;border:1px solid var(--line);color:var(--fg);padding:8px 10px;border-radius:7px;font-size:13px;min-width:170px}
  .bar{display:flex;align-items:center;gap:10px;height:24px;margin:2px 0}
  .bar .nm{width:150px;flex:0 0 150px;text-align:right;color:var(--fg);font-size:13px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
  .bar .tr{flex:1 1 auto;height:14px;background:#0d1017;border-radius:4px;overflow:hidden;position:relative}
  .bar .fl{position:absolute;left:0;top:0;bottom:0;background:linear-gradient(90deg,#2b5fbf,#4f8cff);border-radius:4px}
  .bar .vl{flex:0 0 46px;color:var(--dim);font-size:12px}
  .chips{display:flex;flex-wrap:wrap;gap:6px;margin-top:10px;max-height:170px;overflow:auto}
  .chip{border:1px solid var(--line);border-radius:14px;padding:3px 10px;font-size:12px;cursor:pointer;color:var(--dim);user-select:none}
  .chip.on{background:#1d3a75;border-color:#3d6fd4;color:#dce8ff}
  .chip.k{border-color:#2f4a6b}.chip.s{border-color:#2f6656}.chip.t{border-color:#6b5a2f}
  table{width:100%;border-collapse:collapse;margin-top:10px;font-size:13px}
  th{text-align:left;color:var(--dim);font-weight:500;border-bottom:1px solid var(--line);padding:8px 6px;font-size:12px}
  td{padding:8px 6px;border-bottom:1px solid #1d2129;vertical-align:top}
  a{color:#7fb0ff;text-decoration:none}
  a:hover{text-decoration:underline}
  td a{color:#7fb0ff;text-decoration:none}
  #dl li{margin:6px 0}
  #dl .tag{margin-left:8px;color:#8b93a7}
  .tag{display:inline-block;background:#20242e;border-radius:4px;padding:1px 6px;margin:1px 4px 1px 0;font-size:11px;color:#b9c2d6}
  .muted{color:var(--dim)}
  .hidden{display:none}
  .note{color:var(--dim);font-size:12px;margin-top:10px}
  .miss{color:#ffb4a2}
  .catgrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(330px,1fr));gap:14px}
  .catcard{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px 16px}
  .catcard h4{margin:0 0 10px;font-size:14px;font-weight:600}
  .catcard h4 span{font-weight:400}
</style>
</head>
<body>
<header>
  <h1>JobSkill-KG · 中文 IT/算法岗位—技能知识图谱</h1>
  <div class="sub">数据来自公开渠道的中文招聘信息（字节跳动 / 腾讯 / 网易），抽取技能 span 并在 cnSchema 基础上扩展建模</div>
  <div class="stats" id="stats"></div>
</header>
<nav>
  <button class="on" data-tab="fam">岗位族画像</button>
  <button data-tab="search">技能检索岗位</button>
  <button data-tab="gap">技能差距分析</button>
  <button data-tab="cat">技能分类</button>
  <button data-tab="qa">智能问答</button>
  <button data-tab="about">关于数据</button>
</nav>
<main>
  <section id="tab-fam">
    <div class="card">
      <div class="row">
        <div><label>选择岗位族</label><select id="famSel"></select></div>
        <div class="muted" id="famDesc"></div>
      </div>
      <div id="famBars" style="margin-top:16px"></div>
    </div>
  </section>

  <section id="tab-search" class="hidden">
    <div class="card">
      <label>选技能（可多选，AND 匹配）</label>
      <div class="chips" id="skillChips"></div>
      <div class="row" style="margin-top:14px">
        <div><label>城市</label><select id="citySel"></select></div>
        <div><label>岗位族</label><select id="famFilter"></select></div>
        <button id="clearSkills" style="background:#20242e;border:1px solid var(--line);color:var(--fg);padding:8px 12px;border-radius:7px;cursor:pointer">清空</button>
      </div>
      <div class="note" id="searchHint"></div>
    </div>
    <div class="card"><table id="jobTable"><thead><tr><th>岗位</th><th>公司</th><th>城市</th><th>学历/经验</th><th>命中技能</th></tr></thead><tbody></tbody></table></div>
  </section>

  <section id="tab-gap" class="hidden">
    <div class="card">
      <div class="row">
        <div><label>目标岗位族</label><select id="gapFam"></select></div>
      </div>
      <label style="margin-top:16px">勾选你已经掌握的技能</label>
      <div class="chips" id="mySkills"></div>
      <div id="gapOut" style="margin-top:18px"></div>
    </div>
  </section>

  <section id="tab-cat" class="hidden">
    <div class="card" style="background:none;border:none;padding:0">
      <div class="catgrid" id="catGrid"></div>
    </div>
  </section>

  <section id="tab-qa" class="hidden">
    <div class="card">
      <label>用一句中文提问（规则问答，不需要联网）</label>
      <div class="row" style="margin-top:6px">
        <input id="qaInput" style="min-width:520px" placeholder="例：杭州做计算机视觉的岗位要会什么？">
        <button id="qaBtn" style="background:#2f6fe8;border:none;color:#fff;padding:9px 16px;border-radius:7px;cursor:pointer">提问</button>
      </div>
      <div class="chips" id="qaExamples" style="margin-top:12px"></div>
      <div id="qaAnswer" style="margin-top:16px;line-height:1.9"></div>
    </div>
  </section>

  <section id="tab-about" class="hidden">
    <div class="card">
      <h3 style="margin-top:0">数据来源与边界</h3>
      <p class="muted">采集自企业官方招聘站的公开岗位信息，保留来源 URL 与抓取时间；采集行为说明见数据来源文档。</p>
      <p class="muted">原始 JD 文本仅用于研究与抽取，<b>不随数据集对外分发</b>；对外发布的是抽取后的三元组、聚合统计与脱敏样例。</p>
      <h3>Schema</h3>
      <p class="muted">复用 cnSchema（schema.org 中文版）的 JobPosting / Organization / Place / MonetaryAmount；扩展 cns:Skill、cns:JobFamily、cns:SalaryRange 等 21 个类与属性（5 类 + 16 属性）；技能类型对齐 ESCO 的 LSKT 四维（知识/技能/通用/语言）。</p>
      <h3>抽取方法</h3>
      <p class="muted">图谱采用词典与局部规则。100 句冻结样本经 AI 标注和同一代理自查后，词典 exact P/R/F1 为 0.660/0.201/0.308，BERT 为 0.119/0.312/0.172；不是人工金标准。未说明不等于必备，任选条件需回看原文。</p>
      <div id="dl"></div>
    </div>
  </section>
</main>
<script>
const D = __DATA__;
const S = D.stats;
const $ = s => document.querySelector(s);
const fmt = n => n.toLocaleString('en-US');

$('#stats').innerHTML = [
  ['岗位', fmt(S.jobs)], ['技能', fmt(S.skills)], ['关系边', fmt(S.edges)],
  ['公司', Object.keys(S.by_company).length], ['平均技能/岗', S.avg_skills_per_job]
].map(([k,v]) => `<div class="stat"><b>${v}</b><span>${k}</span></div>`).join('');

const fams = Object.keys(S.by_family);
const famSel = $('#famSel'), famFilter = $('#famFilter'), gapFam = $('#gapFam');
fams.forEach(f => {
  famSel.insertAdjacentHTML('beforeend', `<option value="${f}">${f}（${S.by_family[f]} 个岗位）</option>`);
  famFilter.insertAdjacentHTML('beforeend', `<option value="${f}">${f}</option>`);
  gapFam.insertAdjacentHTML('beforeend', `<option value="${f}">${f}</option>`);
});
famFilter.insertAdjacentHTML('afterbegin', '<option value="">全部</option>');

function bars(el, items, max) {
  el.innerHTML = items.map(([n, v]) =>
    `<div class="bar"><div class="nm" title="${n}">${n}</div><div class="tr"><div class="fl" style="width:${Math.max(2, v / max * 100)}%"></div></div><div class="vl">${v}</div></div>`).join('');
}

function renderFam() {
  const f = famSel.value;
  const items = (D.families[f] || []).slice(0, 20).map(x => [x.skill, x.jobs]);
  bars($('#famBars'), items, items.length ? items[0][1] : 1);
  $('#famDesc').textContent = `该族共 ${S.by_family[f]} 个岗位，下面是出现频次最高的 20 项技能`;
}
famSel.onchange = renderFam;
renderFam();

/* ---------- 技能检索 ---------- */
const allSkills = [];
const seen = new Set();
D.families && Object.values(D.families).forEach(arr => arr.forEach(x => {
  if (!seen.has(x.skill)) { seen.add(x.skill); allSkills.push(x); }
}));
allSkills.sort((a, b) => b.jobs - a.jobs);
const topSkills = allSkills.slice(0, 60);
const picked = new Set();

$('#skillChips').innerHTML = topSkills.map(x =>
  `<span class="chip ${x.type.toLowerCase()}" data-s="${x.skill}">${x.skill}<span class="muted"> ${x.jobs}</span></span>`).join('');
document.querySelectorAll('#skillChips .chip').forEach(c => c.onclick = () => {
  const s = c.dataset.s;
  if (picked.has(s)) { picked.delete(s); c.classList.remove('on'); }
  else { picked.add(s); c.classList.add('on'); }
  renderJobs();
});
$('#clearSkills').onclick = () => {
  picked.clear();
  document.querySelectorAll('#skillChips .chip').forEach(c => c.classList.remove('on'));
  renderJobs();
};

const cities = {};
D.jobs.forEach(j => (j.l || []).forEach(c => cities[c] = (cities[c] || 0) + 1));
const citySel = $('#citySel');
citySel.insertAdjacentHTML('afterbegin', '<option value="">全部城市</option>');
Object.entries(cities).sort((a, b) => b[1] - a[1]).slice(0, 30)
  .forEach(([c, n]) => citySel.insertAdjacentHTML('beforeend', `<option value="${c}">${c}（${n}）</option>`));

function renderJobs() {
  const city = citySel.value, fam = famFilter.value;
  let rows = D.jobs.filter(j =>
    (!city || (j.l || []).includes(city)) && (!fam || j.f === fam) &&
    [...picked].every(s => j.s.includes(s)));
  rows = rows.slice(0, 200);
  $('#searchHint').textContent = picked.size
    ? `命中 ${rows.length} 个岗位（最多显示 200 条）`
    : `共 ${D.jobs.length} 个岗位，选技能后按 AND 过滤`;
  $('#jobTable tbody').innerHTML = rows.map(j => {
    const hit = [...picked].filter(s => j.s.includes(s));
    return `<tr><td><a href="${j.u}" target="_blank" rel="noopener">${j.t}</a></td>
      <td>${j.c}</td><td>${(j.l || []).join('、')}</td>
      <td class="muted">${j.e} / ${j.y}</td>
      <td>${hit.map(s => `<span class="tag">${s}</span>`).join('')}</td></tr>`;
  }).join('') || '<tr><td colspan="5" class="muted">没有匹配的岗位，减少一个技能试试</td></tr>';
}
citySel.onchange = renderJobs; famFilter.onchange = renderJobs;
renderJobs();

/* ---------- 技能差距 ---------- */
const mine = new Set();
function renderGapSkills() {
  const f = gapFam.value;
  const items = (D.families[f] || []).slice(0, 40);
  $('#mySkills').innerHTML = items.map(x =>
    `<span class="chip ${x.type.toLowerCase()}" data-s="${x.skill}">${x.skill}</span>`).join('');
  document.querySelectorAll('#mySkills .chip').forEach(c => c.onclick = () => {
    const s = c.dataset.s;
    if (mine.has(s)) { mine.delete(s); c.classList.remove('on'); }
    else { mine.add(s); c.classList.add('on'); }
    renderGap();
  });
}
function renderGap() {
  const f = gapFam.value;
  const items = (D.families[f] || []).slice(0, 20);
  const miss = items.filter(x => !mine.has(x.skill));
  const max = items.length ? items[0].jobs : 1;
  const done = items.filter(x => mine.has(x.skill));
  $('#gapOut').innerHTML =
    `<div class="muted" style="margin-bottom:8px">目标「${f}」岗最需要的 20 项技能中，你已掌握 ${done.length} 项，还缺 ${miss.length} 项</div>` +
    `<div class="chips" style="max-height:none">${miss.map(x => `<span class="chip on" style="border-color:#7a3a3a;color:#ffc9c9">${x.skill}<span class="muted"> 需求 ${x.jobs}</span></span>`).join('') || '<span class="muted">已全部掌握 🎉</span>'}</div>`;
}
gapFam.onchange = () => { mine.clear(); renderGapSkills(); renderGap(); };
renderGapSkills(); renderGap();

/* ---------- 技能分类 ---------- */
$('#catGrid').innerHTML = Object.entries(D.categories).map(([c, items]) => `
  <div class="catcard"><h4>${c}<span class="muted">　${items.length} 项</span></h4>
    <div class="chips" style="max-height:none">${
      items.slice(0, 40).map(x => `<span class="chip ${x.type.toLowerCase()}">${x.skill}<span class="muted"> ${x.jobs}</span></span>`).join('')
    }</div></div>`).join('');

/* ---------- 智能问答（规则版） ---------- */
const FAM_LIST = Object.keys(D.stats.by_family);
const CITY_LIST = [...new Set(D.jobs.flatMap(j => j.l || []))]
  .filter(c => c && c.length <= 4).sort((a, b) => b.length - a.length);
const SKILL_LIST = allSkills.map(x => x.skill).sort((a, b) => b.length - a.length);

function pick(question, dict) {
  return dict.filter(w => question.includes(w));
}
function answer(q) {
  const fams = pick(q, FAM_LIST);
  const cities = pick(q, CITY_LIST);
  const skills = pick(q, SKILL_LIST).slice(0, 3);
  const wantsSalary = /薪|工资|多少|待遇/.test(q);

  if (wantsSalary) {
    return { text: '三个数据源（字节 / 腾讯 / 网易）都不公布薪资，图谱里没有该字段。'
      + 'schema 里已经建了 <code>cns:SalaryRange</code>，接入含薪资的来源后即可启用。', jobs: [] };
  }

  let pool = D.jobs;
  if (fams.length) pool = pool.filter(j => fams.includes(j.f));
  if (cities.length) pool = pool.filter(j => (j.l || []).some(c => cities.includes(c)));
  if (skills.length) pool = pool.filter(j => skills.every(s => j.s.includes(s)));

  if (!pool.length) {
    return { text: '没有匹配的岗位。可以换个说法，比如「算法岗要会什么」「北京要求 RAG 的岗位有哪些」。', jobs: [] };
  }

  const cnt = {};
  pool.forEach(j => j.s.forEach(s => cnt[s] = (cnt[s] || 0) + 1));
  const top = Object.entries(cnt).filter(([s]) => !skills.includes(s))
    .sort((a, b) => b[1] - a[1]).slice(0, 8);

  const scope = [cities.join('、'), fams.join('、'), skills.join(' + ')].filter(Boolean).join(' · ');
  const text = `在${scope ? '「' + scope + '」范围内' : '全部岗位中'}共命中 <b>${pool.length}</b> 个岗位。`
    + `出现最多的技能是：` + top.map(([s, n]) => `<span class="tag">${s} ${n}</span>`).join('');

  return { text, jobs: pool.slice(0, 5) };
}
function renderQA(q) {
  const r = answer(q);
  const list = r.jobs.map(j => `<div class="muted">· <a href="${j.u}" target="_blank" rel="noopener">${j.t}</a>`
    + `　${j.c}　${(j.l || []).join('/')}</div>`).join('');
  $('#qaAnswer').innerHTML = `<div>${r.text}</div>${list ? '<div style="margin-top:10px">' + list + '</div>' : ''}`;
}
$('#qaBtn').onclick = () => renderQA($('#qaInput').value.trim());
$('#qaInput').addEventListener('keydown', e => { if (e.key === 'Enter') renderQA($('#qaInput').value.trim()); });
const EX = ['算法岗需要会什么', '北京要求 RAG 的岗位', '杭州做计算机视觉的岗位', '这些岗位薪资多少'];
$('#qaExamples').innerHTML = EX.map(x => `<span class="chip" data-q="${x}">${x}</span>`).join('');
document.querySelectorAll('#qaExamples .chip').forEach(c => c.onclick = () => {
  $('#qaInput').value = c.dataset.q; renderQA(c.dataset.q);
});
renderQA('算法岗需要会什么');

/* ---------- tabs ---------- */
document.querySelectorAll('nav button').forEach(b => b.onclick = () => {
  document.querySelectorAll('nav button').forEach(x => x.classList.remove('on'));
  b.classList.add('on');
  ['fam', 'search', 'gap', 'cat', 'qa', 'about'].forEach(t =>
    $('#tab-' + t).classList.toggle('hidden', t !== b.dataset.tab));
});
</script>
</body>
</html>
"""

if __name__ == "__main__":
    main()
