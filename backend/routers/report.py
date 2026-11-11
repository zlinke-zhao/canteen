# -*- coding: utf-8 -*-
"""日报 / 月报汇总（需 can_stat 权限）。"""
import csv
import io
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from deps import get_current_user
from auth import get_user_flags
from db import query, vb, dec_gbk

router = APIRouter(prefix="/api/report", tags=["report"])

# 明细报表列定义（与真实库 meal_order 对齐：5 餐 × 中/越 = 10 个勾选列）
DETAIL_BASE = [
    ("meal_date", "日期"), ("emp_no", "工号"), ("emp_name", "姓名"),
    ("dept_name", "部门"), ("companyid", "公司"), ("canteen_code", "食堂代号"),
]
DETAIL_MEALS = [
    ("breakfast_cn", "早餐(中)"), ("breakfast_vn", "早餐(越)"),
    ("lunch_cn", "中餐(中)"), ("lunch_vn", "中餐(越)"),
    ("wucan_cn", "午餐(中)"), ("wucan_vn", "午餐(越)"),
    ("dinner_cn", "晚餐(中)"), ("dinner_vn", "晚餐(越)"),
    ("midnight_cn", "夜宵(中)"), ("midnight_vn", "夜宵(越)"),
]
DETAIL_TAIL = [("orderer_no", "代点人"), ("remark", "备注"), ("created_at", "下单时间")]
DETAIL_COLS = DETAIL_BASE + DETAIL_MEALS + DETAIL_TAIL

# 5 个餐别（含新增「午餐」wucan）；每餐分 中(cn)/越(vn) 两列
MEALS = ["breakfast", "lunch", "wucan", "dinner", "midnight"]
MEAL_LABELS = {"breakfast": "早餐", "lunch": "中餐", "wucan": "午餐",
               "dinner": "晚餐", "midnight": "夜餐"}


def _group_sql(where, params, canteen=""):
    # 食堂筛选（可选）：canteen_code 为部门节点代号
    if canteen:
        where += " AND o.canteen_code = %s"
        params = params + (canteen,)
    # 8 个勾选位直接求和（中国餐厅 *_cn / 越南餐厅 *_vn）
    cols = []
    for m in MEALS:
        cols.append(f"SUM(ISNULL(o.{m}_cn, 0)) AS {m}_cn")
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
    total = {f"{m}_{nat}": 0 for m in MEALS for nat in ("cn", "vn")}
    for r in rows:
        sub = 0
        d = {"deptno": r["deptno"],
             "dept_name": (dec_gbk(r.get("dept_raw")) or "").strip() or "未分配",
             "manager": dec_gbk(r.get("mgr_raw")) or ""}
        for m in MEALS:
            for nat in ("cn", "vn"):
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


def _fmt_row(r):
    out = {}
    for c, _ in DETAIL_COLS:
        v = r.get(c)
        if c == "meal_date" and v is not None:
            v = v.strftime("%Y-%m-%d") if hasattr(v, "strftime") else str(v)
        elif c == "created_at" and v is not None:
            v = v.strftime("%Y-%m-%d %H:%M:%S") if hasattr(v, "strftime") else str(v)
        out[c] = "" if v is None else v
    return out


def _detail_csv(rows, total, grand, start, end):
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow([l for _, l in DETAIL_COLS])
    for r in rows:
        w.writerow([r.get(c, "") for c, _ in DETAIL_COLS])
    # 合计行
    trow = ["", "", "汇总", "", "", ""]
    for c, _ in DETAIL_MEALS:
        trow.append(total[c])
    trow += ["", "", "总餐次 %d" % grand]
    w.writerow(trow)
    body = buf.getvalue().encode("utf-8-sig")  # BOM 保证 Excel 中文不乱码
    ascii_name = "canteen_detail_%s_%s.csv" % (start, end)
    cn_name = "食堂明细_%s_%s.csv" % (start, end)
    disp = "attachment; filename=\"%s\"; filename*=UTF-8''%s" % (ascii_name, quote(cn_name))
    return Response(content=body, media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": disp})


@router.get("/detail")
def detail(start: str = Query(...), end: str = Query(...),
           canteen: str = Query(""), format: str = Query(""),
           user=Depends(get_current_user)):
    """按日期范围导出明细报表（每人每天一条记录）。"""
    flags = get_user_flags(user["sub"])
    if not flags["can_stat"]:
        raise HTTPException(status_code=403, detail="无汇总统计权限")
    if start > end:
        raise HTTPException(status_code=400, detail="起始日期不能晚于结束日期")
    params = [start, end]
    where = "o.meal_date >= %s AND o.meal_date <= %s"
    if canteen:
        where += " AND o.canteen_code = %s"
        params.append(canteen)
    base_cols = ", ".join("o.%s" % c for c, _ in DETAIL_BASE)
    meal_cols = ", ".join("ISNULL(o.%s,0) AS %s" % (c, c) for c, _ in DETAIL_MEALS)
    tail_cols = ", ".join("o.%s" % c for c, _ in DETAIL_TAIL)
    sql = """
        SELECT {base}, {meal}, {tail}
        FROM dbo.meal_order o
        WHERE {where}
        ORDER BY o.meal_date, o.deptno, o.emp_no
    """.format(base=base_cols, meal=meal_cols, tail=tail_cols, where=where)
    rows = query(sql, params)
    total = {c: 0 for c, _ in DETAIL_MEALS}
    grand = 0
    for r in rows:
        for c, _ in DETAIL_MEALS:
            v = r.get(c) or 0
            total[c] += v
            grand += v
    out_rows = [_fmt_row(r) for r in rows]
    if format == "csv":
        return _detail_csv(out_rows, total, grand, start, end)
    return {"start": start, "end": end, "canteen": canteen,
            "columns": [{"key": c, "label": l} for c, l in DETAIL_COLS],
            "rows": out_rows, "total": total, "grand": grand,
            "count": len(out_rows)}
