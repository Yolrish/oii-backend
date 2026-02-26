# Workflow 动态工作流模块

支持可编排的链式步骤（Step）与步骤内并行任务（Task），带完整生命周期回调。

**设计初衷**：根据 AI 提供的数据创建工作流。流程：

1. **接收 AI 返回的指定格式数据**（如 JSON）
2. **由 ai_spec 将指定格式转为 Workflow / Step / Task**（仅写入 handler 与回调的**模块路径字符串**，不写入函数）
3. **执行时**由服务将路径通过 `resolve_handler(path)` 解析为 callable，再按 Step 串行、Step 内 Task 并行执行

**数据存储与执行分离**：

- **创建 / 存储**：只使用字符串（`handler_path`、`on_before_path` / `on_start_path` / `on_done_path` / `on_retry_path`）。创建 workflow、step、task 时**不传递函数**，只传递模块路径字符串。
- **执行**：在 `run_workflow` / `_run_step` / `_run_task` 中，将路径解析为函数再执行。

## 概念与存储字段

- **Workflow**：工作流。至少存储：**id**、**创建者**（creator）、**创建时间**（created_at）、**名称**（name）、**描述**（description）、**拥有的 step 的 id**（step_ids，由 steps 推导）。
- **Step**：步骤，按链式顺序串行。至少存储：**id**、**父 workflow id**（parent_workflow_id）、**上一个/下一个 step id**（previous_step_id、next_step_id）、**创建者**、**创建时间**、**拥有的 task 的 id**（task_ids）、**名称**、**描述**。
- **Task**：任务，挂在 Step 下、同 Step 内并行。至少存储：**id**、**父 step 与父 workflow 的 id**、**创建者**、**创建时间**、**运行状态**（run_status：pending/running/success/failed）、**名称**、**描述**、**函数的字符信息**（handler_path、params 等）、**执行结果**（result：TaskResultContent）。

## 生命周期回调（路径表示）

每个 Step / Task 均支持四个生命周期回调，在模型中以**路径字符串**存储：

| 路径字段 | 含义 |
|----------|------|
| `on_before_path` | 执行前（即将进入该 step/task 时） |
| `on_start_path` | 开始执行 |
| `on_done_path` | 执行完成（可接收结果） |
| `on_retry_path` | 重新执行时 |

解析后的回调可为同步或异步函数；异步会在执行时被 `await`。

## 快速开始

```python
from packages.workflow import create_workflow_service

async def main():
    svc = create_workflow_service()
    w = svc.create_workflow("示例流程")

    # 添加 Step（回调为模块路径字符串）
    step1 = svc.add_step(
        w.id,
        "第一步",
        on_before_path="myapp.callbacks.before_step",
        on_done_path="myapp.callbacks.done_step",
    )

    # 添加 Task：只传 handler_path 与 params，不传函数
    svc.add_task(
        w.id, step1.id,
        name="t1",
        handler_path="myapp.tasks.my_task",
        params={"value": 10},
    )
    svc.add_task(
        w.id, step1.id,
        name="t2",
        handler_path="myapp.tasks.my_task",
        params={"value": 20},
    )

    # 执行时由服务将路径解析为函数再执行
    result = await svc.run_workflow(w.id, context={})
    print(result.success, result.step_results)
```

## API 摘要

- **Workflow**：`create_workflow(name, creator=..., description=...)`、`get_workflow(id)`、`delete_workflow(id)`
- **Step**：`add_step(workflow_id, name, description=..., creator=..., on_before_path=..., ...)`、`delete_step`、`edit_step`、`re_run_step`
- **Task**：`add_task(workflow_id, step_id, name, description=..., creator=..., handler_path, params=..., ...)`、`delete_task`、`edit_task`、`re_run_task`
- **执行**：`run_workflow(workflow_id, context)`、`re_run_step`、`re_run_task`

执行函数的签名为 `(context: dict, **params) -> Any`，支持 sync/async。由 `resolve_handler(handler_path)` 解析得到。

## 配置

`WorkflowConfig`：

- **执行**：`step_timeout`、`task_timeout`、`max_task_concurrent`（Step 内 Task 并发上限，0 表示不限制）。
- **持久化**：`persist_enabled`、`collection_name`。启用时需在创建服务时传入 `db`（`AsyncIOMotorDatabase`）。

可通过 `WorkflowConfig.from_env()` 从环境变量加载。

