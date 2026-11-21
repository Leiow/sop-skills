# sop-skill

一组可复用的 AI 协作技能（SKILL）。每个技能一个目录，遵循 `skills/<name>/SKILL.md` 结构，可直接放入支持 SKILL 规范的 AI 客户端使用。

## 技能列表

- [掌握式自适应学习](skills/mastery-learning/) —— 把任意知识拆成阶段化课程，诊断前置、学完按个人情况出题、掌握式推进、难度自适应。详见[技能说明](skills/mastery-learning/README.md)。
- [目标锚定执行 SOP](skills/goal-anchored-sop/) —— 推进项目时防止偏离目标、反复返工：任务必须服务最终目标、禁止自评、独立评审最多 3 轮、问题分流。详见[技能说明](skills/goal-anchored-sop/README.md)。

## 安装

把下面这段话发给你的 AI 助手，它会自己完成安装：

> 请读取 `https://raw.githubusercontent.com/Leiow/sop-skills/main/skills/mastery-learning/SKILL.md` 的内容，把它作为一个技能安装到本地。先问我安装到全局还是当前项目，再把文件放到对应的技能目录。

如果助手无法访问该链接，把这行地址给它：`https://github.com/Leiow/sop-skills`，让它从仓库的 `skills/mastery-learning/` 读取 `SKILL.md`。

## 许可

Apache-2.0。详见 `LICENSE`。
