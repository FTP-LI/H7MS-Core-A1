"""Audit the exported native project, not the abandoned import draft.

Checks association, exact pad numbering and planned net connectivity. This is
not a replacement for the editor's DRC or a manufactured-board review.
"""
import argparse
import csv
import hashlib
import json
import math
import zipfile
from collections import Counter
from pathlib import Path

import native_design as n

OFFICIAL_LIBRARY = '0819f05c4eef4c71ace90d822a990e87'
EXCEPTIONS = {
    'C2671243': '修正VIO/EP符号后建立的器件关联副本；封装几何沿用官方库，导出来源记录为个人库',
    'C5184243': 'USB官方封装B5/A8位置错误；按GCT B4修正，并取消外壳槽孔锡膏开口',
    'C79167': '沿用官方焊盘几何；修正符号和焊盘编号的转义不一致',
    'LOCAL_TP_0.8': '非采购器件；0.8mm裸铜测试点，开阻焊且不开锡膏',
    'C428721': '沿用官方焊盘与间距，按 AMASS 图纸将 XT30 通孔钻径改为1.90mm；省略装饰圆弧，无3D关联',
}


def audit(archive):
    state = n.load_state()['CORE']
    net = json.loads((n.HERE/'native-CORE-netlist.json').read_text(encoding='utf-8'))
    components = net['components']
    parts = {p['props']['Designator']: p for p in components.values()}
    errors, rows = [], []
    if len(parts) != len(components):
        errors.append({'type': 'duplicate_designator'})
    if len(components) != len(state['components']):
        errors.append({'type': 'component_count', 'netlist': len(components), 'state': len(state['components'])})
    with zipfile.ZipFile(archive) as z:
        footprints = {}
        for row in n.input_components('CORE'):
            rec = state['components'][row['reference']]
            ref = rec['native_reference']
            component = parts[ref]
            props = component['props']
            fp = props.get('Footprint')
            if not fp or f'FOOTPRINT/{fp}.efoo' not in z.namelist():
                errors.append({'type': 'missing_footprint', 'ref': ref})
                continue
            if fp not in footprints:
                footprints[fp] = [json.loads(line) for line in z.read(f'FOOTPRINT/{fp}.efoo').decode('utf-8').splitlines() if line.strip()]
            data = footprints[fp]
            pads = [x for x in data if x[0] == 'PAD']
            numbers = [str(x[5]) for x in pads]
            pin_numbers = set(component['pinInfoMap'])
            if not pads or set(numbers) != pin_numbers:
                errors.append({'type': 'pin_pad_mismatch', 'ref': ref,
                    'pins_without_pads': sorted(pin_numbers-set(numbers)),
                    'pads_without_pins': sorted(set(numbers)-pin_numbers)})
            code = row['device']['supplierId']
            repeated={k:v for k,v in Counter(numbers).items() if v>1}
            allowed={'C5815189':{'0':4},'C431540':{'4':4}}.get(code,{})
            if repeated != allowed:
                errors.append({'type': 'duplicate_pad_number', 'ref': ref})
            for number, wanted in n.pin_map(row, rec).items():
                actual = component['pinInfoMap'].get(number, {}).get('net')
                valid = actual == wanted
                if wanted == 'NC':
                    valid = not actual or actual.startswith('$')
                if not valid:
                    errors.append({'type': 'net_mismatch', 'ref': ref, 'pin': number,
                        'expected': wanted, 'actual': actual})
            head = next(x[1] for x in data if x[0] == 'HEAD')
            source = head.get('source', '')
            official = source.split('|')[-1] == OFFICIAL_LIBRARY
            code = row['device']['supplierId']
            rows.append(dict(page=n.PAGE_NAMES[row['page']], reference=ref,
                function=row['reference'], manufacturer_part=props.get('Manufacturer Part'),
                supplier_id=code, package=props.get('FootprintName'),
                footprint_source='官方库' if official else '修正版/项目测试点',
                footprint_uuid=fp, source_library=source, pad_count=len(pads),
                exception=EXCEPTIONS.get(code, '') if not official else '',
                symbol_note='符号修正VIO/EP；PCB封装采用官方几何副本' if code=='C2671243' else ''))
            if ref == state['components']['J_USB']['native_reference']:
                if code=='C5815189':audit_usb4145(pads,data,errors)
                else:audit_usb(pads, data, errors)
    counts = Counter(r['package'] for r in rows if r['reference'].startswith(('R', 'C')))
    drc_path=n.HERE/'native-drc-result.json'
    drc=json.loads(drc_path.read_text(encoding='utf-8')) if drc_path.exists() else {'passed':None}
    drc['details']='当前3.2版API只返回级别和数量。旧版4位号供应商属性告警清单不能代表本次结果；未屏蔽规则，未声称告警已清零。'
    report = dict(archive=str(archive.resolve()), sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
        component_count=len(components), pin_count=sum(len(p['pinInfoMap']) for p in components.values()),
        official_footprint_instances=sum(r['footprint_source']=='官方库' for r in rows),
        purchased_components=sum(not r['supplier_id'].startswith('LOCAL_') for r in rows),
        passive_package_counts=dict(counts), errors=errors,
        checks='原生工程封装存在性、非空焊盘、精确引脚编号、连接计划一致性、USB4145信号焊盘/外壳槽孔尺寸；钢网工艺与完整机械装配尚待审核',
        editor_drc=drc,
        fabrication_ready=False)
    (n.HERE/'native-footprint-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    with (n.HERE/'官方封装核对与例外.csv').open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    print(json.dumps(report,ensure_ascii=False,indent=2))
    return not errors


def audit_usb4145(pads,data,errors):
    expected={}
    for row,pins in [('A',[1,4,5,6,7,8,9,12]),('B',[12,9,8,7,6,5,4,1])]:
        for number,x in zip(pins,[-2.75,-1.25,-.75,-.25,.25,.75,1.25,2.75]):
            expected[row+str(number)]=(x,1.48 if row=='A' else -1.48)
    for p in pads:
        number=str(p[5])
        if number=='0':
            vals=[abs(p[6])*.0254,abs(p[7])*.0254,*sorted(v*.0254 for v in p[10][1:3]),*sorted(v*.0254 for v in p[9][1:3])]
            want=[4,1.43,1.1,1.6,.6,1.1]
        else:
            vals=[p[6]*.0254,p[7]*.0254,p[10][1]*.0254,p[10][2]*.0254]
            want=[*expected[number],.3,1.15]
        if any(abs(a-b)>.003 for a,b in zip(vals,want)):
            errors.append(dict(type='usb4145_pad_geometry',pad=number,actual=vals,expected=want))
    holes=[x for x in data if x[0]=='FILL' and x[4]==12]
    if len(holes)!=2:errors.append(dict(type='usb4145_locator_hole_count',count=len(holes)))


def audit_usb(pads, data, errors):
    alias={'S1':'1','S2':'4','S3':'2','S4':'3'}
    by_number={p[5]:p for p in pads}
    with (n.PLAN/'连接器与保护器件焊盘.csv').open(encoding='utf-8-sig') as f:
        expected=[r for r in csv.DictReader(f) if r['board']=='CORE' and r['reference']=='J_USB']
    for r in expected:
        if r['type']=='NPTH':
            circles=[x[7][0] for x in data if x[0]=='FILL' and x[4]==12 and len(x[7])==1 and x[7][0][0]=='CIRCLE']
            target=[float(r['x_mm']),-float(r['y_mm']),float(r['width_mm'])/2]
            if not any(all(abs(a*0.0254-b)<0.003 for a,b in zip(c[1:],target)) for c in circles):
                errors.append({'type':'usb_npth_geometry','pad':r['pad']})
            continue
        number=alias.get(r['pad'],r['pad'].replace('_','-'))
        p=by_number.get(number)
        if p is None:
            continue
        actual=[p[6],p[7],p[10][1],p[10][2]]
        wanted=[float(r['x_mm']),-float(r['y_mm']),float(r['width_mm']),float(r['height_mm'])]
        if not all(abs(a*0.0254-b)<0.003 for a,b in zip(actual,wanted)):
            errors.append({'type':'usb_pad_geometry','pad':number})
        if not math.isclose(p[17]*0.0254,0.05,abs_tol=0.001):
            errors.append({'type':'usb_solder_mask','pad':number})
        if r['type']=='PTH_SLOT':
            h=p[9]
            valid=h[0]=='SLOT' and abs(h[1]*0.0254-float(r['drill_y_mm']))<0.003 and abs(h[2]*0.0254-float(r['drill_x_mm']))<0.003
            valid=valid and p[14]==90 and p[15]==1 and p[19]<=-max(p[10][1:])/2 and p[20]<=-max(p[10][1:])/2
            if not valid:errors.append({'type':'usb_slot_or_paste','pad':number})
        elif p[19]!=0:
            errors.append({'type':'usb_signal_paste','pad':number})


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('archive',type=Path)
    args=parser.parse_args()
    raise SystemExit(0 if audit(args.archive) else 1)
