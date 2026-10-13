"""Validate design documentation against archived ST data; not ERC or hardware tests."""
from pathlib import Path
import csv, hashlib, json, re, xml.etree.ElementTree as ET
from urllib.parse import unquote

HERE = Path(__file__).resolve().parent
PROJECT = next(p for p in HERE.parents if (p / 'project.json').exists())
CORE = PROJECT / 'docs/H7MS'

def read_csv(path):
    with path.open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))

def normal(name):
    m = re.match(r'P[A-Z]\d+(?:_C)?', name)
    return m.group() if m else name

def validate():
    rows = read_csv(CORE / '数据/STM32H735VGH6_75信号.csv')
    balls = read_csv(CORE / '数据/STM32H735VGH6_100球连接表.csv')
    root = ET.parse(CORE / '技术依据/compact-mcu-review/STM32H735VGHx.xml').getroot()
    assert root.attrib['Package'] == 'TFBGA100'
    package = {p.attrib['Position']: p for p in root if p.tag.endswith('Pin')}
    assert len(package) == len(balls) == len({r['ball'] for r in balls}) == 100
    for b in balls:
        assert b['pad'] == package[b['ball']].attrib['Name'], b
    modes = ET.parse(CORE / '技术依据/pin-resource-review/GPIO-STM32H72_gpio_v1_0_Modes.xml').getroot()
    afs = {}
    for pin in modes.iter():
        if pin.tag.endswith('GPIO_Pin') and re.match(r'P[A-Z]\d', pin.attrib['Name']):
            for signal in pin:
                afs[(normal(pin.attrib['Name']), signal.attrib['Name'])] = {
                    int(m.group(1)) for v in signal.iter()
                    if v.tag.endswith('PossibleValue') and v.text
                    and (m := re.match(r'GPIO_AF(\d+)_', v.text))
                }
    assert len(rows) == 75
    for field in ('pin', 'ball', 'function'):
        assert len({r[field] for r in rows}) == 75, field
    for r in rows:
        p = package[r['ball']]
        assert r['pin'] == normal(p.attrib['Name']), r
        assert r['peripheral_signal'] in {s.attrib['Name'] for s in p if s.tag.endswith('Signal')}, r
        if r['mode'] == 'AF':
            assert int(r['af']) in afs[(r['pin'], r['peripheral_signal'])], r
    exti = [int(re.search(r'\d+', r['pin']).group()) for r in rows if r['mode'] == 'EXTI']
    assert len(exti) == len(set(exti))
    signals = {r['function']: r for r in rows}
    for i in range(1,4):
        for d in ('RX', 'TX'):
            assert signals[f'CAN{i}_{d}']['peripheral_signal'] == f'FDCAN{i}_{d}'
    for i in range(1,5):
        for d in ('RX', 'TX', 'DIR'):assert f'UART{i}_{d}' in signals
    for f in ['USB_DM','USB_DP','IMU_SCK','IMU_MISO','IMU_MOSI','IMU_CS','IMU_SECOND_CS','IMU_INT1','IMU_INT2','NOR_CLK','NOR_NCS','NOR_IO0','NOR_IO1','NOR_IO2','NOR_IO3','SWDIO','SWCLK']:
        assert f in signals
    nets = {r['ball']: r['net'] for r in balls}
    for b in ('E2','D8','G6','E6','F7'):assert nets[b] == 'VCORE'
    assert nets['D2'] == 'SMPS_SW' and nets['E1'] == '3V3_D'
    assert nets['A5'] == 'BOOT0' and nets['F2'] == 'NRST' and nets['D3'] == '3V3_D'
    for name, expected in [('VSS','GND'),('VSSSMPS','GND'),('VSSA','GND'),('VDD','3V3_D'),('VDD33USB','3V3_D')]:
        assert all(r['net'] == expected for r in balls if r['pad'] == name)
    categories={k:sum(r['category']==k for r in balls) for k in ('signal','reserved','power-system')}
    assert categories=={'signal':75,'reserved':2,'power-system':23},categories
    con = read_csv(CORE / '数据/板间接口_J1_J2_草案.csv')
    assert len(con)==100 and len({(r['connector'],r['pin']) for r in con})==100
    exported=[r['net'] for r in con if r['mcu_pin']]
    assert len(exported)==len(set(exported))
    for r in con:
        if r['net'] in signals:
            assert (r['mcu_pin'],r['mcu_ball'])==(signals[r['net']]['pin'],signals[r['net']]['ball'])
    required_export = [f'CAN{i}_{d}' for i in range(1,4) for d in ('RX','TX','STB')]
    required_export += [f'UART{i}_{d}' for i in range(1,5) for d in ('RX','TX','DIR')]
    required_export += [f'PWM_OUT{i}' for i in range(1,5)]
    required_export += ['HOST_UART_TX','HOST_UART_RX','AUX_UART_TX','AUX_UART_RX_OR_SBUS','EXP_SPI_CS','EXP_SPI_SCK','EXP_SPI_MISO','EXP_SPI_MOSI','I2C_SCL','I2C_SDA','BASE_VOLTAGE_ADC','BASE_CURRENT_ADC','PWR_EN','PWR_GOOD','ESTOP_N','BASE_FAULT_N']
    assert set(required_export) <= set(exported)
    # Confirm every pre-existing original PDF/DXF/XML that remained live is unchanged.
    migration=json.loads((PROJECT/'archives/2026-10-11_before-docs-v0.8.0/migration-plan.json').read_text(encoding='utf-8'))
    reorg=json.loads((PROJECT/'archives/2026-10-12_docs-reorganization/migration-plan.json').read_text(encoding='utf-8'))
    originals=0
    for old,v in migration['entries'].items():
        if v['destination'] and Path(old).suffix.lower() in ('.pdf','.dxf','.xml'):
            current=reorg['entries'].get(v['destination'],{}).get('destination',v['destination'])
            f=PROJECT/current
            assert hashlib.sha256(f.read_bytes()).hexdigest()==v['sha256'],str(f)
            originals+=1
    unchanged=0
    for old, record in reorg['entries'].items():
        f=PROJECT/record['destination']
        assert f.is_file(), str(f)
        if f.suffix.lower() not in ('.md','.json','.py'):
            assert hashlib.sha256(f.read_bytes()).hexdigest()==record['sha256'],str(f)
            unchanged+=1
    expected_dirs={'DJI A','DJI C','达妙 DM-MC02','D_MAIN_2558','H7MS','OTA'}
    assert {p.name for p in (PROJECT/'docs').iterdir() if p.is_dir()}==expected_dirs
    assert {p.name for p in (PROJECT/'docs').iterdir() if p.is_file()}=={'README.md'}
    # Capacity arithmetic only; this is not an executable bootloader flash map.
    ota_text=(PROJECT/'docs/OTA/分区与实施验证计划.md').read_text(encoding='utf-8')
    ranges=[(int(a,16),int(b,16)) for a,b in re.findall(r'\| `0x([0-9A-Fa-f]+)` \| `0x([0-9A-Fa-f]+)` \|',ota_text)]
    assert len(ranges)==9, ranges
    internal,external=ranges[:2],ranges[2:]
    for area,start,end,alignment in [(internal,0x08000000,0x08100000,0x20000),(external,0,0x1000000,0x1000)]:
        assert area[0][0]==start and area[-1][1]==end
        assert all(a<b and a%alignment==0 and b%alignment==0 for a,b in area)
        assert all(a[1]==b[0] for a,b in zip(area,area[1:]))
    broken=[]
    md_files=[PROJECT/'README.md', PROJECT/'archives/README.md', PROJECT/'archives/2026-10-12_docs-reorganization/README.md']+list((PROJECT/'docs').rglob('*.md'))
    for f in md_files:
        s=f.read_text(encoding='utf-8-sig')
        for m in re.finditer(r'!?\[[^\]\n]*\]\(([^\n]+?)\)',s):
            link=m[1].strip('<>')
            if re.match(r'^(https?://|mailto:|app:|#)',link):continue
            target=unquote(link.split('#')[0])
            if not (f.parent/target).exists():broken.append({'file':str(f.relative_to(PROJECT)),'target':link})
    for board in ['H7MS','DJI A','DJI C','达妙 DM-MC02','D_MAIN_2558']:
        for name in ['总结分析报告.md','硬件架构.md','原理图/README.md']:
            assert (PROJECT/'docs'/board/name).is_file()
    report=dict(status='pass' if not broken else 'needs-link-repair',checked_on='2026-10-12',model='STM32H735VGH6',package='TFBGA100',assigned_signals=75,balls=100,ball_categories=categories,exti_lines=exti,native_can_controllers=3,device_uarts=4,connector_positions=100,unchanged_original_pdf_dxf_xml=originals,reorganization_unchanged_noneditable_files=unchanged,docs_top_level_directories=sorted(expected_dirs),ota_partition_capacity_arithmetic='pass; not a qualified flash map',checked_markdown_files=len(md_files),broken_local_links=broken,limits=['not CubeMX','not EDA/ERC','not clock or DMA qualification','not PCB/SI/thermal qualification','not hardware or recovery test','not OTA implementation or power-failure test'])
    (HERE/'validation-result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))
    return not broken

if __name__=='__main__':
    raise SystemExit(0 if validate() else 1)
