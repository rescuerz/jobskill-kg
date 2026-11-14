"""JobSkill-KG 查询 API（标准库实现，无需额外依赖）。

OpenKG 发布要求里「数据访问 API」是基本要求之一，这个服务就是那一条的落地物：
    python3 src/app/serve_api.py            # 默认 http://127.0.0.1:8000
    python3 src/app/serve_api.py --port 9000

接口（全部 GET，返回 JSON，带 CORS）：
    /api/stats                              图谱规模与分布
    /api/skills?family=算法&q=大模型         技能列表（按岗位数降序）
    /api/jobs?skills=Python,RAG&city=北京&family=算法&limit=20
                                            按技能/城市/族检索岗位
    /api/gap?family=后端&have=Python,SQL     技能差距：缺哪些必備技能
    /api/job/<doc_id>                       单个岗位的全部技能

示例：
    curl 'http://127.0.0.1:8000/api/jobs?skills=大语言模型,RAG&city=北京&limit=5'
"""
from __future__ import annotations

import argparse
import json
import os
import re
from collections import Counter
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlparse

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
KG = os.path.join(ROOT, "data", "kg")
PROC = os.path.join(ROOT, "data", "processed")

_state: dict = {}


def load() -> None:
    jobs = {}
    for line in open(os.path.join(PROC, "jobs.jsonl"), encoding="utf-8"):
        j = json.loads(line)
        jobs[j["doc_id"]] = j
    skills = {}
    requirements = {}
    for line in open(os.path.join(KG, "job_skills_norm.jsonl"), encoding="utf-8"):
        r = json.loads(line)
        skills[r["doc_id"]] = [s["name"] for s in r["skills"]]
        requirements[r["doc_id"]] = r["skills"]
    stats = json.load(open(os.path.join(KG, "stats.json"), encoding="utf-8"))
    _state.update(jobs=jobs, skills=skills, requirements=requirements, stats=stats)


def _norm(s: str) -> str:
    return re.sub(r"\s+", "", (s or "").strip()).lower()


def api_stats(q):
    return _state["stats"]


def api_skills(q):
    fam = (q.get("family") or [""])[0]
    kw = _norm((q.get("q") or [""])[0])
    cnt = Counter()
    for did, names in _state["skills"].items():
        if fam and _state["jobs"][did]["job_family"] != fam:
            continue
        for n in names:
            if not kw or kw in _norm(n):
                cnt[n] += 1
    return {"total": len(cnt),
            "skills": [{"skill": k, "jobs": v} for k, v in cnt.most_common(100)]}


def api_jobs(q):
    want = [_norm(s) for s in (q.get("skills") or [""])[0].split(",") if s.strip()]
    city = (q.get("city") or [""])[0]
    fam = (q.get("family") or [""])[0]
    limit = max(1, min(int((q.get("limit") or ["20"])[0]), 200))
    hit = []
    for did, names in _state["skills"].items():
        j = _state["jobs"][did]
        if fam and j["job_family"] != fam:
            continue
        if city and city not in j["locations"]:
            continue
        low = {_norm(n) for n in names}
        if want and not all(w in low for w in want):
            continue
        hit.append({"doc_id": did, "title": j["title"], "company": j["company"],
                    "family": j["job_family"], "city": j["locations"],
                    "education": j.get("education_level"), "experience": j.get("experience_years"),
                    "url": j["url"], "skills": names})
    hit.sort(key=lambda x: -len(x["skills"]))
    return {"total": len(hit), "items": hit[:limit]}


