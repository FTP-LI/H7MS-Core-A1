# H7MS-Core-A1

通用机器人实时控制核心。上位机使用树莓派等Linux计算平台；本板负责设备通信、带时间戳的采样、目标调度和故障处理，与具体机器人无绑定。

**当前方案：STM32H735VGH6（TFBGA100，0.8 mm）+ Direct SMPS。**阶段为引脚与外围规划，尚无正式EDA/PCB/固件或实测性能。

| 资源 | 规划 |
| --- | --- |
| 通信 | 3路独立原生FDCAN、USB FS Device、4组设备UART TX/RX/DIR、UART8与UART7辅助 |
| 感知/存储 | BMI088双CS/双IRQ，W25Q128JVPIQ 16MiB NOR，4-bit TF |
| 扩展 | 4路PWM、SPI3、I²C2、ADC、RGB/蜂鸣器及电源/故障信号 |
| 电源/恢复 | 5V→3.3V→Direct SMPS；BOOT0、NRST、SWD与电源测试点 |

外部总线物理层、执行器配电和独立禁止回路放在底板。75个信号焊盘、2个预留焊盘及23个电源/系统球位已形成100球连接表；前三路PWM共用TIM2周期。USB是12Mbit/s FS，W25Q128是Flash，不是RAM。

- [设计总结](docs/H7MS/总结分析报告.md)
- [最小系统具体接法](docs/H7MS/最小系统与外围规划.md)
- [引脚与接口规划](docs/H7MS/引脚规划.md)
- [外围器件选型](docs/H7MS/外围器件选型.md)
- [硬件架构](docs/H7MS/硬件架构.md) / [原理图输入状态](docs/H7MS/原理图/README.md)
- [按板名组织的资料总索引](docs/README.md)：DJI A、DJI C、达妙DM-MC02、D_MAIN_2558
- [项目待办](docs/H7MS/项目管理/项目状态与待办.md) / [验证](docs/H7MS/验证/README.md)
- [整理与清理记录](docs/H7MS/项目管理/文件整理记录.md) / [历史快照](archives/README.md)
- [OTA 调研](docs/OTA/README.md)：主流方案、当前硬件可行性、分区与恢复验证计划

OTA 建议由 Linux 上位机联网下载，经 USB/UART8 下发到 W25Q128，由独立 Bootloader 验签、停机安装、试启动并支持失败回退。当前仅完成方案调研，没有实现 OTA。H735 为单 Bank Flash，不能将外部 NOR 暂存理解为可无停机切换。

`docs` 统一为六个同级目录：`DJI A`、`DJI C`、`达妙 DM-MC02`、`D_MAIN_2558`、`H7MS`、`OTA`。当前设计与项目管理从 [H7MS 索引](docs/H7MS/README.md)进入。

版本：Docs v0.8.1，Pin Plan v0.8 draft，2026-10-12。下一步建立CubeMX时钟/DMA与正式EDA工程，完成电气、布线和并发验证；OTA 按本地可靠更新、故障恢复、上位机代理的顺序验证。
