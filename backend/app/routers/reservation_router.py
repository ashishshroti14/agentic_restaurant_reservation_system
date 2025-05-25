from fastapi import APIRouter, HTTPException, Depends, Query, Body
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
import uuid
import logging
from datetime import datetime
from ..models.reservation import Reservation
from ..db import (
    get_reservations, 
    get_reservation, 
    add_reservation, 
    update_reservation, 
    delete_reservation,
    check_availability,
    get_restaurant
)
from ..dependencies.auth import get_current_user

# Set up logger for this module
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/get-reservations",
    tags=["get-reservations"],
    responses={404: {"description": "Not found"}},
)

# Define the request model for fetching reservations by phone number
class ReservationRequest(BaseModel):
    phone_number: str

@router.post("/", response_model=List[Dict[str, Any]])
async def get_user_reservations(
    request: ReservationRequest = Body(...)  # Explicitly use Body to ensure proper parsing
):
    """
    Get all reservations for a user by phone number.
    """
    logger.debug(f"Fetching reservations for phone number: {request.phone_number}")
    
    # Get reservations for this phone number
    reservations = get_reservations(customer_phone=request.phone_number)
    logger.debug(f"Raw reservations data: {reservations}")
    try:
        reservations = get_reservations(customer_phone=request.phone_number)
        logger.debug(f"Raw reservations data: {reservations}")
        
        # Enhance reservation data with restaurant name
        for reservation in reservations:
            restaurant = get_restaurant(reservation["restaurant_id"])
            if restaurant:
                reservation["restaurant_name"] = restaurant["name"]
        
        logger.info(f"Found {len(reservations)} reservations for phone number {request.phone_number}")
        return reservations
    except Exception as e:
        logger.error(f"Error fetching reservations: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("/{reservation_id}", response_model=Dict[str, Any])
async def read_reservation(
    reservation_id: str
):
    """
    Get a specific reservation by ID.
    """
    reservation = get_reservation(reservation_id)
    if reservation is None:
        raise HTTPException(status_code=404, detail="Reservation not found")
    return reservation

@router.post("/create", response_model=Dict[str, Any])
async def create_reservation(
    reservation: Reservation
):
    """
    Create a new reservation.
    """
    # Generate a new ID if not provided
    if not reservation.id:
        reservation.id = str(uuid.uuid4())
    
    # First check if the restaurant has availability
    availability = check_availability(
        restaurant_id=reservation.restaurant_id,
        date_utc=reservation.reservation_time,
        party_size=reservation.party_size
    )
    
    if not availability.get("available"):
        raise HTTPException(
            status_code=400, 
            detail=f"No availability: {availability.get('reason', 'Unknown reason')}"
        )
    
    reservation_dict = reservation.dict()
    result = add_reservation(reservation_dict)
    return result

@router.put("/{reservation_id}", response_model=Reservation)
async def update_reservation_endpoint(
    reservation_id: str, 
    reservation: Reservation
):
    """
    Update an existing reservation.
    """
    existing = get_reservation(reservation_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Reservation not found")
    
    # Ensure ID doesn't change
    reservation_dict = reservation.dict()
    reservation_dict["id"] = reservation_id
    
    result = update_reservation(reservation_dict)
    return result

@router.delete("/{reservation_id}")
async def delete_reservation_endpoint(
    reservation_id: str
):
    """
    Delete a reservation.
    """
    existing = get_reservation(reservation_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Reservation not found")
    
    success = delete_reservation(reservation_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete reservation")
    
    return {"message": "Reservation deleted successfully"}
