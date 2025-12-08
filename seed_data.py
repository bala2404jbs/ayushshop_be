import asyncio
from decimal import Decimal
from sqlmodel import select
from app.database import init_db, get_session
from app.models import User, Category, Product, Variant, ProductCategoryLink, BlogPost, Review, NewsletterSubscriber
from app.security import get_password_hash

async def seed_data():
    print("Starting data seeding...")
    await init_db()
    
    async for session in get_session():
        # 1. Create User
        user_email = "test@example.com"
        result = await session.exec(select(User).where(User.email == user_email))
        user = result.first()
        if not user:
            print(f"Creating user: {user_email}")
            user = User(
                email=user_email,
                hashed_password=get_password_hash("password123"),
                full_name="Test User",
                phone_number="1234567890",
                is_superuser=True
            )
            session.add(user)
        else:
            print(f"User {user_email} already exists.")
            
        # 2. Create Categories
        # 2. Create Categories
        categories_data = [
            {"name": "Ayurvedic Herbs"},
            {"name": "Essential Oils"},
            {"name": "Wellness Kits"},
        ]
        
        category_map = {}
        for cat_data in categories_data:
            result = await session.exec(select(Category).where(Category.name == cat_data["name"]))
            category = result.first()
            if not category:
                print(f"Creating category: {cat_data['name']}")
                category = Category(**cat_data)
                session.add(category)
            else:
                print(f"Category {cat_data['name']} already exists.")
            category_map[cat_data["name"]] = category
            
        await session.commit()
        for cat in category_map.values():
            await session.refresh(cat)

        # 3. Create Products
        # 3. Create Products from CSV
        import csv
        import os
        
        csv_file_path = "app/data/MOCK_DATA.csv"
        products_data = []
        
        if os.path.exists(csv_file_path):
            print(f"Reading products from {csv_file_path}...")
            with open(csv_file_path, mode='r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    # Handle category_names which might be a list in string format or semicolon separated
                    # In MOCK_DATA.csv, the column is 'attributes' which seems to contain category-like info (herbal, organic, etc.)
                    # We will map these attributes to our existing categories or create new ones if needed.
                    # For now, let's map 'herbal' -> 'Ayurvedic Herbs', 'organic' -> 'Wellness Kits', 'natural' -> 'Essential Oils'
                    
                    attribute = row.get("attributes", "").lower()
                    cat_names = []
                    if "herbal" in attribute:
                        cat_names.append("Ayurvedic Herbs")
                    elif "organic" in attribute:
                        cat_names.append("Wellness Kits")
                    elif "natural" in attribute:
                        cat_names.append("Essential Oils")
                    else:
                        cat_names.append("Ayurvedic Herbs") # Default
                    
                    products_data.append({
                        "name": row["name"],
                        "description": row["description"],
                        "base_price": Decimal(row["base_price"]),
                        "stock_quantity": int(row["stock_quantity"]),
                        "category_names": cat_names
                    })
        else:
            print("CSV file not found, using default sample data.")
            products_data = [
                {
                    "name": "Ashwagandha Powder",
                    "description": "Premium organic Ashwagandha root powder for stress relief.",
                    "base_price": Decimal("15.99"),
                    "stock_quantity": 100,
                    "category_names": ["Ayurvedic Herbs"]
                }
            ]
        
        for prod_data in products_data:
            result = await session.exec(select(Product).where(Product.name == prod_data["name"]))
            product = result.first()
            cat_names = prod_data["category_names"]
            
            if not product:
                print(f"Creating product: {prod_data['name']}")
                # Create product without category_names field
                product_dict = {k: v for k, v in prod_data.items() if k != "category_names"}
                product = Product(**product_dict)
                session.add(product)
                await session.commit()
                await session.refresh(product)
                
                # Link categories
                for name in cat_names:
                    name = name.strip()
                    category = category_map.get(name)
                    if category:
                        link = ProductCategoryLink(product_id=product.id, category_id=category.id)
                        session.add(link)
                    else:
                        print(f"Warning: Category '{name}' not found for product '{prod_data['name']}'")
                
                # Create variants for Ashwagandha (Example logic, can be generalized if needed)
                if prod_data["name"] == "Ashwagandha Powder":
                    v1 = Variant(
                        product_id=product.id,
                        sku="ASH-100",
                        name="100g",
                        price_adjustment=Decimal("0.00"),
                        stock_quantity=50
                    )
                    v2 = Variant(
                        product_id=product.id,
                        sku="ASH-250",
                        name="250g",
                        price_adjustment=Decimal("10.00"),
                        stock_quantity=50
                    )
                    session.add(v1)
                    session.add(v2)
                    
                await session.commit()
            else:
                print(f"Product {prod_data['name']} already exists.")

        # 4. Create Blog Posts
        blog_posts_data = [
            {
                "title": "The Benefits of Ashwagandha",
                "content": "Ashwagandha is an ancient medicinal herb...",
                "excerpt": "Discover the power of this ancient herb.",
                "author_name": "Dr. Ayurveda",
                "is_published": True
            },
            {
                "title": "5 Tips for a Balanced Dosha",
                "content": "Balancing your dosha is key to good health...",
                "excerpt": "Simple tips for daily balance.",
                "author_name": "Wellness Expert",
                "is_published": True
            }
        ]
        
        for post_data in blog_posts_data:
            result = await session.exec(select(BlogPost).where(BlogPost.title == post_data["title"]))
            post = result.first()
            if not post:
                print(f"Creating blog post: {post_data['title']}")
                post = BlogPost(**post_data)
                session.add(post)
            else:
                print(f"Blog post {post_data['title']} already exists.")
        
        await session.commit()

        # 5. Create Reviews (Mock)
        # We need a product and a user
        product_result = await session.exec(select(Product).limit(1))
        product = product_result.first()
        
        user_result = await session.exec(select(User).where(User.email == "test@example.com"))
        user = user_result.first()
        
        if product and user:
            review_check = await session.exec(select(Review).where(Review.product_id == product.id, Review.user_id == user.id))
            if not review_check.first():
                print(f"Creating review for product {product.name}")
                review = Review(
                    product_id=product.id,
                    user_id=user.id,
                    rating=5,
                    comment="Great product! Highly recommended."
                )
                session.add(review)
                await session.commit()
            else:
                print("Review already exists.")

        # 6. Create Newsletter Subscriber
        subscriber_email = "subscriber@example.com"
        sub_check = await session.exec(select(NewsletterSubscriber).where(NewsletterSubscriber.email == subscriber_email))
        if not sub_check.first():
            print(f"Creating subscriber: {subscriber_email}")
            subscriber = NewsletterSubscriber(email=subscriber_email)
            session.add(subscriber)
            await session.commit()
        else:
            print(f"Subscriber {subscriber_email} already exists.")

        # Verification
        print("\n--- Verification ---")
        users = await session.exec(select(User))
        print(f"Users: {len(users.all())}")
        cats = await session.exec(select(Category))
        print(f"Categories: {len(cats.all())}")
        prods = await session.exec(select(Product))
        print(f"Products: {len(prods.all())}")
        posts = await session.exec(select(BlogPost))
        print(f"Blog Posts: {len(posts.all())}")
        reviews = await session.exec(select(Review))
        print(f"Reviews: {len(reviews.all())}")
        subs = await session.exec(select(NewsletterSubscriber))
        print(f"Subscribers: {len(subs.all())}")
        
    print("Data seeding completed.")

if __name__ == "__main__":
    asyncio.run(seed_data())
