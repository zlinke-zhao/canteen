# -*- coding: utf-8 -*-
"""管理接口：
- 统计授权名单：管理员 或 已在 meal_stat_auth 名单内的人均可维护；
- 点餐食堂设定：仅管理员。"""
from fastapi import APIRouter, Depends, HTTPException, Query
from deps import get_current_user
from auth import get_user_flags, get_admin_emp_nos
from hr import get_employee, search_employees
from settings import (get_canteens, save_canteens, get_meal_times,
                     save_meal_times, DEFAULT_MEAL_TIMES)
from db import query, execute
from schemas import AuthAdd, CanteenSave

router = APIRouter(prefix="/api/admin", tags=["admin"])


def _require_admin(user):
    flags = get_user_flags(user["sub"])
    if not flags["is_admin"]:
        raise HTTPException(status_code=403, detail="仅管理员可操作")


def _require_auth_manager(user):
    """管理员 或 meal_stat_auth 名单内人员。"""
    flags = get_user_flags(user["sub"])
    if not flags["can_stat"]:
        raise HTTPException(status_code=403, detail="无统计授权管理权限（仅管理员或名单内人员）")


# ---------- 统计授权 ----------
def _resolve_name(emp_no, fallback=""):
    """实时从 HR 取「中文名(越南名)」，取不到退回存量值。"""
    try:
        emp = get_employee(emp_no)
        if emp and emp.get("name"):
            return emp["name"]
    except Exception:
        pass
    return fallback


@router.get("/stat-auth")
def list_auth(user=Depends(get_current_user)):
    _require_auth_manager(user)
    rows = query("SELECT emp_no, emp_name, granted_by, granted_at FROM dbo.meal_stat_auth ORDER BY emp_no")
    for r in rows:
        r["emp_name"] = _resolve_name(r["emp_no"], r.get("emp_name") or "")
    return {"list": rows}


@router.post("/stat-auth")
def add_auth(body: AuthAdd, user=Depends(get_current_user)):
    _require_auth_manager(user)
    emp = get_employee(body.emp_no)
    if not emp:
        raise HTTPException(status_code=400, detail="员工不存在")
    name = emp.get("name") or body.emp_no
    execute(
        """IF NOT EXISTS (SELECT 1 FROM dbo.meal_stat_auth WHERE emp_no=%s)
           INSERT INTO dbo.meal_stat_auth (emp_no, emp_name, granted_by)
           VALUES (%s, %s, %s)""",
        (body.emp_no, body.emp_no, name, user["sub"]))
    return {"msg": "已授权", "emp_name": name}


@router.delete("/stat-auth/{emp_no}")
def del_auth(emp_no: str, user=Depends(get_current_user)):
    _require_auth_manager(user)
    execute("DELETE FROM dbo.meal_stat_auth WHERE emp_no=%s", (emp_no,))
    return {"msg": "已移除"}


@router.get("/employees/search")
def search(keyword: str = Query(""), user=Depends(get_current_user)):
    _require_auth_manager(user)
    return {"list": search_employees(keyword)}


# ---------- 点餐食堂设定 ----------
@router.get("/canteens")
def admin_get_canteens(user=Depends(get_current_user)):
    _require_admin(user)
    return {"list": get_canteens()}


@router.put("/canteens")
def admin_save_canteens(body: CanteenSave, user=Depends(get_current_user)):
    _require_admin(user)
    clean = save_canteens([x.model_dump() for x in body.list])
    return {"list": clean, "msg": f"已保存 {len(clean)} 个食堂"}


@router.get("/config")
def get_config(user=Depends(get_current_user)):
    _require_admin(user)
    return {"admin_emp_nos": sorted(get_admin_emp_nos())}


# ---------- 开餐时间（只能点 2 小时以后的餐） ----------
@router.get("/meal-times")
def get_meal_times_api(user=Depends(get_current_user)):
    """公开：前端按开餐时间禁用过期/过去餐次。"""
    return {"meal_times": get_meal_times(), "defaults": DEFAULT_MEAL_TIMES}


@router.put("/meal-times")
def save_meal_times_api(body: dict, user=Depends(get_current_user)):
    _require_admin(user)
    clean = save_meal_times((body or {}).get("meal_times") or {})
    return {"meal_times": clean, "msg": "已保存开餐时间"}
