import json,math,html
from pathlib import Path
import pymupdf
import native_design as n
D=json.loads((n.HERE/'pcb-placed.json').read_text(encoding='utf-8'));P=json.loads((n.HERE/'pcb-placement-plan.json').read_text(encoding='utf-8'));S=n.load_state()['CORE'];refmap={s['native_reference']:r for r,s in S['components'].items()}
for side in [1,2]:
 svg=['<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="1280" viewBox="-2 -4 44 47"><rect x="-2" y="-4" width="44" height="47" fill="#f8fafc"/><rect x="0" y="0" width="39.8" height="39.8" rx="1" fill="#e8f1ea" stroke="#153a2b" stroke-width="0.1"/>']
 svg.append('<text x="0" y="-1.6" font-size="1" font-family="Arial">H735 / '+('TOP' if side==1 else 'BOTTOM — transparent top view')+' / 39.8 × 39.8 mm</text>')
 for x,y in [(2.5,11),(37.3,11),(2.5,28.8),(37.3,28)]:
  svg.append(f'<circle cx="{x}" cy="{y}" r="2.1" fill="#fca5a530" stroke="#e03030" stroke-dasharray=".2 .2" stroke-width=".04"/><circle cx="{x}" cy="{y}" r="1.1" fill="white" stroke="#333" stroke-width=".07"/>')
 for c in D['components']:
  if c['layer']!=side:continue
  ref=c['designator'];b=D['bbox'][ref];x=b['minX']*.0254;y=-b['maxY']*.0254;w=(b['maxX']-b['minX'])*.0254;h=(b['maxY']-b['minY'])*.0254
  svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="#ffffff90" stroke="#385e83" stroke-width=".04"/>')
  for pad in D['pads'][ref]:
   if not isinstance(pad['pad'][1],(int,float)):continue
   x,y=pad['x']*.0254,-pad['y']*.0254;pw=pad['pad'][1];ph=pad['pad'][2] if len(pad['pad'])>2 else pw;pw*=.0254;ph*=.0254;a=-pad['rotation'];color='#cb8d36' if pad['layer']!=12 else '#e8ad44'
   svg.append(f'<rect x="{x-pw/2}" y="{y-ph/2}" width="{pw}" height="{ph}" transform="rotate({a},{x},{y})" fill="{color}" stroke="#704b1f" stroke-width=".025"/>')
  x=c['x']*.0254;y=-c['y']*.0254
  svg.append(f'<text x="{x}" y="{y}" font-family="Arial" font-size=".48" text-anchor="middle" fill="#031d49">{html.escape(ref)}</text>')
 svg.append('<text x="0" y="41.6" font-family="Arial" font-size=".65">Initial placement • no routing • API geometry review</text></svg>');f=n.HERE/'review-native'/('PCB-'+('TOP' if side==1 else 'BOTTOM')+'.svg');f.write_text(''.join(svg),encoding='utf-8');pdf=pymupdf.open('svg',f.read_bytes());pix=pdf[0].get_pixmap();pix.save(str(f.with_suffix('.png')))
print('rendered PCB')

