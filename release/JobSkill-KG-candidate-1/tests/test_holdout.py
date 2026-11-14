import copy
import json
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src/extract'))
from score_holdout import validate,score,overlap_count
class Evaluation(unittest.TestCase):
    def test_overlap_one_to_one(self):
        self.assertEqual(overlap_count({(0,10,'K')},{(0,4,'K'),(5,10,'K')}),1)
        self.assertEqual(overlap_count({(0,10,'K'),(0,4,'K')},{(0,4,'K'),(5,10,'K')}),2)
    def test_ai_cannot_count_as_human(self):
        pack=ROOT/'eval/holdout_v1'
        manifest=json.loads((pack/'manifest.json').read_text())
        rows=list(map(json.loads,(pack/'ai_annotations.jsonl').read_text().splitlines()))
        validate(rows,manifest,'ai')
        with self.assertRaises(ValueError):validate(rows,manifest,'human')
        changed=copy.deepcopy(rows);changed[0]['text']+='changed'
        with self.assertRaises(ValueError):validate(changed,manifest,'ai')
    def test_known_metrics(self):
        gold=[{'id':1,'text':'abcdef','spans':[{'start':0,'end':2,'label':'K'},{'start':3,'end':6,'label':'S'}]}]
        pred=[[{'start':0,'end':2,'label':'K'},{'start':3,'end':5,'label':'S'},{'start':5,'end':6,'label':'K'}]]
        r,_=score(gold,pred)
        self.assertEqual(r['exact']['tp'],1)
        self.assertEqual(r['overlap_same_label']['tp'],2)
        self.assertEqual(r['exact']['f1'],0.4)
        self.assertIsNone(r['modifier_accuracy_on_exact_matches']['necessity'])
if __name__=='__main__':unittest.main()
