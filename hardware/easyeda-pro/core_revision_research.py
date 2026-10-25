"""Read official library candidates without editing library documents."""
import json
import native_design as n
from eda_bridge import execute
LIB='0819f05c4eef4c71ace90d822a990e87'
queries=['LM5013','PESD5V0S2UT','TFM-110-02-L-D-A','SFM-110-02-L-D-A','SMBJ60A','SS310','TPS2553DBVR','BM02B-GHS-TBT']
path=n.HERE/'core-revision-library-search.json'
data=json.loads(path.read_text(encoding='utf-8'))
existing={r['q'] for r in data}
for q in queries:
    if q in existing:continue
    items=execute('return await eda.lib_Device.search('+json.dumps(q)+','+json.dumps(LIB)+',undefined,undefined,20,1);')
    data.append(dict(q=q,items=items));path.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    print(q,[(i.get('supplierId'),i.get('manufacturerId'),i.get('footprintName')) for i in items[:8]],flush=True)
cat={i['supplierId']:i for r in data for i in r['items']}
chosen=['C161691','C161692','C2983876','C189892','C3445864','C5815189','C428721','C22405313']
out={}
dest=n.HERE/'core-revision-library-source.json'
if dest.exists():out=json.loads(dest.read_text(encoding='utf-8'))
for code in chosen:
    if code in out:continue
    d=cat[code];details=execute('return await eda.lib_Device.get('+json.dumps(d['uuid'])+','+json.dumps(LIB)+');')
    rec=dict(search=d,device=details)
    for kind in ['symbol','footprint']:
        a=details['association'][kind];K=kind.capitalize()
        execute('return await eda.lib_'+K+'.openInEditor('+json.dumps(a['uuid'])+','+json.dumps(a['libraryUuid'])+');')
        rec[kind]=execute('if((await eda.dmt_SelectControl.getCurrentDocumentInfo()).uuid!=='+json.dumps(a['uuid'])+')throw new Error("Wrong library document");return await eda.sys_FileManager.getDocumentSource();',guard=False)
        execute('await eda.dmt_EditorControl.openDocument("d9b9b220117e6b4c");return true;',guard=False)
    out[code]=rec;dest.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    print('captured official sources',code,flush=True)
