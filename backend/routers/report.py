# -*- coding: utf-8 -*-
"""日报 / 月报汇总（需 can_stat 权限）。"""
from fastapi import APIRouter, Depends, HTTPException, Query
from deps import get_current_user
from auth import get_user_flags
from db import query, vb, dec_gbk

router = APIRouter(prefix="/api/report", tags=["report"])

# 5 个餐别（含新增「午餐」wucan）；每餐分 中(tq)/越(vn) 两列
MEALS = ["breakfast", "lunch", "wucan", "dinner", "midnight"]
MEAL_LABELS = {"breakfast": "早餐", "lunch": "中餐", "wucan": "午餐",
               "dinner": "晚餐", "midnight": "夜餐"}


def _group_sql(where, params, canteen=""):
    # 食堂筛选（可选）：canteen_code 为部门节点代号
    if canteen:
        where += " AND o.canteen_code = %s"
        params = params + (canteen,)
    # 8 个勾选位直接求和（中国餐厅 *_tq / 越南餐厅 *_vn）
    cols = []
    for m in MEALS:
        cols.append(f"SUM(ISNULL(o.{m}_tq, 0)) AS {m}_tq")
        cols.append(f"SUM(ISNULL(o.{m}_vn, 0)) AS {m}_vn")
    # deptdesc/deptmanager 是 varchar(GBK)，hex 取字节客户端解码
    return f"""
        SELECT o.deptno,
               {vb('s.deptdesc', 400)} AS dept_raw,
               {vb('s.deptmanager', 200)} AS mgr_raw,
               {', '.join(cols)}
        FROM dbo.meal_order o
        LEFT JOIN sys_dept s ON CAST(o.deptno AS VARCHAR(40)) = s.dept
        WHERE {where}
        GROUP BY o.deptno, s.deptdesc, s.deptmanager
        ORDER BY s.deptdesc
    """, params


def _shape(rows):
    depts = []
    total = {f"{m}_{nat}": 0 for m in MEALS for nat in ("tq", "vn")}
    for r in rows:
        sub = 0
        d = {"deptno": r["deptno"],
             "dept_name": (dec_gbk(r.get("dept_raw")) or "").strip() or "未分配",
             "manager": dec_gbk(r.get("mgr_raw")) or ""}
        for m in MEALS:
            for nat in ("tq", "vn"):
                v = r.get(f"{m}_{nat}") or 0
                d[f"{m}_{nat}"] = v
                total[f"{m}_{nat}"] += v
                sub += v
        d["subtotal"] = sub
        depts.append(d)
    total["grand"] = sum(total.values())
    return depts, total


@router.get("/daily")
def daily(date: str = Query(...), canteen: str = Query(""),
          user=Depends(get_current_user)):
    flags = get_user_flags(user["sub"])
    if not flags["can_stat"]:
        raise HTTPException(status_code=403, detail="无汇总统计权限")
    sql, params = _group_sql("o.meal_date = %s", (date,), canteen)
    rows = query(sql, params)
    depts, total = _shape(rows)
    return {"date": date, "meals": MEALS, "meal_labels": MEAL_LABELS,
            "departments": depts, "total": total}


@router.get("/monthly")
def monthly(year: int = Query(...), month: int = Query(...), canteen: str = Query(""),
            user=Depends(get_current_user)):
    flags = get_user_flags(user["sub"])
    if not flags["can_stat"]:
        raise HTTPException(status_code=403, detail="无汇总统计权限")
    first = f"{year:04d}-{month:02d}-01"
    # 下个月 1 号（半开区间），避免 11-31 这类不存在日期导致 DATE 转换失败
    ny, nm = (year + 1, 1) if month == 12 else (year, month + 1)
    nxt = f"{ny:04d}-{nm:02d}-01"
    sql, params = _group_sql("o.meal_date >= %s AND o.meal_date < %s", (first, nxt), canteen)
    rows = query(sql, params)
    depts, total = _shape(rows)
    return {"year": year, "month": month, "meals": MEALS, "meal_labels": MEAL_LABELS,
            "departments": depts, "total": total}
