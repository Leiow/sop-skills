#!/usr/bin/env python3
"""WorkBuddy 记忆索引工具：把散落的 Markdown 记忆整理成可快速检索的三层结构。

三层对应：
  L1/L2 索引层 —— 本脚本生成的 memory-index.md（关键词 | 摘要 | 源文件:行号）
  L3    原始层 —— 现有 Markdown 记忆文件（只读，不改一个字）

子命令：
  build   全量重建索引（扫描用户级铁律、项目级日志、服务端 profile）
  search  在索引里做关键词匹配，输出命中条目，可选带出原文上下文片段
  stats   查看索引条数、体积、token 估算

设计原则：全量重建、原始层零改动、索引是唯一派生数据、脚本代码不进会话上下文。
"""

import argparse
import os
import re
import sys
from datetime import datetime
from pathlib import Path

HOME = Path.home()
DEFAULT_INDEX = HOME / ".workbuddy" / "memory" / "memory-index.md"

# 扫描时剪枝的目录，避免递归进依赖/缓存
SKIP_DIRS = {"node_modules", ".git", "Library", "node_modules", ".venv", "venv", "dist", "build"}


def clean_md(text: str, limit: int = 0) -> str:
    """去掉 Markdown 标记，压缩空白，可选截断。"""
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"\*\*([^*]*)\*\*", r"\1", text)
    text = re.sub(r"\*([^*]*)\*", r"\1", text)
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"\s+", " ", text).strip()
    if limit and len(text) > limit:
        return text[:limit].rstrip() + "…"
    return text


def est_tokens(text: str) -> int:
    """粗略估算 token：中文按 1 字 1 token、其余按 4 字符 1 token。"""
    cn = len(re.findall(r"[\u4e00-\u9fff]", text))
    other = len(text) - cn
    return cn + other // 4


def relpath(p: Path) -> str:
    """把绝对路径转成以 ~ 开头的短路径，索引里可读。"""
    try:
        return "~/" + str(p.relative_to(HOME))
    except ValueError:
        return str(p)


def find_user_memory() -> Path | None:
    """自动发现用户级 MEMORY.md（不硬编码账号 UUID）。"""
    hits = list(HOME.glob(".workbuddy/user-*-personal/MEMORY.md"))
    return hits[0] if hits else None


def find_profile() -> Path | None:
    """发现服务端注入的 profile 缓存文件。"""
    hits = list((HOME / ".workbuddy" / "memory").glob("*_memory.md"))
    return hits[0] if hits else None


def find_project_logs(root: Path) -> list[Path]:
    """递归找所有项目级 .workbuddy/memory/*.md 日志。"""
    logs = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        p = Path(dirpath)
        if p.name == "memory" and p.parent.name == ".workbuddy":
            for f in filenames:
                if f.endswith(".md") and not f.startswith("memory-index"):
                    logs.append(p / f)
    return sorted(logs)


def project_name(log: Path) -> str:
    """从日志路径里取项目名：.workbuddy 的上级目录名。"""
    try:
        return str(log.parent.parent.parent.name)
    except Exception:
        return log.parent.name


def is_date_heading(title: str) -> bool:
    return bool(re.fullmatch(r"[\d\-.年月日\s]+", title.strip()))


# ---------------------------------------------------------------- build

