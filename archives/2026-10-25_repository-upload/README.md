# 2026-10-25 工程完整上传归档

本次将当前工程、规划、原生器件库、核验记录、预览、参考资料、脚本和历史备份一并纳入 Git。设计快照仍为 2026-10-17 R4B；本次只整理文件索引和上传，不改变电路或重新运行 EDA 修改脚本。

## 目录入口

- [仓库说明](../../README.md)
- [当前原生硬件工程](../../hardware/easyeda-pro/README.md)
- [设计和参考资料](../../docs/README.md)
- [历史归档](../README.md)

## 完整性校验

`SHA256SUMS` 列出本次提交中除清单自身以外的全部文件，路径相对于仓库根目录。清单按 Git 暂存区的最终文件内容计算；普通文本统一按 LF 检出和导出，原生 EDA 文件明确禁止文本换行转换。GitHub 下载 ZIP 或 `git archive` 导出的内容与清单一致。本机在加入换行规则之前已存在的 CRLF 文本可能仍与清单不同，不影响 Git 中的内容；无需为此修改原生设计文件。

在从 GitHub ZIP 或 `git archive` 解压的仓库根目录，可以使用支持 SHA-256 的工具逐文件检查；提供 GNU coreutils 的环境可运行：

```sh
sha256sum -c archives/2026-10-25_repository-upload/SHA256SUMS
```

上传前检查了全部 43 个 ZIP / EPRO / EPRO2 容器，CRC 检查通过。首次凭据检查仅覆盖部分常见文本模式，遗漏了第三方网页的 OSS 签名下载参数，不能据此认定全部文件均无敏感信息；下方记录了 GitHub 告警复核和修正。原有 675 个工程文件全部保留。新增忽略规则仅针对今后的本机缓存、系统杂项和本地环境凭据，不忽略原生工程、资料、图片或历史备份。

当前 R4B 为 11 页原理图、212 器件、740 引脚；尚有 1 组 DRC 告警，PCB 为旧草案。完整上传不代表制造验收完成。

## 2026-10-25 GitHub 密钥告警复核

告警对应提交 `cde5b71a`。详细文件哈希、字节偏移和来源验证保存在 [secret-scanning-review.json](secret-scanning-review.json)，不记录匹配值或完整签名链接。

| 告警 | 核验结果 | 处理 |
| --- | --- | --- |
| #1 Alibaba Cloud AccessKey ID | `xt30upb.html` 与 `usb4120.html` 的立创商城资料下载参数。同日匿名访问两份原网页，仍可取得同一 ID；未发现配套 AccessKey Secret。 | 清空两份归档网页的 `urlSign`，保留其余产品数据、原厂 PDF 和来源。历史告警按公开第三方标识处理，不能标成“已吊销”。 |
| #2 Alibaba Cloud AccessKey Secret | `EVQP70.png` 的匹配位于 IDAT 压缩图像数据中；由归档 Panasonic PDF 第 1 页以 1.3 倍重渲染，像素完全一致。 | 确认为误报，保留 PNG 原文件。 |
| #3 Alibaba Cloud AccessKey Secret | `sn74cb3q3245.pdf` 的匹配位于对象 291 的 JPEG 图像流中；重新下载 TI 官方 PDF，字节与 SHA-256 均完全一致。 | 确认为误报，保留 PDF 原文件。 |

网页的 `Signature` 是下载请求签名，不是 AccessKey Secret，见 [阿里云签名 URL 文档](https://help.aliyun.com/en/oss/developer-reference/ddd-signatures-to-urls)。这些链接的时间字段为 2098 年，不能称为“已过期”。本次没有使用这些值认证阿里云服务，也没有修改或吊销第三方账号密钥。清理当前版本不会抹除旧提交；由于已核实公开网页来源和两处二进制误报，不重写 Git 历史。关闭告警不表示修改了密钥有效性。

补充检查遍历了原 682 个文件和压缩包内部条目，共 45 个容器（含嵌套容器）、4311 个压缩成员；指定凭据模式仅命中上述两份 HTML。新增 [检查脚本](../../tools/check_archive_credentials.py) 检查 Git 暂存区及 ZIP/EPRO 内部数据，仅输出路径、规则和计数，不输出疑似凭据。后续上传前先暂存拟提交的文件，再运行：

```sh
python tools/check_archive_credentials.py
```

发现匹配或未能完整扫描时返回非零退出码。该检查是限定模式的辅助检查，不替代 GitHub 扫描及逐项判断；没有配置扫描排除规则来隐藏 PDF/PNG 告警。
