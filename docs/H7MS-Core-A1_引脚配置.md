# H7MS-Core-A1引脚配置说明

版本：Pin Plan v0.7  
MCU：STM32H743VIH6  
封装：TFBGA100，8 mm × 8 mm，0.8 mm球距  
时钟：8 MHz CMOS有源晶振，HSE Bypass  
状态：原理图输入基线，必须经CubeMX和官方文档复查后投板  

文档注记更新：2026-09-11。料号、球位和信号分配仍为v0.7；RGB与IMU加热共用TIM8的时间基问题尚未关闭，本表不代表全部外设已验证可同时工作。

## 1. 设计边界

- 核心板固定MCU、IMU及加热、QSPI、TF卡、USB-C、SWD、RGB和蜂鸣器。
- 底板提供`BASE_5V`，核心板产生3.3V；电池到5V Buck不放在核心板。
- 电池电压/电流在底板完成调理，Core-A1只接收0～3.3V模拟量。
- 舵机/CAN收发器、执行器电源和机器人专用接插件放在底板。
- 两只50Pin连接器共引出51个外部MCU资源和NRST，详细针序见[上下板接口规范](06_上下板接口规范.md)。
- 正式FOC的编码器、电流环、PWM和功率保护由独立驱动板本地完成。

## 2. 核心板固定功能

### 2.1 时钟、启动和调试

| 功能 | MCU引脚/球位 | 连接 |
| --- | --- | --- |
| HSE_IN | PH0/C1 | 8MHz有源晶振OUT经22～33Ω串联电阻输入 |
| AUX_GPIO | PH1/D1 | HSE Bypass后释放并引到底板 |
| LSE_IN | PC14/A1 | 可选32.768kHz晶体，首版允许DNP |
| LSE_OUT | PC15/B1 | 可选32.768kHz晶体，首版允许DNP |
| SWDIO | PA13/A10 | 5点SWD |
| SWCLK | PA14/A9 | 5点SWD |
| NRST | NRST/E1 | SWD、复位按键并引到底板 |
| BOOT0 | BOOT0/D5 | 100kΩ下拉和测试点 |

SWD固定为`3V3、GND、SWDIO、SWCLK、NRST`。PB3已用于SPI3，不保留SWO；CubeMX只启用Serial Wire，关闭完整JTAG。

有源晶振连接：Pin 1/OE以10kΩ上拉到3.3V，Pin 2/GND接地，Pin 3/OUT接PH0，Pin 4/VDD接3.3V并就近放置100nF和1µF。

### 2.2 USB、状态灯与蜂鸣器

| 功能 | MCU引脚/球位 | 配置 |
| --- | --- | --- |
| USB_DM | PA11/C10 | USB OTG FS Device Only |
| USB_DP | PA12/B10 | USB OTG FS Device Only |
| RGB_DATA | PB0/J4 | TIM8_CH2N + DMA，经AHCT缓冲驱动WS2812 |
| BUZZ_PWM | PC7/E10 | AF2 TIM3_CH2，经MOSFET驱动蜂鸣器 |

USB-C的CC1/CC2分别接5.1kΩ下拉，关闭MCU VBUS sensing。USB_5V与BASE_5V必须防倒灌。RGB数据建议用`74AHCT1G125`进行3.3V到5V缓冲，输入100kΩ下拉，DIN串联220～330Ω。蜂鸣器MOSFET栅极100kΩ下拉，接口建议限制在100mA以内。

### 2.3 SPI1 IMU与恒温

| 功能 | MCU引脚/球位 | AF |
| --- | --- | --- |
| IMU_CS | PA4/G3 | GPIO |
| IMU_SCK | PA5/H3 | AF5 SPI1_SCK |
| IMU_MISO | PA6/J3 | AF5 SPI1_MISO |
| IMU_MOSI | PA7/K3 | AF5 SPI1_MOSI |
| IMU_INT1 | PC4/G4 | EXTI |
| IMU_INT2 | PC5/H4 | EXTI |
| IMU_HEATER_PWM | PC6/F10 | AF3 TIM8_CH1 |
| IMU_HEATER_NTC | PC3_C/F3 | ADC3_INP1 |

加热MOSFET复位默认关闭。NTC开路、短路、超温或IMU无效时必须关闭加热。

### 2.4 QSPI NOR Flash

