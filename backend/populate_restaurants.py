import uuid
import os
import sys
from pathlib import Path

# Add the backend directory to the path so we can import from app
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.db.database import add_restaurant, get_restaurant

# Sample restaurants data
restaurants = [
    {
        "id": str(uuid.uuid4()),
        "name": "Bella Italia",
        "location": "Downtown",
        "cuisine": "Italian",
        "total_capacity": 60,
        "opening_time": "11:00",
        "closing_time": "22:00",
        "description": "Authentic Italian cuisine with homemade pasta and wood-fired pizzas.",
        "latitude": 40.7128,
        "longitude": -74.0060,
        "email": "info@bellaitalia.com",
        "phone": "+1-555-123-4567",
        "website": "https://bellaitalia.example.com",
        "address": "123 Main St, Downtown"
    },
    {
        "id": str(uuid.uuid4()),
        "name": "Sakura Sushi",
        "location": "Midtown",
        "cuisine": "Japanese",
        "total_capacity": 40,
        "opening_time": "12:00",
        "closing_time": "23:00",
        "description": "Premium sushi restaurant offering the freshest fish and traditional Japanese dishes.",
        "latitude": 40.7549,
        "longitude": -73.9840,
        "email": "reservations@sakurasushi.com",
        "phone": "+1-555-234-5678",
        "website": "https://sakurasushi.example.com",
        "address": "456 Park Ave, Midtown"
    },
    {
        "id": str(uuid.uuid4()),
        "name": "Taj Mahal",
        "location": "Uptown",
        "cuisine": "Indian",
        "total_capacity": 50,
        "opening_time": "17:00",
        "closing_time": "23:00",
        "description": "Flavorful Indian cuisine with an extensive menu of curries, tandoori dishes, and fresh naan.",
        "latitude": 40.8075,
        "longitude": -73.9626,
        "email": "contact@tajmahal.com",
        "phone": "+1-555-345-6789",
        "website": "https://tajmahal.example.com",
        "address": "789 Broadway, Uptown"
    },
    {
        "id": str(uuid.uuid4()),
        "name": "Le Petit Bistro",
        "location": "West Side",
        "cuisine": "French",
        "total_capacity": 30,
        "opening_time": "18:00",
        "closing_time": "23:30",
        "description": "Cozy French bistro offering classical dishes with a modern twist.",
        "latitude": 40.7420,
        "longitude": -74.0048,
        "email": "bonjour@lepetitbistro.com",
        "phone": "+1-555-456-7890",
        "website": "https://lepetitbistro.example.com",
        "address": "101 West St, West Side"
    },
    {
        "id": str(uuid.uuid4()),
        "name": "El Mariachi",
        "location": "East Side",
        "cuisine": "Mexican",
        "total_capacity": 70,
        "opening_time": "11:30",
        "closing_time": "22:30",
        "description": "Vibrant Mexican restaurant with authentic tacos, enchiladas, and the best margaritas in town.",
        "latitude": 40.7615,
        "longitude": -73.9570,
        "email": "hola@elmariachi.com",
        "phone": "+1-555-567-8901",
        "website": "https://elmariachi.example.com",
        "address": "202 East Ave, East Side"
    },
    {
        "id": str(uuid.uuid4()),
        "name": "Golden Dragon",
        "location": "Chinatown",
        "cuisine": "Chinese",
        "total_capacity": 80,
        "opening_time": "11:00",
        "closing_time": "23:00",
        "description": "Traditional Chinese restaurant specializing in dim sum and Cantonese cuisine.",
        "latitude": 40.7157,
        "longitude": -73.9970,
        "email": "info@goldendragon.com",
        "phone": "+1-555-678-9012",
        "website": "https://goldendragon.example.com",
        "address": "303 Canal St, Chinatown"
    },
    {
        "id": str(uuid.uuid4()),
        "name": "Acropolis",
        "location": "Greektown",
        "cuisine": "Greek",
        "total_capacity": 45,
        "opening_time": "16:00",
        "closing_time": "22:00",
        "description": "Family-owned Greek taverna serving gyros, souvlaki, and other Mediterranean favorites.",
        "latitude": 40.7310,
        "longitude": -73.9840,
        "email": "hello@acropolis.com",
        "phone": "+1-555-789-0123",
        "website": "https://acropolis.example.com",
        "address": "404 Olympus Dr, Greektown"
    },
    {
        "id": str(uuid.uuid4()),
        "name": "Texas BBQ",
        "location": "South District",
        "cuisine": "American",
        "total_capacity": 90,
        "opening_time": "12:00",
        "closing_time": "21:00",
        "description": "Slow-smoked meats and classic Southern sides in a casual, family-friendly setting.",
        "latitude": 40.6892,
        "longitude": -73.9922,
        "email": "eat@texasbbq.com",
        "phone": "+1-555-890-1234",
        "website": "https://texasbbq.example.com",
        "address": "505 Longhorn Rd, South District"
    },
    {
        "id": str(uuid.uuid4()),
        "name": "Vegan Delight",
        "location": "Downtown",
        "cuisine": "Vegan",
        "total_capacity": 35,
        "opening_time": "10:00",
        "closing_time": "20:00",
        "description": "Creative plant-based dishes that satisfy both vegans and non-vegans alike.",
        "latitude": 40.7200,
        "longitude": -74.0100,
        "email": "hello@vegandelight.com",
        "phone": "+1-555-901-2345",
        "website": "https://vegandelight.example.com",
        "address": "606 Green St, Downtown"
    },
    {
        "id": str(uuid.uuid4()),
        "name": "Mumbai Spice",
        "location": "Midtown",
        "cuisine": "Indian",
        "total_capacity": 55,
        "opening_time": "11:30",
        "closing_time": "22:30",
        "description": "Modern Indian cuisine with focus on street food and regional specialties.",
        "latitude": 40.7540,
        "longitude": -73.9950,
        "email": "spice@mumbai.com",
        "phone": "+1-555-012-3456",
        "website": "https://mumbaispice.example.com",
        "address": "707 Curry Lane, Midtown"
    }
]

def main():
    print("Starting to populate restaurants...")
    
    # Create the database directory if it doesn't exist
    db_dir = Path(__file__).parent / "data"
    db_dir.mkdir(exist_ok=True)
    
    successful = 0
    already_exists = 0
    failed = 0
    
    for restaurant in restaurants:
        # Check if a restaurant with the same name already exists
        existing_restaurants = [r for r in get_restaurant_by_name(restaurant["name"])]
        
        if existing_restaurants:
            print(f"Restaurant '{restaurant['name']}' already exists. Skipping...")
            already_exists += 1
            continue
            
        try:
            add_restaurant(restaurant)
            print(f"Added restaurant: {restaurant['name']} ({restaurant['cuisine']})")
            successful += 1
        except Exception as e:
            print(f"Failed to add restaurant {restaurant['name']}: {str(e)}")
            failed += 1
    
    print(f"\nSummary:")
    print(f"Successfully added: {successful} restaurants")
    print(f"Already existing: {already_exists} restaurants")
    print(f"Failed to add: {failed} restaurants")

def get_restaurant_by_name(name):
    """Helper function to check if a restaurant with the given name exists"""
    from app.db.database import get_connection
    
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM restaurants WHERE name = ?", (name,))
        return cursor.fetchall()

if __name__ == "__main__":
    main()
