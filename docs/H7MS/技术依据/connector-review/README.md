# 连接器及485保护依据

2026-10-13从原厂URL下载。来源、原始PDF的SHA256见[sources.json](sources.json)。本目录PDF为外部器件依据，`.txt`和PNG为本地读图辅助，不是自行绘制的封装库。

| 文件 | 用途 |
| --- | --- |
| [USB4105](USB4105.pdf) | Rev B4第1页：16触点、12信号焊盘、壳槽、定位孔与订货后缀 |
| [TFM产品图](TFM-print.pdf) / [焊盘图](TFM-footprint.pdf) | -125-02-L-D-A-TR；器件面Pin1左下，50信号焊盘、2定位孔 |
| [SFM产品图](SFM-print.pdf) / [焊盘图](SFM-footprint.pdf) | 对应母座；器件面Pin1右下，不能复制公座编号 |
| [插合图](mated.pdf) | 第1页Figure1/Table1，-02/-02板面距6.30 mm，最大6.48 mm |
| [SM712](SM712.pdf) | 引脚1/2为线，3为公共地，非对称工作电压、钳位及SOT23焊盘 |
| [CRCW-HP](CRCW-HP.pdf) | Vishay订货编码和抗脉冲系列；选10R0 J N EA HP |
| [JST XH](JST-XH.pdf) / [JST VH](JST-VH.pdf) | 验证板线端、腔号、压接端子、安装孔 |

THVD1450保护参考沿用已保存的[TI数据手册](../外围器件/THVD1450.pdf)第27页Figure37/Table7；该页截图为[THVD-protection.png](THVD-protection.png)。这是TI的5 V例图，不能直接替代本项目3.3 V整板浪涌测试。USB等网页可能拒绝抓取，但本目录PDF均经本地成功下载、识别并查看相应机械图，不把网页错误当作图纸依据。

设计输入及剩余限制见[定版说明](../../工程规划/连接器与RS485保护定版.md)。