| 功能 | MCU引脚/球位 | AF |
| --- | --- | --- |
| QSPI_CLK | PB2/G5 | AF9 |
| QSPI_NCS | PB6/B5 | AF10 |
| QSPI_IO0 | PD11/G9 | AF9 |
| QSPI_IO1 | PD12/K10 | AF9 |
| QSPI_IO2 | PE2/A3 | AF9 |
| QSPI_IO3 | PD13/J10 | AF9 |

建议使用32MB容量，保存策略、回退模型、参数和故障快照。是否XIP由性能测试决定，不能让实时策略依赖未校验的外部数据。

### 2.5 TF卡：SDMMC1四位模式

| 功能 | MCU引脚/球位 | AF |
| --- | --- | --- |
| SDMMC1_D0 | PC8/F9 | AF12 |
| SDMMC1_D1 | PC9/E9 | AF12 |
| SDMMC1_D2 | PC10/B9 | AF12 |
| SDMMC1_D3 | PC11/B8 | AF12 |
| SDMMC1_CK | PC12/C8 | AF12 |
| SDMMC1_CMD | PD2/B7 | AF12 |
| SD_DETECT | PD10/H9 | GPIO，按卡座极性设置上拉 |

TF卡用于长日志、训练轨迹和升级包。首版可常供3.3V；若增加卡电源开关，需要从预留触点或外部逻辑另行分配使能信号。

### 2.6 板载电源采样

| 功能 | MCU引脚/球位 | ADC | 位置 |
| --- | --- | --- | --- |
| LOCAL_5V_MON | PC2_C/E2 | ADC3_INP0 | 核心板5V分压 |
| IMU_HEATER_NTC | PC3_C/F3 | ADC3_INP1 | 核心板NTC |

3.3V/VDDA通过内部VREFINT估计，不再浪费一个ADC脚测量与ADC参考同源的3.3V。

## 3. 引到底板的通信和控制资源

### 3.1 四路串行执行器接口

| 总线 | TX | RX | DIR |
| --- | --- | --- | --- |
| SERVO1 | PA9/C9，USART1_TX AF7 | PA10/D10，USART1_RX AF7 | PB14/H10 |
| SERVO2 | PD5/B6，USART2_TX AF7 | PD6/C6，USART2_RX AF7 | PB15/G10 |
| SERVO3 | PD8/K9，USART3_TX AF7 | PD9/J9，USART3_RX AF7 | PD14/H8 |
| SERVO4 | PD1/E8，UART4_TX AF8 | PD0/D8，UART4_RX AF8 | PD15/G8 |

DIR必须在底板外部下拉，使复位期间收发器处于接收或高阻状态。

### 3.2 双CAN-FD

| 功能 | MCU引脚/球位 | AF |
| --- | --- | --- |
| FDCAN1_TX | PB9/A4 | AF9 |
| FDCAN1_RX | PB8/B4 | AF9 |
| FDCAN1_STB | PE5/D3 | GPIO |
| FDCAN2_TX | PB13/J8 | AF9 |
| FDCAN2_RX | PB12/K8 | AF9 |
| FDCAN2_STB | PE6/E3 | GPIO |

收发器、TVS、共模电感和可切换120Ω终端放在底板。STB由底板设置为默认待机。

### 3.3 上位机、维护和I²C

| 功能 | MCU引脚/球位 | AF/用途 |
| --- | --- | --- |
| COMPUTE_TX | PE1/C4 | AF8 UART8_TX |
| COMPUTE_RX | PE0/D4 | AF8 UART8_RX |
| AUX_UART_TX | PA15/A8 | AF11 UART7_TX |
| AUX_UART_RX | PE7/H5 | AF7 UART7_RX |
| I2C2_SCL | PB10/J7 | AF4，底板EEPROM/扩展 |
| I2C2_SDA | PB11/K7 | AF4，底板EEPROM/扩展 |

只保留一组外部I²C；地址冲突由底板增加I²C多路复用器解决。所有逻辑接口均为3.3V域。

### 3.4 SPI3与四片选

| 功能 | MCU引脚/球位 | AF |
| --- | --- | --- |
| SPI3_SCK | PB3/A7 | AF6 |
| SPI3_MISO | PB4/A6 | AF6 |
| SPI3_MOSI | PB5/C5 | AF6 |
| SPI3_CS0 | PB7/A5 | GPIO |
| SPI3_CS1 | PD3/C7 | GPIO |
| SPI3_CS2 | PD4/D7 | GPIO |
| SPI3_CS3_OR_MCO | PA8/D9 | GPIO；可切换AF0 MCO1 |

所有片选在底板外部上拉。PA8若输出MCO就不能同时作为CS3。

## 4. 定时器、模拟量和安全

### 4.1 TIM1高级定时器

