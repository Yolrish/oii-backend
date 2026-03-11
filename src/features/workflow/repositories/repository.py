"""
Workflow 持久化：三张表（workflow / step / task），通过关联 id 查询

- workflows：workflow 元数据（id、名称、描述、创建者、创建时间等）
- workflow_steps：step 元数据（id、parent_workflow_id、previous_step_id、next_step_id、名称、描述等）
- workflow_tasks：task 元数据（id、parent_step_id、parent_workflow_id、运行状态、结果等）

单条修改只更新对应表，避免整份文档重写。
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from ..models.models import (
    Workflow,
    Step,
    Task,
    TaskResultContent,
    STEP_TYPE_PROCESS,
)
from ..ai_spec import (
    WorkflowSpec,
    workflow_spec_to_dict,
    dict_to_workflow_spec,
    parse_ai_workflow,
)


# ---------- 三表文档转换 ----------


def _workflow_meta_to_doc(w: Workflow) -> Dict[str, Any]:
    """Workflow 元数据 → workflow 表一行（不含 steps/tasks）"""
    now = datetime.utcnow()
    return {
        "_id": w.id,
        "name": w.name,
        "description": w.description or "",
        "creator": w.creator or "",
        "created_at": w.created_at,
        "first_step_id": w.first_step_id or "",
        "end_step_id": w.end_step_id or "",
        "updated_at": now,
    }


def _step_to_doc(s: Step) -> Dict[str, Any]:
    """Step → step 表一行（不含嵌套 tasks）"""
    return {
        "_id": s.id,
        "type": s.type or STEP_TYPE_PROCESS,
        "parent_workflow_id": s.parent_workflow_id or "",
        "previous_step_id": s.previous_step_id or "",
        "next_step_id": s.next_step_id or "",
        "name": s.name,
        "description": s.description or "",
        "creator": s.creator or "",
        "created_at": s.created_at,
        "on_before_path": s.on_before_path or "",
        "on_start_path": s.on_start_path or "",
        "on_done_path": s.on_done_path or "",
        "on_retry_path": s.on_retry_path or "",
        "updated_at": datetime.utcnow(),
    }


def _task_to_doc(t: Task) -> Dict[str, Any]:
    """Task → task 表一行"""
    return {
        "_id": t.id,
        "parent_step_id": t.parent_step_id or "",
        "parent_workflow_id": t.parent_workflow_id or "",
        "name": t.name,
        "description": t.description or "",
        "creator": t.creator or "",
        "created_at": t.created_at,
        "run_status": t.run_status,
        "handler_path": t.handler_path or "",
        "params": t.params if isinstance(t.params, dict) else {},
        "on_before_path": t.on_before_path or "",
        "on_start_path": t.on_start_path or "",
        "on_done_path": t.on_done_path or "",
        "on_retry_path": t.on_retry_path or "",
        "result": t.result.to_dict() if t.result else None,
        "updated_at": datetime.utcnow(),
    }


def _doc_to_workflow_meta(doc: Dict[str, Any]) -> Workflow:
    """workflow 表一行 → Workflow（仅元数据，steps 为空）"""
    wid = str(doc.get("_id", ""))
    created_at = doc.get("created_at")
    return Workflow(
        id=wid,
        name=str(doc.get("name", "")),
        description=str(doc.get("description", "")),
        creator=str(doc.get("creator", "")),
        created_at=created_at if isinstance(created_at, datetime) else None,
        first_step_id=str(doc.get("first_step_id", "")),
        end_step_id=str(doc.get("end_step_id", "")),
        steps=[],
        task_results={},
    )


def _doc_to_step(doc: Dict[str, Any]) -> Step:
    """step 表一行 → Step（tasks 为空，由 load 时按 parent_step_id 填充）"""
    sid = str(doc.get("_id", ""))
    created_at = doc.get("created_at")
    return Step(
        id=sid,
        type=str(doc.get("type", STEP_TYPE_PROCESS)),
        name=str(doc.get("name", "")),
        description=str(doc.get("description", "")),
        parent_workflow_id=str(doc.get("parent_workflow_id", "")),
        previous_step_id=str(doc.get("previous_step_id", "")),
        next_step_id=str(doc.get("next_step_id", "")),
        creator=str(doc.get("creator", "")),
        created_at=created_at if isinstance(created_at, datetime) else None,
        tasks=[],
        on_before_path=str(doc.get("on_before_path", "")),
        on_start_path=str(doc.get("on_start_path", "")),
        on_done_path=str(doc.get("on_done_path", "")),
        on_retry_path=str(doc.get("on_retry_path", "")),
    )


def _doc_to_task(doc: Dict[str, Any]) -> Task:
    """task 表一行 → Task"""
    tid = str(doc.get("_id", ""))
    created_at = doc.get("created_at")
    result = doc.get("result")
    return Task(
        id=tid,
        name=str(doc.get("name", "")),
        description=str(doc.get("description", "")),
        parent_step_id=str(doc.get("parent_step_id", "")),
        parent_workflow_id=str(doc.get("parent_workflow_id", "")),
        creator=str(doc.get("creator", "")),
        created_at=created_at if isinstance(created_at, datetime) else None,
        run_status=str(doc.get("run_status", "pending")),
        handler_path=str(doc.get("handler_path", "")),
        params=doc.get("params") or {},
        on_before_path=str(doc.get("on_before_path", "")),
        on_start_path=str(doc.get("on_start_path", "")),
        on_done_path=str(doc.get("on_done_path", "")),
        on_retry_path=str(doc.get("on_retry_path", "")),
        result=TaskResultContent.from_dict(result) if result else None,
    )


async def _find_doc_by_id(
    db: Any, collection: str, id_value: str
) -> Optional[Dict[str, Any]]:
    """按 _id 查一条；支持 str 或 ObjectId"""
    try:
        from bson import ObjectId

        doc = await db[collection].find_one({"_id": ObjectId(id_value)})
    except Exception:
        doc = None
    if doc is None:
        doc = await db[collection].find_one({"_id": id_value})
    return doc


# ---------- Workflow 表 ----------


async def save_workflow_meta(
    db: Any,
    workflow_collection: str,
    workflow: Workflow,
) -> bool:
    """仅写入 workflow 表一行（元数据）"""
    doc = _workflow_meta_to_doc(workflow)
    try:
        from bson import ObjectId

        await db[workflow_collection].replace_one(
            {"_id": ObjectId(workflow.id)},
            doc,
            upsert=True,
        )
    except Exception:
        await db[workflow_collection].replace_one(
            {"_id": workflow.id},
            doc,
            upsert=True,
        )
    return True


async def load_workflow_meta(
    db: Any,
    workflow_collection: str,
    workflow_id: str,
) -> Optional[Workflow]:
    """从 workflow 表加载一条，返回 Workflow（steps 为空）"""
    doc = await _find_doc_by_id(db, workflow_collection, workflow_id)
    if not doc:
        return None
    return _doc_to_workflow_meta(doc)


# ---------- Step 表 ----------


async def save_step(
    db: Any,
    step_collection: str,
    step: Step,
) -> bool:
    """写入或覆盖 step 表一行"""
    doc = _step_to_doc(step)
    try:
        from bson import ObjectId

        await db[step_collection].replace_one(
            {"_id": ObjectId(step.id)},
            doc,
            upsert=True,
        )
    except Exception:
        await db[step_collection].replace_one(
            {"_id": step.id},
            doc,
            upsert=True,
        )
    return True


async def update_step(
    db: Any,
    step_collection: str,
    step: Step,
) -> bool:
    """更新 step 表一行（与 save_step 同，按 id 覆盖）"""
    return await save_step(db, step_collection, step)


async def load_steps_by_workflow(
    db: Any,
    step_collection: str,
    workflow_id: str,
) -> List[Step]:
    """按 parent_workflow_id 查询该 workflow 下所有 step，按链顺序排列"""
    cursor = db[step_collection].find({"parent_workflow_id": workflow_id})
    docs = await cursor.to_list(length=None)
    steps = [_doc_to_step(d) for d in docs]
    if not steps:
        return []
    # 按 previous_step_id / next_step_id 排成链序
    by_id = {s.id: s for s in steps}
    ordered = []
    # 找链头：previous_step_id 为空或不在本 workflow 的 step 中
    head = None
    for s in steps:
        if not s.previous_step_id or s.previous_step_id not in by_id:
            head = s
            break
    if not head:
        return steps  # 成环或异常，返回原序
    current = head
    while current:
        ordered.append(current)
        next_id = current.next_step_id
        current = by_id.get(next_id) if next_id else None
    return ordered


async def delete_step_from_db(
    db: Any,
    step_collection: str,
    step_id: str,
) -> bool:
    """删除 step 表一行"""
    try:
        from bson import ObjectId

        res = await db[step_collection].delete_one({"_id": ObjectId(step_id)})
    except Exception:
        res = await db[step_collection].delete_one({"_id": step_id})
    return res.deleted_count > 0


async def delete_steps_by_workflow(
    db: Any,
    step_collection: str,
    workflow_id: str,
) -> int:
    """删除该 workflow 下所有 step"""
    res = await db[step_collection].delete_many({"parent_workflow_id": workflow_id})
    return res.deleted_count


# ---------- Task 表 ----------


async def save_task(
    db: Any,
    task_collection: str,
    task: Task,
) -> bool:
    """写入或覆盖 task 表一行"""
    doc = _task_to_doc(task)
    try:
        from bson import ObjectId

        await db[task_collection].replace_one(
            {"_id": ObjectId(task.id)},
            doc,
            upsert=True,
        )
    except Exception:
        await db[task_collection].replace_one(
            {"_id": task.id},
            doc,
            upsert=True,
        )
    return True


async def update_task(
    db: Any,
    task_collection: str,
    task: Task,
) -> bool:
    """更新 task 表一行"""
    return await save_task(db, task_collection, task)


async def update_task_result(
    db: Any,
    task_collection: str,
    task_id: str,
    run_status: str,
    result_content: TaskResultContent,
) -> bool:
    """仅更新 task 的 run_status 与 result（执行完成后调用）"""
    now = datetime.utcnow()
    try:
        from bson import ObjectId

        res = await db[task_collection].update_one(
            {"_id": ObjectId(task_id)},
            {
                "$set": {
                    "run_status": run_status,
                    "result": result_content.to_dict(),
                    "updated_at": now,
                }
            },
        )
    except Exception:
        res = await db[task_collection].update_one(
            {"_id": task_id},
            {
                "$set": {
                    "run_status": run_status,
                    "result": result_content.to_dict(),
                    "updated_at": now,
                }
            },
        )
    return res.matched_count > 0


async def load_tasks_by_step(
    db: Any,
    task_collection: str,
    step_id: str,
) -> List[Task]:
    """按 parent_step_id 查询该 step 下所有 task"""
    cursor = db[task_collection].find({"parent_step_id": step_id})
    docs = await cursor.to_list(length=None)
    return [_doc_to_task(d) for d in docs]


async def delete_task_from_db(
    db: Any,
    task_collection: str,
    task_id: str,
) -> bool:
    """删除 task 表一行"""
    try:
        from bson import ObjectId

        res = await db[task_collection].delete_one({"_id": ObjectId(task_id)})
    except Exception:
        res = await db[task_collection].delete_one({"_id": task_id})
    return res.deleted_count > 0


async def delete_tasks_by_step(
    db: Any,
    task_collection: str,
    step_id: str,
) -> int:
    """删除该 step 下所有 task"""
    res = await db[task_collection].delete_many({"parent_step_id": step_id})
    return res.deleted_count


async def delete_tasks_by_workflow(
    db: Any,
    task_collection: str,
    workflow_id: str,
) -> int:
    """删除该 workflow 下所有 task"""
    res = await db[task_collection].delete_many({"parent_workflow_id": workflow_id})
    return res.deleted_count


# ---------- 组装与级联删除 ----------


async def load_workflow_from_db(
    db: Any,
    workflow_collection: str,
    step_collection: str,
    task_collection: str,
    workflow_id: str,
) -> Optional[Workflow]:
    """
    从三张表组装完整 Workflow：workflow 表 + step 表（parent_workflow_id）+ task 表（parent_step_id）。
    """
    w = await load_workflow_meta(db, workflow_collection, workflow_id)
    if not w:
        return None
    steps = await load_steps_by_workflow(db, step_collection, workflow_id)
    for s in steps:
        s.tasks = await load_tasks_by_step(db, task_collection, s.id)
        for t in s.tasks:
            if t.result:
                w.task_results[t.id] = t.result
    w.steps = steps
    return w


async def delete_workflow_cascade(
    db: Any,
    workflow_collection: str,
    step_collection: str,
    task_collection: str,
    workflow_id: str,
) -> bool:
    """级联删除：workflow 表一行 + 该 workflow 下所有 step + 所有 task"""
    await delete_tasks_by_workflow(db, task_collection, workflow_id)
    await delete_steps_by_workflow(db, step_collection, workflow_id)
    try:
        from bson import ObjectId

        res = await db[workflow_collection].delete_one({"_id": ObjectId(workflow_id)})
    except Exception:
        res = await db[workflow_collection].delete_one({"_id": workflow_id})
    return res.deleted_count > 0


async def delete_step_cascade(
    db: Any,
    step_collection: str,
    task_collection: str,
    step_id: str,
) -> bool:
    """级联删除：step 表一行 + 该 step 下所有 task"""
    await delete_tasks_by_step(db, task_collection, step_id)
    return await delete_step_from_db(db, step_collection, step_id)


# ---------- Spec 单表（可选，用于仅存 spec 的场景） ----------


async def _find_workflow_doc(
    db: Any, collection_name: str, workflow_id: str
) -> Optional[Any]:
    doc = await _find_doc_by_id(db, collection_name, workflow_id)
    return doc


async def save_workflow_spec(
    db: Any,
    collection_name: str,
    spec: WorkflowSpec,
    workflow_id: Optional[str] = None,
    name: Optional[str] = None,
    creator: Optional[str] = None,
    description: Optional[str] = None,
) -> str:
    """
    将 WorkflowSpec 写入 workflow 表（单条文档含 spec）。
    若已用三表存储，workflow 表仅存元数据，可不使用本函数。
    """
    from bson import ObjectId

    now = datetime.utcnow()
    doc = {
        "name": name if name is not None else spec.name,
        "description": description or "",
        "creator": creator or "",
        "spec": workflow_spec_to_dict(spec),
        "created_at": now,
        "updated_at": now,
    }
    if workflow_id:
        doc["_id"] = workflow_id
        await db[collection_name].replace_one(
            {"_id": workflow_id},
            doc,
            upsert=True,
        )
        return workflow_id
    res = await db[collection_name].insert_one(doc)
    return str(res.inserted_id)


async def load_workflow_spec(
    db: Any,
    collection_name: str,
    workflow_id: str,
) -> Optional[WorkflowSpec]:
    doc = await _find_workflow_doc(db, collection_name, workflow_id)
    if not doc:
        return None
    spec_dict = doc.get("spec")
    if not spec_dict:
        return None
    return dict_to_workflow_spec(spec_dict)


async def update_workflow_spec(
    db: Any,
    collection_name: str,
    workflow_id: str,
    spec: WorkflowSpec,
    name: Optional[str] = None,
) -> bool:
    from bson import ObjectId

    now = datetime.utcnow()
    update = {"spec": workflow_spec_to_dict(spec), "updated_at": now}
    if name is not None:
        update["name"] = name
    try:
        res = await db[collection_name].update_one(
            {"_id": ObjectId(workflow_id)},
            {"$set": update},
        )
    except Exception:
        res = await db[collection_name].update_one(
            {"_id": workflow_id},
            {"$set": update},
        )
    return res.modified_count > 0 or res.matched_count > 0


async def delete_workflow_from_db(
    db: Any,
    collection_name: str,
    workflow_id: str,
) -> bool:
    """仅删 workflow 表一行（不级联）。三表模式下请用 delete_workflow_cascade。"""
    try:
        from bson import ObjectId

        res = await db[collection_name].delete_one({"_id": ObjectId(workflow_id)})
    except Exception:
        res = await db[collection_name].delete_one({"_id": workflow_id})
    return res.deleted_count > 0


async def save_workflow_task_result(
    db: Any,
    task_collection: str,
    task_id: str,
    run_status: str,
    result_content: TaskResultContent,
) -> bool:
    """将 task 执行结果写入 task 表（更新 run_status 与 result）"""
    return await update_task_result(
        db, task_collection, task_id, run_status, result_content
    )


# ---------- 单表整份读写（可选） ----------


def workflow_to_doc(w: Workflow) -> Dict[str, Any]:
    """Workflow 整份导出为单文档；三表模式下可用 save_workflow_meta + save_step + save_task 分表写入"""
    from ..ai_spec import workflow_to_spec as _workflow_to_spec

    now = datetime.utcnow()
    return {
        "_id": w.id,
        "name": w.name,
        "description": w.description or "",
        "creator": w.creator or "",
        "created_at": w.created_at,
        "first_step_id": w.first_step_id or "",
        "end_step_id": w.end_step_id or "",
        "updated_at": now,
        "step_ids": w.step_ids,
        "steps": [_step_to_doc(s) for s in w.steps],
        "task_results": {tid: tr.to_dict() for tid, tr in w.task_results.items()},
        "spec": workflow_spec_to_dict(_workflow_to_spec(w)),
    }


def doc_to_workflow(doc: Dict[str, Any]) -> Workflow:
    """从单文档还原 Workflow；三表模式下请用 load_workflow_from_db"""
    workflow_id = str(doc.get("_id", "") or doc.get("id", ""))
    created_at = doc.get("created_at")
    steps_data = doc.get("steps") or []
    steps = []
    for s in steps_data:
        step = _doc_to_step(s)
        step.tasks = [_doc_to_task(t) for t in s.get("tasks") or []]
        steps.append(step)
    w = _doc_to_workflow_meta(doc)
    w.steps = steps
    raw = doc.get("task_results") or {}
    w.task_results = {str(k): TaskResultContent.from_dict(v) for k, v in raw.items()}
    return w
