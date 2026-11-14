"""Score only completed human annotations against the frozen extractor and samples."""
import hashlib
import json
from pathlib import Path
from evidence import ROOT, extract
PACK=ROOT/'eval/holdout_v1'
def validate(rows,manifest,mode="human"):
    expected = ("ai_annotated", "ai_self_reviewed") if mode == "ai" else ("human_annotated", "human_reviewed")
    if len(rows)!=manifest['n']:raise ValueError('Incomplete sample count')
    originals={r['id']:r for r in manifest['samples']}
    if len({r['id'] for r in rows})!=len(rows):raise ValueError('Duplicate sample id')
    for r in rows:
        if any(r.get(k)!=v for k,v in originals[r['id']].items()):raise ValueError('Sample changed')
        if (r.get('status'),r.get('review_status')) != expected:
            raise ValueError(f"Sample {r['id']} awaits human annotation/review")
        if not r.get('annotator','').strip() or not r.get('reviewer','').strip() or (mode == 'human' and r['annotator']==r['reviewer']):
            raise ValueError('Two distinct human identifiers required')
        seen=set()
        for s in r['spans']:
            start,end=s['start'],s['end']
            if not isinstance(start,int) or not isinstance(end,int) or not 0<=start<end<=len(r['text']):raise ValueError('Invalid span')
            if r['text'][start:end]!=s['text'] or s['label'] not in ('K','S','T','L'):raise ValueError('Invalid span text/type')
            key=(start,end,s['label'])
            if key in seen:raise ValueError('Duplicate span')
            seen.add(key)
            if s['necessity'] not in ('必备','加分','未说明','不要求','冲突'):raise ValueError('Invalid necessity')
            if s['proficiency'] not in ('了解','熟悉','精通','未说明','冲突'):raise ValueError('Invalid proficiency')

def prf(tp,np,ng):
    return {'tp':tp,'predicted':np,'gold':ng,'precision':tp/np if np else 0,
            'recall':tp/ng if ng else 0,'f1':2*tp/(np+ng) if np+ng else 0}

def overlap_count(pred,gold):
    # Maximum bipartite matching, so one long prediction cannot count twice.
    matching={}
    def augment(g,seen):
        for p in sorted(pred):
            if p in seen or p[2]!=g[2] or max(p[0],g[0])>=min(p[1],g[1]):continue
            seen.add(p)
            if p not in matching or augment(matching[p],seen):matching[p]=g;return True
        return False
    return sum(augment(g,set()) for g in sorted(gold))

def score(rows,predictions):
    tp=ng=np=relaxed=matched=0; correct={'necessity':0,'proficiency':0};errors=[]
    per={k:[0,0,0] for k in 'KSTL'}
    for r,spans in zip(rows,predictions):
        pred={(s['start'],s['end'],s['label']):s for s in spans}
        gold={(s['start'],s['end'],s['label']):s for s in r['spans']}
        keys=pred.keys() & gold.keys();tp+=len(keys);np+=len(pred);ng+=len(gold)
        relaxed+=overlap_count(pred,gold)
        for label in per:
            per[label][0]+=sum(k[2]==label for k in keys)
            per[label][1]+=sum(k[2]==label for k in pred)
            per[label][2]+=sum(k[2]==label for k in gold)
        for k in keys:
            if all(prop in pred[k] for prop in correct):
                matched+=1
                for prop in correct:correct[prop]+=pred[k][prop]==gold[k][prop]
        if pred.keys()!=gold.keys():
            errors.append({'id':r['id'],'text':r['text'],
                'missed':[gold[k] for k in sorted(gold.keys()-pred.keys())],
                'extra':[pred[k] for k in sorted(pred.keys()-gold.keys())]})
    return {'exact':prf(tp,np,ng),'overlap_same_label':prf(relaxed,np,ng),
            'per_label':{k:prf(*v) for k,v in per.items()},
            'modifier_accuracy_on_exact_matches':{k:v/matched if matched else None for k,v in correct.items()},
            'modifier_matched_denominator':matched},errors

def bert_predict(rows):
    import torch
    from transformers import AutoTokenizer,AutoModelForTokenClassification
    from eval_ner import tags_to_spans,ID2LABEL
    model_dir=ROOT/'models/jobskill-ner'
    tok=AutoTokenizer.from_pretrained(model_dir,local_files_only=True)
    model=AutoModelForTokenClassification.from_pretrained(model_dir,local_files_only=True).eval()
    predictions=[];truncated=0
    with torch.no_grad():
        for start in range(0,len(rows),8):
            batch=rows[start:start+8]
            enc=tok([r['text'] for r in batch],max_length=128,truncation=True,padding=True,return_offsets_mapping=True,return_tensors='pt')
            offsets=enc.pop('offset_mapping');logits=model(**enc).logits.argmax(-1)
            for r,offs,ids in zip(batch,offsets.tolist(),logits.tolist()):
                tags=['O']*len(r['text']);last=0
                for (a,b),lid in zip(offs,ids):
                    if b<=a:continue
                    last=max(last,b)
                    for i in range(a,min(b,len(tags))):tags[i]=ID2LABEL[lid]
                truncated+=bool(r['text'][last:].strip())
                predictions.append([{'start':a,'end':b,'label':label,'text':r['text'][a:b]} for a,b,label in tags_to_spans(tags)])
    return predictions,{'max_length':128,'truncated_sentences':truncated,'model_sha256':hashlib.sha256((model_dir/'model.safetensors').read_bytes()).hexdigest()}

def main():
    import argparse
    ap=argparse.ArgumentParser();ap.add_argument('--ai',action='store_true');ap.add_argument('--bert',action='store_true');args=ap.parse_args()
    manifest=json.loads((PACK/'manifest.json').read_text())
    for name,digest in manifest['sha256'].items():
        if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=digest:raise ValueError('Frozen input changed: '+name)
    path=PACK/('ai_annotations.jsonl' if args.ai else 'annotations.jsonl')
    rows=list(map(json.loads,path.read_text().splitlines()));validate(rows,manifest,'ai' if args.ai else 'human')
    predictions=[]
    for r in rows:
        predictions.append([dict(start=s['evidence']['start'],end=s['evidence']['end'],text=s['evidence']['surface'],label=s['label'],proficiency=s['proficiency'],necessity=s['necessity']) for s in extract({'requirement':r['text']})])
    (PACK/"dictionary_predictions.json").write_text(json.dumps(predictions,ensure_ascii=False))
    result,errors=score(rows,predictions)
    methods={'dictionary_v2':result}
    if args.bert:
        pred,info=bert_predict(rows);res,err=score(rows,pred);methods['bert']=dict(res,configuration=info)
        (PACK/'bert_predictions.json').write_text(json.dumps(pred,ensure_ascii=False))
        (PACK/'bert_errors.jsonl').write_text(''.join(json.dumps(e,ensure_ascii=False)+'\n' for e in err))
    (PACK/'dictionary_errors.jsonl').write_text(''.join(json.dumps(e,ensure_ascii=False)+'\n' for e in errors))
    report={'status':'ai_self_reviewed' if args.ai else 'human_reviewed','n':len(rows),'methods':methods,
            'scope':'balanced families; same-agent AI annotation/self-review is not independent human gold; modifiers conditional on exact span matches',
            'annotations_sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
    (PACK/('ai_report.json' if args.ai else 'report.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2))
    print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
