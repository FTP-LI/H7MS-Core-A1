# 四款参考控制板独立归档

日期：2026-09-15。每块板独立ZIP，内含原始资料、预览、评估及校验清单；全部ZIP通过CRC及逐文件SHA-256验证。

[共性需求与结论快照](synthesis.md) · [机器可读归档索引](archive-index.json) · [仓库资料与评估入口](../../references/control-boards/2026-09-15/README.md)

| 对象 | 归档 | 内容文件数 | 校验 |
| --- | --- | --- | --- |
| DJI RoboMaster A型 | [DJI-A_2026-09-15_reference-review.zip](DJI-A_2026-09-15_reference-review.zip)（4.93 MiB） | 20 | [SHA-256](DJI-A_2026-09-15_reference-review.sha256) / [清单](DJI-A_2026-09-15_reference-review.manifest.json) |
| DJI RoboMaster C型 | [DJI-C_2026-09-15_reference-review.zip](DJI-C_2026-09-15_reference-review.zip)（4.63 MiB） | 29 | [SHA-256](DJI-C_2026-09-15_reference-review.sha256) / [清单](DJI-C_2026-09-15_reference-review.manifest.json) |
| 达妙DM-MC02 | [Damiao-DM-MC02_2026-09-15_reference-review.zip](Damiao-DM-MC02_2026-09-15_reference-review.zip)（4.03 MiB） | 17 | [SHA-256](Damiao-DM-MC02_2026-09-15_reference-review.sha256) / [清单](Damiao-DM-MC02_2026-09-15_reference-review.manifest.json) |
| D_MAIN_2558 | [D_MAIN_2558_2026-09-15_reference-review.zip](D_MAIN_2558_2026-09-15_reference-review.zip)（3.90 MiB） | 32 | [SHA-256](D_MAIN_2558_2026-09-15_reference-review.sha256) / [清单](D_MAIN_2558_2026-09-15_reference-review.manifest.json) |

内容文件数不包含包内MANIFEST.json。ZIP解压后从README.md进入；单板原始资料与评估链接在包内可用。原始PDF/DXF/官方ZIP未改动，评估和索引仅重定位链接。来源仍在sources/source-index.json，A型原理图的第三方镜像身份明确保留。

先校验ZIP自身SHA-256，再核对清单内每个文件大小与哈希。包内/包外manifest相同；清单不把自身作为内容项。哈希用于一致性检查，不等于厂商数字签名或硬件验收。

综述快照单独保存，哈希记录在archive-index.json；其跨板链接指向仓库位置，完整离线资料按本页四个ZIP查阅。本次快照不覆盖原有2026-09-11 Docs v0.7.1文档包，亦非H7MS生产发布包。后续修改使用新日期/修订，不静默覆盖本批ZIP。
