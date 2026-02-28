# Workflow 动态工作流模块

支持可编排的链式步骤（Step）与步骤内并行任务（Task），带完整生命周期回调。

**设计初衷**：根据 AI 提供的数据创建工作流。流程：

1. **接收 AI 返回的指定格式数据**（如 JSON）
2. **由 ai_spec 将指定格式转为 Workflow / Step / Task**（仅写入 handler 与回调的**模块路径字符串**，不写入函数）
3. **执行时**由服务将路径通过 `resolve_handler(path)` 解析为 callable，再按 Step 串行、Step 内 Task 并行执行

**数据存储与执行分离**：

- **创建 / 存储**：只使用字符串（`handler_path`、`on_before_path` / `on_start_path` / `on_done_path` / `on_retry_path`）。创建 workflow、step、task 时**不传递函数**，只传递模块路径字符串。
- **执行**：在 `run_workflow` / `_run_step` / `_run_task` 中，将路径解析为函数再执行。

## 模块结构

```
workflow/
├── __init__.py              # 包入口，统一导出
├── configs/
│   ├── __init__.py
│   └── config.py            # WorkflowConfig、default_config
├── models/
│   ├── __init__.py
│   ├── models.py            # Workflow / Step / Task / *Result 领域模型
│   └── persistence.py       # resolve_handler(路径字符串 → callable)
├── services/
│   ├── __init__.py
│   └── service.py           # WorkflowService、create_workflow_service
├── repositories/
│   ├── __init__.py
│   └── repository.py        # 三表持久化（workflow / step / task）
├── ai_spec/
│   ├── __init__.py
│   ├── schemas.py           # WorkflowSpec / StepSpec / TaskSpec（AI 格式）
│   └── mapper.py            # parse_ai_workflow、dict_to_workflow_spec 等
└── api/
    ├── __init__.py
    ├── deps.py              # get_workflow_service（FastAPI Depends）
    ├── schemas.py           # 请求/响应 Pydantic Schema
    ├── controller.py        # 业务入口 util（供内部或 Router 调用）
    └── routes.py            # FastAPI Router，基于 controller 暴露 HTTP
```

| 层级 | 职责 |
|------|------|
| **configs** | 配置项与默认值 |
| **models** | 领域模型；`resolve_handler` 将 handler 路径字符串解析为可执行函数 |
| **services** | 业务逻辑：创建/编排/执行 workflow，内部调用 repositories、resolve_handler |
| **repositories** | 数据库读写（三张表） |
| **ai_spec** | AI 指定格式 ↔ Workflow 的转换（仅路径字符串，不解析为函数） |
| **api** | Web 层：Router 暴露 HTTP；Controller 为 util，供 Router 或内部调用 |

## 概念与存储字段

- **Workflow**：工作流。至少存储：**id**、**创建者**（creator）、**创建时间**（created_at）、**名称**（name）、**描述**（description）、**起始 step id**（first_step_id）、**结束 step id**（end_step_id）、**step 列表**（steps）。创建时默认包含起始节点与结束节点，二者不可删除。
- **Step**：步骤，按链式顺序串行。**type** 为「起始」/「过程」/「结尾」之一（存储值分别为 `start` / `process` / `end`）。起始节点 previous_step_id 为空，结束节点 next_step_id 为空；起始与结束节点不可删除、不可添加 Task。至少存储：**id**、**type**、**parent_workflow_id**、**previous_step_id**、**next_step_id**、**创建者**、**创建时间**、**task 列表**、**名称**、**描述**。
- **Task**：任务，挂在 Step 下、同 Step 内并行。至少存储：**id**、**父 step 与父 workflow 的 id**、**创建者**、**创建时间**、**运行状态**（run_status：pending/running/success/failed）、**名称**、**描述**、**函数的字符信息**（handler_path、params 等）、**执行结果**（result：TaskResultContent）。

## Workflow 创建与执行流程（从开始到结束）

下面按顺序说明一次完整的「创建 → 编排 → 执行」流程。

### 1. 创建 Workflow

调用 `create_workflow(name, creator=..., description=...)` 会：

