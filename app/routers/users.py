from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
from typing import List
from uuid import UUID
from datetime import datetime, timedelta
import random
from ..database import get_session
from ..models import User, UserBase, UserUpdate, UserCreate
from ..security import get_password_hash
from ..utils.email import send_email
from ..dependencies import get_current_user

router = APIRouter(prefix="/users", tags=["users"])

@router.post("/", response_model=User, status_code=status.HTTP_201_CREATED)
async def create_user(user: UserCreate, session: AsyncSession = Depends(get_session)):
    # Public endpoint for signup
    # Check if user exists
    result = await session.exec(select(User).where(User.email == user.email))
    if result.first():
        raise HTTPException(status_code=400, detail="Email already registered")
        
    # Check if phone number exists
    result = await session.exec(select(User).where(User.phone_number == user.phone_number))
    if result.first():
        raise HTTPException(status_code=400, detail="Phone number already registered")
    
    hashed_password = get_password_hash(user.password)
    # Create user dict from base model and add hashed password
    user_data = user.dict(exclude={"password"})
    db_user = User(**user_data, hashed_password=hashed_password)
    
    session.add(db_user)
    await session.commit()
    await session.refresh(db_user)
    return db_user

@router.get("/", response_model=List[User])
async def get_users(session: AsyncSession = Depends(get_session), current_user: User = Depends(get_current_user)):
    result = await session.exec(select(User).where(User.deleted == False))
    users = result.all()
    return users

@router.get("/{user_id}", response_model=User)
async def get_user(user_id: UUID, session: AsyncSession = Depends(get_session), current_user: User = Depends(get_current_user)):
    user = await session.get(User, user_id)
    if not user or user.deleted:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.patch("/{user_id}", response_model=User)
async def update_user(user_id: UUID, user_update: UserUpdate, session: AsyncSession = Depends(get_session), current_user: User = Depends(get_current_user)):
    db_user = await session.get(User, user_id)
    if not db_user or db_user.deleted:
        raise HTTPException(status_code=404, detail="User not found")
    
    user_data = user_update.dict(exclude_unset=True)
    if "password" in user_data:
        password = user_data.pop("password")
        db_user.hashed_password = get_password_hash(password)
        
    for key, value in user_data.items():
        setattr(db_user, key, value)
        
    session.add(db_user)
    await session.commit()
    await session.refresh(db_user)
    return db_user

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: UUID, session: AsyncSession = Depends(get_session), current_user: User = Depends(get_current_user)):
    user = await session.get(User, user_id)
    if not user or user.deleted:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Soft delete
    user.deleted = True
    user.deleted_at = datetime.utcnow()
    session.add(user)
    await session.commit()

@router.post("/forgot-password")
async def forgot_password(email: str, session: AsyncSession = Depends(get_session)):
    result = await session.exec(select(User).where(User.email == email))
    user = result.first()
    if not user:
        # Don't reveal if user exists
        return {"message": "If the email exists, an OTP has been sent."}
    
    # Generate OTP
    otp = str(random.randint(100000, 999999))
    otp_expiry = datetime.utcnow() + timedelta(minutes=10)
    
    user.otp_code = otp
    user.otp_expires_at = otp_expiry
    session.add(user)
    await session.commit()
    
    # Send OTP via Email
    await send_email("Password Reset OTP", [email], f"Your OTP is: {otp}")
    
    return {"message": "If the email exists, an OTP has been sent."}

@router.post("/reset-password")
async def reset_password(email: str, otp: str, new_password: str, session: AsyncSession = Depends(get_session)):
    result = await session.exec(select(User).where(User.email == email))
    user = result.first()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid request")
        
    if not user.otp_code or not user.otp_expires_at:
        raise HTTPException(status_code=400, detail="No OTP request found")
        
    if user.otp_code != otp:
        raise HTTPException(status_code=400, detail="Invalid OTP")
        
    if datetime.utcnow() > user.otp_expires_at:
        raise HTTPException(status_code=400, detail="OTP expired")
        
    # Reset password
    user.hashed_password = get_password_hash(new_password)
    user.otp_code = None
    user.otp_expires_at = None
    session.add(user)
    await session.commit()
    
    return {"message": "Password reset successfully"}
