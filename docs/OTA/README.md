# OTA 调研

2026-10-12 · 对象：H7MS-Core-A1 / STM32H735VGH6 + Direct SMPS · 状态：方案建议，尚无固件实现或断电实测。

**当前硬件具备实现 OTA 的基础，建议采用“Linux 上位机联网 + USB/UART 下发 + W25Q128 暂存 + MCU Bootloader 校验、安装和回退”。**不必为此更换主控或增加 ESP32，三路原生 CAN、IMU、四组设备串口等现有资源保持原规划。

H735 的 1 MiB 内部 Flash 是单 Bank，不能照搬双 Bank 无停机更新。W25Q128 的 16 MiB NOR 可以保存候选固件和恢复副本，但它不会增加运行 RAM，也不会自动带来断电恢复能力。下载可设计为低优先级后台任务；**内部 Flash 安装、试启动和回退必须进入停机维护阶段**。芯片依据见 [ST 数据手册 §3.3.1](https://www.st.com/resource/en/datasheet/stm32h735ig.pdf)及 [ST H7 产品手册](https://www.st.com/resource/en/brochure/brstm32h7.pdf)，具体工程推导见下列文档。

| 文档 | 阅读目的 |
| --- | --- |
| [主流 OTA 方案对比](主流OTA方案对比.md) | 分清联网方式、存储更新策略、MCU 框架与 Linux 更新工具 |
| [H7MS 可行性与推荐架构](H7MS_OTA可行性与推荐架构.md) | 现有接口如何复用，上下位机各做什么，失败后如何恢复 |
| [分区与实施验证计划](分区与实施验证计划.md) | 容量预算、框架移植难点、升级包内容、分阶段验证 |
| [资料来源](资料来源.md) | 原厂/项目官方来源、版本与获取范围 |

首版范围建议只更新 **MCU 应用固件**，采用完整镜像；Bootloader、Option Bytes 和分区表不进入首版远程更新范围。优先做 MCUboot 移植验证，暂不冻结框架、最终地址及 Bootloader 大小。树莓派系统自身更新另行评估 RAUC、Mender 或 SWUpdate。

返回：[资料总索引](../README.md) · [H7MS 设计入口](../H7MS/README.md)。
