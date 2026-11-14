import csv
import json
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src/extract'),str(ROOT/'src/app')]
from evidence import extract
import serve_api

class Extraction(unittest.TestCase):
    def test_scope_and_offsets(self):
        text='熟悉 Python，具有 PyTorch 项目经验者优先。无需 Java；使用 Go 开发。Google 平台。'
        rows=extract({'requirement':text}, [('Python','K'),('PyTorch','K'),('Java','K'),('Go','K')])
        by={r['text']:r for r in rows}
        self.assertEqual(by['Python']['necessity'],'未说明')
        self.assertEqual(by['PyTorch']['necessity'],'加分')
        self.assertEqual(by['Java']['necessity'],'不要求')
        self.assertEqual(sum(r['text']=='Go' for r in rows),1)
        for r in rows:
            e=r['evidence'];self.assertEqual(text[e['start']:e['end']],e['surface'])
    def test_query_optional(self):
        old=serve_api._state.copy()
        try:
            serve_api._state.update(jobs={'j':{'title':'算法','company':'甲','locations':['杭州'],'job_family':'算法','url':'https://example.org'}},requirements={'j':[{'name':'Python','necessity':'未说明','evidence':[]},{'name':'大语言模型','necessity':'加分','evidence':[]}]})
            q={'city':['杭州'],'family':['算法'],'skills':['Python'],'optional_skill':['LLM']}
            self.assertEqual(serve_api.api_evidence(q)['total'],1)
            serve_api._state['requirements']['j'][1]['necessity']='冲突'
            self.assertEqual(serve_api.api_evidence(q)['total'],0)
        finally: serve_api._state.clear();serve_api._state.update(old)

class GraphIntegrity(unittest.TestCase):
    def test_exports_and_provenance(self):
        from rdflib import Graph,URIRef,RDF,OWL,RDFS
        p=ROOT/'data/kg'
        ld=json.loads((p/'full.jsonld').read_text()); nodes=ld['@graph']; ids={n['@id'] for n in nodes}
        self.assertEqual(len(ids),len(nodes))
        csv_nodes=list(csv.DictReader((p/'nodes.csv').open(),delimiter='\t'))
        self.assertEqual(ids,{r[':ID'] for r in csv_nodes})
        rdf=Graph().parse(p/'full.jsonld',format='json-ld')
        schema=Graph().parse(ROOT/'schema/cns_jobskill.ttl',format='turtle')
        for edge in csv.DictReader((p/'edges.csv').open(),delimiter='\t'):
            self.assertIn(edge[':END_ID'],ids);self.assertIn(edge[':START_ID'],ids)
            pred=edge[':TYPE'].replace('cns:','http://data.openkg.cn/dataset/jobskill-kg#') if edge[':TYPE'].startswith('cns:') else 'https://schema.org/'+edge[':TYPE']
            self.assertIn((URIRef(edge[':START_ID']),URIRef(pred),URIRef(edge[':END_ID'])),rdf)
        for prop in schema.subjects(RDF.type,OWL.ObjectProperty):
            for subject,obj in rdf.subject_objects(prop):
                self.assertIsInstance(obj,URIRef)
                for cls in schema.objects(prop,RDFS.range): self.assertIn((obj,RDF.type,cls),rdf)
        jobs={j['doc_id']:j for j in map(json.loads,(ROOT/'data/processed/jobs.jsonl').open())}
        for r in map(json.loads,(p/'job_skills_norm.jsonl').open()):
            for sk in r['skills']:
                for e in sk['evidence']:
                    source=jobs[r['doc_id']][e['field']]
                    self.assertEqual(source[e['start']:e['end']],e['surface'])
                    self.assertEqual(source[e['quote_start']:e['quote_start']+len(e['quote'])],e['quote'])
        stats=json.loads((p/'stats.json').read_text())
        self.assertEqual(stats['jobs'],len(jobs));self.assertEqual(stats['rdf_triples'],len(rdf))

if __name__=='__main__':unittest.main()
