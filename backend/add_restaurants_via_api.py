import requests
import json
import uuid

# Make sure the API is running before executing this script
API_URL = "https://agentic-restaurant-reservation-system-backend-962843070701.europe-west1.run.app/restaurants/"

# Sample restaurants data (same as above)
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
    print("Adding restaurants via API...")
    
    successful = 0
    failed = 0
    
    for restaurant in restaurants:
        try:
            response = requests.post(API_URL, json=restaurant, headers={"Authorization": f"Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI4ZjEwNDdhZC0zYTM0LTQzYzUtODhlMS03NGE3ZDI5MjhlNzIiLCJuYW1lIjoiVXNlci0xNDA3IiwicGhvbmUiOiIrOTE5OTgzMzIxNDA3Iiwicm9sZSI6ImN1c3RvbWVyIiwiZXhwIjoxNzQ4Mjg2MzUzLCJpYXQiOjE3NDgxOTk5NTN9.3LU95WAW74qpnGzwqsJsootbG3aUsZUdlIDcyn4ra4A"})

            if response.status_code == 200 or response.status_code == 201:
                print(f"Added restaurant: {restaurant['name']} ({restaurant['cuisine']})")
                successful += 1
            else:
                print(f"Failed to add {restaurant['name']}: {response.status_code} - {response.text}")
                failed += 1
                
        except Exception as e:
            print(f"Error adding {restaurant['name']}: {str(e)}")
            failed += 1
    
    print(f"\nSummary:")
    print(f"Successfully added: {successful} restaurants")
    print(f"Failed to add: {failed} restaurants")

if __name__ == "__main__":
    main()
