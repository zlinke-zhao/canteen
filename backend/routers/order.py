# -*- coding: utf-8 -*-
"""点餐接口：本人 / 本部门及下属部门同事 / 本人登记的客人。
食堂维度：每人每天每食堂一条记录；同一餐不可在两个食堂重复点。"""
import re
import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from deps import get_current_user
from hr import get_employee
from auth import get_user_flags
from settings import get_canteens, get_rules, _find_canteen, dept_in_canteen, get_meal_times
from db import query, execute
from schemas import OrderUpsert, OrderBatch

router = APIRouter(prefix="/api", tags=["order"])

# 10 个餐别存储列（中国餐厅 / 越南餐厅，各 早/中/午/晚/夜餐）
FLAGS = ["breakfast_cn", "breakfast_vn", "lunch_cn", "lunch_vn", "wucan_cn", "wucan_vn",
         "dinner_cn", "dinner_vn", "midnight_cn", "midnight_vn"]
# 5 个基础餐别（点餐页/接口用，后端按点餐模式展开到 *_cn/*_vn）
BASE_MEALS = ["breakfast", "lunch", "wucan", "dinner", "midnight"]
MEAL_LABELS = {
    "breakfast_cn": "早餐", "breakfast_vn": "早餐",
    "lunch_cn": "中餐", "lunch_vn": "中餐",
    "wucan_cn": "午餐", "wucan_vn": "午餐",
    "dinner_cn": "晚餐", "dinner_vn": "晚餐",
    "midnight_cn": "夜餐", "midnight_vn": "夜餐",
}


def meal_orderable(meal_date, meal_key, meal_times=None, now=None):
    """该餐次是否可点（只能点 2 小时以后的餐）：
      - 过去日期一律不可点；
      - 未来日期全部可点；
      - 今天须 开餐时间 >= 当前时间 + 2 小时（不足提前量不可点）。
    未配置开餐时间则该餐不卡时间。now 可注入（用于测试）。"""
    if not meal_date:
        return False
    today = datetime.date.today().isoformat()
    if meal_date < today:
        return False
    if meal_date > today:
        return True
    mt = (meal_times or get_meal_times()).get(meal_key)
    if not mt:
        return True
    try:
        hh, mm = (int(x) for x in str(mt).split(":"))
    except Exception:
        return True
    now = now or datetime.datetime.now()
    meal_dt = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
    return meal_dt >= (now + datetime.timedelta(hours=2))

# 客人工号：当前工号_流水，如 R1036391_1
GUEST_RE = re.compile(r"^(?P<base>.+?)_(?P<seq>\d{1,8})$")


def _is_unique_violation(e):
    """pymssql 的唯一约束冲突（2601/2627）。"""
    return "2601" in str(e) or "2627" in str(e)


class OrderConflict(Exception):
    def __init__(self, msg):
        self.msg = msg


def _is_guest(emp_no):
    return bool(GUEST_RE.match(emp_no))


