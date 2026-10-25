"""Build an EasyEDA Pro V2 schematic draft from the reviewed connection table.

V2 record layout is taken from the unmodified editor export in source-backup.
This is schematic entry, not a fabricated/qualified PCB or an ERC substitute.
Missing land patterns stay explicitly unassigned; no guessed IC footprints.
"""
from pathlib import Path
from collections import defaultdict, Counter
import csv
import hashlib
import json
import math
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PLAN = ROOT / 'docs/H7MS/工程规划'
OUT = HERE / 'H735-draft'
BOARDS = ('CORE', 'BASE_CAN')


def read(name):
    return list(csv.DictReader((PLAN / name).open(encoding='utf-8-sig')))


def uid(text):
    return hashlib.sha256(('H7MS-H735-A1:' + text).encode()).hexdigest()[:32]


def dump(records):
    return '\n'.join(json.dumps(r, ensure_ascii=False, separators=(',', ':')) for r in records) + '\n'


def write_csv(path, rows):
    with path.open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


# Explicit package-pin names. Power pins use Unknown in the V2 four-state
# electrical model, with a separately visible functional name. No fake ERC pass.
PIN_NAMES = {
    'TPS62132RGTR': 'SW SW SW PG FB AGND FSW DEF SS/TR AVIN PVIN PVIN EN VOS PGND PGND'.split(),
    'TPS2553DBVR-1': 'IN GND EN FAULT_N ILIM OUT'.split(),
    'TPS3808G33DBVR': 'RESET_N GND MR_N CT SENSE VDD'.split(),
    'TPS22919DCKR': 'IN GND ON NC QOD OUT'.split(),
    'TPS22975DSGR': 'VIN VIN ON VBIAS GND CT VOUT VOUT'.split(),
    'TMP302ADRLR': 'TRIPSET0 GND OUT_N HYSTSET VS TRIPSET1'.split(),
    'SN74LVC1G08DBVR': 'A B GND Y VCC'.split(),
    'SN74LVC1G125DBVR': 'OE_N A GND Y VCC'.split(),
    'SN74LVC1G17DBVR': 'NC A GND Y VCC'.split(),
    'TCAN1042HGVDRBRQ1': 'TXD GND VCC RXD VIO CANL CANH STB'.split(),
    'THVD1450DR': 'R RE_N DE D GND A B VCC'.split(),
    'DMN2056U-7': 'G S D'.split(),
    'BMI088': 'INT2 NC_GND VDD GNDA CSB2 GNDIO PS SCK SDI SDO2 VDDIO INT3 INT4 CSB1 SDO1 INT1'.split(),
    'USBLC6-2SC6': 'IO1 GND IO2 IO2 VBUS IO1'.split(),
    'X1G004171001500': 'ST GND OUT VCC'.split(),
    'PESD2CANFD24V-T,215': 'CANL CANH GND'.split(),
    'CDSOT23-SM712': 'LINE1 LINE2 GND'.split(),
    'JS102011SCQN': 'OFF COMMON ON'.split(),
}

PAGE_NAMES = {
    'C01': 'MCU and Direct SMPS', 'C02': '3V3 buck and AUX limiter',
    'C03': 'Clock reset boot and SWD', 'C04': 'IMU heater and analog sensing',
    'C05': 'Three CAN physical interfaces', 'C06': 'USB FS Device',
    'C07': 'Core stack interface and test points',
    'B01': 'Power entry and stack interface', 'B02': 'CAN connectors and termination',
    'B03': 'DEV4 RS485', 'B06': 'Stop input and fault injection',
}


class Records:
    def __init__(self, kind):
        self.n = 0
        self.rows = [['DOCTYPE', kind, '1.1'], ['HEAD', {'originX': 0, 'originY': 0, 'version': '2', **({'symbolType': 2} if kind == 'SYMBOL' else {})}]]
        for name, size, va, ha in [('left', 8, 2, 0), ('right', 8, 2, 2), ('center', 9, 1, 1), ('title', 18, 2, 0)]:
            self.rows.append(['FONTSTYLE', name, None, None, None, size, 0, 0, 0, 0, va, ha])
        self.rows += [['LINESTYLE', 'body', None, 0, None, 1, 1], ['LINESTYLE', 'wire', '#008000', 0, None, 1, 0]]

    def add(self, kind, *args):
        self.n += 1
        ident = 'e' + str(self.n)
        self.rows.append([kind, ident, *args])
        return ident

    def attr(self, parent, key, value, x=None, y=None, visible=False, style='left'):
        return self.add('ATTR', parent, key, str(value), 0, int(visible), x, y, 0, style, 0)


