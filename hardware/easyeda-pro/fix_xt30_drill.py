"""Copy official geometry and change only the two manufacturer drill diameters."""
import json
import native_design as n
from eda_bridge import execute
path=n.HERE/'corrected-xt30-library.json';lib='e5af7ca27c24475d8c8223cdd36b7089'
source=json.loads((n.HERE/'core-revision-library-source.json').read_text(encoding='utf-8'))['C428721']
d=source['search'];fp=source['component']['footprint'];name='H7MS_XT30UPB_M_Drill1p90'
r=json.loads(path.read_text(encoding='utf-8')) if path.exists() else dict(libraryUuid=lib,supplierId='C428721',source='reference-pdfs/xt30upb.pdf',change='Only PTH drill diameter 1.80 -> 1.90 mm, retain official pads/pitch/body')
def save():path.write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
if not r.get('footprintUuid'):
    r['footprintUuid']=execute('return await eda.lib_Footprint.create('+','.join(json.dumps(v) for v in [lib,name])+');');save()
assert r['footprintUuid']
if not r.get('geometrySaved'):
    uid=r['footprintUuid'];result=execute('const tab=await eda.lib_Footprint.openInEditor('+json.dumps(uid)+','+json.dumps(lib)+');if(!tab)throw new Error("Copied footprint unavailable");await new Promise(r=>setTimeout(r,1000));return {tab,info:await eda.dmt_SelectControl.getCurrentDocumentInfo()};')
    assert result['info']['uuid']==uid,result
    assert execute('return (await eda.pcb_PrimitivePad.getAll()).length;',guard=False)==0
    rr=[json.loads(line) for line in source['footprint'].splitlines() if line.strip()]
    code='const EPCB_LayerId={MULTI:12,TOP_SILKSCREEN:3,COMPONENT_SHAPE:48};const EPCB_PrimitivePadShapeType={ELLIPSE:"ELLIPSE"};const EPCB_PrimitivePadHoleType={ROUND:"ROUND"};const EPCB_PrimitivePadType={NORMAL:0};'
    for row in rr:
        if row[0]=='PAD':
            code+='await eda.pcb_PrimitivePad.create(EPCB_LayerId.MULTI,'+','.join(json.dumps(v) for v in [row[5],row[6],row[7],row[8]])+',[EPCB_PrimitivePadShapeType.ELLIPSE,98.425,98.425],"",[EPCB_PrimitivePadHoleType.ROUND,'+str(1.9/.0254)+'],0,0,0,true,EPCB_PrimitivePadType.NORMAL,undefined,{topSolderMask:1.9685,bottomSolderMask:1.9685,topPasteMask:-1000,bottomPasteMask:-1000});'
        elif row[0]=='POLY' and 'ARC' not in row[6]:
            xy=[v for v in row[6] if isinstance(v,(int,float))];layer='EPCB_LayerId.TOP_SILKSCREEN' if row[4]==3 else 'EPCB_LayerId.COMPONENT_SHAPE'
            for i in range(0,len(xy)-2,2):code+='await eda.pcb_PrimitiveLine.create("",'+layer+','+','.join(map(str,xy[i:i+4]+[row[5]]))+');'
    execute(code+'return await eda.pcb_Document.save();',guard=False)
    r['change']='Official copper diameter 2.50 mm and 5.00 mm pitch retained; drill 1.80 -> 1.90 mm. Straight body/silk edges retained; decorative arcs omitted. No PTH stencil openings.'
    r['pads']=execute('if((await eda.dmt_SelectControl.getCurrentDocumentInfo()).uuid!=='+json.dumps(uid)+')throw new Error("Wrong copied footprint");const pads=await eda.pcb_PrimitivePad.getAll();if(pads.length!==2)throw new Error("Unexpected pad count");for(const p of pads){const a=p.toAsync();a.setState_Hole(["ROUND",'+str(1.9/.0254)+']);await a.done();}await eda.pcb_Document.save();return await eda.pcb_PrimitivePad.getAll();',guard=False)
    r['geometrySaved']=True;save()
execute('await eda.dmt_EditorControl.openDocument("d9b9b220117e6b4c");return true;',guard=False)
if not r.get('deviceUuid'):
    assoc=dict(symbol={'uuid':d['symbolUuid'],'libraryUuid':d['libraryUuid']},footprint={'uuid':r['footprintUuid'],'libraryUuid':lib})
    props=dict(name='={Manufacturer Part}',designator='J?',manufacturer=d['manufacturer'],manufacturerId=d['manufacturerId'],supplier='LCSC',supplierId='C428721',addIntoBom=True,addIntoPcb=True,otherProperty={k:v for k,v in d['otherProperty'].items() if k not in ['Symbol','Footprint','3D Model','3D Model Title','3D Model Transform']})
    r['deviceUuid']=execute('return await eda.lib_Device.create('+','.join(json.dumps(v,ensure_ascii=False) for v in [lib,name,[],assoc,r['change'],props])+');');save()
assert r['deviceUuid'];print({k:v for k,v in r.items() if k!='pads'})
