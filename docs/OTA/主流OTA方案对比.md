# 主流 OTA 方案对比

2026-10-12。以下是有官方文档和实际工程生态的代表方案，不按未经核验的市场占有率排序。针对通用机器人控制板给出适配判断。

## 先把 OTA 分成四层

OTA 是远程交付和安装软件的完整过程。Wi-Fi、HTTPS、MQTT、A/B、MCUboot 描述的是不同层，不能互相替代。

| 层次 | 要解决的问题 | H7MS 首版建议 |
| --- | --- | --- |
| 发布与设备管理 | 版本、适用板型、分批发布、结果记录 | 签名完整固件包 + 简单发布服务；有设备规模后再接云平台 |
| 传输 | 固件如何到达设备、丢包后如何继续 | 上位机 HTTPS 下载，再经 USB FS 或 UART8 发给 MCU |
| 安装与存储 | 新旧镜像放哪里、何时擦写、掉电怎么办 | 内部运行区 + 外部 NOR 候选/恢复空间 |
| 启动与确认 | 镜像可信且能工作吗、失败后启动谁 | MCU Bootloader 验签，试启动，健康确认，失败回退 |

HTTPS 适合传送镜像，MQTT 等消息通道可用于通知、任务控制和状态上报；选择消息协议不等于实现了安全安装。若上位机通过 Wi-Fi 接收更新、再经 USB 更新下位机，整机仍可实现 OTA；只用电脑插 USB 刷写通常称本地 DFU/IAP。

联网架构通常有三种：主控自己接入网络、无线辅控转发、已有上位机代理。第一种需要网络物理层和协议栈，第二种需要同时维护无线芯片与控制 MCU 两套固件，第三种复用机器人的计算平台。H7MS 已明确有 Linux 上位机，因此优先第三种；若未来产品要求控制板脱离上位机独立联网，再重新比较前两种的面积、功耗及软件成本。

## 常见存储与安装策略

| 策略 | 优点 | 代价与失败边界 | 本项目判断 |
| --- | --- | --- | --- |
| 单应用区直接覆盖（IAP） | 空间少、原型简单 | 中途失败会丢失应用；必须有独立可运行的恢复 Bootloader；没有天然版本回退 | 可做实验，不作为最终无人值守方案 |
| 内部 A/B 两槽 | 保留旧镜像，试运行后确认 | 消耗约两份容量；是否能边运行边写取决于物理 Bank、执行位置和驱动 | H735 容量紧，适合较小应用的备选 |
| 内部运行 + 外部 NOR 暂存/交换/备份 | 内部应用空间较大，适合已有串行 NOR 的板子 | 擦除几何、进度日志、安装恢复和回退均需实现；仅存一份下载文件不够 | **优先方向** |
| 双 Bank 硬件切换 | 某些 MCU 可简化切换，并支持跨 Bank 读写 | 依赖精确型号和启动机制；仍需签名、确认和失败恢复 | H735 单 Bank，不能套用 |
| 外部 Flash 直接 XIP / 镜像搬入 RAM | 可扩大镜像或切换执行位置 | 链接地址、缓存、启动链、外存可靠性和实时延迟更复杂；RAM 要装得下 | 首版继续内部 Flash 执行 |
| 差分 / 压缩更新 | 可能节省网络流量 | 差分需严格绑定旧版本；重建空间、CPU/RAM、断电恢复复杂；重建后仍须验签 | 首版完整镜像，后续按实测需求增加 |