class _Perm:
    """一次请求内复用的下单权限上下文（批量点餐时避免逐行重复查库）。

    允许的四种情形：
      1) 管理员：不限；
      2) 本人 / 本人登记的客人；
      3) 本部门及下属部门（部门代号以本人部门代号起头）；
      4) 统计授权名单（meal_stat_auth）内人员：当前食堂代号起头的任意部门
         —— 如食堂 1013，则可为 1013 及其所有下级部门的人点餐。
    """

    def __init__(self, user, canteen_code=""):
        self.emp_no = user.get("sub") or ""
        self.canteen = str(canteen_code or "")
        flags = get_user_flags(self.emp_no)
        self.is_admin = bool(flags["is_admin"])
        self.can_stat = bool(flags["can_stat"])
        me = get_employee(self.emp_no) or {}
        self.deptno = str(me.get("deptno") or user.get("deptno") or "")
        self.prof_cache = {}   # emp_no -> _profile 结果，同时供写入复用

    def profile(self, emp_no):
        if emp_no not in self.prof_cache:
            self.prof_cache[emp_no] = _profile(emp_no)
        return self.prof_cache[emp_no]

    def in_canteen_scope(self, deptno, dept_name=""):
        """统计名单内人员：部门命中当前食堂 rules（prefix / prefix_name）即可操作。"""
        d = str(deptno or "")
        if not (self.can_stat and self.canteen and d):
            return False
        canteen_obj = _find_canteen(self.canteen)
        if not canteen_obj:
            return False
        return dept_in_canteen(d, str(dept_name or ""), get_rules(canteen_obj))

    def allows(self, target_emp_no):
        target_emp_no = str(target_emp_no or "")
        if target_emp_no == self.emp_no:
            return True
        m = GUEST_RE.match(target_emp_no)
        if m and m.group("base") == self.emp_no:
            return True  # 本人登记的客人
        if self.is_admin:
            return True
        prof = self.profile(target_emp_no)
        if not prof:
            return False
        tg = str(prof[1] or "")   # (name, deptno, dept_name, companyid, active)
        if not tg:
            return False
        if self.deptno and (tg == self.deptno or tg.startswith(self.deptno)):
            return True  # 本部门或下属部门
        return self.in_canteen_scope(tg, prof[2] or "")


def _check_perm(target_emp_no, user, canteen_code=""):
    """单条校验（兼容旧调用）：本人 / 本人客人 / 本部门及下属 / 统计名单内食堂范围 / 管理员。"""
    return _Perm(user, canteen_code).allows(target_emp_no)


def _legacy_sync(vals):
    """由新 10 列推导旧列值（旧列 NOT NULL，保持兼容）：
    nationality：勾了中国列→CN，只勾越南列→VN，都空→CN 占位；
    旧 4 个 bit 列 = 对应餐别中/越任一勾选（新『午餐』折入 lunch 旧位）。"""
    nat = "CN" if (vals["breakfast_cn"] or vals["lunch_cn"] or vals["wucan_cn"]
                   or vals["dinner_cn"] or vals["midnight_cn"]) else "VN"
    return nat, (vals["breakfast_cn"] or vals["breakfast_vn"]), \
        (vals["lunch_cn"] or vals["lunch_vn"] or vals["wucan_cn"] or vals["wucan_vn"]), \
        (vals["dinner_cn"] or vals["dinner_vn"]), \
        (vals["midnight_cn"] or vals["midnight_vn"])


def _profile(emp_no, cache=None):
    """返回 (emp_name, deptno, dept_name, companyid, active)。客人走基准员工档案。
    cache 传入 dict 时同请求内复用（整部门点餐一次查询一个人）。"""
    if cache is not None and emp_no in cache:
        return cache[emp_no]
    prof = _profile_uncached(emp_no)
    if cache is not None:
        cache[emp_no] = prof
    return prof


def _profile_uncached(emp_no):
    if _is_guest(emp_no):
        base = GUEST_RE.match(emp_no).group("base")
        owner = get_employee(base)
        if not owner:
            return None
        seq = emp_no[len(base) + 1:]
        name = f"{owner.get('name') or base}(客人{seq})"
        return (name, owner.get("deptno"), owner.get("dept_name"),
                owner.get("companyid"), True, owner.get("name_vn") or "")
    emp = get_employee(emp_no)
    if not emp or not emp.get("active"):
        return None
    return (emp.get("name"), emp.get("deptno"), emp.get("dept_name"),
            emp.get("companyid"), True, emp.get("name_vn") or "",
            int(emp.get("is_vn") or 0))


