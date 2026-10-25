# H735 原生工程文件索引

## 当前设计：R4B

| 文件 | 用途 |
| --- | --- |
| [H7MS-H735-R4B.epro](H7MS-H735-R4B.epro) | 当前嘉立创EDA原生工程；内含符号、封装、11 页原理图和旧 PCB |
| [review-native/H735-review.html](review-native/H735-review.html) | 当前核验、原理图预览、器件与连接表的总入口；下载后本地打开 |
| [review-native/H735-native-layout-review.pdf](review-native/H735-native-layout-review.pdf) | 11 页独立几何预览，便于在线阅读；不代替 EDA 原生检查 |
| [R4B_当前核心板BOM.csv](R4B_当前核心板BOM.csv) | 当前核心板 BOM，含封装 UUID 和装配说明 |
| [R4B_主控100球与资源分配.csv](R4B_主控100球与资源分配.csv) | MCU 球位、信号与复用资源 |
| [R4B_核心接口与板间针序.csv](R4B_核心接口与板间针序.csv) | 核心接口及两组 30 触点板间接口 |
| [R4B_电源预算.csv](R4B_电源预算.csv) | 电源设计分配，尚非实测结果 |
| [core-interface-revision.json](core-interface-revision.json) | 当前 R4B 器件和连接修订输入，与旧规划合并使用 |
| [native-CORE-netlist.json](native-CORE-netlist.json) | 当前导出的核心板网表 |
| [native-state.json](native-state.json) | 原生工程页和器件标识，供现有脚本定位 |
| [native-footprint-verification.json](native-footprint-verification.json) | 212 器件 / 740 引脚、封装及连接静态核验 |
| [native-drc-result.json](native-drc-result.json) | 当前原生 DRC 结果：1 组告警，API 未提供明细 |
| [官方封装核对与例外.csv](官方封装核对与例外.csv) | 官方封装来源和必要的本地修正记录 |

当前 `.epro` 的 SHA-256：`55bca24ce3e6424bbf2981897a3fd1778aafae92e22d139977f574c39f695adc`。

核心板为四组 UART、四路自定义 GPIO 排针、三路三针直立 GH CAN、SPI3、I2C2、直立 USB、XT30 12–48 V 稳压电源输入。核心板在下、扩展板在上，全部板不超过 40×40 mm；扩展板须为核心接口插拔留出空间。这些是当前设计约束，尚不能据此声称 PCB 装配或电源热性能已经验证。

## 历史与辅助资料

| 路径或文件组 | 状态 |
| --- | --- |
| [source-backup/](source-backup/README.md) | 历次导出、恢复点、库检查工程；保留追溯，不按文件名中的 final 自动判定当前版本 |
| `H7MS-H735-A1-Schematic-Draft.epro`、`H735-draft/`、`review/` | 早期生成/导入草案，已由 R4B 原生工程取代 |
| `pcb-*.json`、`review-native/CORE.epcb`、`review-native/PCB-*` | 旧 PCB 同步/布局阶段记录，未反映 R4B 的 212 器件方案 |
| `compact-*`、`module-*`、`functional-*`、`*-before*` | 各整理阶段快照与旧布局输入 |
| `api-*`、`direct-*`、`routing-*`、`revision-*` | 原生 API 检查、连接和修订过程记录，需结合当前版本索引判断用途 |
| `reference-pdfs/`、`research/`、`*library*.json` | 器件图纸、格式研究和官方库核对证据，保留原文件与来源 |

## 脚本使用范围

本次上传没有运行编辑器修改脚本，也不需要打开或切换嘉立创EDA工程。

- `audit_native_footprints.py`：读取已导出工程、当前网表与连接计划，生成静态核验文件。
- `native_preview.py`、`build_revision_review.py`：生成几何预览和核验页面；会覆盖对应输出，预览脚本依赖 PyMuPDF。
- `native_design.py`：组合旧规划与已启用的 R4B 修订；单独使用旧 CSV 不能还原当前设计。
- `eda_bridge.py`、`capture_native_review.py`、`apply_interface_parts.py`、`layout_interface_revision.py` 及修复脚本：依赖本机桥接服务和指定工程/窗口。窗口标识为历史会话记录，继续编辑前须重新核对目标，不能对其他工程直接运行。
- `plan_interface_revision.py`、`plan_hv_revision.py`、`generate_schematic.py`、`functional_layout.py`、`module_compact.py`、`sync_pcb.py`、`pcb_placement.py` 等保留设计过程；并非可按名称顺序重跑的构建流水线，其中有旧接口、旧器件数量或一次性迁移假设。

完整仓库的文件校验清单见[上传归档说明](../../archives/2026-10-25_repository-upload/README.md)。
