# MBTI Skill

给其他 agent 的一句话：

```text
安装此 skill：https://github.com/<owner>/<repo>/tree/main/skills/mbti ，并开始分析我的 MBTI。只读取我明确授权的记忆、历史会话和工作区笔记。
```

这是一个用于 MBTI 分析的 skill，不是独立应用。

## 入口

- 触发词：`分析我的 MBTI`、`性格分析`、`type me`
- 命令：`mbti-report`

## Agent 必须遵守

- 先发现可用 source，再向用户展示
- 先拿到授权，再读取内容
- 先构建 evidence pool，再做 MBTI inference
- 不要直接从原始历史记录推断 MBTI

## 详细规范

完整执行契约、脚本顺序、证据规则见 `SKILL.md`。