def _upsert_one(emp_no, meal_date, item, orderer_no, canteen_code, prof_cache=None, order_nat="", meal_times=None):
    """单条 upsert（键：emp_no + meal_date + canteen_code）。
    返回 inserted / updated / deleted / none / skip；跨食堂同餐冲突抛 OrderConflict。
    order_nat='vn' 写越南餐厅(*_vn)，'cn' 写中国餐厅(*_cn)；为空则按员工国籍回退。
    特例：中国模式可输入越南人工号点中国餐厅、越南模式可输入中国人工号点越南餐厅。
    只能点 2 小时以后的餐：新建订单不允许过期餐次（拦截），已保存的历史记录予以保留。"""
    prof = _profile(emp_no, prof_cache)
    if not prof:
        return "skip"
    emp_name, deptno, dept_name, companyid, _active, name_vn, is_vn = prof
    # 写入餐厅以「点餐模式」为准（order_nat），而非员工实际国籍；为空时回退国籍
    nat_is_vn = (order_nat == "vn") if order_nat in ("cn", "vn") else bool(is_vn)
    vals = {}
    try:
        existing = query(
            "SELECT id, " + ", ".join(FLAGS) + " FROM dbo.meal_order "
            "WHERE emp_no=%s AND meal_date=%s AND canteen_code=%s",
            (emp_no, meal_date, canteen_code))
    except Exception as e:
        if _is_unique_violation(e):
            return "skip"  # 并发下另一请求已插入同键记录，交由下一次保存更新
        raise
    ex_row = existing[0] if existing else None
    for m in BASE_MEALS:
        on = 1 if getattr(item, m) else 0
        col = m + ("_vn" if nat_is_vn else "_cn")
        if on and not meal_orderable(meal_date, m, meal_times):
            # 过期/不足提前量：不允许新建；已保存的历史记录（DB 同列已有值）予以保留
            if not (ex_row and ex_row.get(col)):
                on = 0
        vals[m + "_cn"] = on if not nat_is_vn else 0
        vals[m + "_vn"] = on if nat_is_vn else 0
    if not any(vals.values()):
        if existing:
            execute("DELETE FROM dbo.meal_order WHERE emp_no=%s AND meal_date=%s AND canteen_code=%s",
                    (emp_no, meal_date, canteen_code))
            return "deleted"
        return "none"
    # 跨食堂冲突：同一餐已在他食堂登记
    others = query(
        f"SELECT {', '.join(FLAGS)} FROM dbo.meal_order "
        "WHERE emp_no=%s AND meal_date=%s AND canteen_code<>%s",
        (emp_no, meal_date, canteen_code))
    for o in others:
        for f in FLAGS:
            if vals[f] and o.get(f):
                raise OrderConflict(
                    f"{emp_name}({emp_no}) {meal_date} {MEAL_LABELS[f]}已登记于其他食堂")
    nat, bf, lc, dn, md = _legacy_sync(vals)
    if existing:
        sets = ", ".join(f"{f}=%s" for f in FLAGS)
        execute(
            f"""UPDATE dbo.meal_order
                   SET {sets}, nationality=%s, breakfast=%s, lunch=%s,
                       dinner=%s, midnight=%s,
                       remark=%s, orderer_no=%s, updated_at=GETDATE()
                 WHERE emp_no=%s AND meal_date=%s AND canteen_code=%s""",
            tuple(vals[f] for f in FLAGS) + (nat, bf, lc, dn, md)
            + (item.remark, orderer_no, emp_no, meal_date, canteen_code))
        return "updated"
    placeholders = ", ".join(["%s"] * len(FLAGS))
    try:
        execute(
            f"""INSERT INTO dbo.meal_order
                   (emp_no, emp_name, deptno, dept_name, companyid, meal_date, canteen_code,
                    {', '.join(FLAGS)}, nationality, breakfast, lunch, dinner, midnight,
                    orderer_no, remark)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,{placeholders},%s,%s,%s,%s,%s,%s,%s)""",
            (emp_no, emp_name, deptno, dept_name, companyid, meal_date, canteen_code)
            + tuple(vals[f] for f in FLAGS) + (nat, bf, lc, dn, md)
            + (orderer_no, item.remark))
    except Exception as e:
        if _is_unique_violation(e):
            # 并发重复提交：同键记录已被另一请求写入，按更新处理避免 500
            sets = ", ".join(f"{f}=%s" for f in FLAGS)
            execute(
                f"""UPDATE dbo.meal_order
                       SET {sets}, nationality=%s, breakfast=%s, lunch=%s,
                           dinner=%s, midnight=%s,
                           remark=%s, orderer_no=%s, updated_at=GETDATE()
                     WHERE emp_no=%s AND meal_date=%s AND canteen_code=%s""",
                tuple(vals[f] for f in FLAGS) + (nat, bf, lc, dn, md)
                + (item.remark, orderer_no, emp_no, meal_date, canteen_code))
            return "updated"
        raise
    return "inserted"