def make_symbol(mpn, pins, names, kind):
    s = Records('SYMBOL')
    n = len(pins)
    passive = n == 2 and kind in ('R', 'C', 'L', 'F', 'NTC', 'JP')
    width = 240 if n == 100 else 100
    count = math.ceil(n / 2)
    height = max(30, (count - 1) * 15 + 20)
    coords = {}
    if passive:
        height, width = 16, 20
    s.rows.append(['PART', 'main', {'BBOX': [-width / 2, -height / 2, width / 2, height / 2]}])
    if passive and kind == 'C':
        for x in (-3, 3):
            s.add('POLY', [x, -8, x, 8], False, 'body', 0)
        s.add('POLY', [-10, 0, -3, 0], False, 'body', 0)
        s.add('POLY', [3, 0, 10, 0], False, 'body', 0)
    else:
        s.add('RECT', -width / 2, height / 2, width / 2, -height / 2, 0, 0, 0, 'body', 0)
    for i, p in enumerate(pins):
        left = i < count
        x = -width / 2 - 15 if left else width / 2 + 15
        y = ((count - 1) * 15 / 2 - (i if left else i - count) * 15) if not passive else 0
        if passive:
            x = -25 if i == 0 else 25
        electric = 0
        # Defined input/output names only; GPIO and bus terminals stay bidirectional.
        if mpn.startswith('STM32') and names[p].startswith(('P',)):
            electric = 3
        if mpn.startswith('SN74'):
            electric = 2 if names[p] == 'Y' else 1 if names[p] in ('A', 'B', 'OE_N') else 0
        if mpn.startswith('TCAN'):
            electric = {'TXD': 1, 'RXD': 2, 'STB': 1, 'CANL': 3, 'CANH': 3}.get(names[p], 0)
        if mpn.startswith('THVD'):
            electric = {'R': 2, 'RE_N': 1, 'DE': 1, 'D': 1, 'A': 3, 'B': 3}.get(names[p], 0)
        pin_id = s.add('PIN', 1, electric, x, y, 15, 0 if left else 180, None, 0, 0)
        s.attr(pin_id, 'NAME', names[p], x + (19 if left else -19), y - 2, not passive, 'left' if left else 'right')
        s.attr(pin_id, 'NUMBER', p, x + (5 if left else -5), y + 3, not passive, 'left' if left else 'right')
        s.attr(pin_id, 'Pin Type', {0: 'Undefined', 1: 'IN', 2: 'OUT', 3: 'BI'}[electric])
        coords[p] = (x, y, left)
    s.attr('', 'Symbol', mpn)
    s.attr('', 'Designator', kind + '?')
    return s.rows, coords, width, height


