from fastapi import APIRouter, Depends, HTTPException, Body
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
from sqlalchemy.orm import selectinload
from typing import List, Optional
from uuid import UUID, uuid4
from ..database import get_session
from ..models import Cart, CartItem, Product, User
from ..dependencies import get_current_user_optional

router = APIRouter(prefix="/cart", tags=["cart"])

@router.get("/", response_model=Cart)
async def get_cart(
    session_token: Optional[str] = None,
    user_id: Optional[UUID] = None,
    current_user: Optional[User] = Depends(get_current_user_optional),
    session: AsyncSession = Depends(get_session)
):
    if current_user:
        user_id = current_user.id

    query = select(Cart).options(selectinload(Cart.items))
    
    if user_id:
        query = query.where(Cart.user_id == user_id)
    elif session_token:
        query = query.where(Cart.session_token == session_token)
    else:
        # Create a new guest cart
        session_token = str(uuid4())
        cart = Cart(session_token=session_token)
        session.add(cart)
        await session.commit()
        await session.refresh(cart)
        return cart

    result = await session.exec(query)
    cart = result.first()
    
    if not cart:
        cart = Cart(user_id=user_id, session_token=session_token)
        session.add(cart)
        await session.commit()
        await session.refresh(cart)
        
    return cart

@router.post("/items", response_model=Cart)
async def add_to_cart(
    product_id: UUID = Body(...),
    quantity: int = Body(1),
    session_token: Optional[str] = Body(None),
    user_id: Optional[UUID] = Body(None),
    current_user: Optional[User] = Depends(get_current_user_optional),
    session: AsyncSession = Depends(get_session)
):
    if current_user:
        user_id = current_user.id

    # Find or create cart
    query = select(Cart).options(selectinload(Cart.items))
    if user_id:
        query = query.where(Cart.user_id == user_id)
    elif session_token:
        query = query.where(Cart.session_token == session_token)
    else:
        session_token = str(uuid4())
        cart = Cart(session_token=session_token)
        session.add(cart)
        await session.commit()
        await session.refresh(cart)
        # Re-query to get options loaded or just use the instance
        # Newly created cart has empty items, so it's fine.
    
    if 'cart' not in locals():
        result = await session.exec(query)
        cart = result.first()
        if not cart:
            cart = Cart(user_id=user_id, session_token=session_token)
            session.add(cart)
            await session.commit()
            await session.refresh(cart)

    # Check if item exists
    item_query = select(CartItem).where(CartItem.cart_id == cart.id, CartItem.product_id == product_id)
    item_result = await session.exec(item_query)
    cart_item = item_result.first()
    
    if cart_item:
        cart_item.quantity += quantity
        session.add(cart_item)
    else:
        cart_item = CartItem(cart_id=cart.id, product_id=product_id, quantity=quantity)
        session.add(cart_item)
        
    await session.commit()
    
    # Refresh cart to get updated items
    # We need to re-fetch with selectinload
    result = await session.exec(select(Cart).options(selectinload(Cart.items)).where(Cart.id == cart.id))
    cart = result.first()
    return cart

@router.put("/items/{item_id}", response_model=CartItem)
async def update_cart_item(
    item_id: UUID,
    quantity: int = Body(...),
    current_user: Optional[User] = Depends(get_current_user_optional),
    session: AsyncSession = Depends(get_session)
):
    cart_item = await session.get(CartItem, item_id)
    if not cart_item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    # Optional: Check ownership if user is logged in
    # if current_user:
    #     cart = await session.get(Cart, cart_item.cart_id)
    #     if cart.user_id != current_user.id:
    #         raise HTTPException(status_code=403, detail="Not authorized")

    if quantity <= 0:
        await session.delete(cart_item)
    else:
        cart_item.quantity = quantity
        session.add(cart_item)
        
    await session.commit()
    if quantity > 0:
        await session.refresh(cart_item)
        return cart_item
    return cart_item

@router.delete("/items/{item_id}")
async def remove_cart_item(
    item_id: UUID,
    current_user: Optional[User] = Depends(get_current_user_optional),
    session: AsyncSession = Depends(get_session)
):
    cart_item = await session.get(CartItem, item_id)
    if not cart_item:
        raise HTTPException(status_code=404, detail="Item not found")
        
    await session.delete(cart_item)
    await session.commit()
    return {"ok": True}