@router.get("/order")
def get_order(emp_no: str = Query(...), date: str = Query(...),
              canteen: str = Query(""), user=Depends(get_current_user)):
    if not _check_perm(emp_no, user, canteen):
        raise HTTPException(status_code=403, detail="无权限操作该员工")
    rows = query(
        "SELECT * FROM dbo.meal_order WHERE emp_no=%s AND meal_date=%s AND canteen_code=%s",
        (emp_no, date, canteen))
    return {"order": rows[0] if rows else None}


@router.get("/orders")
def list_orders(date_from: str = Query(...), date_to: str = Query(...),
                canteen: str = Query(""), user=Depends(get_current_user)):
    """日期范围内、本人/本部门及下属部门/本人客人的全部登记（点餐页预填用）。
    统计名单内人员额外覆盖「当前食堂代号起头」的全部部门，保证跨部门点餐时预填不丢。"""
    me = get_employee(user["sub"]) or {}
    deptno = str(me.get("deptno") or user.get("deptno") or "")
    flags = get_user_flags(user["sub"])
    guest_pat = user["sub"].replace("[", "[[]").replace("_", "[_]") + "\\_%"
    scope = ["emp_no = %s", "emp_no LIKE %s ESCAPE '\\'", "orderer_no = %s"]
    sparams = [user["sub"], guest_pat, user["sub"]]
    if deptno:
        scope.append("deptno = %s")
        sparams.append(deptno)
        scope.append("CAST(deptno AS VARCHAR(40)) LIKE %s")
        sparams.append(deptno + "%")
    if flags["can_stat"] and canteen:
        scope.append("CAST(deptno AS VARCHAR(40)) LIKE %s")
        sparams.append(str(canteen) + "%")
    conds = ["meal_date >= %s", "meal_date <= %s", "(" + " OR ".join(scope) + ")"]
    params = [date_from, date_to] + sparams
    if canteen:
        conds.append("canteen_code = %s")
        params.append(canteen)
    rows = query(
        f"""SELECT emp_no, emp_name, meal_date, canteen_code, orderer_no,
                   breakfast_cn, breakfast_vn, lunch_cn, lunch_vn,
                   wucan_cn, wucan_vn, dinner_cn, dinner_vn,
                   midnight_cn, midnight_vn, remark
              FROM dbo.meal_order
             WHERE {' AND '.join(conds)}
             ORDER BY meal_date, emp_no""",
        tuple(params))
    return {"date_from": date_from, "date_to": date_to, "orders": rows}


@router.post("/order")
def upsert_order(body: OrderUpsert, user=Depends(get_current_user)):
    """单人单日保存（兼容接口；前端批量走 /orders/batch）。"""
    if not body.canteen_code:
        raise HTTPException(status_code=400, detail="请选择点餐食堂")
    perm = _Perm(user, body.canteen_code)
    if not perm.allows(body.emp_no):
        raise HTTPException(status_code=403, detail="无权限为该员工下单")
    try:
        r = _upsert_one(body.emp_no, body.meal_date, body, user["sub"],
                        body.canteen_code, perm.prof_cache, body.order_nat, get_meal_times())
    except OrderConflict as e:
        raise HTTPException(status_code=400, detail=e.msg)
    if r == "skip":
        raise HTTPException(status_code=400, detail="员工不存在或已离职")
    return {"result": r}


