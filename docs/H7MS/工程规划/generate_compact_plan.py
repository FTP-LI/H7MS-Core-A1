"""Physical board variants and placement reservations; NOT a routed PCB.

BASE_DBG remains the logical circuit superset. Compact boards are explicit
subsets, not permission to connect multiple core boards to one parallel bus.
"""
from pathlib import Path
from collections import defaultdict
import csv
import json
import re
import textwrap
from html import escape

HERE = Path(__file__).resolve().parent
BOARDS = ("CORE", "BASE_CAN", "BASE_485", "BASE_LINK", "BASE_IO")


def read(name):
    return list(csv.DictReader((HERE/name).open(encoding="utf-8-sig")))


def write(name, rows, fields=None):
    with (HERE/name).open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields or list(rows[0]));w.writeheader();w.writerows(rows)


def selected(r, board):
    ref,p=r["reference"],r["page"]
    if r["board"]=="CORE": return board=="CORE"
    if board=="CORE": return False
    if p=="B01": return board=="BASE_IO" or ref not in ("U_SD_I2C_ISO","C_SD_I2C_ISO")
    if p=="B06":
        return board=="BASE_IO" or ref in ("J_ESTOP","R_ESTOP_PD","R_ENABLE_PD","R_STATUS_PB7_PU","R_STATUS_PB7_PD","SW_FAULT")
    if p=="B02": return board=="BASE_CAN"
    if p=="B03":
        dev=re.search(r"DEV([1-4])",ref)
        if dev:
            if board=="BASE_LINK":
                return "TTL" in ref or "TXBUF" in ref
            if "TTL" in ref: return False
            return board=="BASE_485" or board=="BASE_CAN" and dev[1]=="4"
        return board in ("BASE_485","BASE_LINK") # HOST and RC
    if p=="B04":
        if "LINK" in ref or ref in ("R_NSS_PU","R_READY_PD"): return board=="BASE_LINK"
        return board=="BASE_IO" # I2C and 49 probe pads
    if p=="B05": return board=="BASE_IO"
    return False


