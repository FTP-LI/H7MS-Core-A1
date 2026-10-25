"""Publish a review of the current native schematic, including unresolved checks."""
import csv,json,html,math
from pathlib import Path
import native_design as n

def write_csv(name,rows):
    with (n.HERE/name).open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

s=n.load_state()['CORE'];rows=n.input_components('CORE');by={r['reference']:r for r in rows}
check=json.loads((n.HERE/'native-footprint-verification.json').read_text(encoding='utf-8'))
rev=json.loads((n.HERE/'core-interface-revision.json').read_text(encoding='utf-8'))
matrix=list(csv.DictReader((n.PLAN/'封装全部复用矩阵.csv').open(encoding='utf-8-sig')))
ball_pin={r['ball']:r['pin'] for r in matrix};resource=[];errors=[]
for ball,net in n.pin_map(by['U1'],s['components']['U1']).items():
    pin=ball_pin.get(ball,'');signal=net.replace('CAN','FDCAN') if net.startswith('CAN') else net
    if net in ['IMU_SCK','IMU_MOSI','IMU_MISO']:signal=net.replace('IMU_','SPI1_')
    af=[r['af'] for r in matrix if r['ball']==ball and r['signal']==signal]
    needs_af=signal.startswith(('FDCAN','USART','UART','LPUART','SPI','I2C')) and not signal.endswith('_STB')
    if needs_af and not af:errors.append(dict(ball=ball,pin=pin,signal=signal))
    use='核心内部'
    if net.startswith(tuple(rev['core_uarts'])):use='核心四针GH'
    elif net.startswith(tuple(rev['extension_uarts'])):use='上层扩展板/J801'
    elif net.startswith('EXP_'):use='核心自定义排针' if pin in rev['user_gpio'] else '上层扩展板/J802'
    elif net.startswith(('SPI3_','I2C2_')):use='核心GH接口'
    resource.append(dict(ball=ball,pin=pin,net=net,AF='/'.join(sorted(set(af))),destination=use))
assert not errors,errors
write_csv('R4B_主控100球与资源分配.csv',resource)
connectors=[]
for ref in ['J1','J2','J_CAN1','J_CAN2','J_CAN3',*[f'J_{p}' for p in rev['core_uarts']],'J_SPI3','J_I2C2','J_USER','J_XT30','J_USB']:
    for pin,net in n.pin_map(by[ref],s['components'][ref]).items():
        connectors.append(dict(reference=s['components'][ref]['native_reference'],function=ref,pin=pin,net=net,part=by[ref]['part'],LCSC=by[ref]['device']['supplierId']))
write_csv('R4B_核心接口与板间针序.csv',connectors)
bom=[]
native=json.loads((n.HERE/'native-CORE-netlist.json').read_text(encoding='utf-8'))
actual={c['props']['Designator']:c['props'] for c in native['components'].values()}
for r in rows:
    rec=s['components'][r['reference']]
    bom.append(dict(page=r['page'],reference=rec['native_reference'],function=r['reference'],part=actual[rec['native_reference']].get('Manufacturer Part',r['part']),LCSC=r['device']['supplierId'],assembly='TESTPOINT' if r['reference'].startswith('TP_') else r.get('assembly','FIT'),footprint_uuid=actual[rec['native_reference']]['Footprint'],notes=r.get('notes','')))
