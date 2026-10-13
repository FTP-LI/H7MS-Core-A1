"""Check research CSVs against ST package data and the archived GPIO AF data.

This is not a CubeMX, power, routing, firmware or hardware qualification.
USB dedicated PHY signals are checked for bonding only, not GPIO AF numbering.
"""
import csv
import re
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT = next(p for p in HERE.parents if (p / 'project.json').exists())
MODELS = {
    "STM32H723VGH6": ("STM32H723VGHx", "TFBGA100"),
    "STM32H723ZGI6": ("STM32H723ZGIx", "UFBGA144"),
    "STM32H725AGI6": ("STM32H725AGIx", "UFBGA169"),
    "STM32H735AGI6": ("STM32H735AGIx", "UFBGA169"),
    "STM32H735VGH6": ("STM32H735VGHx", "TFBGA100"),
    "STM32H735IGK6": ("STM32H735IGKx", "UFBGA176"),
}


def check():
    modes = ET.parse(PROJECT / "docs/H7MS/技术依据/pin-resource-review/GPIO-STM32H72_gpio_v1_0_Modes.xml").getroot()
    afs = {}
    for pin in modes.iter():
        if not pin.tag.endswith("GPIO_Pin"):
            continue
        for signal in pin:
            values = [v.text for v in signal.iter() if v.tag.endswith("PossibleValue") and v.text]
            afs[(pin.attrib["Name"], signal.attrib["Name"])] = {
                int(m.group(1)) for v in values if (m := re.match(r"GPIO_AF(\d+)_", v))
            }
    path = PROJECT / "docs/H7MS/对比与研究/候选引脚/STM32_compact_BGA_interfaces.csv"
    rows = list(csv.DictReader(path.open(encoding="utf-8", newline="")))
    assert set(r["model"] for r in rows) == set(MODELS)
    base_path = PROJECT / "docs/H7MS/对比与研究/候选引脚/STM32H723VGT6_interfaces.csv"
    base_functions = {r["function"] for r in csv.DictReader(base_path.open(encoding="utf-8-sig"))}
    for model, (ref, package) in MODELS.items():
        root = ET.parse(HERE / (ref + ".xml")).getroot()
        assert root.attrib["RefName"] == ref and root.attrib["Package"] == package
        assert any(p.attrib.get("Name") == "GPIO" and p.attrib.get("Version") == "STM32H72_gpio_v1_0" for p in root)
        pins = {
            re.match(r"P[A-Z]\d+(?:_C)?", p.attrib["Name"]).group(): p
            for p in root if p.tag.endswith("Pin") and re.match(r"P[A-Z]\d", p.attrib["Name"])
        }
        selected = [r for r in rows if r["model"] == model]
        assert {r["function"] for r in selected} == base_functions
        for field in ("function", "pin", "ball"):
            assert len({r[field] for r in selected}) == len(selected), (model, field)
        exti = [re.search(r"\d+", r["pin"]).group() for r in selected if r["mode"] == "EXTI"]
        assert len(set(exti)) == len(exti), model
        for row in selected:
            p = pins[row["pin"]]
            assert row["package"] == package and row["ball"] == p.attrib["Position"], row
            assert row["peripheral_signal"] in {s.attrib["Name"] for s in p if s.tag.endswith("Signal")}, row
            if row["mode"] == "AF":
                assert int(row["af"]) in afs[(row["pin"], row["peripheral_signal"])], row
        assigned = {r["peripheral_signal"] for r in selected if r["scope"] == "required"}
        for can in (1, 2, 3):
            assert {f"FDCAN{can}_RX", f"FDCAN{can}_TX"} <= assigned
        for uart in ("USART1", "USART2", "USART3", "UART4"):
            assert {f"{uart}_RX", f"{uart}_TX"} <= assigned
        assert {"USB_OTG_HS_DM", "USB_OTG_HS_DP", "SPI1_SCK", "SPI1_MISO", "SPI1_MOSI"} <= assigned
        assert {"OCTOSPIM_P1_CLK", "OCTOSPIM_P1_NCS", *(f"OCTOSPIM_P1_IO{i}" for i in range(4))} <= assigned
        print("PASS", model, package, len(selected), "pads", dict(Counter(r["scope"] for r in selected)))
    print("Checked bonding, signals, ordinary GPIO AFs, unique pads and EXTI lines.")
    print("USB PHY AF numbering, power/boot/clock/DMA, routing and hardware load NOT qualified.")


if __name__ == "__main__":
    check()
