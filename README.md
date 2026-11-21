# sop-skill

一组可复用的 AI 协作技能（SKILL）。每个技能一个目录，遵循 `skills/<name>/SKILL.md` 结构，可直接放入支持 SKILL 规范的 AI 客户端使用。

## 技能列表

- [掌握式自适应学习](skills/mastery-learning/) —— 把任意知识拆成阶段化课程，诊断前置、学完按个人情况出题、掌握式推进、难度自适应。详见[技能说明](skills/mastery-learning/README.md)。

## 安装

把需要的技能目录复制到你的 AI 客户端技能目录即可，例如：

```bash
cp -r skills/mastery-learning ~/.workbuddy/skills/
```

不同客户端的技能目录位置不同，按各自规范放置 `SKILL.md`。

## 许可

Apache-2.0。详见 `LICENSE`。