write_csv('R4B_当前核心板BOM.csv',bom)
budget=[('MCU及板载3.3V电路预留',3.3,.8,.88),('三路CAN最坏工况预留',5,.24,1),('IMU加热满占空比',5,.1,1),('3V3_AUX外部共享额度',3.3,.3,.88),('5V_PORT外部共享额度',5,.4,1),('其他板载/余量',5,.1,1)]
power=[dict(load=name,voltage_V=v,current_A=i,assumed_efficiency=e,equivalent_5V_A=round(v*i/(5*e),4)) for name,v,i,e in budget]
write_csv('R4B_电源预算.csv',power)
total=sum(p['equivalent_5V_A'] for p in power)
calc=dict(output_V=1+100/24.9,f_sw_kHz=(30970/88.7)**(1/1.027),ILIM_min_mA=25230/(45.3*1.01)**1.016,ILIM_max_mA=22980/(45.3*.99)**.94,input_energy_mJ=.5*18.8e-6*48**2*1000,input_charge_mC=18.8e-6*48*1000,allocated_5V_A=total,remaining_5V_A=2-total,resource_AF_errors=errors,manufacturing_ready=False)
(n.HERE/'R4B-quantitative-review.json').write_text(json.dumps(calc,ensure_ascii=False,indent=2),encoding='utf-8')
exceptions=[dict(code=k,reason=v) for k,v in __import__('audit_native_footprints').EXCEPTIONS.items() if k in {r['device']['supplierId'] for r in rows}]
(n.HERE/'drc-standardization-exceptions.json').write_text(json.dumps(dict(revision='R4B',note='封装来源例外；并非本次原生DRC告警的逐条分类。',exceptions=exceptions),ensure_ascii=False,indent=2),encoding='utf-8')
e=html.escape
def table(head,rr):return '<table><tr>'+''.join('<th>'+e(str(x))+'</th>' for x in head)+'</tr>'+''.join('<tr>'+''.join('<td>'+e(str(x))+'</td>' for x in row)+'</tr>' for row in rr)+'</table>'
warning=sum(g.get('count',0) for g in check['editor_drc']['groups'])
out=['<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>H735 R4B 原生工程核验</title><style>body{font:16px/1.65 system-ui,"Microsoft YaHei",sans-serif;max-width:1120px;margin:36px auto;padding:0 24px;color:#183044;background:#f6f8fa}h1,h2{line-height:1.2}h2{margin-top:36px}table{border-collapse:collapse;background:white;width:100%;font-size:14px}td,th{padding:8px;border:1px solid #d5dde5;text-align:left}img{width:100%;background:white;border:1px solid #ccd7e1}a{color:#175db4}.status{padding:18px;background:#fff1d2;border-left:5px solid #c78a18}code{overflow-wrap:anywhere}details{margin:14px 0}summary{cursor:pointer;font-weight:600}</style>']
out+=['<h1>H735 · R4B 核心板修改与核验</h1><p>2026-10-17。现有工程内通过绑定项目 UUID 的 API 修改；未导入替换工程，未操作桌面鼠标键盘。</p>',f'<div class="status"><b>原理图连接与封装关联检查通过；尚未完成设计发布。</b><br>{check["component_count"]} 个器件、{check["pin_count"]} 个引脚，网表与计划逐脚一致，封装非空且引脚/焊盘集合一致。原生 DRC 当前报告 {warning} 项警告、无 error 级结果；此客户端只返回数量，尚未取得并关闭全部明细。不能将独立检查通过解释为 DRC 已清零。PCB 仍为旧版 137 器件草案，不适用于本次接口和供电方案。</div>']
out+=['<h2>当前接口分配</h2>',table(['位置','接口','连接与电平'],[
('核心板','3×CAN','三针直立GH1.25：1 GND / 2 CANH / 3 CANL；120Ω 默认DNP，仅总线两端安装'),
('核心板','USART1/2/3/6','四针直立GH1.25：1 GND / 2 5V_PORT / 3 MCU_TX / 4 MCU_RX；信号3.3V'),
('核心板','SPI3 / I2C2','六针/四针直立GH；3.3V；SPI1专供BMI088'),
('核心板','自定义2×3排针','1 GND / 2 3V3_AUX / 3 PA0 / 4 PA1 / 5 PB0 / 6 PB1；2.54mm直立排针'),
('上层扩展','UART4/5/7/8/9、USART10、LPUART1','已连接到核心J801；扩展板原生原理图与PCB尚未完成'),
('核心板','USB4145直立USB-C','自供电USB FS设备；VBUS只检测，不从USB给整板供电'),
('核心板','XT30','12–48V稳压电源输入；48V是最大持续值，不适用于满电超过48V的电池')])]
out+=['<h2>器件与库来源</h2>',table(['功能','型号','立创编号'],[
('CAN GH3','BM03B-GHS-TBT(LF)(SN)','C161691'),('UART/I2C GH4','BM04B-GHS-TBT(LF)(SN)','C161692'),('SPI GH6','BM06B-GHS-TBT(LF)(SN)','C189892'),('自定义排针','2.54-2*3PLTPZ','C3152771'),('直立USB','USB4145-03-0070-C','C5815189'),('核心板B2B ×2','TFM-115-02-L-D-A','C5714577'),('扩展板配对候选 ×2','SFM-115-02-L-D-A-K-TR','C3323938'),('XT30直立输入','XT30UPB-M','C428721'),('80V降压','LMR38025SDRRR','C22405313'),('输入保险','0451002.MRL / 2A 125VDC','C99547'),('反接肖特基','STPS3H100U / 100V','C283521'),('输入TVS','SMBJ48A-13-F','C135078')]),f'<p>{check["official_footprint_instances"]} 个器件实例直接引用官方封装。普通阻容以0402为主；100V输入MLCC、储能电容和加热电阻按电气额定值使用更大封装。J1101使用可追溯的XT30修正版：铜盘2.50mm、间距5mm，厂家推荐钻孔1.90mm。修正版没有完整3D关联。</p><p>GH线端端子采用 JST SSHL-002T-P0.2，配对应GHR壳体。USB四个壳焊脚共用pad 0、拨动开关四个壳焊脚共用pad 4，是有意的同网编号，不属于漏封装。USB槽孔钢网工艺、排针和板间连接器的最终装配尺寸仍需装配审核。</p>']
out+=['<h2>电源预算与验证边界</h2>',table(['负载','电压 V','预算 A','折合5V A'],[(p['load'],p['voltage_V'],p['current_A'],p['equivalent_5V_A']) for p in power]),f'<p>5V连续预算2A；目前分配 {total:.3f}A，剩余 {2-total:.3f}A。3.3V转换效率按88%估计，需实测替换。外部所有5V端口合计400mA，所有3V3_AUX端口合计300mA，不能每个插座分别取该额度。</p><p>45.3kΩ、1% ILIM按TI经验公式估算限流范围 {calc["ILIM_min_mA"]:.0f}–{calc["ILIM_max_mA"]:.0f}mA；400mA是工作预算而非限流阈值。5V_PORT过流锁存后需NRST复位重试。</p><p>5V输出名义 {calc["output_V"]:.3f}V，88.7kΩ设频约 {calc["f_sw_kHz"]:.0f}kHz。15µH电感与3×22µF输出电容按TI的48V→5V/300kHz参考档配置。输入4×4.7µF/100V名义18.8µF不等于48V偏压下有效值；需取得Murata偏压与温度曲线，保证最坏条件总有效值≥4.7µF。</p><p>18.8µF在48V的名义储能为 {calc["input_energy_mJ"]:.1f}mJ、充电电荷 {calc["input_charge_mC"]:.3f}mC。输入MLCC插拔浪涌不受降压软启动控制；当前没有主动输入浪涌限流。必须在实际电源阻抗、线束和连接器条件下测输入峰值/振铃、保险I²t及反复热插拔。TVS额定钳位接近80V器件上限，走线寄生过冲不能忽略；未通过该测试前不能宣称48V输入已验收。</p><p>SW1101只控制EN，不切断XT30输入。需要维护级隔离时应拔掉输入连接器或使用上游断电装置。</p>']
out+=['<h2>40×40mm上下板与热岛</h2><p>核心板在最底，B2B公座在核心TOP、配对母座在扩展BOTTOM。USB、GH、XT30和自定义排针必须从扩展板窗口或外轮廓外露，同时预留插头外壳、锁扣和手指操作空间。旧版PCB的100触点、下挂扩展板布局已经失效。</p><p>本轮已确定60触点针序和核心接口器件，尚未完成这套212器件方案的40mm实际布局、上下板碰撞或3D审查。两组B2B的真实配对高度、公母朝向、底面反视针序、固定柱与插拔受力须用厂家机械图和实装进一步核对。不能只依据裸插座高度判断可插拔。</p><p>IMU岛内为BMI088、就近去耦、加热电阻、NTC及TMP302；MCU、降压和功率开关在岛外。保留机械桥并成组跨越电源、地和信号回流，避免大面积铜皮跨桥导致导热过强，也避免回流被槽切断。岛的尺寸/槽/桥尚未转成PCB制造结构。45°C为初始恒温验证目标；60°C硬件截止是保护，需验证温差、超调、复位关断、振动共振与零偏变化。</p>']
out+=['<h2>固件与验证</h2><p>本次100球AF复核无冲突；IMU由SPI4改到SPI1，ACC_CS改PE5，VBUS检测改PC8，PE6接PORT_FAULT_N。必须更新CubeMX/BSP和DMA请求配置；旧版SPI4/DMA及SDMMC/RMII等并发配置不能直接沿用。11路串口、SPI1/SPI3及ADC同时启用时的DMA/中断/Cache与带宽计划仍需固件工程验证。</p><ol><li>先限流供电测试12/24/48V，测5V/3.3V稳态、上电过冲、满负载温升和短路/反接行为。</li><li>四路核心UART逐口环回，再与扩展板其余串口同时收发，检查丢帧、错误计数和供电共享负载。</li><li>三路CAN分别验证终端数量、复位待机、总线故障，再做并发压力测试。</li><li>USB正反插、VBUS撤除、整板独立供电及拔插；SPI/I2C/自定义GPIO逐针核对，验证AUX关断无反灌。</li><li>IMU恒温、过温硬件禁止、NTC开短路、复位期间加热关断与机器人振动环境测试。</li><li>完成所有原生DRC明细分类后再同步新版PCB、做40mm机械装配与布线检查。</li></ol>']
out+=['<h2>核验文件</h2><ul><li><a href="H735-native-layout-review.pdf">11页原理图几何预览 PDF</a>（由原生源数据渲染，非编辑器截屏）</li><li><a href="../R4B_核心接口与板间针序.csv">接口和B2B针序 CSV</a></li><li><a href="../R4B_主控100球与资源分配.csv">100球/AF/资源分配 CSV</a></li><li><a href="../R4B_当前核心板BOM.csv">当前BOM CSV</a></li><li><a href="../R4B_电源预算.csv">电源预算 CSV</a></li><li><a href="../native-footprint-verification.json">封装与网表检查 JSON</a></li><li><a href="../'+e(Path(check['archive']).relative_to(n.HERE).as_posix())+'">原生工程备份 EPRO</a></li></ul>']
out+=['<h2>主要依据</h2><p><a href="https://www.st.com/resource/en/datasheet/stm32h735vg.pdf">ST H735数据手册</a>；<a href="https://www.jst-mfg.com/product/pdf/eng/eGH.pdf">JST GH机械图与配套件</a>；<a href="https://gct.co/connector/usb4145">GCT USB4145</a>；<a href="https://www.ti.com/lit/ds/symlink/lmr38025.pdf">TI LMR38025</a>；<a href="https://www.ti.com/lit/ds/symlink/tps2553.pdf">TI TPS2553限流器</a>；<a href="../reference-pdfs/xt30upb.pdf">AMASS XT30厂家图（本地副本）</a>。</p>']
for page in n.PAGE_NAMES:out+=['<details><summary>'+e(n.PAGE_NAMES[page])+'</summary><a href="'+page+'.svg"><img loading="lazy" src="'+page+'.png" alt="'+e(n.PAGE_NAMES[page])+'"></a></details>']
out+=['</html>'];(n.HERE/'review-native/H735-review.html').write_text('\n'.join(out),encoding='utf-8')
print('Review, current BOM, 100-ball AF audit, connector pinout and power budget exported')
