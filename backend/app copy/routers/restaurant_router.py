from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
import uuid
from ..models.restaurant import Restaurant
from ..db import get_restaurants, get_restaurant, add_restaurant, update_restaurant, delete_restaurant

router = APIRouter(
    prefix="/restaurants",
    tags=["restaurants"],
    responses={404: {"description": "Not found"}},
)

@router.get("/", response_model=List[Restaurant])
async def read_restaurants(
    cuisine: Optional[str] = None, 
    location: Optional[str] = None,
    limit: Optional[int] = Query(None, description="Limit the number of restaurants returned")
):
    """
    Get all restaurants with optional filtering by cuisine, location, and limit.
    """
    restaurants = get_restaurants(cuisine=cuisine, location=location)
    
    # Apply limit if specified
    if limit is not None:
        restaurants = restaurants[:limit]
        
    return restaurants

@router.get("/{restaurant_id}", response_model=Restaurant)
async def read_restaurant(restaurant_id: str):
    """
    Get a specific restaurant by ID.
    """
    restaurant = get_restaurant(restaurant_id)
    if restaurant is None:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    return restaurant

@router.post("/", response_model=Restaurant)
async def create_restaurant(restaurant: Restaurant):
    """
    Create a new restaurant.
    """
    # Generate a new ID if not provided
    if not restaurant.id:
        restaurant.id = str(uuid.uuid4())
    
    restaurant_dict = restaurant.dict()
    result = add_restaurant(restaurant_dict)
    return result

@router.put("/{restaurant_id}", response_model=Restaurant)
async def update_restaurant_endpoint(restaurant_id: str, restaurant: Restaurant):
    """
    Update an existing restaurant.
    """
    existing = get_restaurant(restaurant_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    
    # Ensure ID doesn't change
    restaurant_dict = restaurant.dict()
    restaurant_dict["id"] = restaurant_id
    
    result = update_restaurant(restaurant_dict)
    return result

@router.delete("/{restaurant_id}")
async def delete_restaurant_endpoint(restaurant_id: str):
    """
    Delete a restaurant.
    """
    existing = get_restaurant(restaurant_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    
    success = delete_restaurant(restaurant_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete restaurant")
    
    return {"message": "Restaurant deleted successfully"}
