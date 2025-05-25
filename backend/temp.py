from fastapi import FastAPI, HTTPException, Depends
from typing import List, Optional
from pydantic import BaseModel
import datetime
import uuid

app = FastAPI(title="FoodieSpot Reservation API")

# Models
class Restaurant(BaseModel):
    id: str
    name: str
    location: str
    cuisine: str
    total_capacity: int
    opening_time: str
    closing_time: str
    description: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    
class Reservation(BaseModel):
    id: str
    restaurant_id: str
    customer_name: str
    customer_email: str
    customer_phone: str
    party_size: int
    reservation_time: datetime.datetime
    status: str = "confirmed"  # confirmed, cancelled, completed

# In-memory database (replace with actual DB in production)
restaurants_db = []
reservations_db = []

# API endpoints
@app.get("/")
def read_root():
    return {"message": "Welcome to FoodieSpot Reservation API"}

@app.get("/restaurants/", response_model=List[Restaurant])
def get_restaurants(
    cuisine: Optional[str] = None, 
    location: Optional[str] = None
):
    filtered = restaurants_db
    
    if cuisine:
        filtered = [r for r in filtered if r.cuisine.lower() == cuisine.lower()]
    if location:
        filtered = [r for r in filtered if location.lower() in r.location.lower()]
        
    return filtered

@app.post("/reservations/", response_model=Reservation)
def create_reservation(reservation: Reservation):
    # Validate restaurant exists
    restaurant = next((r for r in restaurants_db if r.id == reservation.restaurant_id), None)
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    
    # Check available capacity (simplified)
    existing_reservations = [
        r for r in reservations_db 
        if r.restaurant_id == reservation.restaurant_id 
        and r.reservation_time.date() == reservation.reservation_time.date()
    ]
    
    total_guests = sum(r.party_size for r in existing_reservations)
    if total_guests + reservation.party_size > restaurant.total_capacity:
        raise HTTPException(status_code=400, detail="Not enough capacity available")
    
    # Add reservation
    reservation.id = str(uuid.uuid4())
    reservations_db.append(reservation)
    return reservation

import uvicorn
from app import app

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)