@router.post("/orders/batch")
def batch_upsert(body: OrderBatch, user=Depends(get_current_user)):
    """多人 × 多天批量保存：同一批勾选应用到 dates 每一天（按部门点餐请只传一天）。"""
    dates = list(dict.fromkeys(
        [d for d in (body.dates or []) if d] + ([body.meal_date] if body.meal_date else [])))
    if not dates:
        raise HTTPException(status_code=400, detail="日期不能为空")
    if len(dates) > 31:
        raise HTTPException(status_code=400, detail="一次最多批量 31 天")
    if not body.canteen_code:
        raise HTTPException(status_code=400, detail="请选择点餐食堂")
    valid = {c["code"] for c in get_canteens()}
    if body.canteen_code not in valid:
        raise HTTPException(status_code=400, detail="无效的点餐食堂，请重新选择")
    bad = [it.meal_date for it in body.items
           if it.meal_date and not re.match(r"^\d{4}-\d{2}-\d{2}$", it.meal_date)]
    if bad:
        raise HTTPException(status_code=400, detail=f"行日期格式错误（应为 YYYY-MM-DD）: {bad[:3]}")

    n_ins = n_upd = n_del = 0
    skipped, conflicts = [], []
    perm = _Perm(user, body.canteen_code)
    meal_times = get_meal_times()   # 一次请求内复用开餐时间配置
    # 同一批内按 (emp_no, 生效日期) 去重；item.meal_date 有值 = 该行只写那一天
    seen = set()
    tasks = []  # (item, date)
    for it in body.items:
        if it.meal_date:
            day_list = [it.meal_date]
        else:
            day_list = dates  # 兼容旧契约：应用到批次每一天
        for d in day_list:
            k = (it.emp_no, d)
            if k in seen:
                continue
            seen.add(k)
            tasks.append((it, d))
    for item, d in tasks:
        if not perm.allows(item.emp_no):
            if item.emp_no not in skipped:
                skipped.append(item.emp_no)
            continue
        try:
            r = _upsert_one(item.emp_no, d, item, user["sub"],
                            body.canteen_code, perm.prof_cache, body.order_nat, meal_times)
        except OrderConflict as e:
            if e.msg not in conflicts:
                conflicts.append(e.msg)
            continue
        except Exception as e:
            # 单条异常不拖垮整批：记入跳过并返回原因（避免整批 500）
            msg = f"{item.emp_no}: {str(e)[:80]}"
            if msg not in skipped:
                skipped.append(msg)
            continue
        if r == "inserted":
            n_ins += 1
        elif r == "updated":
            n_upd += 1
        elif r == "deleted":
            n_del += 1
        elif r == "skip":
            if item.emp_no not in skipped:
                skipped.append(item.emp_no)
    parts = []
    if n_ins:
        parts.append(f"新增 {n_ins}")
    if n_upd:
        parts.append(f"更新 {n_upd}")
    if n_del:
        parts.append(f"取消 {n_del}")
    msg = "已保存：" + ("、".join(parts) if parts else "无变更")
    if skipped:
        msg += f"（{len(skipped)} 条跳过：无权限/不存在/异常——" + "；".join(skipped[:5]) + ("…" if len(skipped) > 5 else "") + "）"
    if conflicts:
        msg += "；冲突未保存：" + "；".join(conflicts)
    return {"msg": msg, "inserted": n_ins, "updated": n_upd,
            "deleted": n_del, "skipped": skipped, "conflicts": conflicts}


@router.delete("/order")
def delete_order(emp_no: str = Query(...), date: str = Query(...),
                 canteen: str = Query(""), user=Depends(get_current_user)):
    if not _check_perm(emp_no, user, canteen):
        raise HTTPException(status_code=403, detail="无权限操作该员工")
    if canteen:
        execute("DELETE FROM dbo.meal_order WHERE emp_no=%s AND meal_date=%s AND canteen_code=%s",
                (emp_no, date, canteen))
    else:
        execute("DELETE FROM dbo.meal_order WHERE emp_no=%s AND meal_date=%s", (emp_no, date))
    return {"msg": "已取消"}
