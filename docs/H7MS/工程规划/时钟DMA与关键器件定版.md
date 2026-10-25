# H735 时钟、DMA 与关键器件设计基线

> 2026-10-16更新：本文件的BASE-DBG按逻辑全集保留；实际五板、39.8 mm外形、电源/机械/MLCC变更以[v0.9.3设计输入](电源机械与40mm布局定版.md)和[紧凑板连接表](紧凑板原理图连接.csv)为准。旧3.3 nF软启动、未定电容/开关、单块大验证板及LSE预留焊盘描述不再用于A1。

2026-10-13，v0.9.1-design。承接 v0.9 引脚分配，三路 CAN 收发器仍全部在核心板。本文件冻结**首版原理图和固件实现的设计输入**，不代表完成 CubeMX、编译、ERC 或实物认证。机器配置见 [时钟DMA配置.json](时钟DMA配置.json)，连接见 [连接设计](核心板与验证扩展板连接设计.md)。

连接器和485保护以[v0.9.2定版](连接器与RS485保护定版.md)为准，时钟/DMA配置未改变。

## 1. 首版时钟：480 MHz，保留 TCM ECC

采用 8 MHz 有源晶振、HSE bypass、Direct SMPS、VOS0。首版不打开 CPU_FREQ_BOOST，避免为 550 MHz 关闭 ITCM/DTCM ECC；480 MHz 已满足用户最低要求。DS13312 Rev4 给出的普通 VOS0 上限为 520 MHz，550 MHz 另需 boost。将来升频必须另建配置并重新核对 UART、定时器、Flash、功耗和控制周期，不能只改 PLLN。

| PLL | 输入 / M | N | VCO | P / 输出 | Q / 输出 | R / 输出 |
| --- | --- | --- | --- | --- | --- | --- |
| PLL1 | 8 MHz / 2 = 4 MHz | 120 | 480 MHz | 1 / 480 MHz | 10 / 48 MHz | 2 / 240 MHz，未分配 |
| PLL2 | 8 MHz / 2 = 4 MHz | 100 | 400 MHz | 5 / 80 MHz | 5 / 80 MHz | 10 / 40 MHz |
| PLL3 | 8 MHz / 2 = 4 MHz | 96 | 384 MHz | 8 / 48 MHz，未分配 | 8 / 48 MHz | 16 / 24 MHz |

三组 FRACN=0、VCOWIDE、VCIRANGE_2（4–8 MHz）。PLL1 的 VCO 上限与 PLL2/3 不同：本方案没有使用“960 MHz VCO 再 /2”生成 CPU 480 MHz。PLL1P=1 有 H735 官方例程依据。

| 时钟域 / 外设 | 选择与结果 | 首版工作参数 |
| --- | --- | --- |
| CPU / AXI / AHB | D1CPRE=/1、HPRE=/2 → 480 / 240 MHz | Flash LATENCY=3、WRHIGHFREQ=3 |
| APB1/2/3/4 | 各 /2 → 120 MHz | 不把 APB 时钟误当定时器时钟 |
| TIM1/2/5/6/7/8 等 | TIMPRE=0，APB 分频非 1 → 240 MHz | 使用下表统一分频 |
| FDCAN1/2/3 | PLL2Q → 80 MHz，共同源 | Classical CAN 默认 1 Mbit/s；FD 单独使能 |
| SPI3 板间 | SPI123=PLL2P → 80 MHz | 主机 /16 = 5 MHz 起步；/8 = 10 MHz 验收目标；从机由对端供时钟 |
| SPI4 IMU | SPI45=PLL2Q → 80 MHz | /16 = 5 MHz，8 bit，Mode 0；不超过 BMI088 10 MHz |
| USB_OTG_HS 内置 FS PHY | PLL3Q → 48 MHz | Device，12 Mbit/s；不需要 ULPI |
| ADC1/2/3 kernel | PLL3R → 24 MHz；ADC 异步 /2 → 12 MHz | ADC3 12 bit，长采样；ADC1 电机专用参数另验 |
| SDMMC1 | PLL1Q → 48 MHz | CLKDIV=60 → 400 kHz 初始化；CLKDIV=1 → 24 MHz，4 bit；首版不用 bypass |
| OCTOSPI1 | PLL2R → 40 MHz | MEMORY_LOGGER 才使用；分频 2 → 20 MHz SDR 起步 |
| USART1/6、UART9/USART10 组 | D2PCLK2 → 120 MHz | 只开启本封装、当前配置实际可用实例 |
| USART2/3、UART4/5/7/8 组 | D2PCLK1 → 120 MHz | UART4 3 Mbit/s；UART8 1 Mbit/s；RC 按接收机协议 |
| I2C2 | D2PCLK1 → 120 MHz | 100 kHz 起步、400 kHz 目标；TIMINGR 依据实测上升时间由工具计算，禁止抄其他主频值 |
| RTC / IWDG | 首版 LSI | LSI 不承担板间同步或精确时间；LSE 焊位保留 DNP |

