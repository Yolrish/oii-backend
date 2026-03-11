"""
用户 MongoDB 持久化
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from ..models.models import User, UserRole


def _user_to_doc(u: User) -> Dict[str, Any]:
    return {
        "_id": u.id,
        "auth0_id": u.auth0_id,
        "email": u.email,
        "nickname": u.nickname,
        "avatar": u.avatar,
        "role": u.role,
        "permissions": u.permissions,
        "quota": u.quota,
        "subscription": u.subscription,
        "preferences": u.preferences or {},
        "created_at": u.created_at,
        "updated_at": u.updated_at,
        "last_login_at": u.last_login_at,
    }


def _doc_to_user(doc: Dict[str, Any]) -> User:
    return User(
        id=str(doc.get("_id", "")),
        auth0_id=doc.get("auth0_id", ""),
        email=doc.get("email", ""),
        nickname=doc.get("nickname", ""),
        avatar=doc.get("avatar", ""),
        role=doc.get("role", UserRole.USER),
        permissions=doc.get("permissions") or [],
        quota=doc.get("quota", 0),
        subscription=doc.get("subscription", "free"),
        preferences=doc.get("preferences") or {},
        created_at=doc.get("created_at"),
        updated_at=doc.get("updated_at"),
        last_login_at=doc.get("last_login_at"),
    )


async def save_user(db: Any, collection: str, user: User) -> bool:
    doc = _user_to_doc(user)
    await db[collection].replace_one({"_id": user.id}, doc, upsert=True)
    return True


async def load_user(db: Any, collection: str, user_id: str) -> Optional[User]:
    doc = await db[collection].find_one({"_id": user_id})
    if not doc:
        return None
    return _doc_to_user(doc)


async def load_user_by_auth0_id(db: Any, collection: str, auth0_id: str) -> Optional[User]:
    doc = await db[collection].find_one({"auth0_id": auth0_id})
    if not doc:
        return None
    return _doc_to_user(doc)


async def update_user(db: Any, collection: str, user: User) -> bool:
    user.updated_at = datetime.utcnow()
    doc = _user_to_doc(user)
    res = await db[collection].replace_one({"_id": user.id}, doc)
    return res.matched_count > 0


async def delete_user(db: Any, collection: str, user_id: str) -> bool:
    res = await db[collection].delete_one({"_id": user_id})
    return res.deleted_count > 0


async def list_users(
    db: Any,
    collection: str,
    role: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
) -> List[User]:
    query: Dict[str, Any] = {}
    if role:
        query["role"] = role
    cursor = (
        db[collection]
        .find(query)
        .sort("created_at", -1)
        .skip(offset)
        .limit(limit)
    )
    docs = await cursor.to_list(length=limit)
    return [_doc_to_user(d) for d in docs]
