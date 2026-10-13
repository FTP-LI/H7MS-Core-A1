"""Derive exact-package comparison from the archived ST pin data.

This is a pin/bonding audit, not electrical, CubeMX or hardware qualification.
"""
import csv
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT = next(p for p in HERE.parents if (p / 'project.json').exists())
SOURCE = PROJECT / "docs/H7MS/技术依据/compact-mcu-review"
MODELS = ["STM32H723VGH6", "STM32H735VGH6"]


def main():
    pins = {}
    for model in MODELS:
        root = ET.parse(SOURCE / (model[:-1] + "x.xml")).getroot()
        pins[model] = {p.attrib["Position"]: p for p in root if p.tag.endswith("Pin")}
        assert len(pins[model]) == 100
    with (HERE / "all-100-balls.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["ball", *MODELS])
        for ball in sorted(pins[MODELS[0]], key=lambda x: (x[0], int(x[1:]))):
            w.writerow([ball, *(pins[m][ball].attrib["Name"] for m in MODELS)])
    all_rows = list(csv.DictReader((PROJECT / "docs/H7MS/对比与研究/候选引脚/STM32_compact_BGA_interfaces.csv").open(encoding="utf-8")))
    selected = {m: {r["function"]: r for r in all_rows if r["model"] == m} for m in MODELS}
    a, b = (selected[m] for m in MODELS)
    assert set(a) == set(b) and len(a) == 62
    with (HERE / "interfaces-side-by-side.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["scope", "function", "signal", "port", "H723_ball", "H735_ball", "af", "mode"])
        for name, r in a.items():
            assert (r["pin"], r["peripheral_signal"], r["af"]) == (b[name]["pin"], b[name]["peripheral_signal"], b[name]["af"])
            w.writerow([r["scope"], name, r["peripheral_signal"], r["pin"], r["ball"], b[name]["ball"], r["af"], r["mode"]])
    ports = {m: {re.match(r"P[A-Z]\d+(?:_C)?", p.attrib["Name"]).group() for p in pins[m].values() if re.match(r"P[A-Z]\d", p.attrib["Name"])} for m in MODELS}
    ch4 = [p.attrib["Name"] for p in pins[MODELS[1]].values() if any(s.attrib.get("Name") == "TIM1_CH4" for s in p)]
    report = {
        "date": "2026-10-11", "selected_signals_each": 62,
        "changed_balls_among_selected": sum(a[k]["ball"] != b[k]["ball"] for k in a),
        "port_named_bonded_pads_not_datasheet_GPIO_count": {m: len(ports[m]) for m in MODELS},
        "H723_only_port_names": sorted(ports[MODELS[0]] - ports[MODELS[1]]),
        "H735_only_port_names": sorted(ports[MODELS[1]] - ports[MODELS[0]]),
        "H735_TIM1_CH4_pins": ch4,
        "legacy_conflict": "H735VGH6 TIM1_CH4 has only PA11, already required for native USB DM.",
        "legacy_full_signal_budget": {
            "status": "Historical limit illustration only; user now requests DM/previous-H723 functional resources, not this complete H743 legacy set.",
            "current_candidate": 62, "remove_new_optional_second_IMU_CS": -1,
            "restore_local_5V_ADC": 1, "restore_aux_UART_TX_RX": 2,
            "restore_SPI3_bus_plus_four_CS": 7, "restore_TIM1_eight_signals": 8,
            "restore_TIM2_four_signals": 4, "restore_base_voltage_current_and_aux_ADC": 3,
            "total_dedicated_signal_pads": 86,
            "assumption": "All listed functions concurrent and independently bonded; LSE retained; no GPIO expander or interface sharing."
        },
        "qualification": "Static evidence only; USB PHY AF numbering, clock/DMA, electrical, routing, errata and mixed load remain unqualified."
    }
    assert ch4 == ["PA11"]
    (HERE / "pin-audit.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
