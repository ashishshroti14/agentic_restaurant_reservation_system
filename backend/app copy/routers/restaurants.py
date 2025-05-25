from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from ..models.restaurant import Restaurant
from ..db.database import get_restaurants as db_get_restaurants, add_restaurant, get_restaurant
from ..utils.auth import get_current_user, verify_admin
import uuid

router = APIRouter(
    prefix="/restaurants",
    tags=["restaurants"],
    responses={404: {"description": "Not found"}},
)

@router.get("/", response_model=List[Restaurant])
def get_restaurants(
    cuisine: Optional[str] = None, 
    location: Optional[str] = None
):
    return db_get_restaurants(cuisine=cuisine, location=location)

@router.post("/", response_model=Restaurant)
def create_restaurant(
    restaurant: Restaurant,
    current_user: dict = Depends(verify_admin)  # Ensure only admins can create restaurants
):
    """Add a new restaurant"""
    # Check if restaurant with same name already exists
    existing_restaurants = db_get_restaurants(location=restaurant.location)
    if any(r["name"].lower() == restaurant.name.lower() for r in existing_restaurants):
        raise HTTPException(
            status_code=400,
            detail=f"Restaurant with name '{restaurant.name}' already exists in {restaurant.location}"
        )
    
    # Check if ID is provided, if not, generate one
    if not restaurant.id:
        restaurant.id = str(uuid.uuid4())
    
    # Add the restaurant to the database
    result = add_restaurant(restaurant.dict())
    
    if not result:
        raise HTTPException(
            status_code=500,
            detail="Failed to create restaurant"
        )
    
    return result

@router.get("/{restaurant_id}", response_model=Restaurant)
def get_restaurant_by_id(restaurant_id: str):
    """Get a specific restaurant by ID"""
    restaurant = get_restaurant(restaurant_id)
    if not restaurant:
        raise HTTPException(
            status_code=404,
            detail="Restaurant not found"
        )
    return restaurant
