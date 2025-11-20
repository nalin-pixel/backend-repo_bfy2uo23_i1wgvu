import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from bson import ObjectId

from database import db, create_document, get_documents
from schemas import Restaurant, MenuItem, Order, OrderItem

app = FastAPI(title="Food Delivery API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Helpers
class IdModel(BaseModel):
    id: str


def oid(id_str: str):
    try:
        return ObjectId(id_str)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid id")


@app.get("/")
def root():
    return {"service": "Food Delivery API", "status": "ok"}


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set"
            response["database_name"] = db.name
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
    return response


# Restaurant Endpoints
@app.post("/restaurants")
def create_restaurant(payload: Restaurant):
    _id = create_document("restaurant", payload)
    return {"id": _id}


@app.get("/restaurants")
def list_restaurants(q: Optional[str] = None, cuisine: Optional[str] = None):
    filt = {}
    if q:
        filt["name"] = {"$regex": q, "$options": "i"}
    if cuisine:
        filt["cuisine"] = {"$elemMatch": {"$regex": cuisine, "$options": "i"}}
    docs = get_documents("restaurant", filt, limit=50)
    for d in docs:
        d["id"] = str(d.pop("_id"))
    return docs


# Menu Endpoints
@app.post("/menu")
def create_menu_item(payload: MenuItem):
    # ensure restaurant exists
    rest = db["restaurant"].find_one({"_id": oid(payload.restaurant_id)})
    if not rest:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    _id = create_document("menuitem", payload)
    return {"id": _id}


@app.get("/menu/{restaurant_id}")
def list_menu(restaurant_id: str):
    docs = get_documents("menuitem", {"restaurant_id": restaurant_id}, limit=200)
    for d in docs:
        d["id"] = str(d.pop("_id"))
    return docs


# Orders
class CreateOrder(BaseModel):
    restaurant_id: str
    customer_name: str
    customer_phone: str
    customer_address: str
    items: List[OrderItem]


@app.post("/orders")
def place_order(payload: CreateOrder):
    # compute total and prepare order
    menu_items = {str(m["_id"]): m for m in db["menuitem"].find({"restaurant_id": payload.restaurant_id})}
    order_items = []
    total = 0.0
    for it in payload.items:
        # trust client-provided name/price if exists in menu, else use provided price
        if it.item_id in menu_items:
            m = menu_items[it.item_id]
            price = float(m.get("price", it.price))
            name = m.get("name", it.name)
        else:
            price = float(it.price)
            name = it.name
        total += price * it.quantity
        order_items.append({"item_id": it.item_id, "name": name, "price": price, "quantity": it.quantity})

    order_doc = Order(
        restaurant_id=payload.restaurant_id,
        restaurant_name=db["restaurant"].find_one({"_id": oid(payload.restaurant_id)} or {}).get("name", "Restaurant"),
        customer_name=payload.customer_name,
        customer_phone=payload.customer_phone,
        customer_address=payload.customer_address,
        items=[OrderItem(**oi) for oi in order_items],
        total=round(total, 2),
    )
    _id = create_document("order", order_doc)
    return {"id": _id, "total": order_doc.total, "status": "placed"}


@app.get("/orders")
def list_orders(limit: int = 50):
    docs = get_documents("order", {}, limit=limit)
    for d in docs:
        d["id"] = str(d.pop("_id"))
    return docs


# Seed demo data endpoint
@app.post("/seed")
def seed_demo():
    if db["restaurant"].count_documents({}) > 0:
        return {"status": "ok", "message": "Data already seeded"}

    rest1 = Restaurant(
        name="Burger Hub",
        description="Juicy burgers and fries",
        cuisine=["American", "Fast Food"],
        rating=4.3,
        delivery_time_mins=25,
        image_url="https://images.unsplash.com/photo-1550547660-d9450f859349?w=1200&q=60",
        location="Downtown",
    )
    rest2 = Restaurant(
        name="Curry Palace",
        description="Authentic Indian cuisine",
        cuisine=["Indian", "Curry"],
        rating=4.6,
        delivery_time_mins=35,
        image_url="https://images.unsplash.com/photo-1604908176997-4312f5b2d3c6?w=1200&q=60",
        location="Midtown",
    )

    r1_id = create_document("restaurant", rest1)
    r2_id = create_document("restaurant", rest2)

    items = [
        MenuItem(restaurant_id=r1_id, name="Classic Burger", description="Beef patty, cheese, lettuce", price=8.99, veg=False, spicy=False, image_url="https://images.unsplash.com/photo-1550317138-10000687a72b?w=1200&q=60", category="Burgers"),
        MenuItem(restaurant_id=r1_id, name="Veggie Burger", description="Grilled veggie patty", price=7.49, veg=True, spicy=False, image_url="https://images.unsplash.com/photo-1606756790138-2614cf5f327f?w=1200&q=60", category="Burgers"),
        MenuItem(restaurant_id=r1_id, name="Fries", description="Crispy golden fries", price=3.49, veg=True, spicy=False, image_url="https://images.unsplash.com/photo-1540189549336-e6e99c3679fe?w=1200&q=60", category="Sides"),
        MenuItem(restaurant_id=r2_id, name="Butter Chicken", description="Creamy tomato gravy", price=12.99, veg=False, spicy=False, image_url="https://images.unsplash.com/photo-1628294895950-980525a64300?w=1200&q=60", category="Main"),
        MenuItem(restaurant_id=r2_id, name="Paneer Tikka", description="Marinated cottage cheese", price=10.99, veg=True, spicy=True, image_url="https://images.unsplash.com/photo-1625944528406-500fd2ecd2ed?w=1200&q=60", category="Starter"),
        MenuItem(restaurant_id=r2_id, name="Garlic Naan", description="Soft and buttery", price=2.49, veg=True, spicy=False, image_url="https://images.unsplash.com/photo-1625944527995-7e2e0adf33c5?w=1200&q=60", category="Bread"),
    ]

    for it in items:
        create_document("menuitem", it)

    return {"status": "ok", "restaurants": 2, "items": len(items)}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
