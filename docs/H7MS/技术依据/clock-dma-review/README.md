# v0.9.1 时钟、DMA和关键器件证据

2026-10-13采集。来源URL和下载文件SHA256见 [sources.json](sources.json)。PDF和ST源码是技术参考，不是待运行的应用固件。HAL/CubeH7 master的文件保留了内容哈希，但尚未锁定用户应用的工具链/SDK版本。

RM0468完整下载约66 MB，阅读后只保留 [关键页摘录](RM0468-selected-pages.pdf)，避免把整本手册重复放入工程。索引同时记录完整下载哈希、摘录哈希和原书页号，摘录页序不能当原书页号引用。DS13312保留Rev4全文；`stm32h735ag.pdf`是覆盖H735xG系列（包括VGH6）的共同手册。

NTC、CAN TVS、USB机械图曾直接下载失败：前两者已通过原厂网页/可读取的原厂PDF核对，设计文档给出原厂链接；USB机械焊盘仍为待关闭项。失败条目不是已保存或已验证的文件。TXT和PNG是检索/读图的派生文件，不替代原版PDF；`limit-equation.png`用于核对TPS2553限流公式中R使用kΩ单位。

本轮核心结论：PLL1P=1生成480 MHz；ADC3可路由DMAMUX1 request115；三FDCAN共用2560 word；SPI/串口/SD缓冲不能随意放DTCM；加热独立温控和AUX掉电隔离使用准确封装脚号。设计与验收入口见 [工程规划](../../工程规划/README.md)。
