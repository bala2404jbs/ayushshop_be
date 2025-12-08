from fastapi import Depends, HTTPException, status, Request
from jose import JWTError, jwt
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
from .database import get_session
from .models import User
from .config import settings

from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer(auto_error=False)

from typing import Optional

async def get_current_user(request: Request, token_creds: Optional[HTTPAuthorizationCredentials] = Depends(security), session: AsyncSession = Depends(get_session)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # Prioritize cookie
    token = None
    cookie_token = request.cookies.get("access_token")
    
    if cookie_token:
        token = cookie_token
        if token.startswith("Bearer "):
            token = token.split(" ")[1]
    
    # Fallback to header token from HTTPBearer
    if not token and token_creds:
        token = token_creds.credentials
    
    if not token:
        raise credentials_exception

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
        
    result = await session.exec(select(User).where(User.email == email))
    user = result.first()
    if user is None or user.deleted:
        raise credentials_exception
        
    return user

async def get_current_user_optional(request: Request, token_creds: Optional[HTTPAuthorizationCredentials] = Depends(security), session: AsyncSession = Depends(get_session)) -> Optional[User]:
    # Prioritize cookie
    token = None
    cookie_token = request.cookies.get("access_token")
    
    if cookie_token:
        token = cookie_token
        if token.startswith("Bearer "):
            token = token.split(" ")[1]
    
    # Fallback to header token from HTTPBearer
    if not token and token_creds:
        token = token_creds.credentials
    
    if not token:
        return None

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            return None
    except JWTError:
        return None
        
    result = await session.exec(select(User).where(User.email == email))
    user = result.first()
    if user is None or user.deleted:
        return None
        
    return user
