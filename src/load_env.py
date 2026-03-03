"""
统一 .env 加载

加载优先级：os.environ（内存）> 模块包 .env > 默认值
- 项目启动时 import load_env 将项目根 .env 加载到 os.environ
- 各模块调用 load_module_env 时，仅补充包 .env 中尚未存在的变量（不覆盖）
"""
from pathlib import Path
from dotenv import load_dotenv

# 项目启动时最先执行：加载项目根 .env
_project_root = Path(__file__).resolve().parent.parent
load_dotenv(_project_root / ".env")


def load_module_env(module_file: str) -> None:
    """
    加载模块所在包根目录下的 .env，不覆盖 os.environ 中已有变量。

    查找规则：从模块文件所在目录向上遍历，找到父目录名为 "packages" 的子目录作为包根
    （如 packages/ffmpeg、packages/log）。非 packages 下的模块则使用模块文件所在目录。

    Args:
        module_file: 通常传入 __file__
    """
    path = Path(module_file).resolve()
    current = path.parent

    # 向上查找包根：packages/<name> 的目录
    package_root = path.parent
    while current != current.parent:
        if current.parent.name == "packages":
            package_root = current
            break
        current = current.parent

    env_path = package_root / ".env"
    if env_path.exists():
        load_dotenv(env_path, override=False)