def main():
    OUT.mkdir(exist_ok=True)
    rows = [r for r in read('紧凑板原理图连接.csv') if r['board'] in BOARDS]
    groups = defaultdict(list)
    for r in rows:
        groups[r['board'], r['reference']].append(r)
    balls = {r['ball']: r['pad'] for r in read('100球连接规划.csv')}
    caps = {r['mpn']: r['nominal'] for r in read('MLCC逐位选型.csv')}
    z = zipfile.ZipFile(HERE / 'source-backup/H7MS-original-20261017.epro')
    source = json.loads(z.read('project.json'))
    project = {'config': {'title': 'H7MS-H735-A1-Schematic-Draft', 'cbbProject': False}, 'boards': {}, 'devices': {}, 'symbols': {}, 'footprints': {}, 'schematics': {}, 'pcbs': {}, 'panels': {}}
    files = {}
    # Reuse only a neutral drawing frame. No old MCU wiring or symbol is reused.
    frame_device = next(v for v in source['devices'].values() if v['attributes'].get('Symbol') == 'e036605d91bc95da')
    frame_symbol = frame_device['attributes']['Symbol']
    project['devices'][frame_device['uuid']] = frame_device
    project['symbols'][frame_symbol] = source['symbols'][frame_symbol]
    files['SYMBOL/' + frame_symbol + '.esym'] = z.read('SYMBOL/' + frame_symbol + '.esym').decode()
    for name in z.namelist():
        if name.startswith('BLOB/') and not name.endswith('/'):
            files[name] = z.read(name)
    pin_manifest, library = [], []
    symbol_data = {}
    # First milestone: symbols and all pin/net wiring. Land-pattern release is
    # explicitly blocked until the pin-pad library review has been completed.
    for (board, ref), rr in groups.items():
        mpn = rr[0]['part']
        pins = [r['pin'] for r in rr]
        names = {p: p for p in pins}
        if mpn == 'STM32H735VGH6':
            names = balls
        elif mpn in PIN_NAMES:
            names = {p: ('EP_GND' if p == 'EP' else PIN_NAMES[mpn][int(p) - 1]) for p in pins}
        kind = 'NTC' if ref.startswith('NTC') else ref.split('_')[0].rstrip('0123456789')
        identity = mpn + ':' + ','.join(pins) + ':' + kind
        sid, did = uid('symbol:' + identity), uid('device:' + identity)
        if sid not in symbol_data:
            sy, coords, w, h = make_symbol(mpn, pins, names, kind)
            files['SYMBOL/' + sid + '.esym'] = dump(sy)
            symbol_data[sid] = (coords, w, h)
            project['symbols'][sid] = {'uuid': sid, 'title': mpn, 'docType': 2, 'type': 2, 'version': '1'}
            project['devices'][did] = {'uuid': did, 'title': mpn, 'attributes': {'Symbol': sid, 'Designator': kind + '?', 'Manufacturer Part': mpn, 'Footprint Status': 'UNASSIGNED - LIBRARY REVIEW REQUIRED', 'Add into BOM': 'yes', 'Convert to PCB': 'yes'}, 'symbol_type': 2}
        rr[0]['_sid'], rr[0]['_did'] = sid, did
        library.append(dict(board=board, reference=ref, part=mpn, symbol=sid, footprint='', footprint_status='UNASSIGNED', fit=rr[0]['fit']))
        for r in rr:
            pin_manifest.append(dict(board=board, reference=ref, part=mpn, pin=r['pin'], function=names[r['pin']], net=r['net'], page=r['page'], fit=r['fit']))
    page_index = []
    for board in BOARDS:
        sch = uid('schematic:' + board)
        project['boards'][board] = {'schematic': sch}
        project['schematics'][sch] = {'name': board, 'sheets': []}
        pages = sorted({rr[0]['page'] for (b, ref), rr in groups.items() if b == board})
        for page_no, page in enumerate(pages, 1):
            s = Records('SCH')
            frame = s.add('COMPONENT', 'ad8697fa1e53c410', 0, 0, 0, 0, {}, 0)
            s.attr(frame, 'Device', frame_device['uuid'])
            s.attr(frame, 'Symbol', frame_symbol)
            for k, v in {'Size': 'A3', 'Width': '1654', 'Height': '1169', 'Border': '1', 'Blade Width': '10', 'Title Block': '1', 'Title Block Position': '3', 'Version': 'v0.9.4 DRAFT', '@Project Name': project['config']['title'], '@Board Name': board, '@Schematic Name': board, '@Page Name': page, '@Page No': page_no, '@Page Count': len(pages), 'Company': 'H7MS', '@Create Date': '2026-10-17', '@Update Date': '2026-10-17'}.items():
                s.attr(frame, k, v)
            # Free attributes are displayed text; they carry no net semantics.
            s.attr('', 'Page', board + ' / ' + page + ' / ' + PAGE_NAMES[page], 35, 1110, True, 'title')
            s.attr('', 'Status', 'SCHEMATIC DRAFT | Footprints pending | NC pins intentionally unwired | Not for fabrication', 35, 1080, True)
            subset = [(ref, rr) for (b, ref), rr in groups.items() if b == board and rr[0]['page'] == page]
            # Tall devices first; shorter parts fill the remaining columns.
            subset.sort(key=lambda item: -symbol_data[item[1][0]['_sid']][2])
            columns = [1040.0] * 4
            for ref, rr in subset:
                r = rr[0]
                coords, w, h = symbol_data[r['_sid']]
                spans = 2 if len(rr) == 100 else 1
                candidates = [(min(columns[c:c + spans]), c) for c in range(5 - spans)]
                top, col = max(candidates, key=lambda q: (q[0], -q[1]))
                x = 220 + col * 395 + (197.5 if spans == 2 else 0)
                y = top - h / 2 - 30
                bottom = y - h / 2 - 20
                if bottom < 170:
                    raise ValueError(f'Page overflow: {board}/{page}/{ref}: {bottom}')
                columns[col:col + spans] = [bottom] * spans
                comp = s.add('COMPONENT', 'main', x, y, 0, 0, {}, 0)
                for k, v in {'Device': r['_did'], 'Symbol': r['_sid'], 'Manufacturer Part': r['part'], 'Unique ID': uid(board + ':' + ref), 'Add into BOM': 'no' if r['fit'] in ('DNP', 'OPEN') or r['part'].startswith('PCB_') else 'yes', 'Convert to PCB': 'yes', 'Assembly': r['fit'], 'Footprint Status': 'UNASSIGNED', 'Design Notes': r['notes']}.items():
                    s.attr(comp, k, v)
                s.attr(comp, 'Designator', ref, x, y + h / 2 + 23, True, 'center')
                value = caps.get(r['part'], r['part'])
                if r['fit'] != 'YES':
                    value += ' [' + r['fit'] + ']'
                s.attr(comp, 'Name', value, x, y + h / 2 + 10, True, 'center')
                for p in rr:
                    dx, dy, left = coords[p['pin']]
                    xx, yy = x + dx, y + dy
                    if p['net'] == 'NC':
                        s.attr('', 'Note', 'NC', xx + (-8 if left else 8), yy + 4, True, 'right' if left else 'left')
                        continue
                    end = xx + (-35 if left else 35)
                    wire = s.add('WIRE', [[xx, yy, end, yy]], 'wire', 0)
                    s.attr(wire, 'NET', p['net'], end, yy + 2, True, 'right' if left else 'left')
            files[f'SHEET/{sch}/{page_no}.esch'] = dump(s.rows)
            project['schematics'][sch]['sheets'].append({'uuid': uid(board + ':' + page), 'id': page_no, 'name': page + ' ' + PAGE_NAMES[page], 'display_title': page + ' ' + PAGE_NAMES[page]})
            page_index.append({'board': board, 'page': page, 'sheet_file': f'SHEET/{sch}/{page_no}.esch', 'components': len(subset)})
    files['project.json'] = json.dumps(project, ensure_ascii=False, indent=2)
    for name, data in files.items():
        p = OUT / name
        p.parent.mkdir(exist_ok=True, parents=True)
        p.write_bytes(data if isinstance(data, bytes) else data.encode('utf8'))
    archive = HERE / 'H7MS-H735-A1-Schematic-Draft.epro'
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as zz:
        # V2 importer enumerates explicit ZIP directories, not only file paths.
        folders = {'BLOB/', 'FONT/', 'SYMBOL/', 'FOOTPRINT/', 'INSTANCE/',
                   'SHEET/', 'PCB/', 'POUR/', 'PANEL/'}
        for name in files:
            folders.update(str(p).replace('\\', '/') + '/' for p in Path(name).parents if str(p) != '.')
        for folder in sorted(folders):
            zz.writestr(folder, b'')
        for name, data in files.items():
            zz.writestr(name, data)
    write_csv(HERE / 'pin-net-manifest.csv', pin_manifest)
    write_csv(HERE / 'library-status.csv', library)
    report = {'status': 'generated-not-yet-editor-verified', 'boards': BOARDS, 'components': len(groups), 'pins': len(rows), 'pages': page_index, 'unassigned_footprints': len(groups), 'source_sha256': hashlib.sha256((PLAN / '紧凑板原理图连接.csv').read_bytes()).hexdigest(), 'archive_sha256': hashlib.sha256(archive.read_bytes()).hexdigest()}
    (HERE / 'generation-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    print(json.dumps({k: v for k, v in report.items() if k != 'pages'}, ensure_ascii=False))


if __name__ == '__main__':
    main()
