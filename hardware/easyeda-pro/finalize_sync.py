import json,hashlib,zipfile
from pathlib import Path
import native_design as n
from eda_bridge import execute

execute('await eda.dmt_EditorControl.openDocument("497aabae1f192fa8");return true;')
result=execute('if((await eda.dmt_SelectControl.getCurrentDocumentInfo()).uuid!=="497aabae1f192fa8")throw new Error("Wrong PCB");const before=await eda.pcb_PrimitiveComponent.getAll();const ok=await eda.pcb_Document.importChanges("2121c62f1518d7c9");if(!ok)throw new Error("PCB synchronization failed");const saved=await eda.pcb_Document.save();const after=await eda.pcb_PrimitiveComponent.getAll();return {ok,saved,before,after,layers:await eda.pcb_Layer.getAllLayers()};')
def pose(cs):return {c['uniqueId']:(c['x'],c['y'],c['rotation'],c['layer']) for c in cs}
result['placement_preserved']=pose(result['before'])==pose(result['after'])
assert result['saved'] and result['placement_preserved']
(n.HERE/'pcb-sync-verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
path=n.HERE/'source-backup/H7MS-H735-compact-placed-final-20261017.epro2'
if path.exists():raise FileExistsError(path)
r=execute('const f=await eda.sys_FileManager.getProjectFile(undefined,undefined,"epro2");if(!f)throw new Error("Export failed");return {name:f.name,bytes:Array.from(new Uint8Array(await f.arrayBuffer()))};')
path.write_bytes(bytes(r['bytes']))
with zipfile.ZipFile(path) as z:assert z.testzip() is None
print({'synced':result['ok'],'saved':result['saved'],'placement_preserved':result['placement_preserved'],'parts':len(result['after']),'backup':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
