import json
from datetime import datetime, date, time
from typing import Any, Dict, List, Union

# Standard format for datetime strings across the application
DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%S"

def to_standard_datetime_string(dt_obj: Union[datetime, date, str, None]) -> Union[str, None]:
    """
    Convert various datetime formats to a standard string format without timezone information.
    
    Args:
        dt_obj: Datetime object, date object, or string representation of a datetime
        
    Returns:
        Standardized datetime string in YYYY-MM-DDTHH:MM:SS format or None if input is None
    """
    if dt_obj is None:
        return None
        
    # If it's already a string, try to standardize it
    if isinstance(dt_obj, str):
        # Remove timezone indicators if present
        if dt_obj.endswith('Z'):
            dt_obj = dt_obj[:-1]
        elif '+' in dt_obj:
            dt_obj = dt_obj.split('+')[0]
        elif '-' in dt_obj and dt_obj.count('-') > 2:  # Timezone with negative offset
            parts = dt_obj.rsplit('-', 3)
            if len(parts) > 1:
                dt_obj = parts[0]
                
        # Check if it looks like an ISO format already
        if 'T' in dt_obj:
            try:
                # Try to parse and reformat to ensure consistency
                parsed = datetime.fromisoformat(dt_obj)
                return parsed.strftime(DATETIME_FORMAT)
            except (ValueError, TypeError):
                # If parsing fails, return the cleaned string
                return dt_obj
        return dt_obj
        
    # Handle datetime object
    if isinstance(dt_obj, datetime):
        # Remove timezone info if present
        if dt_obj.tzinfo is not None:
            dt_obj = dt_obj.replace(tzinfo=None)
        return dt_obj.strftime(DATETIME_FORMAT)
        
    # Handle date object
    if isinstance(dt_obj, date) and not isinstance(dt_obj, datetime):
        # For date objects, use midnight time
        return f"{dt_obj.strftime('%Y-%m-%d')}T00:00:00"
        
    # Handle time object
    if isinstance(dt_obj, time):
        # For time objects, use epoch date (1970-01-01)
        return f"1970-01-01T{dt_obj.strftime('%H:%M:%S')}"
        
    # If we can't handle it, return as is (will need to be handled by default JSON encoder)
    return str(dt_obj)

def standardize_object_for_json(obj: Any) -> Any:
    """
    Recursively convert all datetime objects in a Python data structure to standard string format.
    
    Handles dictionaries, lists, and individual datetime objects.
    
    Args:
        obj: Any Python object potentially containing datetime objects
        
    Returns:
        Object with all datetime objects converted to strings
    """
    if isinstance(obj, dict):
        return {k: standardize_object_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [standardize_object_for_json(item) for item in obj]
    elif isinstance(obj, (datetime, date, time)):
        return to_standard_datetime_string(obj)
    else:
        return obj

class DateTimeJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles datetime objects"""
    
    def default(self, obj):
        if isinstance(obj, (datetime, date, time)):
            return to_standard_datetime_string(obj)
        return super().default(obj)

# Convenience function for JSON dumps with datetime handling
def json_dumps(obj: Any, **kwargs) -> str:
    """
    Convert object to JSON string with datetime handling.
    
    Args:
        obj: Python object to convert to JSON
        **kwargs: Additional arguments to pass to json.dumps
        
    Returns:
        JSON string representation
    """
    return json.dumps(standardize_object_for_json(obj), **kwargs)