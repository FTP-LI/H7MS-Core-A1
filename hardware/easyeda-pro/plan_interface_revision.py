"""R4: all serial ports, vertical connectors and reduced upward expansion."""
import json
import native_design as n
cat=n.catalog();mcu=json.loads((n.HERE/'core-revision-mcu-pin-plan.json').read_text(encoding='utf-8'))
rev=dict(enabled=False,revision='R4-interface-20261017',replace={},add=[])
def part(ref,page,code,pins,**kw):
    return dict(reference=ref,page=page,part=cat[code]['manufacturerId'],supplierId=code,pins={str(k):v for k,v in pins.items()},**kw)
def add(ref,page,code,pins,**kw):rev['add'].append(part(ref,page,code,pins,**kw))
mcu['pins']['A1']='PORT_FAULT_N';rev['replace']['U1']={'pins':mcu['pins']}
up={p:'GND' for p in ['A1','A12','B1','B12']}
up.update({p:'USB_VBUS' for p in ['A4','A9','B4','B9']})
up.update({p:'USB_DP_CONN' for p in ['A6','B6']});up.update({p:'USB_DM_CONN' for p in ['A7','B7']})
up.update(A5='USB_CC1',B5='USB_CC2',A8='NC',B8='NC');up['0']='USB_SHELL'
rev['replace']['J_USB']=part('J_USB','C06','C5815189',up,notes='Vertical, 7.46 mm; official pad geometry checked against GCT A2. Shell repeated pad 0 is intentional.')
add('D_USB_CC','C06','C1855726',{1:'USB_CC1',2:'USB_CC2',3:'GND'})
for i in range(1,4):
    add('J_CAN'+str(i),'C05','C161691',{1:'GND',2:f'CAN{i}_H',3:f'CAN{i}_L',4:'GND',5:'GND'},notes='GH1.25 top entry: 1 GND, 2 H, 3 L; 4/5 mechanical anchors grounded.')
    add('R_CAN'+str(i)+'_TERM','C05','C17909',{1:f'CAN{i}_H',2:f'CAN{i}_L'},assembly='DNP',notes='120 ohm endpoint termination: do not populate except at bus end; exactly two total terminations per bus.')
for port in mcu['ports']:
    add('J_'+port,'C08','C161692',{1:'GND',2:'5V_PORT',3:port+'_TX_CONN',4:port+'_RX_CONN',5:'GND',6:'GND'},notes='GH1.25 top entry: 1 GND / 2 +5V_PORT / 3 MCU_TX / 4 MCU_RX. 3.3V logic. 5V budget shared.')
    for dr in ['TX','RX']:add('R_'+port+'_'+dr,'C08','C106232',{1:port+'_'+dr,2:port+'_'+dr+'_CONN'})
    add('D_'+port,'C08','C1855726',{1:port+'_TX_CONN',2:port+'_RX_CONN',3:'GND'})
add('J_SPI3','C09','C189892',{1:'GND',2:'3V3_AUX',3:'SPI3_SCK_CONN',4:'SPI3_MOSI_CONN',5:'SPI3_MISO_CONN',6:'SPI3_NSS_CONN',7:'GND',8:'GND'})
for name in ['SCK','MOSI','MISO','NSS']:add('R_SPI3_'+name,'C09','C114765',{1:'SPI3_'+name,2:'SPI3_'+name+'_CONN'})
add('D_SPI3_A','C09','C1855726',{1:'SPI3_SCK_CONN',2:'SPI3_MOSI_CONN',3:'GND'})
add('D_SPI3_B','C09','C1855726',{1:'SPI3_MISO_CONN',2:'SPI3_NSS_CONN',3:'GND'})
add('J_I2C2','C09','C161692',{1:'GND',2:'3V3_AUX',3:'I2C2_SCL_CONN',4:'I2C2_SDA_CONN',5:'GND',6:'GND'})
for name in ['SCL','SDA']:
    add('R_I2C2_'+name,'C09','C114765',{1:'I2C2_'+name,2:'I2C2_'+name+'_CONN'})
    add('R_I2C2_'+name+'_PU','C09','C105871',{1:'3V3_AUX',2:'I2C2_'+name+'_CONN'})
add('D_I2C2','C09','C1855726',{1:'I2C2_SCL_CONN',2:'I2C2_SDA_CONN',3:'GND'})
add('U_PORT','C09','C111738',{1:'5V_IN',2:'GND',3:'NRST',4:'PORT_FAULT_N',5:'PORT_ILIM',6:'5V_PORT'},notes='TPS2553-1 latch-off: reset core to retry. All UART and B2B 5V outputs share this rail.')
add('R_PORT_FAULT','C09','C60491',{1:'3V3_D',2:'PORT_FAULT_N'})
add('R_PORT_ILIM','C09','C137977',{1:'PORT_ILIM',2:'GND'},notes='45.3 kohm: current limit bounds calculated separately; allocated continuous external budget 0.4 A.')
for ref,net,code in [('C_PORT_IN','5V_IN','C2167399'),('C_PORT_IN_HF','5V_IN','C2181015'),('C_PORT_OUT','5V_PORT','C84416'),('C_PORT_OUT_HF','5V_PORT','C2181015')]:add(ref,'C09',code,{1:net,2:'GND'})
j1=['GND','5V_PORT','GND','3V3_AUX','CAN1_H','CAN1_L','GND','CAN2_H','CAN2_L','GND','CAN3_H','CAN3_L','GND','NRST','PORT_FAULT_N','EXP_PE10','EXP_PD11','EXP_PB7','EXP_PC10','EXP_PC11']
j2=['GND','5V_PORT','EXP_PA0','EXP_PA1','EXP_PA2','EXP_PA3','GND','3V3_AUX','EXP_PA4','EXP_PA8','EXP_PB0','EXP_PB1','GND','EXP_PB12','EXP_PB13','EXP_PC0','EXP_PC1','EXP_PC4','EXP_PC5','EXP_PC9']
for ref,nets in [('J1',j1),('J2',j2)]:rev['replace'][ref]=part(ref,'C07','C2940504',dict(enumerate(nets,1)),notes='Core TOP TFM-110; upper extension BOTTOM SFM-110. R4 pinout incompatible with previous 50-pin pair. No external 5V input on these contacts.')
free={v for v in mcu['pins'].values() if v.startswith('EXP_')}
assert free=={v for v in j1+j2 if v.startswith('EXP_')}
assert len(free)==20
path=n.HERE/'core-interface-revision.json';assert not path.exists(),'Do not overwrite active revision'
path.write_text(json.dumps(rev,ensure_ascii=False,indent=2),encoding='utf-8')
print('Prepared',len(rev['add']),'new parts;',len(rev['replace']),'replacements; 20 free GPIO to upward B2B')
