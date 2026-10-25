"""Direct API authoring in the existing project; never imports a project file.

Inputs retain the earlier connection plan. Explicit sourcing changes below are
exported with the native input so a netlist review can reproduce every decision.
"""
import csv
import json
import uuid
from pathlib import Path
from eda_bridge import execute

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
PLAN = ROOT / 'docs/H7MS/工程规划'
STATE = HERE / 'native-state.json'
PAGE_NAMES = {
    'C01':'C01A_H735主控与信号分配', 'C01B':'C01B_主控SMPS与电源去耦',
    'C02':'C02_3V3降压与扩展电源保护', 'C03':'C03_时钟复位启动与SWD',
    'C04':'C04_BMI088与加热安全控制', 'C05':'C05_CAN三路收发与保护',
    'C06':'C06_USB设备接口与VBUS检测', 'C07':'C07_板间连接器与测试点',
    'C08':'C08_四组UART直立接口', 'C09':'C09_SPI_I2C自定义排针与接口供电',
    'C10':'C10_XT30宽压输入与5V电源',
}

SELECT = {
    'TPS62132RGTR': 'C337502',
    'X1G004171001500': 'C256004',
    'TFM-125-02-L-D-A-TR': 'C17489091',
    'SFM-125-02-L-D-A-TR': 'C7076347',
    'PESD2CANFD24V-T,215': 'C552486',
    'USBLC6-2SC6': 'C7519',
    'SN74LVC1G08DBVR': 'C7666',
    'SN74LVC1G125DBVR': 'C23654',
    'SN74LVC1G17DBVR': 'C7836',
    'CDSOT23-SM712': 'C404012',
    'XFL4020-222MEC': 'C122469',
    '10k': 'C60490', '100k': 'C60491', '1k': 'C106235',
    '100R': 'C106232', '22R': 'C114765', '5.1k 1%': 'C105872',
    '45.3k 1%': 'C137977', '60.4R 1%': 'C245987',
    '120R 1%': 'C17909', '10k 0.1%': 'C190095', '20k 0.1%': 'C705630',
    'C1608C0G1H103J080AA': 'C22400107',
    'C1608C0G1H221J080AA': 'C71693',
    'B2B-PH-SM4-TB(LF)(SN)': 'C265003',
}

def read_csv(name):
    with (PLAN / name).open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))

def catalog():
    result = {}
    for query in json.loads((HERE / 'lcsc-library-comparison.json').read_text(encoding='utf-8')):
        for item in query['items']:
            result[item['supplierId']] = item
    research=HERE/'core-revision-library-search.json'
    if research.exists():
        for query in json.loads(research.read_text(encoding='utf-8')):
            for item in query['items']:
                result[item['supplierId']]=item
    fixed = HERE / 'corrected-can-library.json'
    if fixed.exists():
        correction = json.loads(fixed.read_text(encoding='utf-8'))
        if correction.get('deviceUuid'):
            result['C2671243'] = dict(result['C2671243'], uuid=correction['deviceUuid'],
                libraryUuid=correction['libraryUuid'], symbolUuid=correction['symbolUuid'])
    fixed_switch = HERE / 'corrected-switch-library.json'
    if fixed_switch.exists():
        correction = json.loads(fixed_switch.read_text(encoding='utf-8'))
        if correction.get('deviceUuid'):
            result['C79167'] = dict(result['C79167'], uuid=correction['deviceUuid'],
                libraryUuid=correction['libraryUuid'], symbolUuid=correction['symbolUuid'],
                footprintUuid=correction['footprintUuid'], footprintName='H7MS_EVQP7A01P_1234')
    fixed_usb = HERE / 'corrected-usb-library.json'
    if fixed_usb.exists():
        correction = json.loads(fixed_usb.read_text(encoding='utf-8'))
        if correction.get('deviceUuid'):
            result['C5184243'] = dict(result['C5184243'], uuid=correction['deviceUuid'],
                libraryUuid=correction['libraryUuid'], footprintUuid=correction['footprintUuid'],
                footprintName=correction.get('name','H7MS_USB4105_GF_A_120_B4'))
    tp = HERE / 'testpoint-library.json'
    if tp.exists():
        d=json.loads(tp.read_text(encoding='utf-8'))
        if d.get('deviceUuid'):
            result['LOCAL_TP_0.8']=dict(uuid=d['deviceUuid'],libraryUuid=d['libraryUuid'],
                manufacturerId='PCB_TP_0.8',supplierId='LOCAL_TP_0.8',footprintUuid=d['footprintUuid'])
    xt=HERE/'corrected-xt30-library.json'
    if xt.exists():
        d=json.loads(xt.read_text(encoding='utf-8'))
        if d.get('deviceUuid'):
            result['C428721']=dict(result['C428721'],uuid=d['deviceUuid'],libraryUuid=d['libraryUuid'],footprintUuid=d['footprintUuid'],footprintName='H7MS_XT30UPB_M_Drill1p90')
    return result

