"""Move only annotations; preserve every component and wire connection."""
import json
import native_design as n
from eda_bridge import execute
from functional_layout import ATTR_JS,on_segment

state=n.load_state();s=state['CORE']
data=json.loads((n.HERE/'compact-current.json').read_text(encoding='utf-8'))
for page,d in data.items():
    if page=='C01':continue
    changes=[]
    for c in d['components']:
        if c['componentType']=='netflag':
            for a in d['attrs'][c['primitiveId']]:
                if a['key']=='Name' and a.get('valueVisible'):
                    changes.append(dict(id=a['primitiveId'],x=c['x'],y=c['y']-25,size=6,align=6))
        if c['componentType']!='part' or len(d['pins'][c['primitiveId']])!=2:continue
        pins=d['pins'][c['primitiveId']]
        if abs(pins[0]['x']-pins[1]['x'])>0.001:continue
        for w in d['wires']:
            ln=w['line']
            if len(ln)!=4 or abs(ln[0]-ln[2])>.001:continue
            hits=[any(abs(p['x']-ln[k])<.001 and abs(p['y']-ln[k+1])<.001 for p in pins) for k in (0,2)]
            if sum(hits)!=1:continue
            free=ln[2:] if hits[0] else ln[:2]
            pin=ln[:2] if hits[0] else ln[2:]
            for a in d['attrs'][w['primitiveId']]:
                if a['key']=='Name' and a.get('valueVisible') and a.get('rotation') in (90,270):
                    changes.append(dict(id=a['primitiveId'],x=free[0]-4,y=free[1]+3 if free[1]>pin[1] else free[1]-7,size=6,align=9))
    if page=='C04':
        a=next(a for a in d['attrs'][s['components']['U_IMU']['id']] if a['key']=='Name')
        changes.append(dict(id=a['primitiveId'],x=a['x']+88,y=a['y'],size=6,align=3))
    execute('await eda.dmt_EditorControl.openDocument('+json.dumps(s['pages'][page])+');return true;')
    guard='if((await eda.dmt_SelectControl.getCurrentDocumentInfo()).uuid!=='+json.dumps(s['pages'][page])+')throw new Error("Wrong SCH");'
    execute(guard+ATTR_JS+'for(const i of '+json.dumps(changes)+'){await style(await eda.sch_PrimitiveAttribute.get(i.id),i.x,i.y,i.size,i.align,0,true);}await eda.sch_Document.save();return true;')
    print(page,'annotation fixes',len(changes),flush=True)
for rec in s['components'].values():
    d=data[rec['page']];pins=d['pins'][rec['id']];rec['pins']=pins
    for con in rec['connections']:
        if con.get('nc'):continue
        pin=next(p for p in pins if p['pinNumber']==con['pin'])
        ids=[]
        for w in d['wires']:
            ln=w['line']
            if w['net']==con['net'] and any(on_segment((round(pin['x'],5),round(pin['y'],5)),tuple(ln[k:k+2]),tuple(ln[k+2:k+4])) for k in range(0,len(ln),4)):
                ids.append(w['primitiveId'])
        if not ids:raise ValueError(('missing wire',rec['native_reference'],con))
        con['id']=ids[0];con['wire_ids']=ids
s['layout_revision']='module-compact-20261017';n.save_state(state)
legacy=json.loads((n.HERE/'functional-layout-state.json').read_text(encoding='utf-8'))
legacy['_status']='superseded; historical primitive IDs; use native-state.json and compact-current.json'
(n.HERE/'functional-layout-state.json').write_text(json.dumps(legacy,ensure_ascii=False,indent=2),encoding='utf-8')
