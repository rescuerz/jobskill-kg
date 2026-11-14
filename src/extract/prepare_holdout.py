"""Create a blind, frozen 100-sentence human evaluation pack; never overwrite annotations."""
import hashlib
import json
import random
import re
from pathlib import Path
from collections import Counter,defaultdict
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'eval/holdout_v1'
def normalized(s): return re.sub(r'\s+','',s).lower()
def main():
    if OUT.exists(): raise SystemExit('Refusing to overwrite existing holdout pack')
    old=[json.loads(l) for l in (ROOT/'eval/domain_review.jsonl').open()]
    excluded={r['doc_id'] for r in old}; old_text={normalized(r['text']) for r in old}
    jobs=[json.loads(l) for l in (ROOT/'data/processed/jobs.jsonl').open()]
    rng=random.Random(20261114); rng.shuffle(jobs); buckets=defaultdict(list);seen=set()
    for j in jobs:
        if j['doc_id'] in excluded:continue
        candidates=[]
        for field in ('requirement','description'):
            for m in re.finditer(r'[^。；;\n]+',j.get(field) or ''):
                text=m.group();key=normalized(text)
                if 15<=len(text)<=180 and key not in seen and key not in old_text:
                    candidates.append((field,m.start(),text,key))
        if candidates:
            field,start,text,key=rng.choice(candidates);seen.add(key)
            buckets[j['job_family']].append({'doc_id':j['doc_id'],'family':j['job_family'],
                    'field':field,'source_start':start,'text':text})
    # Roughly balanced across families, not a population prevalence estimate.
    picked=[]
    while len(picked)<100:
        progressed=False
        for family in sorted(buckets):
            if buckets[family] and len(picked)<100:
                picked.append(buckets[family].pop());progressed=True
        if not progressed: raise ValueError('Insufficient unique unseen jobs')
    rng.shuffle(picked);OUT.mkdir()
    for i,r in enumerate(picked):
        r.update(id=i+1,spans=[],status='todo',annotator='',reviewer='',review_status='todo')
    (OUT/'annotations.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in picked))
    inputs=['data/processed/jobs.jsonl','data/lexicon/tech_skills.txt','src/extract/evidence.py']
    manifest={'seed':20261114,'n':100,'sampling':'one sentence per unseen job; balanced families; no skill-cue selection',
              'family_counts':dict(Counter(r['family'] for r in picked)),
              'excluded_previous_eval_docs':len(excluded),'status':'awaiting_human_annotation',
              'sha256':{f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in inputs},
              'samples':[{k:r[k] for k in ('id','doc_id','field','source_start','text')} for r in picked]}
    (OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
    print('Prepared',OUT)
if __name__=='__main__':main()
