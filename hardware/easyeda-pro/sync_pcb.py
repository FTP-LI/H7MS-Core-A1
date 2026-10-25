from eda_bridge import execute
import json
r=execute('await eda.dmt_EditorControl.openDocument("497aabae1f192fa8");await new Promise(r=>setTimeout(r,800));return {components:await eda.pcb_PrimitiveComponent.getAll(),source:await eda.sys_FileManager.getDocumentSource()};')
open('hardware/easyeda-pro/pcb-before-sync.json','w',encoding='utf-8').write(json.dumps(r,ensure_ascii=False,indent=2));print('PCB components',len(r['components']));print([(c.get('designator'),c.get('uniqueId')) for c in r['components']][:8]);print(execute('return await eda.pcb_Document.importChanges("2121c62f1518d7c9");'))
