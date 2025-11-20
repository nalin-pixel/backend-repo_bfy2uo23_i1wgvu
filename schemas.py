"""
Database Schemas

Define your MongoDB collection schemas here using Pydantic models.
These schemas are used for data validation in your application.

Each Pydantic model represents a collection in your database.
Model name is converted to lowercase for the collection name:
- User -> "user" collection
- Product -> "product" collection
- BlogPost -> "blogs" collection
"""

from pydantic import BaseModel, Field
from typing import Optional, List

# Swiggy-like app schemas

class Restaurant(BaseModel):
    name: str = Field(..., description="Restaurant name")
    description: Optional[str] = Field(None, description="Short description or tagline")
    cuisine: List[str] = Field(default_factory=list, description="Cuisines served")
    rating: float = Field(4.0, ge=0, le=5, description="Average rating")
    delivery_time_mins: int = Field(30, ge=5, le=120, description="Estimated delivery time in minutes")
    image_url: Optional[str] = Field(None, description="Hero image for the restaurant")
    location: Optional[str] = Field(None, description="Area or city")

class MenuItem(BaseModel):
    restaurant_id: str = Field(..., description="Restaurant ObjectId as string")
    name: str = Field(..., description="Item name")
    description: Optional[str] = Field(None, description="Item description")
    price: float = Field(..., ge=0, description="Price in USD")
    veg: bool = Field(False, description="Vegetarian option")
    spicy: bool = Field(False, description="Spicy flag")
    image_url: Optional[str] = Field(None, description="Image of the item")
    category: Optional[str] = Field(None, description="Category like 'Burgers', 'Drinks'")

class OrderItem(BaseModel):
    item_id: str
    name: str
    price: float
    quantity: int = Field(1, ge=1)

class Order(BaseModel):
    restaurant_id: str
    restaurant_name: str
    customer_name: str
    customer_phone: str
    customer_address: str
    items: List[OrderItem]
    total: float
    status: str = Field("placed", description="placed|preparing|on_the_way|delivered|cancelled")