UART 过采样 16、PRESC=1 时，3 Mbit/s 的 BRR=40，1 Mbit/s 的 BRR=120；100 kbit/s 的 BRR=1200。115200 的 BRR 取 1042，误差约 -0.032%。DBUS 等接收机的反相、字长、校验与停止位单独设置，不能按普通 8N1 套用。

| 资源 | 固定用途 | 参数 |
| --- | --- | --- |
| TIM1_CH1 / PE9 | 加热 PWM | PSC=0，ARR=11999，20 kHz；CCR1=0 起机；MOE 最后打开；20 kHz 为验证起点，要检查对 IMU 的耦合 |
| TIM2 | 单调微秒时间戳 | PSC=239，ARR=0xffffffff；32 bit 约 71.6 分钟回卷，使用模运算或维护高字 |
| TIM6_TRGO | ADC3 扫描触发 | PSC=23999，ARR=99，100 Hz，MMS=Update，无需周期中断 |
| TIM7 | HAL 1 ms 时基 | PSC=23999，ARR=9；避免与 FreeRTOS 共用 SysTick |
| SysTick / PendSV | FreeRTOS | 1 kHz / 最低中断优先级；不依赖 tick 实现微秒同步 |
| TIM5 / TIM8 / TIM3 | 扩展 PWM / 电机 PWM / 编码器 | 随配置使用；同一 timer 多通道共用 PSC/ARR，不能承诺同 timer 每路独立频率 |

启动次序：全部输出安全态 → Direct SMPS 配置 → 等待供电与 VOS0 就绪 → Flash 延时 → HSE/PLL → 总线分频与 kernel mux → MPU/Cache/内存初始化 → DMA → 外设 → 中断 → FreeRTOS → 自检完成后使能 CAN 和执行输出。HSE CSS 故障进入 NMI 安全处理：加热清零、STB 置高、PWR_EN 置低、记录故障并复位；不可继续按旧波特率运行。ADC3 的 PC2_C/PC3_C 使用专用模拟输入，明确将 SYSCFG PC2/PC3 模拟开关置 OPEN，避免与扩展 PC2/PC3 误连。

## 2. DMA 定额分配，不使用动态抢占流

RM0468 表 98 明确 ADC3 对应 DMAMUX1 request 115；表 99 同时给出 BDMA request 17。首版选择官方 H735 ADC 示例使用的 DMA1/2 路径。BDMA 留空，避免为了节省一个 stream 引入 D3 SRAM 限制和另一套缓冲区。

