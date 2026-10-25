# H7MS-Core-A1

工程入口：[当前原生工程](hardware/easyeda-pro/H7MS-H735-R4B.epro) · [硬件文件索引](hardware/easyeda-pro/README.md) · [原理图 PDF](hardware/easyeda-pro/review-native/H735-native-layout-review.pdf) · [2026-10-25 完整上传与校验清单](archives/2026-10-25_repository-upload/README.md)。全部设计资料和历史快照保留在仓库内；HTML 核验页需下载后本地打开。

2026-10-17 R4B，核心板原生原理图为11页、212器件：四组核心UART、四路自定义GPIO排针、三路直立GH CAN、直立USB和XT30宽压电源。740个引脚与封装/连接计划已逐项核对。查看[当前核验结果与预览](hardware/easyeda-pro/review-native/H735-review.html)，其中列明原生DRC剩余结果与待验证项目。PCB仍为旧137器件草案，不能用于当前方案制造。

当前引脚、接口和器件以[R4B核验入口](hardware/easyeda-pro/review-native/H735-review.html)及所链接CSV为准。所有板仍要求≤40×40mm；核心在下、扩展在上并开窗避让插拔。旧v0.9.3的100触点、SPI4 IMU、下挂扩展布局及并发应用配置已被本轮修订，不得混用。

> 2026-10-13 v0.9.1进展：[时钟/DMA与原理图连接设计](docs/H7MS/工程规划/时钟DMA与关键器件定版.md) 已补充，含480 MHz配置、CORE/BASE-DBG接线及静态检查；真实EDA/ERC和样机验证尚未执行。
H735 通用机器人实时控制平台，采用核心板与应用扩展板。历史Docs v0.9 draft保留追溯；核心板已进入原生EDA布局阶段，尚无已验证应用固件或实测性能。

**核心板优先保证三路 CAN 物理接口、BMI088、IMU 加热和一个 USB。**主控 STM32H735VGH6，TFBGA100、0.8 mm 球距、Direct SMPS。应用扩展通过明确的引脚配置实现，不将不同配置的资源数量相加。

| 资源层 | 当前规划 |
| --- | --- |
| 核心必需 | 三 FDCAN及三路GH口；SPI1 BMI088；加热/NTC/独立过温禁止；直立USB FS；USART1/2/3/6；SPI3/I2C2；四GPIO排针 |
| 核心最小系统 | XT30 12–48V→5V→3.3V→Direct SMPS；HSE、SWD/BOOT0/NRST、电源监测；宽压电源尚待实测 |
| 灵活扩展 | 两组30触点；另外7组UART、16个可复用GPIO、三CAN总线、电源及复位；旧应用配置需重新评估 |
| 多 MCU | 跨部位 RS-485；同底板 SPI3；各节点本地闭环和独立超时 |
| 已检查配置 | 本次100球AF与网表一致性；时钟/DMA、全串口并发和实物电气尚未验收 |

资源以[R4B 100球表](hardware/easyeda-pro/R4B_主控100球与资源分配.csv)和[核心/B2B针序](hardware/easyeda-pro/R4B_核心接口与板间针序.csv)为准。USB为12 Mbit/s FS；核心没有外部NOR/RAM。B2B已改为两组30触点，旧50触点接口不兼容。

- [当前工程规划入口](docs/H7MS/工程规划/README.md)
- [核心板与扩展板总体规划](docs/H7MS/工程规划/核心板与扩展板总体规划.md)
- [引脚复用和应用配置](docs/H7MS/工程规划/引脚复用与应用配置.md)
- [全部片上与外围资源汇总](docs/H7MS/工程规划/片上与外围资源汇总.md)
- [实施步骤与验收矩阵](docs/H7MS/工程规划/实施步骤与验收矩阵.md)
- [100球规划](docs/H7MS/工程规划/100球连接规划.csv) / [外围候选BOM](docs/H7MS/工程规划/外围资源与候选BOM.csv)
- [项目状态](docs/H7MS/项目管理/项目状态与待办.md) / [参考板与历史文档](docs/README.md)

首发顺序为CORE＋BASE_CAN，再制作BASE_485、BASE_LINK、BASE_IO；RM实际应用板按启用功能另做并发验收。静态引脚和EXTI检查通过不代表时钟、DMA、控制性能或电气验收通过；下一步闭合核心板生产叠层和布线，同时建立CubeMX与扩展板原生工程。

旧v0.8引脚/接口表保留为历史输入，不能用于新版制造。OTA仍是方案研究，外部NOR暂存须配合适用的存储扩展板；无外部存储时基本启动/恢复依赖片内Flash与调试接口。
