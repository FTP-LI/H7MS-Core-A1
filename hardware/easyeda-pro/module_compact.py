"""Compact each functional module independently while preserving the wire graph."""
import json,math
import native_design as n
from eda_bridge import execute
from compact_schematic import Axis
from functional_layout import ATTR_JS,on_segment
S=n.load_state()['CORE'];D=json.loads((n.HERE/'compact-before.json').read_text(encoding='utf-8'))
for d in D.values():
 pins={(round(p['x'],5),round(p['y'],5)) for pp in d['pins'].values() for p in pp}
 flags={(round(c['x'],5),round(c['y'],5)) for c in d['components'] if c['componentType']=='netflag'}
 for w in d['wires']:
  if len(w['line'])!=4:continue
  a=tuple(w['line'][:2]);b=tuple(w['line'][2:]);hits=[a in pins,b in pins]
  if sum(hits)!=1:continue
  pin,free=(a,b) if hits[0] else (b,a)
  if free in flags:continue
  length=abs(pin[0]-free[0])+abs(pin[1]-free[1]);new=min(length,35 if pin[1]==free[1] else 20)
  end=tuple(round(pin[k]+(free[k]-pin[k])*new/length,5) for k in [0,1])
  w['line']=list(pin+end)
  for at in d['attrs'][w['primitiveId']]:
   if at.get('key')=='Name' and at.get('x') is not None and (at['x'] or at['y']):at['x']+=end[0]-free[0];at['y']+=end[1]-free[1]
def groups(page,refs):
 def pick(prefix):return [r for r in refs if r.startswith(prefix)]
 if page=='C01B':return [('内部 SMPS / VCORE', ['L1','C_SMPS_SW','C_VCORE1','C_VCORE2','C_VCAP_D8','C_VCAP_G6']),('SMPS 输入',['C_SMPS_IN','C_SMPS_HF']),('数字电源',['C_VDD_D6','C_VDD_E5','C_VDD_F6','C_VDD_BULK']),('模拟电源 / VREF',['R_ANALOG','C_VDDA_BULK','C_VDDA_HF','C_VREF_BULK','C_VREF_HF']),('USB 电源',['C_USB_BULK','C_USB_HF']),('VBAT 电源',['C_VBAT_BULK','C_VBAT_HF'])]
 if page=='C02':
  aux=pick('C_AUX')+pick('R_AUX')+['U_AUX','SW_AUX_RESET'];return [('5V → 3.296V / TPS62130A',[r for r in refs if r not in aux]),('3V3_AUX 限流与复位',aux)]
 if page=='C03':return [('8 MHz HSE BYPASS',['Y1','R_HSE','C_HSE']),('复位监控 / 手动复位',['U_RESET','C_RESET_U','R_NRST','C_NRST','R_MR','SW_RESET']),('BOOT0 默认下拉',['SW_BOOT','R_BOOT']),('SWD / 不由调试器供电',['J_SWD'])]
 if page=='C04':return [('BMI088 / SPI 与电源',pick('R_IMU')+pick('C_IMU')+['U_IMU']),('60°C 硬件温控',['U_TEMP','R_TEMP','C_TEMP']),('NRST 安全门',['U_HEAT_GATE','C_U_HEAT_GATE','R_HEAT_ALLOW']),('加热电源开关',['U_HEAT_POWER','R_U_HEAT_POWER_QOD','C_U_HEAT_POWER_IN','C_U_HEAT_POWER_OUT']),('IMU 温度 ADC',['R_NTC_TOP','NTC1','R_NTC_ADC','C_NTC']),('5V 输入 ADC',['R_V5_TOP','R_V5_BOT','R_V5_ADC','C_V5']),('加热电阻 / 低边 PWM',['R_HEAT1','R_HEAT2','R_HEAT3','R_HEAT4','Q_HEAT','R_HEAT_G','R_HEAT_G_PD'])]
 if page=='C05':return [(f'CAN{i} / 5V VCC / 3.3V VIO',[f'U_CAN{i}',f'R_CAN{i}_TX',f'R_CAN{i}_STB',f'C_CAN{i}_VCC',f'C_CAN{i}_VIO',f'D_CAN{i}']) for i in range(1,4)]+[('CAN 电源储能',['C_CAN_BULK'])]
 if page=='C06':return [('USB-C / CC 下拉 / 外壳',['J_USB','R_CC1','R_CC2','R_USB_SHELL']),('USB ESD / 串联预留',['U_USB_ESD','R_USB_DP','R_USB_DM','C_USB_VBUS']),('VBUS 检测 / 自供电设备',['U_VBUS','R_VBUS_SER','R_VBUS_PD','C_VBUS_U'])]
 if page=='C07':return [('J801 / 电源与 CAN',['J1']),('J802 / 可复用 GPIO',['J2']),('测试点 / 无钢网开口',pick('TP_'))]
 return []
