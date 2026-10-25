"""Generate schematic-entry worksheets, not an EDA netlist or ERC substitute.

Component pin numbers follow the specifically named packages. J1/J2 and USB
use the v0.9.2 physical-pad contract; other lab headers retain noted conventions.
"""
from pathlib import Path
import csv

# Ordering codes, not a generic capacitance-only substitution contract.
MLCC = {
    "100nF": "C1005X7R1H104K050BB",
    "1uF": "C1608X7R1C105K080AC",
    "10uF": "GRM21BR61E106KA73L",
    "220pF": "C1608C0G1H221J080AA",
    "4.7nF": "C1608C0G1H472J080AA",
    "10nF": "C1608C0G1H103J080AA",
}

HERE = Path(__file__).resolve().parent


def main():
    rows = []
    board, page = "CORE", "C01"

    def part(ref, value, pins, fit="YES", notes=""):
        for pin, net in pins.items():
            rows.append(dict(board=board, page=page, reference=ref, part=value,
                             pin=str(pin), net=net, fit=fit, notes=notes))

    def two(ref, value, a, b="GND", fit="YES", notes=""):
        part(ref, value, {1:a, 2:b}, fit, notes)

    def cap(ref, net, value="100nF >=10V X7R"):
        nominal = value.split()[0]
        two(ref, MLCC[nominal], net, notes=nominal+"; see MLCC selection and effective-C acceptance table")

    def button(ref, a, b="GND"):
        # EVQP7A: four physical terminals, two internally connected pairs.
        part(ref,"EVQP7A01P",{"1L":a,"1R":a,"2L":b,"2R":b},notes="vendor terminal 1 pair and terminal 2 pair; project L/R pad aliases")

    def buf(ref, a, y):
        part(ref, "SN74LVC1G125DBVR", {1:"BUS_OE_N",2:a,3:"GND",4:y,5:"3V3_AUX"})
        cap("C_"+ref, "3V3_AUX")

    def gate(ref, a, b, y, supply):
        part(ref, "SN74LVC1G08DBVR", {1:a,2:b,3:"GND",4:y,5:supply})
        cap("C_"+ref, supply)

    def load_switch(ref, enable, output):
        part(ref,"TPS22919DCKR",{1:"5V_IN",2:"GND",3:enable,4:"NC",5:ref+"_QOD",6:output})
        two("R_"+ref+"_QOD","1k",ref+"_QOD",output)
        cap("C_"+ref+"_IN","5V_IN","1uF >=10V X7R")
        cap("C_"+ref+"_OUT",output)

    balls = list(csv.DictReader((HERE/"100球连接规划.csv").open(encoding="utf-8-sig")))
    part("U1","STM32H735VGH6",{r["ball"]:r["net"] for r in balls},notes="all 100 balls; verify symbol and footprint independently")
    two("L1","VLS252012HBX-2R2M-1","SMPS_SW","VCORE")
    cap("C_SMPS_IN","3V3_D","10uF 10V effective-C qualified")
    cap("C_SMPS_HF","3V3_D")
    cap("C_SMPS_SW","SMPS_SW","220pF C0G >=25V")
    for n in (1,2): cap("C_VCORE"+str(n),"VCORE","10uF 10V effective-C qualified")
    for ball in ("D8","G6"): cap("C_VCAP_"+ball,"VCORE")
    for ball in ("D6","E5","F6"): cap("C_VDD_"+ball,"3V3_D")
    cap("C_VDD_BULK","3V3_D","10uF")
    two("R_ANALOG","0R","3V3_D","3V3_A")
    for ref,net in [("VDDA","3V3_A"),("VREF","3V3_A"),("USB","3V3_D"),("VBAT","3V3_D")]:
        cap("C_"+ref+"_BULK",net,"1uF >=10V")
        cap("C_"+ref+"_HF",net)

    page="C02"
    part("U2","TPS62132RGTR",{1:"BUCK_SW",2:"BUCK_SW",3:"BUCK_SW",4:"BUCK_PG",5:"GND",6:"GND",7:"GND",8:"GND",9:"BUCK_SS",10:"5V_IN",11:"5V_IN",12:"5V_IN",13:"5V_IN",14:"3V3_D",15:"GND",16:"GND","EP":"GND"})
    two("L2","XFL4020-222MEC","BUCK_SW","3V3_D")
    cap("C_BUCK_IN","5V_IN","10uF 10V")
    for n in (2,3): cap("C_BUCK_IN"+str(n),"5V_IN","10uF")
    cap("C_BUCK_HF","5V_IN")
    for n in range(1,5): cap("C_BUCK_OUT"+(str(n) if n>1 else ""),"3V3_D","10uF")
    cap("C_BUCK_SS","BUCK_SS","10nF")
    two("R_BUCK_PG","100k","BUCK_PG","3V3_D")
    part("U_AUX","TPS2553DBVR-1",{1:"3V3_D",2:"GND",3:"AUX_EN",4:"AUX_FAULT_N",5:"AUX_ILIM",6:"3V3_AUX"})
    two("R_AUX_EN","10k","AUX_EN","3V3_D")
    button("SW_AUX_RESET","AUX_EN")
    two("R_AUX_ILIM","45.3k 1%","AUX_ILIM")
    two("R_AUX_FAULT","10k","AUX_FAULT_N","3V3_D")
    for ref,net,value in [("C_AUX_IN","3V3_D","1uF"),("C_AUX_IN_HF","3V3_D","100nF"),("C_AUX_OUT","3V3_AUX","10uF"),("C_AUX_OUT_HF","3V3_AUX","100nF")]: cap(ref,net,value)

    page="C03"
    part("Y1","X1G004171001500",{1:"3V3_D",2:"GND",3:"HSE_OUT",4:"3V3_D"})
    two("R_HSE","22R","HSE_OUT","HSE_IN")
    cap("C_HSE","3V3_D")
    # LSE is explicitly absent on compact A1; PC14/15 remain reserved at U1.
    part("U_RESET","TPS3808G33DBVR",{1:"NRST",2:"GND",3:"MR_N",4:"NC",5:"3V3_D",6:"3V3_D"})
    cap("C_RESET_U","3V3_D")
    two("R_MR","10k","MR_N","3V3_D")
    button("SW_RESET","MR_N")
    two("R_NRST","10k","NRST","3V3_D")
    cap("C_NRST","NRST","100nF")
    two("R_BOOT","10k","BOOT0")
    button("SW_BOOT","BOOT0","3V3_D")
    part("J_SWD","FTSH-105-01-L-DV-007-K",{1:"3V3_D",2:"SWDIO",3:"GND",4:"SWCLK",5:"GND",6:"NC",8:"NC",9:"GND",10:"NRST"},notes="pin 7 physically omitted; VTref is sense only, no debugger power injection")

    page="C04"
    two("R_IMU_POWER","0R","3V3_D","3V3_IMU")
    part("U_IMU","BMI088",{1:"NC",2:"GND",3:"3V3_IMU",4:"GND",5:"IMU_GYRO_CS",6:"GND",7:"GND",8:"IMU_SCK_DEV",9:"IMU_MOSI_DEV",10:"IMU_MISO",11:"3V3_IMU",12:"IMU_GYRO_IRQ",13:"NC",14:"IMU_ACC_CS",15:"IMU_MISO",16:"IMU_ACC_IRQ"})
    for sig in ("SCK","MOSI"): two("R_IMU_"+sig,"22R","IMU_"+sig,"IMU_"+sig+"_DEV")
    for sig in ("ACC","GYRO"): two("R_IMU_"+sig+"_CS","10k","IMU_"+sig+"_CS","3V3_IMU")
    for ref in ("C_IMU_VDD","C_IMU_VDDIO"): cap(ref,"3V3_IMU")
    cap("C_IMU_BULK","3V3_IMU","1uF")
    part("U_TEMP","TMP302ADRLR",{1:"GND",2:"GND",3:"TEMP_OK",4:"3V3_D",5:"3V3_D",6:"3V3_D"})
    cap("C_TEMP","3V3_D")
    two("R_TEMP","10k","TEMP_OK","3V3_D")
    gate("U_HEAT_GATE","TEMP_OK","NRST","HEAT_ALLOW","3V3_D")
    two("R_HEAT_ALLOW","100k","HEAT_ALLOW")
    load_switch("U_HEAT_POWER","HEAT_ALLOW","HEAT_5V")
    for n in range(1,5): two("R_HEAT"+str(n),"RC1206FR-07200RL","HEAT_5V","HEAT_DRAIN",notes="200 ohm 1%, 0.25W at 70C; four in parallel")
    part("Q_HEAT","DMN2056U-7",{1:"HEAT_GATE",2:"GND",3:"HEAT_DRAIN"})
    two("R_HEAT_G","100R","IMU_HEATER_PWM","HEAT_GATE")
    two("R_HEAT_G_PD","100k","HEAT_GATE")
    two("R_NTC_TOP","10k 0.1%","3V3_A","NTC_NODE")
    two("NTC1","NTCG163JF103FT1","NTC_NODE")
    two("R_NTC_ADC","1k","NTC_NODE","IMU_HEATER_NTC")
    cap("C_NTC","IMU_HEATER_NTC","10nF")
    two("R_V5_TOP","20k 0.1%","5V_IN","V5_NODE")
    two("R_V5_BOT","10k 0.1%","V5_NODE")
    two("R_V5_ADC","1k","V5_NODE","LOCAL_5V_ADC")
    cap("C_V5","LOCAL_5V_ADC","10nF")

    page="C05"
    cap("C_CAN_BULK","5V_IN","10uF")
    for n in range(1,4):
        s=f"CAN{n}"
        part("U_"+s,"TCAN1042HGVDRBRQ1",{1:s+"_TX",2:"GND",3:"5V_IN",4:s+"_RX",5:"3V3_D",6:s+"_L",7:s+"_H",8:s+"_STB","EP":"GND"})
        two("R_"+s+"_STB","10k",s+"_STB","3V3_D")
        two("R_"+s+"_TX","10k",s+"_TX","3V3_D")
        cap("C_"+s+"_VCC","5V_IN")
        cap("C_"+s+"_VIO","3V3_D")
        part("D_"+s,"PESD2CANFD24V-T,215",{1:s+"_L",2:s+"_H",3:"GND"})

    page="C06"
    part("J_USB","USB4105-GF-A-120",{"A1_B12":"GND","B1_A12":"GND","A4_B9":"USB_VBUS","B4_A9":"USB_VBUS","A5":"USB_CC1","B5":"USB_CC2","A6":"USB_DP_CONN","B6":"USB_DP_CONN","A7":"USB_DM_CONN","B7":"USB_DM_CONN","A8":"NC","B8":"NC",**{f"S{i}":"USB_SHELL" for i in range(1,5)}},notes="12 electrical lands + 4 plated shell slots; combined-pad aliases defined in connector pad table")
    for n in (1,2): two("R_CC"+str(n),"5.1k 1%","USB_CC"+str(n))
    two("R_USB_SHELL","0R","USB_SHELL")
    part("U_USB_ESD","USBLC6-2SC6",{1:"USB_DP_CONN",2:"GND",3:"USB_DM_CONN",4:"USB_DM_CONN",5:"USB_VBUS",6:"USB_DP_CONN"})
    for sig in ("DP","DM"): two("R_USB_"+sig,"0R","USB_"+sig+"_CONN","USB_"+sig)
    cap("C_USB_VBUS","USB_VBUS")
    part("U_VBUS","SN74LVC1G17DBVR",{1:"NC",2:"VBUS_SENSE",3:"GND",4:"VBUS_PRESENT",5:"3V3_D"})
    two("R_VBUS_SER","1k","USB_VBUS","VBUS_SENSE")
    two("R_VBUS_PD","100k","VBUS_SENSE")
    cap("C_VBUS_U","3V3_D")

    page="C07"
    contacts=list(csv.DictReader((HERE/"板间100触点逻辑规划.csv").open(encoding="utf-8-sig")))
    for ref in ("J1","J2"):
        part(ref,"TFM-125-02-L-D-A-TR",{r["contact"]:r["net"] for r in contacts if r["connector"]==ref},notes="v0.9.2 contact i = manufacturer pin i; CORE bottom; see physical pad coordinates")
    for net in ("5V_IN","3V3_D","3V3_A","3V3_AUX","VCORE","GND","NRST","BOOT0","TEMP_OK","HEAT_ALLOW","HEAT_5V","AUX_FAULT_N","BUCK_PG"):
        part("TP_"+net,"PCB_TP_0.8",{1:net})

    board,page="BASE_DBG","B01"
    for ref in ("J1","J2"):
        part(ref,"SFM-125-02-L-D-A-TR",{r["contact"]:r["net"] for r in contacts if r["connector"]==ref},notes="v0.9.2 contact i = manufacturer pin i; BASE top; SFM numbering is mirrored in X versus TFM component view")
    part("J_PWR","B2P-VH(LF)(SN)",{1:"BENCH_5V",2:"GND"},notes="5V bench input only; VHR-2N housing, SVH-21T-P1.1 contacts; not reverse-polarity protection")
    two("F1","045102.5MRL","BENCH_5V","FUSED_5V",notes="2.5A 451; backup fuse, not semiconductor current limiting")
    part("SW_MAIN","JS102011SCQN",{1:"GND",2:"MAIN_ON",3:"FUSED_5V"},notes="vertical actuator SMT; 2 common; OFF=1-2; ON=2-3; enable only, never load current")
    two("R_MAIN_ON_PD","100k","MAIN_ON")
    part("U_MAIN","TPS22975DSGR",{1:"FUSED_5V",2:"FUSED_5V",3:"MAIN_ON",4:"FUSED_5V",5:"GND",6:"MAIN_CT",7:"5V_IN",8:"5V_IN","EP":"GND"})
    cap("C_MAIN_CT","MAIN_CT","10nF")
    cap("C_MAIN_IN","FUSED_5V","1uF")
    cap("C_MAIN_HF","FUSED_5V")
    for n in range(1,5): cap("C_BASE_5V"+(str(n) if n>1 else ""),"5V_IN","10uF")
    cap("C_BASE_AUX","3V3_AUX","10uF")
    part("U_AUX_MON","TPS3808G33DBVR",{1:"AUX_READY",2:"GND",3:"3V3_AUX",4:"NC",5:"3V3_AUX",6:"3V3_AUX"})
    cap("C_AUX_MON","3V3_AUX")
    two("R_AUX_READY_PU","10k","AUX_READY","3V3_AUX")
    two("R_AUX_READY_PD","100k","AUX_READY")
    part("Q_BUS_ENABLE","DMN2056U-7",{1:"AUX_READY",2:"GND",3:"BUS_OE_N"})
    two("R_BUS_OE_PU","10k","BUS_OE_N","3V3_AUX")
    two("R_PWR_GOOD","100R","AUX_READY","EXP_PA10")
    iso={1:"NC",10:"GND",19:"BUS_OE_N",20:"3V3_AUX"}
    for i,pin in enumerate(("PC8","PC9","PC10","PC11","PD2","PC12","PB10","PB11")):
        iso[2+i]="EXP_"+pin;iso[18-i]="ISO_"+pin
    part("U_SD_I2C_ISO","SN74CB3Q3245PWR",iso)
    cap("C_SD_I2C_ISO","3V3_AUX")
    page="B02"
    for n in range(1,4):
        s=f"CAN{n}"
        part("J_"+s,"B3B-XH-A(LF)(SN)",{1:s+"_H",2:s+"_L",3:"GND"})
        two("R_"+s+"_TH","60.4R 1%",s+"_H",s+"_SPLIT")
        two("R_"+s+"_TL","60.4R 1%",s+"_SPLIT",s+"_TERM_L")
        cap("C_"+s+"_SPLIT",s+"_SPLIT","4.7nF")
        two("JP_"+s+"_TERM","PCB_SJ2_OPEN",s+"_TERM_L",s+"_L",fit="OPEN",notes="PCB copper pads, no purchased component; solder bridge only at bus endpoints")
        part("D_"+s,"PESD2CANFD24V-T,215",{1:s+"_L",2:s+"_H",3:"GND"},fit="DNP")

    page="B03"
    for n,tx,rx,direction in [(1,"PB14","PB15","PA0"),(2,"PD5","PD6","PA1"),(3,"PD8","PD9","PD11"),(4,"PD1","PD0","PD15")]:
        s=f"DEV{n}"
        buf("U_"+s+"_TXBUF","EXP_"+tx,s+"_D")
        buf("U_"+s+"_DIRBUF","EXP_"+direction,s+"_DIR")
        two("R_"+s+"_DIR_PD","10k","EXP_"+direction)
        two("R_"+s+"_DE_PD","10k",s+"_DIR")
        part("U_"+s,"THVD1450DR",{1:s+"_R",2:s+"_DIR",3:s+"_DIR",4:s+"_D",5:"GND",6:s+"_A_IC",7:s+"_B_IC",8:"3V3_AUX"})
        cap("C_"+s,"3V3_AUX")
        two("R_"+s+"_R_PU","10k",s+"_R","3V3_AUX",notes="RX idle while receiver disabled; pull-up on buffer supply domain")
        for line in ("A","B"):
            two("R_"+s+"_"+line+"_SURGE","CRCW060310R0JNEAHP",s+"_"+line,s+"_"+line+"_IC",notes="10 ohm 5% pulse-proof; do not substitute ordinary 0603")
        part("D_"+s+"_485","CDSOT23-SM712",{1:s+"_A",2:s+"_B",3:"GND"},notes="TVS at connector, before both series resistors; THVD1450 Figure 37 reference, board surge qualification pending")
        two("R_"+s+"_RXSEL","0R",s+"_R","EXP_"+rx)
        part("J_"+s+"_485","B3B-XH-A(LF)(SN)",{1:s+"_A",2:s+"_B",3:"GND"},notes="A=TI non-inverting; cable end-to-end numbered continuity; no power pin")
        two("R_"+s+"_TERM","120R 1%",s+"_A",s+"_TERM")
        two("JP_"+s+"_TERM","PCB_SJ2_OPEN",s+"_TERM",s+"_B",fit="OPEN",notes="PCB copper pads; default unbridged")
        buf("U_"+s+"_TTLBUF",s+"_TTL_IN",s+"_TTL_BUF")
        two("R_"+s+"_TTL_IN","1k",s+"_TTL_RX",s+"_TTL_IN")
        two("R_"+s+"_TTL_PU","100k",s+"_TTL_IN","3V3_AUX")
        two("R_"+s+"_TTL_SEL","0R",s+"_TTL_BUF","EXP_"+rx,fit="DNP",notes="remove RXSEL for TTL mode")
        part("J_"+s+"_TTL","B4B-XH-A(LF)(SN)",{1:"GND",2:s+"_D",3:s+"_TTL_RX",4:"3V3_AUX"},notes="pin4 reference only; not external power supply")
    for s,tx,rx in [("HOST","PE1","PE0"),("RC","PE8","PE7")]:
        part("J_"+s,"B4B-XH-A(LF)(SN)",{1:"GND",2:"EXP_"+tx,3:s+"_RX_EXT",4:"3V3_AUX"},notes="pin4 reference only")
        two("R_"+s+"_IN","1k",s+"_RX_EXT",s+"_RX_IN")
        two("R_"+s+"_PU","100k",s+"_RX_IN","3V3_AUX")
        buf("U_"+s+"_RXBUF",s+"_RX_IN","EXP_"+rx)

    page="B04"
    spi=[("SCK","PB3",True),("MOSI","PB2",True),("MISO","PB4",False),("NSS","PA15",True),("READY","PB1",False)]
    hdr={}
    for i,(sig,pin,master_out) in enumerate(spi):
        net="LINK_"+sig
        hdr[2*i+1]=net;hdr[2*i+2]="GND"
        buf("U_"+net,net,net+"_IN_BUF")
        two("R_"+net+"_IDLE","100k",net,"3V3_AUX" if sig=="NSS" else "GND")
        two("R_"+net+"_OUT","22R","EXP_"+pin,net,fit="MASTER" if master_out else "SLAVE",notes="OUT xor IN; default MASTER")
        two("R_"+net+"_IN","0R",net+"_IN_BUF","EXP_"+pin,fit="SLAVE" if master_out else "MASTER",notes="OUT xor IN; default MASTER")
    hdr[11]="LINK_SYNC";hdr[12]="GND"
    part("J_LINK","TSW-106-07-L-D",hdr,notes="2x6 2.54mm; odd signals / even GND; pin 1 marked, no power pin; MASTER/SLAVE assembly exclusive")
    two("R_LINK_SYNC","22R","EXP_PA5","LINK_SYNC",fit="DNP",notes="optional SYNC needs explicit role/receiver buffering")
    two("R_NSS_PU","10k","EXP_PA15","3V3_AUX")
    two("R_READY_PD","100k","EXP_PB1")
    part("J_I2C","B4B-XH-A(LF)(SN)",{1:"GND",2:"3V3_AUX",3:"ISO_PB10",4:"ISO_PB11"})
    for pin in ("PB10","PB11"): two("R_I2C_"+pin,"4.7k","ISO_"+pin,"3V3_AUX")
    for r in contacts:
        if r["net"].startswith("EXP_"): part("TP_"+r["net"],"PCB_TP_0.8",{1:r["net"]})

    page="B05"
    part("J_SD","DM3AT-SF-PEJM5",{1:"ISO_PC10",2:"ISO_PC11",3:"ISO_PD2",4:"3V3_AUX",5:"SD_CLK",6:"GND",7:"ISO_PC8",8:"ISO_PC9","CD_A":"GND","CD_B":"EXP_PA4","SHELL":"GND"},notes="CD_A/CD_B use manufacturer drawing pads")
    two("R_SD_CLK","22R","ISO_PC12","SD_CLK")
    for pin in ("PC8","PC9","PC10","PC11","PD2"): two("R_SD_PU_"+pin,"10k","ISO_"+pin,"3V3_AUX")
    two("R_SD_CD_PU","10k","EXP_PA4","3V3_AUX")
    cap("C_SD_BULK","3V3_AUX","10uF")
    cap("C_SD_HF","3V3_AUX")
    for pin in ("PC6","PC7","PA2","PA3"):
        two("R_PWM_"+pin,"220R","EXP_"+pin,"PWM_"+pin)
        two("R_PWM_"+pin+"_PD","100k","PWM_"+pin)
        part("J_PWM_"+pin,"B2B-XH-A(LF)(SN)",{1:"PWM_"+pin,2:"GND"})
    for pin in ("PC0","PC1"):
        part("RV_"+pin,"TC33X-2-103E",{1:"GND",2:"ADC_TEST_"+pin,3:"3V3_AUX"},notes="10k +/-25%; pin2 wiper; clockwise toward pin3 raises voltage; adjustment only, not precision reference")
        two("R_ADC_"+pin,"1k","ADC_TEST_"+pin,"EXP_"+pin)
        cap("C_ADC_"+pin,"EXP_"+pin,"10nF")
        part("TP_ADC_"+pin,"PCB_TP_0.8",{1:"ADC_TEST_"+pin},notes="remove potentiometer before external signal injection")

    page="B06"
    part("J_ESTOP","B2B-XH-A(LF)(SN)",{1:"3V3_AUX",2:"EXP_PA8"},notes="external normally-closed contact; unplug means STOP")
    two("R_ESTOP_PD","10k","EXP_PA8")
    two("R_ENABLE_PD","10k","EXP_PE10")
    gate("U_ENABLE","EXP_PE10","EXP_PA8","LOAD_ENABLE","3V3_AUX")
    two("R_LOAD_EN_PD","100k","LOAD_ENABLE")
    load_switch("U_LOAD","LOAD_ENABLE","LOAD_5V")
    part("J_LOAD","B2B-XH-A(LF)(SN)",{1:"LOAD_5V",2:"GND"})
    for n in range(1,5): two("R_LOAD"+(str(n) if n>1 else ""),"RC1206FR-07200RL","LOAD_5V",fit="OPTION",notes="four parallel 200 ohm; fit all four for 50 ohm 1W nominal dummy load")
    for pin in ("PB7",):
        two("R_STATUS_"+pin+"_PU","10k","EXP_"+pin,"3V3_AUX")
        two("R_STATUS_"+pin+"_PD","100k","EXP_"+pin)
    button("SW_FAULT","EXP_PB7")

    with (HERE/"原理图连接.csv").open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=["board","page","reference","part","pin","net","fit","notes"])
        w.writeheader();w.writerows(rows)
    print(f"Generated {len(rows)} pin connections; logical worksheet, not EDA/ERC.")


if __name__ == "__main__":
    main()
