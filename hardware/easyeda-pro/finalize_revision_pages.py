"""Normalize sheet sizes, add thermal-island guidance, and preserve known project identity."""
import json
import native_design as n
from eda_bridge import execute,TARGET_WINDOW
s=n.load_state()['CORE'];report={}
for page,pid in s['pages'].items():
    if page not in ['C08','C09','C10']:continue
    report[page]=execute('await eda.dmt_EditorControl.openDocument('+json.dumps(pid)+');await new Promise(r=>setTimeout(r,500));if((await eda.dmt_SelectControl.getCurrentDocumentInfo()).uuid!=='+json.dumps(pid)+')throw new Error("Wrong page");await eda.dmt_Schematic.modifySchematicPageTitleBlock(true,{Size:{showTitle:false,showValue:false,value:"A3"}});await eda.sch_Document.save();return await eda.dmt_Schematic.getSchematicPageInfo('+json.dumps(pid)+');')
pid=s['pages']['C04']
note='IMU 热隔离岛 / PCB 设计约束\n岛内：BMI088、就近去耦、4×200Ω加热电阻、NTC、TMP302\n岛外：MCU、两级降压、电感、加热开关和功率 MOSFET\n岛边开槽并留机械桥；电源/地/信号回流成组跨桥\n隔热同时保留刚性，不能把岛做成易共振的悬臂\n最终槽宽、桥宽、岛尺寸需热仿真/振动与样机验证\n恒温目标先按45°C验证；60°C硬件禁止不是正常设定点\nSPI1 PA5/PA6/PA7，ACC_CS=PE5；旧SPI4固件需修改'
execute('await eda.dmt_EditorControl.openDocument('+json.dumps(pid)+');await new Promise(r=>setTimeout(r,800));const old=(await eda.sch_PrimitiveText.getAll()).filter(t=>String(t.content||t.text||t.value||"").startsWith("IMU 热隔离岛"));if(old.length)await eda.sch_PrimitiveText.delete(old.map(t=>t.primitiveId));const t=await eda.sch_PrimitiveText.create(880,400,'+json.dumps(note,ensure_ascii=False)+',0,"#213547",undefined,8,false,false,false,1);if(!t)throw new Error("Thermal note failed");return await eda.sch_Document.save();')
(n.HERE/'revision-page-check.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
p=n.HERE/'native-authoring-policy.json';d=json.loads(p.read_text(encoding='utf-8'));d['target_window']=TARGET_WINDOW;d['revision']='R4B';p.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8')
print('A3 normalized, IMU thermal note saved',flush=True)
