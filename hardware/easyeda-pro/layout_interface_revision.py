"""Compact R4B functional modules; rebuild only explicitly selected H735 pages."""
import json,sys,math
import native_design as n
from eda_bridge import execute
from functional_layout import Plan,Routing,ATTR_JS,on_segment,segments

def plan(page):
    p=Plan(page);p.text(90,1120,n.PAGE_NAMES[page],16)
    if page=='C01':
        old=json.loads((n.HERE/'layout-before-R4.json').read_text(encoding='utf-8'))[page]
        c=next(c for c in old['components'] if c.get('designator')=='U101');p.put('U1',c['x'],c['y'])
        p.text(100,1040,'480 MHz / 8 MHz HSE BYPASS / STM32 + FreeRTOS',10)
        p.text(100,960,'核心板：3 CAN + 4 UART\nSPI1：BMI088，双片选\nSPI3 / I2C2：独立外设接口\nUSB FS：自供电设备',9)
        p.text(100,820,'上层扩展板：7 组其余 UART\n板间 J801 / J802：2 x 30 pin\nPA0 / PA1 / PB0 / PB1：自定义排针\nPC8：USB VBUS 检测\nPE6：5V_PORT 故障反馈',9)
        p.text(100,650,'与旧固件不同：IMU SPI4 → SPI1\nACC_CS → PE5；VBUS → PC8\nPA9 / PA10 用于 LPUART1\nPE2 / PE3 用于 USART10\n旧引脚复用配置不可直接沿用',9)
    elif page=='C05':
        for i in range(1,4):
            x=100+(i-1)*500;y=950
            p.text(x,1080,f'CAN{i} / GH1.25 直立 / 端点电阻 DNP',11)
            p.put(f'U_CAN{i}',x+160,y);p.put(f'J_CAN{i}',x+350,y+5)
            p.put(f'R_CAN{i}_TX',x+85,y+40,90);p.put(f'R_CAN{i}_STB',x+255,y+40,90)
            p.bank([f'C_CAN{i}_VCC'],x+10,y-20);p.bank([f'C_CAN{i}_VIO'],x+70,y-75)
            p.put(f'D_CAN{i}',x+210,y-120);p.put(f'R_CAN{i}_TERM',x+350,y-170,270)
            p.text(x+290,y-250,'120Ω 默认不装\n仅总线端点装配',8)
        p.bank(['C_CAN_BULK'],160,610)
        p.text(250,665,'GH 针序：1 GND / 2 CANH / 3 CANL；固定焊脚接地\n每条总线全网只装两只 120Ω；扩展板端接不得重复\nCAN 不携带 48V；STB 复位默认上拉进入待机',9)
    elif page=='C06':
        p.put('J_USB',280,960);p.put('R_CC1',120,820,270);p.put('R_CC2',200,820,270);p.put('R_USB_SHELL',280,820,270);p.put('D_USB_CC',410,825)
        p.text(100,1080,'USB4145 / 直立 / 设备接口',11)
        p.put('U_USB_ESD',680,970);p.put('R_USB_DP',850,1000);p.put('R_USB_DM',850,940);p.bank(['C_USB_VBUS'],790,845)
        p.text(540,1080,'USB2.0 ESD / 串联预留',11)
        p.put('U_VBUS',1200,980);p.put('R_VBUS_SER',1035,990);p.put('R_VBUS_PD',1110,870,270);p.bank(['C_VBUS_U'],1290,970)
        p.text(990,1080,'VBUS_PRESENT → PC8 GPIO',11)
        p.text(100,700,'USB VBUS 仅检测，不给核心板供电；CC1 / CC2 各 5.1k 下拉\n四个外壳焊脚同为 pad 0，属于一个 USB_SHELL 网络；A8 / B8 不连接\n上层扩展板须避让 7.46 mm 插座、线缆插头和拔插操作空间',9)
    elif page=='C07':
        p.put('J1',270,950);p.put('J2',650,950)
        p.text(100,1080,'J801 / 7 组串口 / 电源与复位',11);p.text(500,1080,'J802 / CAN / 其余可复用 GPIO',11)
        refs=[r['reference'] for r in n.input_components('CORE') if r['page']==page and r['reference'].startswith('TP_')]
        for i,r in enumerate(refs):p.put(r,970+(i%4)*110,1010-(i//4)*65)
        p.text(910,1080,'测试点 / 无钢网开口',11)
        p.text(100,750,'核心板在下：TOP = TFM-115-02-L-D-A\n扩展板在上：BOTTOM = SFM-115-02-L-D-A-K-TR\n两组 30pin；装配方向与旧版相反；禁止沿用旧 50pin 针序\n5V_PORT 与 3V3_AUX 均为受限流保护的输出，不接外部电源',9)
    elif page=='C08':
        for i,port in enumerate(['USART1','USART2','USART3','USART6']):
            x=330+i%2*610;y=970-i//2*290
            p.put('J_'+port,x,y,270);p.put('R_'+port+'_TX',x-130,y-25);p.put('R_'+port+'_RX',x-130,y+45);p.put('D_'+port,x+210,y)
            p.text(x-230,y+110,port+' / 3.3V UART / GH1.25 直立',11)
        p.text(100,450,'四针统一：1 GND / 2 +5V_PORT / 3 MCU_TX / 4 MCU_RX；外部设备 TX/RX 交叉接线\n5V_PORT 由所有核心 UART 与扩展板共同分配，连续负载预算 400mA，总限流详见 C09\nUART4/5/7/8/9、USART10、LPUART1 从 J801 送往上层扩展板',9)
    elif page=='C09':
        p.text(100,1080,'SPI3 / 3.3V / 六针 GH',11);p.put('J_SPI3',430,960,90)
        for i,k in enumerate(['SCK','MOSI','MISO','NSS']):p.put('R_SPI3_'+k,240,900+i*40)
        p.put('D_SPI3_A',620,995);p.put('D_SPI3_B',620,895)
        p.text(100,820,'1 GND / 2 3V3_AUX / 3 SCK\n4 MOSI / 5 MISO / 6 NSS',8)
        p.text(760,1080,'I2C2 / 3.3V / 四针 GH',11);p.put('J_I2C2',1070,960,270)
        p.put('R_I2C2_SCL',900,925);p.put('R_I2C2_SDA',900,995)
        p.put('R_I2C2_SCL_PU',1020,840,270);p.put('R_I2C2_SDA_PU',1110,840,270);p.put('D_I2C2',1280,960)
        p.text(760,780,'1 GND / 2 3V3_AUX / 3 SCL / 4 SDA\n4.7k 上拉；外部重复上拉需合并计算\nAUX 关断时停用总线，禁用内部上拉',8)
        p.text(100,680,'5V_PORT 共享限流 / 故障锁存',11);p.put('U_PORT',350,530)
        p.bank(['C_PORT_IN','C_PORT_IN_HF'],120,540,70);p.bank(['C_PORT_OUT','C_PORT_OUT_HF'],500,540,70)
        p.put('R_PORT_ILIM',410,420,270);p.put('R_PORT_FAULT',420,630,270)
        p.text(100,330,'NRST 低时关断；故障锁存后复位核心板重试\n45.3k ILIM；外部连续预算 400mA\nPORT_FAULT_N → PE6，并引至扩展板',8)
        p.text(760,680,'自定义 GPIO / 2x3 直立排针 / 2.54mm',11);p.put('J_USER',1060,530)
        for r,x,y in [('PA0',900,530),('PB0',900,450),('PA1',1210,530),('PB1',1210,450)]:p.put('R_GPIO_'+r,x,y)
        p.put('D_GPIO_A',900,620);p.put('D_GPIO_B',1210,620)
        p.text(760,350,'1 GND / 2 3V3_AUX / 3 PA0 / 4 PA1 / 5 PB0 / 6 PB1\n四路均可配置 GPIO；ADC/PWM 复用由固件决定\n0Ω 用于隔离/测量；不得接入 5V、12V、24V 或 48V',8)
    elif page=='C10':
        p.text(100,1080,'XT30 / 12–48V 稳压电源 / 5V 2A 连续预算',11)
        p.put('J_XT30',150,950);p.put('F_INPUT',280,950);p.put('D_REVERSE',420,950,180)
        p.put('D_INPUT_TVS',520,840,270)
        refs=[f'C_HV_IN{i}' for i in range(1,5)]
        for i,r in enumerate(refs):p.put(r,130+i*95,710,90)
        p.banks.append(refs);p.bank(['C_HV_HF'],530,710)
        p.text(100,610,'100V 输入电容：48V 偏压后总有效容量需 ≥4.7µF\n48V TVS：钳位与插拔振铃必须实测；输入未做主动浪涌限流',8)
        p.put('U_HV',840,940);p.put('L_HV',1090,960)
        p.put('C_HV_BOOT',1000,880)
        p.bank(['C_HV_OUT1','C_HV_OUT2','C_HV_OUT3','C_HV_OUT_HF'],1120,820,100)
        p.put('R_HV_RT',830,750,270)
        p.put('R_HV_FB_TOP',970,760,270);p.put('R_HV_FB_BOT',970,650,270)
        p.put('R_HV_PG',680,760,270);p.put('TP_HV_PG',680,650)
        p.text(760,560,'LMR38025 / 300kHz / 15µH / 5.016V\n输出电容：3×22µF 16V；额定 2.5A，热预算按 2A\nHV_SW / BOOT 高频回路紧凑放置，远离 IMU 热岛',8)
        p.text(100,450,'低压差启动 / EN 开关',11)
        p.put('R_HV_EN_TOP1',180,350,270);p.put('R_HV_EN_TOP2',180,250,270);p.put('R_HV_EN_BOT',180,150,270)
        p.put('SW_POWER_EN',390,200,270)
        p.text(500,370,'330k + 330k / 100k：EN 欠压门限约 9.5V\nSW1101 仅关闭降压输出，XT30 输入端仍带电\n保险丝 2A / 125VDC；反接保护为 100V 串联肖特基\n输入最大 48V，不能直接接入满电超过 48V 的电池',9)
    else:raise ValueError(page)
    return p

class Route(Routing):
    def specials(self):
        q=self.plan.page
        def join(r,a,s,b,via=()):
            p0=self.p(r,a);p1=self.p(s,b)
            self.join(r,a,s,b,via,label=dict(x=(p0[0]+p1[0])/2,y=max(p0[1],p1[1])+3,align=6))
        if q=='C05':
            for i in range(1,4):
                u='U_CAN'+str(i);j='J_CAN'+str(i)
                join(u,'7',j,'2');join(u,'6',j,'3')
                for pin,suffix in [('1','TX'),('8','STB')]:
                    r=f'R_CAN{i}_{suffix}';a=self.p(r,'1');b=self.p(u,pin);join(r,'1',u,pin,[(a[0],b[1])])
        if q=='C06':
            join('U_USB_ESD','6','R_USB_DP','1');join('U_USB_ESD','4','R_USB_DM','1')
            a=self.p('R_VBUS_SER','2');b=self.p('U_VBUS','2');join('R_VBUS_SER','2','U_VBUS','2',[(a[0],b[1])])
            a=self.p('R_VBUS_PD','1');b=self.p('U_VBUS','2');join('R_VBUS_PD','1','U_VBUS','2',[(a[0],b[1])])
        if q=='C08':
            for port in ['USART1','USART2','USART3','USART6']:
                for dr,pin,offset in [('TX','3',40),('RX','4',25)]:
                    r='R_'+port+'_'+dr;j='J_'+port;a=self.p(r,'2');b=self.p(j,pin);xx=b[0]-offset;join(r,'2',j,pin,[(xx,a[1]),(xx,b[1])])
        if q=='C09':
            for i,k in enumerate(['SCK','MOSI','MISO','NSS']):
                r='R_SPI3_'+k;a=self.p(r,'2');b=self.p('J_SPI3',str(i+3));xx=b[0]-65+i*10;join(r,'2','J_SPI3',str(i+3),[(xx,a[1]),(xx,b[1])])
            for k,pin,offset in [('SCL','3',40),('SDA','4',25)]:
                r='R_I2C2_'+k;a=self.p(r,'2');b=self.p('J_I2C2',pin);xx=b[0]-offset;join(r,'2','J_I2C2',pin,[(xx,a[1]),(xx,b[1])])
            a=self.p('U_PORT','5');b=self.p('R_PORT_ILIM','1');join('U_PORT','5','R_PORT_ILIM','1',[(b[0],a[1])])
            a=self.p('U_PORT','4');b=self.p('R_PORT_FAULT','2');join('U_PORT','4','R_PORT_FAULT','2',[(b[0],a[1])])
        if q=='C10':
            join('F_INPUT','2','D_REVERSE','2')
            a=self.p('D_REVERSE','1');b=self.p('D_INPUT_TVS','1');join('D_REVERSE','1','D_INPUT_TVS','1',[(b[0],a[1])])
            a=self.p('U_HV','12');b=self.p('L_HV','1');join('U_HV','12','L_HV','1',[(1040,a[1]),(1040,b[1])])
            a=self.p('U_HV','10');b=self.p('C_HV_BOOT','1');join('U_HV','10','C_HV_BOOT','1',[(940,a[1]),(940,b[1])])
            a=self.p('U_HV','7');b=self.p('R_HV_RT','1');join('U_HV','7','R_HV_RT','1',[(920,a[1]),(920,b[1]),b])
            self.divider('R_HV_FB_TOP','R_HV_FB_BOT')
            join('R_HV_PG','2','TP_HV_PG','1')
            join('R_HV_EN_TOP1','2','R_HV_EN_TOP2','1')
            join('R_HV_EN_TOP2','2','R_HV_EN_BOT','1')
    def finish(self):
        for refs in self.plan.banks:self.bank(refs)
        self.specials()
        for ref,pins in self.pins.items():
            for number,p in pins.items():
                net=self.net(ref,number);pt=(p['x'],p['y'])
                if net=='NC' or any(w['net']==net and any(on_segment(pt,a,b) for a,b in segments(w['paths'])) for w in self.wires):continue
                length=30 if p['rotation']%180==0 else 20
                dx,dy={0:(length,0),90:(0,length),180:(-length,0),270:(0,-length)}[p['rotation']%360];end=(pt[0]+dx,pt[1]+dy)
                if dx:label=dict(x=end[0]+(2 if dx>0 else -2),y=end[1]+2,align=3 if dx>0 else 9)
                else:
                    neighbors=[v for k,v in pins.items() if k!=number and v['rotation']%180==90 and abs(v['x']-p['x'])<70]
                    label=dict(x=end[0]+3,y=end[1]+(3 if dy>0 else -3),align=3 if dy>0 else 9,rotation=90) if neighbors else dict(x=end[0]+5,y=end[1]+3,align=3)
                ground=end if net=='GND' and len(pins)==2 and dy<0 else None
                self.add(net,[[pt,end]],None if ground else label,ground)
        result=self.merge()
        for w in result:
            pending=list(w['paths']);ordered=[pending.pop(0)];seen=set(map(tuple,ordered[0]))
            while pending:
                i=next((i for i,path in enumerate(pending) if any(tuple(pt) in seen for pt in path)),None)
                if i is None:raise ValueError(('disconnected wire graph',w['net']))
                path=pending.pop(i);ordered.append(path);seen.update(map(tuple,path))
            w['paths']=ordered
        return result

def apply(page):
    p=plan(page);state=n.load_state();s=state['CORE'];pid=s['pages'][page];rows=[r for r in n.input_components('CORE') if r['page']==page]
    assert set(p.parts)=={r['reference'] for r in rows},(page,set(p.parts)^{r['reference'] for r in rows})
    guard='if((await eda.dmt_SelectControl.getCurrentDocumentInfo()).uuid!=='+json.dumps(pid)+')throw new Error("Wrong H735 page");'
    execute('await eda.dmt_EditorControl.openDocument('+json.dumps(pid)+');await new Promise(r=>setTimeout(r,300));return true;')
    ids=[s['components'][r['reference']]['id'] for r in rows]
    execute(guard+'const known=new Set('+json.dumps(ids)+');if((await eda.sch_PrimitiveComponent.getAll()).some(c=>c.componentType==="part"&&!known.has(c.primitiveId)))throw new Error("Untracked component: stop");const w=await eda.sch_PrimitiveWire.getAll();if(w.length)await eda.sch_PrimitiveWire.delete(w.map(x=>x.primitiveId));const f=(await eda.sch_PrimitiveComponent.getAll()).filter(c=>c.componentType==="netflag");if(f.length)await eda.sch_PrimitiveComponent.delete(f.map(x=>x.primitiveId));const t=await eda.sch_PrimitiveText.getAll();if(t.length)await eda.sch_PrimitiveText.delete(t.map(x=>x.primitiveId));return true;')
    for start in range(0,len(rows),8):
        items=[dict(ref=r['reference'],id=s['components'][r['reference']]['id'],**p.parts[r['reference']]) for r in rows[start:start+8]]
        got=execute(guard+'const out={};for(const i of '+json.dumps(items)+'){const a=(await eda.sch_PrimitiveComponent.get(i.id)).toAsync();a.setState_X(i.x);a.setState_Y(i.y);a.setState_Rotation(i.rotation);await a.done();out[i.ref]=await eda.sch_PrimitiveComponent.getAllPinsByPrimitiveId(i.id);}return out;')
        for ref,pins in got.items():s['components'][ref]['pins']=pins
    n.save_state(state);route=Route(p,rows,s);wires=route.finish()
    execute(guard+'await eda.sch_Document.save();await new Promise(r=>setTimeout(r,1000));return true;')
    for start in range(0,len(wires),8):
        chunk=wires[start:start+8]
        got=execute(guard+ATTR_JS+'const ids=[];for(const w of '+json.dumps(chunk)+'){const c=await eda.sch_PrimitiveWire.create(w.paths.map(p=>p.flat()),w.net);if(!c)throw new Error("Wire failed "+w.net);let shown=false;for(const a of await eda.sch_PrimitiveAttribute.getAll(c.getState_PrimitiveId())){if(a.key==="Name"||a.key==="NET"){const l=w.label||{x:0,y:0,align:3};await style(a,l.x,l.y,6,l.align,l.rotation||0,Boolean(w.label)&&!shown);shown=true;}}if(w.ground){await eda.sch_PrimitiveComponent.createNetFlag("Ground","GND",...w.ground);}ids.push(c.getState_PrimitiveId());}return ids;')
        for w,wid in zip(chunk,got):w['id']=wid
    for row in rows:
        ref=row['reference'];rec=s['components'][ref];pins=rec['pins'];pos=p.parts[ref];two=len(pins)==2 and not ref.startswith('J_');x,y=pos['x'],pos['y']
        if two and pos['rotation'] in [90,270]:rp=(x+14,y+7);np=(x+14,y-7);align=3
        elif two:rp=(x,y+13);np=(x,y-17);align=6
        else:rp=(min(z['x'] for z in pins)+10,max(z['y'] for z in pins)+17);np=(rp[0],min(z['y'] for z in pins)-20);align=3
        if not two and any(z['rotation']%360==270 for z in pins):np=(min(z['x'] for z in pins),min(z['y'] for z in pins)-60)
        if ref.startswith('D_CAN'):rp=(max(z['x'] for z in pins)+25,max(z['y'] for z in pins)-5)
        if ref.startswith('TP_'):rp=(x+10,y-13);np=(0,0)
        payload=dict(id=rec['id'],nets=n.pin_map(row,rec),rp=rp,np=np,align=align,show=not ref.startswith('TP_'))
        execute(guard+ATTR_JS+'const i='+json.dumps(payload)+';for(const a of await eda.sch_PrimitiveAttribute.getAll(i.id)){if(a.key==="Designator")await style(a,...i.rp,7,i.align,0,true);else if(a.key==="Name")await style(a,...i.np,6,i.align,0,i.show);}for(const p of await eda.sch_PrimitiveComponent.getAllPinsByPrimitiveId(i.id)){const a=p.toAsync();a.setState_NoConnected(i.nets[p.pinNumber]==="NC");await a.done();}return true;')
        rec['connections']=[]
        for pin,pp in route.pins[ref].items():
            net=route.net(ref,pin)
            if net=='NC':rec['connections'].append(dict(pin=pin,nc=True));continue
            w=next(w for w in wires if w['net']==net and any(on_segment((pp['x'],pp['y']),a,b) for a,b in segments(w['paths'])))
            rec['connections'].append(dict(pin=pin,net=net,id=w['id']))
        rec.update(functional_layout=True,wired=True,revision='R4B')
    execute(guard+'await eda.sch_Document.save();await new Promise(r=>setTimeout(r,1500));for(const i of '+json.dumps(p.notes,ensure_ascii=False)+'){const t=await eda.sch_PrimitiveText.create(i.x,i.y,i.text,0,"#213547",undefined,i.size,i.size>=10,false,false,1);if(!t)throw new Error("Text failed");}return await eda.sch_Document.save();')
    n.save_state(state);(n.HERE/('routing-R4B-'+page+'.json')).write_text(json.dumps(wires,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Saved compact R4B',page,len(rows),'parts',len(wires),'nets',flush=True)

if __name__=='__main__':
    for page in sys.argv[1:]:apply(page)
