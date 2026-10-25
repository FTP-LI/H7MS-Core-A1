import json
from eda_bridge import execute
from pathlib import Path
execute('await eda.dmt_EditorControl.openDocument("497aabae1f192fa8");return true;')
r=execute('const cs=await eda.pcb_PrimitiveComponent.getAll();const pads={},bbox={};for(const c of cs){pads[c.designator]=await eda.pcb_PrimitiveComponent.getAllPinsByPrimitiveId(c.primitiveId);bbox[c.designator]=await eda.pcb_Primitive.getPrimitivesBBox([c.primitiveId]);}return {components:cs,pads,bbox,source:await eda.sys_FileManager.getDocumentSource()};')
Path('hardware/easyeda-pro/pcb-placed.json').write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
print('pins',sum(len(p) for p in r['pads'].values()))
for ref in ['J801','J802','J701']:
 print(ref,[(p['padNumber'],round(p['x']*.0254,4),round(-p['y']*.0254,4),p['layer']) for p in r['pads'][ref]][:3])
drc=execute('return await eda.pcb_Drc.check(true,false,true);');Path('hardware/easyeda-pro/pcb-drc-details.json').write_text(json.dumps(drc,ensure_ascii=False,indent=2),encoding='utf-8');print([(g.get('name'),g.get('count')) for g in drc])
