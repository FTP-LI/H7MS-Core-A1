"""Inspect official parts through a disposable page in the pinned project."""
import json,zipfile,sys
import native_design as n
from eda_bridge import execute,export_project
LIB='0819f05c4eef4c71ace90d822a990e87'
path=n.HERE/'core-revision-library-search.json'
data=json.loads(path.read_text(encoding='utf-8'))
queries=['STPS3H100U','045101.5MRL','SMBJ48A','SRP5030TA-150M','XAL5030-153MEC','GRM32ER72A225KA35L','GRM31CR61C226KE15L','RC0402FR-0788K7L','RC0402FR-0724K9L','PESD3V3U2BT','TFM-110-02-L-D-A','SFM-110-02-L-D-A']
for q in queries:
    if q in {r['q'] for r in data}:continue
    items=execute('return await eda.lib_Device.search('+json.dumps(q)+','+json.dumps(LIB)+',undefined,undefined,15,1);')
    data.append(dict(q=q,items=items));path.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    print(q,[(i.get('supplierId'),i.get('manufacturerId')) for i in items[:5]],flush=True)
cat={i['supplierId']:i for r in data for i in r['items']}
cat={**n.catalog(),**cat}
codes=['C161691','C161692','C2983876','C189892','C3445864','C5815189','C428721','C22405313','C22450813','C2940504','C3322905']
tag=sys.argv[1] if len(sys.argv)>1 else ''
if len(sys.argv)>2:codes=sys.argv[2:]
statepath=n.HERE/('revision-inspection-state'+tag+'.json')
assert not statepath.exists(),'Inspection already started; inspect journal before resuming'
pid=execute('return await eda.dmt_Schematic.createSchematicPage("2121c62f1518d7c9");')
assert pid
state={'page':pid,'components':{}};statepath.write_text(json.dumps(state),encoding='utf-8')
execute('await eda.dmt_Schematic.modifySchematicPageName('+json.dumps(pid)+',"TEMP_官方连接器封装核对_随后删除");await eda.dmt_EditorControl.openDocument('+json.dumps(pid)+');await new Promise(r=>setTimeout(r,700));return true;')
guard='if((await eda.dmt_SelectControl.getCurrentDocumentInfo()).uuid!=='+json.dumps(pid)+')throw new Error("Wrong inspection page");'
for i,code in enumerate(codes):
    d=cat[code];payload=dict(uuid=d['uuid'],libraryUuid=d['libraryUuid'])
    rec=execute(guard+'const c=await eda.sch_PrimitiveComponent.create('+json.dumps(payload)+','+str(200+i%4*300)+','+str(1000-i//4*300)+',undefined,0,false,false,false);if(!c)throw new Error("Inspection placement failed");const a=c.toAsync();a.setState_Designator('+json.dumps('TMP'+str(i+1))+');await a.done();return {component:await eda.sch_PrimitiveComponent.get(c.getState_PrimitiveId()),pins:await eda.sch_PrimitiveComponent.getAllPinsByPrimitiveId(c.getState_PrimitiveId())};')
    state['components'][code]=rec;statepath.write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding='utf-8')
    print('inspected',code,[(p['pinNumber'],p['pinName']) for p in rec['pins']],flush=True)
execute(guard+'return await eda.sch_Document.save();')
archive=n.HERE/('source-backup/H7MS-official-library-inspection'+tag+'-20261017.epro')
print(export_project(archive),flush=True)
z=zipfile.ZipFile(archive);dest=n.HERE/'core-revision-library-source.json';out=json.loads(dest.read_text(encoding='utf-8')) if dest.exists() else {}
for code,rec in state['components'].items():
    c=rec['component'];out[code]=dict(search=cat[code],component=c,pins=rec['pins'])
    for kind,suffix in [('symbol','esym'),('footprint','efoo')]:
        out[code][kind]=z.read(kind.upper()+'/'+c[kind]['uuid']+'.'+suffix).decode()
(n.HERE/'core-revision-library-source.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
assert execute('return await eda.dmt_Schematic.deleteSchematicPage('+json.dumps(pid)+');')
state['deleted']=True;statepath.write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding='utf-8')
execute('await eda.dmt_EditorControl.openDocument("d9b9b220117e6b4c");return true;')
print('Temporary inspection page removed',flush=True)
