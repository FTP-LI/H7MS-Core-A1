# 紧凑主控选型证据

日期：2026-10-11。结论见[docs/18](../../对比与研究/小型化与高资源主控综合建议.md)。

v0.7.12补充：新增H735VGHx与H735IGKx两个官方XML、各62个候选信号及检查，现共六套封装数据。K230官方0.65 mm球距及用户暂定下限已记录；0.5 mm方案保留为研究背景。IGK的XML包名UFBGA176对应官方176+25机械封装，CSV不是完整焊球网表。

- 四个XML原样来自ST官方STM32_open_pin_data；下载链接及SHA-256见[source-index.json](source-index.json)，附原BSD许可证。
- 数据手册在线核对：H723 DS13313 Rev 5、H725 DS13311 Rev 5、H735 DS13312 Rev 4。本目录未保存新的PDF或完整网页，不宣称完整离线手册归档。
- AF数据复用[上轮归档](../pin-resource-review/README.md)，四个器件XML均引用同一GPIO版本。
- [BGA候选CSV](../../对比与研究/候选引脚/STM32_compact_BGA_interfaces.csv)从既有VGT接口需求迁移，列出精确球位。H723ZGI6的可选NTC改为PF10/ADC3_INP6，其余三个保留PC3_C/ADC3_INP1。每个器件62个不同焊盘，供研究，不是完整电源网表或冻结针序。
- USB专用PHY的信号引出已核对；CSV中的AF10沿用H723官方示例，检查脚本不声称独立验证H725/H735的USB初始化，最终仍需精确型号固件配置。
- [quotes.json](quotes.json)记录在线页面文本返回的美元价格/库存，不是下单报价；与此前中国站人民币报价的地区、税费和交付条件不同。

在仓库根目录运行：

```powershell
python H7MS-Core-A1/docs/H7MS/技术依据/compact-mcu-review/check_compact_candidates.py
```

本检查只覆盖封装/外设信号/普通AF/占脚与EXTI一致性。未进行CubeMX、BGA扇出、电气、电源、温升、全部勘误或混合负载验证；H725与H735球位名称一致也不等于已通过BOM替代认证。N657Z0仅核对紧凑封装方向，未包含在CSV中。