def prepare(page):
 d=D[page];refs=[r for r,s in S['components'].items() if s['id'] in d['pins']];gs=groups(page,refs);assert sorted(r for _,rs in gs for r in rs)==sorted(refs)
 owner={S['components'][r]['id']:i for i,(_,rs) in enumerate(gs) for r in rs};wowner={};points={}
 for w in d['wires']:
  flat=w['line'];segments=[((flat[k],flat[k+1]),(flat[k+2],flat[k+3])) for k in range(0,len(flat),4)]
  hit={owner[cid] for cid,pins in d['pins'].items() if cid in owner and any(on_segment((round(p['x'],5),round(p['y'],5)),a,b) for p in pins for a,b in segments)}
  if len(hit)!=1:raise ValueError((page,w['primitiveId'],hit))
  wowner[w['primitiveId']]=next(iter(hit));points[w['primitiveId']]=segments
 for c in d['components']:
  if c['componentType']=='netflag':
   match={wowner[w['primitiveId']] for w in d['wires'] if any(on_segment((round(c['x'],5),round(c['y'],5)),a,b) for a,b in points[w['primitiveId']])}
   if len(match)!=1:raise ValueError(('flag',page,c['primitiveId'],match))
   owner[c['primitiveId']]=next(iter(match))
 result=[];cx=100;top=1060;row_height=0
 for i,(title,rs) in enumerate(gs):
  cc=[c for c in d['components'] if owner.get(c['primitiveId'])==i];ww=[w for w in d['wires'] if wowner[w['primitiveId']]==i];maps=[]
  for axis in ['x','y']:
   iv=[]
   for c in cc:
    if c['componentType']!='part':continue
    pins=d['pins'][c['primitiveId']];vals=[c[axis]]+[p[axis] for p in pins];lo=min(vals)-12;hi=max(vals)+12
    if axis=='x' and len(pins)==2 and c['rotation'] in [90,270]:hi+=26
    iv.append((lo,hi))
   maps.append(Axis(iv,15 if axis=='x' else 12))
  fx,fy=maps;xx=[fx(v) for w in ww for v in w['line'][::2]];yy=[fy(v) for w in ww for v in w['line'][1::2]]
  xmin=min(xx)-65;xmax=max(xx)+75;ymin=min(yy)-30;ymax=max(yy)+15
  width=xmax-xmin;height=ymax-ymin+20
  if cx+width>1500:cx=100;top-=row_height+30;row_height=0
  dx=cx-xmin;dy=top-ymax;row_height=max(row_height,height);cx+=width+50
  trans=lambda x,y:(fx(x)+dx,fy(y)+dy)
  cr=[];wr=[]
  for c in cc:
   x,y=trans(c['x'],c['y']);attrs=[]
   for a in d['attrs'][c['primitiveId']]:
    if a.get('valueVisible') and a.get('x') is not None:attrs.append({**a,'x':a['x']+x-c['x'],'y':a['y']+y-c['y']})
   cr.append(dict(id=c['primitiveId'],x=x,y=y,attrs=attrs,part=c['componentType']=='part',two=len(d['pins'][c['primitiveId']])==2,rotation=c['rotation']))
  for w in ww:
   paths=[[v for pt in [trans(*a),trans(*b)] for v in pt] for a,b in points[w['primitiveId']]]
   aa=[a for a in d['attrs'][w['primitiveId']] if a.get('key')=='Name'];a=aa[0] if aa else {};x,y=trans(a.get('x') or 0,a.get('y') or 0)
   wr.append(dict(id=w['primitiveId'],net=w['net'],paths=paths,label={**a,'x':x,'y':y,'valueVisible':bool(a.get('valueVisible') and (a.get('x') or a.get('y')))}))
  result.append(dict(title=title,x=cx-width-50,y=top+25,width=width,height=height,components=cr,wires=wr))
 if top-row_height<60:raise ValueError(('overflow',page,top,row_height))
 return result
