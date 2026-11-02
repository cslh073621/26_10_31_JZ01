# 生成输出防覆盖审查

## 1. 默认规则

`fanforge generate`在目标目录存在以下任一受管文件时默认拒绝继续：

- `main.c.in`
- `main.h.in`
- `generation_report.md`
- `acceptance_checklist.md`
- `resolved_plan.json`

目标目录不存在，或目录中只有其他非受管文件时，可以正常生成。

## 2. 为什么必须拒绝

生成后的风扇项目通常还会经过人工脚位复核、客户参数标定、目标编译器适配和实板修正。静默重生成会覆盖这些尚未同步回配置或生成器的修改，因此默认行为必须先停下来提示，而不是猜测哪些差异可以保留。

## 3. 明确覆盖

只有确认已有输出已经提交Git、另行备份，或确实属于可重复生成的展示目录时，才使用：

```powershell
python -m fanforge generate path/to/config.json --out path/to/output --force
```

`tools/generate_showcase.ps1`只维护仓库内由配置完整生成的展示目录，因此固定显式传入`--force`。

## 4. 保持不变

该保护只位于PC端CLI边界：

- 不修改核心C模板。
- 不修改资源规划结果。
- 不修改任何MCU功能函数或运行状态。
- 不改变相同配置加相同版本时的确定性输出。

人工修改过的产品工程不应直接作为展示目录批量重生成；应先把可参数化差异同步回配置或生成器，再进行受控覆盖。
