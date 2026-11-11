# -*- coding: utf-8 -*-
"""MSSQL 连接与查询工具（pymssql）。每次请求新建连接（pymssql 连接非线程安全）。"""
import pymssql
from config import (MSSQL_SERVER, MSSQL_DB, MSSQL_LOGIN, MSSQL_PWD, MSSQL_CHARSET)


def get_conn():
    return pymssql.connect(
        server=MSSQL_SERVER,
        user=MSSQL_LOGIN,
        password=MSSQL_PWD,
        database=MSSQL_DB,
        charset=MSSQL_CHARSET,
        timeout=10,
    )


def query(sql, params=None, as_dict=True):
    """执行查询，返回 list[dict]。"""
    conn = get_conn()
    try:
        cur = conn.cursor(as_dict=as_dict)
        cur.execute(sql, params or ())
        return cur.fetchall()
    finally:
        conn.close()


def execute(sql, params=None):
    """执行增删改，返回影响行数。"""
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(sql, params or ())
        conn.commit()
        return cur.rowcount
    finally:
        conn.close()


def execute_return_id(sql, params=None):
    """执行插入并返回自增 id（MSSQL OUTPUT 方式）。"""
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(sql + " OUTPUT INSERTED.id", params or ())
        row = cur.fetchone()
        conn.commit()
        return row[0] if row else None
    finally:
        conn.close()


# ---------- varchar(GBK) 列的读取辅助 ----------
# 连接用 UTF-8 后，nvarchar 列（含中文/越南文）读写都无损；
# 但 varchar 列（库内按 GBK 存字节）直接读会乱码，须 hex 取原始字节再按 GBK 解码。

def vb(col, size):
    """SQL 片段：把 varchar/nvarchar 列转成原始字节（UTF-16LE 或 GBK）。"""
    return f"CONVERT(VARBINARY({int(size)}), {col})"


def dec_gbk(v):
    """客户端把 CONVERT(VARBINARY) 得到的 varchar(GBK) 字节还原成中文。"""
    if v is None:
        return ""
    if isinstance(v, (bytes, bytearray)):
        return bytes(v).decode("gbk", errors="replace")
    return v


def dec_utf16(v):
    """客户端把 CONVERT(VARBINARY) 得到的 nvarchar 字节还原（含越南文）。"""
    if v is None:
        return ""
    if isinstance(v, (bytes, bytearray)):
        return bytes(v).decode("utf-16-le", errors="replace")
    return v
