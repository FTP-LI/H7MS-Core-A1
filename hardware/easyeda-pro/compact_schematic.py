"""Topology-preserving compaction of the current native schematic, never scaling symbols."""
import json,sys
from pathlib import Path
import native_design as n
from eda_bridge import execute
BEFORE=n.HERE/'compact-before.json'
class Axis:
 def __init__(self,intervals,gap=40):
  merged=[]
  for lo,hi in sorted(intervals):
   if merged and lo<=merged[-1][1]:merged[-1][1]=max(hi,merged[-1][1])
   else:merged.append([lo,hi])
  self.cuts=[(a[1],b[0],min(gap,b[0]-a[1])) for a,b in zip(merged,merged[1:])]
 def __call__(self,v):
  v=round(v,5);removed=0
  for a,b,g in self.cuts:
   if v>=b:removed+=b-a-g
   elif v>a:removed+=(v-a)*(1-g/(b-a))
  return round(v-removed,5)
def prepare(d,page):
 axes=[]
 for axis in ['x','y']:
  intervals=[]
  for c in d['components']:
   if c['componentType']!='part':continue
   pts=d['pins'][c['primitiveId']];vs=[c[axis]]+[p[axis] for p in pts]
   pad=16 if axis=='y' else 15
   lo=min(vs)-pad;hi=max(vs)+pad
   if axis=='x' and len(pts)==2 and c['rotation'] in [90,270]:hi+=25
   intervals.append((lo,hi))
  axes.append(Axis(intervals,30 if axis=='y' else 45))
 fx,fy=axes
 # Keep the page title and circuit top baseline at their established locations.
 shiftx=100-fx(100);shifty=1100-fy(1100)
 X=lambda x:fx(x)+shiftx;Y=lambda y:fy(y)+shifty
 cs=[];ws=[];ats=[];ts=[]
 for c in d['components']:
  if c['componentType']=='sheet':continue
  x,y=X(c['x']),Y(c['y']);dx=x-c['x'];dy=y-c['y'];cs.append(dict(id=c['primitiveId'],x=x,y=y))
  for a in d['attrs'].get(c['primitiveId'],[]):
   if a.get('x') is not None and a.get('valueVisible'):ats.append(dict(id=a['primitiveId'],x=a['x']+dx,y=a['y']+dy))
 for w in d['wires']:
  line=w['line'];paths=line if line and isinstance(line[0],list) else [line[i:i+4] for i in range(0,len(line),4)]
  mapped=[[X(v) if i%2==0 else Y(v) for i,v in enumerate(path)] for path in paths]
  ws.append(dict(id=w['primitiveId'],line=mapped,net=w['net']))
  for a in d['attrs'].get(w['primitiveId'],[]):
   if a.get('x') is not None and a.get('valueVisible'):ats.append(dict(id=a['primitiveId'],x=X(a['x']),y=Y(a['y'])))
 for t in d['texts']:ts.append(dict(id=t['primitiveId'],x=X(t['x']),y=Y(t['y'])))
 return dict(components=cs,wires=ws,attrs=ats,texts=ts,saved_width=round(1500-(X(1500)-X(0)),1),saved_height=round(1100-(Y(1100)-Y(0)),1))
def run(apply=False):
 data=json.loads(BEFORE.read_text(encoding='utf-8'));state=n.load_state();s=state['CORE'];plans={p:prepare(d,p) for p,d in data.items()}
 (n.HERE/'compact-plan.json').write_text(json.dumps(plans,ensure_ascii=False,indent=2),encoding='utf-8')
 for page,pl in plans.items():
  print(page,'removed empty space',pl['saved_width'],pl['saved_height'],flush=True)
  if not apply:continue
  pid=s['pages'][page];guard='if((await eda.dmt_SelectControl.getCurrentDocumentInfo()).uuid!=='+json.dumps(pid)+')throw new Error("Wrong page");'
  execute('await eda.dmt_EditorControl.openDocument('+json.dumps(pid)+');await new Promise(r=>setTimeout(r,250));return true;')
  execute(guard+'const ids=(await eda.sch_PrimitiveWire.getAll()).map(w=>w.primitiveId);if(ids.length)await eda.sch_PrimitiveWire.delete(ids);return true;')
  for kind,api in [('components','sch_PrimitiveComponent'),('texts','sch_PrimitiveText')]:
   for start in range(0,len(pl[kind]),15):
    payload=pl[kind][start:start+15]
    execute(guard+'for(const i of '+json.dumps(payload)+'){const a=(await eda.'+api+'.get(i.id)).toAsync();a.setState_X(i.x);a.setState_Y(i.y);await a.done();}return true;')
  attrs_by_id={a['id']:a for a in pl['attrs']}
  wire_ids={w['primitiveId'] for w in data[page]['wires']}
  component_attr_ids={a['primitiveId'] for parent,aa in data[page]['attrs'].items() if parent not in wire_ids for a in aa}
  for start in range(0,len(pl['attrs']),20):
   payload=[a for a in pl['attrs'][start:start+20] if a['id'] in component_attr_ids]
   execute(guard+'for(const i of '+json.dumps(payload)+'){const a=(await eda.sch_PrimitiveAttribute.get(i.id)).toAsync();a.setState_X(i.x);a.setState_Y(-i.y);await a.done();}return true;')
  replacements={}
  for w in pl['wires']:
   aa=[a for a in data[page]['attrs'][w['id']] if a.get('key')=='Name'];old=aa[0] if aa else {};at=attrs_by_id.get(old.get('primitiveId'),{})
   label={**old,**at};payload={**w,'label':label}
   result=execute(guard+'const i='+json.dumps(payload)+';const w=await eda.sch_PrimitiveWire.create(i.line,i.net);if(!w)throw new Error("Wire creation failed: "+i.id);const aa=await eda.sch_PrimitiveAttribute.getAll(w.getState_PrimitiveId());for(const a of aa){if(a.key==="Name"){const b=a.toAsync();b.setState_ValueVisible(Boolean(i.label.valueVisible));if(i.label.x!==undefined&&i.label.x!==null){b.setState_X(i.label.x);b.setState_Y(-i.label.y);b.setState_FontSize(6);b.setState_Rotation(i.label.rotation||0);b.setState_AlignMode(i.label.alignMode===6?3:i.label.alignMode===8?9:i.label.alignMode===7?6:3);}await b.done();}}return w.getState_PrimitiveId();')
   replacements[w['id']]=result
  for rec in s['components'].values():
   for conn in rec.get('connections',[]):
    if conn.get('id') in replacements:conn['id']=replacements[conn['id']]
  pins=execute(guard+'const p={};for(const c of await eda.sch_PrimitiveComponent.getAll()){if(c.componentType==="part")p[c.primitiveId]=await eda.sch_PrimitiveComponent.getAllPinsByPrimitiveId(c.primitiveId);}await eda.sch_Document.save();return p;')
  for rec in s['components'].values():
   if rec['id'] in pins:rec['pins']=pins[rec['id']]
  n.save_state(state)
  print(page,'saved',flush=True)
if __name__=='__main__':run('--apply' in sys.argv)
