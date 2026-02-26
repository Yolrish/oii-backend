# Workflow 动态工作流模块

支持可编排的链式步骤（Step）与步骤内并行任务（Task），带完整生命周期回调。

## 概念

- **Workflow**：工作流，可创建、删除；包含多个 Step。
- **Step**：步骤，按**链式顺序串行**执行；可添加、删除、编辑、重执行。
- **Task**：任务，挂在 Step 下，在**同一 Step 内并行**执行；可执行外部传入的函数，支持添加、删除、编辑、重执行。

## 回调接口

每个 Step / Task 均支持四个生命周期回调（均为可选）：

| 回调 | 含义 |
|------|------|
| `on_before` | 执行前（即将进入该 step/task 时） |
| `on_start` | 开始执行 |
| `on_done` | 执行完成（可接收结果） |
| `on_retry` | 重新执行时 |

- **Step**：使用 `StepCallbacks(on_before=..., on_start=..., on_done=..., on_retry=...)`
- **Task**：使用 `TaskCallbacks(on_before=..., on_start=..., on_done=..., on_retry=...)`

回调可为同步或异步函数；异步会在执行时被 `await`。

## 快速开始

```python
from packages.workflow import (
    create_workflow_service,
    StepCallbacks,
    TaskCallbacks,
)

async def main():
    svc = create_workflow_service()
    w = svc.create_workflow("示例流程")

    # 添加 Step（可带回调）
    step1 = svc.add_step(w.id, "第一步", callbacks=StepCallbacks(
        on_before=lambda s, ctx: print(f"即将执行 step: {s.name}"),
        on_done=lambda s, ctx, result: print(f"step 完成: {result.success}"),
    ))

    # 添加 Task（传入可执行函数与可选参数）
    def my_task(context, **kwargs):
        return kwargs.get("value", 0) + 1

    svc.add_task(w.id, step1.id, func=my_task, name="t1", params={"value": 10})
    svc.add_task(w.id, step1.id, func=my_task, name="t2", params={"value": 20})

    # 串行执行 Step，Step 内 Task 并行
    result = await svc.run_workflow(w.id, context={})
    print(result.success, result.step_results)
```

## API 摘要

- **Workflow**：`create_workflow(name)`、`get_workflow(id)`、`delete_workflow(id)`
- **Step**：`add_step(workflow_id, name, callbacks)`、`delete_step`、`edit_step`、`re_run_step`
- **Task**：`add_task(workflow_id, step_id, func, name, params, callbacks)`、`delete_task`、`edit_task`、`re_run_task`
- **执行**：`run_workflow(workflow_id, context)`、`re_run_step`、`re_run_task`

Task 的 `func` 签名为 `(context: dict, **params) -> Any`，支持 sync/async。

## 配置

`WorkflowConfig`：`step_timeout`、`task_timeout`、`max_task_concurrent`（Step 内 Task 并发上限，0 表示不限制）。
