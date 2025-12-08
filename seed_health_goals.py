import asyncio
from sqlmodel import select
from app.database import engine
from app.models import HealthGoal, Product, ProductHealthGoalLink
from sqlalchemy.orm import sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession
import random

async def seed_health_goals():
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    print("🌱 Seeding Health Goals...")
    
    async with async_session() as session:
        # 1. Create Health Goals
        goals_data = [
            {"name": "Digestion", "description": "Supports healthy digestion and gut health"},
            {"name": "Stress Relief", "description": "Calms the mind and reduces stress"},
            {"name": "Immunity Boost", "description": "Strengthens the immune system"},
            {"name": "Sleep", "description": "Promotes restful sleep"},
            {"name": "Energy", "description": "Boosts natural energy levels"},
            {"name": "Skin Care", "description": "Promotes healthy, glowing skin"},
            {"name": "Hair Care", "description": "Strengthens hair and scalp health"},
            {"name": "Detox", "description": "Helps remove toxins from the body"},
        ]
        
        created_goals = []
        for data in goals_data:
            result = await session.exec(select(HealthGoal).where(HealthGoal.name == data["name"]))
            goal = result.first()
            
            if not goal:
                goal = HealthGoal(**data)
                session.add(goal)
                print(f"✅ Created Health Goal: {data['name']}")
            else:
                print(f"ℹ️  Health Goal exists: {data['name']}")
            created_goals.append(goal)
            
        await session.commit()
        
        # Refresh to get IDs
        for g in created_goals: await session.refresh(g)
        
        # 2. Link to existing products
        # Fetch all products
        result = await session.exec(select(Product))
        products = result.all()
        
        if not products:
            print("⚠️ No products found. Please seed products first.")
            return

        print(f"🔗 Linking {len(products)} products to health goals...")
        
        for product in products:
            # Check if already linked
            links = await session.exec(select(ProductHealthGoalLink).where(ProductHealthGoalLink.product_id == product.id))
            if links.first():
                continue
                
            # Randomly assign 1-3 goals
            selected_goals = random.sample(created_goals, k=random.randint(1, 3))
            
            for goal in selected_goals:
                link = ProductHealthGoalLink(product_id=product.id, health_goal_id=goal.id)
                session.add(link)
                print(f"   - Linked '{product.name}' to '{goal.name}'")
                
        await session.commit()
        print("🚀 Health Goals Seeding Complete!")

if __name__ == "__main__":
    asyncio.run(seed_health_goals())
