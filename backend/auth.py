# -*- coding: utf-8 -*-
"""认证：ERP 登录接口（可配置）+ pass_hd 本地密码校验 + 开发兜底；JWT 签发与校验。"""
import base64
import datetime
import hashlib
import jwt
import requests

from config import (JWT_SECRET, JWT_EXPIRE_HOURS, ERP_LOGIN_URL,
                    APP_DEV_FALLBACK, APP_DEV_PWD, APP_ADMIN_EMP_NOS)
from hr import get_employee
from db import query, execute, vb

ALG = "HS256"


def _verify_via_erp(username, password):
    """调用 ERP 登录接口。未配置 ERP_LOGIN_URL 时返回 None（交给兜底）。
    默认契约：POST {username,password} -> HTTP 200 且 (success 为真 / code=0 / 含 token) 视为成功。
    若你们 ERP 返回格式不同，改下方判断即可。"""
    if not ERP_LOGIN_URL:
        return None
    try:
        resp = requests.post(ERP_LOGIN_URL, json={"username": username, "password": password}, timeout=8)
        if resp.status_code != 200:
            return None
        body = resp.json()
        if body.get("success") or body.get("code") == 0 or body.get("token"):
            return body
        return None
    except Exception:
        return None


def _verify_dev(username, password):
    """开发兜底：仅当 APP_DEV_FALLBACK=1 且口令匹配，且账号为有效员工。"""
    if not APP_DEV_FALLBACK:
        return None
    if password != APP_DEV_PWD:
        return None
    emp = get_employee(username)
    if emp and emp.get("active"):
        return {"dev": True}
    return None


# ---------- 本地密码校验（直连 pass_hd.pwd，无需 ERP 接口） ----------
def _pwd_candidates(password):
    """ERP 密码参与哈希时可能用不同编码，按 utf-8 / gbk / latin-1 依次尝试。"""
    out = []
    for enc in ("utf-8", "gbk", "latin-1"):
        try:
            b = password.encode(enc)
        except Exception:
            continue
        if b not in out:
            out.append(b)
    return out


def _check_pwd(stored, password):
    """兼容 pass_hd.pwd 的三种历史格式：bcrypt / MD5(32位hex) / Base64(SHA1,28字符)。"""
    if not stored or not password:
        return False
    if isinstance(stored, bytes):
        try:
            stored = stored.decode("latin-1")
        except Exception:
            return False
    s = stored.strip()
    if not s:
        return False

    # 1) bcrypt: $2a$ / $2b$ / $2y$
    if s[:4] in ("$2a$", "$2b$", "$2y$"):
        try:
            import bcrypt
        except Exception:
            return False
        for b in _pwd_candidates(password):
            try:
                if bcrypt.checkpw(b, s.encode("utf-8")):
                    return True
            except Exception:
                continue
        return False

    # 2) MD5 hex（32 位十六进制）
    if len(s) == 32 and all(c in "0123456789abcdefABCDEF" for c in s):
        for b in _pwd_candidates(password):
            if hashlib.md5(b).hexdigest().lower() == s.lower():
                return True
        return False

    # 3) Base64(SHA1)（28 字符 = 20 字节摘要）
    if len(s) == 28:
        try:
            raw = base64.b64decode(s, validate=False)
        except Exception:
            return False
        if len(raw) == 20:
            for b in _pwd_candidates(password):
                if hashlib.sha1(b).digest() == raw:
                    return True
        return False

    return False


def _verify_local(username, password):
    """用 pass_hd.pwd 本地校验员工真实 ERP 密码。
    pwd 是 varchar，hex 取原始字节（避免字符集转码破坏 bcrypt/base64 内容）。"""
    try:
        rows = query(
            f"SELECT {vb('pwd', 400)} AS pwd_raw FROM dbo.pass_hd "
            "WHERE user_name=%s AND ISNULL(delmark,'N')='N'",
            (username,))
    except Exception:
        return None
    if not rows:
        return None
    stored = rows[0].get("pwd_raw")
    if isinstance(stored, str):
        stored = stored.encode("latin-1", errors="replace")
    return {"local": True} if _check_pwd(stored, password) else None


def authenticate(username, password):
    """返回员工档案 dict，失败返回 None。
    校验优先级：ERP 登录接口（若配置）→ pass_hd 本地密码 → 开发兜底。"""
    res = _verify_via_erp(username, password)
    if res is None:
        res = _verify_local(username, password)
    if res is None:
        res = _verify_dev(username, password)
    if res is None:
        return None
    return get_employee(username)


# ---------- 授权标志 ----------
def get_admin_emp_nos():
    """管理员工号集合：环境变量优先，否则读 meal_config.admin_emp_nos。
    表尚未创建/无权限时优雅降级为仅环境变量。"""
    env = [x.strip() for x in (APP_ADMIN_EMP_NOS or "").split(",") if x.strip()]
    db_set = []
    try:
        rows = query("SELECT cfg_value FROM dbo.meal_config WHERE cfg_key='admin_emp_nos'")
        db_val = (rows[0]["cfg_value"] if rows else "") or ""
        db_set = [x.strip() for x in db_val.split(",") if x.strip()]
    except Exception:
        pass  # 表未创建时忽略
    merged = list(dict.fromkeys(env + db_set))  # 去重保序
    return set(merged)


def get_user_flags(emp_no):
    admins = get_admin_emp_nos()
    is_admin = emp_no in admins
    can_stat = is_admin
    try:
        stat_rows = query("SELECT emp_no FROM dbo.meal_stat_auth WHERE emp_no=%s", (emp_no,))
        can_stat = is_admin or bool(stat_rows)
    except Exception:
        pass  # 表未创建时忽略
    return {"is_admin": is_admin, "can_stat": can_stat}


def create_token(emp_no, name, deptno, dept_name):
    now = datetime.datetime.utcnow()
    payload = {
        "sub": emp_no,
        "name": name,
        "deptno": deptno,
        "dept_name": dept_name,
        "iat": now,
        "exp": now + datetime.timedelta(hours=JWT_EXPIRE_HOURS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=ALG)


def decode_token(token):
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[ALG])
    except Exception:
        return None
