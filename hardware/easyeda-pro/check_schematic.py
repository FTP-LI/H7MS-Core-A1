"""Read the generated EDA records back and check geometric connectivity.

This is a local record/connection check. It does NOT claim editor import/ERC.
"""
from pathlib import Path
from collections import defaultdict
from copy import deepcopy
from html import escape
import csv
import json
import math
import zipfile
import pymupdf

HERE = Path(__file__).resolve().parent
PLAN = HERE.parents[1] / 'docs/H7MS/工程规划'


def records(z, name):
    return [json.loads(x) for x in z.read(name).decode('utf8').splitlines() if x.strip()]


def attrs(rr):
    result = defaultdict(dict)
    for r in rr:
        if r[0] == 'ATTR':
            result[r[2]][r[3]] = r[4]
    return result


def extract(project, files):
    result = {}
    pages = []
    for board, b in project['boards'].items():
        sch = b['schematic']
        for sheet in project['schematics'][sch]['sheets']:
            filename = f'SHEET/{sch}/{sheet["id"]}.esch'
            rr = files[filename]
            aa = attrs(rr)
            wires = [r for r in rr if r[0] == 'WIRE']
            pins = []
            primitives = []
            for r in rr:
                if r[0] != 'COMPONENT' or 'Designator' not in aa[r[1]]:
                    continue
                ref = aa[r[1]]['Designator']
                assert r[5] == 0 and r[6] == 0, 'Unsupported transform: checker must be extended'
                sy = files['SYMBOL/' + aa[r[1]]['Symbol'] + '.esym']
                sa = attrs(sy)
                for p in sy:
                    if p[0] == 'PIN':
                        num = sa[p[1]]['NUMBER']
                        pt = (r[3] + p[4], r[4] + p[5])
                        pins.append((ref, num, pt))
                primitives.append((r, sy))
            # Form connected wire groups by intersection, independently of labels.
            segments = []
            for w in wires:
                for path in w[2]:
                    for i in range(0, len(path) - 2, 2):
                        x1, y1, x2, y2 = path[i:i+4]
                        assert y1 == y2, 'Unexpected non-horizontal wire'
                        segments.append((min(x1,x2), max(x1,x2), y1, aa[w[1]].get('NET'), w[1]))
            for i, a in enumerate(segments):
                for bseg in segments[i+1:]:
                    if a[2] == bseg[2] and max(a[0],bseg[0]) <= min(a[1],bseg[1]):
                        assert a[3] == bseg[3], f'Shorted labels: {board}/{sheet["name"]}/{a[3]}/{bseg[3]}'
            used = set()
            for ref, num, (x,y) in pins:
                labels = {s[3] for s in segments if s[2] == y and s[0] <= x <= s[1]}
                assert len(labels) <= 1, (board, ref, num, labels)
                key = (board, ref, num)
                assert key not in result, f'Duplicate pin: {key}'
                result[key] = next(iter(labels), 'NC')
                used.update(s[4] for s in segments if s[2] == y and s[0] <= x <= s[1])
            assert used == {w[1] for w in wires}, 'Wire without a component endpoint'
            pages.append((board, sheet['name'], rr, primitives))
    return result, pages


def compare(actual, expected):
    assert actual.keys() == expected.keys(), 'Missing or extra component pins'
    errors = [(k, expected[k], actual[k]) for k in actual if expected[k] != actual[k]]
    assert not errors, errors[:12]


