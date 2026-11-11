# -*- coding: utf-8 -*-
"""HR 数据访问：员工 / 部门（只读 pass_hd、sys_emp_fourlevel、sys_dept）。

命名约定（ERP 字典）：
- sys_emp_fourlevel.EmpName：中文名；e_name：越南人的越南名（nvarchar，可直接读）；
- pass_hd.name_desc、sys_dept.deptdesc/deptmanager 是 varchar（库内 GBK 字节），
  连接为 UTF-8 时直接读会乱，必须 CONVERT(VARBINARY) 取字节后按 GBK 解码。

展示名：中文名 + 越南名 同时显示，如「武春长(Nguyễn Thị Ngọc)」；
只有一边就显示一边。
"""
from db import query, vb, dec_gbk, dec_utf16


def _has_vn_diacritics(s):
    """是否含越南语变音字符（Ạ/ơ/ư/ễ/é/ê/ô 等）。
    覆盖三个区：Latin-1 增补(0x00C0-0x00FF，含 é/ê/à/ô 等常用预组成字母)、
    Latin 扩展-A(0x0100-0x01FF，含 ă/đ/ơ/ư)、Latin 扩展附加(0x1E00-0x1EFF，含 ậ/ẹ/ị 等带调号字母)。
    e_name 为越南名，库内中文备注是 CJK 不会命中上述任一范围，不会误判。"""
    for c in (s or ""):
        o = ord(c)
        if o in (0x00D7, 0x00F7):   # × ÷ 非字母，跳过
            continue
        if (0x00C0 <= o <= 0x00FF) or (0x0100 <= o <= 0x01FF) or (0x1E00 <= o <= 0x1EFF):
            return True
    return False


def _full_name(cn, vn):
    cn = (cn or "").strip()
    vn = (vn or "").strip()
    if cn and vn and _has_vn_diacritics(vn):
        return f"{cn}({vn})"
    return cn or vn or ""


def get_employee(emp_no):
    """取员工档案：中文名（EmpName/name_desc）+ 越南名（e_name）合并展示。"""
    rows = query(
        f"""
        SELECT e.EmpNo AS emp_no,
               {vb('e.EmpName', 200)} AS cn_raw,
               {vb('p.name_desc', 200)} AS cn2_raw,
               e.e_name,
               CASE WHEN dbo.fn_DetectLanguage(e.e_name) = N'越南文' THEN 1 ELSE 0 END AS is_vn,
               e.deptno,
               {vb('s.deptdesc', 400)} AS dept_raw,
               {vb('s.deptmanager', 200)} AS mgr_raw,
               s.companyid AS companyid,
               CASE WHEN ISNULL(e.IsDelete, 0) = 0 THEN 1 ELSE 0 END AS active
        FROM sys_emp_fourlevel e
        LEFT JOIN pass_hd p
               ON p.user_name = e.EmpNo AND p.delmark = 'N' AND p.valid = 'Y'
        LEFT JOIN sys_dept s
               ON CAST(e.deptno AS VARCHAR(40)) = s.dept
        WHERE e.EmpNo = %s
        """,
        (emp_no,),
    )
    if not rows:
        return None
    r = rows[0]
    return _shape_emp(r)


def _shape_emp(r):
    # EmpName 是 nvarchar（hex 取出为 UTF-16LE 字节）；name_desc 是 varchar（GBK 字节）
    cn = (dec_utf16(r.get("cn_raw")) or "").strip() or (dec_gbk(r.get("cn2_raw")) or "").strip()
    dept_name = (dec_gbk(r.get("dept_raw")) or "").strip()
    return {
        "emp_no": r.get("emp_no"),
        "name": _full_name(cn, r.get("e_name")),
        "name_cn": cn,
        "name_vn": (r.get("e_name") or "").strip(),
        "is_vn": int(bool(int(r.get("is_vn") or 0)) or _has_vn_diacritics(r.get("e_name") or "")),
        "deptno": r.get("deptno"),
        "dept_name": dept_name or "未分配",
        "manager": dec_gbk(r.get("mgr_raw")),
        "companyid": r.get("companyid"),
        "active": r.get("active"),
    }