def input_components(board):
    cat = catalog()
    nets = read_csv('紧凑板原理图连接.csv')
    items = []
    for row in read_csv('紧凑板装配清单.csv'):
        if row['board'] != board:
            continue
        r = dict(row)
        r['pins'] = {p['pin']:p['net'] for p in nets if p['board']==board and p['reference']==r['reference']}
        key = SELECT.get(r['part'])
        if r['part'] == '0R':
            key = 'C96345' if any(n.startswith(('3V3','5V','VBAT')) for n in r['pins'].values()) else 'C60485'
        matches = [d for d in cat.values() if d.get('manufacturerId') == r['part'] and not d.get('supplierId','').startswith('C990')]
        device = cat.get(key) if key else (matches[0] if matches else None)
        r['device'] = device
        if board=='CORE' and r['reference']=='U2':
            r['pins']['5']='BUCK_FB'
            r['revision_note']='TPS62130A adjustable: FB must use the divider, never ground.'
        if r['page']=='C01' and r['reference']!='U1':
            r['page']='C01B'
        items.append(r)
    if board=='CORE':
        for ref,code,pins in [('R_FB_TOP','C861315',{'1':'3V3_D','2':'BUCK_FB'}),('R_FB_BOT','C852472',{'1':'BUCK_FB','2':'GND'})]:
            items.append(dict(board=board,page='C02',reference=ref,part=cat[code]['manufacturerId'],fit='YES',notes='0.8*(1+312k/100k)=3.296V nominal',pins=pins,device=cat[code]))
        revision=HERE/'core-interface-revision.json'
        if revision.exists():
            change=json.loads(revision.read_text(encoding='utf-8'))
            if change.get('enabled'):
                for row in items:
                    if row['reference'] in change['replace']:
                        row.update(change['replace'][row['reference']])
                        if 'supplierId' in row:row['device']=cat[row['supplierId']]
                for row in change['add']:
                    items.append(dict(board=board,fit='YES',**row,device=cat[row['supplierId']]))
    return items

def load_state():
    if STATE.exists():
        return json.loads(STATE.read_text(encoding='utf-8'))
    return {'CORE':{'schematic':'2121c62f1518d7c9','pages':{'C01':'d9b9b220117e6b4c'},'components':{'U1':{'id':'d275f28a3d9cea77','wired':True}}}}

def save_state(state):
    STATE.write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding='utf-8')

def prepare_pages(board):
    state=load_state(); s=state[board]
    for page in dict.fromkeys(x['page'] for x in input_components(board)):
        if page in s['pages']:continue
        uid=execute(f'return await eda.dmt_Schematic.createSchematicPage({json.dumps(s["schematic"])});')
        if not uid:raise RuntimeError('Page creation failed: '+page)
        s['pages'][page]=uid;save_state(state)
        renamed=execute(f'return await eda.dmt_Schematic.modifySchematicPageName({json.dumps(uid)},{json.dumps(page)});')
        if not renamed:raise RuntimeError('Page naming failed: '+page)
    return state