- 在内存中创建一个 **Workflow** 实例（id、name、description、creator、created_at）。
- **自动创建两个内置 Step**：
  - **起始节点**（type=`start`）：名称 "Start"，`previous_step_id` 为空，`next_step_id` 指向结束节点；作为链头，不可删除、不可添加 Task。
  - **结束节点**（type=`end`）：名称 "End"，`previous_step_id` 指向起始节点（后续会随插入过程 step 而更新），`next_step_id` 为空；作为链尾，不可删除、不可添加 Task。
- 设置 `workflow.first_step_id`、`workflow.end_step_id`，链结构初始为：`[Start] → [End]`。
- 若配置了 `persist_enabled` 且注入了 `db`，会写入 **workflow 表**一行，并写入 **step 表**两行（起始、结束）。

### 2. 添加过程 Step

- **add_step(workflow_id, name=..., ...)**：在**结束节点前**插入一个 type=`process` 的 Step。链变为：`[Start] → [过程1] → [End]`；多次调用则依次在结束前追加：`[Start] → [过程1] → [过程2] → [End]`。
- **add_step_after(workflow_id, after_step_id, ...)**：在指定 Step **后面**插入一个 process Step；不允许在结束节点后插入（`after_step_id` 不能为 `end_step_id`）。
- 过程 Step 可删除（**delete_step**）；起始、结束节点不可删除。
- 每次 add/update/delete 若开启持久化，只会同步**受影响的那张表**（workflow 表或 step 表）。

### 3. 在 Step 上添加 Task

- **add_task(workflow_id, step_id, name=..., handler_path=..., params=..., ...)**：在指定 Step 下挂一个 Task。
- **仅允许在 type=`process` 的 Step 上添加**；在起始/结束节点上调用会返回 `None`。
- Task 存储 handler 的**模块路径字符串**（`handler_path`）和参数（`params`），执行时再由服务解析为函数调用。
- 若开启持久化，会写入 **task 表**一行。

### 4. 执行 Workflow

- **run_workflow(workflow_id, context=...)**：
  1. 按 **Step 链顺序**依次执行（顺序与 `workflow.steps` 一致：Start → 过程1 → 过程2 → … → End）。
  2. 每个 Step 内：先执行 Step 的生命周期回调（on_before_path、on_start_path 等），再**并行执行**该 Step 下所有 Task（可通过 `max_task_concurrent` 限制并发数）。
  3. 每个 Task：将 `handler_path` 解析为 callable，以 `(context, **params)` 调用；结果规范为 `TaskResultContent`，写入 `workflow.task_results[task_id]`，若开启持久化则更新 **task 表**的 `run_status` 与 `result`。
  4. 起始/结束节点没有 Task，只跑其生命周期回调（若有）；任一步失败会终止后续 Step，并在 `WorkflowResult` 中记录 `error`。
- **re_run_step** / **re_run_task**：可对单个 Step 或 Task 重跑（会触发 on_retry_path 等）。

### 5. 持久化与加载

- **创建/编排阶段**：若 `persist_enabled=True` 且注入了 `db`，则 `create_workflow`、`add_step`、`add_step_after`、`add_task`、`edit_*`、`delete_*` 会在操作后**按表**同步（workflow 表、step 表、task 表各写各自行）。
- **执行阶段**：`run_workflow` / `re_run_task` 成功后会把 task 结果写回 **task 表**（`run_status`、`result`）。
- **加载已有 Workflow**：使用 `load_workflow_from_db(db, workflow_collection, step_collection, task_collection, workflow_id)` 从三张表组装出完整 Workflow（含 steps、tasks、first_step_id、end_step_id），再放入 `svc._workflows[w.id]` 即可执行。

### 流程小结

