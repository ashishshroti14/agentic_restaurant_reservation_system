"""
Tools for the restaurant reservation chat agent to access database information.
These tools allow the agent to ground its responses in real data.
"""
import os
import re
import json
import uuid
import time
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from ..db.database import (
    get_restaurants, 
    get_restaurant, 
    check_availability,
    get_reservations,
    get_reservation,
    add_reservation,
    update_reservation,
    delete_reservation,
    get_user
)
from .logging_utils import log_tool_call, logger

class Tool:
    """Class to represent a tool with metadata."""
    
    def __init__(self, 
                 func, 
                 name: str, 
                 description: str, 
                 input_schema: dict, 
                 output_description: str):
        """
        Initialize a tool with its function and metadata.
        
        Args:
            func: The function that implements the tool
            name: The name of the tool
            description: A description of what the tool does
            input_schema: A dictionary describing the inputs the tool expects
            output_description: A description of the tool's output format
        """
        self.func = func
        self.name = name
        self.description = description
        self.input_schema = input_schema
        self.output_description = output_description
        
    def __call__(self, *args, **kwargs):
        """Make the tool callable, delegating to the wrapped function."""
        start_time = time.time()
        try:
            result = self.func(*args, **kwargs)
            execution_time = time.time() - start_time
            log_tool_call(self.name, kwargs, result, execution_time)
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            log_tool_call(self.name, kwargs, f"ERROR: {str(e)}", execution_time)
            raise
            
    def get_schema(self):
        """Return a dictionary with the tool's metadata."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
            "output_description": self.output_description
        }

# Custom JSON encoder to handle datetime objects
class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

def safe_json_dump(obj: Any) -> str:
    """
    Safely convert an object to a JSON string, handling datetime objects.
    
    Args:
        obj: The object to convert to JSON
        
    Returns:
        A JSON string representation of the object
    """
    try:
        return json.dumps(obj, cls=DateTimeEncoder)
    except Exception as e:
        print(f"Error serializing to JSON: {str(e)}")
        # Try to create a serializable version of the object
        if isinstance(obj, dict):
            serializable_obj = {}
            for key, value in obj.items():
                # Handle datetime objects
                if isinstance(value, datetime):
                    serializable_obj[key] = value.isoformat()
                elif isinstance(value, list):
                    serializable_obj[key] = [
                        item.isoformat() if isinstance(item, datetime) else item 
                        for item in value
                    ]
                else:
                    serializable_obj[key] = str(value)
            return json.dumps(serializable_obj)
        return json.dumps({"error": "Could not serialize object"})

def ensure_id(obj: Dict, prefix: str = "id_") -> Dict:
    """
    Ensure that a database object has an ID.
    If no ID exists, generate one with the given prefix.
    
    Args:
        obj: The database object dictionary
        prefix: A prefix for the generated ID (default: "id_")
        
    Returns:
        The object with an ensured ID
    """
    if not obj:
        return obj
        
    if "id" not in obj or not obj["id"]:
        obj["id"] = f"{prefix}{str(uuid.uuid4())[:8]}"
    
    return obj

class AgentTools:
    """
    A collection of tools that the chat agent can use to retrieve information
    from the database and perform actions.
    """
    
    @staticmethod
    def search_restaurants(criteria: Dict[str, Any]) -> str:
        """
        Advanced search function for restaurants with flexible criteria.
        
        Args:
            criteria: Dictionary of search criteria in the format {column_name: value}
                     For example: {"cuisine": "Italian", "location": "Downtown"}
                     Supports any column in the restaurant table.
            
        Returns:
            JSON string with restaurant results
        """

        print(f"Searching for restaurants with criteria: {criteria}")
        try:
            # Get all restaurants
            all_restaurants = get_restaurants()
            
            # Filter based on criteria
            matching_restaurants = []
            for restaurant in all_restaurants:
                match = True
                for key, value in criteria.items():
                    if key in restaurant:
                        # Case-insensitive partial matching for string values
                        if isinstance(restaurant[key], str) and isinstance(value, str):
                            if value.lower() not in restaurant[key].lower():
                                match = False
                                break
                        # Exact matching for non-string values
                        elif restaurant[key] != value:
                            match = False
                            break
                    else:
                        match = False
                        break
                
                if match:
                    matching_restaurants.append(restaurant)
            
            if not matching_restaurants:
                return json.dumps({
                    "status": "not_found",
                    "message": "No restaurants found matching the criteria.",
                    "criteria": criteria
                })
            
            # Limit results to avoid overwhelming the context
            limited_restaurants = matching_restaurants[:5]
            has_more = len(matching_restaurants) > 5
            
            result = {
                "status": "success",
                "count": len(matching_restaurants),
                "results": limited_restaurants,
                "has_more": has_more
            }
            return json.dumps(result)
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)})
    
    @staticmethod
    def get_restaurant_details(restaurant_id: str) -> str:
        """
        Get detailed information about a specific restaurant.
        
        Args:
            restaurant_id: Unique identifier for the restaurant
            
        Returns:
            JSON string with restaurant details
        """
        try:
            print(f"Fetching details for restaurant ID: {restaurant_id}")
            restaurant = get_restaurant(restaurant_id)
            if not restaurant:
                return json.dumps({
                    "status": "not_found", 
                    "message": f"No restaurant found with ID: {restaurant_id}"
                })
            
            return json.dumps({"status": "success", "restaurant": restaurant})
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)})
    
    @staticmethod
    def get_restaurant_by_name(name: str) -> str:
        """
        Find restaurants that match a given name (full or partial match).
        
        Args:
            name: Full or partial name of the restaurant to search for
            
        Returns:
            JSON string with matching restaurant results
        """
        try:
            # Validate input
            if not name or len(name.strip()) < 2:
                return json.dumps({
                    "status": "error", 
                    "message": "Restaurant name must be at least 2 characters"
                })
                
            name = name.strip()
            print(f"Searching for restaurants with name containing: '{name}'")
            
            # Get all restaurants
            all_restaurants = get_restaurants()
            
            # Calculate match score and filter restaurants (basic fuzzy matching)
            matching_restaurants = []
            
            for restaurant in all_restaurants:
                if 'name' in restaurant and restaurant['name']:
                    # Calculate simple match score (can be improved with fuzzy matching)
                    restaurant_name = restaurant['name'].lower()
                    search_name = name.lower()
                    
                    # Exact match gets highest score
                    if restaurant_name == search_name:
                        restaurant['_match_score'] = 100
                        matching_restaurants.append(restaurant)
                    # Contains the full search term
                    elif search_name in restaurant_name:
                        restaurant['_match_score'] = 80
                        matching_restaurants.append(restaurant)
                    # Partial match (word by word)
                    elif any(word in restaurant_name for word in search_name.split()):
                        restaurant['_match_score'] = 50
                        matching_restaurants.append(restaurant)
            
            if not matching_restaurants:
                # Try a more lenient match if no results
                for restaurant in all_restaurants:
                    if 'name' in restaurant and restaurant['name']:
                        # Try character by character matching
                        common_chars = set(restaurant['name'].lower()) & set(name.lower())
                        if len(common_chars) >= min(2, len(name) // 2):
                            restaurant['_match_score'] = 30
                            matching_restaurants.append(restaurant)
            
            if not matching_restaurants:
                return json.dumps({
                    "status": "not_found",
                    "message": f"No restaurants found matching the name: {name}"
                })
            
            # Sort by match score (highest first)
            matching_restaurants.sort(key=lambda r: r.get('_match_score', 0), reverse=True)
            
            # Remove the temporary match score before returning
            for restaurant in matching_restaurants:
                if '_match_score' in restaurant:
                    del restaurant['_match_score']
            
            # Limit results to avoid overwhelming the context
            limited_restaurants = matching_restaurants[:5]
            has_more = len(matching_restaurants) > 5
            
            result = {
                "status": "success",
                "count": len(matching_restaurants),
                "results": limited_restaurants,
                "has_more": has_more
            }
            return json.dumps(result)
        except Exception as e:
            print(f"Error in get_restaurant_by_name: {str(e)}")
            return json.dumps({"status": "error", "message": str(e)})
    
    @staticmethod
    def check_restaurant_availability(
        restaurant_id: str, 
        date_utc: str,
        party_size: int,
    ) -> str:
        """
        Check if a restaurant has availability for a given date, time, and party size.
        Time is checked in half-hour slots (e.g., 7:00 PM, 7:30 PM).
        
        Args:
            restaurant_id: Unique identifier for the restaurant
            date_utc: Date for the reservation in ISO format (YYYY-MM-DDTHH:MM:SS) 
            party_size: Number of people in the party
            
        Returns:
            JSON string with availability information including time slot options
        """
        try:
            logger.info(f"Checking availability with: restaurant_id={restaurant_id}, date_utc={date_utc}, party_size={party_size}")
            
            # Parse the date_utc string into a datetime object
            if isinstance(date_utc, str):
                requested_datetime = datetime.fromisoformat(date_utc.replace('Z', '+00:00'))
            else:
                requested_datetime = date_utc
            
            logger.info(f"Parsed requested datetime: {requested_datetime.isoformat()}")
            
            # Get restaurant details
            restaurant = get_restaurant(restaurant_id)
            if not restaurant:
                return json.dumps({
                    "status": "not_found",
                    "message": f"No restaurant found with ID: {restaurant_id}"
                })
            
            # Check availability
            availability = check_availability(
                restaurant_id=restaurant_id,
                date_utc=requested_datetime,
                party_size=party_size
            )
            
            # Format the time for display
            formatted_time = requested_datetime.strftime("%I:%M %p on %A, %B %d, %Y")
            
            # If the requested slot is not available, check nearby slots
            alternative_slots = []
            if not availability.get("available", False):
                # Check 30-minute intervals before and after the requested time
                for offset in [-60, -30, 30, 60, 90]:
                    alt_time = requested_datetime + timedelta(minutes=offset)
                    alt_availability = check_availability(
                        restaurant_id=restaurant_id,
                        date_utc=alt_time,
                        party_size=party_size
                    )
                    
                    if alt_availability.get("available", False):
                        alternative_slots.append({
                            "time": alt_time.strftime("%I:%M %p"),
                            "datetime": alt_time.isoformat(),
                            "available": True
                        })

            result = {
                "status": "success",
                "availability": {
                    "requested_time": formatted_time,
                    "requested_datetime": requested_datetime.isoformat(),
                    "available": availability.get("available", False),
                    "reason": availability.get("reason", None) if not availability.get("available", False) else None,
                    "alternative_slots": alternative_slots
                },
                "restaurant": {
                    "id": restaurant_id,
                    "name": restaurant.get("name", "Unknown"),
                    "opening_time": restaurant.get("opening_time", "Unknown"),
                    "closing_time": restaurant.get("closing_time", "Unknown")
                }
            }
            
            return json.dumps(result)
        except Exception as e:
            logger.error(f"Error in check_restaurant_availability: {str(e)}", exc_info=True)
            return json.dumps({"status": "error", "message": f"Error checking availability: {str(e)}"})
    
    @staticmethod
    def get_customer_reservations(identifier_type: str, identifier_value: str) -> str:
        """
        Get reservation history for a specific customer by their name, email, or phone.
        
        Args:
            identifier_type: Type of identifier to use ('name', 'email', or 'phone')
            identifier_value: Value of the identifier (e.g., customer name, email, or phone number)
            
        Returns:
            JSON string with the customer's reservation history
        """
        try:
            # Map identifier types to database field names
            field_mapping = {
                'name': 'customer_name',
                'email': 'customer_email',
                'phone': 'customer_phone'
            }
            
            # Validate identifier type
            if identifier_type not in field_mapping:
                return json.dumps({
                    "status": "error",
                    "message": f"Invalid identifier type: {identifier_type}. Must be one of: name, email, phone."
                })
            
            # Get the correct field name for the query
            field_name = field_mapping[identifier_type]
            
            try:
                # Get reservations for the customer
                reservations = get_reservations(**{field_name: identifier_value})
                
                if not reservations:
                    return json.dumps({
                        "status": "not_found",
                        "message": f"No reservations found for {identifier_type}: {identifier_value}"
                    })
                
                # Sort reservations by date (most recent first)
                reservations.sort(
                    key=lambda r: r.get('reservation_time', datetime.min),
                    reverse=True
                )
                
                # Format reservation dates for display
                for reservation in reservations:
                    if 'reservation_time' in reservation and reservation['reservation_time']:
                        if isinstance(reservation['reservation_time'], datetime):
                            reservation['formatted_time'] = reservation['reservation_time'].strftime(
                                "%I:%M %p on %A, %B %d, %Y"
                            )
                
                # Add restaurant details to each reservation
                for reservation in reservations:
                    if 'restaurant_id' in reservation and reservation['restaurant_id']:
                        restaurant = get_restaurant(reservation['restaurant_id'])
                        if restaurant:
                            reservation['restaurant'] = {
                                'id': restaurant.get('id'),
                                'name': restaurant.get('name', 'Unknown'),
                                'location': restaurant.get('location', 'Unknown')
                            }
                
                return json.dumps({
                    "status": "success",
                    "count": len(reservations),
                    "reservations": reservations
                })
                
            except Exception as db_error:
                return json.dumps({
                    "status": "error",
                    "message": f"Database error: {str(db_error)}"
                })
            
        except Exception as e:
            print(f"Error in get_customer_reservations: {str(e)}")
            return json.dumps({"status": "error", "message": str(e)})

    @staticmethod
    def create_reservation(
        restaurant_id: str,
        customer_name: str,
        customer_email: str,
        customer_phone: str,
        party_size: int,
        reservation_time: str
    ) -> str:
        """
        Create a new reservation.
        
        Args:
            restaurant_id: Unique identifier for the restaurant
            customer_name: Name of the customer
            customer_email: Email of the customer
            customer_phone: Phone number of the customer
            party_size: Number of people in the party
            reservation_time: Date and time for the reservation (ISO format)
            
        Returns:
            JSON string with the created reservation details
        """
        try:
            # Check availability first
            if isinstance(reservation_time, str):
                date_obj = datetime.fromisoformat(reservation_time.replace('Z', '+00:00'))
            else:
                date_obj = reservation_time
                
            availability = check_availability(
                restaurant_id=restaurant_id,
                date_utc=date_obj,
                party_size=party_size
            )
            
            if not availability["available"]:
                return json.dumps({
                    "status": "error",
                    "message": f"Restaurant is not available at the requested time: {availability.get('reason', 'Unknown reason')}",
                    "availability": availability
                })
            
            # Generate a unique reservation ID if the database doesn't do it automatically
            reservation_id = f"res_{str(uuid.uuid4())[:8]}"
            
            # Create the reservation
            reservation_data = {
                "id": reservation_id,
                "restaurant_id": restaurant_id,
                "customer_name": customer_name,
                "customer_email": customer_email,
                "customer_phone": customer_phone,
                "party_size": party_size,
                "reservation_time": date_obj,
                "status": "confirmed"
            }
            
            created_reservation = add_reservation(reservation_data)
            
            # Ensure the returned reservation has an ID
            if created_reservation and ("id" not in created_reservation or not created_reservation["id"]):
                created_reservation["id"] = reservation_id
            
            return json.dumps({
                "status": "success", 
                "message": "Reservation created successfully",
                "reservation": created_reservation
            })
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)})
    
    @staticmethod
    def modify_reservation(
        reservation_id: str,
        update_fields: Dict[str, Any]
    ) -> str:
        """
        Modify an existing reservation by ID with updated field values.
        
        Args:
            reservation_id: ID of the reservation to modify
            update_fields: Dictionary of fields to update (can include party_size, reservation_time, etc.)
            
        Returns:
            JSON string with the modified reservation details
        """
        try:
            logger.info(f"MODIFY: Starting modification of reservation {reservation_id}")
            
            # Handle case where update_fields is passed as a string
            if isinstance(update_fields, str):
                try:
                    # Try to fix common JSON errors
                    json_str = update_fields
                    # Check for missing closing brace
                    if json_str.count('{') > json_str.count('}'):
                        json_str += '}'
                    # Check for missing closing bracket
                    if json_str.count('[') > json_str.count(']'):
                        json_str += ']'
                    
                    # Try to parse the fixed JSON
                    update_fields = json.loads(json_str)
                    logger.info(f"MODIFY: Successfully parsed update_fields: {update_fields}")
                except json.JSONDecodeError as e:
                    # Log the specific JSON error
                    logger.error(f"MODIFY: JSON decode error: {str(e)}")
                    return json.dumps({
                        "status": "error",
                        "message": f"Invalid update_fields format: {update_fields}. Error: {str(e)}"
                    })
            
            # First check if the reservation exists
            existing_reservation = get_reservation(reservation_id)
            if not existing_reservation:
                return json.dumps({
                    "status": "not_found",
                    "message": f"No reservation found with ID: {reservation_id}"
                })
            
            # Create updated reservation data
            updated_data = dict(existing_reservation)
            
            # Apply updates
            for key, value in update_fields.items():
                updated_data[key] = value
            
            logger.info(f"MODIFY: Updating reservation with new data: {update_fields}")
            
            # Update the reservation
            result = update_reservation(updated_data)
            
            if result:
                return json.dumps({
                    "status": "success",
                    "message": "Reservation updated successfully",
                    "reservation": result
                })
            else:
                return json.dumps({
                    "status": "error",
                    "message": "Failed to update reservation"
                })
                
        except Exception as e:
            logger.error(f"MODIFY: Error modifying reservation: {str(e)}")
            return json.dumps({
                "status": "error",
                "message": f"Error modifying reservation: {str(e)}"
            })

    @staticmethod
    def cancel_reservation(identifier_type: str, identifier_value: str, reservation_date: Optional[str] = None) -> str:
        """
        Cancel a reservation based on customer information and optionally reservation date.
        
        Args:
            identifier_type: Type of identifier ('name', 'email', 'phone', or 'id')
            identifier_value: Value of the identifier
            reservation_date: Optional date string to filter reservations
            
        Returns:
            JSON string with the cancellation result
        """
        try:
            logger.info(f"CANCEL: Starting cancellation with {identifier_type}={identifier_value}, date={reservation_date}")
            
            # Map identifier types to database field names
            field_mapping = {
                'name': 'customer_name',
                'email': 'customer_email',
                'phone': 'customer_phone',
                'id': 'id',
                'reservation_id': 'id'
            }
            
            # Validate identifier type
            if identifier_type not in field_mapping:
                return json.dumps({
                    "status": "error",
                    "message": f"Invalid identifier type: {identifier_type}. Must be one of: name, email, phone, id, reservation_id."
                })
            
            # Get the correct field name for the query
            field_name = field_mapping[identifier_type]
            
            try:
                # If identifier is a reservation ID, directly update that reservation
                if identifier_type in ['id', 'reservation_id']:
                    reservation = get_reservation(identifier_value)
                    if not reservation:
                        return json.dumps({
                            "status": "not_found",
                            "message": f"No reservation found with ID: {identifier_value}"
                        })
                    
                    # Update status to cancelled
                    reservation['status'] = 'cancelled'
                    result = update_reservation(reservation)
                    
                    if result:
                        return json.dumps({
                            "status": "success",
                            "message": f"Reservation {identifier_value} has been cancelled",
                            "reservation": result
                        })
                    else:
                        return json.dumps({
                            "status": "error",
                            "message": f"Failed to cancel reservation {identifier_value}"
                        })
                else:
                    # Get all reservations for the customer
                    reservations = get_reservations(**{field_name: identifier_value})
                    
                    if not reservations:
                        return json.dumps({
                            "status": "not_found",
                            "message": f"No reservations found for {identifier_type}: {identifier_value}"
                        })
                    
                    # If date is provided, filter by date
                    if reservation_date:
                        try:
                            # Parse date string to date object for comparison
                            if isinstance(reservation_date, str):
                                # Handle various date formats
                                date_formats = [
                                    "%Y-%m-%d",  # ISO format
                                    "%m/%d/%Y",  # US format
                                    "%d/%m/%Y",  # UK format
                                    "%B %d, %Y"  # Month name format
                                ]
                                
                                parsed_date = None
                                for fmt in date_formats:
                                    try:
                                        parsed_date = datetime.strptime(reservation_date, fmt).date()
                                        break
                                    except ValueError:
                                        continue
                                
                                if not parsed_date:
                                    # Try to handle "today", "tomorrow", etc.
                                    if reservation_date.lower() == "today":
                                        parsed_date = datetime.now().date()
                                    elif reservation_date.lower() == "tomorrow":
                                        parsed_date = (datetime.now() + timedelta(days=1)).date()
                                    else:
                                        raise ValueError(f"Unrecognized date format: {reservation_date}")
                            else:
                                parsed_date = reservation_date.date() if hasattr(reservation_date, 'date') else reservation_date
                            
                            # Filter reservations by date
                            filtered_reservations = []
                            for res in reservations:
                                if 'reservation_time' in res and res['reservation_time']:
                                    res_date = res['reservation_time'].date() if hasattr(res['reservation_time'], 'date') else res['reservation_time']
                                    if res_date == parsed_date:
                                        filtered_reservations.append(res)
                            
                            reservations = filtered_reservations
                            
                        except Exception as date_error:
                            return json.dumps({
                                "status": "error",
                                "message": f"Error parsing reservation date: {str(date_error)}"
                            })
                    
                    if not reservations:
                        return json.dumps({
                            "status": "not_found",
                            "message": f"No reservations found for {identifier_type}: {identifier_value} on date {reservation_date}"
                        })
                    
                    # If multiple reservations exist, return them all and ask for clarification
                    if len(reservations) > 1:
                        return json.dumps({
                            "status": "multiple_found",
                            "message": f"Multiple reservations found for {identifier_type}: {identifier_value}. Please specify which reservation to cancel.",
                            "reservations": reservations
                        })
                    
                    # Cancel the single reservation found
                    reservation = reservations[0]
                    reservation['status'] = 'cancelled'
                    result = update_reservation(reservation)
                    
                    if result:
                        return json.dumps({
                            "status": "success",
                            "message": f"Reservation {reservation.get('id', 'unknown')} has been cancelled",
                            "reservation": result
                        })
                    else:
                        return json.dumps({
                            "status": "error",
                            "message": f"Failed to cancel reservation {reservation.get('id', 'unknown')}"
                        })
                
            except Exception as db_error:
                logger.error(f"CANCEL: Database error: {str(db_error)}")
                return json.dumps({
                    "status": "error",
                    "message": f"Database error: {str(db_error)}"
                })
            
        except Exception as e:
            logger.error(f"CANCEL: General error: {str(e)}")
            return json.dumps({"status": "error", "message": str(e)})


# Define all tools with metadata
AVAILABLE_TOOLS = {
    "search_restaurants": Tool(
        AgentTools.search_restaurants,
        "search_restaurants",
        "Search for restaurants using various criteria like cuisine type, location, or name",
        {
            "criteria": "Dictionary of search criteria in the format {column_name: value}. "
                       "For example: {'cuisine': 'Italian', 'location': 'Downtown'}"
        },
        "Returns a JSON string with restaurant results, including name, cuisine, location, and IDs"
    ),
    
    "get_restaurant_details": Tool(
        AgentTools.get_restaurant_details,
        "get_restaurant_details",
        "Get detailed information about a specific restaurant by ID",
        {
            "restaurant_id": "String ID of the restaurant to retrieve details for"
        },
        "Returns a JSON string with complete restaurant details"
    ),
    
    "get_restaurant_by_name": Tool(
        AgentTools.get_restaurant_by_name,
        "get_restaurant_by_name",
        "Find restaurants that match a given name (full or partial match)",
        {
            "name": "String name (or partial name) of the restaurant to search for"
        },
        "Returns a JSON string with matching restaurant results"
    ),
    
    "check_restaurant_availability": Tool(
        AgentTools.check_restaurant_availability,
        "check_restaurant_availability",
        "Check if a restaurant has availability for a given date, time, and party size",
        {
            "restaurant_id": "String ID of the restaurant to check",
            "date_utc": "Date and time for the reservation in ISO format (YYYY-MM-DDTHH:MM:SS)",
            "party_size": "Integer number of people in the party"
        },
        "Returns a JSON string with availability information including time slot options"
    ),
    
    "get_customer_reservations": Tool(
        AgentTools.get_customer_reservations,
        "get_customer_reservations",
        "Get reservation history for a specific customer by phone",
        {
            "identifier_type": "Type of identifier to use ('phone')",
            "identifier_value": "Value of the identifier (e.g., customer phone number)"
        },
        "Returns a JSON string with the customer's reservation history"
    ),
    
    "create_reservation": Tool(
        AgentTools.create_reservation,
        "create_reservation",
        "Create a new reservation for a customer at a restaurant",
        {
            "restaurant_id": "String ID of the restaurant",
            "customer_name": "String name of the customer",
            "customer_email": "String email of the customer",
            "customer_phone": "String phone number of the customer",
            "party_size": "Integer number of people in the party",
            "reservation_time": "Date and time for the reservation in ISO format (YYYY-MM-DDTHH:MM:SS)"
        },
        "Returns a JSON string with the created reservation details, including reservation ID"
    ),
    
    "modify_reservation": Tool(
        AgentTools.modify_reservation,
        "modify_reservation",
        "Modify an existing reservation by ID with updated field values",
        {
            "reservation_id": "String ID of the reservation to modify",
            "update_fields": "Dictionary of fields to update (can include party_size, reservation_time, status, etc.)"
        },
        "Returns a JSON string with the modified reservation details"
    ),
    
    "cancel_reservation": Tool(
        AgentTools.cancel_reservation,
        "cancel_reservation",
        "Cancel a reservation based on customer information and optionally reservation date",
        {
            "identifier_type": "Type of identifier ('name', 'email', 'phone', or 'id')",
            "identifier_value": "Value of the identifier",
            "reservation_date": "Optional date string to filter reservations"
        },
        "Returns a JSON string with the cancellation result"
    )
}