| 功能 | MCU引脚/球位 | AF |
| --- | --- | --- |
| TIM1_CH1 | PE9/K5 | AF1 |
| TIM1_CH1N | PE8/J5 | AF1 |
| TIM1_CH2 | PE11/H6 | AF1 |
| TIM1_CH2N | PE10/G6 | AF1 |
| TIM1_CH3 | PE13/K6 | AF1 |
| TIM1_CH3N | PE12/J6 | AF1 |
| TIM1_CH4 | PE14/G7 | AF1 |
| TIM1_BKIN | PE15/H7 | AF1 |

这是实验和通用扩展资源，不代表Core-A1直接承担正式FOC功率级。

### 4.2 TIM2和外部ADC

| 功能 | MCU引脚/球位 | 复用 |
| --- | --- | --- |
| TIM2_CH1 | PA0/G2 | AF1 |
| TIM2_CH2 | PA1/H2 | AF1 |
| TIM2_CH3 | PA2/J2 | AF1 |
| TIM2_CH4_OR_AUX_ADC | PA3/K2 | AF1或ADC12_INP15 |
| BASE_VBAT_SENSE | PC0/F1 | ADC123_INP10 |
| BASE_IBAT_SENSE | PC1/F2 | ADC123_INP11 |
| AUX_ADC | PB1/K4 | ADC12_INP5 |

PC0/PC1接收底板已调理的模拟信号。PA3的定时器和ADC功能二选一。

### 4.3 安全握手

| 功能 | MCU引脚/球位 | 方向与默认状态 |
| --- | --- | --- |
| PWR_EN | PC13/A2 | 输出，核心板和底板外部下拉，复位关闭 |
| PWR_GOOD | PD7/D6 | 输入，下拉，低表示未就绪 |
| ESTOP_N | PE3/B3 | 输入，下拉，低或断线表示急停 |
| BASE_FAULT_N | PE4/C3 | 输入，低有效，建议底板开漏 |
| AUX_GPIO | PH1/D1 | 双向，默认输入无上下拉 |
| NRST | NRST/E1 | 底板可复位核心板 |

使能顺序：底板识别→急停/故障检查→总线初始化→PWR_EN=1→等待PWR_GOOD→READY。

## 5. 电源球位

| 电源 | 球位 | 连接要求 |
| --- | --- | --- |
| VDD | D2、F5、K1 | 3.3V；每球就近100nF，区域增加4.7～10µF |
| VSS | C2、E4、E5、E6、J1 | 完整地平面 |
| VDDA | H1 | 3.3V滤波；就近100nF + 1µF |
| VSSA | G1 | 短路径连接主地平面 |
| VBAT | B2 | 无电池时接3.3V并去耦 |
| VDDLDO | F4 | 内部LDO模式接3.3V |
| VCAP1/2 | E7、F8 | 各自2.2µF低ESR到地，不能合并 |
| VDD33USB | F6 | 3.3V，就近100nF |
| PDR_ON | F7 | 接VDD，启用内部上电复位 |

使用内部LDO和VOS0支持480MHz，VCAP网络不能连接其他负载。

## 6. TFBGA100完整球位表