def main():
    source=read("原理图连接.csv")
    rows=[]
    for board in BOARDS:
        for src in source:
            if not selected(src,board): continue
            r=src.copy();r["board"]=board
            if board!="CORE" and r["reference"]=="J_PWR":
                r["part"]="B2B-PH-SM4-TB(LF)(SN)"
                r["notes"]="compact A1: 2A with AWG24; PHR-2 + SPH-002T-P0.5S; pin1=5V pin2=GND; SMT anchors mechanical only; differs from logical BASE_DBG VH"
            if board=="BASE_LINK" and r["reference"].endswith("_TTL_SEL"): r["fit"]="YES"
            rows.append(r)
    write("紧凑板原理图连接.csv",rows)
    parts={}
    for r in rows: parts.setdefault((r["board"],r["reference"]),r)
    write("紧凑板装配清单.csv",[{k:r[k] for k in ("board","reference","part","fit","page","notes")} for r in parts.values()])
    capspec={
        "C1005X7R1H104K050BB":("100nF",50,"X7R","0402",10),
        "C1608X7R1C105K080AC":("1uF",16,"X7R","0603",10),
        "GRM21BR61E106KA73L":("10uF",25,"X5R","0805",10),
        "C1608C0G1H221J080AA":("220pF",50,"C0G","0603",5),
        "C1608C0G1H472J080AA":("4.7nF",50,"C0G","0603",5),
        "C1608C0G1H103J080AA":("10nF",50,"C0G","0603",5),
    }
    write("MLCC逐位选型.csv",[dict(board=r["board"],reference=r["reference"],mpn=r["part"],nominal=capspec[r["part"]][0],rated_v=capspec[r["part"]][1],dielectric=capspec[r["part"]][2],package=capspec[r["part"]][3],tolerance_pct=capspec[r["part"]][4],rail=r["net"],fit=r["fit"]) for r in parts.values() if r["reference"].startswith("C_")])

    # Mechanical envelopes are component/group reservations, not land patterns.
    boxes=[]
    def box(b,side,ref,x,y,w,h,kind="component",note=""):
        boxes.append(dict(board=b,side=side,reference=ref,x_mm=x,y_mm=y,width_mm=w,height_mm=h,kind=kind,notes=note))
    holes=[(2.5,11),(37.3,11),(2.5,28.8),(37.3,28.0)]
    for b in BOARDS:
        for j,y in [(1,4.8),(2,35.0)]:
            box(b,"BOTTOM" if b=="CORE" else "TOP",f"J{j}",19.9,y,36.8,6.35,"stack","center is mating-array datum; exact lands from v0.9.2; peg holes pass through PCB")
        for i,(x,y) in enumerate(holes,1):box(b,"BOTH",f"H{i}",x,y,4.2,4.2,"hole","NPTH dia2.2; dia4.2 screw/washer/copper keepout")
    for ref,x,y,w,h,note in [
        ("U1 + L1 + local decoupling",23,19,14,14,"U1 body 8x8 at 23,19; local SMPS loop placed first; no claim of completed BGA escape"),
        ("IMU + heater + NTC + TMP302",9,20,11,11,"thermal region; BMI088 near 9,20; four 1206 resistors around sensor; separate from buck"),
        ("Y1 + R_HSE + C_HSE",22,9,5,3,"short HSE to MCU, no LSE footprint"),
        ("RESET supervisor + pulls",10,9,8,4,"low-noise control circuitry"),
        ("J_USB",35.8,19.9,8.0,10,"mouth east at X39.8; signal-pad datum X32.445 Y19.9; rear pad edge X31.87; local +Y maps to global +X"),
        ("J_SWD",30,5.5,7.2,7.2,"top access; nine populated contacts; leave mating-cable clearance above"),
        ("SW_RESET",5.5,2,5.4,3.8,"actuator north"),("SW_BOOT",12.5,2,5.4,3.8,"actuator north"),("SW_AUX_RESET",19.5,2,5.4,3.8,"actuator north"),
        ("CAN1 cell",8,33,7,7,"U_CAN1 + ESD + RC"),("CAN2 cell",17,33,7,7,"U_CAN2 + ESD + RC"),("CAN3 cell",26,33,7,7,"U_CAN3 + ESD + RC"),
        ("USB ESD + VBUS buffer",34.5,29,7,4,"close to J_USB; keep differential pair short")]:box("CORE","TOP",ref,x,y,w,h,note=note)
    box("CORE","BOTTOM","BUCK + L2 + Cin/Cout",24,12.5,14,8,"group","112mm2 reservation includes L2, U2, seven0805 capacitors and SS/HF/PG; max2mm; do not place below IMU")
    box("CORE","BOTTOM","AUX + heater logic + analog RC",25,23,12,12,"group","max1.5mm component height; passives may move within reservation during escape")
    box("CORE","BOTTOM","13 core probe pads",11,29.9,10,3,"group","bare ENIG pads; access when separated or via fixture")

    # Outward-facing underside: all tall plugs and controls are outside the gap.
    # SMT PH entry can sit opposite the SFM without through-hole tails.
    for b in BOARDS[1:]:
        box(b,"BOTTOM","J_PWR",8.5,4.5,9,8,"component","SMT PH; not the previous VH PTH; pin1 marked; cable exits downward")
        box(b,"BOTTOM","F1",20,4.5,8,4,"component","replaceable by soldering, 451 2.5A")
        box(b,"BOTTOM","SW_MAIN",29.8,35.5,9.5,6.8,"component","SC vertical actuator, underside access; 3 SMT terminals; no locating-hole variant")
        box(b,"BOTTOM","SW_FAULT",30,2.0,5.4,3.8,"component","side push north, no through holes")
        # Place circuit cells in central strip; PTH solder tails create local exclusions.
        box(b,"TOP","Power + AUX monitor cell",9,19.8,8,20,"group","U_MAIN, CT, input/output capacitors, U_AUX_MON; allow underside header PTH keepouts within cell")
        if b=="BASE_CAN":
            box(b,"TOP","DEV4 RS485 cell",22,19.8,13,20,"group","SOIC8 + TX/DIR buffers + TVS + pulse resistors; connector TVS first")
        elif b=="BASE_485":
            box(b,"TOP","DEV1/2 RS485 cells",20.5,19.8,11,20,"group","two SOIC8, buffers, TVS, RC; no components on PTH annuli")
            box(b,"TOP","DEV3/4 + HOST/RC cells",31.2,19.8,9.5,20,"group","two SOIC8 plus interface buffers; detailed packing required before PCB release")
        elif b=="BASE_LINK":
            box(b,"TOP","SPI + TTL buffer cells",25,19.8,20,20,"group","all SN74LVC1G125; master/slave resistors exclusive; no RS485 receiver connected")
        else:
            box(b,"TOP","SD/I2C isolation + ADC + load gate",25,19.8,20,20,"group","TSSOP20, gates and local RC; dummy resistors kept away from core IMU")

    # Bodies include conservative courtyard reservation. XH through-hole tails must
    # remain outside the two stack-connector strips on the opposite face.
    def connector(b,ref,x,y,w=10.5,h=7.0):box(b,"BOTTOM",ref,x,y,w,h,note="XH outward-facing; pin-row and body origin reconciled in EDA; keep PTH tails out of SFM courtyard")
    for ref,x,y in [("J_CAN1",10,12),("J_CAN2",24,12),("J_CAN3",10,21),("J_DEV4_485",24,21)]:connector("BASE_CAN",ref,x,y)
    connector("BASE_CAN","J_ESTOP",10,30,8)
    for ref,x,y in [("J_DEV1_485",10,12),("J_DEV2_485",24,12),("J_DEV3_485",10,21),("J_DEV4_485",24,21)]:connector("BASE_485",ref,x,y)
    connector("BASE_485","J_HOST",11,30,13)
    connector("BASE_485","J_RC",25,30,13)
    connector("BASE_485","J_ESTOP",35,20,7.8)
    for ref,x,y in [("J_DEV1_TTL",11,12),("J_DEV2_TTL",25,12),("J_DEV3_TTL",11,21),("J_DEV4_TTL",25,21),("J_HOST",11,30),("J_RC",25,30)]:connector("BASE_LINK",ref,x,y,13)
    connector("BASE_LINK","J_ESTOP",35,20,7.8)
    box("BASE_LINK","BOTTOM","J_LINK",15,36.5,16.2,5.5,"component","PTH SPI header: conflict with SFM strip; relocation required, see layout report")
    # IO: SD is SMT and can lie opposite stack connector; normal plug bodies below.
    box("BASE_IO","BOTTOM","J_SD",10.5,18,16,16,"component","microSD insertion west; exact DM3AT shell and card travel checked in 3D")
    for ref,x,y in [("J_PWM_PC6",23,12),("J_PWM_PC7",33,12),("J_PWM_PA2",23,21),("J_PWM_PA3",33,21),("J_ESTOP",23,30),("J_LOAD",33,30)]:connector("BASE_IO",ref,x,y,8)
    connector("BASE_IO","J_I2C",11,30,13)
    box("BASE_IO","BOTTOM","RV_PC0 + RV_PC1",31,5,10,4.5,"group","two TC33X-2-103E, adjustment from underside")
    box("BASE_IO","TOP","49 flexible probe pads",19.9,39,31,1.2,"group","single row impossible at this pitch; see derived probe-grid placement")

    # Resolve two layout pressure points using existing smaller, SMT alternatives.
    # SPI connector changes to 1.27mm FTSH to avoid TH tails under SFM.
    # Consolidate four PWM outlets into one compact 2x4 SMT header on BASE_IO.
    pwm_pins=("PC6","PC7","PA2","PA3")
    pwm_rows=[r for r in rows if r["board"]=="BASE_IO" and r["reference"].startswith("J_PWM_")]
    rows=[r for r in rows if r not in pwm_rows]
    for i,pin in enumerate(pwm_pins):
        for p,net in [(2*i+1,"PWM_"+pin),(2*i+2,"GND")]:
            rows.append(dict(board="BASE_IO",page="B05",reference="J_PWM",part="FTSH-104-01-L-DV",pin=str(p),net=net,fit="YES",notes="compact 1.27mm 2x4 SMT PWM bank; odd pins PC6/PC7/PA2/PA3, even GND; no servo power"))
    for r in rows:
        if r["board"]=="BASE_LINK" and r["reference"]=="J_LINK":
            r["part"]="FTSH-106-01-L-DV"
            r["notes"]="compact SPI: 2x6 1.27mm SMT; unchanged electrical pin sequence; not compatible with previous 2.54mm cable"
    for r in boxes:
        if r["reference"]=="J_LINK":r.update(x_mm=15,y_mm=36.0,width_mm=8.4,height_mm=7.0,notes="FTSH-106-01-L-DV 1.27mm SMT; no TH tails; 12 pins odd signal/even ground; mating cable exits down")
        if r["reference"]=="49 flexible probe pads":r.update(reference="24 south probe pads",x_mm=19.9,y_mm=39.0,width_mm=31,height_mm=1.2,notes="49 pads split: 25 north at y0.8, 24 south at y39.0, pitch1.27, dia0.8; TOP fixture access before stacking")
        if r["board"]=="CORE" and r["reference"]=="CAN1 cell":r["x_mm"]=8.6
        if r["board"]=="CORE" and r["reference"]=="USB ESD + VBUS buffer":r.update(side="BOTTOM",x_mm=35,y_mm=20,width_mm=7,height_mm=8)
        if r["reference"]=="SW_MAIN":r["y_mm"]=36.0
        if r["reference"]=="J_LINK":r["y_mm"]=36.1
        if r["reference"] in ("J_HOST","J_I2C"):r["x_mm"]=11.2
        if r["reference"] in ("J_HOST","J_RC"):r["y_mm"]=29
        if r["board"]=="BASE_LINK" and r["reference"].startswith("J_DEV"):r["x_mm"]+=0.2
        if r["board"]=="BASE_LINK" and r["reference"]=="J_ESTOP":r["x_mm"]=35.7
        if r["board"]=="BASE_485" and r["reference"]=="DEV3/4 + HOST/RC cells":r.update(x_mm=31,width_mm=8)
        if r["board"]=="BASE_485" and r["reference"]=="Power + AUX monitor cell":r['notes']+="; HOST/RC receive buffers may share this cell; dense RS485 pull resistors may use underside gaps"
        if r["board"]=="BASE_IO":
            if r["reference"]=="J_SD":r.update(x_mm=12.8,y_mm=19)
            if r["reference"]=="J_I2C":r.update(x_mm=28,y_mm=21)
            if r["reference"]=="J_ESTOP":r.update(x_mm=26,y_mm=29)
            if r["reference"]=="J_LOAD":r.update(x_mm=26,y_mm=12)
            if r["reference"]=="SW_FAULT":r.update(x_mm=21,y_mm=36)
            if r["reference"]=="RV_PC0 + RV_PC1":r.update(x_mm=11,y_mm=35.5)
    boxes=[r for r in boxes if not (r["board"]=="BASE_IO" and r["reference"].startswith("J_PWM_"))]
    box("BASE_IO","BOTTOM","J_PWM",30,4.5,6.5,7.0,"component","FTSH-104-01-L-DV 2x4 SMT; four PWM plus four GND; no motor power")
    box("BASE_IO","TOP","25 north probe pads",19.9,0.8,31.3,1.2,"group","25 bare pads, 1.27 pitch; 24 remaining pads at south edge")
    write("紧凑板原理图连接.csv",rows)
    parts={}
    for r in rows:parts.setdefault((r["board"],r["reference"]),r)
    write("紧凑板装配清单.csv",[{k:r[k] for k in ("board","reference","part","fit","page","notes")} for r in parts.values()])
    groups=defaultdict(list)
    for r in parts.values():
        if r["part"].startswith("PCB_") or re.fullmatch(r"[0-9.]+[Rk](?: .*|)",r["part"]):continue
        groups[(r['board'],r['part'],r['fit'])].append(r['reference'])
    write("关键器件定版.csv",[dict(board=b,part=p,quantity=len(refs),references=" / ".join(sorted(refs)),fit=fit,decision="v0.9.3 schematic-selected",qualification="design input only; library, electrical and assembly qualification required") for (b,p,fit),refs in sorted(groups.items())])
    extra=[]
    def land(r,x,y,w,h,source):
        extra.append(dict(board=r['board'],reference=r['reference'],mpn=r['part'],pad=r['pin'],net=r['net'],x_mm=round(x,5),y_mm=round(y,5),width_mm=round(w,5),height_mm=round(h,5),type='SMD',source=source,view='LOCAL component-side; X right Y down; not global PCB coordinates'))
    for r in rows:
        p=r['part'];pin=r['pin']
        if p=='EVQP7A01P':
            land(r,-1.8 if pin.endswith('L') else 1.8,-.725 if pin.startswith('1') else .725,1.4,1.05,'Panasonic EVQP7 page2 No1; aliases1L/1R internally joined,2L/2R joined')
        elif p.startswith('FTSH-10'):
            n=int(p.split('-')[1])-100;i=int(pin)
            land(r,((i-1)//2-(n-1)/2)*1.27,2.032 if i%2 else -2.032,.7366,2.794,'Samtec FTSH DV footprint RevH Fig1; no alignment hole without -A; omit absent pin7 on SWD')
        elif p=='045102.5MRL':land(r,-2.4525 if pin=='1' else 2.4525,0,1.955,3.15,'Littelfuse451 page4: outer6.86,inner2.95,width3.15; symmetric electrical part')
        elif p=='PCB_SJ2_OPEN':land(r,-.525 if pin=='1' else .525,0,.8,1.0,'project PCB primitive; no paste; copper gap.25; default unbridged')
        elif p=='PCB_TP_0.8':land(r,0,0,.8,.8,'project PCB primitive; circular copper dia.8; mask dia1.0; no paste/drill')
    write('辅助器件焊盘.csv',extra)
    write("布局区域与机械坐标.csv",boxes)
    machine=dict(version="v0.9.3-design",date="2026-10-16",board_mm=[39.8,39.8],outline_tolerance_mm=0.1,corner_radius_mm=1.0,
                 board_thickness_mm=1.6,core_layers=6,base_layers=4,board_names=list(BOARDS),
                 connector_centers_mm=[[19.9,4.8],[19.9,35.0]],mount_holes_mm=holes,
                 hole_diameter_mm=2.2,hole_keepout_diameter_mm=4.2,
                 spacer_project_pn="H7MS-MECH-M2-6P35-A1",spacer_length_mm=6.35,spacer_tolerance_mm=0.03,
                 gap_min_mm=6.32,gap_max_mm=6.38,mating_max_gap_mm=6.48,
                 core_bottom_max_height_mm=2.3,base_top_max_height_mm=1.8,assembly_clearance_budget_mm=0.5,
                 power=dict(core_3v3_ma=450,aux_3v3_ma=500,rail_3v3_max_v=3.465,input_5v_min_v=4.75,input_5v_max_v=5.25,buck_efficiency_budget=0.80,can_each_ma=80,other_5v_ma=15,
                     heater_parallel_resistance_min_ohm=49.5,dummy_parallel_resistance_min_ohm=49.5,
                     fuse_a=2.5,fuse_continuous_factor=0.75,fuse_temperature_factor_assumption=0.90,
                     ct_nf=10,main_rise_typ_ms=16.98,main_rise_acceptance_min_ms=5.0,buck_ss_nf=10,buck_ss_typ_ms=5.0,
                     smps_input_startup_max_ma=420,aux_limit_upper_ma=644,core_non_smps_ma=50),
                 qualification="design inputs only; no PCB/DRC/3D collision/thermal qualification")
    (HERE/"紧凑板设计参数.json").write_text(json.dumps(machine,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    # 2-column top/bottom schematic illustration, same top-view XY coordinates.
    svg=['<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="2760" viewBox="0 0 1200 2760">',
         '<rect width="1200" height="2760" fill="#f3f6fa"/>',
         '<style>text{font-family:Arial,Microsoft YaHei,sans-serif;fill:#17304a} .tiny{font-size:10px}.label{font-size:13px}</style>',
         '<text x="40" y="35" font-size="24">H7MS A1 — 39.8 × 39.8 mm placement reservations</text>',
         '<text x="40" y="60" font-size="14">TOP / BOTTOM shown in the SAME assembly top-view coordinates. Regions are not routed footprints.</text>']
    colors={"stack":"#bdd7f5","component":"#d3eadf","group":"#f5e8ba","hole":"#ffffff"}
    for bi,b in enumerate(BOARDS):
        yy=100+bi*525
        svg.append(f'<text x="40" y="{yy}" font-size="21">{b}</text>')
        for si,side in enumerate(("TOP","BOTTOM")):
            x0=65+si*580;y0=yy+40;s=10
            svg.append(f'<text x="{x0}" y="{y0-12}" font-size="16">{side}</text><rect x="{x0}" y="{y0}" width="398" height="398" rx="10" fill="white" stroke="#17304a" stroke-width="2"/>')
            for r in boxes:
                if r["board"]!=b or r["side"] not in (side,"BOTH"):continue
                x,y,w,h=[r[k]*s for k in ("x_mm","y_mm","width_mm","height_mm")]
                if r["kind"]=="hole":
                    svg.append(f'<circle cx="{x0+x}" cy="{y0+y}" r="21" fill="none" stroke="#d26363" stroke-dasharray="3 2"/><circle cx="{x0+x}" cy="{y0+y}" r="11" fill="#f3f6fa" stroke="#7f8da0"/>')
                else:
                    svg.append(f'<rect x="{x0+x-w/2}" y="{y0+y-h/2}" width="{w}" height="{h}" rx="3" fill="{colors[r["kind"]]}" stroke="#6d849a"/><title>{escape(r["notes"])}</title>')
                    label=r["reference"]
                    words=[line for segment in label.split(" + ") for line in textwrap.wrap(segment,width=max(6,int(w/5.5)))]
                    for j,line in enumerate(words):svg.append(f'<text x="{x0+x}" y="{y0+y+4+(j-(len(words)-1)/2)*12}" text-anchor="middle" class="tiny">{escape(line)}</text>')
            svg.append(f'<text x="{x0}" y="{y0+422}" class="label">X → / Y ↓ · mm · dashed red: mounting keepout</text>')
    svg.append('</svg>');(HERE/"40mm板组布局.svg").write_text("\n".join(svg),encoding="utf8")
    print({b:len({r['reference'] for r in rows if r['board']==b}) for b in BOARDS})


if __name__=="__main__": main()
