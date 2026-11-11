# -*- coding: utf-8 -*-
"""员工 / 部门 / 食堂基础接口。"""
from fastapi import APIRouter, Depends, HTTPException, Query
from deps import get_current_user
from hr import (get_employee, search_employee_exact, get_sub_depts,
                get_dept_employees, get_canteen_depts, dec_gbk)
from auth import get_user_flags
from settings import get_canteens, get_rules, _find_canteen, dept_in_canteen
from db import query, vb

router = APIRouter(prefix="/api", tags=["employee"])

DEPT_EMP_LIMIT = 1200  # 单个部门（含下属）一次载入上限


@router.get("/me")
def me(user=Depends(get_current_user)):
    emp = get_employee(user["sub"]) or {}
    flags = get_user_flags(user["sub"])
    return {
        "emp_no": user["sub"],
        "name": user.get("name") or emp.get("name") or "",
        "deptno": user.get("deptno") or emp.get("deptno") or "",
        "dept_name": user.get("dept_name") or emp.get("dept_name") or "未分配",
        "is_admin": flags["is_admin"],
        "can_stat": flags["can_stat"],
    }


@router.get("/canteens")
def canteens(user=Depends(get_current_user)):
    """食堂列表（设定页维护，点餐页选择）。"""
    return {"list": get_canteens()}


@router.get("/emp/search")
def emp_search(keyword: str = Query(""), user=Depends(get_current_user)):
    """按工号精确 / 姓名模糊搜索（点餐-为他人点餐）。"""
    return {"list": search_employee_exact(keyword.strip())}


def _dept_name(deptno):
    rows = query("SELECT %s AS dept_raw FROM sys_dept WHERE dept=%%s" % vb('deptdesc', 400),
                 (str(deptno),))
    if rows:
        return dec_gbk(rows[0].get("dept_raw")) or ""
    return ""


def _dept_scope_ok(deptno, user, canteen=""):
    """目标部门是否允许操作：
    - 管理员：不限；
    - 统计授权名单内人员：命中当前食堂 rules 的任意部门（prefix / prefix_name）；
    - 其他人员：本人部门及下属部门。"""
    flags = get_user_flags(user["sub"])
    if flags["is_admin"]:
        return True
    d = str(deptno or "")
    if not d:
        return False
    c = str(canteen or "")
    if flags["can_stat"] and c:
        canteen_obj = _find_canteen(c)
        if canteen_obj:
            rules = get_rules(canteen_obj)
            # prefix_name 规则需部门名，按需查一次
            dname = _dept_name(d) if any(r.get("type") == "prefix_name" for r in rules) else ""
            if dept_in_canteen(d, dname, rules):
                return True
    me = get_employee(user["sub"]) or {}
    my = str(me.get("deptno") or user.get("deptno") or "")
    if not my:
        return False
    return d == my or d.startswith(my)


@router.get("/depts")
def depts(canteen: str = Query(""), user=Depends(get_current_user)):
    """按部门点餐的部门下拉。
    统计名单内人员：当前食堂 rules 覆盖的全部部门（并集）；
    其他人员：本人部门 + 下属部门。"""
    me = get_employee(user["sub"]) or {}
    deptno = str(me.get("deptno") or user.get("deptno") or "")
    flags = get_user_flags(user["sub"])
    canteen = str(canteen or "")
    if flags["can_stat"] and canteen:
        rows = get_canteen_depts(canteen)
        seen = {str(r["deptno"]) for r in rows}
        for r in get_sub_depts(deptno):     # 本人部门不在食堂前缀下时也保留
            if str(r["deptno"]) not in seen:
                rows.append(r)
                seen.add(str(r["deptno"]))
        rows.sort(key=lambda r: str(r["deptno"]))
        return {"deptno": deptno, "scope": "canteen", "canteen": canteen, "list": rows}
    return {"deptno": deptno, "scope": "self", "list": get_sub_depts(deptno)}


@router.get("/dept/employees")
def dept_employees(deptno: str = Query(...), canteen: str = Query(""),
                   nat: str = Query(""), user=Depends(get_current_user)):
    """某部门（含下属）在职员工；统计名单内人员可查当前食堂下任意部门。
    nat='cn' 只留中国员工（剔除越南籍），nat='vn' 只留越南籍；按工号点餐不受限制。"""
    if not _dept_scope_ok(deptno, user, canteen):
        raise HTTPException(status_code=403,
                            detail="只能查看本部门/下属部门，或当前食堂范围内的部门")
    rows = get_dept_employees(deptno, limit=DEPT_EMP_LIMIT, nat=nat or None)
    return {"list": rows, "truncated": len(rows) >= DEPT_EMP_LIMIT,
            "limit": DEPT_EMP_LIMIT, "nat": nat or ""}