def parse_iron_laws(path: Path) -> list[dict]:
    """从用户级 MEMORY.md 提取主题分组要点。

    注意：用户级 MEMORY.md 会被平台每轮自动注入上下文（实测约 1 万 token），
    默认【不】收进索引——再抄一遍纯属浪费。仅当 --include-irons 显式开启时收录，
    用于平台不注入该文件的其它客户端场景。
    """
    entries = []
    topic = "其他"
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    for i, line in enumerate(lines, 1):
        h = re.match(r"^##\s+(.+?)\s*$", line)
        if h:
            topic = clean_md(h.group(1), 24)
            continue
        item = re.match(r"^[-*]\s+(.+?)\s*$", line)
        if not item:
            continue
        raw = item.group(1)
        # 关键词取冒号前主标题（去括号日期），摘要取冒号后正文，避免 key/summary 重复
        head = raw.split("：")[0].split(":")[0]
        head = re.sub(r"[（(].*?[）)]", "", head)
        key = clean_md(head, 26)
        body = raw[len(head):].lstrip("：: -") if raw.startswith(head) else raw
        # 有加粗标题时，摘要用加粗标题 + 正文首句，key 用更短的标签
        bold = re.search(r"\*\*(.+?)\*\*", raw)
        if bold:
            btitle = re.sub(r"[（(].*?[）)]", "", bold.group(1))
            key = clean_md(btitle, 26)
        summary = clean_md(body, 34) or clean_md(raw, 34)
        if not key or key == summary[:len(key)]:
            key = clean_md(raw, 20)
        entries.append({
            "group": topic,
            "key": key,
            "summary": summary,
            "ref": f"{relpath(path)}:{i}",
        })
    return entries


def parse_profile(path: Path) -> list[dict]:
    """服务端 profile 按加粗块标题（工作背景/个人背景等）分块。"""
    entries = []
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    for i, line in enumerate(lines, 1):
        m = re.match(r"^\*\*(.+?)\*\*\s*$", line)
        if m:
            title = clean_md(m.group(1), 20)
            # 向后找第一句有内容的正文当摘要
            summary = ""
            for j in range(i, min(i + 8, len(lines))):
                cand = clean_md(lines[j], 40)
                if cand and not cand.startswith("**"):
                    summary = cand
                    break
            entries.append({
                "group": "服务端 profile（只读）",
                "key": title,
                "summary": summary,
                "ref": f"{relpath(path)}:{i}",
            })
    return entries


def parse_project_logs(logs: list[Path], per_project: int) -> tuple[list[dict], dict]:
    """按项目提取 ### 主题标题作条目，每项目限量，避免索引爆炸。"""
    by_project: dict[str, list[tuple[float, dict]]] = {}
    total_topics = 0
    for path in logs:
        proj = project_name(path)
        try:
            mtime = path.stat().st_mtime
        except OSError:
            mtime = 0
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        cur = None
        for i, line in enumerate(lines, 1):
            h3 = re.match(r"^###\s+(.+?)\s*$", line)
            h2 = re.match(r"^##\s+(.+?)\s*$", line)
            if h2:
                cur = clean_md(h2.group(1), 24)
                if is_date_heading(cur):
                    cur = None
                continue
            if h3:
                title = clean_md(h3.group(1), 30)
                if is_date_heading(title):
                    continue
                # 摘要：该标题下第一条实质内容（跳过子标题/空行/纯标记行）
                summary = ""
                for j in range(i, min(i + 8, len(lines))):
                    nxt = lines[j].strip()
                    if not nxt or nxt.startswith("#") or nxt.startswith("---"):
                        continue
                    cand = re.match(r"^[-*]?\s*(.+?)\s*$", nxt)
                    if cand:
                        s = clean_md(cand.group(1), 44)
                        if len(s) > 3:  # 过滤掉没信息量的空摘要
                            summary = s
                            break
                # 摘要仍为空则跳过该条目，不占索引位置
                if not summary:
                    continue
                # group 直接用项目名；主题标题作 key。避免"每条一个分组"造成标题重复烧 token
                by_project.setdefault(proj, []).append((mtime, {
                    "group": proj,
                    "key": title,
                    "summary": summary,
                    "ref": f"{relpath(path)}:{i}",
                }))
                total_topics += 1

    final = []
    kept = {}
    for proj, items in by_project.items():
        # 新文件优先，其次文件内原顺序
        items.sort(key=lambda x: -x[0])
        chosen = [it for _, it in items[:per_project]]
        final.extend(chosen)
        kept[proj] = {"kept": len(chosen), "total": len(items)}
    return final, kept


