from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select, col
from typing import List, Optional, Dict, Any
from uuid import UUID
from ..database import get_session
from datetime import datetime
from ..models import Product, ProductBase, Review, Category, ProductCategoryLink, ProductRead, ProductCreate, CategoryRead, ProductUpdate, HealthGoal, ProductHealthGoalLink
from fastapi import status

from sqlalchemy.orm import selectinload

router = APIRouter(prefix="/products", tags=["products"])

from ..schemas import PaginatedResponse
from sqlmodel import func

@router.get("/", response_model=PaginatedResponse[ProductRead])
async def get_products(
    category_name: Optional[str] = None,
    category_id: Optional[UUID] = None,
    search: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    sort_by: Optional[str] = "popularity",
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
    health_goal_name: Optional[str] = None,
    health_goal_id: Optional[UUID] = None,
    session: AsyncSession = Depends(get_session)
):
    # Base query
    query = select(Product).where(Product.deleted == False)
    
    # Apply filters
    if category_name:
        query = query.join(ProductCategoryLink).join(Category).where(Category.name == category_name)
        
    if category_id:
        if not category_name:
             query = query.join(ProductCategoryLink).join(Category)
        query = query.where(Category.id == category_id)

    if health_goal_name:
        query = query.join(ProductHealthGoalLink).join(HealthGoal).where(HealthGoal.name == health_goal_name)
        
    if health_goal_id:
        if not health_goal_name:
             query = query.join(ProductHealthGoalLink).join(HealthGoal)
        query = query.where(HealthGoal.id == health_goal_id)
        
    if search:
        query = query.where(col(Product.name).contains(search) | col(Product.description).contains(search))
        
    if min_price is not None:
        query = query.where(Product.base_price >= min_price)
        
    if max_price is not None:
        query = query.where(Product.base_price <= max_price)

    # Count total items (before pagination)
    count_query = select(func.count()).select_from(query.subquery())
    total_item_result = await session.exec(count_query)
    total_item = total_item_result.one()

    # Apply sorting
    if sort_by == "price_asc":
        query = query.order_by(Product.base_price.asc())
    elif sort_by == "price_desc":
        query = query.order_by(Product.base_price.desc())
        
    # Apply pagination
    skip = (page - 1) * pageSize
    query = query.options(selectinload(Product.categories), selectinload(Product.health_goals)).offset(skip).limit(pageSize)
        
    result = await session.exec(query)
    products_db = result.unique().all()
    
    # Explicitly convert to Pydantic models to ensure relationships are serialized
    products = [ProductRead.from_orm(p) for p in products_db]
    
    total_page = (total_item + pageSize - 1) // pageSize if pageSize > 0 else 0
    
    return PaginatedResponse(
        data=products,
        page=page,
        pageSize=pageSize,
        totalItem=total_item,
        totalPage=total_page
    )

@router.post("/", response_model=ProductRead)
async def create_product(product: ProductCreate, session: AsyncSession = Depends(get_session)):
    db_product = Product.from_orm(product)
    session.add(db_product)
    await session.commit()
    await session.refresh(db_product)
    
    if product.category_ids:
        for cat_id in product.category_ids:
            category = await session.get(Category, cat_id)
            if category:
                link = ProductCategoryLink(product_id=db_product.id, category_id=cat_id)
                session.add(link)
        await session.commit()
        
    if product.health_goal_ids:
        for goal_id in product.health_goal_ids:
            goal = await session.get(HealthGoal, goal_id)
            if goal:
                link = ProductHealthGoalLink(product_id=db_product.id, health_goal_id=goal_id)
                session.add(link)
        await session.commit()
        
    # Re-fetch with categories and health goals
    query = select(Product).where(Product.id == db_product.id).options(selectinload(Product.categories), selectinload(Product.health_goals))
    result = await session.exec(query)
    updated_product = result.first()
    
    return updated_product

from ..models import HealthGoalRead