| 环境变量 | 说明 | 默认 |
|----------|------|------|
| `WORKFLOW_PERSIST_ENABLED` | 是否启用持久化 | false |
| `WORKFLOW_COLLECTION_NAME` | 存储 workflow 的集合名 | workflows |
| `WORKFLOW_STEP_TIMEOUT` | Step 超时（秒） | 0 |
| `WORKFLOW_TASK_TIMEOUT` | Task 超时（秒） | 0 |
| `WORKFLOW_MAX_TASK_CONCURRENT` | Step 内 Task 并发上限 | 0 |

## AI 指定格式模块（ai_spec）

将「AI 返回的指定格式」转为 Workflow（仅写路径，不解析为函数）。

- **WorkflowSpec / StepSpec / TaskSpec**：AI 格式的 schema（全可序列化）。TaskSpec 含 `handler`、`params`、`on_before`/`on_start`/`on_done`/`on_retry`（均为模块路径字符串）。
- **parse_ai_workflow(spec)** / **parse_ai_workflow_from_dict(data)**：Spec 或 dict → Workflow，**只写入路径字符串**，不解析为 callable。
- **workflow_to_spec(workflow)**、**workflow_spec_to_dict(spec)**、**dict_to_workflow_spec(data)**：与 dict 互转，便于落库或回传 AI。

示例：AI 返回 JSON 后解析并执行

```python
from packages.workflow import (
    dict_to_workflow_spec,
    parse_ai_workflow,
    create_workflow_service,
)

ai_json = {
    "name": "用户操作流程",
    "steps": [
        {
            "name": "步骤1",
            "tasks": [
                {"handler": "myapp.actions.fetch", "params": {"url": "..."}},
                {"handler": "myapp.actions.validate", "params": {}},
            ],
        },
        {"name": "步骤2", "tasks": [{"handler": "myapp.actions.save", "params": {}}]},
    ],
}
spec = dict_to_workflow_spec(ai_json)
w = parse_ai_workflow(spec)  # 仅写路径，不解析
svc = create_workflow_service()
svc._workflows[w.id] = w
# 执行时由服务按路径解析并执行
result = await svc.run_workflow(w.id, context={})
```

## Task 结果格式（持久化到 DB）

执行过并收到结果的 task，其结果统一为 **{ type, content }**，两者均为字符串：

- **type**：内容类型，取值为 `text` | `image` | `video` | `audio`（暂定四种）。
- **content**：对应文本内容或文件服务器 URL。

Handler 可返回 `dict`（如 `{"type": "text", "content": "..."}` 或 `{"type": "image", "content": "https://..."}`），服务会规范为 `TaskResultContent` 并写入内存与 DB。类型未指定或非法时默认为 `text`。

- **TaskResultContent(type, content)**：模型类，含 `to_dict()` / `from_dict()`，便于落库与反序列化。
- **Workflow.task_results**：`Dict[task_id, TaskResultContent]`，与 DB 中 `task_results` 一致；加载 workflow 时会带回。

## 持久化（以 Spec 为源，含 task 结果）

以 **WorkflowSpec** 为源存储 workflow 实例；文档中同时保存已执行 task 的结果。

- 文档结构（完整实例）：`_id`、`name`、`description`、`creator`、`created_at`、`updated_at`、`step_ids`、`steps`（含每 step 的 id/父 workflow/上一步/下一步/创建者/时间/task_ids/名称/描述及嵌套的 `tasks`）、`task_results`、`spec`（兼容）。
- **save_workflow_spec(...)**：按 Spec 写入，可带 `creator`、`description`；返回 `_id`。
- **save_workflow(db, collection_name, workflow)**：将完整 Workflow 实例写入 DB。
- **load_workflow_spec(...)**：读出 WorkflowSpec。
- **load_workflow_from_db(...)**：若文档含完整 `steps`（含 `tasks`）则反序列化为完整 Workflow；否则从 spec 解析并叠加 `task_results` 与 name/description/creator/created_at。
- **update_workflow_spec(...)**：更新已有文档的 spec。
- **save_workflow_task_result(db, collection_name, workflow_id, task_id, result_content)**：将单个 task 结果写入 `task_results[task_id]`。
- **workflow_to_doc(w)** / **doc_to_workflow(doc)**：完整实例与文档互转。

当服务配置了 `persist_enabled` 且注入了 `db` 时，`run_workflow` 与 `re_run_task` 会在成功完成后自动将 task 结果写入 DB。

```python
from core.mongodb import get_database
from packages.workflow import (
    save_workflow_spec,
    load_workflow_from_db,
    create_workflow_service,
)

db = get_database()
spec = dict_to_workflow_spec(ai_response_json)
wid = await save_workflow_spec(db, "workflows", spec, name=spec.name)
w = await load_workflow_from_db(db, "workflows", wid)
svc = create_workflow_service()
svc._workflows[w.id] = w
result = await svc.run_workflow(w.id, context={})
```