# 员工列表通用 SELECT（工号 / 合并姓名 / 部门）
_EMP_SELECT = f"""
        SELECT e.EmpNo AS emp_no,
               {vb('e.EmpName', 200)} AS cn_raw,
               {vb('p.name_desc', 200)} AS cn2_raw,
               e.e_name,
               CASE WHEN dbo.fn_DetectLanguage(e.e_name) = N'越南文' THEN 1 ELSE 0 END AS is_vn,
               e.deptno,
               {vb('s.deptdesc', 400)} AS dept_raw
        FROM sys_emp_fourlevel e
        LEFT JOIN pass_hd p
               ON p.user_name = e.EmpNo AND p.delmark = 'N' AND p.valid = 'Y'
        LEFT JOIN sys_dept s
               ON CAST(e.deptno AS VARCHAR(40)) = s.dept
"""


def _shape_list(rows):
    out = []
    for r in rows:
        d = _shape_emp(r)
        out.append({"emp_no": d["emp_no"], "name": d["name"],
                    "deptno": d["deptno"], "dept_name": d["dept_name"],
                    "name_vn": d["name_vn"], "is_vn": d["is_vn"]})
    return out


def is_vn_employee(emp):
    """越南籍员工判定（双信号并集，取较宽口径，避免漏判）：
      - DB 函数 dbo.fn_DetectLanguage(e_name)='越南文'（权威正判）；
      - 或 e_name 含越南语变音字符（fn 对只含葡/西语共用变音的名字会误判为『英文』，用变音字符兜底补回）。
    中文职务备注（如『清废工』）无拉丁变音，不会误判。
    档案里的 is_vn 字段已是上述组合结果，直接采用；缺字段时回退到变音字符启发式。"""
    if isinstance(emp, dict):
        if emp.get("is_vn") is not None:
            return bool(emp.get("is_vn"))
        vn = emp.get("name_vn") or emp.get("e_name") or ""
        return _has_vn_diacritics(vn)
    return False


def search_colleagues(deptno, keyword, exclude_emp_no, limit=300):
    """同部门在职同事（用于代点）。keyword 可为工号/姓名片段，应用层过滤。"""
    if not deptno:
        return []
    rows = query(
        _EMP_SELECT + """
        WHERE e.deptno = %s
          AND ISNULL(e.IsDelete, 0) = 0
          AND e.EmpNo <> %s
        ORDER BY e.EmpNo
        """,
        (deptno, exclude_emp_no),
    )
    out = _shape_list(rows)
    if keyword:
        k = keyword.lower()
        rows2 = [r for r in out
                 if k in (r["emp_no"] or "").lower() or k in (r["name"] or "").lower()]
        return rows2[:limit]
    return out[:limit]


def search_employees(keyword, limit=50):
    """全厂员工搜索（添加授权名单用）。"""
    kw = f"%{keyword or ''}%"
    rows = query(
        _EMP_SELECT + """
        WHERE ISNULL(e.IsDelete, 0) = 0
          AND (e.EmpNo LIKE %s OR p.name_desc LIKE %s OR e.EmpName LIKE %s OR e.e_name LIKE %s)
        ORDER BY e.EmpNo
        """,
        (kw, kw, kw, kw),
    )
    return _shape_list(rows)[:limit]


def search_employee_exact(keyword, limit=20):
    """点餐-按工号搜索：工号精确匹配优先，姓名模糊其次。"""
    if not keyword:
        return []
    kw = f"%{keyword}%"
    rows = query(
        f"""
        SELECT TOP {int(limit)}
               e.EmpNo AS emp_no,
               {vb('e.EmpName', 200)} AS cn_raw,
               {vb('p.name_desc', 200)} AS cn2_raw,
               e.e_name,
               CASE WHEN dbo.fn_DetectLanguage(e.e_name) = N'越南文' THEN 1 ELSE 0 END AS is_vn,
               e.deptno,
               {vb('s.deptdesc', 400)} AS dept_raw
        FROM sys_emp_fourlevel e
        LEFT JOIN pass_hd p
               ON p.user_name = e.EmpNo AND p.delmark = 'N' AND p.valid = 'Y'
        LEFT JOIN sys_dept s
               ON CAST(e.deptno AS VARCHAR(40)) = s.dept
        WHERE ISNULL(e.IsDelete, 0) = 0
          AND (e.EmpNo = %s OR p.name_desc LIKE %s OR e.EmpName LIKE %s OR e.e_name LIKE %s)
        ORDER BY CASE WHEN e.EmpNo = %s THEN 0 ELSE 1 END, e.EmpNo
        """,
        (keyword, kw, kw, kw, keyword),
    )
    return _shape_list(rows)


