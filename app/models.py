from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import UUID, uuid4
from sqlmodel import Field, SQLModel, Relationship, Column, JSON, Integer, Identity
from decimal import Decimal

# --- Core Identity ---

class UserBase(SQLModel):
    email: str = Field(unique=True, index=True)
    is_active: bool = True
    is_superuser: bool = False
    full_name: Optional[str] = None
    phone_number: str = Field(unique=True, index=True)

class UserCreate(UserBase):
    password: str

class User(UserBase, table=True):
    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True)
    hashed_password: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    otp_code: Optional[str] = None
    otp_expires_at: Optional[datetime] = None
    deleted: bool = Field(default=False)
    deleted_at: Optional[datetime] = None
    
    addresses: List["Address"] = Relationship(back_populates="user")
    orders: List["Order"] = Relationship(back_populates="user")
    cart: Optional["Cart"] = Relationship(back_populates="user")
    reviews: List["Review"] = Relationship(back_populates="user")

class UserUpdate(SQLModel):
    email: Optional[str] = None
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None

class LoginRequest(SQLModel):
    email: str
    password: str

class AddressBase(SQLModel):
    first_name: str
    last_name: str
    address_line1: str
    address_line2: Optional[str] = None
    city: str
    state: Optional[str] = None
    country: str
    zip_code: str
    is_default: bool = False

class Address(AddressBase, table=True):
    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="user.id")
    user: Optional[User] = Relationship(back_populates="addresses")

# --- Catalog ---

class ProductCategoryLink(SQLModel, table=True):
    product_id: UUID = Field(foreign_key="product.id", primary_key=True)
    category_id: UUID = Field(foreign_key="category.id", primary_key=True)

class ProductHealthGoalLink(SQLModel, table=True):
    product_id: UUID = Field(foreign_key="product.id", primary_key=True)
    health_goal_id: UUID = Field(foreign_key="health_goal.id", primary_key=True)

class CategoryBase(SQLModel):
    name: str = Field(index=True)
    parent_id: Optional[UUID] = Field(default=None, foreign_key="category.id")

class Category(CategoryBase, table=True):
    __tablename__ = "category"
    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True)
    products: List["Product"] = Relationship(back_populates="categories", link_model=ProductCategoryLink)

class HealthGoalBase(SQLModel):
    name: str = Field(index=True, unique=True)
    description: Optional[str] = None

class HealthGoal(HealthGoalBase, table=True):
    __tablename__ = "health_goal"
    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True)
    products: List["Product"] = Relationship(back_populates="health_goals", link_model=ProductHealthGoalLink)

class ProductBase(SQLModel):
    name: str = Field(index=True)
    description: Optional[str] = None
    base_price: Decimal = Field(default=0.0, max_digits=10, decimal_places=2)
    currency: str = "USD"
    stock_quantity: int = 0
    is_active: bool = True
    attributes: Dict[str, Any] = Field(default={}, sa_column=Column(JSON)) # For custom fields like ingredients, dosha

class CategoryRead(CategoryBase):
    id: UUID

class HealthGoalRead(HealthGoalBase):
    id: UUID

class ProductCreate(ProductBase):
    category_ids: List[UUID] = []
    health_goal_ids: List[UUID] = []

class ProductRead(ProductBase):
    id: UUID
    categories: List[CategoryRead] = []
    health_goals: List[HealthGoalRead] = []

class ProductUpdate(SQLModel):
    name: Optional[str] = None
    description: Optional[str] = None
    base_price: Optional[Decimal] = None
    stock_quantity: Optional[int] = None
    is_active: Optional[bool] = None
    attributes: Optional[Dict[str, Any]] = None
    category_ids: Optional[List[UUID]] = None
    health_goal_ids: Optional[List[UUID]] = None

class Product(ProductBase, table=True):
    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True)
    deleted: bool = Field(default=False)
    deleted_at: Optional[datetime] = None
    
    categories: List[Category] = Relationship(back_populates="products", link_model=ProductCategoryLink)
    health_goals: List[HealthGoal] = Relationship(back_populates="products", link_model=ProductHealthGoalLink)
    images: List["ProductImage"] = Relationship(back_populates="product")
    variants: List["Variant"] = Relationship(back_populates="product")
    reviews: List["Review"] = Relationship(back_populates="product")