def place_page(board,page):
    state=load_state(); s=state[board]; pid=s['pages'][page]
    execute(f'await eda.dmt_EditorControl.openDocument({json.dumps(pid)});await new Promise(r=>setTimeout(r,1500));return await eda.dmt_SelectControl.getCurrentDocumentInfo();')
    items=[x for x in input_components(board) if x['page']==page]
    for index,row in enumerate(items):
        ref=row['reference']
        if ref in s['components'] or not row['device']:continue
        d=row['device']; x=180+(index%4)*265; y=-150-(index//4)*170
        if page=='C07':
            x=400+index*750;y=700
            if index>=2:x=200+((index-2)%5)*300;y=400-((index-2)//5)*110
        data={'device':{'libraryUuid':d['libraryUuid'],'uuid':d['uuid']},'x':x,'y':y,'ref':ref,'bom':not ref.startswith('TP_'),'page':pid,'uniqueId':uuid.uuid4().hex}
        code='const i='+json.dumps(data)+';if((await eda.dmt_SelectControl.getCurrentDocumentInfo()).uuid!==i.page)throw new Error("Page changed");const c=await eda.sch_PrimitiveComponent.create(i.device,i.x,i.y,undefined,0,false,i.bom,true);if(!c)throw new Error("Placement failed "+i.ref);const a=c.toAsync();a.setState_Designator(i.ref);a.setState_UniqueId(i.uniqueId);await a.done();return {id:c.getState_PrimitiveId(),pins:await eda.sch_PrimitiveComponent.getAllPinsByPrimitiveId(c.getState_PrimitiveId())};'
        record=execute(code); record['page']=page;record['supplierId']=d['supplierId'];record['wired']=False;record['uniqueId']=data['uniqueId'];record['deviceUuid']=d['uuid']
        s['components'][ref]=record;save_state(state)
        print('placed',board,page,ref,d['supplierId'],flush=True)
    execute('return await eda.sch_Document.save();')

def export_input(board):
    items=input_components(board)
    (HERE / f'native-{board}-input.json').write_text(json.dumps(items,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Missing devices:',[(x['reference'],x['part']) for x in items if not x['device']])

def pin_map(row, record):
    aliases = {}
    if row['part']=='TPS62132RGTR': aliases['17']='EP'
    if row['part']=='TCAN1042HGVDRBRQ1': aliases['9']='EP'
    if row['part']=='EVQP7A01P':
        aliases.update({'1':'1L','1&apos;':'1R',"1'":'1R','2':'2L','2&apos;':'2R',"2'":'2R','3':'1R','4':'2R'})
    if row['part']=='USB4105-GF-A-120':
        aliases.update({'A1-B12':'A1_B12','B1-A12':'B1_A12','A4-B9':'A4_B9','B4-A9':'B4_A9',
                        '1':'S1','2':'S2','3':'S3','4':'S4'})
    actual={p['pinNumber'] for p in record['pins']}
    mapped={aliases.get(p,p) for p in actual}
    if mapped != set(row['pins']):
        raise ValueError((row['reference'],'pin mismatch',mapped-set(row['pins']),set(row['pins'])-mapped))
    return {p:row['pins'][aliases.get(p,p)] for p in actual}

def short_name(row):
    d=row['device']; props=d.get('otherProperty',{})
    return props.get('Name',d['manufacturerId'])

def layout_page(board,page):
    state=load_state(); s=state[board]
    execute('return await eda.dmt_EditorControl.openDocument('+json.dumps(s['pages'][page])+');')
    rows=[r for r in input_components(board) if r['page']==page and r['reference'] in s['components']]
    if any(s['components'][r['reference']].get('wired') for r in rows):
        raise ValueError('Layout requires unwired components')
    execute('return await eda.dmt_Schematic.modifySchematicPageTitleBlock(true,{Size:{showTitle:false,showValue:false,value:"A3"}});')
    for idx,row in enumerate(rows):
        ref=row['reference'];rec=s['components'][ref]
        cols=5 if page=='C04' else 4
        x=210+(idx%cols)*(300 if cols==5 else 360);y=980-(idx//cols)*140
        if page=='C01':x,y=650,650
        if page=='C07': x=400+idx*750;y=700
        if page=='C05':
            if idx==0:x,y=200,1020
            else:
                ch=(idx-1)//6;local=(idx-1)%6
                x=300+ch*500;y=850-local*115
        data=dict(id=rec['id'],x=x,y=y,name=short_name(row))
        rec['pins']=execute('const i='+json.dumps(data)+';const c=await eda.sch_PrimitiveComponent.get(i.id);if(!c)throw new Error("Missing component");const a=c.toAsync();a.setState_X(i.x);a.setState_Y(i.y);a.setState_Name(i.name);await a.done();return await eda.sch_PrimitiveComponent.getAllPinsByPrimitiveId(i.id);')
        save_state(state)
    execute('return await eda.sch_Document.save();')
    print('layout',board,page,flush=True)

def wire_page(board,page):
    state=load_state();s=state[board]
    execute('return await eda.dmt_EditorControl.openDocument('+json.dumps(s['pages'][page])+');')
    rows=[r for r in input_components(board) if r['page']==page]
    for row in rows:
        ref=row['reference'];rec=s['components'].get(ref)
        if not rec or rec.get('wired'):continue
        pin_nets=pin_map(row,rec)
        payload={'id':rec['id'],'nets':pin_nets,'page':s['pages'][page]}
        code='const i='+json.dumps(payload)+';if((await eda.dmt_SelectControl.getCurrentDocumentInfo()).uuid!==i.page)throw new Error("Page changed");const pins=await eda.sch_PrimitiveComponent.getAllPinsByPrimitiveId(i.id);const result=[];for(const p of pins){const n=i.nets[p.pinNumber];if(!n)throw new Error("Unmapped pin "+p.pinNumber);if(n==="NC"){const a=p.toAsync();a.setState_NoConnected(true);await a.done();result.push({pin:p.pinNumber,nc:true});continue;}const dx=p.rotation===0?40:p.rotation===180?-40:0;const dy=p.rotation===90?40:p.rotation===270?-40:0;const w=await eda.sch_PrimitiveWire.create([p.x,p.y,p.x+dx,p.y+dy],n);if(!w)throw new Error("Wire failed");result.push({pin:p.pinNumber,net:n,id:w.getState_PrimitiveId()});}return result;'
        rec['connections']=execute(code);rec['wired']=True;save_state(state)
        print('wired',board,page,ref,len(pin_nets),flush=True)
    execute('return await eda.sch_Document.save();')

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('action',choices=['pages','place','input','layout','wire']);p.add_argument('--board',default='CORE');p.add_argument('--page')
    a=p.parse_args()
    if a.action=='pages':prepare_pages(a.board)
    elif a.action=='place':place_page(a.board,a.page)
    elif a.action=='input':export_input(a.board)
    elif a.action=='layout':layout_page(a.board,a.page)
    elif a.action=='wire':wire_page(a.board,a.page)
