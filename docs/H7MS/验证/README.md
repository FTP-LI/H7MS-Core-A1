# 规划验证

从 `H7MS-Core-A1` 项目根目录执行：

```powershell
python -X utf8 docs/H7MS/验证/validate_plan.py
python -X utf8 docs/H7MS/验证/verify_sources.py
```

脚本对原始 ST XML 检查封装、球位、引出信号、普通 GPIO AF、重复信号及 EXTI 分配；检查三 CAN、四串口、USB/IMU/NOR/SWD 的保留、100 球覆盖、Direct SMPS 电源网络和板间引出。还核查保留的原始 PDF/DXF/XML 未被修改，以及工作文档的本地链接。

输出：[validation-result.json](validation-result.json)。USB 专用 PHY、模拟功能及电气细节仍须结合原厂手册人工复核。

来源校验结果：[source-verification.json](source-verification.json)，覆盖保留文件的 SHA-256 以及已归档条目的 ZIP 成员。迁移改写的 Markdown/Python 保留原始哈希并记录更新；PDF/DXF/XML原图不改写。

这些检查只证明规划数据一致。未运行 CubeMX，没有 EDA 网表/ERC、PCB、示波器或实物并发/恢复测试。待办见[验收计划](../验收计划.md)。

2026-10-12 增加六个同级目录、迁移后未编辑资料哈希及 OTA 预算表的容量/对齐/重叠检查。旧来源路径先按两次迁移记录追踪，历史记录本身不改写。OTA 表格的算术通过不等于 Boot 框架的 Flash map 或掉电恢复通过。
