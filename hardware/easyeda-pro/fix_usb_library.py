"""USB4105 B4 land pattern, built from the reviewed manufacturer-coordinate table."""
import csv
import json
from eda_bridge import execute
from native_design import HERE, PLAN, catalog

path=HERE/'corrected-usb-library.json'
lib='e5af7ca27c24475d8c8223cdd36b7089'
original=next(item for query in json.loads((HERE/'lcsc-library-comparison.json').read_text(encoding='utf-8')) for item in query['items'] if item.get('supplierId')=='C5184243')
record=json.loads(path.read_text(encoding='utf-8')) if path.exists() else dict(libraryUuid=lib,source='https://gct.co/files/drawings/usb4105.pdf',source_revision='B4',supplierId='C5184243')
library_name=record.get('name','H7MS_USB4105_GF_A_120_B4')
if not record.get('footprintUuid'):record['footprintUuid']=execute('return await eda.lib_Footprint.create('+json.dumps(lib)+','+json.dumps(library_name)+');')
footprint=record['footprintUuid']
def save():path.write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
save()
if not footprint:raise RuntimeError('Footprint creation failed')
execute('const tab=await eda.lib_Footprint.openInEditor('+json.dumps(footprint)+','+json.dumps(lib)+');if(!tab)throw new Error("Footprint editor unavailable");await new Promise(r=>setTimeout(r,1500));if((await eda.dmt_SelectControl.getCurrentDocumentInfo()).uuid!=='+json.dumps(footprint)+')throw new Error("Wrong footprint");return tab;',guard=False)
with (PLAN/'连接器与保护器件焊盘.csv').open(encoding='utf-8-sig') as f:
    rows=[r for r in csv.DictReader(f) if r['board']=='CORE' and r['reference']=='J_USB']
record['plannedPads']=rows;save()
if not record.get('geometrySaved'):
    if execute('return (await eda.pcb_PrimitivePad.getAll()).length;',guard=False):raise RuntimeError('Inspect partial geometry before resuming')
    aliases={'S1':'1','S2':'4','S3':'2','S4':'3'}
    code='const EPCB_LayerId={TOP:1,MULTI:12,TOP_SILKSCREEN:3,DOCUMENT:13};const EPCB_PrimitivePadShapeType={RECTANGLE:"RECT",OBLONG:"OVAL"};const EPCB_PrimitivePadHoleType={ROUND:"ROUND",SLOT:"SLOT"};const EPCB_PrimitivePadType={NORMAL:0};const EPCB_PrimitiveFillMode={SOLID:0};'
    for r in rows:
        x=float(r['x_mm'])/0.0254;y=-float(r['y_mm'])/0.0254
        w=float(r['width_mm'])/0.0254;h=float(r['height_mm'])/0.0254
        number=aliases.get(r['pad'],r['pad'].replace('_','-'))
        if r['type']=='NPTH':
            code+='await eda.pcb_PrimitiveFill.create(EPCB_LayerId.MULTI,eda.pcb_MathPolygon.createPolygon('+json.dumps(['CIRCLE',x,y,w/2])+'),"",EPCB_PrimitiveFillMode.SOLID,0);'
            continue
        is_slot=r['type']=='PTH_SLOT'
        layer='EPCB_LayerId.MULTI' if is_slot else 'EPCB_LayerId.TOP'
        shape='[EPCB_PrimitivePadShapeType.OBLONG,'+str(w)+','+str(h)+']' if is_slot else '[EPCB_PrimitivePadShapeType.RECTANGLE,'+str(w)+','+str(h)+',0]'
        hole='[EPCB_PrimitivePadHoleType.SLOT,'+str(float(r['drill_x_mm'])/0.0254)+','+str(float(r['drill_y_mm'])/0.0254)+']' if is_slot else 'null'
        paste='-1000' if is_slot else '0'
        args=layer+','+','.join(json.dumps(v) for v in [number,x,y,0])+','+shape+',"",'+hole+',0,0,'+('90,true' if is_slot else '0,false')+',EPCB_PrimitivePadType.NORMAL,undefined,{topSolderMask:1.968503937,bottomSolderMask:1.968503937,topPasteMask:'+paste+',bottomPasteMask:'+paste+'}'
        code+='{const p=await eda.pcb_PrimitivePad.create('+args+');if(!p)throw new Error("USB pad failed '+number+'");const a=p.toAsync();a.setState_PadNumber('+json.dumps(number)+');await a.done();}'
    for x in [-4.7,4.7]:
        code+='await eda.pcb_PrimitiveLine.create("",EPCB_LayerId.TOP_SILKSCREEN,'+','.join(str(v/0.0254) for v in [x,-1.9,x,-3.4,0.15])+');'
    code+='await eda.pcb_PrimitiveLine.create("",EPCB_LayerId.DOCUMENT,'+','.join(str(v/0.0254) for v in [-4.7,-7.355,4.7,-7.355,0.1])+');return {saved:await eda.pcb_Document.save(),pads:await eda.pcb_PrimitivePad.getAll()};'
    result=execute(code,guard=False);record['geometrySaved']=result['saved'];record['actualPads']=result['pads'];save()
if not record.get('deviceUuid'):
    association={'symbol':{'uuid':original['symbolUuid'],'libraryUuid':original['libraryUuid']},'footprint':{'uuid':footprint,'libraryUuid':lib}}
    excluded={'Symbol','Footprint','3D Model','3D Model Title','3D Model Transform'}
    props=dict(name='={Manufacturer Part}',designator='J?',manufacturer=original['manufacturer'],manufacturerId=original['manufacturerId'],supplier='LCSC',supplierId='C5184243',addIntoBom=True,addIntoPcb=True,otherProperty={k:v for k,v in original['otherProperty'].items() if k not in excluded})
    previous=record.get('superseded',{}).get('deviceUuid')
    if previous:
        ok=execute('return await eda.lib_Device.modify('+','.join(json.dumps(v,ensure_ascii=False) for v in [previous,lib,library_name,[],{'footprint':association['footprint']}])+');',guard=False)
        if not ok:raise RuntimeError('Existing device association update failed')
        record['deviceUuid']=previous
    else:
        record['deviceUuid']=execute('return await eda.lib_Device.create('+','.join(json.dumps(v,ensure_ascii=False) for v in [lib,library_name,[],association,'GCT B4 pad positions; B5=+1.25mm, A8=+1.75mm. No shell paste. 3D body intentionally unassociated pending exact model.',props])+');',guard=False)
    save()
print(json.dumps({k:v for k,v in record.items() if k not in ('plannedPads','actualPads','superseded')},ensure_ascii=False,indent=2))
