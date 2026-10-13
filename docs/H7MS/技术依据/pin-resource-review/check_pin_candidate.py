"""Check a research pin candidate against archived ST package/AF data.

This is a document consistency check, not CubeMX or hardware qualification.
USB PHY AF10 is reviewed separately against ST's H723ZG USB example because
the GPIO AF XML omits the dedicated PHY functions.
"""
import csv
import re
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT = next(p for p in HERE.parents if (p / 'project.json').exists())
CSV = PROJECT / "docs/H7MS/对比与研究/候选引脚/STM32H723VGT6_interfaces.csv"


def short_pin(name):
    return re.match(r"P[A-Z]\d+(?:_C)?", name).group(0)


def check():
    package = ET.parse(HERE / "STM32H723VGTx.xml").getroot()
    assert package.attrib["Package"] == "LQFP100"
    assert package.attrib["RefName"] == "STM32H723VGTx"
    pins = {
        short_pin(p.attrib["Name"]): p
        for p in package
        if p.tag.endswith("Pin") and re.match(r"P[A-Z]\d", p.attrib["Name"])
    }
    modes = ET.parse(HERE / "GPIO-STM32H72_gpio_v1_0_Modes.xml").getroot()
    afs = {}
    for pin in modes.iter():
        if not pin.tag.endswith("GPIO_Pin"):
            continue
        for signal in pin:
            values = [
                v.text
                for v in signal.iter()
                if v.tag.endswith("PossibleValue") and v.text
            ]
            afs[(pin.attrib["Name"], signal.attrib["Name"])] = {
                int(m.group(1))
                for v in values
                if (m := re.match(r"GPIO_AF(\d+)_", v))
            }
    rows = list(csv.DictReader(CSV.open(encoding="utf-8-sig", newline="")))
    assert len({r["pin"] for r in rows}) == len(rows), "Duplicate pad allocation"
    assert len({r["lqfp100_pin"] for r in rows}) == len(rows), "Duplicate pin number"
    assert len({r["function"] for r in rows}) == len(rows), "Duplicate function"
    exti = [re.search(r"\d+", r["pin"]).group() for r in rows if r["mode"] == "EXTI"]
    assert len(set(exti)) == len(exti), "Shared EXTI line"
    for row in rows:
        pin, signal = row["pin"], row["peripheral_signal"]
        source = pins[pin]
        assert source.attrib["Position"] == row["lqfp100_pin"], row
        signals = {s.attrib["Name"] for s in source if s.tag.endswith("Signal")}
        assert signal in signals, row
        if row["mode"] == "AF":
            assert int(row["af"]) in afs[(pin, signal)], row
        elif row["mode"] == "USB_PHY":
            assert (pin, signal, row["af"]) in {
                ("PA11", "USB_OTG_HS_DM", "10"),
                ("PA12", "USB_OTG_HS_DP", "10"),
            }, row
    assigned = {r["peripheral_signal"] for r in rows if r["scope"] == "required"}
    for can in (1, 2, 3):
        assert {f"FDCAN{can}_RX", f"FDCAN{can}_TX"} <= assigned
    for uart in ("USART1", "USART2", "USART3", "UART4"):
        assert {f"{uart}_RX", f"{uart}_TX"} <= assigned
    assert {f"OCTOSPIM_P1_IO{i}" for i in range(4)} <= assigned
    assert {"OCTOSPIM_P1_CLK", "OCTOSPIM_P1_NCS"} <= assigned
    assert {"SPI1_SCK", "SPI1_MISO", "SPI1_MOSI"} <= assigned
    print("PASS:", len(rows), "distinct pads;", dict(Counter(r["scope"] for r in rows)))
    print("Package positions, signal availability, AF mappings and EXTI uniqueness checked.")
    print("USB PHY AF10: separately reviewed ST example; not provided by AF XML.")
    print("NOT checked: CubeMX clocks/DMA, schematics, electrical timing or hardware load.")


if __name__ == "__main__":
    check()
