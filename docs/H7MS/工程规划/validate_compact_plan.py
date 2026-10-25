"""Static design-input checks. No EDA/ERC, routing or hardware result implied."""
from pathlib import Path
from collections import Counter
import csv,json,itertools,hashlib

H=Path(__file__).resolve().parent
def read(n):return list(csv.DictReader((H/n).open(encoding="utf-8-sig")))

def main():
    cfg=json.loads((H/"紧凑板设计参数.json").read_text(encoding="utf8"))
    rows=read("紧凑板原理图连接.csv"); parts=read("紧凑板装配清单.csv"); caps=read("MLCC逐位选型.csv")
    keys=[(r['board'],r['reference'],r['pin']) for r in rows]
    assert len(set(keys))==len(keys)
    lookup={k:r['net'] for k,r in zip(keys,rows)}
    def pin(b,r,p):return lookup[b,r,str(p)]
    contacts=read("板间100触点逻辑规划.csv")
    for b in cfg['board_names']:
        for r in contacts:assert pin(b,r['connector'],r['contact'])==r['net']
        if b=='CORE':continue
        for p in (1,2,4):assert pin(b,'U_MAIN',p)=='FUSED_5V'
        for p in (7,8):assert pin(b,'U_MAIN',p)=='5V_IN'
        assert pin(b,'SW_MAIN',2)==pin(b,'U_MAIN',3)=='MAIN_ON'
        assert pin(b,'F1',1)=='BENCH_5V' and pin(b,'F1',2)=='FUSED_5V'
        assert pin(b,'SW_MAIN',1)=='GND' and pin(b,'SW_MAIN',3)=='FUSED_5V'
        assert pin(b,'J_ESTOP',2)=='EXP_PA8'
    assert ('CORE','J_SWD','7') not in lookup
    extra=read('辅助器件焊盘.csv')
    for r in extra:assert pin(r['board'],r['reference'],r['pad'])==r['net']
    for b in cfg['board_names']:
        buttons={r['reference'] for r in parts if r['board']==b and r['part']=='EVQP7A01P'}
        for ref in buttons:
            assert pin(b,ref,'1L')==pin(b,ref,'1R') and pin(b,ref,'2L')==pin(b,ref,'2R')
            assert pin(b,ref,'1L')!=pin(b,ref,'2L')
    for n,rx in [(1,'PB15'),(2,'PD6'),(3,'PD9'),(4,'PD0')]:
        assert ('BASE_LINK',f'R_DEV{n}_RXSEL','1') not in lookup
        assert pin('BASE_LINK',f'R_DEV{n}_TTL_SEL',2)=='EXP_'+rx
    for i,p in enumerate(('PC6','PC7','PA2','PA3')):
        assert pin('BASE_IO','J_PWM',2*i+1)=='PWM_'+p and pin('BASE_IO','J_PWM',2*i+2)=='GND'
    assert {(r['board'],r['reference']) for r in caps}=={(r['board'],r['reference']) for r in parts if r['reference'].startswith('C_')}
    boxes=read('布局区域与机械坐标.csv')
    for r in boxes:
        for k in ('x_mm','y_mm','width_mm','height_mm'):r[k]=float(r[k])
        for axis,dim in [('x','width'),('y','height')]:
            assert r[axis+'_mm']-r[dim+'_mm']/2>=-1e-6,r
            assert r[axis+'_mm']+r[dim+'_mm']/2<=39.8+1e-6,r
    collisions=[]
    for a,b in itertools.combinations(boxes,2):
        if a['board']!=b['board'] or a['side']!=b['side'] and 'BOTH' not in (a['side'],b['side']):continue
        if abs(a['x_mm']-b['x_mm'])<(a['width_mm']+b['width_mm'])/2-1e-6 and abs(a['y_mm']-b['y_mm'])<(a['height_mm']+b['height_mm'])/2-1e-6:collisions.append((a['board'],a['reference'],b['reference']))
    assert not collisions,collisions
    assert max(cfg['board_mm'])+cfg['outline_tolerance_mm']<=40
    assert cfg['gap_max_mm']<=cfg['mating_max_gap_mm']
    assert cfg['core_bottom_max_height_mm']+cfg['base_top_max_height_mm']+cfg['assembly_clearance_budget_mm']<cfg['gap_min_mm']
    p=cfg['power'];i33=(p['core_3v3_ma']+p['aux_3v3_ma'])/1000
    buck=i33*p['rail_3v3_max_v']/(p['input_5v_min_v']*p['buck_efficiency_budget'])
    heat=p['input_5v_max_v']/p['heater_parallel_resistance_min_ohm']
    dummy=p['input_5v_max_v']/p['dummy_parallel_resistance_min_ohm']
    steady=buck+3*p['can_each_ma']/1000+heat+dummy+p['other_5v_ma']/1000
    fuse=p['fuse_a']*p['fuse_continuous_factor']*p['fuse_temperature_factor_assumption']
    assert steady<fuse and steady<2.0
    values={'100nF':.1,'1uF':1,'10uF':10,'220pF':.00022,'4.7nF':.0047,'10nF':.01}
    perboard={}
    for b in cfg['board_names'][1:]:
        selected=[r for r in caps if r['board'] in ('CORE',b)]
        def maxcap(rails):return sum(values[r['nominal']]*(1.265 if r['dielectric']!='C0G' else 1.05) for r in selected if r['rail'] in rails)
        c5=maxcap(['5V_IN']);c33=maxcap(['3V3_D','3V3_A','3V3_IMU'])
        slew=c5*1e-6*.8*p['input_5v_max_v']/(p['main_rise_acceptance_min_ms']/1000)
        # AUX current limit envelope includes its own capacitor-charging current.
        initial33=(p['smps_input_startup_max_ma']+p['core_non_smps_ma']+p['aux_limit_upper_ma'])/1000+c33*1e-6*p['rail_3v3_max_v']/.003
        initial5=initial33*p['rail_3v3_max_v']/(p['input_5v_min_v']*p['buck_efficiency_budget'])+slew+.015
        assert initial5<1.6
        perboard[b]=dict(direct_5v_cap_max_budget_uf=round(c5,3),upstream_fused_cap_max_budget_uf=round(maxcap(['FUSED_5V']),3),main_3v3_cap_max_budget_uf=round(c33,3),aux_cap_max_budget_uf=round(maxcap(['3V3_AUX']),3),main_slew_current_a=round(slew,4),startup_input_budget_a=round(initial5,4))
    effective={v:round(10*k*.9*.85*.9,4) for v,k in [('5.25V',.50),('3.465V',.70),('1.3V',.95)]}
    assert 3*effective['5.25V']>=10
    assert 4*effective['3.465V']>=11
    report=dict(version='v0.9.3-design',status='pass-static-input-checks',connection_rows=len(rows),components_by_board=dict(Counter(r['board'] for r in parts)),mlcc_reference_rows=len(caps),
        placement_reservations=len(boxes),reservation_overlaps=collisions,mating_contacts_checked=500,auxiliary_land_rows_checked=len(extra),
        power=dict(conservative_all_functions_5v_a=round(steady,4),fuse_continuous_budget_a=round(fuse,4),fuse_temp_factor_is_assumption=True,per_board=perboard,mlcc_single_10u_effective_estimate_uf=effective,
                   startup_pulse_example_i2t_a2s=round(1.6**2*.030,5),fuse_nominal_melting_i2t_a2s=1.029),
        unresolved_qualification=['manufacturer MLCC DC-bias/temperature combined limits and SMPS loop margin','loaded power ramps and hot-plug before soft-start switch','temperature derating and fuse coordination','exact land placement, PTH annuli, 3D plugs and screwdriver access','BGA routing, EDA/ERC and DRC','simultaneous peripheral load across separate compact variants'],
        not_claimed=['completed schematic','fabrication-ready PCB','every component individually placed','manufacturing test or EMC qualification'])
    report['sha256']={n:hashlib.sha256((H/n).read_bytes()).hexdigest() for n in ['紧凑板原理图连接.csv','紧凑板装配清单.csv','MLCC逐位选型.csv','布局区域与机械坐标.csv','紧凑板设计参数.json','辅助器件焊盘.csv']}
    (H/'紧凑板检查报告.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps({k:v for k,v in report.items() if k!='sha256'},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
