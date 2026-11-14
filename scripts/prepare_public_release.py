"""Build an allowlisted public repository, excluding private raw data and model weights."""
import hashlib
import json
import shutil
import zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'release/JobSkill-KG'

def main():
    if OUT.exists():raise SystemExit('Release exists; inspect it before replacing')
    OUT.mkdir(parents=True)
    def copy(path):
        dst=OUT/path;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/path,dst)
    for folder in ['src/crawl','src/extract','src/build','schema']:
        for p in (ROOT/folder).rglob('*'):
            if p.is_file() and '__pycache__' not in p.parts and p.suffix in ('.py','.jsonld','.ttl','.md'):
                copy(p.relative_to(ROOT))
    for path in ['src/app/serve_api.py','src/app/build_site.py','src/app/build_pages.py','app/evidence.html','app/site/index.html','LICENSE','docs/report.md','docs/figures/evidence_query_v2.jpg','docs/api.md','docs/schema-v0.2.md','docs/evaluation-v0.2.md','docs/答辩讲稿-v0.2.md','data/lexicon/tech_skills.txt','scripts/recompute_public_scores.py','tests/test_holdout.py','tests/test_public_data.py','scripts/verify_publication.py','docs/PUBLISH.md','docs/README.md']:
        copy(Path(path))
    for p in (ROOT/'eval/holdout_v1').glob('*'):
        if p.is_file():copy(p.relative_to(ROOT))
    # Runtime data goes in one archive, avoiding large Git blobs and exposing only derived data.
    with zipfile.ZipFile(OUT/'JobSkill-KG-data.zip','w',zipfile.ZIP_DEFLATED) as z:
        for p in (ROOT/'data/kg').glob('*'):
            if p.is_file() and p.name!='job_skills_norm.jsonl':z.write(p,str(p.relative_to(ROOT)))
        public_jobs=[]
        for j in map(json.loads,(ROOT/'data/processed/jobs.jsonl').read_text().splitlines()):
            public_jobs.append({k:j[k] for k in ['doc_id','title','company','locations','job_family','url','crawled_at','education_level','experience_years']})
        z.writestr('data/processed/jobs.jsonl',''.join(json.dumps(j,ensure_ascii=False)+'\n' for j in public_jobs))
        norm=[];demo={'bytedance:7595090762887350581','bytedance:7665552336577775877','netease:79141'}
        for r in map(json.loads,(ROOT/'data/kg/job_skills_norm.jsonl').read_text().splitlines()):
            for s in r['skills']:
                old=s['evidence'];s['evidence']=[{k:v for k,v in e.items() if k not in ('quote','surface')} for e in old]
                if r['doc_id'] in demo and s['name'] in ('Python','PyTorch','大语言模型'):
                    i=next((i for i,e in enumerate(old) if e['necessity']==s['necessity']),0)
                    s['evidence'][i]['quote']=old[i]['quote']
            norm.append(r)
        z.writestr('data/kg/job_skills_norm.jsonl',''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in norm))
    (OUT/'requirements.txt').write_text('rdflib==7.6.0\nisodate>=0.6\nrequests>=2.31\n')
    (OUT/'requirements-model.txt').write_text('torch>=2.2\ntransformers>=4.40\n')
    (OUT/'.gitignore').write_text('__pycache__/\n*.pyc\n.venv/\nmodels/\ndata/raw/\ndata/processed/\ndata/kg/\n.pkgs/\n')
    copy(Path('docs/README-public.md'));shutil.move(OUT/'docs/README-public.md',OUT/'README.md')
    files={str(p.relative_to(OUT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(OUT.rglob('*')) if p.is_file()}
    (OUT/'SHA256SUMS.json').write_text(json.dumps(files,indent=2))
    print(len(files),'public files; archive bytes',(OUT/'JobSkill-KG-data.zip').stat().st_size)
if __name__=='__main__':main()
