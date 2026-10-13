"""Build a DM-inspired functional extension, not a DM pin-compatible clone.

Verify package bonding, ordinary AFs, independent pads and EXTI allocation.
This does not qualify clocks, DMA, electrical performance or PCB routing.
"""
import csv
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT = next(p for p in HERE.parents if (p / 'project.json').exists())
MODELS = ("STM32H723VGH6", "STM32H735VGH6")
ADDITIONS = [
    ("PWM_OUT1", "TIM2_CH1", "PA0", 1, "AF"),
    ("PWM_OUT2", "TIM2_CH3", "PA2", 1, "AF"),
    ("PWM_OUT3", "TIM2_CH4", "PA3", 1, "AF"),
    ("PWM_OUT4", "TIM1_CH1", "PE9", 1, "AF"),
    ("EXP_SPI_SCK", "SPI3_SCK", "PB3", 6, "AF"),
    ("EXP_SPI_MISO", "SPI3_MISO", "PB4", 6, "AF"),
    ("EXP_SPI_MOSI", "SPI3_MOSI", "PB5", 7, "AF"),
    ("EXP_SPI_CS", "GPIO", "PE4", "", "OUTPUT"),
    ("BASE_VOLTAGE_ADC", "ADC3_INP10", "PC0", "", "ANALOG"),
    ("BASE_CURRENT_ADC", "ADC3_INP11", "PC1", "", "ANALOG"),
    ("LOCAL_5V_ADC", "ADC3_INP0", "PC2_C", "", "ANALOG"),
    ("AUX_UART_TX", "UART7_TX", "PE8", 7, "AF"),
    ("AUX_UART_RX_OR_SBUS", "UART7_RX", "PE7", 7, "AF"),
]


def main():
    original = list(csv.DictReader((PROJECT / "docs/H7MS/对比与研究/候选引脚/STM32_compact_BGA_interfaces.csv").open(encoding="utf-8")))
    modes = ET.parse(PROJECT / "docs/H7MS/技术依据/pin-resource-review/GPIO-STM32H72_gpio_v1_0_Modes.xml").getroot()
    afs = {}
    for pin in modes.iter():
        if pin.tag.endswith("GPIO_Pin") and re.match(r"P[A-Z]\d", pin.attrib["Name"]):
            for signal in pin:
                port_name = re.match(r"P[A-Z]\d+(?:_C)?", pin.attrib["Name"]).group()
                afs[(port_name, signal.attrib["Name"])] = {
                    int(m.group(1)) for v in signal.iter()
                    if v.tag.endswith("PossibleValue") and v.text
                    and (m := re.match(r"GPIO_AF(\d+)_", v.text))
                }
    result, summary = [], {}
    for model in MODELS:
        root = ET.parse(PROJECT / "docs/H7MS/技术依据/compact-mcu-review" / (model[:-1] + "x.xml")).getroot()
        pins = {re.match(r"P[A-Z]\d+(?:_C)?", p.attrib["Name"]).group(): p for p in root
                if p.tag.endswith("Pin") and re.match(r"P[A-Z]\d", p.attrib["Name"])}
        rows = [dict(r) for r in original if r["model"] == model]
        assert len(rows) == 62
        for name, signal, port, af, mode in ADDITIONS:
            rows.append(dict(model=model, package="TFBGA100", scope="dm_extension", function=name,
                             peripheral_signal=signal, pin=port, ball=pins[port].attrib["Position"], af=str(af), mode=mode))
        assert len(rows) == 75
        for field in ("function", "pin", "ball"):
            assert len({r[field] for r in rows}) == len(rows), (model, field)
        exti = [re.search(r"\d+", r["pin"]).group() for r in rows if r["mode"] == "EXTI"]
        assert len(set(exti)) == len(exti), model
        for r in rows:
            p = pins[r["pin"]]
            assert r["ball"] == p.attrib["Position"], r
            assert r["peripheral_signal"] in {s.attrib["Name"] for s in p if s.tag.endswith("Signal")}, r
            if r["mode"] == "AF":
                assert int(r["af"]) in afs[(r["pin"], r["peripheral_signal"])], r
        result.extend(rows)
        summary[model] = {"assigned_signal_pads_including_oscillator_and_analog": len(rows),
                          "unassigned_port_names": sorted(set(pins) - {r["pin"] for r in rows}),
                          "static_check": "pass"}
    out = PROJECT / "docs/H7MS/对比与研究/候选引脚/STM32H735_H723_VGH_DM_interfaces.csv"
    with out.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(original[0]))
        writer.writeheader()
        writer.writerows(result)
    report = {"date": "2026-10-11", "scope": "DM functional reference plus previous H723 candidate; not a connector/pin-compatible copy",
              "models": summary,
              "limitations": ["No CubeMX, clock, DMA, electrical, routing or mixed-load qualification",
                              "PWM OUT1/2/3 share TIM2 period; OUT4 uses TIM1",
                              "SBUS substitutes AUX UART RX and requires a validated inversion scheme",
                              "DCMI camera is an alternative profile, not concurrent with this mapping",
                              "USB uses internal FS PHY; AF numbering for PHY not checked",
                              "75 includes oscillator and dedicated analog pads; not 75 ordinary GPIOs"]}
    (HERE / "dm-pin-audit.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
