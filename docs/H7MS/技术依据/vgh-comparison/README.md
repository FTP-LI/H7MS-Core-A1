# H735VGH6与H723VGH6对比证据

日期：2026-10-11；结论见[docs/19](../../对比与研究/H735VGH6与H723VGH6最终候选对比.md)。用户已说明H735有合适的其他采购渠道；扩展按DM/此前H723的功能类别收敛，不要求旧H743完整定时器集合。

## 内容和证据边界

- [quotes.json](quotes.json)：两个精确料号在立创中国站、DigiKey美国站的公开价格阶梯及供货观察，另记录用户采购前提；不是成交凭证或交期承诺。
- [all-100-balls.csv](all-100-balls.csv)：全部100球的名称对照，包含电源/系统脚；用于证明机械封装相同不等于可换料。
- [interfaces-side-by-side.csv](interfaces-side-by-side.csv)：此前62信号方案的逐项球位比较；未包含本轮13项DM扩展。
- [DM功能候选CSV](../../对比与研究/候选引脚/STM32H735_H723_VGH_DM_interfaces.csv)：两型号各75项独立信号，含62项原候选及13项扩展；不是完整连接器针序或原理图网表。
- [pin-audit.json](pin-audit.json)与[dm-pin-audit.json](dm-pin-audit.json)：静态检查结果。前者86信号的旧H743预算仅作历史边界，后者才对应本轮用户范围。
- [lost-pin-impact.json](lost-pin-impact.json)：PE11～PE15功能和H735剩余TIM1/SPI4替代引脚，标注它们在75信号候选中的占用；不表示相关外设从芯片内消失。
- [user_SMPS_Figure17.png](user_SMPS_Figure17.png)：用户提供的图17/表16原图，未修改；两种供电方式、元件含义与VCAP电容区别归纳在docs/19 §4.4。
- [H735_LCSC_Rev3.pdf](H735_LCSC_Rev3.pdf)：ST DS13312 **Rev3，2021-12**镜像，285个PDF页面。来自立创公开附件，不能因为下载URL含20250630就写成2025版。SHA-256和来源见[source-index.json](source-index.json)。
- [previews](previews)：已查看的H735/H723旧版TFBGA100球阵、H735旧版表24电流页。H723原PDF继续引用[已有Rev3归档](../pin-resource-review/H723_LCSC_Rev3.pdf)，不重复复制。

当前技术正文通过ST官网在线核对：DS13312 Rev4（2023-11）、DS13313 Rev5（2025-05）、AN5419 Rev3（2026-01）。本轮未获得这些当前版本的本地PDF文件；这里保存的镜像只用于披露版本的视觉交叉检查，不能声称已完整离线归档最新手册。

封装/AF使用此前已保存的ST官方STM32_open_pin_data XML，源版本、哈希及原许可证见[compact-mcu-review](../compact-mcu-review/README.md)和[pin-resource-review](../pin-resource-review/README.md)。达妙原始资料继续使用[DM独立目录](<../../../达妙 DM-MC02>)，不改写历史ZIP。

## 复现

在仓库根目录依次运行：

```powershell
python H7MS-Core-A1/docs/H7MS/技术依据/compact-mcu-review/check_compact_candidates.py
python H7MS-Core-A1/docs/H7MS/技术依据/vgh-comparison/compare_packages.py
python H7MS-Core-A1/docs/H7MS/技术依据/vgh-comparison/build_dm_candidates.py
```

第三个脚本读取原62信号CSV，生成新的75信号文件，不覆盖原候选。普通GPIO AF按官方数据库验证，专用USB PHY只检查引出；扩展PB5/SPI3_MOSI为AF7。焊盘唯一性和EXTI线占用也会检查。

检查不涵盖CubeMX、时钟、DMA/Cache、电源启动、芯片勘误、模拟精度、PCB布线、连接器、制造与混合负载；`pass`仅表示上述静态一致性。四路PWM分属两个定时器，其中三路共享TIM2周期；SBUS使用辅助串口且须处理反相；DCMI不在并发方案中。