| 球位 | MCU引脚 | 冻结功能 |
| --- | --- | --- |
| A1 | PC14 | LSE_IN，可选DNP |
| A2 | PC13 | PWR_EN |
| A3 | PE2 | QSPI_IO2 |
| A4 | PB9 | FDCAN1_TX |
| A5 | PB7 | SPI3_CS0 |
| A6 | PB4 | SPI3_MISO |
| A7 | PB3 | SPI3_SCK |
| A8 | PA15 | UART7_TX |
| A9 | PA14 | SWCLK |
| A10 | PA13 | SWDIO |
| B1 | PC15 | LSE_OUT，可选DNP |
| B2 | VBAT | 3.3V或后备电源 |
| B3 | PE3 | ESTOP_N |
| B4 | PB8 | FDCAN1_RX |
| B5 | PB6 | QSPI_NCS |
| B6 | PD5 | SERVO2_TX |
| B7 | PD2 | SDMMC1_CMD |
| B8 | PC11 | SDMMC1_D3 |
| B9 | PC10 | SDMMC1_D2 |
| B10 | PA12 | USB_DP |
| C1 | PH0 | HSE_IN |
| C2 | VSS | GND |
| C3 | PE4 | BASE_FAULT_N |
| C4 | PE1 | COMPUTE_TX |
| C5 | PB5 | SPI3_MOSI |
| C6 | PD6 | SERVO2_RX |
| C7 | PD3 | SPI3_CS1 |
| C8 | PC12 | SDMMC1_CK |
| C9 | PA9 | SERVO1_TX |
| C10 | PA11 | USB_DM |
| D1 | PH1 | AUX_GPIO |
| D2 | VDD | 3.3V |
| D3 | PE5 | FDCAN1_STB |
| D4 | PE0 | COMPUTE_RX |
| D5 | BOOT0 | 启动选择 |
| D6 | PD7 | PWR_GOOD |
| D7 | PD4 | SPI3_CS2 |
| D8 | PD0 | SERVO4_RX |
| D9 | PA8 | SPI3_CS3_OR_MCO |
| D10 | PA10 | SERVO1_RX |
| E1 | NRST | 复位 |
| E2 | PC2_C | LOCAL_5V_MON |
| E3 | PE6 | FDCAN2_STB |
| E4 | VSS | GND |
| E5 | VSS | GND |
| E6 | VSS | GND |
| E7 | VCAP1 | 2.2µF到地 |
| E8 | PD1 | SERVO4_TX |
| E9 | PC9 | SDMMC1_D1 |
| E10 | PC7 | BUZZ_PWM/TIM3_CH2 |
| F1 | PC0 | BASE_VBAT_SENSE |
| F2 | PC1 | BASE_IBAT_SENSE |
| F3 | PC3_C | IMU_HEATER_NTC |
| F4 | VDDLDO | 3.3V |
| F5 | VDD | 3.3V |
| F6 | VDD33USB | 3.3V |
| F7 | PDR_ON | 接VDD |
| F8 | VCAP2 | 2.2µF到地 |
| F9 | PC8 | SDMMC1_D0 |
| F10 | PC6 | IMU_HEATER_PWM |
| G1 | VSSA | 模拟地 |
| G2 | PA0 | TIM2_CH1 |
| G3 | PA4 | IMU_CS |
| G4 | PC4 | IMU_INT1 |
| G5 | PB2 | QSPI_CLK |
| G6 | PE10 | TIM1_CH2N |
| G7 | PE14 | TIM1_CH4 |
| G8 | PD15 | SERVO4_DIR |
| G9 | PD11 | QSPI_IO0 |
| G10 | PB15 | SERVO2_DIR |
| H1 | VDDA | 模拟3.3V |
| H2 | PA1 | TIM2_CH2 |
| H3 | PA5 | IMU_SCK |
| H4 | PC5 | IMU_INT2 |
| H5 | PE7 | UART7_RX |
| H6 | PE11 | TIM1_CH2 |
| H7 | PE15 | TIM1_BKIN |
| H8 | PD14 | SERVO3_DIR |
| H9 | PD10 | SD_DETECT |
| H10 | PB14 | SERVO1_DIR |
| J1 | VSS | GND |
| J2 | PA2 | TIM2_CH3 |
| J3 | PA6 | IMU_MISO |
| J4 | PB0 | RGB_DATA |
| J5 | PE8 | TIM1_CH1N |
| J6 | PE12 | TIM1_CH3N |
| J7 | PB10 | I2C2_SCL |
| J8 | PB13 | FDCAN2_TX |
| J9 | PD9 | SERVO3_RX |
| J10 | PD13 | QSPI_IO3 |
| K1 | VDD | 3.3V |
| K2 | PA3 | TIM2_CH4_OR_AUX_ADC |
| K3 | PA7 | IMU_MOSI |
| K4 | PB1 | AUX_ADC |
| K5 | PE9 | TIM1_CH1 |
| K6 | PE13 | TIM1_CH3 |
| K7 | PB11 | I2C2_SDA |
| K8 | PB12 | FDCAN2_RX |
| K9 | PD8 | SERVO3_TX |
| K10 | PD12 | QSPI_IO1 |

## 7. 关键复用冲突

| 引脚 | 默认功能 | 可选/原功能 | 规则 |
| --- | --- | --- | --- |
| PH1 | AUX_GPIO | HSE_OUT | 只因HSE Bypass释放 |
| PB0 | RGB_DATA | 其他定时器功能 | 固定给RGB |
| PB3/PB4/PB5 | SPI3 | SWO、原蜂鸣器等 | PB3不再提供SWO；蜂鸣器迁到PC7 |
| PC6 | IMU_HEATER_PWM | TIM3_CH1/HRTIM | 固定给加热 |
| PC7 | BUZZ_PWM | TIM3_CH2 | 固定给蜂鸣器 |
| PC8～PC12、PD2 | SDMMC1 | 原TIM3/I2C3/SPI3/PWR_GOOD | 固定给TF卡 |
| PD7 | PWR_GOOD | AUX_GPIO | 固定给电源良好 |
| PD10 | SD_DETECT | AUX_GPIO | 固定给卡检测 |
| PA3 | TIM2_CH4 | ADC12_INP15 | 二选一 |
| PA8 | SPI3_CS3 | MCO1 | 二选一，默认CS3 |
| PB1 | AUX_ADC | GPIO | 默认模拟输入 |
| PA9/PA10 | SERVO1 | USB VBUS/ID相关功能 | USB仅Device并关闭VBUS sensing |