| stream | request | 活跃配置 / 行为 |
| --- | --- | --- |
| DMA2 Stream0 | ADC3 | 全配置；半字、循环，核心 2 rank；RM_STANDARD 加 PC0/PC1 后 4 rank |
| DMA2 Stream1 / 2 | SPI4_RX / TX | 全配置；字节、normal；ACC/GYRO 串行调度，共用这对流 |
| DMA1 Stream0 / 1 | SPI3_RX / TX | SPI_LINK；字节、normal；先 RX 再 TX，NSS 帧间重新装载 |
| DMA1 Stream2 / 3 | UART4_RX / TX | 板间 RS-485；RX 循环 + IDLE/HT/TC，TX normal |
| DMA1 Stream4 / 5 | UART8_RX / TX | 上位机；RX 循环，TX normal |
| DMA1 Stream6 / 7 | USART1_RX / USART2_RX | 对应设备串口；TX 用 FIFO/中断 |
| DMA2 Stream3 / 4 | USART3_RX / UART7_RX | 设备与遥控器；TX 用 FIFO/中断 |
| DMA2 Stream5 / 6 / 7 | UART5_RX / USART6_RX / UART9_RX | 仅相应配置启用；其余配置空闲 |

RM_STANDARD / DUAL_SPI 使用 13/16 个 stream；SERIAL_IO 使用 16/16。CORE_BRINGUP 使用 3/16。其他配置由检查脚本计算，不能把未启用串口的流也初始化。新增持续 ADC1 DMA、RGB DMA、额外 UART TX DMA 前必须重新配额；MOTOR_LAB 电流环优先 ADC1 注入转换中断，不能挤入默认串口表。SPI4 两个片选互斥，BMI088 ACC 读操作需要 dummy byte，GYRO 事务单独处理，不能把两个芯片片选同时拉低。

FDCAN 不占 DMA1/2 stream；SDMMC 使用自身 IDMA；USB 首版采用 FIFO/中断、关闭 USB 内部 DMA；网络配置 ETH 使用自身 DMA。它们仍竞争 SRAM 和总线带宽，不能据此声称没有并发影响。NOR 首版采用有超时的低优先级间接读写；MDMA 优化单列后续验证，不在本次定额内。

**缓冲区基线：**TCM_AXI_SHARED=00，即 ITCM 64 KiB、AXI 320 KiB；DTCM 128 KiB 不变。开机读回 option bytes，不默默改写量产选项。AXI `0x24000000–0x2400ffff` 64 KiB 单独 `.dma_buffer`，MPU Normal、non-cacheable、shareable、XN，32 byte 对齐；普通 AXI 数据从 `0x24010000` 开始。DMA1/2、SDMMC1、ETH 的缓冲区都放此区；禁止栈上/DTCM 中的指针传给 DMA，SDMMC1 也不能随意改用 D2 SRAM。任务读写需要明确所有权与内存屏障；non-cacheable 不替代同步。若后来改为 cacheable，必须补充按整条 cache line 的 clean/invalidate 并防止相邻对象共享行。

分配目标：UART RX 每路 1 KiB，UART4/8 TX 各 1 KiB，SPI3 双收双发共 512 byte（4×128），SPI4 四组 32 byte 对齐缓冲，ADC3 双扫描 32 byte，SD staging 16 KiB，ETH 配置预留 24 KiB；SERIAL 与 ETH 的上限不相加。启动检查 linker map 和每个 buffer 地址/长度，不只检查数组声明。

**中断方案：**NVIC 4 bit 全抢占，`configLIBRARY_MAX_SYSCALL_INTERRUPT_PRIORITY=5`、kernel priority=15。ESTOP/故障 IRQ=3，只做寄存器禁能和原子标志，不调用 RTOS/HAL 阻塞函数；IMU DRDY/SPI4 DMA=5；FDCAN/SPI3=6；UART RX+IDLE=7、TX/USB/ADC=8、SD=9、TIM7/SysTick/PendSV=15。用到 FromISR 的 IRQ 数值不得小于 5；数值较小才更紧急。EXTI10 与 EXTI13 共享 EXTI15_10 向量，处理器必须检查两条 pending，避免漏掉另一颗 IMU 事件。

## 3. 三路 FDCAN 的时序和消息 RAM

三路共享 10 KiB = 2560 个 32-bit word，硬件不替软件检查重叠。为每路保留 768 word：offset 分别 **0、768、1536**；HAL `MessageRAMOffset` 的单位是 word，不是 byte。

