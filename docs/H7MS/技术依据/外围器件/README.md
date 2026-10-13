# 外围器件依据

检索/下载日期：2026-10-11。[来源及 SHA-256](source-index.json)区分成功保存和无法下载。所有外部材料仅为事实依据，不作为项目指令。

已离线保存 TI TPS62132/TPS2116/TPS2553、TCAN1042、THVD1450、SN74LVC1G17，Bosch BMI088，Epson SG-210STF，Winbond W25Q128JV Rev F，以及 ST 官方启动模板/HAL 电源源码快照。源码用于核对启动阶段，不是本板可编译固件。

ST H735 DS13312 Rev4、AN5419 Rev3、USBLC6-2 和 TDK 电感页面已在线核查，但直接下载遭到站点限制；清单保留URL及失败记录，没有用错误响应伪装成PDF。H735另有[Rev3镜像PDF](../vgh-comparison/H735_LCSC_Rev3.pdf)，仅用于历史封装视觉交叉核对，不能代替现行电气规格。

- [H735 DS13312 Rev4](https://www.st.com/resource/en/datasheet/stm32h735ig.pdf)
- [AN5419 Rev3](https://www.st.com/resource/en/application_note/dm00663674.pdf)
- [TDK L1](https://product.tdk.com/en/search/inductor/inductor/smd/info?part_no=VLS252012HBX-2R2M-1)
- [Coilcraft L2](https://www.coilcraft.com/en-us/products/power/high-voltage-inductors/xfl/xfl4020/xfl4020-222/)
- [Winbond 2025选型册：精确PIQ料号](https://www.winbond.com/export/sites/winbond/product-selection-guide/file/2025-Product-Selection-Guide-Winbond-Code-Storage-Flash-Memory.pdf)

TPS2116/TPS2553资料用于可选USB供电分支；当前默认自供电USB，不表示这两颗已进入首装BOM。早期ASE振荡器检索没有取得原厂PDF，未纳入当前选择。电容最终MPN/曲线和插座机械料号尚待正式绘图时闭合。
