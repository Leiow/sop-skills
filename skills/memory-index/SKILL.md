---
name: memory-index
description: "记忆检索：从 WorkBuddy 各项目的 Markdown 工作日志里定位并取回历史记忆。当用户要『查之前记录的 XX』『某项目当时怎么定的』『找一下关于 XX 的记忆』『记忆太多找不到』『刷新记忆索引』『这个决定之前讨论过吗』，或需要回忆跨项目的历史结论、踩坑、客户信息、技术决策时使用。触发词：记忆检索、查记忆、找记录、历史结论、之前说过、刷新记忆索引。"
license: Apache-2.0
metadata:
  version: "1.0"
  origin: "2026-11 为 WorkBuddy 的 Markdown 记忆设计。"
---

# 记忆检索（memory-index）

脚本在本技能目录 `scripts/memory_index.py`，下称 `<SCRIPT>`。

## 检索

1. 关键词快速匹配：`python3 <SCRIPT> search <关键词>`
2. 命中后取原文：`python3 <SCRIPT> search <关键词> --context 3 --limit 3`，按输出的 `路径:行号` 读片段，带进回答。
3. 索引未命中时脚本会自动搜原始日志，兜底命中同样加 `--context` 取片段。
4. 索引和原始日志都没有，就答没有这条记录，建议换个关键词。

## 刷新

记忆有更新、或用户说「刷新记忆索引」时执行：

```
python3 <SCRIPT> build
```

参数：

- `--max-tokens N`：索引 token 上限，默认 3000
- `--per-project N`：每个项目最多收录的主题数，默认 6
- `--root PATH`：扫描根目录，默认用户主目录
- `--include-irons`、`--include-profile`：连用户级铁律和服务端 profile 一起收录（默认不收，这两类平台已自动注入上下文）

全量重建，不改动原始记忆文件。