每路：16 个 standard filter（16 word）、8 个 extended filter（16 word）、FIFO0 16 个、FIFO1 8 个、TX FIFO 8 个，各消息元素使用 64-byte payload 槽（18 word），TX event 8 个（16 word），无 dedicated RX/TX buffer。总计 **624 word/路**，三路实际 1872 word；预留块总计 2304 word，尾部还有 256 word。最后一路末端是 word 2160（exclusive）。默认全局滤波拒绝未匹配 ID 与不需要的 remote frame；TX event 不取走也会溢出，任务必须消费或停用并同步改布局。

| 模式 | 80 MHz 参数 | 结果 |
| --- | --- | --- |
| nominal | Prescaler=4，Seg1=15，Seg2=4，SJW=4 | 1 Mbit/s，20 tq，80% sample point |
| FD data | Prescaler=2，Seg1=15，Seg2=4，SJW=4 | 2 Mbit/s，20 tq，80% sample point |

Classical CAN 的 DLC 最大 8，64-byte RAM 槽不等于总线开启 FD。RM 电机总线保持 Classical；只有全网节点支持时才使用 FD/BRS。以上位时序是短线台架起点，线束长度、收发器延时、晶振偏差、FD TDC 需波形验证。每路总线上只有两个终端；三路之间没有数据线互联。

## 4. 关键器件与硬件修订

详细料号、位置、依据见 [关键器件定版.csv](关键器件定版.csv)。本轮锁定功能器件的原理图选型，采购库存、批次、封装库和热验证仍独立签核。

| 功能 | 选用型号 | 决策 |
| --- | --- | --- |
| MCU | STM32H735VGH6 | 不更换；0.8 mm TFBGA100 |
| 3.3 V buck | TPS62132RGTR + XFL4020-222MEC | 5 V 输入；输出与接地布局按原厂；不是保证能在小核心板连续输出额定 3 A |
| MCU SMPS 电感 | VLS252012HBX-2R2M-1 | 保留 2.2 µH；Direct SMPS 电源连接不变 |
| 8 MHz HSE | **Epson X1G004171001500** | 对应 SG-210STF 8.000000 MHz L；3.3 V、±50 ppm，完成原先缺失的完整订货号 |
| IMU | BMI088 | SPI4，独立两 CS/两 IRQ；热源与振动布局优先 |
| CAN ×3 | TCAN1042HGVDRBRQ1 | 核心板；DRB VSON8，VCC=5 V、VIO=3.3 V、独立 STB |
| CAN TVS | PESD2CANFD24V-T,215 | 核心保护；底板电缆口再设 DNP 焊位；首版 CMC 旁路，不未经 EMC 测试串入任意电感 |
| RS-485 ×4 | THVD1450DR | 验证扩展板；UART4 优先板间，另三路设备/负载模拟 |
| 加热低边 MOS | DMN2056U-7 | 2.5 V 栅压有 Rds(on) 保证；100 Ω 栅阻、100 kΩ 下拉 |
| 软件测温 NTC | NTCG163JF103FT1 | 10 kΩ ±1%；B25/50=3380 K typ、B25/85=3435 K，固件用原厂 R/T 表或校准，不能用一个 B 值当全温区精确模型 |
| 独立温控 | TMP302ADRLR + TPS22919DCKR | 60°C 动作、10°C 回差，独立切断加热高边电源；不依赖 MCU 或 PWM MOS 正常 |
| 加热器 | 4×200 Ω 1% 1206 ≥0.25 W | 并联 50 Ω；5.25 V/负公差下约 0.557 W，总电流约 106 mA；温升和电阻降额待实测 |
| 核心复位监控 | TPS3808G33DBVR | 监控 3.3 V，CT 悬空采用约 20 ms 延时；RESET 开漏并入 NRST |
| 3V3_AUX 支路 | TPS2553DBVR-1 + 45.3 kΩ 1% ILIM | 500 mA 设计负载；最差限流估算约 519–644 mA，典型约 577 mA；短路锁断，手动复位支路 |
| USB ESD / VBUS | USBLC6-2SC6 / SN74LVC1G17DBVR | 自供电 USB；VBUS 只检测，不回灌 5V_IN |
| SD/I2C掉电隔离 | SN74CB3Q3245PWR + TPS3808G33DBVR | AUX电源有效后导通，掉电高阻 |
| microSD | DM3AT-SF-PEJM5 | 通用验证板，带卡检测；卡本体需限定实测峰值电流 |
| NOR | W25Q128JVPIQ | MEMORY_LOGGER 专用装配，默认验证板不装 |
| 两组板间连接器 | TFM-125-02-L-D-A-TR / SFM-125-02-L-D-A-TR | 1.27 mm、每组2×25；v0.9.2已核对实际针序和6.30 mm插合高度；板轮廓/固定孔/装配仍需签核 |

