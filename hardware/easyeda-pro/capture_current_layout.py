import json
from pathlib import Path
import native_design as n
from eda_bridge import execute
s=n.load_state()['CORE'];out={}
for page,pid in s['pages'].items():
    out[page]=execute('await eda.dmt_EditorControl.openDocument('+json.dumps(pid)+');await new Promise(r=>setTimeout(r,250));const cs=await eda.sch_PrimitiveComponent.getAll();const ws=await eda.sch_PrimitiveWire.getAll();const attrs={};const pins={};for(const p of [...cs,...ws]){attrs[p.primitiveId]=await eda.sch_PrimitiveAttribute.getAll(p.primitiveId);}for(const c of cs){pins[c.primitiveId]=await eda.sch_PrimitiveComponent.getAllPinsByPrimitiveId(c.primitiveId);}return {components:cs,wires:ws,texts:await eda.sch_PrimitiveText.getAll(),attrs,pins};')
    print(page,len(out[page]['components']),len(out[page]['wires']),flush=True)
(n.HERE/'compact-current.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
print(execute('return await eda.sch_Drc.check(true,false,true);'))

