"""Check design arithmetic, DMA allocation and schematic worksheet invariants.

Not a circuit simulator, firmware test, CubeMX validator or EDA ERC.
"""
from pathlib import Path
from fractions import Fraction
from collections import Counter
from datetime import datetime, timezone
import copy
import csv
import hashlib
import json
import re

HERE = Path(__file__).resolve().parent


def clocks(c):
    result = {}
    for name, p in c["plls"].items():
        fin = Fraction(c["hse_hz"], p["M"])
        assert p["FRACN"] == 0 and p["vco"] == "WIDE"
        assert 4000000 <= fin <= 8000000 and p["range"] == 2
        vco = fin * p["N"]
        assert 192000000 <= vco <= (836000000 if name == "PLL1" else 960000000)
        for output in "PQR":
            assert 1 <= p[output] <= 128
            if name == "PLL1" and output == "P":
                assert p[output] == 1 or p[output] % 2 == 0
            value = vco / p[output]
            assert value.denominator == 1
            result[name+"."+output] = int(value)
    actual = {k:result[v] for k,v in c["kernels"].items()}
    d = c["bus_dividers"]
    actual["CPU"] //= d["D1CPRE"]
    actual["HCLK"] = actual["CPU"] // d["HPRE"]
    assert len({d[k] for k in ("D1PPRE","D2PPRE1","D2PPRE2","D3PPRE")}) == 1
    actual["PCLK"] = actual["HCLK"] // d["D2PPRE1"]
    assert d["TIMPRE"] == 0 and d["D2PPRE1"] == 2
    actual["TIMER"] = actual["PCLK"] * 2
    assert actual == c["expected_hz"], (actual,c["expected_hz"])
    assert actual["USB"] == 48000000
    assert c["voltage_scale"] == "VOS0" and not c["cpu_freq_boost"]
    assert 480000000 <= actual["CPU"] <= 520000000
    assert actual["HCLK"] <= 275000000 and actual["PCLK"] <= 137500000
    assert c["flash_latency"] == 3 and c["flash_wrhighfreq"] == 3
    return actual


def dma(c, pins, header):
    requests = {m.group(1):int(m.group(2)) for m in re.finditer(r"#define DMA_REQUEST_(\w+)\s+(\d+)U",header)}
    report = {}
    for name,groups in pins["profiles"].items():
        groups = set(groups) | {"CORE"}
        active = [r for r in c["dma"] if groups.intersection(r["groups"])]
        stream_names = [r["stream"] for r in active]
        req_names = [r["request"] for r in active]
        assert len(stream_names) == len(set(stream_names)), (name,"stream collision")
        assert len(req_names) == len(set(req_names)), (name,"duplicate request")
        for r in active:
            assert re.fullmatch(r"DMA[12]_Stream[0-7]",r["stream"])
            assert r["request"] in requests, r
        report[name] = {"streams":len(active),"free":16-len(active),
                        "requests":{r["stream"]:{"request":r["request"],"dmamux1_id":requests[r["request"]]} for r in active}}
    assert requests["ADC3"] == 115
    return report


def can_ram(c):
    f=c["fdcan"];s=f["per_instance"]
    assert s["payload_bytes"] in (8,12,16,20,24,32,48,64)
    element_words = 2+s["payload_bytes"]//4
    words = s["std_filters"]+2*s["ext_filters"]+2*s["tx_events"]+element_words*sum(s[x] for x in ("rx_fifo0","rx_fifo1","rx_buffers","tx_buffers","tx_fifo"))
    previous_end=0
    for start in f["offsets_words"]:
        assert start >= previous_end and start+words <= f["ram_words"], "CAN RAM overlap/overflow"
        previous_end=start+words
    for key,target in [("nominal_1m",1000000),("data_2m",2000000)]:
        b=f[key];tq=1+b["seg1"]+b["seg2"]
        assert c["expected_hz"]["FDCAN"] == target*b["prescaler"]*tq
        assert b["sjw"] <= b["seg2"]
    return {"words_per_instance":words,"total_used_words":3*words,"last_end_exclusive":previous_end,"capacity_words":f["ram_words"]}