def build(args):
    root = Path(args.root).expanduser() if args.root else HOME
    idx_path = Path(args.out).expanduser() if args.out else DEFAULT_INDEX

    # 用户级铁律与服务端 profile 均被平台每轮自动注入，默认不重复收录。
    iron = parse_iron_laws(find_user_memory()) if (args.include_irons and find_user_memory()) else []
    profile = parse_profile(find_profile()) if (args.include_profile and find_profile()) else []
    logs = find_project_logs(root)
    projects, kept = parse_project_logs(logs, args.per_project)

    all_entries = iron + profile + projects

    # token 预算：超了就从项目主题尾部（较早的）裁剪，铁律/profile 全保留
    def render(entries):
        groups: dict[str, list[dict]] = {}
        for e in entries:
            groups.setdefault(e["group"], []).append(e)
        lines = ["# 记忆检索索引（自动生成，勿手改）",
                 f"> 覆盖：铁律 {len(iron)} / profile {len(profile)} / 项目主题 {len(entries)-len(iron)-len(profile)} 条"
                 f"（来自 {len(logs)} 个日志、{len(kept)} 个项目）",
                 "> 用法：search 命中后按 路径:行号 读原文片段；原始记忆零改动。", ""]
        for group, es in groups.items():
            lines.append(f"## {group}")
            for e in es:
                lines.append(f"- {e['key']} | {e['summary']} | `{e['ref']}`")
            lines.append("")
        return "\n".join(lines)

    clipped = 0
    body = projects[:]
    while body and est_tokens(render(iron + profile + body)) > args.max_tokens:
        body.pop()
        clipped += 1
    all_entries = iron + profile + body

    text = render(all_entries)
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # 先算最终全文 token（含 header），保证头部数字与 stats 一致
    header_no_tokens = f"> 生成时间：{stamp}\n"
    if clipped:
        header_no_tokens += f"> ⚠ 按预算裁掉 {clipped} 条较早主题；完整内容仍在原始日志，可直接读源文件。\n"
    provisional = text.replace("# 记忆检索索引（自动生成，勿手改）\n",
                               "# 记忆检索索引（自动生成，勿手改）\n" + header_no_tokens, 1)
    final_tokens = est_tokens(provisional) + 16  # 加上 token 那一行自身的开销
    header = header_no_tokens + f"> 估算 token：{final_tokens} / 上限 {args.max_tokens}\n"
    text = text.replace("# 记忆检索索引（自动生成，勿手改）\n",
                        "# 记忆检索索引（自动生成，勿手改）\n" + header, 1)

    idx_path.parent.mkdir(parents=True, exist_ok=True)
    idx_path.write_text(text, encoding="utf-8")
    print(f"[build] 索引已生成：{idx_path}")
    print(f"[build] 铁律 {len(iron)} / profile {len(profile)} / 项目主题 {len(body)} / 源日志 {len(logs)} / 项目 {len(kept)} / 裁剪 {clipped}")
    print(f"[build] 估算 token：{est_tokens(text)}（上限 {args.max_tokens}）")


# ---------------------------------------------------------------- search

def read_ref(ref: str, context: int) -> str:
    """按 路径:行号 读原文上下文片段。"""
    if ":" not in ref:
        return "（无法解析引用）"
    path_s, line_s = ref.rsplit(":", 1)
    path = Path(path_s.replace("~/", str(HOME) + "/")).expanduser()
    if not path.exists():
        return f"（源文件不存在：{path}）"
    try:
        lineno = int(line_s)
    except ValueError:
        return "（行号无效）"
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    start = max(0, lineno - 1 - context)
    end = min(len(lines), lineno + context)
    return "\n".join(f"{n+1}: {lines[n]}" for n in range(start, end))


