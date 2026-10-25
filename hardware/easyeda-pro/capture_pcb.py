import json,zipfile,collections
from eda_bridge import execute
r=execute('await eda.dmt_EditorControl.openDocument("497aabae1f192fa8");const c=await eda.pcb_PrimitiveComponent.getAll();const pp={};const bb={};for(const i of c){pp[i.designator]=await eda.pcb_PrimitiveComponent.getAllPinsByPrimitiveId(i.primitiveId);bb[i.designator]=await eda.pcb_Primitive.getPrimitivesBBox([i.primitiveId]);}return {components:c,pads:pp,bbox:bb,source:await eda.sys_FileManager.getDocumentSource()};')
open('hardware/easyeda-pro/pcb-synced.json','w',encoding='utf-8').write(json.dumps(r,ensure_ascii=False,indent=2))
print(len(r['components']),r['pads']['J801'][:2],r['bbox']['J801'])
z=zipfile.ZipFile('hardware/easyeda-pro/source-backup/H7MS-compact-before-pcb-20261017.epro')
for c in r['components']:
 if c['designator'] in ['J801','J701','U101','SW401','Y401']:
  f=[json.loads(l) for l in z.read('FOOTPRINT/'+c['footprint']['uuid']+'.efoo').decode().splitlines()]
  print(c['designator'],c['footprint']);print([p for p in f if p[0] in ['PAD','FILL','POLY']][:7])
