# -*- coding: utf-8 -*-
"""食堂配置：存 meal_config.canteens（JSON 数组 [{code, name}]）。
食堂对应部门节点代号：下属部门代号自动包含上级代号（如 1013 覆盖 1013 及所有下级）。"""
import json
from db import query, execute

DEFAULT_CANTEENS = [
    {"code": "1013", "name": "越南旺盈食堂"},
    {"code": "1020", "name": "越南至美食堂"},
]


def _clean(lst):
    out, seen = [], set()
    for x in lst or []:
        code = str(x.get("code", "")).strip()
        if not code or code in seen:
            continue
        seen.add(code)
        name = str(x.get("name", "")).strip() or code
        rules = x.get("rules")
        if isinstance(rules, list):
            rules = [r for r in rules if isinstance(r, dict)]
        else:
            rules = None
        out.append({"code": code, "name": name, "rules": rules})
    return out


def get_canteens():
    """返回 [{code, name, rules}]；未配置/解析失败返回空列表。"""
    try:
        rows = query("SELECT cfg_value FROM dbo.meal_config WHERE cfg_key=%s", ("canteens",))
        if rows and rows[0].get("cfg_value"):
            val = json.loads(rows[0]["cfg_value"])
            if isinstance(val, list):
                return _clean(val)
    except Exception:
        pass
    return []


def save_canteens(lst):
    clean = _clean(lst)
    val = json.dumps(clean, ensure_ascii=False)
    execute(
        """IF NOT EXISTS (SELECT 1 FROM dbo.meal_config WHERE cfg_key=%s)
               INSERT INTO dbo.meal_config (cfg_key, cfg_value) VALUES (%s, %s)
           ELSE UPDATE dbo.meal_config
                   SET cfg_value=%s, updated_at=GETDATE() WHERE cfg_key=%s""",
        ("canteens", "canteens", val, val, "canteens"))
    return clean


# ---------- 开餐时间（用于「只能点 2 小时以后的餐」判定） ----------
MEAL_TIME_KEY = "meal_times"
# 默认开餐时间：早/中/午(17:00 办公室晚餐)/晚(夜班前晚餐)/夜(夜宵)
DEFAULT_MEAL_TIMES = {
    "breakfast": "07:00", "lunch": "11:30", "wucan": "17:00",
    "dinner": "19:00", "midnight": "23:30",
}


def _is_hhmm(s):
    import re
    return bool(re.match(r"^([01]\d|2[0-3]):[0-5]\d$", str(s or "")))


def get_meal_times():
    """返回 {meal_key: "HH:MM"}；未配置/解析失败退回默认。"""
    try:
        rows = query("SELECT cfg_value FROM dbo.meal_config WHERE cfg_key=%s", (MEAL_TIME_KEY,))
        if rows and rows[0].get("cfg_value"):
            val = json.loads(rows[0]["cfg_value"])
            if isinstance(val, dict):
                out = dict(DEFAULT_MEAL_TIMES)
                for k in DEFAULT_MEAL_TIMES:
                    if _is_hhmm(val.get(k)):
                        out[k] = val[k]
                return out
    except Exception:
        pass
    return dict(DEFAULT_MEAL_TIMES)


def save_meal_times(times):
    """管理员设定开餐时间；无效或缺失的键退回默认，始终保留全部 5 个餐别。"""
    clean = {}
    src = times if isinstance(times, dict) else {}
    for k in DEFAULT_MEAL_TIMES:
        v = src.get(k)
        clean[k] = v if _is_hhmm(v) else DEFAULT_MEAL_TIMES[k]
    val = json.dumps(clean, ensure_ascii=False)
    execute(
        """IF NOT EXISTS (SELECT 1 FROM dbo.meal_config WHERE cfg_key=%s)
               INSERT INTO dbo.meal_config (cfg_key, cfg_value) VALUES (%s, %s)
           ELSE UPDATE dbo.meal_config
                   SET cfg_value=%s, updated_at=GETDATE() WHERE cfg_key=%s""",
        (MEAL_TIME_KEY, MEAL_TIME_KEY, val, val, MEAL_TIME_KEY))
    return clean


def _find_canteen(code):
    """按 code 找到食堂配置（含 rules）。"""
    code = str(code or "")
    for c in get_canteens():
        if str(c.get("code", "")) == code:
            return c
    return None


def get_rules(canteen):
    """取食堂的规则列表；无 rules 时退回「单前缀」语义（code 本身即前缀），向后兼容。"""
    r = canteen.get("rules") if isinstance(canteen, dict) else None
    if isinstance(r, list) and r:
        return r
    return [{"type": "prefix", "value": str(canteen.get("code", ""))}]


def dept_in_canteen(deptno, dept_name, rules):
    """部门是否归属某食堂（命中任意一条规则即可）。

    规则类型：
      - {"type":"prefix","value":"101305"}          部门代号以 value 起头
      - {"type":"prefix_name","prefix":"1013",
         "name":"安阳"}                             代号以 prefix 起头 且 部门名含 name
    前缀匹配沿用系统「部门代号前缀=层级」约定；prefix_name 用于无法用单一前缀表达的子集。
    """
    d = str(deptno or "")
    dn = str(dept_name or "")
    for r in (rules or []):
        t = r.get("type")
        if t == "prefix":
            v = str(r.get("value", ""))
            if v and d.startswith(v):
                return True
        elif t == "prefix_name":
            p = str(r.get("prefix", ""))
            nm = str(r.get("name", ""))
            if p and d.startswith(p) and nm and nm in dn:
                return True
    return False
