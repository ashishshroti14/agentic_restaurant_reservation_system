from fastapi import APIRouter, HTTPException
from typing import List
from ..models.reservation import Reservation
from ..db.database import (
    get_restaurant,
    add_reservation,
    get_reservation,
    update_reservation,
    delete_reservation,
    check_availability,
)
import uuid
from datetime import datetime

router = APIRouter(
    prefix="/reservations",
    tags=["reservations"],
    responses={404: {"description": "Not found"}},
)

@router.post("/", response_model=Reservation)
def create_reservation(reservation: Reservation):
    # Validate restaurant exists
    restaurant = get_restaurant(reservation.restaurant_id)
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    
    # Check availability
    availability = check_availability(
        restaurant_id=reservation.restaurant_id,
        date=reservation.reservation_time,
        party_size=reservation.party_size
    )
    
    if not availability["available"]:
        raise HTTPException(status_code=400, detail=availability["reason"])
    
    # Add reservation
    reservation_dict = reservation.dict()
    if not reservation_dict.get("id"):
        reservation_dict["id"] = str(uuid.uuid4())
    
    added_reservation = add_reservation(reservation_dict)
    return added_reservation

@router.put("/{reservation_id}", response_model=Reservation)
def update_reservation_endpoint(reservation_id: str, updated_reservation: Reservation):
    # Check if reservation exists
    existing_reservation = get_reservation(reservation_id)
    if not existing_reservation:
        raise HTTPException(status_code=404, detail="Reservation not found")
    
    # Validate restaurant exists
    restaurant = get_restaurant(updated_reservation.restaurant_id)
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    
    # Ensure ID in path matches ID in body
    updated_data = updated_reservation.dict()
    updated_data["id"] = reservation_id
    
    # Check availability if party size or date changed
    if (updated_reservation.party_size != existing_reservation["party_size"] or 
        datetime.fromisoformat(str(updated_reservation.reservation_time)).date() != 
        datetime.fromisoformat(str(existing_reservation["reservation_time"])).date()):
        
        availability = check_availability(
            restaurant_id=updated_reservation.restaurant_id,
            date=updated_reservation.reservation_time,
            party_size=updated_reservation.party_size
        )
        
        if not availability["available"]:
            raise HTTPException(status_code=400, detail=availability["reason"])
    
    # Update reservation
    updated = update_reservation(updated_data)
    return updated

@router.delete("/{reservation_id}")
def delete_reservation_endpoint(reservation_id: str):
    # Check if reservation exists
    existing_reservation = get_reservation(reservation_id)
    if not existing_reservation:
        raise HTTPException(status_code=404, detail="Reservation not found")
    
    # Delete reservation
    success = delete_reservation(reservation_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete reservation")
        
    return {"message": f"Reservation for {existing_reservation['customer_name']} deleted successfully"}
