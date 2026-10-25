# 电源与紧凑布局依据

2026-10-16。设计结论见[电源机械与40mm布局定版](../../工程规划/电源机械与40mm布局定版.md)。

[原始来源索引](source-index.json)记录已保存的8份PDF及SHA256。`sources*.json`是下载尝试日志，含403/超时，不能当作全部下载成功。C&K staging曾返回网站落地页的PDF，已识别并删除，没有把它当作数据手册。

| 文件 | 用途 |
| --- | --- |
| [TPS22975](TPS22975.pdf) | WSON脚号、CT与典型斜率、关断放电 |
| [AN5419](AN5419.pdf) | H735 Direct SMPS连接及推荐电容 |
| [Murata特性页](Murata-10u-25V.pdf) | 原厂编制、Farnell保存的2013典型曲线；不是现批次保证下限 |
| [EVQP7](EVQP7.pdf) | 四个实际焊脚/两组触点、按键尺寸 |
| [TC33](TC33.pdf) | 电位器滑臂脚号、调节方向、尺寸 |
| [FTSH焊盘](FTSH-pad.pdf) / [产品图](FTSH-print.pdf) | 1.27 mm SMT头，SWD缺针和不同长度 |
| [JST PH](JST-PH.pdf) | SMT入口、电流对应线规、针序和焊盘图 |

以下通过网页工具读取原厂资料，未成功下载原始PDF，因此不伪造本地哈希：

- [Littelfuse 451/453](https://www.littelfuse.com/assetdocs/fuse-451-and-453-datasheet?assetguid=533cd5cc-956c-4243-867f-6ab5a62f6ba1)：2.5 A条目、连续降额说明、I²t与尺寸。
- [C&K JS](https://www.ckswitches.com/media/1422/js.pdf)：2026版，SC与SA封装区别、公共端2、开关额定值。
- TDK各MLCC规格、Samtec精确型号、Yageo加热电阻：链接在主设计文档中。

本目录的TPS62132、TCAN1042文本/SS截图从仓库[外围器件依据](../外围器件/README.md)的原始PDF提取；DS13312沿用[时钟/DMA依据](../clock-dma-review/README.md)。PNG是读图/复核辅助，不替代原厂PDF。物料状态的检索不代表已询价、下单或有现货保证。
