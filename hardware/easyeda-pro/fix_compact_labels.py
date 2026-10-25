import json
from eda_bridge import execute
import native_design as n
from functional_layout import ATTR_JS
before=json.load(open(n.HERE/'compact-before.json',encoding='utf-8'));plans=json.load(open(n.HERE/'compact-plan.json',encoding='utf-8'));s=n.load_state()['CORE']
for page,d in before.items():
 execute('await eda.dmt_EditorControl.openDocument('+json.dumps(s['pages'][page])+');return true;')
 ts={t['primitiveId']:t for t in d['texts']};payload=[{**ts[t['id']],**t} for t in plans[page]['texts']]
 ids=[t['id'] for t in payload]
 execute('await eda.sch_PrimitiveText.delete('+json.dumps(ids)+');for(const t of '+json.dumps(payload,ensure_ascii=False)+'){await eda.sch_PrimitiveText.create(t.x,t.y,t.content,0,"#213547",undefined,t.fontSize,t.bold,false,false,1);}return true;')
 amap={a['id']:a for a in plans[page]['attrs']};parts=[]
 for c in d['components']:
  if c['componentType']!='part':continue
  ref=c.get('otherProperty',{}).get('H7MS_Function','');two=len(d['pins'][c['primitiveId']])==2
  align=3 if not two or c['rotation'] in (90,270) else 6
  for a in d['attrs'][c['primitiveId']]:
   if a['primitiveId'] in amap and a.get('key') in ('Name','Designator'):parts.append({**amap[a['primitiveId']],'size':7 if a['key']=='Designator' else 6,'align':align})
 execute(ATTR_JS+'for(const i of '+json.dumps(parts)+'){await style(await eda.sch_PrimitiveAttribute.get(i.id),i.x,i.y,i.size,i.align,0,true);}await eda.sch_Document.save();return true;')
print(execute('return await eda.sch_Drc.check(true,false,true);'))