| 阶段     | 操作 | 说明 |
|----------|------|------|
| 创建     | `create_workflow` / `register_workflow_from_ai` | 空流程或从 AI 格式解析并注册 |
| 编排     | `add_step` / `add_step_after` | 在结束前或指定 Step 后插入 process Step |
| 编排     | `edit_step` / `delete_step` | 编辑或删除 process Step |
| 编排     | `add_task` / `edit_task` / `delete_task` | 在 process Step 上增删改 Task |
| 执行     | `run_workflow` | 按链串行执行 Step，Step 内 Task 并行；结果写入 task_results 并可选落库 |
| 重跑     | `re_run_step` / `re_run_task` | 重跑指定 Step 或 Task（先触发 on_retry_path） |
| 持久化   | `persist_workflow` | 将 workflow 全量同步到三张表 |
| 加载     | `load_workflow_from_db` | 从三表组装 Workflow，再注册到服务后执行 |

## Workflow 整体流程逻辑梳理

### 一、数据模型与 ID 规则

| 实体 | 主键 id 格式 | 说明 |
|------|----------------|------|
| Workflow | `workflow_` + UUID | 未传 id 时由 `_new_workflow_id()` 生成 |
| Step | `step_` + UUID | 由 `_new_step_id()` 生成 |
| Task | `task_` + UUID | 由 `_new_task_id()` 生成 |

链结构：Step 通过 `previous_step_id` / `next_step_id` 形成单向链；Workflow 通过 `first_step_id`（链头）、`end_step_id`（链尾）定位起止。起始 step 的 `previous_step_id` 为空，结束 step 的 `next_step_id` 为空。

### 二、创建入口（两条路径）

| 入口 | 说明 | 结果 |
|------|------|------|
| **create_workflow** | 服务层创建空流程 | Workflow + Start Step + End Step，链为 [Start]→[End]，写入 `_workflows`，可选落库 workflow 表 + step 表 |
| **parse_ai_workflow** | 从 AI Spec 解析 | Workflow(id 可指定或自动带前缀) + Start + 若干 process Step + End，链完整，未写入服务；需手动 `svc._workflows[w.id] = w` 后才能 add_step / run_workflow |

两路径产出的 Workflow 结构一致（均有 first_step_id、end_step_id 与 Start/End 节点），便于统一后续编排与执行。

### 三、编排逻辑

- **add_step(workflow_id, ...)**：在 `end_step` 前插入一个 process Step，更新 end 的 previous、前一个 step 的 next、内存 `w.steps` 顺序；持久化时写 step 表并更新受影响 step 行。
- **add_step_after(workflow_id, after_step_id, ...)**：禁止 `after_step_id == end_step_id`；在指定 step 后插入 process Step，维护前后链指针与 `w.steps`；持久化同上。
- **delete_step(workflow_id, step_id)**：禁止删除 `first_step_id` / `end_step_id`；从链中摘除后更新前驱与后继的 next/previous，并级联删除 step 表与 task 表中该 step 及其 tasks。
- **add_task(workflow_id, step_id, ...)**：仅允许 step.type == process；起始/结束节点返回 None。
- **delete_task** / **edit_task**：同样禁止在 start/end 节点上操作（防御性）。

### 四、持久化（三张表）

- **workflow 表**：仅元数据（id、name、description、creator、created_at、first_step_id、end_step_id、updated_at）；create/update workflow 或 first/end 变化时写入。
- **step 表**：每行一个 Step（含 type、parent_workflow_id、previous_step_id、next_step_id、回调路径等）；add/update/delete step 时只写或删对应行。
- **task 表**：每行一个 Task（含 parent_step_id、handler_path、params、run_status、result 等）；add/update/delete task 或执行结果落库时写对应行。

**加载**：`load_workflow_from_db` 先查 workflow 表得元数据，再按 `parent_workflow_id` 查 step 表，按链序排好，再按 `parent_step_id` 为每个 step 查 task 表并填回；最后把 task 的 result 填到 `workflow.task_results`。ID 为带前缀字符串时，Mongo 以 string 存 `_id`，查询用同一 string 即可。

### 五、执行顺序与生命周期

**run_workflow(workflow_id, context)**：

1. 从 `w.steps` 按**当前顺序**依次执行（顺序与链一致：Start → 过程1 → … → End）。
2. 对每个 Step：先 step 级 on_before → on_start；再对该 step 下所有 Task **并行**执行（可配 `max_task_concurrent`）；再 step 级 on_done。
3. 对每个 Task：on_before → on_start → `resolve_handler(handler_path)(context, **params)` → 结果规范为 TaskResultContent → on_done；结果写入 `w.task_results[task_id]` 并可选写 task 表。
4. 任一步失败则终止后续 step，`WorkflowResult.error` 记录原因；Start/End 无 task，仅跑其 step 级回调。

