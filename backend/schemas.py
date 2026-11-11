# -*- coding: utf-8 -*-
"""Pydantic 请求/响应模型。"""
from pydantic import BaseModel, Field


class LoginReq(BaseModel):
    username: str
    password: str


class TokenResp(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


class OrderItem(BaseModel):
    """单人单日点餐：5 个基础餐别（早/中/午/晚/夜餐）。
    中国/越南餐厅由后端按员工国籍(e_name 越南变音)自动判定写入 *_tq/*_vn。
    meal_date 为空时应用到批次 dates 里每一天（旧兼容），否则只保存该行日期。"""
    emp_no: str
    meal_date: str = ""  # YYYY-MM-DD；逐行携带（点餐页一行 = 一人一天）
    breakfast: bool = False
    lunch: bool = False
    wucan: bool = False
    dinner: bool = False
    midnight: bool = False
    remark: str = ""


class OrderUpsert(OrderItem):
    meal_date: str  # YYYY-MM-DD（兼容旧单日接口）


class OrderBatch(BaseModel):
    """多人批量保存：同一批餐别勾选应用到 dates 里每一天（按人批量多天点餐）。
    order_nat：本次点餐模式 tq/vn，决定写入中国(*_tq)还是越南(*_vn)餐厅列；
    特例：中国模式可输入越南人工号点中国餐厅、越南模式可输入中国人工号点越南餐厅。"""
    canteen_code: str = ""          # 点餐食堂（部门节点代号）
    dates: list[str] = []           # 用餐日期范围展开后的日期列表
    meal_date: str = ""             # 兼容旧单日接口
    order_nat: str = ""             # tq / vn；空则按员工国籍回退
    items: list[OrderItem]


class CanteenItem(BaseModel):
    code: str
    name: str = ""
    rules: list = []  # 可选：[{type:"prefix",value:"101305"}] / [{type:"prefix_name",prefix:"1013",name:"安阳"}]；留空=按 code 前缀


class CanteenSave(BaseModel):
    list: list[CanteenItem]


class AuthAdd(BaseModel):
    emp_no: str
