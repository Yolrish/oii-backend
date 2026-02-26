"""
基于 AI Spec 的 Workflow 持久化

workflow 实例文档存储：id、创建者、创建时间、名称、描述、step_ids、steps（含 task 列表）、task_results。
支持从完整文档反序列化为 Workflow，或从 spec 解析后叠加 meta 与 task_results。
"""
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..models.models import (
    Workflow,
    Step,
    Task,
    TaskResultContent,
)
from ..ai_spec import (
    WorkflowSpec,
    workflow_spec_to_dict,
    dict_to_workflow_spec,
    parse_ai_workflow,
)


async def _find_workflow_doc(db: Any, collection_name: str, workflow_id: str) -> Optional[Any]:
    """按 workflow_id 查找文档；支持 _id 为 ObjectId 或 str"""
    try:
        from bson import ObjectId
        doc = await db[collection_name].find_one({"_id": ObjectId(workflow_id)})
    except Exception:
        doc = None
    if doc is None:
        doc = await db[collection_name].find_one({"_id": workflow_id})
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
    将 WorkflowSpec（AI 指定格式）写入数据库，作为持久化源。
    可同时写入 name、creator、description；返回文档 _id。
    """
    from bson import ObjectId

    now = datetime.utcnow()
    doc = {
        "name": name if name is not None else spec.name,
        "description": description or "",
        "creator": creator or "",
        "spec": workflow_spec_to_dict(spec),
        "task_results": {},
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
    """从数据库按 id 加载 WorkflowSpec（AI 指定格式）；支持 _id 为字符串或 ObjectId"""
    doc = await _find_workflow_doc(db, collection_name, workflow_id)
    if not doc:
        return None
    spec_dict = doc.get("spec")
    if not spec_dict:
        return None
    return dict_to_workflow_spec(spec_dict)


def _doc_task_results_to_map(doc: Any) -> Dict[str, TaskResultContent]:
    """从文档的 task_results 字段转为 Dict[str, TaskResultContent]"""
    raw = doc.get("task_results") or {}
    return {
        str(k): TaskResultContent.from_dict(v)
        for k, v in raw.items()
    }


# ---------- 完整 workflow 实例序列化（含 id、创建者、时间、描述、关联 id、运行状态、结果） ----------


def _task_to_doc(t: Task) -> Dict[str, Any]:
    """Task → 可落库 dict"""
    return {
        "id": t.id,
        "name": t.name,
        "description": t.description or "",
        "parent_step_id": t.parent_step_id or "",
        "parent_workflow_id": t.parent_workflow_id or "",
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
    }


def _step_to_doc(s: Step, workflow_id: str) -> Dict[str, Any]:
    """Step → 可落库 dict（含 tasks）"""
    return {
        "id": s.id,
        "name": s.name,
        "description": s.description or "",
        "parent_workflow_id": s.parent_workflow_id or workflow_id,
        "previous_step_id": s.previous_step_id or "",
        "next_step_id": s.next_step_id or "",
        "creator": s.creator or "",
        "created_at": s.created_at,
        "task_ids": s.task_ids,
        "on_before_path": s.on_before_path or "",
        "on_start_path": s.on_start_path or "",
        "on_done_path": s.on_done_path or "",
        "on_retry_path": s.on_retry_path or "",
        "tasks": [_task_to_doc(t) for t in s.tasks],
    }


def workflow_to_doc(w: Workflow) -> Dict[str, Any]:
    """Workflow 实例 → 可写入 DB 的完整文档"""
    from ..ai_spec import workflow_to_spec as _workflow_to_spec
    now = datetime.utcnow()
    return {
        "_id": w.id,
        "name": w.name,
        "description": w.description or "",
        "creator": w.creator or "",
        "created_at": w.created_at,
        "updated_at": now,
        "step_ids": w.step_ids,
        "steps": [_step_to_doc(s, w.id) for s in w.steps],
        "task_results": {tid: tr.to_dict() for tid, tr in w.task_results.items()},
        "spec": workflow_spec_to_dict(_workflow_to_spec(w)),  # 兼容：可由 spec 还原结构
    }


def _doc_to_task(d: Dict[str, Any]) -> Task:
    """文档中的 task dict → Task"""
    created_at = d.get("created_at")
    result = d.get("result")
    return Task(
        id=str(d.get("id", "")),
        name=str(d.get("name", "")),
        description=str(d.get("description", "")),
        parent_step_id=str(d.get("parent_step_id", "")),
        parent_workflow_id=str(d.get("parent_workflow_id", "")),
        creator=str(d.get("creator", "")),
        created_at=created_at if isinstance(created_at, datetime) else None,
        run_status=str(d.get("run_status", "pending")),
        handler_path=str(d.get("handler_path", "")),
        params=d.get("params") or {},
        on_before_path=str(d.get("on_before_path", "")),
        on_start_path=str(d.get("on_start_path", "")),
        on_done_path=str(d.get("on_done_path", "")),
        on_retry_path=str(d.get("on_retry_path", "")),
        result=TaskResultContent.from_dict(result) if result else None,
    )


def _doc_to_step(d: Dict[str, Any], workflow_id: str) -> Step:
    """文档中的 step dict（含 tasks）→ Step"""
    created_at = d.get("created_at")
    tasks_data = d.get("tasks") or []
    return Step(
        id=str(d.get("id", "")),
        name=str(d.get("name", "")),
        description=str(d.get("description", "")),
        parent_workflow_id=str(d.get("parent_workflow_id", "") or workflow_id),
        previous_step_id=str(d.get("previous_step_id", "")),
        next_step_id=str(d.get("next_step_id", "")),
        creator=str(d.get("creator", "")),
        created_at=created_at if isinstance(created_at, datetime) else None,
        tasks=[_doc_to_task(t) for t in tasks_data],
        on_before_path=str(d.get("on_before_path", "")),
        on_start_path=str(d.get("on_start_path", "")),
        on_done_path=str(d.get("on_done_path", "")),
        on_retry_path=str(d.get("on_retry_path", "")),
    )


def doc_to_workflow(doc: Dict[str, Any]) -> Workflow:
    """完整文档 → Workflow 实例"""
    workflow_id = str(doc.get("_id", "") or doc.get("id", ""))
    created_at = doc.get("created_at")
    steps_data = doc.get("steps") or []
    w = Workflow(
        id=workflow_id,
        name=str(doc.get("name", "")),
        description=str(doc.get("description", "")),
        creator=str(doc.get("creator", "")),
        created_at=created_at if isinstance(created_at, datetime) else None,
        steps=[_doc_to_step(s, workflow_id) for s in steps_data],
        task_results=_doc_task_results_to_map(doc),
    )
    return w


async def save_workflow(
    db: Any,
    collection_name: str,
    workflow: Workflow,
) -> bool:
    """
    将完整 Workflow 实例写入数据库（含 id、创建者、创建时间、名称、描述、steps、task_results、spec）。
    """
    from bson import ObjectId
    doc = workflow_to_doc(workflow)
    try:
        await db[collection_name].replace_one(
            {"_id": ObjectId(workflow.id)},
            doc,
            upsert=True,
        )
    except Exception:
        await db[collection_name].replace_one(
            {"_id": workflow.id},
            doc,
            upsert=True,
        )
    return True


async def load_workflow_from_db(
    db: Any,
    collection_name: str,
    workflow_id: str,
) -> Optional[Any]:
    """
    从数据库加载为 Workflow 实例。
    若文档含完整 steps（含 tasks）则反序列化为完整 Workflow（id、创建者、时间、描述、关联 id、运行状态、结果等）；
    否则从 spec 解析并叠加 task_results 与文档中的 name、description、creator、created_at。
    """
    doc = await _find_workflow_doc(db, collection_name, workflow_id)
    if not doc:
        return None
    steps_data = doc.get("steps")
    if isinstance(steps_data, list) and (len(steps_data) == 0 or isinstance(steps_data[0], dict)):
        return doc_to_workflow(doc)
    spec_dict = doc.get("spec")
    if not spec_dict:
        return None
    spec = dict_to_workflow_spec(spec_dict)
    w = parse_ai_workflow(spec, workflow_id=workflow_id)
    w.task_results = _doc_task_results_to_map(doc)
    if doc.get("name") is not None:
        w.name = str(doc["name"])
    if doc.get("description") is not None:
        w.description = str(doc["description"])
    if doc.get("creator") is not None:
        w.creator = str(doc["creator"])
    if doc.get("created_at") is not None and isinstance(doc["created_at"], datetime):
        w.created_at = doc["created_at"]
    return w


async def update_workflow_spec(
    db: Any,
    collection_name: str,
    workflow_id: str,
    spec: WorkflowSpec,
    name: Optional[str] = None,
) -> bool:
    """更新已存在的 workflow 文档的 spec；支持 _id 为字符串或 ObjectId"""
    from bson import ObjectId

    now = datetime.utcnow()
    update = {
        "spec": workflow_spec_to_dict(spec),
        "updated_at": now,
    }
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


async def save_workflow_task_result(
    db: Any,
    collection_name: str,
    workflow_id: str,
    task_id: str,
    result_content: TaskResultContent,
) -> bool:
    """
    将已执行 task 的结果写入 workflow 文档的 task_results 字段。
    格式：task_results[task_id] = { "type": "text"|"image"|"video"|"audio", "content": "..." }。
    """
    from bson import ObjectId

    now = datetime.utcnow()
    payload = result_content.to_dict()
    try:
        res = await db[collection_name].update_one(
            {"_id": ObjectId(workflow_id)},
            {"$set": {f"task_results.{task_id}": payload, "updated_at": now}},
        )
    except Exception:
        res = await db[collection_name].update_one(
            {"_id": workflow_id},
            {"$set": {f"task_results.{task_id}": payload, "updated_at": now}},
        )
    return res.matched_count > 0
