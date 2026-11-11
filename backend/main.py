# -*- coding: utf-8 -*-
"""工厂食堂预约吃饭 - FastAPI 后端入口。"""
import asyncio
import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, Response

from config import FRONTEND_DIR
from auth import authenticate, create_token, get_user_flags, get_admin_emp_nos
from schemas import LoginReq
from routers import emp, order, report, admin
from hr import get_employee
from settings import get_canteens, save_canteens, DEFAULT_CANTEENS

app = FastAPI(title="工厂食堂预约系统", version="1.0.0")

# 食堂配置首次启动自动种子（可在「设定」页修改）
try:
    if not get_canteens():
        save_canteens(DEFAULT_CANTEENS)
except Exception:
    pass

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

app.include_router(emp.router)
app.include_router(order.router)
app.include_router(report.router)
app.include_router(admin.router)


@app.on_event("startup")
async def _quiet_windows_disconnects():
    """静音 Windows Proactor 的 ConnectionResetError(10054) 回调噪音。

    浏览器刷新 / 关闭页面时 asyncio 的 _call_connection_lost 会抛
    "远程主机强迫关闭了一个现有的连接"，与业务无关却刷满控制台。
    只过滤这一种，其它异常照常打印，避免掩盖真问题。
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return

    def handler(loop_, context):
        exc = context.get("exception")
        cb = str(context.get("message", "")) + " " + str(context.get("handle", ""))
        noisy = isinstance(exc, (ConnectionResetError, ConnectionAbortedError)) or (
            isinstance(exc, OSError) and getattr(exc, "winerror", None) in (10054, 10053, 10038))
        if noisy and ("connection_lost" in cb or "Proactor" in cb):
            return
        loop_.default_exception_handler(context)

    loop.set_exception_handler(handler)


@app.post("/api/login")
def login(body: LoginReq):
    emp = authenticate(body.username.strip(), body.password)
    if not emp:
        raise HTTPException(status_code=401, detail="工号或密码错误")
    if not emp.get("active"):
        raise HTTPException(status_code=403, detail="该账号已停用")
    token = create_token(emp["emp_no"], emp.get("name", ""), emp.get("deptno", ""), emp.get("dept_name", ""))
    flags = get_user_flags(emp["emp_no"])
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "emp_no": emp["emp_no"], "name": emp.get("name", ""),
            "deptno": emp.get("deptno", ""), "dept_name": emp.get("dept_name", "未分配"),
            "is_admin": flags["is_admin"], "can_stat": flags["can_stat"],
        },
    }


@app.get("/api/health")
def health():
    return {"status": "ok", "admin_seeded": sorted(get_admin_emp_nos())}


@app.get("/favicon.ico")
def favicon():
    return Response(status_code=204)


# ---- 前端静态托管 ----
INDEX = os.path.join(FRONTEND_DIR, "index.html")


@app.get("/")
def index():
    if os.path.exists(INDEX):
        return FileResponse(INDEX)
    return JSONResponse({"msg": "backend ok, frontend 未找到: " + FRONTEND_DIR})


if os.path.isdir(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