def wiring(rows):
    keys=[(r["board"],r["reference"],r["pin"]) for r in rows]
    assert len(keys)==len(set(keys)), "duplicate component pin"
    lookup={k:r["net"] for k,r in zip(keys,rows)}
    def pin(board,ref,p): return lookup[(board,ref,str(p))]
    for r in csv.DictReader((HERE/"100球连接规划.csv").open(encoding="utf-8-sig")):
        assert pin("CORE","U1",r["ball"])==r["net"]
    assert sum(r["board"]=="CORE" and r["reference"]=="U1" for r in rows)==100
    for r in csv.DictReader((HERE/"板间100触点逻辑规划.csv").open(encoding="utf-8-sig")):
        for board in ("CORE","BASE_DBG"):
            assert pin(board,r["connector"],r["contact"])==r["net"]
    pads=list(csv.DictReader((HERE/"连接器与保护器件焊盘.csv").open(encoding="utf-8-sig")))
    for r in pads:
        if r["type"] != "NPTH":
            assert pin(r["board"],r["reference"],r["pad"])==r["net"], "physical pad/net mismatch"
    def land(board, ref, p):
        return next(r for r in pads if (r["board"],r["reference"],r["pad"])==(board,ref,str(p)))
    for ref in ("J1","J2"):
        assert float(land("CORE",ref,1)["x_mm"])==-15.24
        assert float(land("BASE_DBG",ref,1)["x_mm"])==15.24
        for i in range(1,51):
            a,b=land("CORE",ref,i),land("BASE_DBG",ref,i)
            assert float(a["x_mm"])==-float(b["x_mm"]), "stack X mirror mismatch"
            assert float(a["y_mm"])*float(b["y_mm"])>0, "stack row reversed"
    for p in ("A4_B9","B4_A9"): assert pin("CORE","J_USB",p)=="USB_VBUS"
    assert pin("CORE","J_USB","A5")=="USB_CC1" and pin("CORE","J_USB","B5")=="USB_CC2"
    for n in range(1,5):
        s=f"DEV{n}"
        for line,up,dp in [("A",6,1),("B",7,2)]:
            assert pin("BASE_DBG","U_"+s,up)==s+"_"+line+"_IC"
            assert pin("BASE_DBG","R_"+s+"_"+line+"_SURGE",1)==s+"_"+line
            assert pin("BASE_DBG","R_"+s+"_"+line+"_SURGE",2)==s+"_"+line+"_IC"
            assert pin("BASE_DBG","D_"+s+"_485",dp)==s+"_"+line
        assert pin("BASE_DBG","D_"+s+"_485",3)=="GND"
        assert pin("BASE_DBG","R_"+s+"_TERM",1)==s+"_A"
        assert pin("BASE_DBG","JP_"+s+"_TERM",2)==s+"_B"
        assert pin("BASE_DBG","R_"+s+"_R_PU",1)==s+"_R"
        assert pin("BASE_DBG","R_"+s+"_R_PU",2)=="3V3_AUX"
    for ball in ("D8","G6","E6","F7","E2"): assert pin("CORE","U1",ball)=="VCORE"
    assert pin("CORE","U1","E1")=="3V3_D"
    assert pin("CORE","U1","D2")=="SMPS_SW"
    assert pin("CORE","U_AUX",1)=="3V3_D" and pin("CORE","U_AUX",6)=="3V3_AUX"
    for n in range(1,4):
        for p,net in [(1,f"CAN{n}_TX"),(4,f"CAN{n}_RX"),(8,f"CAN{n}_STB"),(3,"5V_IN"),(5,"3V3_D"),(6,f"CAN{n}_L"),(7,f"CAN{n}_H")]:
            assert pin("CORE",f"U_CAN{n}",p)==net
    assert pin("CORE","U_HEAT_POWER",6)=="HEAT_5V"
    assert pin("CORE","Q_HEAT",3)=="HEAT_DRAIN"
    assert pin("CORE","U_HEAT_GATE",1)=="TEMP_OK" and pin("CORE","U_HEAT_GATE",2)=="NRST"
    assert pin("CORE","U_HEAT_GATE",4)==pin("CORE","U_HEAT_POWER",3)=="HEAT_ALLOW"
    assert pin("CORE","U_TEMP",1)=="GND" and pin("CORE","U_TEMP",6)=="3V3_D"
    for i,p in enumerate(("PC8","PC9","PC10","PC11","PD2","PC12","PB10","PB11")):
        assert pin("BASE_DBG","U_SD_I2C_ISO",2+i)=="EXP_"+p
        assert pin("BASE_DBG","U_SD_I2C_ISO",18-i)=="ISO_"+p
    assert pin("BASE_DBG","U_SD_I2C_ISO",19)=="BUS_OE_N"
    assert pin("BASE_DBG","U_SD_I2C_ISO",20)=="3V3_AUX"
    assert pin("BASE_DBG","U_AUX_MON",1)==pin("BASE_DBG","Q_BUS_ENABLE",1)=="AUX_READY"
    assert pin("BASE_DBG","Q_BUS_ENABLE",3)=="BUS_OE_N"
    for r in rows:
        if r["part"]=="SN74LVC1G125DBVR" and r["pin"]=="1":
            assert r["net"]=="BUS_OE_N"
    for sig in ("SCK","MOSI","MISO","NSS","READY"):
        variants={r["reference"]:r["fit"] for r in rows if r["board"]=="BASE_DBG" and r["reference"] in ("R_LINK_"+sig+"_OUT","R_LINK_"+sig+"_IN")}
        assert set(variants.values())=={"MASTER","SLAVE"}, (sig,"SPI direction paths not exclusive")
    # Detect accidental direct bridges of power domains through fitted zero-ohm links.
    parent={}
    def root(n):
        parent.setdefault(n,n)
        if parent[n]!=n: parent[n]=root(parent[n])
        return parent[n]
    pairs={}
    for r in rows:
        if r["fit"]=="YES" and r["part"]=="0R":
            pairs.setdefault((r["board"],r["reference"]),[]).append(r["net"])
    for nets in pairs.values():
        assert len(nets)==2
        parent[root(nets[0])]=root(nets[1])
    for a,b in [("USB_VBUS","5V_IN"),("3V3_D","VCORE"),("3V3_D","3V3_AUX")]:
        assert root(a)!=root(b), ("unintended power bridge",a,b)
    return {"pin_connections":len(rows),"components_by_board":{b:len({r["reference"] for r in rows if r["board"]==b}) for b in ("CORE","BASE_DBG")},"mcu_balls":100,"stack_contacts_checked":100,"physical_land_rows":len(pads),"limitations":"selected net and pad-coordinate invariants only; no EDA footprint/DRC, full ERC or transient simulation"}


