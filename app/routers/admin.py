from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select, func, col
from datetime import datetime, timedelta, date
from typing import List, Dict, Any
from uuid import UUID

from ..database import get_session
from ..models import User, Order, Product
from ..dependencies import get_current_user

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    responses={404: {"description": "Not found"}},
)

# Helper to ensure user is admin
def check_admin(user: User = Depends(get_current_user)):
    if not user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    return user

@router.get("/dashboard-stats")
async def get_dashboard_stats(
    current_user: User = Depends(check_admin),
    session: AsyncSession = Depends(get_session)
):
    """
    Get aggregated statistics for the admin dashboard.
    """
    
    # 1. Date Ranges
    today_start = datetime.combine(date.today(), datetime.min.time())
    yesterday_start = today_start - timedelta(days=1)
    
    # 2. Revenue Stats
    # Today's Revenue
    query_today_revenue = select(func.sum(Order.total_amount)).where(Order.created_at >= today_start)
    today_revenue_result = await session.exec(query_today_revenue)
    today_revenue = today_revenue_result.one() or 0
    
    # Yesterday's Revenue (for percentage calc)
    query_yesterday_revenue = select(func.sum(Order.total_amount)).where(
        Order.created_at >= yesterday_start,
        Order.created_at < today_start
    )
    yesterday_revenue_result = await session.exec(query_yesterday_revenue)
    yesterday_revenue = yesterday_revenue_result.one() or 0
    
    # Revenue Growth
    revenue_growth = 0
    if yesterday_revenue > 0:
        revenue_growth = ((today_revenue - yesterday_revenue) / yesterday_revenue) * 100
    elif today_revenue > 0:
        revenue_growth = 100 # 100% growth if yesterday was 0
        
    # 3. Order Stats
    # Today's Orders
    query_today_orders = select(func.count(Order.id)).where(Order.created_at >= today_start)
    today_orders_result = await session.exec(query_today_orders)
    today_orders = today_orders_result.one() or 0
    
    # Yesterday's Orders
    query_yesterday_orders = select(func.count(Order.id)).where(
        Order.created_at >= yesterday_start,
        Order.created_at < today_start
    )
    yesterday_orders_result = await session.exec(query_yesterday_orders)
    yesterday_orders = yesterday_orders_result.one() or 0
    
    # Order Growth
    order_growth = 0
    if yesterday_orders > 0:
        order_growth = ((today_orders - yesterday_orders) / yesterday_orders) * 100
    elif today_orders > 0:
        order_growth = 100
        
    # 4. Product Stats
    # Low Stock Products (threshold < 10)
    LOW_STOCK_THRESHOLD = 10
    query_low_stock = select(func.count(Product.id)).where(Product.stock_quantity < LOW_STOCK_THRESHOLD)
    low_stock_result = await session.exec(query_low_stock)
    low_stock_count = low_stock_result.one() or 0
    
    # 5. Customer Stats
    # New Customers Today
    query_new_customers = select(func.count(User.id)).where(User.created_at >= today_start)
    new_customers_result = await session.exec(query_new_customers)
    new_customers = new_customers_result.one() or 0
    
    # Yesterday's Customers
    query_yesterday_customers = select(func.count(User.id)).where(
        User.created_at >= yesterday_start,
        User.created_at < today_start
    )
    yesterday_customers_result = await session.exec(query_yesterday_customers)
    yesterday_customers = yesterday_customers_result.one() or 0
    
    # Customer Growth
    customer_growth = 0
    if yesterday_customers > 0:
        customer_growth = ((new_customers - yesterday_customers) / yesterday_customers) * 100
    elif new_customers > 0:
        customer_growth = 100

    # 6. Recent Orders List (Top 5)
    query_recent_orders = select(Order).order_by(col(Order.created_at).desc()).limit(5)
    recent_orders_result = await session.exec(query_recent_orders)
    recent_orders = recent_orders_result.all()
    
    # Fetch user names for these orders efficiently
    # Note: In a real app with high load, we might use a join. 
    # For now, lazy loading or explicit fetch is fine for 5 items.
    recent_orders_data = []
    for order in recent_orders:
        user_name = "Guest"
        if order.user_id:
            user = await session.get(User, order.user_id)
            if user:
                user_name = user.full_name or user.email
        
        recent_orders_data.append({
            "id": order.id,
            "readable_id": order.readable_id, # The new field we added
            "customer_name": user_name,
            "date": order.created_at,
            "status": order.status,
            "total_amount": order.total_amount
        })

    # 7. Low Stock Alerts List (Top 5)
    query_low_stock_list = select(Product).where(Product.stock_quantity < LOW_STOCK_THRESHOLD).limit(5)
    low_stock_list_result = await session.exec(query_low_stock_list)
    low_stock_items = low_stock_list_result.all()
    
    low_stock_data = [
        {
            "id": p.id,
            "name": p.name,
            "stock_quantity": p.stock_quantity
        }
        for p in low_stock_items
    ]

    return {
        "stats": {
            "revenue": {
                "value": today_revenue,
                "growth": round(revenue_growth, 1)
            },
            "orders": {
                "value": today_orders,
                "growth": round(order_growth, 1)
            },
            "low_stock": {
                "value": low_stock_count,
                # "growth": 0 # Not really relevant for stock
            },
            "customers": {
                "value": new_customers,
                "growth": round(customer_growth, 1)
            }
        },
        "recent_orders": recent_orders_data,
        "low_stock_alerts": low_stock_data
    }