@router.get("/filters", response_model=Dict[str, List[Any]])
async def get_product_filters(session: AsyncSession = Depends(get_session)):
    """
    Get available filters for products (Categories, Health Goals).
    """
    # Fetch Categories
    categories_result = await session.exec(select(Category))
    categories = categories_result.all()
    
    # Fetch Health Goals
    health_goals_result = await session.exec(select(HealthGoal))
    health_goals = health_goals_result.all()
    
    return {
        "categories": categories,
        "health_goals": health_goals
    }

@router.get("/{product_id}", response_model=ProductRead)
async def get_product(product_id: UUID, session: AsyncSession = Depends(get_session)):
    query = select(Product).where(Product.id == product_id).options(selectinload(Product.categories), selectinload(Product.health_goals))
    result = await session.exec(query)
    product = result.first()
    if not product or product.deleted:
        raise HTTPException(status_code=404, detail="Product not found")
    return product

@router.patch("/{product_id}", response_model=ProductRead)
async def update_product(product_id: UUID, product_update: ProductUpdate, session: AsyncSession = Depends(get_session)):
    db_product = await session.get(Product, product_id)
    if not db_product or db_product.deleted:
        raise HTTPException(status_code=404, detail="Product not found")
    
    product_data = product_update.dict(exclude_unset=True)
    
    # Handle categories separately
    if "category_ids" in product_data:
        category_ids = product_data.pop("category_ids")
        # Clear existing links
        links = await session.exec(select(ProductCategoryLink).where(ProductCategoryLink.product_id == product_id))
        for link in links.all():
            await session.delete(link)
            
        # Add new links
        if category_ids:
            for cat_id in category_ids:
                category = await session.get(Category, cat_id)
                if category:
                    link = ProductCategoryLink(product_id=product_id, category_id=cat_id)
                    session.add(link)
                    
    # Handle health goals separately
    if "health_goal_ids" in product_data:
        health_goal_ids = product_data.pop("health_goal_ids")
        # Clear existing links
        links = await session.exec(select(ProductHealthGoalLink).where(ProductHealthGoalLink.product_id == product_id))
        for link in links.all():
            await session.delete(link)
            
        # Add new links
        if health_goal_ids:
            for goal_id in health_goal_ids:
                goal = await session.get(HealthGoal, goal_id)
                if goal:
                    link = ProductHealthGoalLink(product_id=product_id, health_goal_id=goal_id)
                    session.add(link)
    
    for key, value in product_data.items():
        setattr(db_product, key, value)
        
    session.add(db_product)
    await session.commit()
    await session.refresh(db_product)
    
    # Re-fetch with categories and health goals
    query = select(Product).where(Product.id == db_product.id).options(selectinload(Product.categories), selectinload(Product.health_goals))
    result = await session.exec(query)
    updated_product = result.first()
    
    return updated_product

@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(product_id: UUID, session: AsyncSession = Depends(get_session)):
    product = await session.get(Product, product_id)
    if not product or product.deleted:
        raise HTTPException(status_code=404, detail="Product not found")
    
    product.deleted = True
    product.deleted_at = datetime.utcnow()
    session.add(product)
    await session.commit()

@router.get("/{product_id}/reviews", response_model=List[Review])
async def get_product_reviews(product_id: UUID, session: AsyncSession = Depends(get_session)):
    query = select(Review).where(Review.product_id == product_id)
    result = await session.exec(query)
    return result.all()

from ..dependencies import get_current_user
from ..models import User

@router.post("/{product_id}/reviews", response_model=Review)
async def create_product_review(
    product_id: UUID, 
    review: Review, 
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    review.product_id = product_id
    review.user_id = current_user.id
    session.add(review)
    await session.commit()
    await session.refresh(review)
    return review

@router.get("/{product_id}/related", response_model=List[ProductRead])
async def get_related_products(product_id: UUID, session: AsyncSession = Depends(get_session)):
    query = select(Product).where(Product.id != product_id).where(Product.deleted == False).options(selectinload(Product.categories)).limit(4)
    result = await session.exec(query)
    return result.all()