def render(pages):
    directory = HERE / 'review'
    directory.mkdir(exist_ok=True)
    pdf = pymupdf.open()
    for board, title, rr, comps in pages:
        draw = ['<svg xmlns="http://www.w3.org/2000/svg" width="1654" height="1169" viewBox="0 0 1654 1169">', '<rect width="1654" height="1169" fill="white"/>', '<rect x="15" y="15" width="1624" height="1139" fill="none" stroke="#9c2938"/>']
        def line(x1,y1,x2,y2,color='#19804a'):
            draw.append(f'<line x1="{x1}" y1="{1169-y1}" x2="{x2}" y2="{1169-y2}" stroke="{color}" stroke-width="1"/>')
        def render_rows(records, tx=0, ty=0):
            styles = {r[1]: r for r in records if r[0] == 'FONTSTYLE'}
            for r in records:
                if r[0] == 'RECT':
                    x1,y1,x2,y2=r[2:6]
                    draw.append(f'<rect x="{tx+min(x1,x2)}" y="{1169-ty-max(y1,y2)}" width="{abs(x2-x1)}" height="{abs(y2-y1)}" fill="none" stroke="#9c2938"/>')
                elif r[0] == 'POLY':
                    p=r[2]
                    for i in range(0,len(p)-2,2):line(tx+p[i],ty+p[i+1],tx+p[i+2],ty+p[i+3],'#9c2938')
                elif r[0] == 'PIN':
                    angle=math.radians(r[7])
                    line(tx+r[4],ty+r[5],tx+r[4]+r[6]*math.cos(angle),ty+r[5]+r[6]*math.sin(angle),'#9c2938')
                elif r[0] == 'WIRE':
                    for p in r[2]:
                        for i in range(0,len(p)-2,2):line(p[i],p[i+1],p[i+2],p[i+3])
                elif r[0] == 'ATTR' and r[6] and r[7] is not None:
                    st=styles[r[10]]
                    anchor={0:'start',1:'middle',2:'end'}[st[11]]
                    txt=escape(str(r[4]))
                    draw.append(f'<text x="{tx+r[7]}" y="{1169-ty-r[8]}" font-size="{st[5]}" font-family="Arial, sans-serif" text-anchor="{anchor}" fill="#16243e">{txt}</text>')
        render_rows(rr)
        for c, sy in comps:render_rows(sy,c[3],c[4])
        draw.append('<text x="35" y="1110" font-family="Arial" font-size="12">Local EDA-record preview. Not an editor-rendered PDF. Footprints / ERC / PCB not released.</text></svg>')
        svg='\n'.join(draw)
        stem=board+'-'+title.split()[0]
        (directory/(stem+'.svg')).write_text(svg,encoding='utf8')
        doc=pymupdf.open(stream=svg.encode(),filetype='svg')
        converted=pymupdf.open(stream=doc.convert_to_pdf(),filetype='pdf')
        pdf.insert_pdf(converted)
        if title.startswith(('C01','C04','B03')):
            converted[0].get_pixmap(matrix=pymupdf.Matrix(1,1)).save(directory/(stem+'.png'))
    pdf.set_metadata({'title':'H7MS H735 CORE + BASE_CAN schematic draft', 'subject':'Local record preview; native editor verification is separate'})
    pdf.save(directory/'H7MS-H735-schematic-preview.pdf')


def main():
    archive=HERE/'H7MS-H735-A1-Schematic-Draft.epro'
    with zipfile.ZipFile(archive) as z:
        project=json.loads(z.read('project.json'))
        files={n:records(z,n) for n in z.namelist() if n.endswith(('.esym','.esch'))}
    source=list(csv.DictReader((PLAN/'紧凑板原理图连接.csv').open(encoding='utf-8-sig')))
    expected={(r['board'],r['reference'],r['pin']):r['net'] for r in source if r['board'] in project['boards']}
    actual,pages=extract(project,files)
    compare(actual,expected)
    negatives=[]
    for mode in ('missing-wire','wrong-net','missing-pin'):
        mutant=deepcopy(files)
        schfile=next(n for n in mutant if n.endswith('.esch'))
        wire=next(r for r in mutant[schfile] if r[0]=='WIRE')
        if mode=='missing-wire':
            mutant[schfile].remove(wire)
        elif mode=='wrong-net':
            next(r for r in mutant[schfile] if r[0]=='ATTR' and r[2]==wire[1] and r[3]=='NET')[4]='INJECTED_ERROR'
        else:
            ca=attrs(mutant[schfile])
            component=next(r for r in mutant[schfile] if r[0]=='COMPONENT' and 'Designator' in ca[r[1]])
            sf='SYMBOL/'+ca[component[1]]['Symbol']+'.esym'
            mutant[sf].remove(next(r for r in mutant[sf] if r[0]=='PIN'))
        try:
            bad,_=extract(project,mutant)
            compare(bad,expected)
        except AssertionError:
            negatives.append(mode)
        else:
            raise AssertionError('Negative check failed: '+mode)
    render(pages)
    report={'status':'PASS-local-record-connectivity', 'components':len({k[:2] for k in actual}), 'pins':len(actual), 'connected_pins':sum(v!='NC' for v in actual.values()), 'nc_pins':sum(v=='NC' for v in actual.values()), 'sheets':len(pages), 'negative_checks_detected':negatives, 'editor_import':'pending', 'editor_netlist':'pending', 'erc':'not-run', 'footprints':'unassigned', 'pcb':'not-created'}
    (HERE/'record-check-report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
    print(json.dumps(report))


if __name__=='__main__':main()
