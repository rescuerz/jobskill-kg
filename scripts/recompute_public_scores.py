"""Verify cached prediction scores, without claiming model-training reproducibility."""
import hashlib
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src/extract'))
from score_holdout import score,validate
PACK=ROOT/'eval/holdout_v1'
manifest=json.loads((PACK/'manifest.json').read_text())
rows=list(map(json.loads,(PACK/'ai_annotations.jsonl').read_text().splitlines()))
validate(rows,manifest,'ai')
report=json.loads((PACK/'ai_report.json').read_text())
assert hashlib.sha256((PACK/'ai_annotations.jsonl').read_bytes()).hexdigest()==report['annotations_sha256']
for name,filename in [('dictionary_v2','dictionary_predictions.json'),('bert','bert_predictions.json')]:
    pred=json.loads((PACK/filename).read_text());assert len(pred)==len(rows)
    result,_=score(rows,pred)
    for key,value in result.items():assert value==report['methods'][name][key],(name,key)
    print(name,'cached exact F1:',result['exact']['f1'])
