"""Conservative dictionary extraction with source offsets; no model dependencies.
Offsets are Python Unicode character offsets in the named original field.
Modifiers are clause-local heuristics, not calibrated or human verified.
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def lexicon():
    rows = []
    for line in (ROOT/'data/lexicon/tech_skills.txt').read_text().splitlines():
        if line.strip() and not line.startswith('#'):
            parts = line.split('\t')
            rows.append((parts[0], parts[1] if len(parts)>1 else 'S'))
    return sorted(rows, key=lambda r: -len(r[0]))

def modifiers(clause, relative_start):
    if re.search(r'无需|不要求|不需要|无须|不必', clause):
        return '未说明', '不要求'
    optional = bool(re.search(r'优先|加分|更佳|\bplus\b|preferred', clause, re.I))
    required = bool(re.search(r'必须|必备|需具备|至少|要求', clause))
    # Ambiguous mixed scope is deliberately not resolved as mandatory.
    necessity = '未说明' if optional and required else ('加分' if optional else ('必备' if required else '未说明'))
    cues = list(re.finditer(r'精通|深入理解|熟练掌握|熟练使用|熟练|熟悉|掌握|了解|接触过', clause[:relative_start]))
    proficiency = '未说明'
    if cues:
        cue = cues[-1].group()
        proficiency = '精通' if cue in ('精通','深入理解') else ('了解' if cue in ('了解','接触过') else '熟悉')
    return proficiency, necessity

def extract(job, terms=None):
    terms = terms or lexicon()
    found = []
    for field in ('description','requirement'):
        text = job.get(field) or ''
        for clause_match in re.finditer(r'[^。；;\n，,]+', text):
            clause = clause_match.group()
            occupied = set()
            for term, label in terms:
                # Latin words must not match substrings such as Go in Google.
                pattern = re.escape(term)
                if re.match(r'[A-Za-z0-9]',term): pattern = r'(?<![A-Za-z0-9_])'+pattern
                if re.search(r'[A-Za-z0-9]$',term): pattern += r'(?![A-Za-z0-9_])'
                for m in re.finditer(pattern,clause,re.I):
                    positions = set(range(m.start(),m.end()))
                    if occupied & positions: continue
                    occupied |= positions
                    prof, nec = modifiers(clause,m.start())
                    found.append({'text':term,'label':label,'source':'lexicon','confidence':None,
                                  'proficiency':prof,'necessity':nec,
                                  'evidence':{'field':field,'start':clause_match.start()+m.start(),
                                  'end':clause_match.start()+m.end(),'surface':m.group(),
                                  'quote':clause,'quote_start':clause_match.start(),
                                  'url':job.get('url',''),'crawled_at':job.get('crawled_at','')}})
    return found

def main():
    terms=lexicon()
    source=ROOT/'data/processed/jobs.jsonl'
    target=ROOT/'data/processed/job_skills.jsonl'
    with target.open('w') as out:
        for line in source.open():
            j=json.loads(line)
            out.write(json.dumps({'doc_id':j['doc_id'],'job_family':j['job_family'],'skills':extract(j,terms)},ensure_ascii=False)+'\n')
    print(target)

if __name__=='__main__': main()
