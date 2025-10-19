import os
import sys

def get_resource_root():
    """
    返回资源根目录：
    - 打包态：优先使用 dist 顶层（存在 data/static/styles 任一），否则使用 _internal；最后回退 exe 同级
    - 开发态：使用项目根目录（utils 的上一级）
    """
    # 开发态
    if not getattr(sys, "frozen", False):
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    # 打包态
    base = os.path.dirname(sys.executable)
    top_has_resources = any(
        os.path.isdir(os.path.join(base, d)) for d in ("data", "static", "styles")
    )
    if top_has_resources:
        return base
    internal = os.path.join(base, "_internal")
    internal_has_resources = any(
        os.path.isdir(os.path.join(internal, d)) for d in ("data", "static", "styles")
    )
    if internal_has_resources:
        return internal
    return base

# 统一的资源根目录
file_abs_path = get_resource_root()

# 相对路径常量（保持兼容）
default_scripts_rel_path = r"data\default_scripts.json"
default_config_rel_path = r"data\default_config.json"
real_scripts_rel_path = r"data\scripts.json"
real_config_rel_path = r"data\config.json"
index_file = r"data\index.json"

# 绝对路径常量（DataAdapter/工具模块使用）
default_scripts_abs_path = os.path.join(file_abs_path, default_scripts_rel_path)
default_config_abs_path = os.path.join(file_abs_path, default_config_rel_path)
real_scripts_abs_path = os.path.join(file_abs_path, real_scripts_rel_path)
real_config_abs_path = os.path.join(file_abs_path, real_config_rel_path)
index_abs_path = os.path.join(file_abs_path, index_file)

user_id = None