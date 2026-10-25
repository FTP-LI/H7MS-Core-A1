"""Independent placement checks against the live SCH netlist and mechanical CSV."""
import json,csv,math
from collections import Counter
import native_design as n

d=json.loads((n.HERE/'pcb-placed.json').read_text(encoding='utf-8'))
net=json.loads((n.HERE/'native-CORE-netlist.json').read_text(encoding='utf-8'))
s=n.load_state()['CORE'];byref={c['designator']:c for c in d['components']}
errors=[];pads_checked=0;connector_checks=[]
for row in n.input_components('CORE'):
    rec=s['components'][row['reference']];ref=rec['native_reference'];c=byref[ref]
    if c['uniqueId']!=rec['uniqueId']:errors.append(['unique_id',ref])
    expected=n.pin_map(row,rec);actual={p['padNumber']:p for p in d['pads'][ref]}
    if set(expected)!=set(actual):errors.append(['pad_numbers',ref])
    for pin,want in expected.items():
        pads_checked+=1;got=actual[pin]['net']
        if want=='NC':
            if got and not got.startswith('$'):errors.append(['nc_net',ref,pin,got])
        elif got!=want:errors.append(['pad_net',ref,pin,want,got])
with (n.PLAN/'连接器与保护器件焊盘.csv').open(encoding='utf-8-sig') as f:
    for r in csv.DictReader(f):
        if r['board']!='CORE' or r['reference'] not in ['J1','J2'] or r['type']!='SMD':continue
        ref='J801' if r['reference']=='J1' else 'J802';cy=4.8 if ref=='J801' else 35
        p=next(p for p in d['pads'][ref] if p['padNumber']==r['pad'])
        wanted=(19.9-float(r['x_mm']),cy+float(r['y_mm']))
        actual=(p['x']*.0254,-p['y']*.0254)
        delta=max(abs(a-b) for a,b in zip(wanted,actual))
        if delta>.003 or p['layer']!=2 or p['net']!=r['net']:errors.append(['connector',ref,r['pad'],delta])
        connector_checks.append(delta)
bounds=[];edge_annotations=[]
for ref,b in d['bbox'].items():
    bmm=[b['minX']*.0254,-b['maxY']*.0254,b['maxX']*.0254,-b['minY']*.0254]
    if min(bmm)<-.003 or max(bmm)>39.803:
        if ref=='J701' and bmm[2]<=39.851:
            edge_annotations.append(dict(ref=ref,bbox_mm=bmm,reason='Layer 13 mouth-edge guide centered at x=39.8 mm, 0.1 mm stroke; 0.05 mm extends outside. Not copper or board outline.'))
        else:bounds.append([ref,bmm])
if bounds:errors.append(['footprint_bbox_outside',bounds])
overlaps=[]
for i,a in enumerate(d['components']):
    for b in d['components'][i+1:]:
        if a['layer']!=b['layer']:continue
        ab=d['bbox'][a['designator']];bb=d['bbox'][b['designator']]
        dx=min(ab['maxX'],bb['maxX'])-max(ab['minX'],bb['minX']);dy=min(ab['maxY'],bb['maxY'])-max(ab['minY'],bb['minY'])
        if dx>0 and dy>0:overlaps.append([a['designator'],b['designator'],round(dx*.0254,3),round(dy*.0254,3)])
records=[]
for line in d['source'].splitlines():
    if '||' in line:
        a,b=line.split('||');records.append((json.loads(a),json.loads(b.rstrip('|'))))
types=Counter(a['type'] for a,b in records)
layers=json.loads((n.HERE/'pcb-sync-verification.json').read_text(encoding='utf-8'))['layers']
drc=json.loads((n.HERE/'pcb-drc-details.json').read_text(encoding='utf-8'))
out=dict(component_count=len(byref),pin_pad_checks=pads_checked,component_layers=dict(Counter(c['layer'] for c in d['components'])),
    errors=errors,connector_pads_checked=len(connector_checks),connector_max_coordinate_error_mm=max(connector_checks),
    footprint_bbox_overlaps=overlaps,footprint_bboxes_within_board_except_edge_annotation=not bounds,edge_annotation_exceptions=edge_annotations,
    board_mm=[39.8,39.8],source_record_types=dict(types),layers=layers,
    physical_stack=[b for a,b in records if a['type']=='LAYER_PHYS'],
    drc_groups=[dict(name=g['name'],count=g['count']) for g in drc],
    caveat='Initial placement; footprint bounding boxes are not a complete 3D collision or assembly check. Physical stack and routing remain unfinished.',fabrication_ready=False)
(n.HERE/'pcb-placement-verification.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
(n.HERE/'review-native/CORE.epcb').write_text(d['source'],encoding='utf-8')
print({k:out[k] for k in ['component_count','pin_pad_checks','component_layers','errors','connector_pads_checked','connector_max_coordinate_error_mm','footprint_bbox_overlaps','footprint_bboxes_within_board_except_edge_annotation','source_record_types','drc_groups']})
assert not errors