def main():
    c=json.loads((HERE/"时钟DMA配置.json").read_text(encoding="utf8"))
    pins=json.loads((HERE/"资源配置.json").read_text(encoding="utf8"))
    header=(HERE.parent/"技术依据/clock-dma-review/dma.h").read_text(encoding="utf8")
    rows=list(csv.DictReader((HERE/"原理图连接.csv").open(encoding="utf-8-sig")))
    report={"version":"v0.9.3-design","clock_config_version":c["version"],"checked_at":datetime.now(timezone.utc).isoformat(),"status":"pass",
            "clocks_hz":clocks(c),"dma":dma(c,pins,header),"fdcan_ram":can_ram(c),"connections":wiring(rows)}
    negative={}
    for name in ("usb_wrong_frequency","duplicate_dma_stream","fdcan_ram_overlap","wrong_vddldo","both_spi_directions","usb_cc_short","rs485_tvs_after_resistor","stack_wrong_net"):
        bad=copy.deepcopy(c); br=copy.deepcopy(rows)
        try:
            if name=="usb_wrong_frequency": bad["plls"]["PLL3"]["Q"]=7;clocks(bad)
            elif name=="duplicate_dma_stream": bad["dma"][1]["stream"]=bad["dma"][0]["stream"];dma(bad,pins,header)
            elif name=="fdcan_ram_overlap": bad["fdcan"]["offsets_words"][1]=0;can_ram(bad)
            elif name=="wrong_vddldo":
                for r in br:
                    if (r["board"],r["reference"],r["pin"])==("CORE","U1","E6"): r["net"]="3V3_D"
                wiring(br)
            elif name=="both_spi_directions":
                for r in br:
                    if r["reference"]=="R_LINK_SCK_IN": r["fit"]="MASTER"
                wiring(br)
            else:
                key,new={"usb_cc_short":(("CORE","J_USB","B5"),"USB_CC1"),
                         "rs485_tvs_after_resistor":(("BASE_DBG","D_DEV1_485","1"),"DEV1_A_IC"),
                         "stack_wrong_net":(("BASE_DBG","J1","10"),"GND")}[name]
                for r in br:
                    if (r["board"],r["reference"],r["pin"])==key:r["net"]=new
                wiring(br)
        except AssertionError: negative[name]="rejected"
        else: raise AssertionError(name+" not rejected")
    report["negative_checks"]=negative
    report["sources_sha256"]={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [HERE/"时钟DMA配置.json",HERE/"资源配置.json",HERE/"原理图连接.csv",HERE/"连接器与保护器件焊盘.csv",HERE/"板间实体针序.csv",HERE.parent/"技术依据/clock-dma-review/dma.h"]}
    report["not_performed"]=["CubeMX generation","firmware compilation","EDA/ERC/netlist export","PCB/SI/EMC/thermal","hardware timing and fault tests"]
    (HERE/"电气规划校验.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    print(json.dumps({k:v for k,v in report.items() if k not in ("dma","sources_sha256")},ensure_ascii=False,indent=2))
    print("DMA streams:", {k:v["streams"] for k,v in report["dma"].items()})


if __name__=="__main__": main()
