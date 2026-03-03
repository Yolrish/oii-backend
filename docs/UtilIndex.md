# 会话需求记录

## 项目前提

- **技术栈**: FastAPI + MongoDB
- **主要用途**: AI 服务后端
- **模块架构**: 功能模块位于 `/src/packages` 下
- **模块要求**:
  - 每个功能模块需**独立**（可单独维护、低耦合）
  - 每个功能模块需具备**对外接口**（可被其他模块或外部调用）

## .env 加载规范

- **启动时**：`import load_env` 将项目根 `.env` 加载到 `os.environ`
- **优先级**：内存（os.environ）> 模块包 `.env` > 默认值
- **新模块**：在 config 中调用 `load_module_env(__file__)` 后使用 `os.getenv()`
