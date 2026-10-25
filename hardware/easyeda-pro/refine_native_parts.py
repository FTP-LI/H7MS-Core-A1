"""Replace identified parts in place, preserving planned nets and recoverable records."""
import csv
import json
import re
import uuid
from collections import Counter
import native_design as n
from eda_bridge import execute

def guard(pid):
    return 'if((await eda.dmt_SelectControl.getCurrentDocumentInfo()).uuid!=='+json.dumps(pid)+')throw new Error("Active page changed");'

def replace_changed(force_references=()):
    state=n.load_state();s=state['CORE']
    for row in n.input_components('CORE'):
        ref=row['reference'];old=s['components'][ref];d=row['device'];pid=s['pages'][row['page']]
        switch=(ref.startswith('SW_') or ref=='J_USB') and old.get('deviceUuid')!=d['uuid']
        if old.get('supplierId',d['supplierId'])==d['supplierId'] and not switch and ref not in force_references:continue
        if old.get('functional_layout'):
            raise RuntimeError('This part now shares local wiring. Replace using a full page routing rebuild, not per-part wire deletion: '+ref)
        execute('await eda.dmt_EditorControl.openDocument('+json.dumps(pid)+');await new Promise(r=>setTimeout(r,1500));return await eda.dmt_SelectControl.getCurrentDocumentInfo();',guard=False)
        p=dict(oldId=old['id'],device={k:d[k] for k in ('uuid','libraryUuid')},ref=old.get('native_reference',ref),uniqueId=uuid.uuid4().hex)
        code=guard(pid)+'const i='+json.dumps(p)+';const old=await eda.sch_PrimitiveComponent.get(i.oldId);if(!old)throw new Error("Old part missing");const c=await eda.sch_PrimitiveComponent.create(i.device,old.x,old.y,undefined,old.rotation,old.mirror,true,true);if(!c)throw new Error("New part missing");const a=c.toAsync();a.setState_UniqueId(i.uniqueId);await a.done();return {id:c.getState_PrimitiveId(),pins:await eda.sch_PrimitiveComponent.getAllPinsByPrimitiveId(c.getState_PrimitiveId())};'
        new=execute(code)
        old['pending_replacement']=new;n.save_state(state)
        n.pin_map(row,new)
        wires=[w['id'] for w in old.get('connections',[]) if 'id' in w]
        code=guard(pid)+'if(!await eda.sch_PrimitiveWire.delete('+json.dumps(wires)+'))throw new Error("Wire delete failed");if(!await eda.sch_PrimitiveComponent.delete('+json.dumps(old['id'])+'))throw new Error("Part delete failed");const a=(await eda.sch_PrimitiveComponent.get('+json.dumps(new['id'])+')).toAsync();a.setState_Designator('+json.dumps(p['ref'])+');await a.done();return true;'
        execute(code)
        old.pop('pending_replacement',None)
        new.update(page=row['page'],supplierId=d['supplierId'],deviceUuid=d['uuid'],uniqueId=p['uniqueId'],wired=False,replaced=old)
        if old.get('native_reference'):new['native_reference']=old['native_reference']
        s['components'][ref]=new;n.save_state(state)
        n.wire_page('CORE',row['page']);state=n.load_state();s=state['CORE']
        print('replaced',ref,d['supplierId'],d.get('footprintName'),flush=True)

def annotate():
    state=n.load_state();s=state['CORE'];mapping=[]
    rows=n.input_components('CORE')
    for page_no,page in enumerate(n.PAGE_NAMES,1):
        pid=s['pages'][page];execute('await eda.dmt_EditorControl.openDocument('+json.dumps(pid)+');await new Promise(r=>setTimeout(r,1500));return await eda.dmt_SelectControl.getCurrentDocumentInfo();')
        counts=Counter();payload=[]
        for row in [r for r in rows if r['page']==page]:
            oldref=row['reference'];rec=s['components'][oldref]
            prefix=re.match('[A-Z]+',oldref)[0];counts[prefix]+=1
            ref=f'{prefix}{page_no*100+counts[prefix]}'
            payload.append(dict(id=rec['id'],ref=ref,name=n.short_name(row),function=oldref))
            rec['native_reference']=ref
            d=row['device']
            mapping.append(dict(page=n.PAGE_NAMES[page],reference=ref,function=oldref,manufacturer_part=d['manufacturerId'],supplier_id=d['supplierId'],package=d.get('footprintName','H7MS_TP_0p8'),assembly=row.get('fit','YES')))
        execute(guard(pid)+'const items='+json.dumps(payload,ensure_ascii=False)+';for(const i of items){const c=await eda.sch_PrimitiveComponent.get(i.id);if(!c)throw new Error("Missing part");const a=c.toAsync();a.setState_Designator(i.ref);a.setState_Name(i.name);a.setState_OtherProperty({...c.getState_OtherProperty(),H7MS_Function:i.function});await a.done();if((await eda.sch_PrimitiveComponent.get(i.id)).designator!==i.ref)throw new Error("Annotation did not persist");}await new Promise(r=>setTimeout(r,400));return await eda.sch_Document.save();')
        n.save_state(state);print('annotated',page,len(payload),flush=True)
    with (n.HERE/'核心板位号与封装对照.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(mapping[0]));w.writeheader();w.writerows(mapping)
    n.export_input('CORE')

if __name__=='__main__':
    replace_changed()
    annotate()