USB-C 首选 GCT USB4105-GF-A 系列方案，但本轮未取得可核对的完整厂商机械图，**不把该焊盘库列为已冻结**；原理图按 Type-C 引脚名称连接。LSE 首版不装，因此没有为不影响首版的可选晶体虚构订货号。电阻、电容依电压/容差/封装/有效电容量规范建立 AVL，不能用“标称 10 µF”替代直流偏压后的有效电容核对。

辅助电源从原规划 200 mA 改为 **500 mA 设计目标**，两个触点合计。BASE-DBG 的 RS-485、SD、逻辑电路统一由这一路供电，不再引入并联的底板 3.3 V 电源。初步分配：TF 卡峰值 ≤250 mA，四路 RS-485 同时驱动及静态 ≤160 mA，其他逻辑/指示 ≤40 mA，留 50 mA 余量。这些是选卡/实测限额，不是从典型电流推导的保证值；超出则拆分独立供电扩展板并加电平隔离。TPS2553 有反向保护但不是理想瞬时阻断，禁止外部对 AUX 反向供电。

## 5. 来源和实现边界

- [DS13312 Rev4](https://www.st.com/resource/en/datasheet/stm32h735ag.pdf)：p118 电压/频率；p153–156 PLL；本地 [数据手册](../技术依据/clock-dma-review/DS13312.pdf)。
- [RM0468 Rev3](https://www.st.com/resource/en/reference_manual/rm0468-stm32h723733-stm32h725735-and-stm32h730-value-line-advanced-armbased-32bit-mcus-stmicroelectronics.pdf)：p161 Flash；内存与 RCC；p582/585 DMA；§61 三路 FDCAN 共用 RAM，p2516 容量与 word 地址；本地保留关键页摘录和原下载 SHA256。
- [ST H735 ADC DMA 示例](https://github.com/STMicroelectronics/STM32CubeH7/blob/master/Projects/STM32H735G-DK/Examples/ADC/ADC_DMA_Transfer/Src/stm32h7xx_hal_msp.c)、[HAL RCC](https://github.com/STMicroelectronics/stm32h7xx-hal-driver/blob/master/Inc/stm32h7xx_hal_rcc_ex.h)：实际 DMA 请求与 mux；下载快照有 SHA256，尚未绑定最终应用使用的 CubeH7 版本。
- [Epson 精确订货规格](https://download.epsondevice.com/td/pdf/td_spxo_spso_mhz/SG-210STF_X1G0041710015_en.pdf)、[TMP302](https://www.ti.com/lit/ds/symlink/tmp302.pdf)、[TPS22919](https://www.ti.com/lit/ds/symlink/tps22919.pdf)、[TPS3808](https://www.ti.com/lit/ds/symlink/tps3808.pdf)、[TPS2553](https://www.ti.com/lit/ds/symlink/tps2553.pdf)、[TDK NTC](https://product.tdk.com/en/search/sensor/ntc/chip-ntc-thermistor/info?part_no=NTCG163JF103FT1)。

正式固件开始时须锁定 CubeH7/HAL/FreeRTOS 版本、编译器和 linker script，并逐项评审 [ES0491](https://www.st.com/resource/en/errata_sheet/es0491-stm32h72xx73xx-device-errata-stmicroelectronics.pdf)。本轮没有现成 H723 应用工程可迁移，也没有声称这份设计配置已经编译运行。
