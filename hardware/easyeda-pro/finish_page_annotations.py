import json,sys
import native_design as n
from eda_bridge import execute
from layout_interface_revision import plan,Route
from functional_layout import on_segment
page=sys.argv[1];state=n.load_state();s=state['CORE'];pid=s['pages'][page];p=plan(page)
guard='if((await eda.dmt_SelectControl.getCurrentDocumentInfo()).uuid!=='+json.dumps(pid)+')throw new Error("Wrong page");'
execute('await eda.dmt_EditorControl.openDocument('+json.dumps(pid)+');await new Promise(r=>setTimeout(r,1500));return true;')
existing=execute(guard+'return await eda.sch_PrimitiveText.getAll();')
for note in p.notes:
    if any(note['text'] in [t.get('content'),t.get('text'),t.get('value')] for t in existing):continue
    execute(guard+'const t=await eda.sch_PrimitiveText.create('+','.join(json.dumps(v,ensure_ascii=False) for v in [note['x'],note['y'],note['text'],0,'#213547',None,note['size'],note['size']>=10,False,False,1])+');if(!t)throw new Error("Text failed");return t.getState_PrimitiveId();')
live=execute(guard+'await eda.sch_Document.save();return await eda.sch_PrimitiveWire.getAll();')
for row in [r for r in n.input_components('CORE') if r['page']==page]:
    rec=s['components'][row['reference']];nets=n.pin_map(row,rec);rec['connections']=[]
    for pin in rec['pins']:
        number=pin['pinNumber'];net=nets[number]
        if net=='NC':rec['connections'].append(dict(pin=number,nc=True));continue
        pt=(round(pin['x'],5),round(pin['y'],5));match=[]
        for w in live:
            line=w['line']
            if w['net']==net and any(on_segment(pt,tuple(line[i:i+2]),tuple(line[i+2:i+4])) for i in range(0,len(line),4)):match.append(w)
        assert match,(row['reference'],number,net)
        rec['connections'].append(dict(pin=number,net=net,id=match[0]['primitiveId']))
    rec.update(wired=True,revision='R4B',functional_layout=True)
n.save_state(state);print('Annotations and live connections verified',page)
