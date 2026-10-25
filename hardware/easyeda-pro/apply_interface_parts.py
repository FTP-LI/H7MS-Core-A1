"""Apply tracked R4 parts directly; preserve existing page/part identities where possible."""
import json,uuid,re,shutil,sys
from collections import Counter
import native_design as n
from eda_bridge import execute,export_project
rp=n.HERE/'core-interface-revision.json';rev=json.loads(rp.read_text(encoding='utf-8'))
jp=n.HERE/'interface-revision-progress.json';journal=json.loads(jp.read_text(encoding='utf-8')) if jp.exists() else {}
def log():jp.write_text(json.dumps(journal,ensure_ascii=False,indent=2),encoding='utf-8')
if not journal:
    print(export_project(n.HERE/'source-backup/H7MS-before-R4-interfaces-20261017.epro'),flush=True)
    shutil.copyfile(n.STATE,n.HERE/'native-state-before-R4.json')
    shutil.copyfile(n.HERE/'compact-current.json',n.HERE/'layout-before-R4.json')
    journal['backup']=True;log()
rev['enabled']=True;rp.write_text(json.dumps(rev,ensure_ascii=False,indent=2),encoding='utf-8')
s=n.prepare_pages('CORE')['CORE'];rows=n.input_components('CORE')
for page in (sys.argv[1:] or ['C06','C07','C05','C08','C09']):
    pid=s['pages'][page];guard='if((await eda.dmt_SelectControl.getCurrentDocumentInfo()).uuid!=='+json.dumps(pid)+')throw new Error("Wrong H735 page");'
    execute('await eda.dmt_EditorControl.openDocument('+json.dumps(pid)+');await new Promise(r=>setTimeout(r,300));return true;')
    execute(guard+'return await eda.dmt_Schematic.modifySchematicPageName('+json.dumps(pid)+','+json.dumps(n.PAGE_NAMES[page],ensure_ascii=False)+');')
    if page in ['C06','C07'] and page not in journal.get('cleared',[]):
        execute(guard+'const w=await eda.sch_PrimitiveWire.getAll();if(w.length)await eda.sch_PrimitiveWire.delete(w.map(x=>x.primitiveId));const f=(await eda.sch_PrimitiveComponent.getAll()).filter(c=>c.componentType==="netflag");if(f.length)await eda.sch_PrimitiveComponent.delete(f.map(x=>x.primitiveId));const t=await eda.sch_PrimitiveText.getAll();if(t.length)await eda.sch_PrimitiveText.delete(t.map(x=>x.primitiveId));return await eda.sch_Document.save();')
        journal.setdefault('cleared',[]).append(page);log()
    existing_refs=[r['native_reference'] for r in s['components'].values() if r['page']==page and r.get('native_reference')]
    base= {'C05':600,'C06':700,'C07':800,'C08':900,'C09':1000,'C10':1100}[page];counts=Counter()
    for ref in existing_refs:
        match=re.match(r'([A-Z]+)(\d+)$',ref)
        if match:counts[match[1]]=max(counts[match[1]],int(match[2])-base)
    for idx,row in enumerate(r for r in rows if r['page']==page):
        ref=row['reference'];old=s['components'].get(ref);d=row['device']
        if old and old.get('deviceUuid')==d['uuid']:continue
        if old and ref not in ['J_USB','J1','J2','J_XT30']:continue
        native=old.get('native_reference') if old else None
        if not native:
            prefix=re.match('[A-Z]+',ref)[0];counts[prefix]+=1;native=prefix+str(base+counts[prefix])
        payload=dict(ref=ref,native=native,device={k:d[k] for k in ('uuid','libraryUuid')},unique=uuid.uuid4().hex,x=200+(idx%5)*200,y=950-(idx//5)*130,bom=row.get('assembly')!='DNP' and not ref.startswith('TP_'))
        record=execute(guard+'const i='+json.dumps(payload)+';const c=await eda.sch_PrimitiveComponent.create(i.device,i.x,i.y,undefined,0,false,i.bom,true);if(!c)throw new Error("Create failed "+i.ref);const a=c.toAsync();a.setState_UniqueId(i.unique);a.setState_Designator(i.native);a.setState_OtherProperty({...c.getState_OtherProperty(),H7MS_Function:i.ref,H7MS_Revision:"R4",H7MS_Assembly:i.bom?"FIT":"DNP"});await a.done();return {id:c.getState_PrimitiveId(),pins:await eda.sch_PrimitiveComponent.getAllPinsByPrimitiveId(c.getState_PrimitiveId())};')
        n.pin_map(row,record)
        if old:
            journal.setdefault('replaced',{})[ref]=old;log()
            assert execute(guard+'return await eda.sch_PrimitiveComponent.delete('+json.dumps(old['id'])+');')
        record.update(page=page,supplierId=d['supplierId'],deviceUuid=d['uuid'],uniqueId=payload['unique'],native_reference=native,wired=False)
        s['components'][ref]=record;state=n.load_state();state['CORE']=s;n.save_state(state)
        print('placed',ref,native,d['supplierId'],flush=True)
    execute(guard+'return await eda.sch_Document.save();')
journal['parts_complete']=True;log();n.export_input('CORE')
