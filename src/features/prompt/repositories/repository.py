"""
Prompt MongoDB 持久化

存储用户创建的 prompt 模板。
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from ..models.models import PromptTemplate, PromptVar, PromptSource


def _template_to_doc(t: PromptTemplate) -> Dict[str, Any]:
    return {
        "_id": t.id,
        "name": t.name,
        "template": t.template,
        "description": t.description,
        "source": t.source,
        "variables": [
            {"name": v.name, "description": v.description,
             "default": v.default, "required": v.required}
            for v in t.variables
        ],
        "tags": t.tags,
        "created_at": t.created_at,
        "updated_at": t.updated_at,
    }


def _doc_to_template(doc: Dict[str, Any]) -> PromptTemplate:
    variables = [
        PromptVar(
            name=v.get("name", ""),
            description=v.get("description", ""),
            default=v.get("default"),
            required=v.get("required", False),
        )
        for v in doc.get("variables") or []
    ]
    return PromptTemplate(
        id=str(doc.get("_id", "")),
        name=doc.get("name", ""),
        template=doc.get("template", ""),
        description=doc.get("description", ""),
        source=doc.get("source", PromptSource.USER),
        variables=variables,
        tags=doc.get("tags") or [],
        created_at=doc.get("created_at"),
        updated_at=doc.get("updated_at"),
    )


async def save_prompt(db: Any, collection: str, template: PromptTemplate) -> bool:
    doc = _template_to_doc(template)
    await db[collection].replace_one({"_id": template.id}, doc, upsert=True)
    return True


async def load_prompt(db: Any, collection: str, prompt_id: str) -> Optional[PromptTemplate]:
    doc = await db[collection].find_one({"_id": prompt_id})
    if not doc:
        return None
    return _doc_to_template(doc)


async def load_prompt_by_name(db: Any, collection: str, name: str) -> Optional[PromptTemplate]:
    doc = await db[collection].find_one({"name": name})
    if not doc:
        return None
    return _doc_to_template(doc)


async def update_prompt(db: Any, collection: str, template: PromptTemplate) -> bool:
    template.updated_at = datetime.utcnow()
    doc = _template_to_doc(template)
    res = await db[collection].replace_one({"_id": template.id}, doc)
    return res.matched_count > 0


async def delete_prompt(db: Any, collection: str, prompt_id: str) -> bool:
    res = await db[collection].delete_one({"_id": prompt_id})
    return res.deleted_count > 0


async def list_prompts(
    db: Any,
    collection: str,
    source: Optional[str] = None,
    tag: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> List[PromptTemplate]:
    query: Dict[str, Any] = {}
    if source:
        query["source"] = source
    if tag:
        query["tags"] = tag
    cursor = (
        db[collection]
        .find(query)
        .sort("updated_at", -1)
        .skip(offset)
        .limit(limit)
    )
    docs = await cursor.to_list(length=limit)
    return [_doc_to_template(d) for d in docs]
