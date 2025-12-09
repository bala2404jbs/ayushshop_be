from fastapi import APIRouter, Depends, HTTPException, Body
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
from sqlalchemy.orm import selectinload
from typing import List, Optional
from uuid import UUID
from ..database import get_session
from ..models import Order, OrderItem, Cart, CartItem, Product

router = APIRouter(prefix="/orders", tags=["orders"])

@router.post("/", response_model=Order)
async def create_order(
    cart_id: UUID = Body(...),
    shipping_address: dict = Body(...),
    billing_address: dict = Body(...),
    session: AsyncSession = Depends(get_session)
):
    # Get cart with items
    query = select(Cart).options(selectinload(Cart.items)).where(Cart.id == cart_id)
    result = await session.exec(query)
    cart = result.first()
    
    if not cart or not cart.items:
        raise HTTPException(status_code=400, detail="Cart is empty or not found")
        
    # Calculate total
    total_amount = 0
    order_items = []
    
    for item in cart.items:
        product = await session.get(Product, item.product_id)
        if not product:
            continue
            
        total_amount += product.base_price * item.quantity
        
        order_item = OrderItem(
            product_id=product.id,
            product_name=product.name,
            unit_price=product.base_price,
            quantity=item.quantity
        )
        order_items.append(order_item)
        
    # Create Order
    order = Order(
        user_id=cart.user_id,
        total_amount=total_amount,
        status="pending",
        shipping_address_snapshot=shipping_address,
        billing_address_snapshot=billing_address,
        items=order_items
    )
    
    session.add(order)
    
    # Clear cart items
    for item in cart.items:
        await session.delete(item)
        
    await session.commit()
    await session.refresh(order)
    
    return order

from ..dependencies import get_current_user
from ..models import User

@router.get("/", response_model=List[Order])
async def get_orders(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Get all orders for the current user.
    """
    query = select(Order).where(Order.user_id == current_user.id).options(selectinload(Order.items)).order_by(Order.created_at.desc())
    result = await session.exec(query)
    return result.all()

@router.get("/{order_id}", response_model=Order)
async def get_order(
    order_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Get a specific order by ID.
    """
    query = select(Order).where(Order.id == order_id, Order.user_id == current_user.id).options(selectinload(Order.items))
    result = await session.exec(query)
    order = result.first()
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
        
    return order
