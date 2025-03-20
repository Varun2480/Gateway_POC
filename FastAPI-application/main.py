from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List

SERVICE_NAME= "/restaurants-service"
app = FastAPI(
    title="Restaurants application"
    )

class Restaurant(BaseModel):
    id: int
    name: str
    cuisine: str
    rating: float

restaurants_data = [
    Restaurant(id=1, name="Restaurant A", cuisine="Italian", rating=4.5),
    Restaurant(id=2, name="Restaurant B", cuisine="Mexican", rating=4.0),
    Restaurant(id=3, name="Restaurant C", cuisine="Japanese", rating=4.8),
]

@app.get("/restaurants/", response_model=List[Restaurant])
async def get_restaurants():
    return restaurants_data

@app.post("/restaurants/", response_model=Restaurant, status_code=201)
async def create_restaurant(restaurant: Restaurant):
    for existing_restaurant in restaurants_data:
        if existing_restaurant.id == restaurant.id:
            raise HTTPException(status_code=400, detail="Restaurant with this ID already exists")
    restaurants_data.append(restaurant)
    return restaurant
