import csv
import json
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class PublicData(unittest.TestCase):
    def test_closed_consistent_graph(self):
        p=ROOT/'data/kg'
        if not (p/'full.jsonld').exists():self.skipTest('Unzip JobSkill-KG-data.zip first')
        nodes=json.loads((p/'full.jsonld').read_text())['@graph']; ids={n['@id'] for n in nodes}
        self.assertEqual(len(ids),len(nodes))
        with (p/'nodes.csv').open() as f:self.assertEqual(ids,{r[':ID'] for r in csv.DictReader(f,delimiter='\t')})
        links=set()
        for n in nodes:
            for prop,value in n.items():
                for v in value if isinstance(value,list) else [value]:
                    if isinstance(v,dict) and '@id' in v:
                        self.assertIn(v['@id'],ids);links.add((n['@id'],prop,v['@id']))
        with (p/'edges.csv').open() as f:csv_edges={(r[':START_ID'],r[':TYPE'],r[':END_ID']) for r in csv.DictReader(f,delimiter='\t')}
        self.assertEqual(links,csv_edges)
        stats=json.loads((p/'stats.json').read_text());self.assertEqual(stats['nodes'],len(nodes));self.assertEqual(stats['edges'],len(csv_edges))
if __name__=='__main__':unittest.main()