def api_evidence(q):
    """Join location + family + ALL skills + optional skill requirement, with provenance."""
    import sys
    sys.path.insert(0, os.path.join(ROOT, "src", "build"))
    from build_kg import canon
    query = dict(q)
    query['skills'] = [','.join(canon(s.strip()) for s in (q.get('skills') or [''])[0].split(',') if s.strip())]
    # Apply additional condition before pagination, including matches beyond first 200 jobs.
    wanted = {_norm(x) for x in query['skills'][0].split(',') if x}
    optional = canon((q.get('optional_skill') or [''])[0].strip())
    limit = max(1, min(int((q.get('limit') or ['20'])[0]),200))
    items=[]
    for did, reqs in _state['requirements'].items():
        j=_state['jobs'][did]
        if (q.get('city') or [''])[0] and q['city'][0] not in j['locations']: continue
        if (q.get('family') or [''])[0] and q['family'][0]!=j['job_family']: continue
        by_name={_norm(r['name']):r for r in reqs}
        if not wanted.issubset(by_name): continue
        if optional and (not by_name.get(_norm(optional)) or by_name[_norm(optional)]['necessity']!='加分'): continue
        selected=(wanted | ({_norm(optional)} if optional else set())) or set(by_name)
        items.append({'doc_id':did,'title':j['title'],'company':j['company'],'city':j['locations'],
                      'family':j['job_family'],'url':j['url'],
                      'evidence':[by_name[n] for n in sorted(selected)]})
    return {'total':len(items),'items':items[:limit], 'method':'词典与局部规则；未人工验证；未说明不等于必备'}


def api_gap(q):
    fam = (q.get("family") or ["算法"])[0]
    have = {_norm(s) for s in (q.get("have") or [""])[0].split(",") if s.strip()}
    cnt = Counter()
    for did, names in _state["skills"].items():
        if _state["jobs"][did]["job_family"] == fam:
            for n in names:
                cnt[n] += 1
    miss = [{"skill": k, "jobs": v} for k, v in cnt.most_common(50) if _norm(k) not in have]
    return {"family": fam, "have": len(have),
            "missing": miss[:20], "total_missing": len(miss), "meaning": "未掌握的岗位提及技能，不代表必备或录用条件"}


def api_job(doc_id):
    j = _state["jobs"].get(doc_id)
    if not j:
        return None
    return {"doc_id": doc_id, "title": j["title"], "company": j["company"],
            "family": j["job_family"], "city": j["locations"],
            "education": j.get("education_level"), "experience": j.get("experience_years"),
            "skills": _state["skills"].get(doc_id, []), "url": j["url"]}


class Handler(BaseHTTPRequestHandler):
    def _send(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):  # noqa: N802
        # BaseHTTPRequestHandler 按 latin-1 解请求行，中文参数需要转回 utf-8
        raw = self.path.encode("latin-1", "ignore").decode("utf-8", "ignore")
        u = urlparse(raw)
        q = parse_qs(u.query)
        try:
            if u.path == "/evidence":
                with open(os.path.join(ROOT, "app", "evidence.html"), "rb") as fh:
                    body = fh.read()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            if u.path == "/api/evidence":
                return self._send(api_evidence(q))
            if u.path == "/api/stats":
                return self._send(api_stats(q))
            if u.path == "/api/skills":
                return self._send(api_skills(q))
            if u.path == "/api/jobs":
                return self._send(api_jobs(q))
            if u.path == "/api/gap":
                return self._send(api_gap(q))
            if u.path.startswith("/api/job/"):
                doc = api_job(unquote(u.path[len("/api/job/"):]))
                return self._send(doc) if doc else self._send({"error": "not found"}, 404)
            if u.path in ("/", "/api"):
                return self._send({"service": "JobSkill-KG API", "endpoints":
                                   ["/api/stats", "/api/skills", "/api/jobs", "/api/gap", "/api/job/<doc_id>"]})
            self._send({"error": "not found"}, 404)
        except Exception as exc:  # noqa: BLE001
            self._send({"error": repr(exc)[:200]}, 500)

    def log_message(self, *args):  # 静默
        pass


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--host", default="127.0.0.1")
    args = ap.parse_args()
    load()
    srv = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"JobSkill-KG API -> http://{args.host}:{args.port}/api/stats  (Ctrl+C 退出)")
    srv.serve_forever()


if __name__ == "__main__":
    main()
