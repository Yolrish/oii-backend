# Prompt 管理模块

多来源统一管理 prompt：builtin（代码内置）+ user（MongoDB）+ external（第三方预留）。

## 模块结构

```
features/prompt/
├── configs/config.py              # 集合名等
├── models/models.py               # PromptTemplate、PromptVar、PromptSource
├── providers/
│   ├── builtin.py                 # 内置 prompt（代码定义，不可 API 删改）
│   └── external.py                # 第三方平台接口（预留）
├── repositories/repository.py     # MongoDB CRUD（user prompt）
├── services/service.py            # PromptService（多来源统一接口）
├── api/routes.py                  # HTTP API
└── README.md
```

## 三种来源

| 来源 | 存储 | 可 CRUD | 优先级 |
|------|------|---------|--------|
| builtin | 代码内存 | 不可 | 最低 |
| user | MongoDB | 可 | 最高（同名覆盖 builtin） |
| external | 第三方平台 | 只读 | 中 |

## HTTP API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/prompts` | 列出所有 prompt（合并三种来源） |
| GET | `/api/v1/prompts/{name}` | 按名称获取 |
| POST | `/api/v1/prompts/render` | 渲染模板 |
| POST | `/api/v1/prompts` | 创建 user prompt |
| PUT | `/api/v1/prompts/{id}` | 更新 user prompt |
| DELETE | `/api/v1/prompts/{id}` | 删除 user prompt |

## 内部调用

```python
from core.mongodb import get_database
from features.prompt import create_prompt_service

db = get_database()
svc = create_prompt_service(db)

# 获取并渲染
text = await svc.render("video_assistant")

# 带变量
text = await svc.render("custom_role", role="翻译专家")

# 组合
text = await svc.compose(["default_with_tools", "video_assistant"])

# 列出所有
all_prompts = await svc.list_all(tag="tools")
```

## 与 chat 的集成

创建 session 时通过 `prompt_name` 指定：

```json
POST /api/v1/chat/sessions
{
  "title": "视频助手",
  "prompt_name": "video_assistant",
  "use_tools": true
}
```
