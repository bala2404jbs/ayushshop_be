from fastapi import FastAPI
from contextlib import asynccontextmanager
from .database import init_db
from .routers import products, users, cart, orders, content, auth, admin

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield

app = FastAPI(title="E-commerce Core API", lifespan=lifespan)

app.include_router(products.router)
app.include_router(users.router)
app.include_router(auth.router)
app.include_router(cart.router)
app.include_router(orders.router)
app.include_router(content.router)
app.include_router(admin.router)

from fastapi import Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

@app.exception_handler(IntegrityError)
async def integrity_exception_handler(request: Request, exc: IntegrityError):
    # Extract the original error message
    orig_error = str(exc.orig) if exc.orig else str(exc)
    
    # Extract the specific violation message (e.g., "null value in column ...")
    # The error usually looks like: <class '...'>: THE_MESSAGE
    if ": " in orig_error:
        detail = orig_error.split(": ", 1)[1]
    else:
        detail = orig_error

    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": detail},
    )

@app.get("/health")
async def health_check():
    return {"status": "ok"}
