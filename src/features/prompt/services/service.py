"""
Prompt 服务

多来源统一接口：builtin + user DB + external（预留）
查询优先级：user 同名覆盖 builtin，external 按需拉取。
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from ..configs.config import PromptConfig
from ..models.models import PromptTemplate, PromptSource
from ..providers.builtin import get_builtin_prompt, get_builtin_prompts, get_system_guard
from ..providers.external import ExternalPromptProvider
from ..repositories import repository as repo


class PromptService:
    """
    Prompt 管理服务

    统一管理三种来源的 prompt：
    - builtin：代码内置，启动时加载
    - user：用户通过 API 创建，存 MongoDB
    - external：第三方平台（预留）

    查询优先级：user 同名 > builtin（用户可覆盖内置）
    """

    def __init__(
        self,
        db: Any,
        config: Optional[PromptConfig] = None,
        external_provider: Optional[ExternalPromptProvider] = None,
    ):
        self.db = db
        self.config = config or PromptConfig.from_env()
        self.external = external_provider

    # ==================== 查询（多来源合并） ====================

    async def get(self, name: str) -> Optional[PromptTemplate]:
        """
        按名称获取 prompt（优先级：user > builtin > external）
        """
        # 1. 查 user DB
        tpl = await repo.load_prompt_by_name(self.db, self.config.collection, name)
        if tpl:
            return tpl
        # 2. 查 builtin
        tpl = get_builtin_prompt(name)
        if tpl:
            return tpl
        # 3. 查 external
        if self.external:
            tpl = await self.external.get_prompt(name)
            if tpl:
                return tpl
        return None

    async def list_all(
        self,
        source: Optional[str] = None,
        tag: Optional[str] = None,
    ) -> List[PromptTemplate]:
        """
        列出所有 prompt（合并 builtin + user + external）

        可按 source 或 tag 筛选。
        """
        result: Dict[str, PromptTemplate] = {}

        # builtin（底层）
        if source is None or source == PromptSource.BUILTIN:
            for p in get_builtin_prompts(tag=tag):
                result[p.name] = p

        # user DB（覆盖同名 builtin）
        if source is None or source == PromptSource.USER:
            db_prompts = await repo.list_prompts(
                self.db, self.config.collection, source=PromptSource.USER, tag=tag,
            )
            for p in db_prompts:
                result[p.name] = p

        # external
        if self.external and (source is None or source == PromptSource.EXTERNAL):
            try:
                ext_prompts = await self.external.list_prompts(tag=tag)
                for p in ext_prompts:
                    if p.name not in result:
                        result[p.name] = p
            except Exception:
                pass

        return list(result.values())

    # ==================== 系统 prompt 组装 ====================

    async def build_system_prompt(
        self,
        prompt_name: str = "",
        prompt_vars: Optional[Dict[str, Any]] = None,
        raw_system_prompt: str = "",
        include_guard: bool = True,
    ) -> str:
        """
        组装最终 system prompt，注入安全底线

        拼接顺序：[guard] + [业务 prompt]
        业务 prompt 优先级：raw_system_prompt > prompt_name 渲染结果

        Args:
            prompt_name: 预定义 prompt 模板名称
            prompt_vars: 模板变量
            raw_system_prompt: 直接传入的 system prompt
            include_guard: 是否注入安全底线（默认 True）
        """
        parts = []

        # 1. 安全底线（最高优先级，放最前面）
        if include_guard:
            guard = get_system_guard()
            if guard:
                parts.append(guard.render())

        # 2. 业务 prompt
        biz_prompt = raw_system_prompt
        if not biz_prompt and prompt_name:
            biz_prompt = await self.render_or_default(
                prompt_name, default="", **(prompt_vars or {}),
            )
        if biz_prompt:
            parts.append(biz_prompt)

        return "\n\n".join(parts)

    # ==================== 渲染 ====================

    async def render(self, name: str, **kwargs: Any) -> str:
        """按名称获取并渲染 prompt"""
        tpl = await self.get(name)
        if not tpl:
            raise ValueError(f"Prompt not found: {name}")
        return tpl.render(**kwargs)

    async def render_or_default(
        self, name: str, default: str = "", **kwargs: Any,
    ) -> str:
        """按名称获取并渲染，不存在时返回 default"""
        tpl = await self.get(name)
        if not tpl:
            return default
        return tpl.render(**kwargs)

    async def compose(
        self, names: List[str], separator: str = "\n\n", **kwargs: Any,
    ) -> str:
        """组合多个 prompt 模板"""
        parts = []
        for name in names:
            tpl = await self.get(name)
            if tpl:
                parts.append(tpl.render(**kwargs))
        return separator.join(parts)

    # ==================== 用户 CRUD ====================

    async def create(
        self,
        name: str,
        template: str,
        description: str = "",
        variables: Optional[List[Dict[str, Any]]] = None,
        tags: Optional[List[str]] = None,
    ) -> PromptTemplate:
        """创建用户 prompt"""
        from ..models.models import PromptVar

        vars_list = []
        if variables:
            for v in variables:
                vars_list.append(PromptVar(
                    name=v["name"],
                    description=v.get("description", ""),
                    default=v.get("default"),
                    required=v.get("required", False),
                ))

        tpl = PromptTemplate(
            name=name,
            template=template,
            description=description,
            source=PromptSource.USER,
            variables=vars_list,
            tags=tags or [],
        )
        await repo.save_prompt(self.db, self.config.collection, tpl)
        return tpl

    async def update(
        self,
        prompt_id: str,
        template: Optional[str] = None,
        description: Optional[str] = None,
        variables: Optional[List[Dict[str, Any]]] = None,
        tags: Optional[List[str]] = None,
    ) -> Optional[PromptTemplate]:
        """更新用户 prompt（不允许修改 builtin）"""
        tpl = await repo.load_prompt(self.db, self.config.collection, prompt_id)
        if not tpl:
            return None
        if template is not None:
            tpl.template = template
        if description is not None:
            tpl.description = description
        if variables is not None:
            from ..models.models import PromptVar
            tpl.variables = [
                PromptVar(
                    name=v["name"],
                    description=v.get("description", ""),
                    default=v.get("default"),
                    required=v.get("required", False),
                )
                for v in variables
            ]
        if tags is not None:
            tpl.tags = tags
        await repo.update_prompt(self.db, self.config.collection, tpl)
        return tpl

    async def delete(self, prompt_id: str) -> bool:
        """删除用户 prompt（不允许删除 builtin）"""
        return await repo.delete_prompt(self.db, self.config.collection, prompt_id)

    async def get_by_id(self, prompt_id: str) -> Optional[PromptTemplate]:
        """按 ID 获取（仅 DB 中的）"""
        return await repo.load_prompt(self.db, self.config.collection, prompt_id)


def create_prompt_service(
    db: Any,
    config: Optional[PromptConfig] = None,
    external_provider: Optional[ExternalPromptProvider] = None,
) -> PromptService:
    """创建 PromptService"""
    return PromptService(db, config, external_provider)