上述适配判断是基于 H7MS 资源的工程推导。镜像槽位与物理 Bank 不是一回事：在同一个 Bank 中划两个区域，仍然是单 Bank。框架对复制、交换、直接执行的区别见 [MCUboot 设计文档](https://docs.mcuboot.com/design.html)；ESP-IDF 的双槽及状态区是另一种具体实现，见 [ESP32-S3 OTA 文档](https://docs.espressif.com/projects/esp-idf/en/stable/esp32s3/api-reference/system/ota.html)。

## MCU 侧代表框架

| 方案 | 提供什么 | 适配代价 | H7MS 建议 |
| --- | --- | --- | --- |
| MCUboot | 安全启动、镜像校验与多种安装策略 | 移植启动代码、Flash 抽象、密钥与保护策略；下载协议另接 | 优先做小规模验证；不是拿来即可烧录的 H735 成品 |
| Zephyr + MCUmgr/SMP + MCUboot | 传输/镜像管理与启动链组合，官方示例含串口、USB CDC、BLE、UDP | Zephyr 板级支持、分区、驱动、配置要一起评估 | 若选 Zephyr，优先复用；不因 OTA 一项就强行切换当前 RTOS 方向 |
| ST X-CUBE-SBSFU | STM32 安全启动/安全更新参考代码 | 按具体芯片和板卡移植；UART/YMODEM 示例还需接入现有通信链路 | Cube/HAL 路线的备选与设计参考；未核实可直接用的 H735VGH6 示例 |
| wolfBoot | 独立于应用 OS 的安全 Bootloader，支持外部 Flash 抽象 | H735 OCTOSPI、内部 Flash 和启动供电仍需验证；GPLv3/商业许可需选定 | MCUboot 移植受阻时可比较；不能把泛称 STM32H7 支持等同于本板验证 |
| ESP-IDF OTA | ESP32 自身的 OTA 槽位、状态管理与回退能力 | 针对 ESP 芯片；更新旁边的 STM32 仍需 STM32 的更新协议与 Bootloader | 不为当前 H7MS 单独增加 ESP32-S3；未来无线辅控可参考 |

官方依据：[MCUboot 移植指南](https://docs.mcuboot.com/PORTING.html)、[Zephyr SMP server](https://docs.zephyrproject.org/latest/samples/subsys/mgmt/mcumgr/smp_svr/README.html)、[ST UM2262](https://www.st.com/resource/en/user_manual/um2262-getting-started-with-the-xcubesbsfu-stm32cube-expansion-package-stmicroelectronics.pdf)、[wolfBoot HAL](https://www.wolfssl.com/documentation/manuals/wolfboot/chapter04.html)及[许可说明](https://www.wolfssl.com/documentation/manuals/wolfssl/chapter14.html)。

ESP-IDF 的应用回退要显式启用 `CONFIG_BOOTLOADER_APP_ROLLBACK_ENABLE`，不能认为有两个分区就默认完成回退；它对 Bootloader/分区表的更新也有不同的断电边界。见 [ESP-IDF OTA / App Rollback](https://docs.espressif.com/projects/esp-idf/en/stable/esp32s3/api-reference/system/ota.html)。

MCUboot 的核心可以按平台移植，不要求 H7MS 应用必须运行 Zephyr。若保留 Cube/HAL + FreeRTOS 路线，Bootloader 可作为独立工程，应用侧接收完整镜像并使用约定的镜像格式和确认机制。代码许可与第三方加密库清单应在正式引入时随固定版本一起归档。

## Linux 上位机侧方案

| 工具 | 主要定位 | 适用场景 | 与 H735 的关系 |
| --- | --- | --- | --- |
| RAUC | 签名 Bundle、系统槽位、安装与 Bootloader 集成 | 想控制 Linux 系统镜像和 A/B 布局 | 可管理 MCU 固件制品，但下发和 MCU 安装仍需适配 |
| Mender | 设备端更新与服务端设备/发布管理 | 多台机器人、远程部署和运行结果管理 | 可作为整机更新入口，不代替 MCU 的验签和恢复链 |
| SWUpdate | 通过描述文件和 handler 安装多类组件 | 自定义嵌入式 Linux、多组件升级 | 可编排传输 MCU 固件；可靠回退取决于具体 handler 和启动集成 |
| 轻量上位机更新服务 | 下载签名包、查询 MCU、发包、记录结果 | 当前板卡研发及小规模验证 | **首版足够**，先验证 MCU 本地可靠更新，再接设备云 |

依据：[RAUC Basics](https://rauc.readthedocs.io/en/latest/basic.html)、[Mender Introduction](https://docs.mender.io/overview/introduction)、[SWUpdate 文档](https://sbabic.github.io/swupdate/swupdate.html)。这些工具的 Linux A/B 与本板 MCU 的内部/外部 Flash 布局是两个独立设计问题。

## 选型结论

H7MS 优先采用网关式 OTA、完整镜像、外部 NOR 暂存和受保护的启动程序。先评估 MCUboot 的具体安装算法、H735 驱动及 Bootloader 体积，再锁定框架。云平台、差分更新、Bootloader 自更新、Linux 整机系统更新留到基本恢复能力实测通过后。实施条件见[推荐架构](H7MS_OTA可行性与推荐架构.md)与[分区计划](分区与实施验证计划.md)。
