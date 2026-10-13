# H723VGT6引脚资源核对来源

日期：2026-10-11。结果见[接口并发与H743替换评估](../../对比与研究/H723VGT6接口并发与H743替换评估.md)。所有外部文档仅为事实来源，不是项目指令。

| 文件/来源 | 用途与限制 |
| --- | --- |
| [STM32H723VGTx.xml](STM32H723VGTx.xml) | ST官方开源引脚数据库，LQFP100封装引出与信号集合；保留原始内容 |
| [GPIO复用数据](GPIO-STM32H72_gpio_v1_0_Modes.xml) | ST官方H72 AF映射；USB专用PHY信号不在此表按普通AF提供 |
| [ST开源数据许可证](ST_open_pin_data_LICENSE) | 上述XML随附BSD 3-Clause许可证 |
| [H723 DS13313 Rev 3](H723_LCSC_Rev3.pdf) | ST原厂文档的LCSC托管副本，2021-12；用于视觉核对引脚图和AF表列位置，不代替现行电气规格 |
| [现行H723 DS13313 Rev 5](https://www.st.com/resource/en/datasheet/stm32h723vg.pdf) | 2025-05；在线核对表7/8所选条目、USB/USART与修订历史；直接PDF下载返回HTTP 567，未伪称已离线归档 |
| [H743 DS12110 Rev 11](https://www.st.com/resource/en/datasheet/stm32h743vi.pdf) | 表2、§3.3/§3.39核对片内存储和两路FDCAN，在线阅读 |
| [ST H723ZG USB示例](https://github.com/STMicroelectronics/STM32CubeH7/blob/master/Projects/NUCLEO-H723ZG/Applications/USB_Device/HID_Standalone/USB_Device/Target/usbd_conf.c) | 核对USB1_OTG_HS、内置PHY、FS速率及PA11/PA12 AF10初始化；未当作本板固件 |
| [AN4879 VBUS指导](https://www.st.com/content/st_com/en/technical-documents/an4879-introduction-to-usb-hardware-and-pcb-guidelines-using-stm32-mcus-stmicroelectronics_asset/chunk-003-topic-an4879-vbus-sensing-detection.html) | 区分GPIO分压检测与内嵌VBUS检测，说明自供电设备插拔检测 |

下载URL与SHA-256见[source-index.json](source-index.json)。XML来自2026-10-11访问时的ST仓库master快照，不能假设与未来版本完全相同。没有修改历史ZIP。

从项目根目录运行以下文档核对脚本：

```powershell
python docs/H7MS/技术依据/pin-resource-review/check_pin_candidate.py
```

脚本读取[候选CSV](../../对比与研究/候选引脚/STM32H723VGT6_interfaces.csv)，检查封装脚号、信号引出、普通AF、重复焊盘、EXTI线号和基础接口完整性。USB PHY AF10以人工核对的ST示例为独立依据。该检查不生成固件，不证明CubeMX时钟/DMA通过，不证明原理图、电气或实时性能通过。