plans={p:prepare(p) for p in D if p!='C01'}
(n.HERE/'module-compact-plan.json').write_text(json.dumps(plans,ensure_ascii=False,indent=2),encoding='utf-8')
if __name__=='__main__':
 import sys
 for p,gg in plans.items():print(p,[(g['title'],round(g['width']),round(g['height'])) for g in gg],flush=True)
 if '--apply' not in sys.argv:sys.exit()
 for page,gg in plans.items():
  if len(sys.argv)>2 and page not in sys.argv[2:]:continue
  pid=S['pages'][page];guard='if((await eda.dmt_SelectControl.getCurrentDocumentInfo()).uuid!=='+json.dumps(pid)+')throw new Error("Wrong SCH");'
  execute('await eda.dmt_EditorControl.openDocument('+json.dumps(pid)+');return true;')
  execute(guard+'const ww=await eda.sch_PrimitiveWire.getAll();await eda.sch_PrimitiveWire.delete(ww.map(w=>w.primitiveId));const tt=await eda.sch_PrimitiveText.getAll();await eda.sch_PrimitiveText.delete(tt.map(t=>t.primitiveId));return true;')
  for g in gg:
   for c in g['components']:
    execute(guard+'const i='+json.dumps(c)+';const c=(await eda.sch_PrimitiveComponent.get(i.id)).toAsync();c.setState_X(i.x);c.setState_Y(i.y);await c.done();return true;')
    for a in c['attrs']:
     align=3 if not c['two'] or c['rotation'] in [90,270] else 6
     execute(guard+ATTR_JS+'const i='+json.dumps(a)+';await style(await eda.sch_PrimitiveAttribute.get(i.primitiveId),i.x,i.y,'+str(7 if a['key']=='Designator' else 6)+','+str(align)+',0,true);return true;')
   for w in g['wires']:
    wid=execute(guard+ATTR_JS+'const i='+json.dumps(w)+';const w=await eda.sch_PrimitiveWire.create(i.paths,i.net);if(!w)throw new Error("wire failed");for(const a of await eda.sch_PrimitiveAttribute.getAll(w.getState_PrimitiveId())){if(a.key==="Name")await style(a,i.label.x,i.label.y,6,i.label.alignMode===8?9:i.label.alignMode===7?6:3,i.label.rotation||0,Boolean(i.label.valueVisible));}return w.getState_PrimitiveId();')
    w['new_id']=wid
   execute(guard+'await eda.sch_Document.save();await new Promise(r=>setTimeout(r,500));return (await eda.sch_PrimitiveText.create('+str(g['x'])+','+str(g['y'])+','+json.dumps(g['title'],ensure_ascii=False)+',0,"#213547",undefined,11,true,false,false,1))?.getState_PrimitiveId()||null;')
  title=n.PAGE_NAMES[page]
  pins=execute(guard+'await eda.sch_PrimitiveText.create(100,1120,'+json.dumps(title,ensure_ascii=False)+',0,"#213547",undefined,16,true,false,false,1);const pins={};for(const c of await eda.sch_PrimitiveComponent.getAll()){if(c.componentType==="part")pins[c.primitiveId]=await eda.sch_PrimitiveComponent.getAllPinsByPrimitiveId(c.primitiveId);}await eda.sch_Document.save();return pins;')
  for r,rec in S['components'].items():
   if rec['id'] in pins:rec['pins']=pins[rec['id']];rec['module_compact']=True
  state=n.load_state();state['CORE']=S;n.save_state(state)
  print('saved module layout',page,flush=True)
(n.HERE/'module-compact-plan.json').write_text(json.dumps(plans,ensure_ascii=False,indent=2),encoding='utf-8')

