"""Single graph source for JSON-LD and TSV node/edge export."""
import csv
import hashlib
import json
from pathlib import Path
from collections import Counter, defaultdict
from urllib.parse import quote

BASE='http://data.openkg.cn/dataset/jobskill-kg#'
def iri(key): return BASE+quote(key,safe=':')
def ref(key): return {'@id':iri(key)}

def build(root, canon, skill_type, category_of):
    root=Path(root); out=root/'data/kg'; out.mkdir(exist_ok=True)
    jobs={j['doc_id']:j for j in map(json.loads,(root/'data/processed/jobs.jsonl').open())}
    records=list(map(json.loads,(root/'data/processed/job_skills.jsonl').open()))
    normalized={}; metadata={}; counts=Counter(); families=defaultdict(Counter)
    for r in records:
        merged={}
        for s in r['skills']:
            if 'evidence' not in s: raise ValueError('Run extract/evidence.py first')
            name=canon(s['text'])
            if s['necessity']=='不要求': continue
            m=merged.setdefault(name,{'name':name,'proficiency':'未说明','necessity':'未说明','evidence':[]})
            ev=dict(s['evidence'], proficiency=s['proficiency'], necessity=s['necessity'])
            if ev not in m['evidence']: m['evidence'].append(ev)
        for name,m in merged.items():
            for prop in ('proficiency','necessity'):
                values={e[prop] for e in m['evidence'] if e[prop]!='未说明'}
                m[prop]=next(iter(values)) if len(values)==1 else ('冲突' if values else '未说明')
            counts[name]+=1; families[jobs[r['doc_id']]['job_family']][name]+=1
            typ=skill_type(name); metadata[name]={'type':typ,'category':category_of(name,typ)}
        # Keep zero-skill jobs in all formats; they are valid observations.
        normalized[r['doc_id']]=list(merged.values())
    graph={}
    def node(key,typ,name=None,**props):
        obj={'@id':iri(key),'@type':typ}
        if name is not None: obj['name']=name
        obj.update(props); graph[key]=obj
        return obj
    for name,m in metadata.items():
        node('category:'+m['category'],'cns:SkillCategory',m['category'])
        node('skill:'+name,'cns:Skill',name,**{'cns:skillType':m['type'],'cns:inCategory':ref('category:'+m['category'])})
    for did,j in jobs.items():
        company='company:'+j['company']; family='family:'+j['job_family']
        node(company,'Organization',j['company']); node(family,'cns:JobFamily',j['job_family'])
        cities=[]
        for city in j['locations']:
            node('city:'+city,'Place',city); cities.append(ref('city:'+city))
        obj=node(did,'JobPosting',j['title'],**{'url':j['url'],'hiringOrganization':ref(company),
            'jobLocation':cities,'cns:belongsToFamily':ref(family),
            'cns:educationLevel':j.get('education_level','未说明'),
            'cns:experienceYears':j.get('experience_years','未说明'),
            'cns:requiresSkill':[],'cns:hasRequirement':[]})
        for m in normalized.get(did,[]):
            name=m['name']; key='requirement:'+hashlib.sha256((did+'|'+name).encode()).hexdigest()[:24]
            obj['cns:requiresSkill'].append(ref('skill:'+name)); obj['cns:hasRequirement'].append(ref(key))
            # Evidence retained privately with verbatim quote; public graph has source and offsets.
            node(key,'cns:JobRequirement',name,**{'cns:forSkill':ref('skill:'+name),
                 'cns:proficiency':m['proficiency'],'cns:necessity':m['necessity'],
                 'cns:evidence':json.dumps([{k:v for k,v in e.items() if k not in ('quote','surface')} for e in m['evidence']],ensure_ascii=False)})
    ctx=json.loads((root/'schema/context.jsonld').read_text())['@context']
    def save(name,keys):
        (out/name).write_text(json.dumps({'@context':ctx,'@graph':[graph[k] for k in sorted(keys)]},ensure_ascii=False,indent=2))
    save('full.jsonld',graph)
    selected=[]; per=Counter()
    for did,j in jobs.items():
        if per[j['job_family']]<20: selected.append(did);per[j['job_family']]+=1
    reverse={v['@id']:k for k,v in graph.items()}
    def links(obj):
        for value in obj.values():
            for x in value if isinstance(value,list) else [value]:
                if isinstance(x,dict) and '@id' in x: yield reverse[x['@id']]
    selected=set(selected); todo=list(selected)
    while todo:
        for key in links(graph[todo.pop()]):
            if key not in selected: selected.add(key);todo.append(key)
    save('sample.jsonld',selected)
    edges=[]
    with (out/'nodes.csv').open('w') as f:
        writer=csv.writer(f,delimiter='\t');writer.writerow([':ID',':LABEL','name','properties'])
        for key,obj in sorted(graph.items()):
            literals={k:v for k,v in obj.items() if k not in ('@id','@type','name') and not isinstance(v,(dict,list))}
            writer.writerow([obj['@id'],obj['@type'],obj.get('name',''),json.dumps(literals,ensure_ascii=False)])
            for prop,value in obj.items():
                for v in value if isinstance(value,list) else [value]:
                    if isinstance(v,dict) and '@id' in v: edges.append((obj['@id'],prop,v['@id']))
    with (out/'edges.csv').open('w') as f:
        writer=csv.writer(f,delimiter='\t');writer.writerow([':START_ID',':TYPE',':END_ID']);writer.writerows(edges)
    with (out/'job_skills_norm.jsonl').open('w') as f:
        for did,ss in normalized.items(): f.write(json.dumps({'doc_id':did,'skills':ss},ensure_ascii=False)+'\n')
    def entry(name,count): return dict(skill=name,jobs=count,**metadata[name])
    by_family={fam:[entry(n,c) for n,c in cnt.most_common(30)] for fam,cnt in families.items()}
    by_category=defaultdict(list)
    for name,c in counts.most_common(): by_category[metadata[name]['category']].append(entry(name,c))
    stats={'jobs':len(jobs),'jobs_with_skills':sum(bool(x) for x in normalized.values()),
           'skills':len(metadata),'categories':len(by_category),'nodes':len(graph),'edges':len(edges),
           'by_family':dict(Counter(j['job_family'] for j in jobs.values())),
           'by_company':dict(Counter(j['company'] for j in jobs.values())),
           'by_category':dict(Counter(m['category'] for m in metadata.values())),
           'top_skills':[entry(n,c) for n,c in counts.most_common(50)],
           'avg_skills_per_job':round(sum(counts.values())/len(jobs),2),'version':'0.2.0'}
    from rdflib import Graph
    rdf=Graph().parse(out/'full.jsonld',format='json-ld'); stats['rdf_triples']=len(rdf)
    for name,value in [('stats',stats),('skills_by_family',by_family),('skills_by_category',by_category)]:
        (out/(name+'.json')).write_text(json.dumps(value,ensure_ascii=False,indent=2))
    print({k:stats[k] for k in ['jobs','jobs_with_skills','skills','nodes','edges','rdf_triples']})
