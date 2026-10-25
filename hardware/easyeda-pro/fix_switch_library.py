"""Repair only escaped contact numbers; preserve the supplier footprint geometry."""
import json
import zipfile
from pathlib import Path
from eda_bridge import execute
from native_design import catalog, HERE

path = HERE / 'corrected-switch-library.json'
lib = 'e5af7ca27c24475d8c8223cdd36b7089'
original = catalog()['C79167']
z = zipfile.ZipFile(HERE / 'source-backup/H7MS-native-wired-before-footprint-audit-20261017.epro')
symbol = [json.loads(s) for s in z.read('SYMBOL/b2549c1d3f2fa9ca.esym').decode().splitlines()]
footprint = [json.loads(s) for s in z.read('FOOTPRINT/c86a7f6361adcc0b.efoo').decode().splitlines()]
mapping = {"1'": '3', "2'": '4', '1&apos;': '3', '2&apos;': '4'}
for r in symbol:
    if r[0] == 'ATTR' and r[3] in ('NUMBER', 'NAME'):
        r[4] = mapping.get(r[4], r[4])
for r in footprint:
    if r[0] == 'PAD':
        r[5] = mapping.get(r[5], r[5])
record = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {'libraryUuid':lib, 'supplierId':'C79167', 'mapping':mapping}
def save():
    path.write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
if not record.get('symbolUuid'):record['symbolUuid'] = execute(f'return await eda.lib_Symbol.create({json.dumps(lib)},"H7MS_EVQP7A01P_1234");')
save()
if not record.get('footprintUuid'):record['footprintUuid'] = execute(f'return await eda.lib_Footprint.create({json.dumps(lib)},"H7MS_EVQP7A01P_1234");')
save()
for key, records in [('Symbol',symbol),('Footprint',footprint)]:
    uid = record[key.lower()+'Uuid']
    if not uid:raise RuntimeError('Library creation failed')
    for r in records:
        if r[0]=='HEAD' and key=='Footprint':
            r[1].update(uuid=uid,title='H7MS_EVQP7A01P_1234')
            r[1].pop('source',None)
    if record.get(key.lower()+'Updated'):continue
    execute(f'return await eda.lib_{key}.openInEditor({json.dumps(uid)},{json.dumps(lib)});',guard=False)
    count = execute('return (await eda.'+('sch_PrimitivePin' if key=='Symbol' else 'pcb_PrimitivePad')+'.getAll()).length;',guard=False)
    if count:raise RuntimeError('Nonempty correction editor; inspect before resuming')
    code='const EPCB_LayerId={TOP:1,TOP_SILKSCREEN:3,COMPONENT_SHAPE:48};const EPCB_PrimitivePadShapeType={RECTANGLE:"RECT"};const EPCB_PrimitivePadType={NORMAL:0};'
    if key=='Symbol':
        attrs={(r[2],r[3]):r[4] for r in records if r[0]=='ATTR'}
        for r in records:
            if r[0]=='PIN':
                args=[r[4],r[5],attrs[(r[1],'NUMBER')],attrs[(r[1],'NAME')],r[7],r[6]]
                code+='if(!await eda.sch_PrimitivePin.create('+','.join(json.dumps(a) for a in args)+'))throw new Error("Pin create failed");'
            elif r[0]=='POLY':code+='await eda.sch_PrimitivePolygon.create('+json.dumps(r[2])+',null,"none",1);'
            elif r[0]=='CIRCLE':code+='await eda.sch_PrimitiveCircle.create('+','.join(map(str,r[2:5]))+',null,"none",1);'
        code+='return await eda.sch_Document.save();'
    else:
        for r in records:
            if r[0]=='PAD':
                code+='if(!await eda.pcb_PrimitivePad.create(EPCB_LayerId.TOP,'+','.join(json.dumps(a) for a in [r[5],r[6],r[7],r[8]])+',[EPCB_PrimitivePadShapeType.RECTANGLE,41.339,55.118,0],"",null,0,0,0,false,EPCB_PrimitivePadType.NORMAL,undefined,{topSolderMask:1.9685,topPasteMask:0}))throw new Error("Pad create failed");'
            elif r[0]=='POLY':
                points=[v for v in r[6] if v!='L']
                layer='EPCB_LayerId.TOP_SILKSCREEN' if r[4]==3 else 'EPCB_LayerId.COMPONENT_SHAPE'
                for i in range(0,len(points)-2,2):
                    code+='await eda.pcb_PrimitiveLine.create("",'+layer+','+','.join(map(str,points[i:i+4]+[r[5]]))+');'
        code+='return await eda.pcb_Document.save();'
    ok=execute(code,guard=False)
    record[key.lower()+'Updated']=ok;save()
    if not ok:raise RuntimeError('Library source update failed: '+key)
association = {k:{'uuid':record[k+'Uuid'],'libraryUuid':lib} for k in ('symbol','footprint')}
association['model3D']={'uuid':original['model3DUuid'],'libraryUuid':original['libraryUuid']}
props=dict(name='={Manufacturer Part}',designator='SW?',manufacturer=original['manufacturer'],manufacturerId='EVQP7A01P',supplier='LCSC',supplierId='C79167',addIntoBom=True,addIntoPcb=True,otherProperty={k:v for k,v in original['otherProperty'].items() if k not in ('Symbol','Footprint','3D Model')})
if not record.get('deviceUuid'):record['deviceUuid']=execute('return await eda.lib_Device.create('+','.join(json.dumps(x,ensure_ascii=False) for x in [lib,'H7MS_EVQP7A01P_1234',[],association,'Original C79167 copper pads and silkscreen; contacts 1/3 and 2/4 replace apostrophe pad aliases.',props])+');',guard=False)
save()
print(json.dumps(record,ensure_ascii=False,indent=2))