def get_sub_depts(deptno):
    """本部门 + 下属部门（节点代号：下属部门代号包含上级代号前缀）。"""
    if not deptno:
        return []
    rows = query(
        f"""
        SELECT dept AS deptno, {vb('deptdesc', 400)} AS dept_raw
        FROM sys_dept
        WHERE dept = %s OR dept LIKE %s
        ORDER BY dept
        """,
        (str(deptno), str(deptno) + "%"),
    )
    return [{"deptno": r["deptno"], "name": dec_gbk(r.get("dept_raw")).strip()}
            for r in rows]


def get_depts_by_prefix(prefix):
    """按部门节点代号前缀取部门列表（食堂范围用）：如 1013 → 1013 及全部下级部门。
    过滤名称含「失效」的历史节点，避免下拉里堆一堆废部门（只影响展示，不影响权限判断）。"""
    p = str(prefix or "")
    if not p:
        return []
    rows = query(
        f"""
        SELECT dept AS deptno, {vb('deptdesc', 400)} AS dept_raw
        FROM sys_dept
        WHERE dept LIKE %s
        ORDER BY dept
        """,
        (p + "%",),
    )
    out = []
    for r in rows:
        name = dec_gbk(r.get("dept_raw")).strip()
        if "失效" in name:
            continue
        out.append({"deptno": r["deptno"], "name": name})
    return out


def _depts_like_prefix_name(prefix, name):
    """前缀 + 部门名包含：如 代号 1013 起头 且 名称含「安阳」且 isvalid='Y'（sys_deptsingle）。"""
    p = str(prefix or "")
    nm = str(name or "")
    if not p or not nm:
        return []
    rows = query(
        f"""
        SELECT dept AS deptno, {vb('deptdesc', 400)} AS dept_raw
        FROM sys_deptsingle
        WHERE dept LIKE %s AND isvalid = 'Y' AND deptdesc LIKE %s
        ORDER BY dept
        """,
        (p + "%", "%" + nm + "%"),
    )
    out = []
    for r in rows:
        nm_dec = dec_gbk(r.get("dept_raw")).strip()
        if nm_dec:
            out.append({"deptno": r["deptno"], "name": nm_dec})
    return out


def get_canteen_depts(code):
    """某食堂（按 code）其 rules 下覆盖的全部部门（并集去重），用于按部门点餐下拉。

    规则类型：
      - prefix       → 复用 get_depts_by_prefix（sys_dept，过滤「失效」）
      - prefix_name  → _depts_like_prefix_name（sys_deptsingle + isvalid='Y'）
    """
    from settings import get_canteens, get_rules
    code = str(code or "")
    for c in get_canteens():
        if str(c.get("code", "")) == code:
            return _union_by_rules(c)
    return []


def _union_by_rules(canteen):
    from settings import get_rules
    rules = get_rules(canteen)
    out = {}
    for r in rules:
        t = r.get("type")
        if t == "prefix":
            for d in get_depts_by_prefix(r.get("value", "")):
                out.setdefault(d["deptno"], d["name"])
        elif t == "prefix_name":
            for d in _depts_like_prefix_name(r.get("prefix", ""), r.get("name", "")):
                out.setdefault(d["deptno"], d["name"])
    return [{"deptno": k, "name": v} for k, v in sorted(out.items())]


def get_dept_employees(deptno, limit=500, nat=None):
    """某部门（含下属部门）全部在职员工，按部门点餐用。
    国籍判定（权威+兜底）：dbo.fn_DetectLanguage(e_name)='越南文' 或 e_name 含越南语变音字符
    （fn 对只含葡/西语共用变音的名字会误判为『英文』，用变音字符兜底补回真越南人）。
      nat='tq' 剔除越南籍（只留中国员工，含 e_name 空/中文/英文）；
      nat='vn' 只留越南籍；其他=不过滤。
    过滤在应用层完成（部门子集已限定范围，量小且判定需变音字符）；按工号点餐不受 nat 限制。"""
    if not deptno:
        return []
    rows = query(
        _EMP_SELECT + f"""
        WHERE ISNULL(e.IsDelete, 0) = 0
          AND (e.deptno = %s OR CAST(e.deptno AS VARCHAR(40)) LIKE %s)
        ORDER BY e.deptno, e.EmpNo
        OFFSET 0 ROWS FETCH NEXT {int(limit)} ROWS ONLY
        """,
        (str(deptno), str(deptno) + "%"),
    )
    out = _shape_list(rows)
    if nat == "vn":
        out = [e for e in out if is_vn_employee(e)]
    elif nat == "tq":
        out = [e for e in out if not is_vn_employee(e)]
    return out