引入TF卡的明确代价是取消第二路外部I²C和外部TIM3通道。需要更多I²C时在底板使用多路复用器。

### 待解决：TIM8时间基共用（H0-03）

RGB使用`PB0/TIM8_CH2N + DMA`，IMU加热使用`PC6/TIM8_CH1`。两个通道共用计数器及常规PWM周期配置，不能按两个独立频率的定时器配置。IMU恒温任务的100 Hz是软件闭环更新频率，不等于加热PWM载波频率。

需先确定RGB具体器件时序、加热PWM频率和MOSFET开关损耗，再选择兼容实现或重新分配资源。更改周期、停止RGB DMA或关闭定时器时均需验证加热输出；当前没有选定替代引脚，也未修改本版分配。关闭证据为CubeMX配置、驱动说明和两路信号同时工作的波形，跟踪于[项目状态与待办](08_项目状态与待办.md)。

## 8. CubeMX基线

1. 选择精确料号`STM32H743VIH6`。
2. RCC HSE选择Bypass Clock Source，输入8MHz；LSE按是否贴装选择。
3. SYS Debug选择Serial Wire。
4. USB_OTG_FS选择Device Only并关闭VBUS sensing。
5. 启用SPI1、QUADSPI Bank1和SDMMC1 4-bit Wide Bus。
6. 启用SPI3：PB3/PB4/PB5；片选使用GPIO。
7. 启用USART1、USART2、USART3、UART4、UART8；UART7默认关闭。
8. 启用FDCAN1、FDCAN2和I2C2。
9. ADC启用PC0、PC1、PC2_C、PC3_C和PB1；PA3默认保持TIM2/ADC均关闭，按底板选择。
10. TIM3_CH2用于蜂鸣器；TIM8_CH1用于加热；TIM8_CH2N + DMA用于RGB（待关闭H0-03，不能把此项视为已通过的并发配置）。
11. TIM1、TIM2和其他扩展外设默认关闭，按底板能力启用。
12. 未使用且不外露的GPIO设为Analog/No Pull；所有外露备用GPIO上电为Input/No Pull。

480MHz时钟基线：

```text
HSE = 8 MHz
PLL1M = 2
PLL1N = 240
PLL1P = 2       → CPU 480 MHz
PLL1Q = 20      → 48 MHz候选域
PLL1R = 2
HCLK = 240 MHz
APB1/2/3/4 = 120 MHz
```

USB和SDMMC的最终48MHz内核时钟来源、Flash等待周期、电源档位和外设时钟必须以当前CubeMX合法性检查为准。

## 9. 上电默认状态

| 信号 | 硬件默认 |
| --- | --- |
| PWR_EN | 下拉，执行器关闭 |
| SERVOx_DIR | 底板下拉，收发器接收/高阻 |
| CANx_STB | 底板默认待机 |
| SPI3_CSx | 底板上拉，全部不选中 |
| RGB_DATA | 缓冲器输入下拉，数据为低 |
| BUZZ_PWM | MOSFET栅极下拉，蜂鸣器关闭 |
| IMU_HEATER_PWM | MOSFET栅极下拉，加热关闭 |
| ESTOP_N | 下拉，未确认安全 |
| BASE_FAULT_N | 上拉，无故障；任意低电平撤销PWR_EN |
| PWR_GOOD | 下拉，电源未就绪 |

本表是核心板、底板和固件共同遵守的接口契约，安全状态不能只依赖软件初始化。

## 10. 复核资料

- [STM32H743/753官方文档入口](https://www.st.com/en/microcontrollers-microprocessors/stm32h743-753/documentation.html)
- [STM32H743VI数据手册](https://www.st.com/resource/en/datasheet/stm32h743vi.pdf)
- CubeMX必须选择精确料号`STM32H743VIH6`，以当前安装版本生成的引脚冲突和时钟检查结果为最终复核输入。