**re_run_step** / **re_run_task**：先触发对应 on_retry_path，再按 step 或 task 执行一次，成功则同上写回 task_results 与 task 表。

### 六、约束汇总

| 约束 | 说明 |
|------|------|
| 起始/结束节点不可删除 | delete_step 时 step_id 不能为 first_step_id / end_step_id |
| 起始/结束节点不可添加/删除/编辑 Task | add_task / delete_task / edit_task 在 step.type 为 start/end 时直接返回 None/False |
| 不可在结束节点后插入 Step | add_step_after 的 after_step_id 不能为 end_step_id |
| 无 end_step_id 的 workflow | 未通过 create_workflow/parse_ai_workflow 创建时 add_step 会返回 None |

---

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
    w = await svc.create_workflow("示例流程")

    # 添加 Step（回调为模块路径字符串）；启用持久化时会自动同步到 DB
    step1 = await svc.add_step(
        w.id,
        "第一步",
        on_before_path="myapp.callbacks.before_step",
        on_done_path="myapp.callbacks.done_step",
    )

    # 添加 Task：只传 handler_path 与 params，不传函数
    await svc.add_task(
        w.id, step1.id,
        name="t1",
        handler_path="myapp.tasks.my_task",
        params={"value": 10},
    )
    await svc.add_task(
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

### 服务层（WorkflowService）

- **Workflow**：`create_workflow`、`register_workflow_from_ai`、`get_workflow`、`delete_workflow`、`persist_workflow`
- **Step**：`add_step`、`add_step_after`、`edit_step`、`delete_step`、`re_run_step`
- **Task**：`add_task`、`edit_task`、`delete_task`、`re_run_task`
- **执行**：`run_workflow(workflow_id, context)`、`re_run_step`、`re_run_task`

当已注入 `db` 且 `persist_enabled=True` 时，create/add/edit/delete 在操作完成后会**自动同步到数据库**。上述方法均为 **async**，调用时需 **await**。Task 执行函数签名为 `(context: dict, **params) -> Any`，由 `resolve_handler(handler_path)` 解析得到。

### HTTP 接口（Router，前缀 `/api/v1/workflows`）

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/from-ai` | 从 AI 格式 JSON 创建并注册 Workflow |
| POST | `` | 创建空 Workflow（含 Start/End） |
| GET | `/{workflow_id}` | 获取 Workflow |
| DELETE | `/{workflow_id}` | 删除 Workflow |
| POST | `/{workflow_id}/steps` | 在结束节点前添加 Step |
| POST | `/{workflow_id}/steps/after/{after_step_id}` | 在指定 Step 后添加 Step |
| PATCH | `/{workflow_id}/steps/{step_id}` | 编辑 Step |
| DELETE | `/{workflow_id}/steps/{step_id}` | 删除 Step |
| POST | `/{workflow_id}/steps/{step_id}/rerun` | 重跑 Step |
| POST | `/{workflow_id}/steps/{step_id}/tasks` | 添加 Task |
| PATCH | `/{workflow_id}/steps/{step_id}/tasks/{task_id}` | 编辑 Task |
| DELETE | `/{workflow_id}/steps/{step_id}/tasks/{task_id}` | 删除 Task |
| POST | `/{workflow_id}/steps/{step_id}/tasks/{task_id}/rerun` | 重跑 Task |
| POST | `/{workflow_id}/run` | 执行 Workflow |
| POST | `/{workflow_id}/persist` | 全量持久化到三张表 |

## 配置

`WorkflowConfig`：

- **执行**：`step_timeout`、`task_timeout`、`max_task_concurrent`（Step 内 Task 并发上限，0 表示不限制）。
- **持久化**：`persist_enabled`；三张表名 `workflow_collection_name`、`step_collection_name`、`task_collection_name`。启用时需在创建服务时传入 `db`（`AsyncIOMotorDatabase`）。

可通过 `WorkflowConfig.from_env()` 从环境变量加载。

| 环境变量 | 说明 | 默认 |
|----------|------|------|
| `WORKFLOW_PERSIST_ENABLED` | 是否启用持久化 | false |
| `WORKFLOW_COLLECTION_NAME` | workflow 表/集合名 | workflows |
| `WORKFLOW_STEP_COLLECTION_NAME` | step 表/集合名 | workflow_steps |
| `WORKFLOW_TASK_COLLECTION_NAME` | task 表/集合名 | workflow_tasks |
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

## 持久化（三张表，按关联 id 查询）

Workflow / Step / Task **各占一张表**，通过 `parent_workflow_id`、`parent_step_id`、`previous_step_id`、`next_step_id` 等关联 id 查询；**只改单个 step 或 task 时只更新对应表**，避免整份文档重写。

- **workflow 表**：`_id`、`name`、`description`、`creator`、`created_at`、`first_step_id`、`end_step_id`、`updated_at`。
- **step 表**：`_id`、`type`、`parent_workflow_id`、`previous_step_id`、`next_step_id`、`name`、`description`、`creator`、`created_at`、回调路径等。
- **task 表**：`_id`、`parent_step_id`、`parent_workflow_id`、`name`、`description`、`creator`、`created_at`、`run_status`、`handler_path`、`params`、`result` 等。

**仓库接口**：

- **save_workflow_meta(db, workflow_collection, workflow)**：仅写 workflow 表一行。
- **save_step** / **update_step**：仅写/更新 step 表。
- **save_task** / **update_task** / **update_task_result**：仅写/更新 task 表。
- **load_workflow_from_db(db, workflow_collection, step_collection, task_collection, workflow_id)**：按三表组装完整 Workflow（先查 workflow，再按 parent_workflow_id 查 steps，再按 parent_step_id 查 tasks）。
- **delete_workflow_cascade**：级联删除 workflow 表一行及该 workflow 下所有 step、task。
- **delete_step_cascade**：级联删除 step 表一行及该 step 下所有 task。
- **save_workflow_task_result(db, task_collection, task_id, run_status, result_content)**：仅更新 task 表的 `run_status` 与 `result`。

当服务配置了 `persist_enabled` 且注入了 `db` 时，create/add/edit/delete 会**只同步对应表**；`run_workflow` / `re_run_task` 成功后将 task 结果写入 **task 表**。

```python
from core.mongodb import get_database
from packages.workflow import (
    load_workflow_from_db,
    create_workflow_service,
)

db = get_database()
# 三表名需与 config 一致（或从 config 取）
w = await load_workflow_from_db(db, "workflows", "workflow_steps", "workflow_tasks", workflow_id)
svc = create_workflow_service(config=config, db=db)
svc._workflows[w.id] = w
result = await svc.run_workflow(w.id, context={})
```

## 模块自检与待优化

**本次已修复/统一：**

- **workflow_to_doc**：导出时包含 `first_step_id`、`end_step_id`，与三表元数据一致。
- **parse_ai_workflow**：`workflow_id` 为空时自动生成带前缀 id；解析结果统一包一层 Start/End 节点并设置 `first_step_id`/`end_step_id`，与 `create_workflow` 结构一致。
- **workflow_to_spec**：仅导出 type=`process` 的 step，不包含 Start/End。
- **delete_task** / **edit_task**：起始/结束节点上禁止操作（与 add_task 一致）。

**可选后续优化：**

- **Workflow 内存存储**：已采用「按需从 DB 加载」：`_workflows` 为内存缓存，`get_workflow`、`run_workflow`、`add_step` 等若缓存未命中且已开启持久化则从三表加载并写入缓存，适合 Web 后端（跨请求、多实例、重启后仍可操作）。后续可按需加 LRU/TTL 限制缓存大小。
- **step_timeout / task_timeout**：配置项已存在，执行层尚未用 `asyncio.wait_for` 做超时，可按需加上。
- **MongoDB 索引**：step 表按 `parent_workflow_id`、task 表按 `parent_step_id` / `parent_workflow_id` 查询，数据量大时建议加对应索引。
