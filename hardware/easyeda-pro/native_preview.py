"""Review images from exported symbols and live native schematic records.

This is an independent geometry preview, not an editor screen capture. The
v2 archive exporter resets some wire-label positions, so use live v3 attributes.
"""
import argparse,json,math,zipfile,html,re
from collections import defaultdict
from pathlib import Path
import pymupdf
import native_design as n

OUT=n.HERE/'review-native'

def read_v3(path):
    out=[]
    for line in path.read_text(encoding='utf-8').splitlines():
        if '||' in line:
            a,b=line.split('||');out.append((json.loads(a),json.loads(b.rstrip('|'))))
    return out

def render(archive):
    OUT.mkdir(exist_ok=True)
    z=zipfile.ZipFile(archive)
    def records(name):return [json.loads(l) for l in z.read(name).decode().splitlines() if l.strip()]
    project=json.loads(z.read('project.json'));sch=project['schematics']['2121c62f1518d7c9']
    pages=[]
    for sheet in sch['sheets']:
        key=next(k for k,v in n.load_state()['CORE']['pages'].items() if v==sheet['uuid'])
        src=OUT/(key+'.esch')
        if not src.exists():continue
        rr=records('SHEET/2121c62f1518d7c9/'+str(sheet['id'])+'.esch')
        aa=defaultdict(dict)
        for r in rr:
            if r[0]=='ATTR':aa[r[2]][r[3]]=r[4]
        symbols={aa[r[1]].get('Designator'):records('SYMBOL/'+aa[r[1]]['Symbol']+'.esym') for r in rr if r[0]=='COMPONENT' and aa[r[1]].get('Designator')}
        live=read_v3(src);la=defaultdict(dict)
        for a,b in live:
            if a['type']=='ATTR':la[b['parentId']][b['key']]=b
        svg=['<svg xmlns="http://www.w3.org/2000/svg" width="1655" height="1170" viewBox="0 0 1655 1170">','<rect width="1655" height="1170" fill="white"/>']
        def line(p,q,color='#087d31',width=.8):
            svg.append(f'<line x1="{p[0]}" y1="{p[1]}" x2="{q[0]}" y2="{q[1]}" stroke="{color}" stroke-width="{width}"/>')
        def text(x,y,t,size=8,align='LEFT_BOTTOM',rotation=0,color='#161689',bold=False):
            anchor='end' if align.startswith('RIGHT') else 'middle' if align.startswith('CENTER') else 'start'
            baseline=size*.85 if align.endswith('TOP') else size*.35 if align.endswith('MIDDLE') else 0
            for i,s in enumerate(str(t).splitlines()):
                svg.append(f'<text x="{x}" y="{y+baseline+i*size*1.4}" transform="rotate({rotation},{x},{y})" text-anchor="{anchor}" font-family="Microsoft YaHei,Arial,sans-serif" font-size="{size}" font-weight="{700 if bold else 400}" fill="{color}">{html.escape(s)}</text>')
        for a,b in live:
            if a['type']=='LINE':line((b['startX'],1170+b['startY']),(b['endX'],1170+b['endY']))
        for a,b in live:
            if a['type']!='COMPONENT':continue
            props=la[a['id']];ref=props.get('Designator',{}).get('value');sym=symbols.get(ref)
            tx,ty=b['x'],1170+b['y'];angle=b['rotation'];rad=math.radians(angle)
            def xy(x,y):return (tx+x*math.cos(rad)-y*math.sin(rad),ty-x*math.sin(rad)-y*math.cos(rad))
            if not sym:
                if props.get('Name',{}).get('value')=='GND' or props.get('Net Name',{}).get('value')=='GND':
                    line((tx,ty),(tx,ty+6));line((tx-8,ty+6),(tx+8,ty+6));line((tx-5,ty+9),(tx+5,ty+9));line((tx-2,ty+12),(tx+2,ty+12))
                continue
            styles={r[1]:r for r in sym if r[0]=='FONTSTYLE'}
            for r in sym:
                typ=r[0]
                if typ=='RECT':
                    p=[xy(r[2],r[3]),xy(r[4],r[3]),xy(r[4],r[5]),xy(r[2],r[5]),xy(r[2],r[3])]
                    for u,v in zip(p,p[1:]):line(u,v,'#a2131c')
                elif typ=='POLY':
                    p=[xy(r[2][i],r[2][i+1]) for i in range(0,len(r[2]),2)]
                    if r[3]:p.append(p[0])
                    for u,v in zip(p,p[1:]):line(u,v,'#a2131c')
                elif typ=='PIN':
                    radp=math.radians(r[7]);line(xy(r[4],r[5]),xy(r[4]+r[6]*math.cos(radp),r[5]+r[6]*math.sin(radp)),'#a2131c')
                elif typ in ('CIRCLE','ELLIPSE'):
                    x,y=xy(r[2],r[3]);svg.append(f'<circle cx="{x}" cy="{y}" r="{r[4]}" fill="none" stroke="#a2131c" stroke-width=".7"/>')
                elif typ=='ARC':
                    p,q,v=xy(r[2],r[3]),xy(r[4],r[5]),xy(r[6],r[7]);svg.append(f'<path d="M {p[0]} {p[1]} Q {q[0]} {q[1]} {v[0]} {v[1]}" fill="none" stroke="#a2131c"/>')
                elif typ=='ATTR' and r[6] and r[7] is not None:
                    st=styles[r[10]];x,y=xy(r[7],r[8]);al=['LEFT','CENTER','RIGHT'][st[11]]+'_'+['TOP','MIDDLE','BOTTOM'][st[10]]
                    rot=(-(r[9]+angle))%360
                    if rot==180:rot=0
                    if rot==270:rot=90
                    text(x,y,r[4],st[5],al,rot,'#191919')
        for a,b in live:
            if a['type']=='ATTR' and b.get('valueVisible') and b.get('x') is not None:
                par=la[b['parentId']]
                if not par.get('Designator') and b['key']!='NET':continue
                val=b['value']
                match=re.fullmatch(r'=\{(.+)\}',str(val))
                if match:val=par.get(match.group(1),{}).get('value','')
                text(b['x'],1170+b['y'],val,b.get('fontSize') or 8,b.get('align') or 'LEFT_BOTTOM',b.get('rotation') or 0)
            elif a['type']=='TEXT':text(b['x'],1170+b['y'],b['value'],b['fontSize'],b['align'],b['rotation'],b.get('color') or '#213547',b.get('fontWeight'))
        for row in n.input_components('CORE'):
            if row['page']!=key:continue
            rec=n.load_state()['CORE']['components'][row['reference']]
            nets=n.pin_map(row,rec)
            for pin in rec['pins']:
                if nets[pin['pinNumber']]=='NC':
                    x,y=pin['x'],1170-pin['y'];line((x-3,y-3),(x+3,y+3),'#27ad33',1);line((x+3,y-3),(x-3,y+3),'#27ad33',1)
        text(30,1150,'Native-source geometry preview / not an editor-rendered or fabrication drawing',8,color='#667085')
        svg.append('</svg>');data='\n'.join(svg).encode();(OUT/(key+'.svg')).write_bytes(data)
        doc=pymupdf.open(stream=data,filetype='svg');pdf=pymupdf.open(stream=doc.convert_to_pdf(),filetype='pdf')
        pdf[0].get_pixmap(matrix=pymupdf.Matrix(1.5,1.5)).save(OUT/(key+'.png'));pages.append(pdf)
    result=pymupdf.open()
    for pdf in pages:result.insert_pdf(pdf)
    if pages:result.save(OUT/'H735-native-layout-review.pdf')
    print('rendered',len(pages),'pages')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('archive');render(p.parse_args().archive)
