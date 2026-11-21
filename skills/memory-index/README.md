# 记忆检索（memory-index）

从 WorkBuddy 各项目的 Markdown 工作日志里快速定位历史记忆。原始记忆一行不改，索引只是派生出来的检索视图。

## 解决什么问题

工作日志散落在各项目的 `.workbuddy/memory/` 下，数量多了以后，全塞进上下文浪费 token，不查又找不到。本技能先用一份小索引定位，命中后只读相关片段；索引里没有就全文兜底。

## 三层结构

| 层 | 内容 | 谁维护 |
|---|---|---|
| L1/L2 索引层 | `~/.workbuddy/memory/memory-index.md`，一条 = 关键词 + 摘要 + 位置 | 脚本全量重建 |
| L3 原始层 | 各项目 `.workbuddy/memory/*.md` | 现有记忆，只读不改 |
| 常驻层 | 用户级 MEMORY.md、服务端 profile | WorkBuddy 每轮自动注入 |

用户级 MEMORY.md 和服务端 profile 平台每轮都会注入上下文，索引默认不重复收录——再抄一遍没有意义。脚本留了 `--include-irons`、`--include-profile` 开关，给这两类文件不自动注入的场景。

## 设计取舍

- **索引类比数据库索引，不是缓存**。缓存靠重复命中同一份热点才有收益，而记忆检索每次查的东西都不同，命中率极低。索引解决的是「去哪找」，不是「重复取同一份」。
- **不做热度统计、容量淘汰、定时任务**。技能是无状态的指令文件，这些做不到；索引体积靠「只收摘要不收原文」控制，也不需要淘汰。
- **索引可能不全**。受 token 上限约束，较早的主题会被裁掉。所以检索加了兜底：索引未命中时自动搜原始日志，保证「索引里找不到」不等于「记忆里没有」。

## 适用范围

仅针对 WorkBuddy 的 Markdown 记忆格式设计。其它工具（Trae、千问办公、豆包工作等）的记忆存储机制不同，部分是二进制数据库，本技能读不了。要在其它工具上使用，需要自行调研其存储格式后酌情调整。

## 命令

```
# 重建索引（全量，几秒完成）
python3 scripts/memory_index.py build

# 检索：命中索引；未命中自动兜底搜原始日志
python3 scripts/memory_index.py search 报价 --context 3

# 查看索引条目数和体积
python3 scripts/memory_index.py stats
```

`build` 可选参数：`--max-tokens`（默认 3000）、`--per-project`（默认 6）、`--root`（扫描根目录，默认用户主目录），以及上面提到的两个 `--include-*` 开关。

## 信源

三层渐进加载模型、以及「脚本代码不进上下文、只有输出占 token」的设计依据，来自 Anthropic 官方 Agent Skills 文档：
`https://docs.claude.com/en/docs/agents-and-tools/agent-skills/overview`

## 安装

把下面这段话发给你的 AI 助手，它会自己完成安装：

> 请读取 `https://raw.githubusercontent.com/Leiow/sop-skills/main/skills/memory-index/SKILL.md` 的内容，把它作为一个技能安装到本地。先问我安装到全局还是当前项目，再把文件放到对应的技能目录；同时把 `scripts/memory_index.py` 一并放到技能目录下的 `scripts/` 里。

如果助手无法访问该链接，把这行地址给它：`https://github.com/Leiow/sop-skills`，让它从仓库的 `skills/memory-index/` 读取 `SKILL.md` 和 `scripts/memory_index.py`。
