from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
from ..database import get_session
from ..models import User, LoginRequest
from ..security import verify_password, create_access_token
from datetime import timedelta

router = APIRouter(tags=["auth"])

@router.post("/login")
async def login(response: Response, login_request: LoginRequest, session: AsyncSession = Depends(get_session)):
    result = await session.exec(select(User).where(User.email == login_request.email))
    user = result.first()
    if not user or user.deleted or not verify_password(login_request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"sub": user.email})
    
    # Set HTTP-only cookie
    response.set_cookie(
        key="access_token",
        value=f"Bearer {access_token}",
        httponly=True,
        max_age=1800, # 30 minutes
        expires=1800,
        samesite="lax",
        secure=False # Set to True in production with HTTPS
    )
    
    return {"access_token": access_token, "token_type": "bearer", "message": "Login successful"}

@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("access_token")
    return {"message": "Logged out successfully"}
