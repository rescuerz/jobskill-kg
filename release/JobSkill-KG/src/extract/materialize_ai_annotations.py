"""Materialize explicitly authored AI span decisions; never read model predictions."""
import json
import re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];PACK=ROOT/'eval/holdout_v1'
def main():
    decisions=json.loads((PACK/'ai_span_decisions.json').read_text())
    notes={9:'至少一门表示选择条件，不把每种语言都标成必备。',14:'优先仅修饰后半句 ElasticSearch/Druid。',
           23:'中文全名与括号别名单独标注；嵌套术语保留最长完整术语。',
           47:'专业和学历要求不是技能提及。',52:'至少一种或两种语言为选择条件。',
           53:'游戏知识在本岗位中是明确的领域知识要求，保留而非按技术词典范围删去。',
           54:'语言至少一种，不逐项视为必备；优先只修饰数据治理和数据安全。',
           57:'公司工作领域介绍，未提出应聘者能力或具体职责，不标技能。',
           75:'专业与学历，不标技能。',83:'专业与学历，不标技能。',89:'专业与学历，不标技能。',
           94:'动作整体标注；平台名称单独为知识类，允许较长动作边界。'}
    rows=[]
    for line in (PACK/'annotations.jsonl').read_text().splitlines():
        r=json.loads(line);spans=[];occupied=set()
        choices=[v.split('|') for v in decisions[str(r['id'])].split(';') if v]
        for choice in sorted(choices,key=lambda x:-len(x[0])):
            term,label,*mods=choice; matches=list(re.finditer(re.escape(term),r['text']))
            if not matches:raise ValueError((r['id'],term))
            for m in matches:
                positions=set(range(m.start(),m.end()))
                if positions & occupied:continue
                occupied |= positions
                spans.append({'start':m.start(),'end':m.end(),'text':m.group(),'label':label,
                              'proficiency':mods[0] if mods else '未说明',
                              'necessity':mods[1] if len(mods)>1 else '未说明'})
        r.update(spans=sorted(spans,key=lambda s:s['start']),status='ai_annotated',
                 annotator='Codex AI / root',reviewer='Codex AI / root / self-review',
                 review_status='ai_self_reviewed',review_note=notes.get(r['id'],'按原句审阅，采用不重叠技能片段；无明确程度/必要性时不作推定。'))
        rows.append(r)
    (PACK/'ai_annotations.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows))
    print(len(rows),'sentences;',sum(len(r['spans']) for r in rows),'spans; no human review claimed')
if __name__=='__main__':main()