class ProductImage(SQLModel, table=True):
    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True)
    product_id: UUID = Field(foreign_key="product.id")
    url: str
    alt_text: Optional[str] = None
    display_order: int = 0
    product: Optional[Product] = Relationship(back_populates="images")

class Variant(SQLModel, table=True):
    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True)
    product_id: UUID = Field(foreign_key="product.id")
    sku: str = Field(unique=True)
    name: str # e.g. "Small", "Red"
    price_adjustment: Decimal = Field(default=0.0, max_digits=10, decimal_places=2)
    stock_quantity: int = 0
    attributes: Dict[str, Any] = Field(default={}, sa_column=Column(JSON))
    product: Optional[Product] = Relationship(back_populates="variants")

# --- Sales ---

class Cart(SQLModel, table=True):
    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True)
    user_id: Optional[UUID] = Field(default=None, foreign_key="user.id")
    session_token: Optional[str] = Field(index=True) # For guest carts
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    user: Optional[User] = Relationship(back_populates="cart")
    items: List["CartItem"] = Relationship(back_populates="cart")

class CartItem(SQLModel, table=True):
    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True)
    cart_id: UUID = Field(foreign_key="cart.id")
    product_id: UUID = Field(foreign_key="product.id")
    variant_id: Optional[UUID] = Field(default=None, foreign_key="variant.id")
    quantity: int = 1
    
    cart: Optional[Cart] = Relationship(back_populates="items")

class Order(SQLModel, table=True):
    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True)
    readable_id: Optional[int] = Field(default=None, sa_column=Column(Integer, Identity(start=1000), unique=True)) # Auto-incrementing ID like #1001
    user_id: Optional[UUID] = Field(default=None, foreign_key="user.id")
    total_amount: Decimal = Field(max_digits=10, decimal_places=2)
    status: str = "pending" # pending, paid, shipped, delivered, cancelled
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    shipping_address_snapshot: Dict[str, Any] = Field(default={}, sa_column=Column(JSON))
    billing_address_snapshot: Dict[str, Any] = Field(default={}, sa_column=Column(JSON))
    
    user: Optional[User] = Relationship(back_populates="orders")
    items: List["OrderItem"] = Relationship(back_populates="order")
    payments: List["Payment"] = Relationship(back_populates="order")

class OrderItem(SQLModel, table=True):
    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True)
    order_id: UUID = Field(foreign_key="order.id")
    product_id: UUID = Field(foreign_key="product.id")
    product_name: str
    unit_price: Decimal = Field(max_digits=10, decimal_places=2)
    quantity: int
    
    order: Optional[Order] = Relationship(back_populates="items")

class Payment(SQLModel, table=True):
    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True)
    order_id: UUID = Field(foreign_key="order.id")
    amount: Decimal = Field(max_digits=10, decimal_places=2)
    provider: str # stripe, paypal
    transaction_id: Optional[str] = None
    status: str = "pending"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    order: Optional[Order] = Relationship(back_populates="payments")

# --- Content & Social ---

class Review(SQLModel, table=True):
    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True)
    product_id: UUID = Field(foreign_key="product.id")
    user_id: UUID = Field(foreign_key="user.id")
    rating: int = Field(ge=1, le=5)
    comment: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    product: Optional[Product] = Relationship(back_populates="reviews")
    user: Optional[User] = Relationship(back_populates="reviews")

class BlogPost(SQLModel, table=True):
    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True)
    title: str
    content: str
    excerpt: Optional[str] = None
    cover_image_url: Optional[str] = None
    author_name: str
    published_at: datetime = Field(default_factory=datetime.utcnow)
    is_published: bool = True

class NewsletterSubscriber(SQLModel, table=True):
    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True)
    email: str = Field(unique=True, index=True)
    subscribed_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = True