def search(args):
    idx_path = Path(args.index).expanduser() if args.index else DEFAULT_INDEX
    if not idx_path.exists():
        print(f"[search] 索引不存在：{idx_path}，请先运行 build。", file=sys.stderr)
        sys.exit(2)
    text = idx_path.read_text(encoding="utf-8", errors="ignore")
    keywords = [k.lower() for k in args.keywords]
    hits = []
    for line in text.splitlines():
        if not line.startswith("- "):
            continue
        low = line.lower()
        if any(k in low for k in keywords):
            hits.append(line)
    if not hits:
        # 索引未命中不等于记忆不存在——可能被体积预算裁掉了。回退到原始日志兜底搜索。
        print(f"[search] 索引未命中：{' / '.join(args.keywords)}；回退搜索原始日志…")
        raw_hits = []
        root = Path(args.root).expanduser() if args.root else HOME
        for path in find_project_logs(root):
            try:
                lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
            except OSError:
                continue
            for i, line in enumerate(lines, 1):
                low = line.lower()
                if any(k in low for k in keywords) and len(line.strip()) > 4:
                    raw_hits.append((f"{relpath(path)}:{i}", clean_md(line, 60)))
                    if len(raw_hits) >= args.limit:
                        break
            if len(raw_hits) >= args.limit:
                break
        if not raw_hits:
            print(f"[search] 原始记忆中也没有：{' / '.join(args.keywords)}。如实告知用户没有匹配项，不要编造。")
            return
        print(f"[search] 原始日志命中 {len(raw_hits)} 条（索引已裁剪或关键词不在摘要里）：")
        for ref, snippet in raw_hits:
            print(f"  {snippet} | `{ref}`")
        if args.context > 0:
            print("\n--- 原文片段 ---")
            for ref, _ in raw_hits[:args.limit]:
                print(f"\n[{ref}]")
                print(read_ref(ref, args.context))
        return
    print(f"[search] 命中 {len(hits)} 条：")
    for h in hits[:args.limit]:
        print("  " + h)
    if args.context > 0:
        print("\n--- 原文片段 ---")
        seen = set()
        for h in hits[:args.limit]:
            m = re.search(r"`([^`]+)`", h)
            if not m or m.group(1) in seen:
                continue
            seen.add(m.group(1))
            print(f"\n[{m.group(1)}]")
            print(read_ref(m.group(1), args.context))


def stats(args):
    idx_path = Path(args.index).expanduser() if args.index else DEFAULT_INDEX
    if not idx_path.exists():
        print(f"[stats] 索引不存在：{idx_path}", file=sys.stderr)
        sys.exit(2)
    text = idx_path.read_text(encoding="utf-8", errors="ignore")
    entries = [l for l in text.splitlines() if l.startswith("- ")]
    print(f"[stats] 索引：{idx_path}")
    print(f"[stats] 条目数：{len(entries)}")
    print(f"[stats] 字符数：{len(text)} / 估算 token：{est_tokens(text)}")
    print(f"[stats] 头部信息：")
    for l in text.splitlines()[:6]:
        print("  " + l)


def main():
    p = argparse.ArgumentParser(description="WorkBuddy 记忆索引工具")
    sub = p.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("build", help="全量重建索引")
    b.add_argument("--out", help="索引输出路径，默认 ~/.workbuddy/memory/memory-index.md")
    b.add_argument("--root", help="项目记忆扫描根，默认用户主目录")
    b.add_argument("--per-project", type=int, default=6, help="每个项目最多收录的主题条数，默认 6")
    b.add_argument("--max-tokens", type=int, default=3000, help="索引 token 上限，默认 3000")
    b.add_argument("--include-irons", action="store_true", help="收录用户级 MEMORY.md 铁律（默认不收，因平台每轮已自动注入）")
    b.add_argument("--include-profile", action="store_true", help="收录服务端 profile（默认不收，同理已自动注入）")
    b.set_defaults(func=build)

    s = sub.add_parser("search", help="关键词检索索引")
    s.add_argument("keywords", nargs="+", help="关键词，任一命中即可")
    s.add_argument("--index", help="索引路径")
    s.add_argument("--root", help="原始日志搜索根，默认用户主目录（索引未命中时兜底用）")
    s.add_argument("--context", type=int, default=0, help="带出原文上下文行数，默认 0")
    s.add_argument("--limit", type=int, default=10, help="最多显示条数，默认 10")
    s.set_defaults(func=search)

    st = sub.add_parser("stats", help="查看索引统计")
    st.add_argument("--index", help="索引路径")
    st.set_defaults(func=stats)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
