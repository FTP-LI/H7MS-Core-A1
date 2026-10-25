"""Generate and validate v0.9 planning tables against saved ST package/AF data.

Pin/EXTI checks only: this does not validate clocks, DMA, electronics or control.
Run with Python 3: python -X utf8 docs/H7MS/工程规划/validate_resources.py
"""
from pathlib import Path
import csv
import hashlib
import json
import re
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
CORE = HERE.parent


def normal(name):
    return re.match(r"P[A-Z]\d+(?:_C)?", name).group()


def write_csv(name, columns, rows):
    with (HERE / name).open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=columns)
        w.writeheader()
        w.writerows(rows)


def main():
    config = json.loads((HERE / "资源配置.json").read_text(encoding="utf-8"))
    package_path = CORE / "技术依据/compact-mcu-review/STM32H735VGHx.xml"
    af_path = CORE / "技术依据/pin-resource-review/GPIO-STM32H72_gpio_v1_0_Modes.xml"
    package = ET.parse(package_path).getroot()
    pins = {normal(p.attrib["Name"]): p for p in package
            if p.tag.endswith("Pin") and re.match(r"P[A-Z]\d", p.attrib["Name"])}
    afs = {}
    for p in ET.parse(af_path).getroot().iter():
        if p.tag.endswith("GPIO_Pin") and re.match(r"P[A-Z]\d", p.attrib.get("Name", "")):
            for s in p:
                afs[(normal(p.attrib["Name"]), s.attrib["Name"])] = sorted({
                    int(m.group(1)) for v in s.iter()
                    if v.tag.endswith("PossibleValue") and v.text
                    and (m := re.match(r"GPIO_AF(\d+)_", v.text))})

    def check_mapping(mapping):
        exti = []
        nets = [entry[1] for entry in mapping.values()]
        assert len(nets) == len(set(nets)), ("duplicate signal net", nets)
        for pin, entry in mapping.items():
            signal = entry[0]
            assert pin in pins, (pin, signal)
            available = {s.attrib["Name"] for s in pins[pin]}
            if signal != "GPIO":
                assert signal in available, (pin, signal)
                if not signal.startswith(("ADC", "DAC", "RCC", "USB", "DEBUG")):
                    assert afs.get((pin, signal)), (pin, signal, "missing AF")
            if len(entry) == 3:
                assert entry[2] == int(re.search(r"\d+", pin).group())
                exti.append(entry[2])
        assert len(exti) == len(set(exti)), ("EXTI collision", exti)

    fixed = config["core"]
    check_mapping(fixed)
    assert len(pins) == 77 and len(fixed) == 28
    exports = sorted(set(pins) - set(fixed))
    assert len(exports) == 49
    profile_rows, profile_results = [], {}
    for name, groups in config["profiles"].items():
        mapping = dict(fixed)
        for group in groups:
            values = config["groups"][group]
            assert not set(values) & set(mapping), (name, group, "pin collision", set(values) & set(mapping))
            mapping.update(values)
        check_mapping(mapping)
        for pin, entry in mapping.items():
            profile_rows.append(dict(profile=name, pin=pin, ball=pins[pin].attrib["Position"],
                                     signal=entry[0], net=entry[1],
                                     af="/".join(map(str, afs.get((pin, entry[0]), []))),
                                     exti=entry[2] if len(entry) == 3 else "",
                                     placement="core" if pin in fixed else "extension"))
        profile_results[name] = dict(status="pass", used_signal_pads=len(mapping),
                                     unused_extension_pins=sorted(set(pins)-set(mapping)))
    write_csv("应用配置引脚.csv", ["profile","pin","ball","signal","net","af","exti","placement"], profile_rows)

    matrix, inventory = [], []
    for pin, p in pins.items():
        inventory.append(dict(pin=pin, ball=p.attrib["Position"],
                              ownership="core-fixed" if pin in fixed else "extension-flex",
                              core_net=fixed.get(pin,["",""])[1],
                              core_signal=fixed.get(pin,[""])[0]))
        for s in p:
            signal=s.attrib["Name"]
            matrix.append(dict(pin=pin, ball=p.attrib["Position"], signal=signal,
                               af="/".join(map(str,afs.get((pin,signal),[]))),
                               core_reserved=pin in fixed))
    write_csv("77信号资源归属.csv",["pin","ball","ownership","core_net","core_signal"],inventory)
    write_csv("封装全部复用矩阵.csv",["pin","ball","signal","af","core_reserved"],matrix)

    old_balls = list(csv.DictReader((CORE / "数据/STM32H735VGH6_100球连接表.csv").open(encoding="utf-8-sig")))
    balls = []
    for b in old_balls:
        n = normal(b["pad"]) if re.match(r"P[A-Z]\d", b["pad"]) else None
        if n:
            b.update(net=fixed[n][1] if n in fixed else "EXP_"+n,
                     category="core-fixed" if n in fixed else "extension-flex",
                     connection="按v0.9资源配置；外设初始禁能/高阻；电气见规划")
        balls.append(b)
    write_csv("100球连接规划.csv",["ball","pad","net","category","connection"],balls)

    contacts=[]
    for n in range(1,4): contacts += [f"CAN{n}_H",f"CAN{n}_L","GND"]
    for _ in range(6): contacts += ["5V_IN","GND"]
    for _ in range(2): contacts += ["3V3_AUX","GND"]
    for i,pin in enumerate(exports):
        contacts.append("EXP_"+pin)
        if i%2 or i==len(exports)-1: contacts.append("GND")
    contacts.append("GND")
    assert len(contacts)==100 and contacts.count("GND")==37
    write_csv("板间100触点逻辑规划.csv",["connector","contact","net","mcu_pin","ball","status"],[
        dict(connector="J1" if i<50 else "J2",contact=i%50+1,net=net,
             mcu_pin=net[4:] if net.startswith("EXP_") else "",
             ball=pins[net[4:]].attrib["Position"] if net.startswith("EXP_") else "",
             status="v0.9.2 contact equals physical pin; see connector pad table; not v0.8 compatible; PCB/SI unqualified")
        for i,net in enumerate(contacts)])

    iprows=[]
    for ip in package:
        if not ip.tag.endswith("IP"): continue
        inst=ip.attrib.get("InstanceName",ip.attrib["Name"])
        signals=[r for r in matrix if r["signal"].startswith(inst+"_")]
        iprows.append(dict(instance=inst,xml_kind=ip.attrib["Name"],
                           package_signal_options=len(signals),
                           options_on_extension_pins=sum(not r["core_reserved"] for r in signals),
                           interpretation="XML entry; middleware/internal IP included; counts are mux options, not ports/channels"))
    write_csv("芯片XML资源索引.csv",["instance","xml_kind","package_signal_options","options_on_extension_pins","interpretation"],iprows)

    # Adversarial cases ensure the checker rejects common planning errors.
    negative={}
    for name,bad in [("invalid_af",{"PE4":["SPI3_NSS","BAD"]}),
                     ("exti_collision",{"PD10":["GPIO","IRQ",10],"PE10":["GPIO","IRQ2",10]}),
                     ("duplicate_net",{"PA0":["GPIO","SAME"],"PA1":["GPIO","SAME"]})]:
        try: check_mapping(bad)
        except AssertionError: negative[name]="rejected"
        else: raise AssertionError((name,"was not rejected"))
    report=dict(version=config["version"],performed_on=config["date"],status="pass",
                signal_pads=77,core_fixed=28,extension_flex=49,power_system_balls=23,
                connector_positions=100,connector_ground=37,profiles=profile_results,
                negative_checks=negative,
                source_sha256={str(p.relative_to(CORE)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [package_path,af_path,HERE/"资源配置.json"]},
                limits=["not CubeMX or timing/DMA validation","not EDA/ERC/PCB/SI/thermal validation","no firmware or hardware test","XML IP list contains middleware; do not count entries as physical peripherals"])
    (HERE/"validation.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__=="__main__":
    main()
