# -*- coding: utf-8 -*-
"""鉴权依赖。"""
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from auth import decode_token

bearer = HTTPBearer(auto_error=False)


def get_current_user(cred: HTTPAuthorizationCredentials = Depends(bearer)):
    if not cred or not cred.credentials:
        raise HTTPException(status_code=401, detail="请先登录")
    payload = decode_token(cred.credentials)
    if not payload:
        raise HTTPException(status_code=401, detail="登录状态已失效，请重新登录")
    return payload
