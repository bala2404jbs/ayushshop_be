import asyncio
from datetime import datetime, timedelta
from sqlmodel import select
from app.database import get_session, init_db, engine
from app.models import User, Product, Order, OrderItem, Category
from app.security import get_password_hash
from decimal import Decimal
import random

async def seed_dashboard_data():
    # We need to use the session context manager manually since we are not in a FastAPI request
    from sqlalchemy.orm import sessionmaker
    from sqlmodel.ext.asyncio.session import AsyncSession
    
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    print("🌱 Seeding Dashboard Data...")
    
    async with async_session() as session:
        # 1. Ensure we have an Admin User
        result = await session.exec(select(User).where(User.email == "admin@example.com"))
        admin = result.first()
        if not admin:
            admin = User(
                email="admin@example.com",
                hashed_password=get_password_hash("admin123"),
                full_name="Admin User",
                phone_number="+1000000000",
                is_superuser=True,
                is_active=True
            )
            session.add(admin)
            print("✅ Created Admin User: admin@example.com / admin123")
        
        # 2. Create some Customers (Today and Yesterday)
        customers = []
        for i in range(5):
            email = f"customer{i}@example.com"
            result = await session.exec(select(User).where(User.email == email))
            user = result.first()
            
            if not user:
                # Check if phone exists too
                phone = f"+100000000{i}"
                existing_phone_result = await session.exec(select(User).where(User.phone_number == phone))
                existing_user = existing_phone_result.first()
                
                if existing_user:
                    print(f"⚠️ Skipping Customer {i} (Phone {phone} exists)")
                    customers.append(existing_user)
                    continue

                # Randomly assign created_at to today or yesterday
                is_today = random.choice([True, False])
                created_at = datetime.utcnow() if is_today else datetime.utcnow() - timedelta(days=1)
                
                user = User(
                    email=email,
                    hashed_password=get_password_hash("user123"),
                    full_name=f"Customer {i}",
                    phone_number=phone,
                    created_at=created_at
                )
                session.add(user)
                customers.append(user)
                print(f"✅ Created Customer: {email} ({'Today' if is_today else 'Yesterday'})")
            else:
                customers.append(user)
        
        # 3. Create Products (Some low stock)
        products = []
        for i in range(10):
            name = f"Ayurvedic Product {i}"
            result = await session.exec(select(Product).where(Product.name == name))
            product = result.first()
            
            if not product:
                stock = random.randint(0, 50)
                # Force some low stock
                if i < 3: 
                    stock = random.randint(0, 5)
                
                product = Product(
                    name=name,
                    description="Natural healing product",
                    base_price=Decimal(random.randint(10, 100)),
                    stock_quantity=stock,
                    is_active=True
                )
                session.add(product)
                products.append(product)
                print(f"✅ Created Product: {name} (Stock: {stock})")
            else:
                products.append(product)

        await session.commit()
        
        # Refresh to get IDs
        for p in products: await session.refresh(p)
        for c in customers: await session.refresh(c)

        # 4. Create Orders (Today and Yesterday)
        # We need products and customers to exist first
        if products and customers:
            for i in range(10):
                # Randomly assign to today or yesterday
                is_today = random.choice([True, False])
                created_at = datetime.utcnow() if is_today else datetime.utcnow() - timedelta(days=1)
                
                customer = random.choice(customers)
                
                order = Order(
                    user_id=customer.id,
                    total_amount=Decimal(0), # Will calculate
                    status=random.choice(["pending", "shipped", "delivered"]),
                    created_at=created_at
                )
                session.add(order)
                await session.commit()
                await session.refresh(order)
                
                # Add Items
                total = 0
                for _ in range(random.randint(1, 3)):
                    product = random.choice(products)
                    qty = random.randint(1, 2)
                    price = product.base_price
                    
                    item = OrderItem(
                        order_id=order.id,
                        product_id=product.id,
                        product_name=product.name,
                        unit_price=price,
                        quantity=qty
                    )
                    session.add(item)
                    total += (price * qty)
                
                order.total_amount = total
                session.add(order)
                print(f"✅ Created Order #{order.readable_id} for ${total} ({'Today' if is_today else 'Yesterday'})")

        await session.commit()
        print("🚀 Seeding Complete!")

if __name__ == "__main__":
    asyncio.run(seed_dashboard_data())
