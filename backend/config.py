# -*- coding: utf-8 -*-
"""应用配置：优先读环境变量 / .env，兜底读 Windows 机器级注册表（与现有 ERP 脚本一致）。"""
import os
import sys

try:
    from dotenv import load_dotenv
    # 确定性加载：项目根(canteen/.env) 与 backend/.env 都找，避免受 CWD 影响
    _backend_dir = os.path.dirname(os.path.abspath(__file__))
    _root_dir = os.path.dirname(_backend_dir)
    for _p in (os.path.join(_root_dir, ".env"), os.path.join(_backend_dir, ".env")):
        if os.path.exists(_p):
            load_dotenv(_p, override=False)
except Exception:
    pass

# ---- MSSQL 连接（与 mssql_connect.py 同一来源）----
def _reg(key):
    try:
        import winreg
        with winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment",
        ) as hk:
            return winreg.QueryValueEx(hk, key)[0]
    except Exception:
        return None

def _env_or_reg(key):
    v = os.environ.get(key)
    if v:
        return v
    return _reg(key)

MSSQL_SERVER = _env_or_reg("MSSQL_servername") or "192.168.129.8"
MSSQL_DB     = _env_or_reg("MSSQL_dbname") or "erpdatanew"
MSSQL_LOGIN  = _env_or_reg("MSSQL_login") or "erpadmin"
MSSQL_PWD    = _env_or_reg("MSSQL_pwd") or ""
# 客户端字符集：用 UTF-8 才能无损写入/读出 nvarchar 里的越南文（ễ/ơ 等，GBK 编不了）。
# varchar 列（GBK 存储，如 pass_hd.name_desc / sys_dept.deptdesc）读出来会乱，
# 统一用 CONVERT(VARBINARY(...)) 取原始字节后按 GBK 解码（见 db.dec_gbk）。
MSSQL_CHARSET = os.environ.get("MSSQL_CHARSET", "UTF-8")

# ---- 应用设置 ----
JWT_SECRET = os.environ.get("JWT_SECRET", "change-me-canteen-dev-secret")
JWT_EXPIRE_HOURS = int(os.environ.get("JWT_EXPIRE_HOURS", "12"))

# ERP 登录接口（用户选择走 ERP 登录）。未配置时只能走开发兜底。
ERP_LOGIN_URL = os.environ.get("ERP_LOGIN_URL", "")

# 开发兜底：仅在显式开启时使用，用统一口令登录任意员工账号，便于本地联调。生产务必关闭。
APP_DEV_FALLBACK = os.environ.get("APP_DEV_FALLBACK", "0") == "1"
APP_DEV_PWD = os.environ.get("APP_DEV_PWD", "123456")

# 首次启动注入的管理员工号（逗号分隔）。也可在 meal_config.admin_emp_nos 维护。
APP_ADMIN_EMP_NOS = os.environ.get("APP_ADMIN_EMP_NOS", "")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.environ.get("FRONTEND_DIR", os.path.join(BASE_DIR, "..", "frontend"))
