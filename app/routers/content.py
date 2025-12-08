from fastapi import APIRouter, Depends, HTTPException, Body
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
from typing import List
from ..database import get_session
from ..models import BlogPost, NewsletterSubscriber

router = APIRouter(prefix="/content", tags=["content"])

@router.get("/posts", response_model=List[BlogPost])
async def get_posts(session: AsyncSession = Depends(get_session)):
    query = select(BlogPost).where(BlogPost.is_published == True).order_by(BlogPost.published_at.desc())
    result = await session.exec(query)
    return result.all()

@router.post("/newsletter/subscribe", response_model=NewsletterSubscriber)
async def subscribe_newsletter(
    email: str = Body(..., embed=True),
    session: AsyncSession = Depends(get_session)
):
    # Check if already subscribed
    query = select(NewsletterSubscriber).where(NewsletterSubscriber.email == email)
    result = await session.exec(query)
    existing = result.first()
    
    if existing:
        if not existing.is_active:
            existing.is_active = True
            session.add(existing)
            await session.commit()
            await session.refresh(existing)
        return existing
        
    subscriber = NewsletterSubscriber(email=email)
    session.add(subscriber)
    await session.commit()
    await session.refresh(subscriber)
    return subscriber
