"""Functional schematic placement and local wiring in the existing H735 pages.

All purchased parts, pins and nets are retained.  Only this project's known
pages are changed; no desktop focus or native input is used.  The v3 attribute
setter uses source Y coordinates, unlike component coordinates.
"""
import argparse
import json
import math
import copy
from collections import defaultdict
from pathlib import Path
import native_design as n
from eda_bridge import execute

JOURNAL=n.HERE/'functional-layout-state.json'


class Plan:
    def __init__(self,page):
        self.page=page;self.parts={};self.banks=[];self.notes=[]
    def put(self,ref,x,y,rotation=0):
        self.parts[ref]=dict(x=x,y=y,rotation=rotation)
    def text(self,x,y,s,size=11):self.notes.append(dict(x=x,y=y,text=s,size=size))
    def bank(self,refs,x,y,step=100):
        for i,r in enumerate(refs):self.put(r,x+i*step,y,270)
        self.banks.append(refs)


def plans():
    out={p:Plan(p) for p in n.PAGE_NAMES}
    p=out['C01'];p.put('U1',820,650)
    p.text(100,1070,'H735 主控 / 信号分配',16)
    p.text(100,1000,'CPU 480 MHz  |  HSE 8 MHz BYPASS  |  STM32 / FreeRTOS',10)
    p.text(100,850,'核心板固定资源',12)
    p.text(100,810,'CAN1 / CAN2 / CAN3\nSPI4：BMI088\nUSB FS：设备接口\nSWD：下载与调试',9)
    p.text(100,650,'扩展接口',12)
    p.text(100,610,'EXP_*：板间可复用 GPIO\n默认不开启的功能由固件配置\n电源去耦详见 C01B\n板间针序详见 C07',9)
    p.text(100,420,'首版明确不连接\nPH1：HSE BYPASS 不使用\nPC14 / PC15：LSE 保留，不装晶体\n固件禁用 LSE，保留脚保持高阻',9)
    p=out['C01B'];p.text(100,1080,'主控电源 / SMPS 与就近去耦',16)
    p.put('L1',350,940)
    p.bank(['C_SMPS_SW'],210,850)
    p.bank(['C_VCORE1','C_VCORE2','C_VCAP_D8','C_VCAP_G6'],450,850)
    p.text(100,1010,'内部 SMPS：SMPS_SW → 2.2 µH → VCORE')
    p.bank(['C_SMPS_IN','C_SMPS_HF'],1100,900)
    p.text(1030,1010,'VDD / VDDSMPS 输入去耦')
    p.bank(['C_VDD_D6','C_VDD_E5','C_VDD_F6','C_VDD_BULK'],200,550)
    p.text(100,680,'数字电源：每组电源球就近放置 100 nF')
    p.put('R_ANALOG',850,630)
    p.bank(['C_VDDA_BULK','C_VDDA_HF','C_VREF_BULK','C_VREF_HF'],950,550)
    p.text(800,710,'模拟电源 / 参考电压')
    p.bank(['C_USB_BULK','C_USB_HF'],250,270)
    p.bank(['C_VBAT_BULK','C_VBAT_HF'],850,270)
    p.text(150,400,'USB 内部电源去耦');p.text(750,400,'VBAT：首版与 3V3_D 同源')
    p=out['C02'];p.text(100,1090,'3V3 电源 / 扩展口限流保护',16)
    p.put('U2',750,850,180);p.put('L2',1070,855)
    p.bank(['C_BUCK_IN','C_BUCK_IN2','C_BUCK_IN3','C_BUCK_HF'],170,850,90)
    p.bank(['C_BUCK_OUT','C_BUCK_OUT2','C_BUCK_OUT3','C_BUCK_OUT4'],1020,700,110)
    p.put('C_BUCK_SS',530,700,270);p.put('R_BUCK_PG',950,980,90)
    p.text(100,1020,'5V_IN → TPS62130A → 3V3_D')
    p.put('U_AUX',500,420)
    p.bank(['C_AUX_IN','C_AUX_IN_HF'],170,430)
    p.bank(['C_AUX_OUT','C_AUX_OUT_HF'],900,430)
    p.put('R_AUX_EN',300,300,90);p.put('SW_AUX_RESET',470,240)
    p.put('R_AUX_ILIM',700,310,270);p.put('R_AUX_FAULT',720,570,90)
    p.text(100,610,'扩展 3V3_AUX：限流 / 故障反馈 / 手动重置')
    p.put('R_FB_TOP',1250,430,270);p.put('R_FB_BOT',1250,280,270)
    p.text(1160,570,'反馈分压：312k / 100k')
    p.text(1160,530,'0.8 × (1 + 3.12) = 3.296 V',8)
    p=out['C03'];p.text(100,1090,'时钟 / 复位 / 启动与调试',16)
    p.put('Y1',350,900);p.put('R_HSE',550,890);p.bank(['C_HSE'],150,900)
    p.text(100,1020,'8 MHz 有源时钟；HSE 使用 BYPASS')
    p.put('U_RESET',450,590,180);p.bank(['C_RESET_U'],180,590)
    p.put('R_NRST',700,700,90);p.put('C_NRST',700,520,270)
    p.put('R_MR',260,430,90);p.put('SW_RESET',450,340)
    p.text(100,780,'电源监控与复位：手动按键作用于 MR_N')
    p.put('SW_BOOT',1080,880);p.put('R_BOOT',1080,730,270)
    p.text(950,1020,'BOOT0：默认下拉，按下进入启动配置')
    p.put('J_SWD',1130,450);p.text(950,620,'10 针 SWD / VTREF / NRST')
    p.text(950,270,'SWO / 保留脚不连接；调试器不向核心板供电',8)
    p=out['C04'];p.text(100,1120,'BMI088 / 加热安全链与模拟采样',16)
    p.put('U_IMU',500,930);p.put('R_IMU_POWER',200,1050)
    p.bank(['C_IMU_VDD','C_IMU_VDDIO','C_IMU_BULK'],1050,990)
    p.put('R_IMU_SCK',430,780);p.put('R_IMU_MOSI',810,900,180)
    p.put('R_IMU_ACC_CS',800,1010,90);p.put('R_IMU_GYRO_CS',220,900,90)
    p.text(100,1090,'IMU 电源与双片选 SPI',10)
    p.put('U_TEMP',300,610);p.put('R_TEMP',140,730,90);p.bank(['C_TEMP'],450,700)
    p.put('U_HEAT_GATE',650,610);p.bank(['C_U_HEAT_GATE'],800,700)
    p.put('R_HEAT_ALLOW',800,540,270)
    p.put('U_HEAT_POWER',1100,610);p.put('R_U_HEAT_POWER_QOD',1260,530)
    p.bank(['C_U_HEAT_POWER_IN'],980,720);p.bank(['C_U_HEAT_POWER_OUT'],1400,610)
    p.text(100,800,'硬件安全：温度开关 + NRST → HEAT_ALLOW',10)
    p.put('R_NTC_TOP',200,400,270);p.put('NTC1',200,250,270)
    p.put('R_NTC_ADC',360,325);p.put('C_NTC',470,250,270)
    p.text(100,470,'IMU 温度采样',10)
    p.put('R_V5_TOP',650,400,270);p.put('R_V5_BOT',650,250,270)
    p.put('R_V5_ADC',810,325);p.put('C_V5',920,250,270)
    p.text(590,470,'5V 输入采样 / RC 滤波',10)
    p.bank(['R_HEAT1','R_HEAT2','R_HEAT3','R_HEAT4'],1120,400,90)
    p.put('Q_HEAT',1300,220);p.put('R_HEAT_G',1110,220);p.put('R_HEAT_G_PD',1210,140,270)
    p.text(1090,470,'加热：4 × 200Ω / 1206',10)
    p=out['C05'];p.text(100,1110,'三路 CAN / 逻辑供电 / 线端 ESD',16)
    p.bank(['C_CAN_BULK'],1390,990)
    for i,y in enumerate([920,610,300],1):
        p.put(f'U_CAN{i}',600,y);p.put(f'R_CAN{i}_TX',420,y+90,90)
        p.put(f'R_CAN{i}_STB',810,y+90,90)
        p.bank([f'C_CAN{i}_VCC'],180,y);p.bank([f'C_CAN{i}_VIO'],310,y)
        p.put(f'D_CAN{i}',1000,y-100)
        p.text(100,y+150,f'CAN{i}：TCAN1042HG / 5V VCC / 3.3V VIO',11)
    p.text(1210,600,'CANH / CANL 经板间连接器引出\n终端电阻位于扩展板\nSTB 默认上拉：复位期间待机',9)
    p=out['C06'];p.text(100,1090,'USB FS 设备接口 / ESD / VBUS 检测',16)
    p.put('J_USB',350,850)
    p.put('R_CC1',150,590,270);p.put('R_CC2',350,590,270);p.put('R_USB_SHELL',550,590,270)
    p.text(100,1020,'USB Type-C：自供电设备，仅使用 USB 2.0')
    p.put('U_USB_ESD',1000,900);p.put('R_USB_DP',1220,930);p.put('R_USB_DM',1220,870)
    p.bank(['C_USB_VBUS'],1100,720)
    p.text(850,1020,'ESD → 串联预留 → MCU USB FS')
    p.put('U_VBUS',1050,430);p.put('R_VBUS_SER',750,440)
    p.put('R_VBUS_PD',850,340,270);p.bank(['C_VBUS_U'],1260,420)
    p.text(700,590,'VBUS 检测：5V 容忍施密特输入，3.3V 输出')
    p.text(100,380,'CC1 / CC2：各 5.1k 下拉\n外壳通过 0Ω 预留接系统地\nVBUS 不接入核心板 5V_IN',9)
    p=out['C07'];p.text(100,1100,'板间连接器 / 电源与信号测试点',16)
    p.put('J1',420,800);p.put('J2',1130,800)
    p.text(160,1000,'J801：电源 / 三路 CAN / 可复用 GPIO')
    p.text(900,1000,'J802：可复用 GPIO / 地回流')
    refs=[r['reference'] for r in n.input_components('CORE') if r['page']=='C07' and r['reference'].startswith('TP_')]
    for i,ref in enumerate(refs):p.put(ref,200+(i%5)*270,450-(i//5)*140)
    p.text(100,530,'测试点：0.8 mm 裸铜，开阻焊，不开锡膏',10)
    return out


def flat(points):return [v for pt in points for v in pt]
def segments(paths):
    for path in paths:
        for a,b in zip(path,path[1:]):
            if a!=b:yield a,b
def on_segment(p,a,b):
    return ((a[0]==b[0]==p[0] and min(a[1],b[1])<=p[1]<=max(a[1],b[1])) or
            (a[1]==b[1]==p[1] and min(a[0],b[0])<=p[0]<=max(a[0],b[0])))


class Routing:
    def __init__(self,plan,items,state):
        self.plan=plan;self.items=items;self.state=state;self.wires=[];self.pins={};self.nets={}
        for row in items:
            ref=row['reference'];rec=state['components'][ref]
            self.pins[ref]={p['pinNumber']:{**p,'x':round(p['x'],5),'y':round(p['y'],5)} for p in rec['pins']}
            self.nets[ref]=n.pin_map(row,rec)
    def p(self,ref,pin):
        p=self.pins[ref][str(pin)];return (p['x'],p['y'])
    def net(self,ref,pin):return self.nets[ref][str(pin)]
    def add(self,net,paths,label=None,ground=None):
        paths=[[tuple(pt) for pt in path] for path in paths]
        self.wires.append(dict(net=net,paths=paths,label=label,ground=ground))
    def join(self,ref1,pin1,ref2,pin2,via=(),label=None):
        assert self.net(ref1,pin1)==self.net(ref2,pin2),(ref1,pin1,ref2,pin2)
        self.add(self.net(ref1,pin1),[[self.p(ref1,pin1),*via,self.p(ref2,pin2)]],label)
    def bank(self,refs):
        for pin in ('1','2'):
            pts=[self.p(ref,pin) for ref in refs]
            net=self.net(refs[0],pin)
            assert all(self.net(ref,pin)==net for ref in refs)
            y=max(p[1] for p in pts)+25 if pin=='1' else min(p[1] for p in pts)-25
            paths=[[p,(p[0],y)] for p in pts]
            if len(pts)>1:paths.append([(pts[0][0],y),(pts[-1][0],y)])
            anchor=(pts[0][0],y)
            self.add(net,paths,None if net=='GND' else dict(x=anchor[0]-5,y=y+4,align=9),anchor if net=='GND' else None)
    def switch(self,ref):
        for a,b,delta in [('1','3',35),('2','4',-35)]:
            left=self.p(ref,a);right=self.p(ref,b);net=self.net(ref,a)
            assert self.net(ref,b)==net
            yy=left[1]+delta
            self.add(net,[[left,(left[0]-20,left[1]),(left[0]-20,yy),(right[0]+20,yy),(right[0]+20,right[1]),right]],
                None if net=='GND' else dict(x=left[0]-25,y=yy+3,align=9),
                (right[0]+20,yy) if net=='GND' else None)
    def divider(self,top,bottom,series=None,cap=None):
        a=self.p(top,'2');b=self.p(bottom,'1');yy=(a[1]+b[1])/2
        paths=[[a,(a[0],yy),b]]
        if series:paths.append([(a[0],yy),self.p(series,'1')])
        self.add(self.net(top,'2'),paths,dict(x=a[0]-6,y=yy+4,align=9))
        if cap:
            c=self.p(cap,'1');o=self.p(series,'2')
            self.add(self.net(series,'2'),[[o,(c[0],o[1]),c]],dict(x=c[0]+8,y=o[1]+3,align=3))
            self.add('GND',[[self.p(bottom,'2'),(b[0],b[1]-100),(c[0],b[1]-100),self.p(cap,'2')]],ground=(c[0],b[1]-100))
    def specials(self):
        q=self.plan.page
        if q=='C01B':
            self.join('L1','1','C_SMPS_SW','1',[(210,940)])
            self.join('L1','2','C_VCORE1','1',[(450,940)])
            self.join('R_ANALOG','2','C_VDDA_BULK','1',[(950,630)])
        elif q=='C02':
            pp=[self.p('U2',i) for i in ('1','2','3')];x=960
            self.add('BUCK_SW',[[v,(x,v[1])] for v in pp]+[[(x,min(v[1] for v in pp)),(x,max(v[1] for v in pp))],[(x,self.p('L2','1')[1]),self.p('L2','1')]])
            pp=[self.p('U2',i) for i in ('10','11','12')];x=620
            self.add('5V_IN',[[v,(x,v[1])] for v in pp]+[[(x,min(v[1] for v in pp)),(x,895),(170,895)]])
            self.join('L2','2','C_BUCK_OUT','1',[(1450,855),(1450,745),(1020,745)])
            self.divider('R_FB_TOP','R_FB_BOT')
            self.switch('SW_AUX_RESET')
            self.join('U_AUX','5','R_AUX_ILIM','1',[(700,420)])
            self.join('U_AUX','6','C_AUX_OUT','1',[(820,430),(820,475),(900,475)])
        elif q=='C03':
            self.join('Y1','3','R_HSE','1')
            self.switch('SW_RESET');self.switch('SW_BOOT')
            self.join('R_NRST','1','C_NRST','1',label=dict(x=707,y=613,align=3))
            self.add('NRST',[[self.p('U_RESET','1'),(650,580),(650,610),(700,610)]])
        elif q=='C04':
            self.join('U_IMU','9','R_IMU_MOSI','2')
            self.join('U_IMU','8','R_IMU_SCK','2',[(500,780)])
            self.divider('R_NTC_TOP','NTC1','R_NTC_ADC','C_NTC')
            self.divider('R_V5_TOP','R_V5_BOT','R_V5_ADC','C_V5')
            self.join('R_HEAT_G','2','Q_HEAT','1')
            self.join('R_HEAT_G_PD','1','Q_HEAT','1',[(1210,220)])
            self.join('U_HEAT_POWER','5','R_U_HEAT_POWER_QOD','1',[(1200,610),(1200,530)])
        elif q=='C05':
            for i in range(1,4):
                u=f'U_CAN{i}';d=f'D_CAN{i}';y=self.plan.parts[u]['y']
                self.join(u,'7',d,'2',[(1040,y+5),(1040,y-140),(1010,y-140)],dict(x=750,y=y+8,align=3))
                self.join(u,'6',d,'1',[(940,y-5),(940,y-120)],dict(x=750,y=y-2,align=3))
                self.join(u,'1',f'R_CAN{i}_TX','1',[(500,y+15),(500,y+70)],dict(x=495,y=y+25,align=9))
                self.join(u,'8',f'R_CAN{i}_STB','1',[(740,y+15),(740,y+70)],dict(x=745,y=y+25,align=3))
        elif q=='C06':
            pts=[self.p('J_USB',p) for p in ('1','2','3','4')];xx=440
            self.add('USB_SHELL',[[v,(xx,v[1])] for v in pts]+[[(xx,min(p[1] for p in pts)),(xx,max(p[1] for p in pts))]],dict(x=xx+5,y=max(p[1] for p in pts)+4,align=3))
            self.join('U_USB_ESD','6','R_USB_DP','1');self.join('U_USB_ESD','4','R_USB_DM','1')
            self.join('R_VBUS_SER','2','U_VBUS','2')
            self.join('R_VBUS_PD','1','R_VBUS_SER','2',[(850,440)])
        for ref in self.plan.parts:
            if ref.startswith('SW_') and not any(self.p(ref,'1') in path for w in self.wires for path in w['paths']):self.switch(ref)
    def finish(self):
        for refs in self.plan.banks:self.bank(refs)
        self.specials()
        existing=[(w['net'],a,b) for w in self.wires for a,b in segments(w['paths'])]
        for ref,pins in self.pins.items():
            for number,p in pins.items():
                net=self.net(ref,number);pt=(p['x'],p['y'])
                if net=='NC' or any(net==n0 and on_segment(pt,a,b) for n0,a,b in existing):continue
                rot=p['rotation']%360;length=65 if len(pins)>2 else 30
                dx,dy={0:(length,0),90:(0,30),180:(-length,0),270:(0,-30)}[rot]
                end=(pt[0]+dx,pt[1]+dy)
                if dx:label=dict(x=end[0]+(3 if dx>0 else -3),y=end[1]+2,align=3 if dx>0 else 9)
                else:
                    vertical_neighbors=[q for q in pins.values() if q['pinNumber']!=number and q['rotation']%180==90 and abs(q['x']-p['x'])<60]
                    label=dict(x=end[0]+3,y=end[1]+(3 if dy>0 else -3),align=3 if dy>0 else 9,rotation=90) if vertical_neighbors else dict(x=end[0]+7,y=end[1]+3,align=3,rotation=0)
                self.add(net,[[pt,end]],label)
        return self.merge()
    def merge(self):
        groups=[]
        for w in self.wires:
            matches=[]
            for i,g in enumerate(groups):
                if g['net']!=w['net']:continue
                if any(on_segment(a,c,d) or on_segment(b,c,d) or on_segment(c,a,b) or on_segment(d,a,b) for a,b in segments(w['paths']) for c,d in segments(g['paths'])):matches.append(i)
            for i in reversed(matches):
                g=groups.pop(i);w['paths']+=g['paths'];w['label']=w['label'] or g['label'];w['ground']=w['ground'] or g['ground']
            groups.append(w)
        # A pin on a different net's segment is an unambiguous short, not a crossing.
        for w in groups:
            for a,b in segments(w['paths']):
                if a[0]!=b[0] and a[1]!=b[1]:raise ValueError(('diagonal',w['net'],a,b))
                for ref,pp in self.pins.items():
                    for number,p in pp.items():
                        if on_segment((p['x'],p['y']),a,b) and self.net(ref,number)!=w['net']:
                            raise ValueError(('wire crosses other pin',w['net'],ref,number,self.net(ref,number)))
            raw=list(segments(w['paths']));nodes={p for ab in raw for p in ab};edges=set()
            for a,b in raw:
                chain=sorted(p for p in nodes if on_segment(p,a,b))
                for u,v in zip(chain,chain[1:]):edges.add((u,v))
            w['paths']=[list(edge) for edge in sorted(edges)]
        return groups


ATTR_JS='''function style(a,x,y,size,align,rotation,visible){const b=a.toAsync();b.setState_X(x);b.setState_Y(-y);b.setState_FontSize(size);b.setState_AlignMode(align);b.setState_Rotation(rotation);b.setState_KeyVisible(false);b.setState_ValueVisible(visible);return b.done();}'''


def apply(page):
    plan=plans()[page];state=n.load_state();s=state['CORE'];pid=s['pages'][page]
    rows=[r for r in n.input_components('CORE') if r['page']==page]
    assert set(plan.parts)=={r['reference'] for r in rows},(page,set(plan.parts)^{r['reference'] for r in rows})
    journal=json.loads(JOURNAL.read_text(encoding='utf-8')) if JOURNAL.exists() else {}
    old=journal.get(page,{})
    def log(**kw):
        old.update(kw);journal[page]=old;JOURNAL.write_text(json.dumps(journal,ensure_ascii=False,indent=2),encoding='utf-8')
    guard='if((await eda.dmt_SelectControl.getCurrentDocumentInfo()).uuid!=='+json.dumps(pid)+')throw new Error("Wrong page");'
    execute('await eda.dmt_EditorControl.openDocument('+json.dumps(pid)+');await new Promise(r=>setTimeout(r,1500));return await eda.dmt_SelectControl.getCurrentDocumentInfo();')
    known=[s['components'][r['reference']]['id'] for r in rows]
    execute(guard+'const known=new Set('+json.dumps(known)+');for(const c of await eda.sch_PrimitiveComponent.getAll()){if(c.componentType==="part"&&!known.has(c.primitiveId))throw new Error("Untracked component: preserve and inspect");}return true;')
    cleanup_flags=list(set(old.get('old_flag_ids',[])+old.get('flag_ids',[])))
    cleanup_texts=list(set(old.get('old_text_ids',[])+old.get('text_ids',[])))
    log(phase='rebuilding',page_uuid=pid,wire_ids=[],flag_ids=[],text_ids=[],old_flag_ids=cleanup_flags,old_text_ids=cleanup_texts)
    execute(guard+'const wires=await eda.sch_PrimitiveWire.getAll();if(wires.length&&!await eda.sch_PrimitiveWire.delete(wires.map(w=>w.primitiveId)))throw new Error("Wire removal failed");return true;')
    if old.get('old_flag_ids'):
        execute(guard+'return await eda.sch_PrimitiveComponent.delete('+json.dumps(old['old_flag_ids'])+');')
    if old.get('old_text_ids'):
        execute(guard+'return await eda.sch_PrimitiveText.delete('+json.dumps(old['old_text_ids'])+');')
    placements=[dict(id=s['components'][ref]['id'],ref=ref,**pos) for ref,pos in plan.parts.items()]
    for start in range(0,len(placements),8):
        payload=placements[start:start+8]
        result=execute(guard+'const out={};for(const i of '+json.dumps(payload)+'){const a=(await eda.sch_PrimitiveComponent.get(i.id)).toAsync();a.setState_X(i.x);a.setState_Y(i.y);a.setState_Rotation(i.rotation);await a.done();out[i.ref]=await eda.sch_PrimitiveComponent.getAllPinsByPrimitiveId(i.id);}return out;')
        for ref,pins in result.items():s['components'][ref]['pins']=pins
    n.save_state(state)
    route=Routing(plan,rows,s);wires=route.finish();log(plan_wires=wires)
    for row in rows:
        rec=s['components'][row['reference']];payload=dict(id=rec['id'],nets=n.pin_map(row,rec))
        execute(guard+'const i='+json.dumps(payload)+';for(const p of await eda.sch_PrimitiveComponent.getAllPinsByPrimitiveId(i.id)){const a=p.toAsync();a.setState_NoConnected(i.nets[p.pinNumber]==="NC");await a.done();}return true;')
    made=[];flags=[]
    for index,w in enumerate(wires):
        result=execute(guard+'const w='+json.dumps(w)+';const p=await eda.sch_PrimitiveWire.create(w.paths.map(path=>path.flat()),w.net);if(!p)throw new Error("Wire failed: "+w.net);return {id:p.getState_PrimitiveId()};')
        w['id']=result['id'];made.append(w['id'])
        if w['ground']:
            x,y=w['ground'];f=execute(guard+'const f=await eda.sch_PrimitiveComponent.createNetFlag("Ground","GND",'+str(x)+','+str(y)+');if(!f)throw new Error("Ground flag failed");return f.getState_PrimitiveId();');flags.append(f)
        log(wire_ids=made,flag_ids=flags)
    for w in wires:
        label=w['label'];x,y,align,rotation=(label['x'],label['y'],label['align'],label.get('rotation',0)) if label else (0,0,3,0)
        execute(guard+ATTR_JS+'const aa=await eda.sch_PrimitiveAttribute.getAll('+json.dumps(w['id'])+');let first=true;for(const a of aa){if(a.key==="Name"||a.key==="NET"){await style(a,'+','.join(json.dumps(v) for v in [x,y,6,align,rotation])+','+json.dumps(bool(label))+');first=false;}}return true;')
    for row in rows:
        ref=row['reference'];rec=s['components'][ref];pos=plan.parts[ref];pins=rec['pins'];x,y=pos['x'],pos['y']
        is_two=len(pins)==2
        if is_two and pos['rotation'] in (90,270):namepos=(x+18,y-7);refpos=(x+18,y+7);align=3
        elif is_two:namepos=(x,y-19);refpos=(x,y+15);align=6
        else:
            refpos=(min(p['x'] for p in pins)+10,max(p['y'] for p in pins)+22)
            namepos=(refpos[0],min(p['y'] for p in pins)-24);align=3
        if ref.startswith('TP_'):refpos=(x+16,y);namepos=(x,y-20)
        if ref=='Q_HEAT' or ref.startswith('D_CAN'):refpos=(x+30,y+12);namepos=(x+30,y-10);align=3
        pld=dict(id=rec['id'],refpos=refpos,namepos=namepos,align=align,showname=not ref.startswith('TP_'))
        execute(guard+ATTR_JS+'const i='+json.dumps(pld)+';for(const a of await eda.sch_PrimitiveAttribute.getAll(i.id)){if(a.key==="Designator")await style(a,i.refpos[0],i.refpos[1],7,i.align,0,true);else if(a.key==="Name")await style(a,i.namepos[0],i.namepos[1],6,i.align,0,i.showname);}return true;')
        rec['connections']=[]
        for pin,p in route.pins[ref].items():
            net=route.net(ref,pin)
            if net=='NC':rec['connections'].append(dict(pin=pin,nc=True));continue
            hit=next(w for w in wires if w['net']==net and any(on_segment((p['x'],p['y']),a,b) for a,b in segments(w['paths'])))
            rec['connections'].append(dict(pin=pin,net=net,id=hit['id']))
        rec['functional_layout']=True;rec['wired']=True
    texts=[]
    for t in plan.notes:
        a=execute(guard+'const i='+json.dumps(t,ensure_ascii=False)+';const ESCH_PrimitiveTextAlignMode={LEFT_TOP:1};const t=await eda.sch_PrimitiveText.create(i.x,i.y,i.text,0,"#213547",undefined,i.size,i.size>=10,false,false,ESCH_PrimitiveTextAlignMode.LEFT_TOP);return t.getState_PrimitiveId();');texts.append(a);log(text_ids=texts)
    n.save_state(state)
    execute(guard+'await new Promise(r=>setTimeout(r,1500));return await eda.sch_Document.save();')
    log(phase='complete',old_flag_ids=flags,old_text_ids=texts)
    print('layout complete',page,len(rows),'parts',len(wires),'wire groups',flush=True)


def dryrun(page):
    plan=plans()[page];s=copy.deepcopy(n.load_state()['CORE'])
    before=json.loads((n.HERE/'native-layout-before.json').read_text(encoding='utf-8'))
    for ref,pos in plan.parts.items():
        rec=s['components'][ref]
        orig=next(c for c in before[page]['components'] if c['primitiveId']==rec['id'])
        if rec.get('functional_layout'):continue
        angle=math.radians(pos['rotation']-orig['rotation'])
        for pin in rec['pins']:
            x=pin['x']-orig['x'];y=pin['y']-orig['y']
            pin['x']=round(pos['x']+x*math.cos(angle)-y*math.sin(angle),5)
            pin['y']=round(pos['y']+x*math.sin(angle)+y*math.cos(angle),5)
            pin['rotation']=(pin['rotation']+pos['rotation']-orig['rotation'])%360
    rows=[r for r in n.input_components('CORE') if r['page']==page]
    wires=Routing(plan,rows,s).finish()
    print(page,'checked',len(wires),'groups')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('pages',nargs='+');p.add_argument('--dry-run',action='store_true');args=p.parse_args()
    for page in args.pages:(dryrun if args.dry_run else apply)(page)
