import asyncio
from app.database import init_db, get_session
from app.models import User, Product
from app.config import settings

async def main():
    print(f"Connecting to database at {settings.DATABASE_URL}...")
    try:
        await init_db()
        print("Database initialized successfully.")
        
        # Test session
        async for session in get_session():
            print("Session created successfully.")
            # Try a simple query
            # result = await session.exec(select(User))
            # print(f"User count: {len(result.all())}")
            break
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
