"""Vendor-drawing-based, EDA-neutral land definitions; dimensions in mm.

Local view is from the component side: X right, Y down, no PCB flip applied.
Samtec dimensions use the governing inch figures converted to mm.
This produces design inputs, not a fabrication-qualified footprint library.
"""
from pathlib import Path
import csv

HERE = Path(__file__).resolve().parent


def main():
    contacts = list(csv.DictReader((HERE / "板间100触点逻辑规划.csv").open(encoding="utf-8-sig")))
    rows = []

    def pad(board, ref, mpn, name, net, kind, x, y, w, h, dx=0, dy=0, note=""):
        rows.append(dict(board=board, reference=ref, mpn=mpn, pad=name, net=net,
                         type=kind, x_mm=round(x, 5), y_mm=round(y, 5),
                         width_mm=round(w, 5), height_mm=round(h, 5),
                         drill_x_mm=dx, drill_y_mm=dy, notes=note))

    for board, family, outer in [("CORE", "TFM", .250 * 25.4), ("BASE_DBG", "SFM", .195 * 25.4)]:
        mpn = family + "-125-02-L-D-A-TR"
        for ref in ("J1", "J2"):
            for c in (r for r in contacts if r["connector"] == ref):
                i = int(c["contact"])
                x = -15.24 + ((i - 1) // 2) * 1.27
                if family == "SFM":
                    x = -x  # SFM vendor print: pin 1 at right, unlike TFM.
                y = (outer + .020 * 25.4) / 4 * (1 if i % 2 else -1)
                pad(board, ref, mpn, str(i), c["net"], "SMD", x, y,
                    .029 * 25.4, (outer - .020 * 25.4) / 2,
                    note="component-side view; mating contacts lie at Y=+/-0.635, not at solder-pad centers")
            for j, x in enumerate((-16.8275, 16.8275), 1):
                pad(board, ref, mpn, f"NP{j}", "MECHANICAL", "NPTH", x, 0, 1.4224, 1.4224,
                    1.4224, 1.4224, "alignment peg; unnumbered and unconnected in EDA")

    usb = [
        ("A1_B12", -3.2, "GND"), ("A4_B9", -2.4, "USB_VBUS"),
        ("B8", -1.75, "NC"), ("A5", -1.25, "USB_CC1"),
        ("B7", -.75, "USB_DM_CONN"), ("A6", -.25, "USB_DP_CONN"),
        ("A7", .25, "USB_DM_CONN"), ("B6", .75, "USB_DP_CONN"),
        ("B5", 1.25, "USB_CC2"), ("A8", 1.75, "NC"),
        ("B4_A9", 2.4, "USB_VBUS"), ("B1_A12", 3.2, "GND")]
    for name, x, net in usb:
        pad("CORE", "J_USB", "USB4105-GF-A-120", name, net, "SMD", x, 0,
            .6 if "_" in name else .3, 1.15, note="combined names are project pad aliases; USB4105 Rev B4 p1")
    for i, (x, y, h, hole_h) in enumerate([(-4.32, .575, 2.1, 1.7), (4.32, .575, 2.1, 1.7),
                                         (-4.32, 4.755, 1.8, 1.4), (4.32, 4.755, 1.8, 1.4)], 1):
        pad("CORE", "J_USB", "USB4105-GF-A-120", f"S{i}", "USB_SHELL", "PTH_SLOT",
            x, y, 1.0, h, .6, hole_h, "plated slot; no paste aperture; shell stake S=1.20 mm")
    for i, x in enumerate((-2.89, 2.89), 1):
        pad("CORE", "J_USB", "USB4105-GF-A-120", f"NP{i}", "MECHANICAL", "NPTH",
            x, 1.075, .65, .65, .65, .65, "locating peg; PCB edge Y=7.355")

    # Bourns p2: 0.85 mm square lands, 1.90 mm lead pitch, 2.00 mm row spacing.
    for n in range(1, 5):
        for i, x, y, net in [(1, -.95, 1, f"DEV{n}_A"), (2, .95, 1, f"DEV{n}_B"), (3, 0, -1, "GND")]:
            pad("BASE_DBG", f"D_DEV{n}_485", "CDSOT23-SM712", str(i), net, "SMD", x, y, .85, .85,
                note="Bourns recommended lands; pin 3 common ground")
    connections=list(csv.DictReader((HERE / "原理图连接.csv").open(encoding="utf-8-sig")))
    for r in connections:
        mpn=r["part"]
        if mpn in ("B2B-XH-A(LF)(SN)","B3B-XH-A(LF)(SN)","B4B-XH-A(LF)(SN)"):
            hole=1.0 if mpn.startswith("B2") else .9
            pad(r["board"],r["reference"],mpn,r["pin"],r["net"],"PTH",
                -(int(r["pin"])-1)*2.5,0,hole+.8,hole+.8,hole,hole,
                "JST XH p2 component view: pin 1 right; no boss; copper diameter is project choice, hole per JST")
        elif mpn=="B2P-VH(LF)(SN)":
            pad(r["board"],r["reference"],mpn,r["pin"],r["net"],"PTH",
                (int(r["pin"])-1)*3.96,0,2.7,2.7,1.65,1.65,
                "JST VH p4 component view: pin 1 left; copper diameter is project choice")
    with (HERE / "连接器与保护器件焊盘.csv").open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)

    mating = []
    for r in contacts:
        i = int(r["contact"])
        x = 15.24 - ((i - 1) // 2) * 1.27
        y = .635 if i % 2 else -.635
        mating.append(dict(connector=r["connector"], core_pin=i, base_pin=i, net=r["net"],
                           mating_x_mm=round(x, 3), mating_y_mm=y,
                           core_local_to_assembly="X=-local_X; Y=local_Y (CORE bottom)",
                           base_local_to_assembly="X=local_X; Y=local_Y (BASE top)"))
    with (HERE / "板间实体针序.csv").open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(mating[0])); w.writeheader(); w.writerows(mating)
    print(f"Generated {len(rows)} land/hole rows and {len(mating)} physical mating pairs.")


if __name__ == "__main__":
    main()
